"""Sensor platform for Fotbollstabeller integration.

NOTE: This file is kept for backward compatibility but no sensors
are created in v3+. Cards use WebSocket directly.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """No sensors are created in v3+."""
    return
