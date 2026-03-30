"""Strict IO contracts for the decision logic agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import StrEnum


class TradePosture(StrEnum):
    TRADE_YES = "TRADE_YES"
    TRADE_NO = "TRADE_NO"
    PLACE_PASSIVE_ORDER = "PLACE_PASSIVE_ORDER"
    WAIT = "WAIT"
    ESCALATE = "ESCALATE"
    NO_TRADE = "NO_TRADE"


class MarketState(StrEnum):
    NORMAL = "NORMAL"
    THIN = "THIN"
    WIDE = "WIDE"
    ONE_SIDED = "ONE_SIDED"
    CROSSED = "CROSSED"


class SettlementState(StrEnum):
    LIVE = "LIVE"
    OPEN = "OPEN"
    NEAR_RESOLUTION = "NEAR_RESOLUTION"
    ECONOMICALLY_RESOLVED = "ECONOMICALLY_RESOLVED"
    OFFICIALLY_SETTLED = "OFFICIALLY_SETTLED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


@dataclass(slots=True)
class DecisionPolicy:
    """Policy thresholds kept separate from pure calculation helpers."""

    min_trade_edge_after_costs: float = 0.01
    min_escalation_edge: float = 0.03
    wide_spread_pct: float = 0.05
    thin_book_size: float = 100.0
    low_confidence_threshold: float = 0.45
    economic_resolution_confidence: float = 0.95
    near_resolution_confidence: float = 0.75
    low_settlement_risk: float = 0.10
    high_settlement_risk: float = 0.50
    reduced_kelly_multiplier: float = 0.25
    max_sizing_fraction: float = 0.10


@dataclass(slots=True)
class DecisionLogicInput:
    market_type: str
    app_source: str
    yes_price: float
    no_price: float
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    fair_yes_probability: float
    fees_bps: float
    slippage_estimate: float
    position_size: float
    max_inventory: float
    event_still_live: bool
    effective_resolution_confidence: float
    settlement_risk_score: float
    official_settlement_confirmed: bool = False
    market_id: str = ""
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_probability("yes_price", self.yes_price)
        _validate_probability("no_price", self.no_price)
        _validate_probability("bid", self.bid)
        _validate_probability("ask", self.ask)
        _validate_probability("fair_yes_probability", self.fair_yes_probability)
        _validate_probability(
            "effective_resolution_confidence",
            self.effective_resolution_confidence,
        )
        _validate_probability("settlement_risk_score", self.settlement_risk_score)
        if self.ask < self.bid:
            # Allow crossed books, but keep the values sane individually.
            pass
        for name, value in (
            ("bid_size", self.bid_size),
            ("ask_size", self.ask_size),
            ("fees_bps", self.fees_bps),
            ("slippage_estimate", self.slippage_estimate),
            ("position_size", self.position_size),
            ("max_inventory", self.max_inventory),
        ):
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.max_inventory <= 0:
            raise ValueError("max_inventory must be positive")
        if not self.market_type:
            raise ValueError("market_type is required")
        if not self.app_source:
            raise ValueError("app_source is required")


@dataclass(slots=True)
class DecisionLogicOutput:
    fair_yes_probability: float
    fair_no_probability: float
    fair_yes_value: float
    fair_no_value: float
    raw_edge_yes: float
    raw_edge_no: float
    edge_yes_after_costs: float
    edge_no_after_costs: float
    best_side: str
    best_executable_edge: float
    edge_after_costs: float
    midpoint: float
    microprice: float
    quoted_spread: float
    effective_spread_pct: float
    market_state: MarketState
    settlement_state: SettlementState
    recommended_side: str
    trade_posture: TradePosture
    sizing_fraction: float
    confidence: float
    reject_reason: str
    normalized_yes_implied_probability: float
    normalized_no_implied_probability: float
    maker_taker_recommendation: str
    inventory_utilization: float
    expected_value_yes: float
    expected_value_no: float
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    notes: list[str] = field(default_factory=list)


def _validate_probability(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")
