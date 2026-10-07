"""Models for the RBFA integration.

The API models mirror the GraphQL JSON and are deserialized with mashumaro
(already installed with Home Assistant). A missing or invalid field raises a
mashumaro error (a LookupError/ValueError), which the API client turns into
RbfaApiError. ``Match`` and ``RbfaData`` combine those responses into what
the entities show.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated

from mashumaro import DataClassDictMixin
from mashumaro.types import Alias

# --- API models (GraphQL responses) ---------------------------------------


@dataclass(frozen=True, slots=True)
class Team(DataClassDictMixin):
    """The configured team (GetTeam)."""

    club_name: Annotated[str, Alias("clubName")]
    name: str


@dataclass(frozen=True, slots=True)
class TeamRef(DataClassDictMixin):
    id: str
    name: str
    logo: str | None = None


@dataclass(frozen=True, slots=True)
class SeriesRef(DataClassDictMixin):
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class Outcome(DataClassDictMixin):
    home_team_goals: Annotated[int | None, Alias("homeTeamGoals")] = None
    away_team_goals: Annotated[int | None, Alias("awayTeamGoals")] = None
    home_team_penalties: Annotated[int | None, Alias("homeTeamPenaltiesScored")] = None
    away_team_penalties: Annotated[int | None, Alias("awayTeamPenaltiesScored")] = None


@dataclass(frozen=True, slots=True)
class CalendarMatch(DataClassDictMixin):
    """One entry of the team calendar (GetTeamCalendar)."""

    id: str
    start_time: Annotated[datetime, Alias("startTime")]  # naive, Belgian local time
    channel: str
    state: str
    home_team: Annotated[TeamRef, Alias("homeTeam")]
    away_team: Annotated[TeamRef, Alias("awayTeam")]
    outcome: Outcome
    series: SeriesRef


@dataclass(frozen=True, slots=True)
class MatchLocation(DataClassDictMixin):
    address: str
    postal_code: Annotated[str, Alias("postalCode")]
    city: str


@dataclass(frozen=True, slots=True)
class Official(DataClassDictMixin):
    function: str
    first_name: Annotated[str, Alias("firstName")]
    last_name: Annotated[str, Alias("lastName")]


@dataclass(frozen=True, slots=True)
class MatchDetail(DataClassDictMixin):
    """Location and officials of a single match (GetMatchDetail)."""

    location: MatchLocation
    officials: list[Official] = field(default_factory=list)

    @property
    def address(self) -> str:
        loc = self.location
        return f"{loc.address}\n{loc.postal_code} {loc.city}\nBelgium"

    @property
    def referee(self) -> str | None:
        return next(
            (
                f"{o.first_name} {o.last_name}"
                for o in self.officials
                if o.function == "referee"
            ),
            None,
        )


@dataclass(frozen=True, slots=True)
class RankingTeam(DataClassDictMixin):
    position: int
    name: str
    team_id: Annotated[str, Alias("teamId")]


@dataclass(frozen=True, slots=True)
class Ranking(DataClassDictMixin):
    teams: list[RankingTeam]


@dataclass(frozen=True, slots=True)
class SeriesRankings(DataClassDictMixin):
    """Rankings of a series (GetSeriesRankings)."""

    rankings: list[Ranking]


# --- Integration models (what the entities read) --------------------------


@dataclass(frozen=True, slots=True)
class MatchTeam:
    """One side of a match, with its score and series position."""

    id: str
    name: str
    logo: str | None
    goals: int | None
    penalties: int | None
    position: int | None


@dataclass(slots=True)
class Match:
    """A calendar match, enriched with details and the series ranking."""

    calendar: CalendarMatch
    starttime: datetime
    endtime: datetime
    location: str | None = None
    referee: str | None = None
    ranking: list[RankingTeam] = field(default_factory=list)

    @property
    def id(self) -> str:
        return self.calendar.id

    @property
    def channel(self) -> str:
        return self.calendar.channel

    @property
    def series(self) -> str:
        return self.calendar.series.name

    @property
    def series_id(self) -> str:
        return self.calendar.series.id

    @property
    def home(self) -> MatchTeam:
        outcome = self.calendar.outcome
        return self._side(
            self.calendar.home_team,
            outcome.home_team_goals,
            outcome.home_team_penalties,
        )

    @property
    def away(self) -> MatchTeam:
        outcome = self.calendar.outcome
        return self._side(
            self.calendar.away_team,
            outcome.away_team_goals,
            outcome.away_team_penalties,
        )

    def _side(
        self, team: TeamRef, goals: int | None, penalties: int | None
    ) -> MatchTeam:
        position = next(
            (r.position for r in self.ranking if r.team_id == team.id), None
        )
        return MatchTeam(team.id, team.name, team.logo, goals, penalties, position)

    @property
    def summary(self) -> str:
        return f"{self.calendar.home_team.name} - {self.calendar.away_team.name}"

    def description(self, include_score: bool) -> str:
        description = f"{self.series} (state: {self.calendar.state})"
        if include_score:
            home, away = self.home, self.away
            result = "No match score"
            if home.goals is not None:
                result = f"Goals: {home.goals} - {away.goals}"
            if home.penalties is not None:
                result += f"; Penalties: {home.penalties} - {away.penalties}"
            description += "; " + result
        return description


@dataclass(slots=True)
class RbfaData:
    """Everything the coordinator exposes to the entities."""

    team: Team | None = None
    matches: list[Match] = field(default_factory=list)
    upcoming: Match | None = None
    lastmatch: Match | None = None
