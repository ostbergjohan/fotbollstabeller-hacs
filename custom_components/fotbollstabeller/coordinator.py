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

from .const import BASE_URL, DEFAULT_API_KEY, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)
_STORAGE_VERSION = 2

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "sv-SE,sv;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://www.thesportsdb.com",
    "Referer": "https://www.thesportsdb.com/",
    "Connection": "keep-alive",
}

_SPORTSDB_LEAGUE_ALIASES = {
    "allsvenskan": "4347",
    "allsvenskan-herrar": "4347",
    "fotbollsallsvenskan": "4347",
    "swedish allsvenskan": "4347",
    "damallsvenskan": "5209",
    "sweden damallsvenskan": "5209",
    "svenska cupen": "4756",
    "cupen": "4756",
    "ettan norra": "4674",
    "division 1 north": "4674",
    "swedish division 1 north": "4674",
    "ettan sodra": "4845",
    "division 1 south": "4845",
    "swedish division 1 south": "4845",
}

_SPORTSDB_LEAGUE_NAMES = {
    "4347": "Swedish Allsvenskan",
    "5209": "Sweden Damallsvenskan",
    "4756": "Svenska Cupen",
    "4674": "Swedish Division 1 North",
    "4845": "Swedish Division 1 South",
}

# GD column: "19-7 (12)" or "0-16 (−16)"
_GD_RE = re.compile(r"(\d+)\s*[-–]\s*(\d+)\s*\(\s*([+\-−]?\d+)\s*\)")

# Extract data-id from group page
_DATA_ID_RE = re.compile(r'data-id="(\d+)"')

# New page format: pipe-delimited standings rows rendered directly in the page HTML
_PIPE_STANDINGS_RE = re.compile(
    r"\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([+\-−]?\d+)\s*\|\s*(\d+)\s*\|",
    re.IGNORECASE,
)


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


def _resolve_league_id(group_url: str) -> str:
    """Resolve a legacy slug, team-card input or API league ID to a SportsDB league id."""
    raw = (group_url or "").strip().rstrip("/")
    if not raw:
        raise UpdateFailed("No league specified")

    text = raw
    if text.startswith("http://") or text.startswith("https://"):
        text = text.split("//", 1)[-1].split("/", 1)[-1] if "/" in text.split("//", 1)[-1] else ""
        if not text:
            raise UpdateFailed("Unsupported league URL")

    cleaned = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    if cleaned.isdigit():
        return cleaned

    if cleaned in _SPORTSDB_LEAGUE_ALIASES:
        return _SPORTSDB_LEAGUE_ALIASES[cleaned]

    # Accept legacy names like 'allsvenskan-herrar' after converting to a space-separated key.
    normalized = cleaned.replace("-", " ")
    if normalized in _SPORTSDB_LEAGUE_ALIASES:
        return _SPORTSDB_LEAGUE_ALIASES[normalized]

    if text in _SPORTSDB_LEAGUE_NAMES.values():
        for league_id, league_name in _SPORTSDB_LEAGUE_NAMES.items():
            if league_name == text:
                return league_id

    raise UpdateFailed(f"Unsupported league '{group_url}'")


def _normalize_sportsdb_table(table: list[dict]) -> list[dict]:
    """Map SportsDB table rows to the Home Assistant standings schema."""
    standings: list[dict] = []
    for row in table:
        team = str(row.get("strTeam") or "").strip()
        if not team:
            continue

        try:
            position = int(str(row.get("intRank") or 0))
        except (TypeError, ValueError):
            position = 0

        try:
            played = int(str(row.get("intPlayed") or 0))
            won = int(str(row.get("intWin") or 0))
            draw = int(str(row.get("intDraw") or 0))
            lost = int(str(row.get("intLoss") or 0))
            goals_for = int(str(row.get("intGoalsFor") or 0))
            goals_against = int(str(row.get("intGoalsAgainst") or 0))
            goal_difference = int(str(row.get("intGoalDifference") or 0))
            points = int(str(row.get("intPoints") or 0))
        except (TypeError, ValueError):
            continue

        standings.append(
            {
                "position": position,
                "team": team,
                "team_short": team,
                "team_logo": row.get("strBadge"),
                "played_games": played,
                "won": won,
                "draw": draw,
                "lost": lost,
                "goals_for": goals_for,
                "goals_against": goals_against,
                "goal_difference": goal_difference,
                "points": points,
            }
        )
    return standings


def _extract_group_name(html: str) -> str:
    """Extract the group name from the page markup."""
    h1p = _H1Parser()
    h1p.feed(html)
    name = h1p.text.strip()
    if name:
        return name

    match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    title = re.sub(r"\s+", " ", match.group(1)).strip()
    return title.split(" | ")[0].split(" – ")[0].strip()


def _parse_standings(html: str) -> list[dict]:
    """Parse standings from legacy AJAX markup or the current page-rendered table."""
    tp = _DivTableParser()
    tp.feed(html)
    if tp.rows:
        # First row should be headers
        headers = [h.upper() for h in tp.rows[0]]
        if "RK" in headers and "TP" in headers:
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
            if standings:
                return standings

    standings: list[dict] = []
    for match in _PIPE_STANDINGS_RE.findall(html):
        pos_txt, team, played_txt, won_txt, draw_txt, lost_txt, gd_txt, points_txt = match
        try:
            pos = int(pos_txt)
            played = int(played_txt)
            won = int(won_txt)
            draw = int(draw_txt)
            lost = int(lost_txt)
            points = int(points_txt)
        except ValueError:
            continue

        gd = int(gd_txt.replace("\u2212", "-"))
        team = team.strip()
        if not team:
            continue

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
                "goals_for": 0,
                "goals_against": 0,
                "goal_difference": gd,
                "points": points,
            }
        )

    return standings


async def fetch_standings(
    session: aiohttp.ClientSession,
    group_url: str,
    timeout: aiohttp.ClientTimeout | None = None,
    api_key: str | None = None,
) -> tuple[str, list[dict]]:
    """Fetch standings from the SportsDB API using a legacy league slug/id."""
    if timeout is None:
        timeout = aiohttp.ClientTimeout(total=15)

    league_id = _resolve_league_id(group_url)
    league_name = _SPORTSDB_LEAGUE_NAMES.get(league_id, "Swedish league")
    api_key = (api_key or DEFAULT_API_KEY).strip() or DEFAULT_API_KEY
    api_url = f"{BASE_URL}/{api_key}/lookuptable.php?l={league_id}"

    try:
        async with session.get(api_url, headers=_HEADERS, timeout=timeout) as resp:
            if resp.status != 200:
                raise UpdateFailed(f"SportsDB returned HTTP {resp.status}")
            payload = await resp.json()
    except Exception as err:  # noqa: BLE001
        raise UpdateFailed(f"Unable to fetch standings from SportsDB: {err}") from err

    table = payload.get("table") if isinstance(payload, dict) else None
    if not table:
        raise UpdateFailed(f"No standings table found for league {league_id}")

    standings = _normalize_sportsdb_table(table)
    if not standings:
        raise UpdateFailed(f"Could not parse standings for league {league_id}")

    return league_name, standings


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
