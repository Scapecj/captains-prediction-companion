"""MLB Home Run Prop App — batter HR props only.

REQUIRES confirmed lineup before recommending a prop.

Input signals:
  - Barrel rate, hard-hit rate, launch-angle profile
  - Rolling power form (last 10/30 games HR rate)
  - Splits vs pitcher handedness
  - Lineup slot
  - Opposing pitcher HR vulnerability (HR/9, hard contact allowed, fly-ball %)
  - Park factor (HR-specific)
  - Weather (wind, temperature)

Output fields:
  - fair_prob_hr, market_prob_hr, edge_hr, confidence_hr, primary_driver_hr, notes
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.sports.companion_router import RouterInput, RouterOutput

# Minimum sample sizes before trusting rates
_MIN_PA_SAMPLE = 100
_MIN_PITCHER_BF = 50


@dataclass(slots=True)
class HRPropContext:
    batter_name: str | None
    lineup_confirmed: bool
    # Batter power profile
    barrel_rate: float | None = None      # fraction e.g. 0.12
    hard_hit_rate: float | None = None    # fraction e.g. 0.42
    launch_angle_avg: float | None = None
    hr_rate_l10: float | None = None      # HRs per PA last 10 games
    hr_rate_l30: float | None = None      # HRs per PA last 30 games
    platoon_advantage: float = 0.0        # positive = batter has platoon edge
    lineup_slot: int | None = None        # 1-9
    pa_sample: int = 0
    # Pitcher vulnerability
    pitcher_hr_per_9: float | None = None
    pitcher_hard_contact_rate: float | None = None
    pitcher_fb_rate: float | None = None  # fly-ball rate allowed
    pitcher_bf_sample: int = 0
    # Context
    park_factor_hr: float = 1.0           # HR-specific park factor
    wind_speed_mph: float | None = None
    wind_direction: str | None = None     # "out" | "in" | "across"
    temperature_f: float | None = None
    # Market
    market_prob_hr: float = 0.12          # typical market HR prob


def build_context(inp: RouterInput) -> HRPropContext:
    meta = inp.raw_metadata or {}
    return HRPropContext(
        batter_name=meta.get("batter_name") or inp.title,
        lineup_confirmed=bool(meta.get("lineup_confirmed", False)),
        barrel_rate=meta.get("barrel_rate"),
        hard_hit_rate=meta.get("hard_hit_rate"),
        launch_angle_avg=meta.get("launch_angle_avg"),
        hr_rate_l10=meta.get("hr_rate_l10"),
        hr_rate_l30=meta.get("hr_rate_l30"),
        platoon_advantage=float(meta.get("platoon_advantage", 0.0)),
        lineup_slot=meta.get("lineup_slot"),
        pa_sample=int(meta.get("pa_sample", 0)),
        pitcher_hr_per_9=meta.get("pitcher_hr_per_9"),
        pitcher_hard_contact_rate=meta.get("pitcher_hard_contact_rate"),
        pitcher_fb_rate=meta.get("pitcher_fb_rate"),
        pitcher_bf_sample=int(meta.get("pitcher_bf_sample", 0)),
        park_factor_hr=float(meta.get("park_factor_hr", 1.0)),
        wind_speed_mph=meta.get("wind_speed_mph"),
        wind_direction=meta.get("wind_direction"),
        temperature_f=meta.get("temperature_f"),
        market_prob_hr=float(meta.get("market_prob_hr", 0.12)),
    )


def _base_hr_probability(ctx: HRPropContext) -> tuple[float, list[str]]:
    """Estimate base HR probability per PA from batter profile."""
    notes: list[str] = []

    # League average HR/PA ≈ 0.035 (roughly 3.5%)
    base = 0.035

    if ctx.barrel_rate is not None:
        # High barrel rate strongly predicts HR
        base += (ctx.barrel_rate - 0.07) * 0.5  # league avg barrel ~7%
        notes.append(f"barrel_rate={ctx.barrel_rate:.3f}")

    if ctx.hr_rate_l30 is not None and ctx.pa_sample >= _MIN_PA_SAMPLE:
        base = (base + ctx.hr_rate_l30) / 2  # blend with rolling form
        notes.append(f"hr_rate_l30={ctx.hr_rate_l30:.4f}")
    elif ctx.hr_rate_l10 is not None:
        base = (base + ctx.hr_rate_l10) / 2
        notes.append(f"hr_rate_l10={ctx.hr_rate_l10:.4f} (short sample)")

    # Platoon advantage
    base += ctx.platoon_advantage * 0.005
    if ctx.platoon_advantage > 0.2:
        notes.append("platoon advantage for batter")

    # Lineup slot — top of order sees more PAs
    if ctx.lineup_slot is not None:
        if ctx.lineup_slot <= 3:
            base *= 1.05  # ~extra PA per game
        elif ctx.lineup_slot >= 7:
            base *= 0.95

    return max(0.005, min(0.5, base)), notes


def _pitcher_vulnerability_multiplier(ctx: HRPropContext) -> tuple[float, list[str]]:
    """Scale HR probability by pitcher's vulnerability to HRs."""
    mult = 1.0
    notes: list[str] = []

    if ctx.pitcher_hr_per_9 is not None and ctx.pitcher_bf_sample >= _MIN_PITCHER_BF:
        league_avg_hr9 = 1.3
        if ctx.pitcher_hr_per_9 > league_avg_hr9 * 1.2:
            mult *= 1.12
            notes.append(f"pitcher HR-prone (HR/9={ctx.pitcher_hr_per_9:.2f})")
        elif ctx.pitcher_hr_per_9 < league_avg_hr9 * 0.8:
            mult *= 0.88
            notes.append(f"pitcher suppresses HRs (HR/9={ctx.pitcher_hr_per_9:.2f})")

    if ctx.pitcher_fb_rate is not None and ctx.pitcher_fb_rate > 0.40:
        mult *= 1.06
        notes.append(f"pitcher fly-ball prone (fb%={ctx.pitcher_fb_rate:.2%})")

    return mult, notes


