"""Tests for RBFA setup, data parsing and unload."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.rbfa.const import API_URL


async def test_setup_and_unload(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_rbfa_api
) -> None:
    """The entry loads, exposes parsed data, and unloads cleanly."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    data = config_entry.runtime_data.data
    assert data.team is not None
    assert data.team.club_name == "Home FC"
    assert data.upcoming is not None
    assert data.lastmatch is not None
    assert data.upcoming.id == "M2"
    assert data.lastmatch.id == "M1"
    assert data.upcoming.referee == "Jan Peeters"
    assert data.upcoming.home.position == 2
    assert data.upcoming.away.position == 1
    assert len(data.matches) == 2
    assert "Goals: 2 - 0" in data.matches[0].description(include_score=True)

    assert hass.states.get("calendar.rbfa_123456") is not None

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retries_on_connection_error(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A network failure on first refresh puts the entry in setup-retry."""
    aioclient_mock.post(API_URL, exc=TimeoutError())
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_retries_on_unexpected_response(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_rbfa_api, aioclient_mock
) -> None:
    """A response that doesn't match the models puts the entry in setup-retry."""
    aioclient_mock.clear_requests()
    mock_rbfa_api(GetTeamCalendar={"teamCalendar": [{"id": "M1"}]})
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_no_calendar(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_rbfa_api, aioclient_mock
) -> None:
    """A team without a calendar loads with empty data instead of crashing."""
    aioclient_mock.clear_requests()
    mock_rbfa_api(GetTeamCalendar={"teamCalendar": None})
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    data = config_entry.runtime_data.data
    assert data.matches == []
    assert data.upcoming is None
    assert data.lastmatch is None
