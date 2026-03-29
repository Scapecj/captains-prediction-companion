"""Companion Router — dispatcher and normalizer for sports/event markets.

Architecture role:
  Companion router (this file)
    → Event-type app registry (app_registry.py)
    → Per-app alpha pipeline (apps/*.py)
    → Shared portfolio/review layer (ev, kelly, clv, logging)

The router DOES NOT do heavy modeling.
It classifies, normalizes, routes, and shuttles standardized I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.sports.app_registry import (
    APP_REGISTRY,
    route_to_app,
    is_kalshi_nascar_futures,
    get_kalshi_nascar_meta,
)
from core.sports.config import normalize_league_name


# ---------------------------------------------------------------------------
# Standardized I/O contracts
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class RouterInput:
    """Standardized input to the companion router.

    Accepts raw data from any source (Kalshi, Polymarket, direct link,
    market ID, title, tags) and normalizes it before dispatch.
    """

    source: str  # "kalshi" | "polymarket" | "manual"
    market_id: str | None = None
    url: str | None = None
    league: str | None = None
    event_type: str | None = None
    market_type: str | None = None
    market_subtype: str | None = None
    phase: str | None = None  # "pre_game" | "live" | "futures"
    title: str | None = None
    tags: tuple[str, ...] = ()
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RouterOutput:
    """Standardized output from a dispatched alpha app."""

    pipeline: str
    classification_confidence: float = 0.0
    fair_probability: float = 0.0
    market_probability: float = 0.0
    edge: float = 0.0
    expected_value: float = 0.0
    confidence: float = 0.0
    no_bet_flag: bool = False
    primary_signal: str = ""
    notes: list[str] = field(default_factory=list)
    # Extended fields surfaced by specific apps
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RouteResult:
    """Classification result before dispatching to an app."""

    app: str | None
    league: str | None
    market_type: str | None
    phase: str
    classification_confidence: float
    notes: list[str] = field(default_factory=list)
    kalshi_nascar_meta: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------


def _infer_phase(inp: RouterInput) -> str:
    """Infer the market phase from available signals."""
    if inp.phase:
        return inp.phase.lower()
    mt = (inp.market_type or "").lower()
    ms = (inp.market_subtype or "").lower()
    title = (inp.title or "").lower()
    if any(kw in mt or kw in ms or kw in title for kw in ("futures", "champion", "series", "season")):
        return "futures"
    if any(kw in mt or kw in ms or kw in title for kw in ("live", "in_play", "in-play", "inplay")):
        return "live"
    return "pre_game"


def _infer_market_type(inp: RouterInput) -> str | None:
    """Coerce market_type from subtype or title hints."""
    if inp.market_type:
        return inp.market_type.lower()
    ms = (inp.market_subtype or "").lower()
    title = (inp.title or "").lower()
    for kw in ("moneyline", "spread", "total", "prop", "futures", "race_winner", "top3", "method"):
        if kw in ms or kw in title:
            return kw
    return None


def _confidence_for_route(league: str | None, app: str | None, phase: str) -> float:
    """Heuristic confidence that the classification is correct."""
    if not league or not app:
        return 0.3
    spec = APP_REGISTRY.get(app)
    if spec and league in spec.leagues and phase in spec.phases:
        return 0.92
    if spec and league in spec.leagues:
        return 0.75
    return 0.5


# ---------------------------------------------------------------------------
# Companion Router
# ---------------------------------------------------------------------------


class CompanionRouter:
    """Accept market data, classify it, route to the correct alpha app.

    Usage::

        router = CompanionRouter()
        route = router.classify(inp)
        # Optionally dispatch if an app runner is registered:
        output = router.dispatch(inp)
    """

    def __init__(self) -> None:
        # App runners: app_name → callable(RouterInput) → RouterOutput
        self._runners: dict[str, Any] = {}

    def register(self, app: str, runner: Any) -> None:
        """Register a callable app runner for a given app name."""
        if app not in APP_REGISTRY:
            raise ValueError(f"Unknown app: {app!r}. Must be one of {list(APP_REGISTRY)}")
        self._runners[app] = runner

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def classify(self, inp: RouterInput) -> RouteResult:
        """Normalize and classify a market input into a route result."""
        # Normalize league
        raw_league = inp.league or (inp.raw_metadata or {}).get("league") or ""
        league = normalize_league_name(str(raw_league)) if raw_league else None

        # Kalshi NASCAR series futures shortcut
        if inp.market_id and is_kalshi_nascar_futures(inp.market_id):
            meta = get_kalshi_nascar_meta(inp.market_id)
            league = str(meta["league"]) if meta else league
            return RouteResult(
                app="nascar_series_futures_app",
                league=league,
                market_type="futures",
                phase="futures",
                classification_confidence=0.98,
                notes=["Matched Kalshi NASCAR series futures market ID"],
                kalshi_nascar_meta=meta,
            )

        phase = _infer_phase(inp)
        market_type = _infer_market_type(inp)

        app = route_to_app(
            league or "",
            market_type,
            phase,
            title=inp.title,
            market_subtype=inp.market_subtype,
        )

        confidence = _confidence_for_route(league, app, phase)
        notes: list[str] = []
        if not league:
            notes.append("league could not be determined from input")
        if not app:
            notes.append("no matching app found for this market")

        return RouteResult(
            app=app,
            league=league,
            market_type=market_type,
            phase=phase,
            classification_confidence=confidence,
            notes=notes,
        )

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(self, inp: RouterInput) -> RouterOutput:
        """Classify and dispatch to the registered app runner.

        If the app has no registered runner, returns a stub output with
        no_bet_flag=True and a note explaining the gap.
        """
        route = self.classify(inp)
        app = route.app

        if app is None:
            return RouterOutput(
                pipeline="unrouted",
                classification_confidence=route.classification_confidence,
                no_bet_flag=True,
                notes=["No app matched for this market"] + route.notes,
            )

        runner = self._runners.get(app)
        if runner is None:
            return RouterOutput(
                pipeline=app,
                classification_confidence=route.classification_confidence,
                no_bet_flag=True,
                notes=[f"App '{app}' has no registered runner yet"] + route.notes,
            )

        # Inject normalized context into metadata before handing off
        enriched = RouterInput(
            source=inp.source,
            market_id=inp.market_id,
            url=inp.url,
            league=route.league or inp.league,
            event_type=inp.event_type,
            market_type=route.market_type or inp.market_type,
            market_subtype=inp.market_subtype,
            phase=route.phase,
            title=inp.title,
            tags=inp.tags,
            raw_metadata={
                **inp.raw_metadata,
                "_route": {
                    "app": app,
                    "league": route.league,
                    "phase": route.phase,
                    "classification_confidence": route.classification_confidence,
                    "kalshi_nascar_meta": route.kalshi_nascar_meta,
                },
            },
        )

        result: RouterOutput = runner(enriched)
        # Stamp pipeline name for traceability
        result.pipeline = app
        result.classification_confidence = route.classification_confidence
        return result


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_router: CompanionRouter | None = None


def get_router() -> CompanionRouter:
    """Return the module-level singleton router (lazy init)."""
    global _router
    if _router is None:
        _router = CompanionRouter()
    return _router
