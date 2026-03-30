"""Deterministic decision engine for normalized market inputs."""

from __future__ import annotations

from .calculations import (
    binary_fair_values,
    effective_spread_pct,
    expected_value,
    inventory_utilization,
    maker_cost_rate,
    net_edge_after_costs,
    normalize_implied_probabilities,
    quoted_spread,
    taker_cost_rate,
)
from .market_state import classify_market_state, classify_settlement_state, prefers_passive_execution
from .models import (
    DecisionLogicInput,
    DecisionLogicOutput,
    DecisionPolicy,
    MarketState,
    SettlementState,
    TradePosture,
)
from .sizing import bounded_side_sizing_fraction


def _execution_cost_for_state(
    market_state: MarketState,
    taker_cost: float,
    passive_cost: float,
) -> tuple[float, str]:
    if prefers_passive_execution(market_state):
        return passive_cost, "MAKER"
    return taker_cost, "TAKER"


def rank_by_best_executable_edge(outputs: list[DecisionLogicOutput]) -> list[DecisionLogicOutput]:
    """Rank outputs by executable edge, then confidence and raw edge.

    Event-level runners should use this instead of fair_yes_probability alone.
    """
    return sorted(
        outputs,
        key=lambda out: (
            out.best_executable_edge,
            out.confidence,
            out.edge_yes_after_costs,
            out.edge_no_after_costs,
        ),
        reverse=True,
    )


class DecisionLogicAgent:
    """Apply market math plus deterministic trade policy to a single market."""

    def __init__(self, policy: DecisionPolicy | None = None) -> None:
        self.policy = policy or DecisionPolicy()

    def evaluate(self, inp: DecisionLogicInput) -> DecisionLogicOutput:
        policy = self.policy

        fair_yes, fair_no = binary_fair_values(inp.fair_yes_probability)

        norm_yes, norm_no = normalize_implied_probabilities(inp.yes_price, inp.no_price)
        raw_edge_yes = fair_yes - norm_yes
        raw_edge_no = fair_no - norm_no

        mid = (inp.bid + inp.ask) / 2.0
        micro = (
            (inp.ask * inp.bid_size + inp.bid * inp.ask_size) / (inp.bid_size + inp.ask_size)
            if (inp.bid_size + inp.ask_size) > 0
            else mid
        )
        spread = quoted_spread(inp.bid, inp.ask)
        spread_pct = effective_spread_pct(inp.bid, inp.ask)

        state = classify_market_state(inp, policy)
        settlement = classify_settlement_state(inp, policy)

        taker_cost = taker_cost_rate(inp.fees_bps, inp.slippage_estimate, inp.bid, inp.ask)
        passive_cost = maker_cost_rate(inp.fees_bps, inp.slippage_estimate, inp.bid, inp.ask)
        execution_cost, maker_taker = _execution_cost_for_state(state, taker_cost, passive_cost)

        edge_yes_after_costs = net_edge_after_costs(raw_edge_yes, execution_cost)
        edge_no_after_costs = net_edge_after_costs(raw_edge_no, execution_cost)
        best_side = "YES" if edge_yes_after_costs >= edge_no_after_costs else "NO"
        best_executable_edge = max(edge_yes_after_costs, edge_no_after_costs)
        edge_after_costs = best_executable_edge

        expected_yes = expected_value(fair_yes, inp.ask)
        expected_no = expected_value(fair_no, inp.no_price)
        utilization = inventory_utilization(inp.position_size, inp.max_inventory)

        confidence = max(fair_yes, fair_no)
        recommended_side = "NONE"
        posture = TradePosture.NO_TRADE
        reject_reason = ""
        sizing_fraction = 0.0
        notes: list[str] = [
            f"best_side={best_side}",
            f"edge_yes_after_costs={edge_yes_after_costs:.4f}",
            f"edge_no_after_costs={edge_no_after_costs:.4f}",
            f"best_executable_edge={best_executable_edge:.4f}",
        ]

        if settlement == SettlementState.ECONOMICALLY_RESOLVED:
            posture = TradePosture.WAIT
            reject_reason = "economically_resolved_pending_settlement"
            notes.append("Economic resolution is strong enough to avoid fresh risk before official settlement.")
        elif settlement == SettlementState.MANUAL_REVIEW_REQUIRED:
            posture = TradePosture.ESCALATE
            reject_reason = "settlement_risk_too_high"
            notes.append("Settlement risk is too high for deterministic handling.")
        elif utilization >= 1.0:
            posture = TradePosture.NO_TRADE
            reject_reason = "inventory_cap_reached"
        elif state == MarketState.CROSSED:
            posture = TradePosture.ESCALATE
            reject_reason = "crossed_market_manual_review"
        else:
            if best_executable_edge < policy.min_trade_edge_after_costs:
                posture = TradePosture.NO_TRADE
                reject_reason = "edge_after_costs_below_threshold"
            else:
                execution_price = inp.ask if best_side == "YES" else inp.no_price
                probability = fair_yes if best_side == "YES" else fair_no

                if prefers_passive_execution(state):
                    maker_taker = "MAKER"
                    posture = TradePosture.PLACE_PASSIVE_ORDER
                else:
                    maker_taker = "TAKER"
                    posture = TradePosture.TRADE_YES if best_side == "YES" else TradePosture.TRADE_NO

                sizing_fraction = bounded_side_sizing_fraction(
                    probability=probability,
                    execution_price=execution_price,
                    multiplier=policy.reduced_kelly_multiplier,
                    max_fraction=policy.max_sizing_fraction,
                    position_size=inp.position_size,
                    max_inventory=inp.max_inventory,
                )

                if sizing_fraction <= 0.0:
                    posture = TradePosture.NO_TRADE
                    reject_reason = "no_inventory_headroom_for_trade"

                if confidence < policy.low_confidence_threshold and posture in (
                    TradePosture.TRADE_YES,
                    TradePosture.TRADE_NO,
                    TradePosture.PLACE_PASSIVE_ORDER,
                ):
                    posture = TradePosture.WAIT
                    reject_reason = "confidence_below_threshold"

        if posture in (TradePosture.WAIT, TradePosture.ESCALATE, TradePosture.NO_TRADE):
            recommended_side = "NONE"
        else:
            recommended_side = best_side

        return DecisionLogicOutput(
            fair_yes_probability=fair_yes,
            fair_no_probability=fair_no,
            fair_yes_value=fair_yes,
            fair_no_value=fair_no,
            raw_edge_yes=raw_edge_yes,
            raw_edge_no=raw_edge_no,
            edge_yes_after_costs=edge_yes_after_costs,
            edge_no_after_costs=edge_no_after_costs,
            best_side=best_side,
            best_executable_edge=best_executable_edge,
            edge_after_costs=edge_after_costs,
            midpoint=mid,
            microprice=micro,
            quoted_spread=spread,
            effective_spread_pct=spread_pct,
            market_state=state,
            settlement_state=settlement,
            recommended_side=recommended_side,
            trade_posture=posture,
            sizing_fraction=sizing_fraction,
            confidence=confidence,
            reject_reason=reject_reason,
            normalized_yes_implied_probability=norm_yes,
            normalized_no_implied_probability=norm_no,
            maker_taker_recommendation=maker_taker if posture not in (
                TradePosture.WAIT,
                TradePosture.ESCALATE,
                TradePosture.NO_TRADE,
            ) else "NONE",
            inventory_utilization=utilization,
            expected_value_yes=expected_yes,
            expected_value_no=expected_no,
            notes=notes,
        )
