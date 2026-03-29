"""Football Game App — NFL and NCAA Football alpha pipeline.

Handles: sides / spreads / totals / game-state live pricing
Leagues: NFL, NCAA_FB

Input signals (pre-game):
  - EPA (expected points added) differentials
  - Offensive/defensive efficiency ratings
  - QB status and injury flags
  - Injury report (key skill positions)
  - Weather (wind speed, precipitation for outdoor venues)

Input signals (live):
  - Current score and clock
  - Possession and field position
  - Drive state and momentum indicators
  - Live win probability delta

Output fields (in addition to standard RouterOutput):
  - fair_spread
  - fair_total
  - injury_adjusted_edge
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.sports.companion_router import RouterInput, RouterOutput


@dataclass(slots=True)
class FootballGameContext:
    """Parsed context passed into the football model."""

    league: str
    event_id: str | None
    phase: str
    # Pre-game signals
    epa_differential: float | None = None
    efficiency_differential: float | None = None
    qb_status_home: str = "active"  # "active" | "questionable" | "out"
    qb_status_away: str = "active"
    injury_flag: bool = False
    weather_wind_mph: float | None = None
    weather_precipitation: bool = False
    # Live signals
    score_home: int | None = None
    score_away: int | None = None
    clock_seconds_remaining: int | None = None
    possession: str | None = None
    # Market
    market_probability: float = 0.5
    market_spread: float | None = None
    market_total: float | None = None


def _apply_weather_discount(fair_total: float | None, wind_mph: float | None, precip: bool) -> float | None:
    """Reduce expected total for high-wind or precipitation games."""
    if fair_total is None:
        return None
    discount = 0.0
    if wind_mph and wind_mph > 20:
        discount += min((wind_mph - 20) * 0.15, 3.0)
    if precip:
        discount += 1.5
    return fair_total - discount


def _qb_injury_edge_adjustment(qb_home: str, qb_away: str, base_edge: float) -> tuple[float, str]:
    """Widen or narrow edge based on QB availability."""
    note = ""
    adj = 0.0
    if qb_home == "out":
        adj -= 0.04
        note = "home QB out — fade home or reduce confidence"
    elif qb_home == "questionable":
        adj -= 0.015
        note = "home QB questionable"
    if qb_away == "out":
        adj += 0.04
        note += " | away QB out — lean home"
    elif qb_away == "questionable":
        adj += 0.015
    return base_edge + adj, note.strip()


def build_context(inp: RouterInput) -> FootballGameContext:
    """Extract a FootballGameContext from a RouterInput."""
    meta = inp.raw_metadata or {}
    return FootballGameContext(
        league=inp.league or "NFL",
        event_id=inp.market_id,
        phase=inp.phase or "pre_game",
        epa_differential=meta.get("epa_differential"),
        efficiency_differential=meta.get("efficiency_differential"),
        qb_status_home=meta.get("qb_status_home", "active"),
        qb_status_away=meta.get("qb_status_away", "active"),
        injury_flag=bool(meta.get("injury_flag", False)),
        weather_wind_mph=meta.get("weather_wind_mph"),
        weather_precipitation=bool(meta.get("weather_precipitation", False)),
        score_home=meta.get("score_home"),
        score_away=meta.get("score_away"),
        clock_seconds_remaining=meta.get("clock_seconds_remaining"),
        possession=meta.get("possession"),
        market_probability=float(meta.get("market_probability", 0.5)),
        market_spread=meta.get("market_spread"),
        market_total=meta.get("market_total"),
    )


def _price_pregame(ctx: FootballGameContext) -> dict[str, Any]:
    """Stub pre-game pricing model for football."""
    # Baseline: use efficiency differential to adjust from 50%
    base_prob = 0.5
    if ctx.epa_differential is not None:
        # 1 point of EPA differential ≈ 2pp probability shift (rough heuristic)
        base_prob = max(0.05, min(0.95, 0.5 + ctx.epa_differential * 0.02))

    # Spread: NFL average ~3 points per 10pp probability
    fair_spread = (base_prob - 0.5) * 30.0  # rough: ±15 pt spread range for 0-100%

    # Total: placeholder from market or league average
    fair_total = ctx.market_total if ctx.market_total else 44.5
    fair_total = _apply_weather_discount(fair_total, ctx.weather_wind_mph, ctx.weather_precipitation)

    edge = base_prob - ctx.market_probability
    inj_edge, inj_note = _qb_injury_edge_adjustment(ctx.qb_status_home, ctx.qb_status_away, edge)

    confidence = 0.60
    if ctx.injury_flag:
        confidence -= 0.10
    if ctx.epa_differential is None:
        confidence -= 0.10

    notes: list[str] = []
    if inj_note:
        notes.append(inj_note)
    if ctx.weather_wind_mph and ctx.weather_wind_mph > 20:
        notes.append(f"high wind ({ctx.weather_wind_mph} mph) — total discounted")
    if ctx.weather_precipitation:
        notes.append("precipitation — total discounted")

    return {
        "fair_probability": base_prob,
        "fair_spread": fair_spread,
        "fair_total": fair_total,
        "edge": inj_edge,
        "confidence": confidence,
        "injury_adjusted_edge": inj_edge,
        "notes": notes,
    }


def _price_live(ctx: FootballGameContext) -> dict[str, Any]:
    """Stub live-game pricing model for football."""
    # Without a full live model, use score state to adjust probability
    fair_probability = ctx.market_probability
    notes: list[str] = ["live pricing: using market probability as base (no full live model yet)"]

    if ctx.score_home is not None and ctx.score_away is not None and ctx.clock_seconds_remaining is not None:
        score_diff = ctx.score_home - ctx.score_away
        # Very rough: each TD differential shifts ~15pp, scaled by time remaining
        time_factor = ctx.clock_seconds_remaining / 3600.0  # fraction of game remaining
        prob_adj = (score_diff / 7.0) * 0.15 * (1 - time_factor)
        fair_probability = max(0.02, min(0.98, 0.5 + prob_adj))
        notes = [f"live: score diff={score_diff}, time_factor={time_factor:.2f}"]

    return {
        "fair_probability": fair_probability,
        "fair_spread": None,
        "fair_total": None,
        "edge": fair_probability - ctx.market_probability,
        "confidence": 0.55,
        "injury_adjusted_edge": fair_probability - ctx.market_probability,
        "notes": notes,
    }


def run(inp: RouterInput) -> RouterOutput:
    """Entry point for the football game alpha pipeline."""
    ctx = build_context(inp)
    pricing = _price_pregame(ctx) if ctx.phase == "pre_game" else _price_live(ctx)

    edge = pricing["edge"]
    fair_prob = pricing["fair_probability"]
    market_prob = ctx.market_probability
    ev = fair_prob * (1.0 / market_prob) - 1.0 if market_prob > 0 else 0.0

    no_bet = abs(edge) < 0.02 or pricing["confidence"] < 0.45

    return RouterOutput(
        pipeline="football_game_app",
        fair_probability=fair_prob,
        market_probability=market_prob,
        edge=edge,
        expected_value=ev,
        confidence=pricing["confidence"],
        no_bet_flag=no_bet,
        primary_signal=f"epa_diff={ctx.epa_differential}",
        notes=pricing["notes"],
        extra={
            "fair_spread": pricing["fair_spread"],
            "fair_total": pricing["fair_total"],
            "injury_adjusted_edge": pricing["injury_adjusted_edge"],
        },
    )
