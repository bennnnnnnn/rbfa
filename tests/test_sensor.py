"""Tests for the RBFA sensors."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant, State
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rbfa.sensor import RbfaSensor


def _state(hass: HomeAssistant, entity_id: str) -> State:
    state = hass.states.get(entity_id)
    assert state is not None, f"{entity_id} has no state"
    return state


@pytest.fixture
def enable_sensors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sensors are disabled by default; enable them so they get a state."""
    monkeypatch.setattr(RbfaSensor, "_attr_entity_registry_enabled_default", True)


@pytest.mark.usefixtures("enable_sensors")
async def test_sensor_states_and_attributes(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_rbfa_api
) -> None:
    """Sensor states and attributes keep their existing format."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    home = _state(hass, "sensor.home_team")
    assert home.state == "Home FC"
    assert home.attributes["entity_picture"] == "https://logo/1.png"
    assert home.attributes["baseid"] == "123456"
    assert home.attributes["tag"] == "upcoming"
    assert home.attributes["id"] == "1"
    assert home.attributes["position"] == 2
    assert "goals" not in home.attributes  # upcoming match has no score yet

    series = _state(hass, "sensor.series")
    assert series.state == "Series 1"
    assert series.attributes["entity_picture"].endswith("/LogoVFV.svg")
    assert series.attributes["ranking"] == [
        {"position": 1, "team": "Away FC", "id": "2"},
        {"position": 2, "team": "Home FC", "id": "1"},
    ]

    assert _state(hass, "sensor.referee").state == "Jan Peeters"
    assert _state(hass, "sensor.match_id").state == "M2"
    assert _state(hass, "sensor.start_time").state == "2999-01-01T14:00:00+00:00"

    last_home = _state(hass, "sensor.home_team_2")
    assert last_home.attributes["tag"] == "lastmatch"
    assert last_home.attributes["goals"] == 2
