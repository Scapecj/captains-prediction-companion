"""Typed models for sports routing and market intelligence outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class SportEvent:
    league: str
    event_id: str
    title: str | None = None
    start_time: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SportsCalendarRoute:
    active_sports: tuple[str, ...]
    counts_by_league: dict[str, int]
    games: tuple[SportEvent, ...] = ()
    fallback_used: bool = False


@dataclass(slots=True)
class SportsMarketQuote:
    venue: str
    market_id: str
    price: float
    implied_probability: float
    timestamp: datetime | None = None
    liquidity: float | None = None
    is_stale: bool = False


@dataclass(slots=True)
class SportMarketDecision:
    league: str
    event_id: str
    market_type: str
    market_subtype: str
    phase: str
    fair_probability: float
    market_probability: float
    edge: float
    expected_value: float
    confidence: float
    confidence_notes: str
    primary_signal: str
    secondary_signals: tuple[str, ...] = ()
    no_bet_flag: bool = False
    recommended_stake_cap: float | None = None
    notes: str = ""
