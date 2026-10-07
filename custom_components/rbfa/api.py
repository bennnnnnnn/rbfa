"""Client for the RBFA GraphQL API."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import API_URL, HASHES, REQUEST_TIMEOUT, REQUIRED, TZ, VARIABLES
from .helpers import entry_option
from .models import (
    CalendarMatch,
    Match,
    MatchDetail,
    RbfaData,
    SeriesRankings,
    Team,
)

_LOGGER = logging.getLogger(__name__)

# mashumaro's MissingField/InvalidFieldValue subclass LookupError/ValueError.
PARSE_ERRORS = (LookupError, TypeError, ValueError)


class RbfaApiError(Exception):
    """Raised when the RBFA API cannot be reached or returns an invalid response."""


def _parse[T](operation: str, parser: Callable[[Any], T], raw: Any) -> T:
    """Run a model parser, turning schema mismatches into RbfaApiError."""
    try:
        return parser(raw)
    except PARSE_ERRORS as exc:
        raise RbfaApiError(f"Unexpected {operation} response: {exc!r}") from exc


class RbfaClient:
    """Fetch team, calendar, match and ranking data for one team."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._session = async_get_clientsession(hass)
        self.entry = entry
        self.team = entry.data["team"]

    async def _query(self, operation: str, value: str) -> Any:
        """Run a persisted GraphQL query and return its result field.

        Raises RbfaApiError on network/HTTP errors; returns None when the
        query succeeds but yields no results.
        """
        payload = {
            "operationName": operation,
            "variables": {VARIABLES[operation]: value, "language": "nl"},
            "extensions": {
                "persistedQuery": {"version": 1, "sha256Hash": HASHES[operation]}
            },
        }
        try:
            async with self._session.post(
                API_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as response:
                response.raise_for_status()
                rj = await response.json()
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise RbfaApiError(f"Error fetching {operation}: {exc!r}") from exc

        if rj.get("data") is None:
            _LOGGER.debug("Error for operation %s: %s", operation, rj.get("errors"))
            return None
        result = rj["data"].get(REQUIRED[operation])
        if result is None:
            _LOGGER.debug("No results for operation %s", operation)
        return result

    async def update(self) -> RbfaData:
        """Fetch all data for the configured team."""
        _LOGGER.debug("Updating match details using GraphQL API")

        duration = entry_option(self.entry, "duration")
        show_ranking = entry_option(self.entry, "show_ranking", True)
        show_referee = entry_option(self.entry, "show_referee", True)
        _LOGGER.debug("duration: %r, show ranking: %r", duration, show_ranking)

        data = RbfaData()

        raw = await self._query("GetTeam", self.team)
        if raw is not None:
            data.team = _parse("GetTeam", Team.from_dict, raw)

        raw = await self._query("GetTeamCalendar", self.team)
        if raw is None:
            return data
        calendar = _parse(
            "GetTeamCalendar", lambda r: [CalendarMatch.from_dict(m) for m in r], raw
        )

        for entry in calendar:
            starttime = entry.start_time.replace(tzinfo=ZoneInfo(TZ))
            match = Match(
                calendar=entry,
                starttime=starttime,
                endtime=starttime + timedelta(minutes=duration),
            )
            raw = await self._query("GetMatchDetail", match.id)
            if raw is not None:
                detail = _parse("GetMatchDetail", MatchDetail.from_dict, raw)
                match.location = detail.address
                if show_referee:
                    match.referee = detail.referee
            data.matches.append(match)

        now = dt_util.utcnow()
        previous = None
        for match in data.matches:
            if match.endtime >= now:
                data.upcoming = match
                break
            previous = match
        data.lastmatch = previous

        if show_ranking:
            for match in (data.upcoming, data.lastmatch):
                if match is not None:
                    await self._add_ranking(match)

        return data

    async def _add_ranking(self, match: Match) -> None:
        """Add the series ranking (and so team positions) to a match."""
        try:
            raw = await self._query("GetSeriesRankings", match.series_id)
            if raw is None:
                return
            match.ranking = _parse(
                "GetSeriesRankings",
                lambda r: SeriesRankings.from_dict(r).rankings[0].teams,
                raw,
            )
        except RbfaApiError as exc:
            _LOGGER.warning("Could not fetch ranking: %s", exc)
