"""Config flow for the RBFA integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import UnitOfTime
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN
from .helpers import entry_option


class RbfaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for RBFA."""

    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            team = user_input["team"]
            await self.async_set_unique_id(f"{team}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(title=f"{team}", data=user_input)

        schema = vol.Schema(
            {
                vol.Required("team"): str,
                vol.Optional("alt_name"): str,
                vol.Required("duration", default=105): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5,
                        max=120,
                        step=5,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement=UnitOfTime.MINUTES,
                    ),
                ),
                vol.Required("show_ranking", default=True): bool,
                vol.Required("show_referee", default=True): bool,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors={},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlowWithReload):
    """Handle RBFA options; the entry reloads automatically on save."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        alt_name = entry_option(self.config_entry, "alt_name", "")
        duration = entry_option(self.config_entry, "duration")
        show_ranking = entry_option(self.config_entry, "show_ranking", True)
        show_referee = entry_option(self.config_entry, "show_referee", True)

        # https://community.home-assistant.io/t/voluptuous-options-flow-validation-for-an-optional-string-how/305538/3
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "alt_name", description={"suggested_value": alt_name}
                    ): str,
                    vol.Required("duration", default=duration): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=5,
                            max=120,
                            step=5,
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement=UnitOfTime.MINUTES,
                        ),
                    ),
                    vol.Required("show_ranking", default=show_ranking): bool,
                    vol.Required("show_referee", default=show_referee): bool,
                }
            ),
        )
