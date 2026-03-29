"""NASCAR Race App — Cup, Trucks, O'Reilly race-level markets.

Handles: race-winner, top-3 finish, race-level live markets
NOT for championship futures (those go to nascar_series_futures_app).

Input signals (pre-race):
  - Practice speed (best single-lap and 5-lap/10-lap averages)
  - Tire falloff rate
  - Qualifying position context
  - Track-type performance (superspeedway, intermediate, short track, road course)
  - Season form (last 5-race average finish, DNF rate)

Input signals (live):
  - Running order and gap to leader
  - Active cautions
  - Pit strategy context (track position vs. pit cycle)
  - Stage position changes

Output fields:
  - fair_prob_win, fair_prob_top3, confidence, notes, post_race_signal
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.sports.companion_router import RouterInput, RouterOutput

TRACK_TYPES = ("superspeedway", "intermediate", "short_track", "road_course", "dirt")


@dataclass(slots=True)
class NASCARRaceContext:
    driver: str | None
    league: str
    phase: str
    field_size: int = 36
    # Practice / qualifying
    practice_best_lap: float | None = None   # speed in mph
    practice_5lap_avg: float | None = None
    practice_10lap_avg: float | None = None
    qualifying_position: int | None = None
    tire_falloff_pct: float | None = None    # % speed drop over 10 laps
    # Track type
    track_type: str = "intermediate"
    track_type_avg_finish: float | None = None  # driver's avg finish at this track type
    # Season form
    last5_avg_finish: float | None = None
    dnf_rate_season: float | None = None         # DNFs / races
    wins_season: int = 0
    # Live signals
    running_position: int | None = None
    gap_to_leader: float | None = None      # seconds
    caution_laps: int = 0
    laps_remaining: int | None = None
    stage_points: int = 0
    # Market
    market_prob_win: float = 0.05
    market_prob_top3: float | None = None


def build_context(inp: RouterInput) -> NASCARRaceContext:
    meta = inp.raw_metadata or {}
    return NASCARRaceContext(
        driver=meta.get("driver") or inp.title,
        league=inp.league or "NASCAR_CUP",
        phase=inp.phase or "pre_game",
        field_size=int(meta.get("field_size", 36)),
        practice_best_lap=meta.get("practice_best_lap"),
        practice_5lap_avg=meta.get("practice_5lap_avg"),
        practice_10lap_avg=meta.get("practice_10lap_avg"),
        qualifying_position=meta.get("qualifying_position"),
        tire_falloff_pct=meta.get("tire_falloff_pct"),
        track_type=meta.get("track_type", "intermediate"),
        track_type_avg_finish=meta.get("track_type_avg_finish"),
        last5_avg_finish=meta.get("last5_avg_finish"),
        dnf_rate_season=meta.get("dnf_rate_season"),
        wins_season=int(meta.get("wins_season", 0)),
        running_position=meta.get("running_position"),
        gap_to_leader=meta.get("gap_to_leader"),
        caution_laps=int(meta.get("caution_laps", 0)),
        laps_remaining=meta.get("laps_remaining"),
        stage_points=int(meta.get("stage_points", 0)),
        market_prob_win=float(meta.get("market_prob_win", 0.05)),
        market_prob_top3=meta.get("market_prob_top3"),
    )


def _base_win_probability(ctx: NASCARRaceContext) -> float:
    """Estimate base win probability from pre-race signals."""
    # Start from field-size baseline
    base = 1.0 / ctx.field_size

    # Qualifying position is a strong predictor on superspeedways and short tracks
    if ctx.qualifying_position is not None:
        if ctx.qualifying_position == 1:
            base *= 2.5
        elif ctx.qualifying_position <= 5:
            base *= 1.8
        elif ctx.qualifying_position <= 10:
            base *= 1.3
        elif ctx.qualifying_position > 20:
            base *= 0.7

    # Track-type historical average finish
    if ctx.track_type_avg_finish is not None:
        # Avg finish of 1-5 → multiply, 20+ → discount
        finish_factor = max(0.4, min(2.0, (ctx.field_size - ctx.track_type_avg_finish) / (ctx.field_size / 2)))
        base *= finish_factor

    # Season form
    if ctx.last5_avg_finish is not None:
        form_factor = max(0.5, min(1.8, (ctx.field_size - ctx.last5_avg_finish) / (ctx.field_size / 2)))
        base *= form_factor

    # Tire falloff advantage (low falloff = stronger long-run pace)
    if ctx.tire_falloff_pct is not None and ctx.tire_falloff_pct < 0.015:
        base *= 1.15
    elif ctx.tire_falloff_pct is not None and ctx.tire_falloff_pct > 0.035:
        base *= 0.85

    # Practice speed advantage
    if ctx.practice_10lap_avg is not None and ctx.practice_best_lap is not None:
        diff = ctx.practice_best_lap - ctx.practice_10lap_avg
        if diff < 0.3:  # small falloff in practice = long-run strength
            base *= 1.10

    return max(0.005, min(0.70, base))


def _top3_from_win(win_prob: float, field_size: int) -> float:
    """Rough top-3 estimate: ~3× win probability, capped."""
    return min(win_prob * 3.0, 0.65)


def _price_pregame(ctx: NASCARRaceContext) -> dict[str, Any]:
    fair_win = _base_win_probability(ctx)
    fair_top3 = _top3_from_win(fair_win, ctx.field_size)

    edge = fair_win - ctx.market_prob_win

    confidence = 0.55
    if ctx.practice_10lap_avg is None and ctx.qualifying_position is None:
        confidence -= 0.10
    if ctx.track_type_avg_finish is None:
        confidence -= 0.08
    if ctx.dnf_rate_season is not None and ctx.dnf_rate_season > 0.15:
        confidence -= 0.07

    notes: list[str] = []
    if ctx.qualifying_position == 1:
        notes.append("pole position — track position advantage")
    if ctx.tire_falloff_pct is not None and ctx.tire_falloff_pct < 0.015:
        notes.append("low tire falloff — strong long-run package")
    elif ctx.tire_falloff_pct is not None and ctx.tire_falloff_pct > 0.035:
        notes.append("high tire falloff — struggles on long runs")
    if ctx.dnf_rate_season and ctx.dnf_rate_season > 0.15:
        notes.append(f"reliability concern (DNF rate={ctx.dnf_rate_season:.0%})")

    return {
        "fair_prob_win": fair_win,
        "fair_prob_top3": fair_top3,
        "edge": edge,
        "confidence": confidence,
        "notes": notes,
        "post_race_signal": None,
    }


def _price_live(ctx: NASCARRaceContext) -> dict[str, Any]:
    fair_win = ctx.market_prob_win
    notes: list[str] = ["live: using running position to adjust"]

    if ctx.running_position is not None and ctx.laps_remaining is not None:
        total_laps_approx = ctx.laps_remaining + 50  # rough estimate
        completion = 1 - ctx.laps_remaining / max(total_laps_approx, 1)
        pos = ctx.running_position
        if pos == 1:
            fair_win = min(0.80, ctx.market_prob_win * (1.5 + completion))
            notes.append(f"running 1st with {ctx.laps_remaining} laps remaining")
        elif pos <= 5:
            fair_win = ctx.market_prob_win * 1.2
            notes.append(f"running P{pos}")
        elif pos > 20:
            fair_win = ctx.market_prob_win * 0.5
            notes.append(f"running P{pos} — long shot")

    fair_win = max(0.001, min(0.95, fair_win))

    return {
        "fair_prob_win": fair_win,
        "fair_prob_top3": _top3_from_win(fair_win, ctx.field_size),
        "edge": fair_win - ctx.market_prob_win,
        "confidence": 0.52,
        "notes": notes,
        "post_race_signal": "capture stage results and final position after race",
    }


def run(inp: RouterInput) -> RouterOutput:
    ctx = build_context(inp)
    pricing = _price_pregame(ctx) if ctx.phase != "live" else _price_live(ctx)

    fair_win = pricing["fair_prob_win"]
    market_prob = ctx.market_prob_win
    ev = fair_win * (1.0 / market_prob) - 1.0 if market_prob > 0 else 0.0
    edge = pricing["edge"]
    no_bet = abs(edge) < 0.015 or pricing["confidence"] < 0.40

    return RouterOutput(
        pipeline="nascar_race_app",
        fair_probability=fair_win,
        market_probability=market_prob,
        edge=edge,
        expected_value=ev,
        confidence=pricing["confidence"],
        no_bet_flag=no_bet,
        primary_signal=f"qual_pos={ctx.qualifying_position}, track_type={ctx.track_type}",
        notes=pricing["notes"],
        extra={
            "fair_prob_win": pricing["fair_prob_win"],
            "fair_prob_top3": pricing["fair_prob_top3"],
            "post_race_signal": pricing["post_race_signal"],
        },
    )
