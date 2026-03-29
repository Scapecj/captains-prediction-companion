"""Baseball Game App — MLB and NCAA Baseball full-game sides/totals.

Handles: moneyline / totals (no player props — those go to mlb_home_run_prop_app
         or mlb_strikeout_prop_app)
Leagues: MLB, NCAA_BASEBALL

Input signals:
  - Starter quality (FIP, xFIP, ERA-, or ERA for NCAA)
  - Workload context (days rest, pitch count limit)
  - Lineup handedness vs starter
  - Bullpen state (high-leverage arms availability)
  - Weather (wind direction, temperature, humidity)
  - Park factor

Output fields:
  - fair_moneyline, fair_total, confidence, pitcher_edge_note, bullpen_edge_note
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.sports.companion_router import RouterInput, RouterOutput


@dataclass(slots=True)
class BaseballGameContext:
    league: str
    event_id: str | None
    phase: str
    # Starter quality (lower = better for pitchers)
    fip_home: float | None = None   # or ERA- for NCAA
    fip_away: float | None = None
    starter_rest_home: int | None = None  # days rest
    starter_rest_away: int | None = None
    # Lineup vs handedness (fraction of lineup platoon advantage)
    handedness_advantage_home: float = 0.0  # positive = home lineup favored
    # Bullpen
    bullpen_depleted_home: bool = False
    bullpen_depleted_away: bool = False
    # Context
    park_factor: float = 1.0       # >1 = hitter-friendly
    wind_speed_mph: float | None = None
    wind_direction: str | None = None  # "out" | "in" | "across"
    temperature_f: float | None = None
    # Market
    market_probability: float = 0.5
    market_total: float | None = None


def build_context(inp: RouterInput) -> BaseballGameContext:
    meta = inp.raw_metadata or {}
    return BaseballGameContext(
        league=inp.league or "MLB",
        event_id=inp.market_id,
        phase=inp.phase or "pre_game",
        fip_home=meta.get("fip_home"),
        fip_away=meta.get("fip_away"),
        starter_rest_home=meta.get("starter_rest_home"),
        starter_rest_away=meta.get("starter_rest_away"),
        handedness_advantage_home=float(meta.get("handedness_advantage_home", 0.0)),
        bullpen_depleted_home=bool(meta.get("bullpen_depleted_home", False)),
        bullpen_depleted_away=bool(meta.get("bullpen_depleted_away", False)),
        park_factor=float(meta.get("park_factor", 1.0)),
        wind_speed_mph=meta.get("wind_speed_mph"),
        wind_direction=meta.get("wind_direction"),
        temperature_f=meta.get("temperature_f"),
        market_probability=float(meta.get("market_probability", 0.5)),
        market_total=meta.get("market_total"),
    )


def _pitcher_advantage(fip_home: float | None, fip_away: float | None) -> float:
    """Return probability adjustment from FIP differential (home perspective)."""
    if fip_home is None or fip_away is None:
        return 0.0
    diff = fip_away - fip_home  # positive = home pitcher is better
    return diff * 0.015  # rough: 1 FIP point ≈ 1.5pp


def _total_adjustment(
    park_factor: float,
    wind_speed: float | None,
    wind_dir: str | None,
    temp_f: float | None,
    base_total: float,
) -> tuple[float, list[str]]:
    notes: list[str] = []
    adj = 0.0
    # Park factor
    adj += (park_factor - 1.0) * 1.5
    if park_factor > 1.05:
        notes.append(f"hitter-friendly park (factor={park_factor:.2f}) — total up")
    elif park_factor < 0.95:
        notes.append(f"pitcher-friendly park (factor={park_factor:.2f}) — total down")
    # Wind
    if wind_speed and wind_dir:
        if wind_dir == "out" and wind_speed > 10:
            adj += min(wind_speed * 0.05, 1.5)
            notes.append(f"wind blowing out at {wind_speed} mph — total up")
        elif wind_dir == "in" and wind_speed > 10:
            adj -= min(wind_speed * 0.05, 1.5)
            notes.append(f"wind blowing in at {wind_speed} mph — total down")
    # Temperature: cold suppresses offense
    if temp_f is not None and temp_f < 50:
        adj -= (50 - temp_f) * 0.04
        notes.append(f"cold weather ({temp_f}°F) — total down")
    return base_total + adj, notes


def _price_game(ctx: BaseballGameContext) -> dict[str, Any]:
    base_prob = 0.5
    base_prob += _pitcher_advantage(ctx.fip_home, ctx.fip_away)
    base_prob += ctx.handedness_advantage_home * 0.01
    base_prob = max(0.05, min(0.95, base_prob))

    base_total = ctx.market_total or 8.5
    fair_total, total_notes = _total_adjustment(
        ctx.park_factor, ctx.wind_speed_mph, ctx.wind_direction, ctx.temperature_f, base_total
    )

    edge = base_prob - ctx.market_probability
    confidence = 0.65
    if ctx.fip_home is None or ctx.fip_away is None:
        confidence -= 0.10

    pitcher_note = ""
    if ctx.fip_home is not None and ctx.fip_away is not None:
        if ctx.fip_home < ctx.fip_away - 0.5:
            pitcher_note = f"home starter advantage (FIP {ctx.fip_home:.2f} vs {ctx.fip_away:.2f})"
        elif ctx.fip_away < ctx.fip_home - 0.5:
            pitcher_note = f"away starter advantage (FIP {ctx.fip_away:.2f} vs {ctx.fip_home:.2f})"

    bullpen_note = ""
    if ctx.bullpen_depleted_home and not ctx.bullpen_depleted_away:
        edge -= 0.02
        bullpen_note = "home bullpen depleted — fade home late"
    elif ctx.bullpen_depleted_away and not ctx.bullpen_depleted_home:
        edge += 0.02
        bullpen_note = "away bullpen depleted — lean home late"

    notes = total_notes[:]
    if pitcher_note:
        notes.append(pitcher_note)
    if bullpen_note:
        notes.append(bullpen_note)

    return {
        "fair_moneyline": base_prob,
        "fair_total": fair_total,
        "edge": edge,
        "confidence": confidence,
        "pitcher_edge_note": pitcher_note,
        "bullpen_edge_note": bullpen_note,
        "notes": notes,
    }


def run(inp: RouterInput) -> RouterOutput:
    ctx = build_context(inp)
    pricing = _price_game(ctx)

    fair_prob = pricing["fair_moneyline"]
    market_prob = ctx.market_probability
    ev = fair_prob * (1.0 / market_prob) - 1.0 if market_prob > 0 else 0.0
    edge = pricing["edge"]
    no_bet = abs(edge) < 0.02 or pricing["confidence"] < 0.45

    return RouterOutput(
        pipeline="baseball_game_app",
        fair_probability=fair_prob,
        market_probability=market_prob,
        edge=edge,
        expected_value=ev,
        confidence=pricing["confidence"],
        no_bet_flag=no_bet,
        primary_signal=f"fip_diff={( (ctx.fip_home or 0) - (ctx.fip_away or 0)):.2f}",
        notes=pricing["notes"],
        extra={
            "fair_moneyline": pricing["fair_moneyline"],
            "fair_total": pricing["fair_total"],
            "pitcher_edge_note": pricing["pitcher_edge_note"],
            "bullpen_edge_note": pricing["bullpen_edge_note"],
        },
    )
