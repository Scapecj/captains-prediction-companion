"""NASCAR Series Futures App — championship futures only.

Handles LONG-HORIZON markets only. Not for race-level or live markets.
Leagues: NASCAR_CUP, NASCAR_TRUCKS, NASCAR_OREILLY

Refresh cadence: after each race weekend, or on a scheduled basis.
DO NOT use for fast live polling.

Kalshi series markets supported:
  KXNASCARTRUCKSERIES-NTS26    → NASCAR_TRUCKS championship 2026
  KXNASCARCUPSERIES-NCS26      → NASCAR_CUP championship 2026
  KXNASCARAUTOPARTSSERIES-NAPS26 → NASCAR_OREILLY championship 2026

Input signals:
  - Current points standings
  - Wins and playoff eligibility
  - Average finish (recent vs season)
  - Track-type performance for remaining schedule
  - Recent form (last 5 race avg finish)
  - Market probabilities (per driver)

Output fields:
  - series_championship_probabilities (dict driver → prob)
  - edge, confidence, notes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.sports.companion_router import RouterInput, RouterOutput


@dataclass(slots=True)
class DriverFuturesEntry:
    driver: str
    points: int = 0
    wins: int = 0
    playoff_eligible: bool = True
    avg_finish_season: float | None = None
    avg_finish_recent5: float | None = None
    track_type_fit_score: float = 1.0   # 0-2, relative to field average
    market_prob: float = 0.05


@dataclass(slots=True)
class NASCARFuturesContext:
    league: str
    season: int
    races_remaining: int
    playoff_format: bool = True         # True for Cup (playoff-style)
    drivers: list[DriverFuturesEntry] = field(default_factory=list)
    target_driver: str | None = None    # if pricing a single driver
    market_prob_target: float = 0.05
    kalshi_market_id: str | None = None


def build_context(inp: RouterInput) -> NASCARFuturesContext:
    meta = inp.raw_metadata or {}
    kalshi_meta = meta.get("_route", {}).get("kalshi_nascar_meta") or {}

    league = inp.league or kalshi_meta.get("league") or "NASCAR_CUP"
    season = int(kalshi_meta.get("season") or meta.get("season") or 2026)

    raw_drivers = meta.get("drivers", [])
    drivers = []
    for d in raw_drivers:
        drivers.append(DriverFuturesEntry(
            driver=d.get("driver", "Unknown"),
            points=int(d.get("points", 0)),
            wins=int(d.get("wins", 0)),
            playoff_eligible=bool(d.get("playoff_eligible", True)),
            avg_finish_season=d.get("avg_finish_season"),
            avg_finish_recent5=d.get("avg_finish_recent5"),
            track_type_fit_score=float(d.get("track_type_fit_score", 1.0)),
            market_prob=float(d.get("market_prob", 0.05)),
        ))

    return NASCARFuturesContext(
        league=str(league),
        season=season,
        races_remaining=int(meta.get("races_remaining", 10)),
        playoff_format=bool(meta.get("playoff_format", league == "NASCAR_CUP")),
        drivers=drivers,
        target_driver=meta.get("target_driver") or inp.title,
        market_prob_target=float(meta.get("market_prob_target", 0.05)),
        kalshi_market_id=inp.market_id,
    )


def _score_driver(entry: DriverFuturesEntry, races_remaining: int, field_size: int = 36) -> float:
    """Compute a relative strength score for championship probability."""
    score = 1.0

    # Wins are the strongest signal (playoff qualification)
    if entry.wins > 0:
        score *= 1.5 + entry.wins * 0.2

    # Recent form vs season average
    if entry.avg_finish_recent5 is not None:
        form_factor = max(0.4, min(2.0, (field_size - entry.avg_finish_recent5) / (field_size / 2)))
        score *= form_factor
    elif entry.avg_finish_season is not None:
        form_factor = max(0.4, min(1.8, (field_size - entry.avg_finish_season) / (field_size / 2)))
        score *= form_factor

    # Track type fit for remaining schedule
    score *= max(0.5, min(2.0, entry.track_type_fit_score))

    # Points position (rough)
    if entry.points > 0:
        # Higher points = more competitive
        score *= max(0.7, min(1.4, entry.points / 1000.0))

    # Non-eligible drivers can't win championship
    if not entry.playoff_eligible:
        score *= 0.01

    return max(0.0, score)


def _normalize_probabilities(scores: dict[str, float]) -> dict[str, float]:
    """Convert raw scores to probabilities that sum to ~1."""
    total = sum(scores.values())
    if total <= 0:
        n = len(scores)
        return {k: 1.0 / n for k in scores}
    return {k: v / total for k, v in scores.items()}


def run(inp: RouterInput) -> RouterOutput:
    ctx = build_context(inp)

    if not ctx.drivers:
        # Single-driver mode: just evaluate edge on the target
        market_prob = ctx.market_prob_target
        # Without comparative field data, use market price as anchor with mild edge
        fair_prob = market_prob  # no adjustment without field data
        return RouterOutput(
            pipeline="nascar_series_futures_app",
            fair_probability=fair_prob,
            market_probability=market_prob,
            edge=0.0,
            expected_value=0.0,
            confidence=0.35,
            no_bet_flag=True,
            notes=[
                "no driver comparison data provided — cannot generate edge",
                f"league={ctx.league}, season={ctx.season}",
                f"kalshi_market_id={ctx.kalshi_market_id}",
            ],
        )

    field_size = len(ctx.drivers)
    scores = {d.driver: _score_driver(d, ctx.races_remaining, field_size) for d in ctx.drivers}
    probs = _normalize_probabilities(scores)

    # Build output for target driver if specified
    target = ctx.target_driver
    fair_prob_target = probs.get(target, ctx.market_prob_target) if target else None

    edge = 0.0
    market_prob = ctx.market_prob_target
    if fair_prob_target is not None:
        # Find market prob for target in driver list
        for d in ctx.drivers:
            if d.driver == target:
                market_prob = d.market_prob
                break
        edge = fair_prob_target - market_prob

    confidence = 0.52
    if ctx.races_remaining > 15:
        confidence -= 0.08  # too far out, high variance
    if all(d.avg_finish_season is None and d.wins == 0 for d in ctx.drivers):
        confidence -= 0.10

    no_bet = abs(edge) < 0.015 or confidence < 0.35

    notes: list[str] = [
        f"league={ctx.league}, season={ctx.season}",
        f"races_remaining={ctx.races_remaining}",
        f"playoff_format={ctx.playoff_format}",
    ]
    if ctx.kalshi_market_id:
        notes.append(f"kalshi_market_id={ctx.kalshi_market_id}")
    top3 = sorted(probs.items(), key=lambda x: x[1], reverse=True)[:3]
    notes.append("top-3 fair probs: " + ", ".join(f"{d}={p:.3f}" for d, p in top3))

    ev = (fair_prob_target or 0) * (1.0 / market_prob) - 1.0 if market_prob > 0 else 0.0

    return RouterOutput(
        pipeline="nascar_series_futures_app",
        fair_probability=fair_prob_target or 0.0,
        market_probability=market_prob,
        edge=edge,
        expected_value=ev,
        confidence=confidence,
        no_bet_flag=no_bet,
        primary_signal=f"points+wins+form composite (target={target})",
        notes=notes,
        extra={
            "series_championship_probabilities": probs,
            "target_driver": target,
            "league": ctx.league,
            "season": ctx.season,
            "races_remaining": ctx.races_remaining,
        },
    )
