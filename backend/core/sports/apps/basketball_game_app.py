"""Basketball Game App — NBA and NCAA Men's Basketball alpha pipeline.

Handles: sides / spreads / totals / live pricing
Leagues: NBA, NCAA_BB

Input signals (pre-game):
  - Pace (possessions per 40 min)
  - Offensive/defensive efficiency (ORtg, DRtg)
  - Rest days differential
  - Back-to-back flag
  - Travel distance/timezone differential
  - Lineup availability (key rotations)

Input signals (live):
  - Current score and foul trouble state
  - Possession pace vs expected
  - Live volatility flag

Output fields:
  - fair_prob, fair_total, confidence, volatility_flag, notes
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.sports.companion_router import RouterInput, RouterOutput


@dataclass(slots=True)
class BasketballGameContext:
    league: str
    event_id: str | None
    phase: str
    # Pre-game signals
    pace_home: float | None = None
    pace_away: float | None = None
    ortg_differential: float | None = None  # home - away net rating
    drtg_differential: float | None = None
    rest_days_home: int | None = None
    rest_days_away: int | None = None
    back_to_back_home: bool = False
    back_to_back_away: bool = False
    lineup_flag: bool = False  # True if key players are missing
    # Live signals
    score_home: int | None = None
    score_away: int | None = None
    foul_trouble_home: bool = False
    foul_trouble_away: bool = False
    # Market
    market_probability: float = 0.5
    market_total: float | None = None


def build_context(inp: RouterInput) -> BasketballGameContext:
    meta = inp.raw_metadata or {}
    return BasketballGameContext(
        league=inp.league or "NBA",
        event_id=inp.market_id,
        phase=inp.phase or "pre_game",
        pace_home=meta.get("pace_home"),
        pace_away=meta.get("pace_away"),
        ortg_differential=meta.get("ortg_differential"),
        drtg_differential=meta.get("drtg_differential"),
        rest_days_home=meta.get("rest_days_home"),
        rest_days_away=meta.get("rest_days_away"),
        back_to_back_home=bool(meta.get("back_to_back_home", False)),
        back_to_back_away=bool(meta.get("back_to_back_away", False)),
        lineup_flag=bool(meta.get("lineup_flag", False)),
        score_home=meta.get("score_home"),
        score_away=meta.get("score_away"),
        foul_trouble_home=bool(meta.get("foul_trouble_home", False)),
        foul_trouble_away=bool(meta.get("foul_trouble_away", False)),
        market_probability=float(meta.get("market_probability", 0.5)),
        market_total=meta.get("market_total"),
    )


def _rest_adjustment(rest_home: int | None, rest_away: int | None, b2b_home: bool, b2b_away: bool) -> float:
    """Return probability adjustment for rest/travel asymmetry."""
    adj = 0.0
    if b2b_home and not b2b_away:
        adj -= 0.03
    elif b2b_away and not b2b_home:
        adj += 0.03
    if rest_home is not None and rest_away is not None:
        diff = rest_home - rest_away
        adj += diff * 0.008  # ~0.8pp per extra rest day
    return adj


def _price_pregame(ctx: BasketballGameContext) -> dict[str, Any]:
    base_prob = 0.5
    if ctx.ortg_differential is not None:
        # ~1pp per net-rating point differential (rough)
        base_prob = max(0.05, min(0.95, 0.5 + ctx.ortg_differential * 0.01))

    base_prob += _rest_adjustment(ctx.rest_days_home, ctx.rest_days_away, ctx.back_to_back_home, ctx.back_to_back_away)
    base_prob = max(0.05, min(0.95, base_prob))

    # Total: average pace drives expected points
    avg_pace = None
    if ctx.pace_home is not None and ctx.pace_away is not None:
        avg_pace = (ctx.pace_home + ctx.pace_away) / 2.0
    fair_total = ctx.market_total or (avg_pace * 2.2 if avg_pace else 220.0)  # rough possessions × pts/poss

    edge = base_prob - ctx.market_probability
    confidence = 0.62
    if ctx.lineup_flag:
        confidence -= 0.12
    if ctx.ortg_differential is None:
        confidence -= 0.08

    notes: list[str] = []
    if ctx.back_to_back_home:
        notes.append("home team on back-to-back")
    if ctx.back_to_back_away:
        notes.append("away team on back-to-back")
    if ctx.lineup_flag:
        notes.append("key lineup absence flagged — confidence reduced")

    return {
        "fair_probability": base_prob,
        "fair_total": fair_total,
        "edge": edge,
        "confidence": confidence,
        "volatility_flag": ctx.lineup_flag or ctx.foul_trouble_home or ctx.foul_trouble_away,
        "notes": notes,
    }


def _price_live(ctx: BasketballGameContext) -> dict[str, Any]:
    fair_probability = ctx.market_probability
    notes: list[str] = ["live: using market probability as base"]

    if ctx.score_home is not None and ctx.score_away is not None:
        diff = ctx.score_home - ctx.score_away
        fair_probability = max(0.02, min(0.98, 0.5 + diff * 0.015))
        notes = [f"live score diff={diff}"]

    volatility_flag = ctx.foul_trouble_home or ctx.foul_trouble_away
    if volatility_flag:
        notes.append("foul trouble detected — high volatility")

    return {
        "fair_probability": fair_probability,
        "fair_total": ctx.market_total,
        "edge": fair_probability - ctx.market_probability,
        "confidence": 0.52,
        "volatility_flag": volatility_flag,
        "notes": notes,
    }


def run(inp: RouterInput) -> RouterOutput:
    ctx = build_context(inp)
    pricing = _price_pregame(ctx) if ctx.phase == "pre_game" else _price_live(ctx)

    edge = pricing["edge"]
    fair_prob = pricing["fair_probability"]
    market_prob = ctx.market_probability
    ev = fair_prob * (1.0 / market_prob) - 1.0 if market_prob > 0 else 0.0
    no_bet = abs(edge) < 0.02 or pricing["confidence"] < 0.45

    return RouterOutput(
        pipeline="basketball_game_app",
        fair_probability=fair_prob,
        market_probability=market_prob,
        edge=edge,
        expected_value=ev,
        confidence=pricing["confidence"],
        no_bet_flag=no_bet,
        primary_signal=f"ortg_diff={ctx.ortg_differential}",
        notes=pricing["notes"],
        extra={
            "fair_total": pricing["fair_total"],
            "volatility_flag": pricing["volatility_flag"],
        },
    )
