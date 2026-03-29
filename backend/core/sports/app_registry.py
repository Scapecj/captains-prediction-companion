"""Event-type app registry.

Maps (league, market_type_hint) to the canonical app pipeline name.
The companion router uses this to dispatch incoming markets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

# ---------------------------------------------------------------------------
# App names (canonical identifiers used throughout the system)
# ---------------------------------------------------------------------------

APP_FOOTBALL_GAME = "football_game_app"
APP_BASKETBALL_GAME = "basketball_game_app"
APP_BASEBALL_GAME = "baseball_game_app"
APP_MLB_HOME_RUN_PROP = "mlb_home_run_prop_app"
APP_MLB_STRIKEOUT_PROP = "mlb_strikeout_prop_app"
APP_UFC_FIGHT = "ufc_fight_app"
APP_NASCAR_RACE = "nascar_race_app"
APP_NASCAR_SERIES_FUTURES = "nascar_series_futures_app"

ALL_APPS: tuple[str, ...] = (
    APP_FOOTBALL_GAME,
    APP_BASKETBALL_GAME,
    APP_BASEBALL_GAME,
    APP_MLB_HOME_RUN_PROP,
    APP_MLB_STRIKEOUT_PROP,
    APP_UFC_FIGHT,
    APP_NASCAR_RACE,
    APP_NASCAR_SERIES_FUTURES,
)

# ---------------------------------------------------------------------------
# Kalshi NASCAR series futures market IDs
# ---------------------------------------------------------------------------

KALSHI_NASCAR_SERIES_MARKETS: dict[str, dict[str, str | int]] = {
    "KXNASCARTRUCKSERIES-NTS26": {
        "league": "NASCAR_TRUCKS",
        "type": "series_championship",
        "season": 2026,
    },
    "KXNASCARCUPSERIES-NCS26": {
        "league": "NASCAR_CUP",
        "type": "series_championship",
        "season": 2026,
    },
    "KXNASCARAUTOPARTSSERIES-NAPS26": {
        "league": "NASCAR_OREILLY",
        "type": "series_championship",
        "season": 2026,
    },
}

# ---------------------------------------------------------------------------
# App descriptor
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AppSpec:
    """Static descriptor for an event-type alpha app."""

    app: str
    leagues: tuple[str, ...]
    market_types: tuple[str, ...]
    phases: tuple[str, ...]
    description: str
    prop_keywords: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

APP_REGISTRY: dict[str, AppSpec] = {
    APP_FOOTBALL_GAME: AppSpec(
        app=APP_FOOTBALL_GAME,
        leagues=("NFL", "NCAA_FB"),
        market_types=("moneyline", "spread", "total", "game"),
        phases=("pre_game", "live"),
        description="NFL and NCAA football game markets (sides, spreads, totals, live).",
    ),
    APP_BASKETBALL_GAME: AppSpec(
        app=APP_BASKETBALL_GAME,
        leagues=("NBA", "NCAA_BB"),
        market_types=("moneyline", "spread", "total", "game"),
        phases=("pre_game", "live"),
        description="NBA and NCAA men's basketball game markets.",
    ),
    APP_BASEBALL_GAME: AppSpec(
        app=APP_BASEBALL_GAME,
        leagues=("MLB", "NCAA_BASEBALL"),
        market_types=("moneyline", "total", "game"),
        phases=("pre_game",),
        description="MLB and NCAA baseball full-game sides and totals.",
    ),
    APP_MLB_HOME_RUN_PROP: AppSpec(
        app=APP_MLB_HOME_RUN_PROP,
        leagues=("MLB",),
        market_types=("player_prop", "prop"),
        phases=("pre_game",),
        prop_keywords=("home run", "hr", "home_run"),
        description="MLB batter home-run props. Requires confirmed lineup.",
    ),
    APP_MLB_STRIKEOUT_PROP: AppSpec(
        app=APP_MLB_STRIKEOUT_PROP,
        leagues=("MLB",),
        market_types=("player_prop", "prop"),
        phases=("pre_game",),
        prop_keywords=("strikeout", "strikeouts", "k prop", "pitcher k", "ks"),
        description="MLB pitcher strikeout props. Requires confirmed lineup context.",
    ),
    APP_UFC_FIGHT: AppSpec(
        app=APP_UFC_FIGHT,
        leagues=("UFC",),
        market_types=("moneyline", "method", "round", "fight"),
        phases=("pre_game", "live"),
        description="UFC fight markets: win, method of victory, live.",
    ),
    APP_NASCAR_RACE: AppSpec(
        app=APP_NASCAR_RACE,
        leagues=("NASCAR_CUP", "NASCAR_TRUCKS", "NASCAR_OREILLY"),
        market_types=("race_winner", "top3", "race"),
        phases=("pre_game", "live"),
        description="NASCAR race-level markets: Cup, Trucks, O'Reilly.",
    ),
    APP_NASCAR_SERIES_FUTURES: AppSpec(
        app=APP_NASCAR_SERIES_FUTURES,
        leagues=("NASCAR_CUP", "NASCAR_TRUCKS", "NASCAR_OREILLY"),
        market_types=("futures", "series_champion", "championship"),
        phases=("futures",),
        description="NASCAR season championship futures (long-horizon, not live).",
    ),
}

# Reverse lookup: league → apps that handle it
_LEAGUE_TO_APPS: dict[str, list[str]] = {}
for _app_name, _spec in APP_REGISTRY.items():
    for _league in _spec.leagues:
        _LEAGUE_TO_APPS.setdefault(_league, []).append(_app_name)


def get_apps_for_league(league: str) -> list[str]:
    """Return all app names that handle a given canonical league."""
    return list(_LEAGUE_TO_APPS.get(league, []))


def route_to_app(
    league: str,
    market_type: str | None,
    phase: str | None = None,
    *,
    title: str | None = None,
    market_subtype: str | None = None,
) -> str | None:
    """Return the best-matching app name for the given inputs, or None.

    Priority order:
    1. Prop keyword match (MLB HR and K props before generic baseball)
    2. Phase=futures → NASCAR series futures if applicable
    3. Exact market_type + league match
    4. League-only fallback (first registered app for the league)
    """
    canonical_league = league.strip().upper() if league else ""
    mt = (market_type or "").lower()
    ph = (phase or "pre_game").lower()
    text = ((title or "") + " " + (market_subtype or "")).lower()

    # 1. Prop keyword matching (MLB only)
    if canonical_league == "MLB":
        hr_spec = APP_REGISTRY[APP_MLB_HOME_RUN_PROP]
        if any(kw in text or kw in mt for kw in hr_spec.prop_keywords):
            return APP_MLB_HOME_RUN_PROP
        k_spec = APP_REGISTRY[APP_MLB_STRIKEOUT_PROP]
        if any(kw in text or kw in mt for kw in k_spec.prop_keywords):
            return APP_MLB_STRIKEOUT_PROP

    # 2. Futures phase → NASCAR series
    if ph == "futures" and canonical_league in ("NASCAR_CUP", "NASCAR_TRUCKS", "NASCAR_OREILLY"):
        return APP_NASCAR_SERIES_FUTURES

    # 3. Exact match on league + market_type
    for app_name, spec in APP_REGISTRY.items():
        if canonical_league not in spec.leagues:
            continue
        if mt and any(mt in m or m in mt for m in spec.market_types):
            if ph in spec.phases or not ph:
                return app_name

    # 4. League-only fallback
    apps = get_apps_for_league(canonical_league)
    # Prefer non-futures apps unless phase=futures
    for app_name in apps:
        spec = APP_REGISTRY[app_name]
        if ph != "futures" and "futures" in spec.phases and len(spec.phases) == 1:
            continue
        return app_name

    return None


def is_kalshi_nascar_futures(market_id: str) -> bool:
    """Return True if the market ID is a known Kalshi NASCAR series futures contract."""
    return market_id.upper() in {k.upper() for k in KALSHI_NASCAR_SERIES_MARKETS}


def get_kalshi_nascar_meta(market_id: str) -> dict[str, str | int] | None:
    """Return metadata for a Kalshi NASCAR series futures market, or None."""
    return KALSHI_NASCAR_SERIES_MARKETS.get(market_id.upper())
