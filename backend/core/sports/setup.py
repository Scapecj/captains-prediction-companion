"""
setup.py — wires all app runners into the CompanionRouter singleton.

Call `bootstrap_router()` once at server/process startup.
The router singleton is then ready to dispatch any market.

Usage:
    from backend.core.sports.setup import bootstrap_router
    router = bootstrap_router()
    output = router.dispatch(inp)
"""

from __future__ import annotations

from .companion_router import CompanionRouter, get_router
from .app_registry import (
    APP_FOOTBALL_GAME,
    APP_BASKETBALL_GAME,
    APP_BASEBALL_GAME,
    APP_MLB_HOME_RUN_PROP,
    APP_MLB_STRIKEOUT_PROP,
    APP_UFC_FIGHT,
    APP_NASCAR_RACE,
    APP_NASCAR_SERIES_FUTURES,
)
from .apps import (
    football_game_app,
    basketball_game_app,
    baseball_game_app,
    mlb_home_run_prop_app,
    mlb_strikeout_prop_app,
    ufc_fight_app,
    nascar_race_app,
    nascar_series_futures_app,
)

_BOOTSTRAPPED = False


def bootstrap_router(router: CompanionRouter | None = None) -> CompanionRouter:
    """
    Register all app runners with the companion router singleton.
    Safe to call multiple times — idempotent after first call.
    """
    global _BOOTSTRAPPED
    r = router or get_router()

    if _BOOTSTRAPPED and router is None:
        return r

    r.register(APP_FOOTBALL_GAME,       football_game_app.run)
    r.register(APP_BASKETBALL_GAME,     basketball_game_app.run)
    r.register(APP_BASEBALL_GAME,       baseball_game_app.run)
    r.register(APP_MLB_HOME_RUN_PROP,   mlb_home_run_prop_app.run)
    r.register(APP_MLB_STRIKEOUT_PROP,  mlb_strikeout_prop_app.run)
    r.register(APP_UFC_FIGHT,           ufc_fight_app.run)
    r.register(APP_NASCAR_RACE,         nascar_race_app.run)
    r.register(APP_NASCAR_SERIES_FUTURES, nascar_series_futures_app.run)

    _BOOTSTRAPPED = True
    return r
