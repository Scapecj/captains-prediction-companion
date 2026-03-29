"""Kelly Criterion bankroll manager for sports prediction markets."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(slots=True)
class KellyResult:
    full_kelly_fraction: float
    recommended_fraction: float  # scaled by kelly_scale
    recommended_stake: float     # in bankroll units
    edge: float
    odds: float
    rationale: str


class KellyBankrollManager:
    """Compute Kelly stakes for binary prediction market bets.

    Parameters
    ----------
    kelly_scale:
        Fraction of full Kelly to use (default 0.25 = quarter Kelly).
    max_fraction:
        Hard cap on stake as fraction of bankroll.
    min_edge:
        Minimum edge (fair_prob - market_prob) required to size a bet.
    """

    def __init__(
        self,
        *,
        kelly_scale: float = 0.25,
        max_fraction: float = 0.25,
        min_edge: float = 0.02,
    ) -> None:
        if not 0 < kelly_scale <= 1:
            raise ValueError("kelly_scale must be in (0, 1]")
        if not 0 < max_fraction <= 1:
            raise ValueError("max_fraction must be in (0, 1]")
        self.kelly_scale = kelly_scale
        self.max_fraction = max_fraction
        self.min_edge = min_edge

    # ------------------------------------------------------------------
    # Core sizing
    # ------------------------------------------------------------------

    def size(
        self,
        fair_probability: float,
        market_probability: float,
        bankroll: float,
        *,
        phase: str = "pre_game",
    ) -> KellyResult:
        """Compute a Kelly-scaled stake.

        For prediction markets priced as probabilities (not decimal odds),
        the implied decimal odds on a YES bet are 1 / market_probability.

        Kelly fraction = (b*p - q) / b
          where b = (1/market_prob) - 1  (net profit per unit staked)
                p = fair_probability
                q = 1 - p
        """
        edge = fair_probability - market_probability
        if edge < self.min_edge:
            return KellyResult(
                full_kelly_fraction=0.0,
                recommended_fraction=0.0,
                recommended_stake=0.0,
                edge=edge,
                odds=0.0,
                rationale=f"Edge {edge:.4f} below min_edge {self.min_edge}",
            )

        if market_probability <= 0 or market_probability >= 1:
            return KellyResult(
                full_kelly_fraction=0.0,
                recommended_fraction=0.0,
                recommended_stake=0.0,
                edge=edge,
                odds=0.0,
                rationale="Market probability out of (0, 1) range",
            )

        b = (1.0 / market_probability) - 1.0  # net odds
        p = fair_probability
        q = 1.0 - p
        full_kelly = (b * p - q) / b if b > 0 else 0.0
        full_kelly = max(0.0, full_kelly)

        # Live markets get additional caution
        scale = self.kelly_scale
        if phase == "live":
            scale = scale * 0.5

        recommended = min(full_kelly * scale, self.max_fraction)
        stake = recommended * bankroll

        return KellyResult(
            full_kelly_fraction=full_kelly,
            recommended_fraction=recommended,
            recommended_stake=stake,
            edge=edge,
            odds=b,
            rationale=(
                f"full_kelly={full_kelly:.4f} × scale={scale:.2f} "
                f"→ {recommended:.4f} (cap={self.max_fraction})"
            ),
        )

    def size_futures(
        self,
        fair_probability: float,
        market_probability: float,
        bankroll: float,
    ) -> KellyResult:
        """Size a futures bet with more conservative defaults."""
        edge = fair_probability - market_probability
        if edge < self.min_edge:
            return KellyResult(
                full_kelly_fraction=0.0,
                recommended_fraction=0.0,
                recommended_stake=0.0,
                edge=edge,
                odds=0.0,
                rationale=f"Edge {edge:.4f} below min_edge {self.min_edge}",
            )

        if market_probability <= 0 or market_probability >= 1:
            return KellyResult(
                full_kelly_fraction=0.0,
                recommended_fraction=0.0,
                recommended_stake=0.0,
                edge=edge,
                odds=0.0,
                rationale="Market probability out of (0, 1) range",
            )

        b = (1.0 / market_probability) - 1.0
        p = fair_probability
        q = 1.0 - p
        full_kelly = max(0.0, (b * p - q) / b) if b > 0 else 0.0

        # Futures cap: 15% of bankroll max, quarter-Kelly
        futures_scale = min(self.kelly_scale, 0.25)
        futures_cap = min(self.max_fraction, 0.15)
        recommended = min(full_kelly * futures_scale, futures_cap)
        stake = recommended * bankroll

        return KellyResult(
            full_kelly_fraction=full_kelly,
            recommended_fraction=recommended,
            recommended_stake=stake,
            edge=edge,
            odds=b,
            rationale=(
                f"futures full_kelly={full_kelly:.4f} × scale={futures_scale:.2f} "
                f"→ {recommended:.4f} (futures_cap={futures_cap})"
            ),
        )


# ---------------------------------------------------------------------------
# Expected value helper
# ---------------------------------------------------------------------------


def compute_ev(fair_probability: float, market_probability: float) -> float:
    """Return edge as simple EV percentage: fair_prob - market_prob."""
    return fair_probability - market_probability


def ev_to_units(
    fair_probability: float,
    market_probability: float,
    stake: float,
) -> float:
    """Return expected profit in currency units for a stake."""
    if market_probability <= 0:
        return 0.0
    decimal_odds = 1.0 / market_probability
    return stake * (fair_probability * decimal_odds - 1.0)
