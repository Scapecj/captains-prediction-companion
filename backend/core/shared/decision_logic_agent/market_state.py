"""Market state and settlement state classification helpers."""

from __future__ import annotations

from .calculations import effective_spread_pct
from .models import DecisionLogicInput, DecisionPolicy, MarketState, SettlementState


def prefers_passive_execution(state: MarketState) -> bool:
    return state in (MarketState.THIN, MarketState.WIDE, MarketState.ONE_SIDED)


def classify_market_state(inp: DecisionLogicInput, policy: DecisionPolicy) -> MarketState:
    if inp.bid > inp.ask:
        return MarketState.CROSSED
    if inp.bid_size <= 0 or inp.ask_size <= 0:
        return MarketState.ONE_SIDED
    if min(inp.bid_size, inp.ask_size) < policy.thin_book_size:
        return MarketState.THIN
    if effective_spread_pct(inp.bid, inp.ask) >= policy.wide_spread_pct:
        return MarketState.WIDE
    return MarketState.NORMAL


def classify_settlement_state(
    inp: DecisionLogicInput,
    policy: DecisionPolicy,
) -> SettlementState:
    if inp.official_settlement_confirmed:
        return SettlementState.OFFICIALLY_SETTLED
    if inp.event_still_live:
        return SettlementState.LIVE
    if inp.settlement_risk_score >= policy.high_settlement_risk:
        return SettlementState.MANUAL_REVIEW_REQUIRED
    if (
        inp.effective_resolution_confidence >= policy.economic_resolution_confidence
        and inp.settlement_risk_score <= policy.low_settlement_risk
    ):
        return SettlementState.ECONOMICALLY_RESOLVED
    if inp.effective_resolution_confidence >= policy.near_resolution_confidence:
        return SettlementState.NEAR_RESOLUTION
    return SettlementState.OPEN
