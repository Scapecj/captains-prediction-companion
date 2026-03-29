"""Season-aware sports calendar router."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from core.sports.config import (
    DEFAULT_PREFERRED_SPORTS,
    DEFAULT_SPORTS_CONFIG,
    SportsConfig,
    normalize_league_name,
)
from core.sports.models import SportEvent, SportsCalendarRoute


def _coerce_event(item: SportEvent | Mapping[str, Any]) -> SportEvent:
    if isinstance(item, SportEvent):
        league = normalize_league_name(item.league) or item.league
        return SportEvent(
            league=league,
            event_id=item.event_id,
            title=item.title,
            start_time=item.start_time,
            metadata=dict(item.metadata),
        )

    league = normalize_league_name(str(item.get("league") or item.get("sport") or ""))
    event_id = str(
        item.get("event_id") or item.get("id") or item.get("market_id") or ""
    )
    if not league or not event_id:
        raise ValueError("Each sports event must include a league and event_id")
    return SportEvent(
        league=league,
        event_id=event_id,
        title=item.get("title") or item.get("name"),
        metadata={
            k: v
            for k, v in item.items()
            if k
            not in {"league", "sport", "event_id", "id", "market_id", "title", "name"}
        },
    )


def sports_calendar_router(
    schedule_fetcher: Callable[[int], Iterable[SportEvent | Mapping[str, Any]]],
    *,
    config: SportsConfig = DEFAULT_SPORTS_CONFIG,
    preferred_sports: Iterable[str] | None = None,
) -> SportsCalendarRoute:
    """Return active sports in preference order, bounded by config."""
    if schedule_fetcher is None:
        raise ValueError("schedule_fetcher is required")

    date_range_days = config.routing.date_range_days
    raw_games = [_coerce_event(item) for item in schedule_fetcher(date_range_days)]

    counts = Counter(game.league for game in raw_games if game.league)
    preferred = tuple(
        preferred_sports or config.routing.preferred_sports or DEFAULT_PREFERRED_SPORTS
    )

    active_sports = [
        league
        for league in preferred
        if counts.get(league, 0) >= config.routing.min_games_per_league
    ][: config.routing.max_active_sports]

    fallback_used = False
    if not active_sports:
        active_sports = list(config.pre_game.default_leagues_if_none)
        fallback_used = True

    return SportsCalendarRoute(
        active_sports=tuple(active_sports),
        counts_by_league=dict(counts),
        games=tuple(raw_games),
        fallback_used=fallback_used,
    )
