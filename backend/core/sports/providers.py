"""Sports data provider matrix and adapter descriptors.

Cost-first default stack:
- Perplexity for research / discovery / source-finding
- The Odds API for market prices and consensus odds
- nflverse for NFL historical + schedule data
- MLB Stats API + Baseball Savant for MLB schedule/live/props

Everything else is intentionally not in the hot path until we have a cheap,
reliable structured source that justifies the added API surface.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from core.sports.config import canonicalize_league

DataKind = Literal[
    "research",
    "schedule",
    "historical",
    "live",
    "odds",
    "injury",
    "weather",
    "props",
    "futures",
]


@dataclass(frozen=True, slots=True)
class ProviderAdapterSpec:
    """Static descriptor for a sports data provider."""

    name: str
    provider_type: str
    data_kinds: tuple[DataKind, ...]
    leagues: tuple[str, ...]
    auth_env_vars: tuple[str, ...] = ()
    notes: str = ""
    url: str | None = None
    supports_live: bool = False
    supports_historical: bool = False
    supports_props: bool = False
    supports_schedule: bool = False
    supports_odds: bool = False

    def is_configured(self) -> bool:
        return all(os.getenv(var) for var in self.auth_env_vars)


PROVIDER_ADAPTERS: dict[str, ProviderAdapterSpec] = {
    "Perplexity": ProviderAdapterSpec(
        name="Perplexity",
        provider_type="research",
        data_kinds=("research",),
        leagues=("NFL", "NCAA_FB", "NCAA_BB", "NBA", "MLB", "NCAA_BASEBALL", "UFC", "NASCAR_TRUCKS", "NASCAR_OREILLY", "NASCAR_CUP"),
        auth_env_vars=("PERPLEXITY_API_KEY",),
        notes="Perplexity-first research and source discovery layer for news, injuries, weather, and official source mapping.",
        url="https://docs.perplexity.ai/",
    ),
    "Playwright Scraper Skill": ProviderAdapterSpec(
        name="Playwright Scraper Skill",
        provider_type="research_scraper",
        data_kinds=("research",),
        leagues=("NFL", "NCAA_FB", "NCAA_BB", "NBA", "MLB", "NCAA_BASEBALL", "UFC", "NASCAR_TRUCKS", "NASCAR_OREILLY", "NASCAR_CUP"),
        notes="Built-in scraper skill for public pages, official docs, schedules, injury reports, and source discovery when a paid API is unnecessary.",
        url="https://playwright.dev/",
    ),
    "The Odds API": ProviderAdapterSpec(
        name="The Odds API",
        provider_type="odds_aggregator",
        data_kinds=("odds",),
        leagues=(
            "NFL",
            "NCAA_FB",
            "NCAA_BB",
            "NBA",
            "MLB",
            "NCAA_BASEBALL",
            "UFC",
            "NASCAR_TRUCKS",
            "NASCAR_OREILLY",
            "NASCAR_CUP",
        ),
        auth_env_vars=("THE_ODDS_API_KEY",),
        notes="Fast consensus odds layer for market-implied probabilities and book comparison.",
        url="https://the-odds-api.com/liveapi/guides/v4/",
        supports_odds=True,
    ),
    "nflverse": ProviderAdapterSpec(
        name="nflverse",
        provider_type="historical_public",
        data_kinds=("schedule", "historical"),
        leagues=("NFL",),
        notes="Best public historical NFL backbone for play-by-play, rosters, and season simulations.",
        url="https://nflverse.nflverse.com/",
        supports_historical=True,
        supports_schedule=True,
    ),
    "MLB Stats API": ProviderAdapterSpec(
        name="MLB Stats API",
        provider_type="official_public",
        data_kinds=("schedule", "historical", "live", "props", "injury"),
        leagues=("MLB", "NCAA_BASEBALL"),
        notes="Public MLB game state, schedules, box scores, and event feeds. Undocumented but widely used.",
        supports_live=True,
        supports_historical=True,
        supports_schedule=True,
        supports_props=True,
        supports_odds=False,
    ),
    "Baseball Savant": ProviderAdapterSpec(
        name="Baseball Savant",
        provider_type="official_public",
        data_kinds=("historical", "live", "props"),
        leagues=("MLB", "NCAA_BASEBALL"),
        notes="Statcast search and pitch-level / batted-ball data for MLB prop modeling.",
        url="https://baseballsavant.mlb.com/statcast_search",
        supports_live=True,
        supports_historical=True,
        supports_props=True,
    ),
}


SPORTS_PROVIDER_MATRIX: dict[str, dict[DataKind, tuple[str, ...]]] = {
    "NFL": {
        "research": ("Perplexity", "Playwright Scraper Skill"),
        "schedule": ("nflverse",),
        "historical": ("nflverse",),
        "live": (),
        "odds": ("The Odds API",),
        "injury": ("Perplexity",),
        "weather": ("Perplexity",),
        "props": ("The Odds API",),
        "futures": ("The Odds API",),
    },
    "NCAA_FB": {
        "research": ("Perplexity", "Playwright Scraper Skill"),
        "schedule": (),
        "historical": (),
        "live": (),
        "odds": ("The Odds API",),
        "injury": ("Perplexity",),
        "weather": ("Perplexity",),
        "props": ("The Odds API",),
        "futures": ("The Odds API",),
    },
    "NCAA_BB": {
        "research": ("Perplexity", "Playwright Scraper Skill"),
        "schedule": (),
        "historical": (),
        "live": (),
        "odds": ("The Odds API",),
        "injury": ("Perplexity",),
        "weather": ("Perplexity",),
        "props": ("The Odds API",),
        "futures": ("The Odds API",),
    },
    "NBA": {
        "research": ("Perplexity", "Playwright Scraper Skill"),
        "schedule": (),
        "historical": (),
        "live": (),
        "odds": ("The Odds API",),
        "injury": ("Perplexity",),
        "weather": ("Perplexity",),
        "props": ("The Odds API",),
        "futures": ("The Odds API",),
    },
    "MLB": {
        "research": ("Perplexity", "Playwright Scraper Skill"),
        "schedule": ("MLB Stats API",),
        "historical": ("Baseball Savant", "MLB Stats API"),
        "live": ("MLB Stats API",),
        "odds": ("The Odds API",),
        "injury": ("Perplexity",),
        "weather": ("Perplexity",),
        "props": ("Baseball Savant", "MLB Stats API", "The Odds API"),
        "futures": ("The Odds API",),
    },
    "NCAA_BASEBALL": {
        "research": ("Perplexity", "Playwright Scraper Skill"),
        "schedule": (),
        "historical": (),
        "live": (),
        "odds": ("The Odds API",),
        "injury": ("Perplexity",),
        "weather": ("Perplexity",),
        "props": ("The Odds API",),
        "futures": ("The Odds API",),
    },
    "UFC": {
        "research": ("Perplexity", "Playwright Scraper Skill"),
        "schedule": (),
        "historical": (),
        "live": (),
        "odds": ("The Odds API",),
        "injury": ("Perplexity",),
        "weather": (),
        "props": ("The Odds API",),
        "futures": ("The Odds API",),
    },
    "NASCAR_TRUCKS": {
        "research": ("Perplexity", "Playwright Scraper Skill"),
        "schedule": (),
        "historical": (),
        "live": (),
        "odds": ("The Odds API",),
        "injury": (),
        "weather": ("Perplexity",),
        "props": ("The Odds API",),
        "futures": ("The Odds API",),
    },
    "NASCAR_OREILLY": {
        "research": ("Perplexity", "Playwright Scraper Skill"),
        "schedule": (),
        "historical": (),
        "live": (),
        "odds": ("The Odds API",),
        "injury": (),
        "weather": ("Perplexity",),
        "props": ("The Odds API",),
        "futures": ("The Odds API",),
    },
    "NASCAR_CUP": {
        "research": ("Perplexity", "Playwright Scraper Skill"),
        "schedule": (),
        "historical": (),
        "live": (),
        "odds": ("The Odds API",),
        "injury": (),
        "weather": ("Perplexity",),
        "props": ("The Odds API",),
        "futures": ("The Odds API",),
    },
}


SPORTS_PROP_FALLBACKS: dict[str, tuple[str, ...]] = {
    "mlb_home_run_prop": ("Baseball Savant", "MLB Stats API", "Playwright Scraper Skill", "The Odds API"),
    "mlb_pitcher_strikeout_prop": ("MLB Stats API", "Baseball Savant", "Playwright Scraper Skill", "The Odds API"),
}

SPORTS_FALLBACK_ORDER: dict[str, dict[str, tuple[str, ...]]] = {
    league: {
        **matrix,
        "research": ("Perplexity", "Playwright Scraper Skill"),
        "mlb_home_run_prop": SPORTS_PROP_FALLBACKS["mlb_home_run_prop"],
        "mlb_pitcher_strikeout_prop": SPORTS_PROP_FALLBACKS["mlb_pitcher_strikeout_prop"],
    }
    for league, matrix in SPORTS_PROVIDER_MATRIX.items()
}


def get_provider_stack(
    league: str,
    data_kind: DataKind,
    *,
    market_subtype: str | None = None,
) -> tuple[str, ...]:
    """Return the ordered provider stack for a league/data kind."""
    canonical = canonicalize_league(league)
    if canonical is None:
        raise ValueError("league is required")

    if market_subtype and market_subtype in SPORTS_PROP_FALLBACKS:
        return SPORTS_PROP_FALLBACKS[market_subtype]

    league_matrix = SPORTS_PROVIDER_MATRIX.get(canonical)
    if not league_matrix:
        raise KeyError(f"Unsupported league: {canonical}")

    stack = league_matrix.get(data_kind)
    if stack is None:
        raise KeyError(f"Unsupported data kind '{data_kind}' for league {canonical}")
    return stack


def get_research_stack(league: str) -> tuple[str, ...]:
    """Return the research-first provider stack for a league."""
    return get_provider_stack(league, "research")


def build_provider_rows() -> list[dict[str, object]]:
    """Return a flattened provider matrix for docs and UI debugging."""
    rows: list[dict[str, object]] = []
    for league, matrix in SPORTS_PROVIDER_MATRIX.items():
        for kind, stack in matrix.items():
            rows.append(
                {
                    "league": league,
                    "data_kind": kind,
                    "providers": stack,
                }
            )
    return rows
