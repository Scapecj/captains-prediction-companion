"""Pure pricing and market microstructure math for prediction markets."""

from __future__ import annotations


def clamp_probability(value: float) -> float:
    return max(0.0, min(1.0, value))


def complement_probability(value: float) -> float:
    return 1.0 - clamp_probability(value)


def normalize_implied_probabilities(yes_price: float, no_price: float) -> tuple[float, float]:
    """Normalize a YES/NO pair to sum to 1.0.

    Markets often carry a small overround or stale mismatch. This function
    removes that mismatch before edge calculations.
    """
    total = yes_price + no_price
    if total <= 0:
        return 0.5, 0.5
    return yes_price / total, no_price / total


def binary_fair_values(fair_yes_probability: float) -> tuple[float, float]:
    fair_yes = clamp_probability(fair_yes_probability)
    return fair_yes, complement_probability(fair_yes)


def midpoint(bid: float, ask: float) -> float:
    return (bid + ask) / 2.0


def microprice(bid: float, ask: float, bid_size: float, ask_size: float) -> float:
    """Book-weighted microprice for the YES side.

    We weight each quote by the size resting on the opposite side. If there is
    no depth, fall back to the midpoint.
    """
    total_size = bid_size + ask_size
    if total_size <= 0:
        return midpoint(bid, ask)
    return ((ask * bid_size) + (bid * ask_size)) / total_size


def quoted_spread(bid: float, ask: float) -> float:
    return ask - bid


def effective_spread_pct(bid: float, ask: float) -> float:
    mid = midpoint(bid, ask)
    if mid <= 0:
        return 0.0
    return quoted_spread(bid, ask) / mid


def fee_rate_from_bps(fees_bps: float) -> float:
    return fees_bps / 10_000.0


def expected_value(probability: float, execution_price: float) -> float:
    """Expected value of buying a binary contract at `execution_price`."""
    return probability - execution_price


def net_edge_after_costs(raw_edge: float, cost_rate: float) -> float:
    return raw_edge - cost_rate


def inventory_utilization(position_size: float, max_inventory: float) -> float:
    if max_inventory <= 0:
        return 1.0
    return min(1.0, max(0.0, position_size / max_inventory))


def taker_cost_rate(
    fees_bps: float,
    slippage_estimate: float,
    bid: float,
    ask: float,
) -> float:
    """Estimated one-way taker cost in probability points."""
    return fee_rate_from_bps(fees_bps) + slippage_estimate + (quoted_spread(bid, ask) / 2.0)


def maker_cost_rate(
    fees_bps: float,
    slippage_estimate: float,
    bid: float,
    ask: float,
) -> float:
    """Estimated passive-entry cost.

    We assume a passive order avoids half-spread crossing but still pays fees
    and some adverse selection / queue risk.
    """
    return fee_rate_from_bps(fees_bps) + (slippage_estimate * 0.5) + (quoted_spread(bid, ask) * 0.10)
