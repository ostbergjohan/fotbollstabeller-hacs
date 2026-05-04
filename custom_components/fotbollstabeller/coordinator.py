"""Data coordinator for Fotbollstabeller integration (fotbollstabeller.nu)."""
from __future__ import annotations

import logging
import re
from datetime import timedelta
from html.parser import HTMLParser

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .const import DOMAIN, BASE_URL, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)
_STORAGE_VERSION = 2

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*",
}

# GD column: "19-7 (12)" or "0-16 (−16)"
_GD_RE = re.compile(r"(\d+)\s*[-–]\s*(\d+)\s*\(\s*([+\-−]?\d+)\s*\)")

# Extract data-id from group page
_DATA_ID_RE = re.compile(r'data-id="(\d+)"')


# ---------------------------------------------------------------------------
# HTML parsers
# ---------------------------------------------------------------------------

class _H1Parser(HTMLParser):
    """Extract the first <h1> text."""

    def __init__(self):
        super().__init__()
        self.text: str = ""
        self._inside = False

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "h1":
            self._inside = True

    def handle_endtag(self, tag):
        if tag.lower() == "h1":
            self._inside = False

    def handle_data(self, data):
        if self._inside:
            self.text += data


class _DivTableParser(HTMLParser):
    """Parse the div-based table returned by /home/get_group_details/{id}.

    Structure:
      <h2 class="annytab-basic-title-container">Tabell</h2>
      <div class="annytab-list-table">
        <div class="annytab-list-tr">          ← header row
          <div class="annytab-list-th-center">RK</div>
          ...
        </div>
        <div class="annytab-list-tr-main">     ← data row
          <div class="annytab-list-td-center">1</div>
          ...
        </div>
      </div>

    The response contains multiple sections (Tabell, Resultat, etc.).
    We only parse the first div-table that has RK/TP headers.
    """

    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self._cur_row: list[str] | None = None
        self._cur_cell: str | None = None
        self._in_cell = False
        self._in_table = False
        self._done = False  # stop after first valid table

    def handle_starttag(self, tag, attrs):
        if self._done:
            return
        if tag.lower() != "div":
            return
        cls = dict(attrs).get("class", "")

        # Detect start of a list-table section
        if cls == "annytab-list-table":
            self._in_table = True
            return

        if not self._in_table:
            return

        # Start of a row (header or data)
        if cls in ("annytab-list-tr", "annytab-list-tr-main", "annytab-list-tr-alt"):
            self._cur_row = []
        # Start of a cell (header or data)
        elif cls.startswith("annytab-list-th-") or cls.startswith("annytab-list-td-"):
            if self._cur_row is not None:
                self._cur_cell = ""
                self._in_cell = True

    def handle_endtag(self, tag):
        if self._done:
            return
        if tag.lower() != "div":
            return
        if self._in_cell and self._cur_cell is not None:
            if self._cur_row is not None:
                self._cur_row.append(self._cur_cell.strip())
            self._cur_cell = None
            self._in_cell = False
        elif self._cur_row is not None and not self._in_cell:
            if self._cur_row:
                self.rows.append(self._cur_row)
            self._cur_row = None
        elif self._in_table and self._cur_row is None and not self._in_cell:
            # End of the annytab-list-table div
            if self.rows:
                # Check if this was the standings table (has RK + TP headers)
                hdrs = [h.upper() for h in self.rows[0]] if self.rows else []
                if "RK" in hdrs and "TP" in hdrs:
                    self._done = True  # we found the standings, stop
                else:
                    self.rows.clear()  # not the right table, reset
            self._in_table = False

    def handle_data(self, data):
        if self._done:
            return
        if self._in_cell and self._cur_cell is not None:
            self._cur_cell += data


# ---------------------------------------------------------------------------
# Parse helpers
# ---------------------------------------------------------------------------

def _extract_group_id(html: str) -> str | None:
    """Extract the data-id attribute from the group page HTML."""
    m = _DATA_ID_RE.search(html)
    return m.group(1) if m else None


def _extract_group_name(html: str) -> str:
    """Extract the group name from the <h1> tag."""
    h1p = _H1Parser()
    h1p.feed(html)
    return h1p.text.strip()


