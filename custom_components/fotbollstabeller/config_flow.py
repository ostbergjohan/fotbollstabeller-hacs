"""Config flow for Fotbollstabeller integration."""
from __future__ import annotations

import logging
import re

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_GROUP_URL, BASE_URL
from .coordinator import fetch_standings

_LOGGER = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*",
}


def _normalize_url(raw: str) -> tuple[str, str]:
    """Return (full_url, slug) from whatever the user typed."""
    url = raw.strip().rstrip("/")

    # Bare slug, e.g. "u17-allsvenskan-sodra"
    if "/" not in url:
        return f"{BASE_URL}/home/group/{url}", url

    # Strip protocol
    clean = re.sub(r"^https?://(www\.)?", "", url)

    if clean.startswith("fotbollstabeller.nu"):
        url = "https://www." + clean
    elif not raw.startswith("http"):
        url = "https://" + raw

    match = re.search(r"/home/group/([^/?#]+)", url)
    slug = match.group(1) if match else url.split("/")[-1]
    return url, slug


class FotbollstabellerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fotbollstabeller."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Ask for a fotbollstabeller.nu group URL."""
        errors: dict[str, str] = {}

        if user_input is not None:
            url, slug = _normalize_url(user_input[CONF_GROUP_URL])

            await self.async_set_unique_id(f"{DOMAIN}_{slug}")
            self._abort_if_unique_id_configured()

            # Validate by doing the real two-step fetch (group page + AJAX)
            session = async_get_clientsession(self.hass)
            group_name = slug
            try:
                group_name, standings = await fetch_standings(session, url)
                if not standings:
                    errors["base"] = "no_standings"
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("Validation fetch failed: %s", err)
                errors["base"] = "cannot_connect"

            if not errors:
                return self.async_create_entry(
                    title=group_name,
                    data={CONF_GROUP_URL: url},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_GROUP_URL): str,
                }
            ),
            errors=errors,
        )
