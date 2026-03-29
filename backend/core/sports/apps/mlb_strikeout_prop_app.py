"""MLB Strikeout Prop App — pitcher strikeout props only.

REQUIRES sufficiently reliable or confirmed lineup context.

Input signals:
  - K/BF, K%, swinging-strike rate (SwStr%), CSW%
  - Expected batters faced (pitch count projection, leash)
  - Opponent lineup K tendencies (K%, whiff rate)
  - Handedness matchup effects
  - Moneyline and total context (proxy for game pace/script)

Output fields:
  - expected_strikeouts, fair_prob_over, fair_prob_under, market_prob,
    edge_k, confidence_k, primary_driver_k, notes
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from core.sports.companion_router import RouterInput, RouterOutput

_MIN_BF_SAMPLE = 80


@dataclass(slots=True)
class StrikeoutPropContext:
    pitcher_name: str | None
    lineup_confirmed: bool
    # Pitcher stuff rates
    k_per_bf: float | None = None        # K per batter faced
    k_pct: float | None = None           # K% (0-1)
    swstr_pct: float | None = None       # swinging strike rate (0-1)
    csw_pct: float | None = None         # called + swinging strikes / pitches (0-1)
    pitcher_bf_sample: int = 0
    # Workload
    expected_bf: float | None = None     # projected batters faced this start
    pitch_count_limit: int | None = None
    days_rest: int | None = None
    # Opponent lineup
    opponent_k_pct: float | None = None  # lineup K% (0-1)
    opponent_whiff_rate: float | None = None
    handedness_edge: float = 0.0         # positive = pitcher has platoon edge
    # Game script proxy
    moneyline_implied: float | None = None  # implied win prob for pitcher's team
    game_total: float | None = None
    # Market
    market_line: float = 5.5             # over/under line
    market_prob_over: float = 0.50


def build_context(inp: RouterInput) -> StrikeoutPropContext:
    meta = inp.raw_metadata or {}
    return StrikeoutPropContext(
        pitcher_name=meta.get("pitcher_name") or inp.title,
        lineup_confirmed=bool(meta.get("lineup_confirmed", False)),
        k_per_bf=meta.get("k_per_bf"),
        k_pct=meta.get("k_pct"),
        swstr_pct=meta.get("swstr_pct"),
        csw_pct=meta.get("csw_pct"),
        pitcher_bf_sample=int(meta.get("pitcher_bf_sample", 0)),
        expected_bf=meta.get("expected_bf"),
        pitch_count_limit=meta.get("pitch_count_limit"),
        days_rest=meta.get("days_rest"),
        opponent_k_pct=meta.get("opponent_k_pct"),
        opponent_whiff_rate=meta.get("opponent_whiff_rate"),
        handedness_edge=float(meta.get("handedness_edge", 0.0)),
        moneyline_implied=meta.get("moneyline_implied"),
        game_total=meta.get("game_total"),
        market_line=float(meta.get("market_line", 5.5)),
        market_prob_over=float(meta.get("market_prob_over", 0.50)),
    )


def _estimate_k_rate(ctx: StrikeoutPropContext) -> tuple[float, list[str]]:
    """Estimate pitcher K per BF for this start."""
    notes: list[str] = []

    # League average K/BF ≈ 0.225
    base_k_rate = 0.225

    if ctx.k_per_bf is not None and ctx.pitcher_bf_sample >= _MIN_BF_SAMPLE:
        base_k_rate = ctx.k_per_bf
        notes.append(f"k_per_bf={ctx.k_per_bf:.3f}")
    elif ctx.k_pct is not None and ctx.pitcher_bf_sample >= _MIN_BF_SAMPLE:
        base_k_rate = ctx.k_pct
        notes.append(f"k_pct={ctx.k_pct:.3f}")
    else:
        notes.append("using league-average K rate (small/no sample)")

    # SwStr% is a leading indicator — blend it in
    if ctx.swstr_pct is not None:
        # ≈ SwStr% * 2.4 ≈ K% (rough conversion)
        swstr_implied_k = ctx.swstr_pct * 2.4
        base_k_rate = (base_k_rate + swstr_implied_k) / 2
        notes.append(f"swstr_pct={ctx.swstr_pct:.3f}")

    if ctx.csw_pct is not None:
        # CSW%: strong leading indicator, ~0.6 correlation with K%
        csw_adj = (ctx.csw_pct - 0.29) * 0.5  # league avg CSW ~29%
        base_k_rate += csw_adj
        notes.append(f"csw_pct={ctx.csw_pct:.3f}")

    # Opponent K tendency
    if ctx.opponent_k_pct is not None:
        league_avg_opp_k = 0.225
        opp_adj = (ctx.opponent_k_pct - league_avg_opp_k) * 0.3
        base_k_rate += opp_adj
        if ctx.opponent_k_pct > 0.25:
            notes.append(f"strikeout-prone lineup (K%={ctx.opponent_k_pct:.2%})")
        elif ctx.opponent_k_pct < 0.20:
            notes.append(f"contact-heavy lineup (K%={ctx.opponent_k_pct:.2%})")

    # Handedness edge
    base_k_rate += ctx.handedness_edge * 0.01

    return max(0.05, min(0.45, base_k_rate)), notes


def _estimate_bf(ctx: StrikeoutPropContext) -> tuple[float, list[str]]:
    """Estimate batters faced for this start."""
    notes: list[str] = []

    if ctx.expected_bf is not None:
        notes.append(f"expected_bf={ctx.expected_bf:.1f}")
        return ctx.expected_bf, notes

    # Estimate from pitch count limit
    if ctx.pitch_count_limit:
        # Average ~3.8 pitches per PA → bf = pitches / 3.8
        est_bf = ctx.pitch_count_limit / 3.8
        notes.append(f"pitch_count_limit={ctx.pitch_count_limit} → estimated bf={est_bf:.1f}")
        return est_bf, notes

    # Default: league average QS uses ~20 BF (5-6 innings)
    if ctx.days_rest is not None and ctx.days_rest >= 4:
        return 22.0, ["default bf=22 (regular rest)"]
    return 18.0, ["default bf=18 (short rest)"]


def _poisson_over_prob(expected_k: float, line: float) -> tuple[float, float]:
    """Use Poisson approximation to price over/under K.

    Returns (prob_over, prob_under).
    """
    # P(X > line) where X ~ Poisson(lambda)
    # P(X <= floor(line)) via CDF
    k_floor = int(math.floor(line))
    prob_under_or_equal = 0.0
    for k in range(k_floor + 1):
        prob_under_or_equal += math.exp(-expected_k) * (expected_k ** k) / math.factorial(k)
    prob_over = 1.0 - prob_under_or_equal
    # If line is a half-integer, no push possible
    return max(0.01, min(0.99, prob_over)), max(0.01, min(0.99, 1 - prob_over))


def run(inp: RouterInput) -> RouterOutput:
    ctx = build_context(inp)

    if not ctx.lineup_confirmed:
        return RouterOutput(
            pipeline="mlb_strikeout_prop_app",
            no_bet_flag=True,
            notes=["lineup not confirmed — no strikeout prop recommendation"],
        )

    k_rate, k_notes = _estimate_k_rate(ctx)
    expected_bf, bf_notes = _estimate_bf(ctx)

    expected_strikeouts = k_rate * expected_bf

    fair_prob_over, fair_prob_under = _poisson_over_prob(expected_strikeouts, ctx.market_line)

    edge_k = fair_prob_over - ctx.market_prob_over
    ev = edge_k / ctx.market_prob_over if ctx.market_prob_over > 0 else 0.0

    confidence = 0.62
    if ctx.pitcher_bf_sample < _MIN_BF_SAMPLE:
        confidence -= 0.12
    if ctx.k_per_bf is None and ctx.k_pct is None:
        confidence -= 0.10
    if ctx.expected_bf is None:
        confidence -= 0.05

    no_bet = abs(edge_k) < 0.025 or confidence < 0.40

    primary_driver = (
        "swstr_pct" if ctx.swstr_pct else
        "k_per_bf" if ctx.k_per_bf else
        "csw_pct" if ctx.csw_pct else
        "market_base"
    )

    all_notes = k_notes + bf_notes

    return RouterOutput(
        pipeline="mlb_strikeout_prop_app",
        fair_probability=fair_prob_over,
        market_probability=ctx.market_prob_over,
        edge=edge_k,
        expected_value=ev,
        confidence=confidence,
        no_bet_flag=no_bet,
        primary_signal=primary_driver,
        notes=all_notes,
        extra={
            "expected_strikeouts": expected_strikeouts,
            "fair_prob_over": fair_prob_over,
            "fair_prob_under": fair_prob_under,
            "market_prob": ctx.market_prob_over,
            "edge_k": edge_k,
            "confidence_k": confidence,
            "primary_driver_k": primary_driver,
            "k_rate": k_rate,
            "expected_bf": expected_bf,
        },
    )
