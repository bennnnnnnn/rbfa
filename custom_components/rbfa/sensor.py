"""Platform for sensor integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import RbfaConfigEntry, RbfaCoordinator
from .entity import RbfaEntity
from .helpers import entry_option
from .models import Match, MatchTeam

SERIES_LOGO_URL = "https://www.rbfa.be/assets/img/icons/organisers/Logo{}.svg"


@dataclass(frozen=True, kw_only=True)
class RbfaSensorEntityDescription(SensorEntityDescription):
    """Describes an RBFA sensor."""

    value_fn: Callable[[Match], str | datetime | None]
    picture_fn: Callable[[Match], str | None] = lambda _: None
    attrs_fn: Callable[[Match], dict[str, Any]] = lambda _: {}


def _team_attrs(team: MatchTeam) -> dict[str, Any]:
    attrs = {
        "id": team.id,
        "goals": team.goals,
        "penalties": team.penalties,
        "position": team.position,
    }
    return {k: v for k, v in attrs.items() if v is not None}


SENSORS: tuple[RbfaSensorEntityDescription, ...] = (
    RbfaSensorEntityDescription(
        key="starttime",
        translation_key="starttime",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda m: m.starttime,
    ),
    RbfaSensorEntityDescription(
        key="endtime",
        translation_key="endtime",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda m: m.endtime,
    ),
    RbfaSensorEntityDescription(
        key="hometeam",
        translation_key="hometeam",
        value_fn=lambda m: m.home.name,
        picture_fn=lambda m: m.home.logo,
        attrs_fn=lambda m: _team_attrs(m.home),
    ),
    RbfaSensorEntityDescription(
        key="awayteam",
        translation_key="awayteam",
        value_fn=lambda m: m.away.name,
        picture_fn=lambda m: m.away.logo,
        attrs_fn=lambda m: _team_attrs(m.away),
    ),
    RbfaSensorEntityDescription(
        key="location",
        translation_key="location",
        icon="mdi:soccer-field",
        value_fn=lambda m: m.location,
    ),
    RbfaSensorEntityDescription(
        key="series",
        translation_key="series",
        icon="mdi:table-row",
        value_fn=lambda m: m.series,
        picture_fn=lambda m: SERIES_LOGO_URL.format(m.channel.upper()),
        attrs_fn=lambda m: (
            {
                "ranking": [
                    {"position": r.position, "team": r.name, "id": r.team_id}
                    for r in m.ranking
                ]
            }
            if m.ranking
            else {}
        ),
    ),
    RbfaSensorEntityDescription(
        key="referee",
        translation_key="referee",
        icon="mdi:whistle",
        value_fn=lambda m: m.referee,
    ),
    RbfaSensorEntityDescription(
        key="matchid",
        translation_key="matchid",
        icon="mdi:soccer",
        value_fn=lambda m: m.id,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RbfaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up RBFA sensor based on a config entry."""
    coordinator = entry.runtime_data
    show_referee = entry_option(entry, "show_referee", True)

    async_add_entities(
        RbfaSensor(coordinator, description, entry, collection)
        for description in SENSORS
        if show_referee or description.key != "referee"
        for collection in ("upcoming", "lastmatch")
    )


class RbfaSensor(RbfaEntity, SensorEntity):
    """Representation of a Sensor."""

    entity_description: RbfaSensorEntityDescription
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: RbfaCoordinator,
        description: RbfaSensorEntityDescription,
        entry: RbfaConfigEntry,
        collection: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self.collection = collection
        self.team = entry.data.get("team")
        self._attr_unique_id = f"{DOMAIN}_{collection}_{description.key}_{self.team}"

        self._update_attrs()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_attrs()
        super()._handle_coordinator_update()

    def _update_attrs(self) -> None:
        """Set state, picture and attributes from the latest coordinator data."""
        match: Match | None = getattr(self.coordinator.data, self.collection)
        description = self.entity_description
        attributes: dict[str, Any] = {"baseid": self.team, "tag": self.collection}
        if match is None:
            self._attr_native_value = None
            self._attr_entity_picture = None
        else:
            self._attr_native_value = description.value_fn(match)
            self._attr_entity_picture = description.picture_fn(match)
            attributes |= description.attrs_fn(match)
        self._attr_extra_state_attributes = attributes
