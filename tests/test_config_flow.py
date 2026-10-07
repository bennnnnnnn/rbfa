"""Tests for the RBFA config and options flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rbfa.const import DOMAIN

from .conftest import TEAM_ID


async def test_user_flow(hass: HomeAssistant, mock_rbfa_api) -> None:
    """A team can be added through the UI."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"team": TEAM_ID, "duration": 90, "show_ranking": True, "show_referee": False},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEAM_ID
    assert result["data"]["duration"] == 90


async def test_duplicate_team_aborts(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Adding the same team twice aborts."""
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"team": TEAM_ID, "duration": 90, "show_ranking": True, "show_referee": True},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_rbfa_api
) -> None:
    """Options are saved and the entry reloads."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "alt_name": "My team",
            "duration": 60,
            "show_ranking": False,
            "show_referee": True,
        },
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options["duration"] == 60
    upcoming = config_entry.runtime_data.data.upcoming
    assert upcoming is not None
    assert upcoming.ranking == []
