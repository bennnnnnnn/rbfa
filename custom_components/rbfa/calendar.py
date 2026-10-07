"""Platform for calendar integration."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import RbfaConfigEntry, RbfaCoordinator
from .entity import RbfaEntity
from .helpers import entry_option

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RbfaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up RBFA calendar based on a config entry."""
    coordinator = entry.runtime_data

    async_add_entities(
        [
            TeamCalendar(
                coordinator,
                entry,
            )
        ]
    )


class TeamCalendar(RbfaEntity, CalendarEntity):
    """Defines a RBFA Team Calendar."""

    _attr_icon = "mdi:soccer"

    def __init__(
        self,
        coordinator: RbfaCoordinator,
        config: RbfaConfigEntry,
    ) -> None:
        """Initialize the RBFA Team entity."""
        super().__init__(coordinator)
        self.config = config
        team = config.data["team"]
        _LOGGER.debug("team: %r", team)
        self._attr_name = f"{DOMAIN} {team}"
        self._attr_unique_id = f"{DOMAIN}_calendar_{team}"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""

        alt_name = entry_option(self.config, "alt_name")
        team = self.coordinator.data.team
        if alt_name:
            self._attr_name = alt_name
        elif team is not None:
            self._attr_name = f"{team.club_name} | {team.name}"

        upcoming = self.coordinator.data.upcoming
        if upcoming is None:
            return None
        return CalendarEvent(
            uid=upcoming.id,
            summary=upcoming.summary,
            start=upcoming.starttime,
            end=upcoming.endtime,
            location=upcoming.location,
            description=upcoming.series,
        )

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return calendar events"""
        include_score = entry_option(self.config, "show_ranking", True)
        return [
            CalendarEvent(
                uid=match.id,
                summary=match.summary,
                start=match.starttime,
                end=match.endtime,
                location=match.location,
                description=match.description(include_score),
            )
            for match in self.coordinator.data.matches
            if start_date.date() <= match.starttime.date() <= end_date.date()
        ]
