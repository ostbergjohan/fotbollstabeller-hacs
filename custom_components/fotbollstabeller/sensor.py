"""Sensor platform for Fotbollstabeller integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_GROUP_URL
from .coordinator import FotbollstabellerCoordinator

_LOGGER = logging.getLogger(__name__)


def _slug(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Fotbollstabeller sensors from a config entry."""
    coordinator: FotbollstabellerCoordinator = hass.data[DOMAIN][entry.entry_id]
    slug = _slug(entry.data.get(CONF_GROUP_URL, ""))

    group_name = ""
    if coordinator.data:
        group_name = coordinator.data.get("group_name", slug)

    entities: list[SensorEntity] = [TableSensor(coordinator, entry, slug, group_name)]

    if coordinator.data and coordinator.data.get("standings"):
        for row in coordinator.data["standings"]:
            entities.append(
                TeamSensor(coordinator, entry, slug, group_name, row["team"])
            )

    async_add_entities(entities, True)


class TableSensor(CoordinatorEntity, SensorEntity):
    """Sensor that holds the full standings table for a group."""

    _attr_icon = "mdi:soccer"

    def __init__(
        self,
        coordinator: FotbollstabellerCoordinator,
        entry: ConfigEntry,
        slug: str,
        group_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{slug}_table"
        self._attr_name = f"{group_name} Tabell" if group_name else f"{slug} Tabell"
        self._entry = entry

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data and self.coordinator.data.get("standings"):
            return self.coordinator.data["standings"][0].get("team")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        return {
            "group_name": self.coordinator.data.get("group_name"),
            "standings": self.coordinator.data.get("standings", []),
        }


class TeamSensor(CoordinatorEntity, SensorEntity):
    """Sensor for an individual team's current standing."""

    _attr_icon = "mdi:soccer"

    def __init__(
        self,
        coordinator: FotbollstabellerCoordinator,
        entry: ConfigEntry,
        slug: str,
        group_name: str,
        team_name: str,
    ) -> None:
        super().__init__(coordinator)
        safe_name = team_name.lower().replace(" ", "_").replace("-", "_")
        self._attr_unique_id = f"{DOMAIN}_{slug}_team_{safe_name}"
        self._attr_name = f"{group_name} {team_name}" if group_name else team_name
        self._team_name = team_name

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None

    def _get_team_row(self) -> dict | None:
        if not self.coordinator.data:
            return None
        for row in self.coordinator.data.get("standings", []):
            if row.get("team") == self._team_name:
                return row
        return None

    @property
    def native_value(self) -> int | None:
        row = self._get_team_row()
        return row.get("position") if row else None

    @property
    def native_unit_of_measurement(self) -> str:
        return "pos"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        row = self._get_team_row()
        if not row:
            return {}
        return {
            "team": row.get("team"),
            "points": row.get("points"),
            "played": row.get("played_games"),
            "won": row.get("won"),
            "draw": row.get("draw"),
            "lost": row.get("lost"),
            "goals_for": row.get("goals_for"),
            "goals_against": row.get("goals_against"),
            "goal_difference": row.get("goal_difference"),
            "crest": row.get("team_logo"),
        }
