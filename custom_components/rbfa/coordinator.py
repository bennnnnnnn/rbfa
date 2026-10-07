"""Data update coordinator for the RBFA integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import RbfaApiError, RbfaClient
from .const import DOMAIN
from .models import RbfaData

_LOGGER = logging.getLogger(__name__)

type RbfaConfigEntry = ConfigEntry[RbfaCoordinator]


class RbfaCoordinator(DataUpdateCoordinator[RbfaData]):
    """Class to manage fetching RBFA data."""

    config_entry: RbfaConfigEntry

    def __init__(self, hass: HomeAssistant, entry: RbfaConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=15),
        )
        self.client = RbfaClient(hass, entry)

    async def _async_update_data(self) -> RbfaData:
        """Fetch data from the RBFA service."""
        try:
            return await self.client.update()
        except RbfaApiError as exc:
            raise UpdateFailed(str(exc)) from exc