def _context_multiplier(ctx: HRPropContext) -> tuple[float, list[str]]:
    """Scale by park, wind, and temperature."""
    mult = ctx.park_factor_hr
    notes: list[str] = []

    if ctx.park_factor_hr != 1.0:
        notes.append(f"park_factor_hr={ctx.park_factor_hr:.2f}")

    if ctx.wind_speed_mph and ctx.wind_direction == "out" and ctx.wind_speed_mph > 10:
        mult *= 1.0 + min(ctx.wind_speed_mph * 0.004, 0.10)
        notes.append(f"wind blowing out {ctx.wind_speed_mph} mph — HR boosted")
    elif ctx.wind_speed_mph and ctx.wind_direction == "in" and ctx.wind_speed_mph > 10:
        mult *= 1.0 - min(ctx.wind_speed_mph * 0.004, 0.10)
        notes.append(f"wind blowing in {ctx.wind_speed_mph} mph — HR reduced")

    if ctx.temperature_f is not None and ctx.temperature_f < 50:
        mult *= 0.93
        notes.append(f"cold weather ({ctx.temperature_f}°F) — ball carries less")
    elif ctx.temperature_f is not None and ctx.temperature_f > 85:
        mult *= 1.04

    return mult, notes


def _pa_per_game(lineup_slot: int | None) -> float:
    """Approximate plate appearances per game by lineup slot."""
    if lineup_slot is None:
        return 3.8
    if lineup_slot <= 3:
        return 4.2
    if lineup_slot <= 6:
        return 3.9
    return 3.5


def run(inp: RouterInput) -> RouterOutput:
    ctx = build_context(inp)

    if not ctx.lineup_confirmed:
        return RouterOutput(
            pipeline="mlb_home_run_prop_app",
            no_bet_flag=True,
            notes=["lineup not confirmed — no HR prop recommendation"],
        )

    base_hr_prob_per_pa, batter_notes = _base_hr_probability(ctx)
    pitcher_mult, pitcher_notes = _pitcher_vulnerability_multiplier(ctx)
    ctx_mult, ctx_notes = _context_multiplier(ctx)

    # Convert per-PA probability to per-game probability
    pa = _pa_per_game(ctx.lineup_slot)
    hr_prob_per_pa = base_hr_prob_per_pa * pitcher_mult * ctx_mult
    # P(at least 1 HR in N PAs) = 1 - (1 - p)^N
    fair_prob_hr = 1.0 - (1.0 - hr_prob_per_pa) ** pa
    fair_prob_hr = max(0.01, min(0.70, fair_prob_hr))

    edge = fair_prob_hr - ctx.market_prob_hr
    ev = edge / ctx.market_prob_hr if ctx.market_prob_hr > 0 else 0.0

    confidence = 0.60
    if ctx.pa_sample < _MIN_PA_SAMPLE:
        confidence -= 0.10
    if ctx.pitcher_bf_sample < _MIN_PITCHER_BF:
        confidence -= 0.08
    if ctx.barrel_rate is None:
        confidence -= 0.08

    no_bet = abs(edge) < 0.02 or confidence < 0.40 or not ctx.lineup_confirmed

    primary_driver = "barrel_rate" if ctx.barrel_rate else ("hr_rate_l30" if ctx.hr_rate_l30 else "market_base")

    all_notes = batter_notes + pitcher_notes + ctx_notes

    return RouterOutput(
        pipeline="mlb_home_run_prop_app",
        fair_probability=fair_prob_hr,
        market_probability=ctx.market_prob_hr,
        edge=edge,
        expected_value=ev,
        confidence=confidence,
        no_bet_flag=no_bet,
        primary_signal=primary_driver,
        notes=all_notes,
        extra={
            "fair_prob_hr": fair_prob_hr,
            "market_prob_hr": ctx.market_prob_hr,
            "edge_hr": edge,
            "confidence_hr": confidence,
            "primary_driver_hr": primary_driver,
            "hr_prob_per_pa": hr_prob_per_pa,
            "pa_projected": pa,
        },
    )
