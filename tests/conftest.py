"""Fixtures for RBFA tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)

from custom_components.rbfa.const import API_URL, DOMAIN

TEAM_ID = "123456"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading the integration from custom_components."""


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a config entry for a team."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEAM_ID,
        title=TEAM_ID,
        data={
            "team": TEAM_ID,
            "duration": 105,
            "show_ranking": True,
            "show_referee": True,
        },
    )


def _match(match_id: str, start: str, home_goals: int | None) -> dict[str, Any]:
    return {
        "id": match_id,
        "startTime": start,
        "channel": "vfv",
        "state": "planned" if home_goals is None else "finished",
        "homeTeam": {"id": "1", "name": "Home FC", "logo": "https://logo/1.png"},
        "awayTeam": {"id": "2", "name": "Away FC", "logo": "https://logo/2.png"},
        "outcome": {
            "homeTeamGoals": home_goals,
            "awayTeamGoals": None if home_goals is None else 0,
            "homeTeamPenaltiesScored": None,
            "awayTeamPenaltiesScored": None,
        },
        "series": {"id": "S1", "name": "Series 1"},
    }


RESPONSES: dict[str, dict[str, Any]] = {
    "GetTeam": {"team": {"clubName": "Home FC", "name": "U13"}},
    "GetTeamCalendar": {
        "teamCalendar": [
            _match("M1", "2000-01-01T15:00:00", 2),
            _match("M2", "2999-01-01T15:00:00", None),
        ]
    },
    "GetMatchDetail": {
        "matchDetail": {
            "location": {
                "address": "Street 1",
                "postalCode": "1000",
                "city": "Brussels",
            },
            "officials": [
                {"function": "referee", "firstName": "Jan", "lastName": "Peeters"}
            ],
        }
    },
    "GetSeriesRankings": {
        "seriesRankings": {
            "rankings": [
                {
                    "teams": [
                        {"position": 1, "name": "Away FC", "teamId": "2"},
                        {"position": 2, "name": "Home FC", "teamId": "1"},
                    ]
                }
            ]
        }
    },
}


@pytest.fixture
def mock_rbfa_api(aioclient_mock: AiohttpClientMocker) -> Callable[..., None]:
    """Mock the RBFA GraphQL endpoint, answering per operationName."""

    def _setup(**overrides: dict[str, Any] | None) -> None:
        responses = {**RESPONSES, **overrides}

        async def _side_effect(method, url, data):
            return AiohttpClientMockResponse(
                method, url, json={"data": responses[data["operationName"]]}
            )

        aioclient_mock.post(API_URL, side_effect=_side_effect)

    _setup()
    return _setup
