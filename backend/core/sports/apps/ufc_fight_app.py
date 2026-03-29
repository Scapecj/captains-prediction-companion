"""UFC Fight App — UFC fight markets and matchup pricing.

Handles: moneyline, method of victory, live fight markets
League: UFC

Input signals (pre-fight):
  - Striking volume and accuracy differentials
  - Striking defense differentials
  - Takedown/grappling efficiency and defense
  - Contextual form (finish rate, recent results, weight class)
  - Style matchup tags

Input signals (live):
  - Round state and time remaining
  - Knockdowns
  - Control time and grappling volume
  - Observed striking vs grappling balance vs pre-fight expectation

Output fields:
  - fair_prob, confidence, style_note, uncertainty_discount
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.sports.companion_router import RouterInput, RouterOutput


@dataclass(slots=True)
class UFCFightContext:
    fighter_a: str | None
    fighter_b: str | None
    phase: str
    # Pre-fight striking
    slpm_a: float | None = None   # significant strikes landed per minute
    slpm_b: float | None = None
    str_acc_a: float | None = None  # striking accuracy
    str_acc_b: float | None = None
    str_def_a: float | None = None  # striking defense
    str_def_b: float | None = None
    # Grappling
    td_avg_a: float | None = None   # takedowns per 15 min
    td_avg_b: float | None = None
    td_acc_a: float | None = None
    td_def_a: float | None = None   # takedown defense
    td_def_b: float | None = None
    # Context
    finish_rate_a: float | None = None  # fraction of wins by finish
    finish_rate_b: float | None = None
    reach_adv: float | None = None      # A reach - B reach in inches
    style_a: str | None = None          # "striker" | "wrestler" | "grappler" | "all-around"
    style_b: str | None = None
    # Live signals
    round_number: int | None = None
    knockdowns_a: int = 0
    knockdowns_b: int = 0
    control_time_a: float | None = None  # seconds
    control_time_b: float | None = None
    # Market
    market_probability: float = 0.5     # prob fighter A wins


def build_context(inp: RouterInput) -> UFCFightContext:
    meta = inp.raw_metadata or {}
    return UFCFightContext(
        fighter_a=meta.get("fighter_a") or inp.title,
        fighter_b=meta.get("fighter_b"),
        phase=inp.phase or "pre_game",
        slpm_a=meta.get("slpm_a"),
        slpm_b=meta.get("slpm_b"),
        str_acc_a=meta.get("str_acc_a"),
        str_acc_b=meta.get("str_acc_b"),
        str_def_a=meta.get("str_def_a"),
        str_def_b=meta.get("str_def_b"),
        td_avg_a=meta.get("td_avg_a"),
        td_avg_b=meta.get("td_avg_b"),
        td_acc_a=meta.get("td_acc_a"),
        td_def_a=meta.get("td_def_a"),
        td_def_b=meta.get("td_def_b"),
        finish_rate_a=meta.get("finish_rate_a"),
        finish_rate_b=meta.get("finish_rate_b"),
        reach_adv=meta.get("reach_adv"),
        style_a=meta.get("style_a"),
        style_b=meta.get("style_b"),
        round_number=meta.get("round_number"),
        knockdowns_a=int(meta.get("knockdowns_a", 0)),
        knockdowns_b=int(meta.get("knockdowns_b", 0)),
        control_time_a=meta.get("control_time_a"),
        control_time_b=meta.get("control_time_b"),
        market_probability=float(meta.get("market_probability", 0.5)),
    )


def _striking_edge(ctx: UFCFightContext) -> float:
    """Score striking differential for fighter A vs B."""
    score = 0.0
    if ctx.slpm_a is not None and ctx.slpm_b is not None:
        score += (ctx.slpm_a - ctx.slpm_b) * 0.02
    if ctx.str_acc_a is not None and ctx.str_acc_b is not None:
        score += (ctx.str_acc_a - ctx.str_acc_b) * 0.3
    if ctx.str_def_a is not None and ctx.str_def_b is not None:
        score += (ctx.str_def_a - ctx.str_def_b) * 0.25
    return score


def _grappling_edge(ctx: UFCFightContext) -> float:
    """Score grappling differential for fighter A."""
    score = 0.0
    if ctx.td_avg_a is not None and ctx.td_avg_b is not None:
        score += (ctx.td_avg_a - ctx.td_avg_b) * 0.03
    if ctx.td_def_a is not None and ctx.td_def_b is not None:
        score += (ctx.td_def_a - ctx.td_def_b) * 0.2
    return score


def _style_note(ctx: UFCFightContext) -> str:
    """Generate a style matchup note."""
    if not ctx.style_a or not ctx.style_b:
        return ""
    combos = {
        ("striker", "wrestler"): "wrestling vs striking — takedown success critical",
        ("wrestler", "striker"): "striking vs wrestling — takedown defense critical",
        ("grappler", "striker"): "grappling vs striking — clinch and takedowns favor A",
        ("striker", "grappler"): "striking vs grappling — keeping it standing favors A",
        ("striker", "striker"): "striker vs striker — pace and reach may decide",
        ("wrestler", "wrestler"): "grappling battle — top position control likely key",
    }
    return combos.get((ctx.style_a.lower(), ctx.style_b.lower()), f"{ctx.style_a} vs {ctx.style_b}")


def _price_prefight(ctx: UFCFightContext) -> dict[str, Any]:
    str_edge = _striking_edge(ctx)
    grap_edge = _grappling_edge(ctx)

    total_score = str_edge + grap_edge
    # Reach advantage
    if ctx.reach_adv:
        total_score += ctx.reach_adv * 0.005

    fair_prob = max(0.05, min(0.95, 0.5 + total_score))
    edge = fair_prob - ctx.market_probability

    confidence = 0.60
    # If we have no striking or grappling data, drop confidence
    has_data = sum([
        ctx.slpm_a is not None,
        ctx.str_acc_a is not None,
        ctx.td_avg_a is not None,
    ])
    confidence -= (3 - has_data) * 0.07

    # Uncertainty discount for high variance fight styles
    high_finish = (ctx.finish_rate_a or 0) > 0.7 or (ctx.finish_rate_b or 0) > 0.7
    uncertainty_discount = 0.1 if high_finish else 0.0
    if high_finish:
        confidence -= 0.05

    note = _style_note(ctx)

    return {
        "fair_probability": fair_prob,
        "edge": edge,
        "confidence": confidence,
        "style_note": note,
        "uncertainty_discount": uncertainty_discount,
        "notes": [note] if note else [],
    }


def _price_live(ctx: UFCFightContext) -> dict[str, Any]:
    fair_prob = ctx.market_probability
    notes: list[str] = ["live: using market prob as base"]

    # Knockdowns strongly shift probability
    kd_adj = (ctx.knockdowns_a - ctx.knockdowns_b) * 0.10
    fair_prob = max(0.02, min(0.98, fair_prob + kd_adj))

    # Control time
    if ctx.control_time_a is not None and ctx.control_time_b is not None:
        ctrl_diff = ctx.control_time_a - ctx.control_time_b
        fair_prob = max(0.02, min(0.98, fair_prob + ctrl_diff * 0.001))

    if ctx.knockdowns_a > ctx.knockdowns_b:
        notes.append(f"fighter A has {ctx.knockdowns_a} knockdown(s) — momentum shift")
    elif ctx.knockdowns_b > ctx.knockdowns_a:
        notes.append(f"fighter B has {ctx.knockdowns_b} knockdown(s) — momentum shift")

    return {
        "fair_probability": fair_prob,
        "edge": fair_prob - ctx.market_probability,
        "confidence": 0.55,
        "style_note": "",
        "uncertainty_discount": 0.0,
        "notes": notes,
    }


def run(inp: RouterInput) -> RouterOutput:
    ctx = build_context(inp)
    pricing = _price_prefight(ctx) if ctx.phase == "pre_game" else _price_live(ctx)

    fair_prob = pricing["fair_probability"]
    market_prob = ctx.market_probability
    ev = fair_prob * (1.0 / market_prob) - 1.0 if market_prob > 0 else 0.0
    edge = pricing["edge"]
    no_bet = abs(edge) < 0.02 or pricing["confidence"] < 0.40

    return RouterOutput(
        pipeline="ufc_fight_app",
        fair_probability=fair_prob,
        market_probability=market_prob,
        edge=edge,
        expected_value=ev,
        confidence=pricing["confidence"],
        no_bet_flag=no_bet,
        primary_signal="striking+grappling composite",
        notes=pricing["notes"],
        extra={
            "style_note": pricing["style_note"],
            "uncertainty_discount": pricing["uncertainty_discount"],
        },
    )
