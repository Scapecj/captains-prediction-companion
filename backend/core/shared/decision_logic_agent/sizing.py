"""Sizing helpers for binary prediction markets."""

from __future__ import annotations

from .calculations import clamp_probability, inventory_utilization


def kelly_fraction_for_binary(probability: float, execution_price: float) -> float:
    """Kelly fraction for a binary contract paying 1.0 on success.

    For a binary contract bought at price `p_mkt` with fair success probability
    `p_fair`, the closed-form Kelly fraction is:

      f* = (p_fair - p_mkt) / (1 - p_mkt)

    We clamp at zero because negative Kelly means do not buy that side.
    """
    execution_price = clamp_probability(execution_price)
    probability = clamp_probability(probability)
    if execution_price >= 1.0:
        return 0.0
    return max(0.0, (probability - execution_price) / (1.0 - execution_price))


def kelly_fraction_for_side(probability: float, execution_price: float) -> float:
    """Side-agnostic Kelly helper for YES or NO execution."""
    return kelly_fraction_for_binary(probability, execution_price)


def reduced_kelly_fraction(
    probability: float,
    execution_price: float,
    multiplier: float,
) -> float:
    return max(0.0, kelly_fraction_for_binary(probability, execution_price) * multiplier)


def bounded_sizing_fraction(
    probability: float,
    execution_price: float,
    multiplier: float,
    max_fraction: float,
    position_size: float,
    max_inventory: float,
) -> float:
    base = reduced_kelly_fraction(probability, execution_price, multiplier)
    inventory_headroom = 1.0 - inventory_utilization(position_size, max_inventory)
    return max(0.0, min(max_fraction, base, inventory_headroom))


def bounded_side_sizing_fraction(
    probability: float,
    execution_price: float,
    multiplier: float,
    max_fraction: float,
    position_size: float,
    max_inventory: float,
) -> float:
    return bounded_sizing_fraction(
        probability=probability,
        execution_price=execution_price,
        multiplier=multiplier,
        max_fraction=max_fraction,
        position_size=position_size,
        max_inventory=max_inventory,
    )
