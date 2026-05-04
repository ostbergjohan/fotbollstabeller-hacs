"""Fotbollstabeller HACS Integration (fotbollstabeller.nu)."""
from __future__ import annotations

import logging
import pathlib
import time

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, BASE_URL, KNOWN_LEAGUES
from .coordinator import fetch_standings

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_CARD_URL = f"/{DOMAIN}/fotbollstabeller-card.js"
_TEAM_CARD_URL = f"/{DOMAIN}/fotbollstabeller-team-card.js"
_CARD_VERSION = "7"  # bump this to bust browser cache after updates

_WS_CACHE_TTL = 300  # 5 minutes


# ─── Websocket commands ────────────────────────────────────────────


@websocket_api.websocket_command(
    {
        vol.Required("type"): "fotbollstabeller/get_standings",
        vol.Required("url"): str,
    }
)
@websocket_api.async_response
async def ws_get_standings(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Fetch and return standings for any fotbollstabeller.nu group URL/slug."""
    raw = msg["url"].strip().rstrip("/")
    url = raw if raw.startswith("http") else f"{BASE_URL}/home/group/{raw}"

    # Simple in-memory cache
    cache: dict = hass.data[DOMAIN].setdefault("_ws_cache", {})
    now = time.time()
    if url in cache and now - cache[url]["ts"] < _WS_CACHE_TTL:
        connection.send_result(msg["id"], cache[url]["data"])
        return

    session = async_get_clientsession(hass)
    try:
        group_name, standings = await fetch_standings(session, url)
    except Exception as err:  # noqa: BLE001
        connection.send_error(msg["id"], "fetch_error", str(err))
        return

    result = {"group_name": group_name, "standings": standings}
    cache[url] = {"data": result, "ts": now}
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {vol.Required("type"): "fotbollstabeller/get_leagues"}
)
@websocket_api.async_response
async def ws_get_leagues(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Return list of known leagues."""
    connection.send_result(msg["id"], KNOWN_LEAGUES)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Serve the card JS as a static file and register websocket commands."""
    hass.data.setdefault(DOMAIN, {})

    # Register websocket commands (available even without a config entry)
    websocket_api.async_register_command(hass, ws_get_standings)
    websocket_api.async_register_command(hass, ws_get_leagues)

    www_dir = pathlib.Path(__file__).parent / "www"
    js_path = str(www_dir / "fotbollstabeller-card.js")
    team_js_path = str(www_dir / "fotbollstabeller-team-card.js")

    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(_CARD_URL, js_path, False),
                StaticPathConfig(_TEAM_CARD_URL, team_js_path, False),
            ]
        )
    except (ImportError, AttributeError):
        try:
            hass.http.register_static_path(_CARD_URL, js_path, False)
            hass.http.register_static_path(_TEAM_CARD_URL, team_js_path, False)
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Fotbollstabeller: could not register static path: %s", err)
            return True
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Fotbollstabeller: could not register static path: %s", err)
        return True

    for card_url in (_CARD_URL, _TEAM_CARD_URL):
        url = f"{card_url}?v={_CARD_VERSION}"
        add_extra_js_url(hass, url)
        _LOGGER.info("Fotbollstabeller: card JS registered at %s", url)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Fotbollstabeller from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True