def _parse_standings(html: str) -> list[dict]:
    """Parse the div-based standings from the AJAX response."""
    tp = _DivTableParser()
    tp.feed(html)

    if not tp.rows:
        return []

    # First row should be headers
    headers = [h.upper() for h in tp.rows[0]]
    if "RK" not in headers or "TP" not in headers:
        return []

    idx: dict[str, int] = {}
    for key in ("RK", "LAG", "GP", "W", "T", "L", "GD", "TP"):
        if key in headers:
            idx[key] = headers.index(key)

    standings: list[dict] = []
    for row in tp.rows[1:]:
        if not row:
            continue
        try:
            pos = int(row[idx["RK"]])
        except (ValueError, IndexError, KeyError):
            continue

        team = row[idx["LAG"]] if "LAG" in idx and idx["LAG"] < len(row) else ""
        played = _safe_int(row, idx.get("GP"))
        won = _safe_int(row, idx.get("W"))
        draw = _safe_int(row, idx.get("T"))
        lost = _safe_int(row, idx.get("L"))
        points = _safe_int(row, idx.get("TP"))

        gf, ga, gd = 0, 0, 0
        if "GD" in idx and idx["GD"] < len(row):
            m = _GD_RE.search(row[idx["GD"]])
            if m:
                gf = int(m.group(1))
                ga = int(m.group(2))
                gd = int(m.group(3).replace("\u2212", "-"))

        standings.append(
            {
                "position": pos,
                "team": team,
                "team_short": team,
                "team_logo": None,
                "played_games": played,
                "won": won,
                "draw": draw,
                "lost": lost,
                "goals_for": gf,
                "goals_against": ga,
                "goal_difference": gd,
                "points": points,
            }
        )

    return standings


async def fetch_standings(
    session: aiohttp.ClientSession,
    group_url: str,
    timeout: aiohttp.ClientTimeout | None = None,
) -> tuple[str, list[dict]]:
    """Fetch standings for a group URL or slug.

    Two-step process:
    1. GET the group page to extract the group name (<h1>) and AJAX id (data-id).
    2. GET /home/get_group_details/{id} to get the div-based standings table.

    Returns (group_name, standings_list).
    """
    if timeout is None:
        timeout = aiohttp.ClientTimeout(total=15)

    # Normalise URL
    url = group_url.strip().rstrip("/")
    if not url.startswith("http"):
        url = f"{BASE_URL}/home/group/{url}"

    # Step 1: Fetch group page for name + data-id
    async with session.get(url, headers=_HEADERS, timeout=timeout) as resp:
        if resp.status != 200:
            raise UpdateFailed(f"fotbollstabeller.nu returned HTTP {resp.status}")
        page_html = await resp.text()

    group_name = _extract_group_name(page_html)
    group_id = _extract_group_id(page_html)

    if not group_id:
        raise UpdateFailed("Could not find data-id on group page")

    # Step 2: Fetch AJAX standings
    ajax_url = f"{BASE_URL}/home/get_group_details/{group_id}"
    ajax_headers = {**_HEADERS, "X-Requested-With": "XMLHttpRequest"}
    async with session.get(ajax_url, headers=ajax_headers, timeout=timeout) as resp:
        if resp.status != 200:
            raise UpdateFailed(f"AJAX endpoint returned HTTP {resp.status}")
        ajax_html = await resp.text()

    standings = _parse_standings(ajax_html)
    return group_name, standings


def _safe_int(row: list[str], idx: int | None) -> int:
    if idx is None or idx >= len(row):
        return 0
    try:
        return int(row[idx])
    except (ValueError, TypeError):
        return 0


# ---------------------------------------------------------------------------
# Coordinator
# ---------------------------------------------------------------------------

class FotbollstabellerCoordinator(DataUpdateCoordinator):
    """Fetch standings from fotbollstabeller.nu and parse the HTML table."""

    def __init__(self, hass: HomeAssistant, group_url: str) -> None:
        slug = group_url.rstrip("/").split("/")[-1]
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{slug}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.group_url = group_url
        self.session = async_get_clientsession(hass)
        self._store = Store(hass, _STORAGE_VERSION, f"{DOMAIN}.cache.{slug}")

    async def _async_update_data(self) -> dict:
        """Fetch group page + AJAX standings, cache result."""
        try:
            group_name, standings = await fetch_standings(
                self.session, self.group_url
            )
        except Exception as err:  # noqa: BLE001
            cached = await self._store.async_load()
            if cached:
                _LOGGER.warning(
                    "Fetch failed (%s). Using cached standings.", err
                )
                return cached
            raise UpdateFailed(f"Error fetching data: {err}") from err

        if not standings:
            cached = await self._store.async_load()
            if cached:
                _LOGGER.warning("No standings found. Using cached data.")
                return cached
            raise UpdateFailed("No standings table found on page")

        result = {
            "group_name": group_name,
            "standings": standings,
        }

        await self._store.async_save(result)
        return result
