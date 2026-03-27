"""Reusable sports intelligence helpers for CLV, consensus, gating, and calibration."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from dataclasses import replace
from statistics import median
from typing import Any, Callable, Iterable, Sequence

from core.sports.models import SportsMarketQuote


@dataclass(slots=True)
class ClosingLineRecord:
    timestamp: str
    league: str
    season: str | int | None
    event_id: str
    market_id: str
    market_type: str
    market_subtype: str
    phase: str
    side: str
    stake: float
    bankroll_snapshot: float
    fair_probability: float
    market_probability: float
    closing_price: float | None = None
    closing_probability: float | None = None
    clv: float | None = None
    market_state_label: str | None = None
    result_if_known: str | None = None
    notes: str = ""


class ClosingLineTracker:
    """Track entry and closing prices for CLV analysis."""

    def __init__(self) -> None:
        self.records: list[ClosingLineRecord] = []

    def record(self, record: ClosingLineRecord) -> None:
        self.records.append(record)

    @staticmethod
    def compute_clv(entry_probability: float, closing_probability: float, side: str) -> float:
        if side.upper() == "YES":
            return closing_probability - entry_probability
        if side.upper() == "NO":
            return entry_probability - closing_probability
        raise ValueError(f"Unsupported side: {side}")

    def attach_clv(self, record: ClosingLineRecord) -> ClosingLineRecord:
        if record.closing_probability is None:
            return record
        clv = self.compute_clv(record.market_probability, record.closing_probability, record.side)
        return replace(record, clv=clv)

    def summarize_by(self, key_fn: Callable[[ClosingLineRecord], str]) -> dict[str, dict[str, float]]:
        buckets: dict[str, list[float]] = defaultdict(list)
        for record in self.records:
            if record.clv is not None:
                buckets[key_fn(record)].append(record.clv)
        return {
            key: {
                "count": float(len(values)),
                "avg_clv": sum(values) / len(values),
                "median_clv": median(values),
            }
            for key, values in buckets.items()
            if values
        }


@dataclass(slots=True)
class ConsensusResult:
    consensus_probability: float
    per_venue: dict[str, float]
    stale_venues: tuple[str, ...] = ()
    spread: float = 0.0


class ConsensusPriceEngine:
    """Build consensus probabilities from connected venues."""

    def __init__(self, stale_price_threshold_prob: float = 0.02) -> None:
        self.stale_price_threshold_prob = stale_price_threshold_prob

    @staticmethod
    def _prob_from_quote(quote: SportsMarketQuote | dict[str, Any]) -> float:
        if isinstance(quote, SportsMarketQuote):
            return quote.implied_probability
        if "implied_probability" in quote:
            return float(quote["implied_probability"])
        if "price" in quote:
            return float(quote["price"])
        raise ValueError("Quote must include implied_probability or price")

    def build_consensus(self, quotes: Sequence[SportsMarketQuote | dict[str, Any]]) -> ConsensusResult:
        if not quotes:
            raise ValueError("At least one quote is required")
        per_venue: dict[str, float] = {}
        for quote in quotes:
            venue = quote.venue if isinstance(quote, SportsMarketQuote) else str(quote.get("venue", "unknown"))
            per_venue[venue] = self._prob_from_quote(quote)
        consensus = median(per_venue.values())
        stale_venues = tuple(
            venue
            for venue, probability in per_venue.items()
            if abs(probability - consensus) > self.stale_price_threshold_prob
        )
        spread = max(per_venue.values()) - min(per_venue.values())
        return ConsensusResult(
            consensus_probability=consensus,
            per_venue=per_venue,
            stale_venues=stale_venues,
            spread=spread,
        )


@dataclass(slots=True)
class InjuryGateDecision:
    action: str
    reason: str
    confidence: float


class InjuryNewsGate:
    """Block, delay, or downgrade trades when information quality is weak."""

    def assess(
        self,
        *,
        league: str,
        injury_confirmed: bool,
        lineup_confirmed: bool,
        weather_confirmed: bool = True,
        news_quality: str = "confirmed",
        strict_leagues: Iterable[str] = ("NFL", "NCAA_FB", "NBA", "NCAA_BB", "MLB", "NCAA_BASEBALL"),
    ) -> InjuryGateDecision:
        strict = league in set(strict_leagues)
        if strict and not (injury_confirmed and lineup_confirmed and weather_confirmed):
            return InjuryGateDecision(
                action="block",
                reason="Strict league with incomplete injury/lineup/weather confirmation",
                confidence=0.9,
            )
        if news_quality != "confirmed":
            return InjuryGateDecision(
                action="delay",
                reason="News inputs are not fully confirmed",
                confidence=0.7,
            )
        return InjuryGateDecision(action="allow", reason="Inputs confirmed", confidence=0.95)


@dataclass(slots=True)
class MonteCarloResult:
    fair_probability: float
    distribution: list[float] = field(default_factory=list)
    runs: int = 0


class MonteCarloPricer:
    """Generic Monte Carlo pricing helper."""

    def price(
        self,
        sampler: Callable[[], bool | float],
        *,
        runs: int,
    ) -> MonteCarloResult:
        outcomes: list[float] = []
        wins = 0
        for _ in range(runs):
            sample = sampler()
            if isinstance(sample, bool):
                wins += int(sample)
                outcomes.append(1.0 if sample else 0.0)
            else:
                outcomes.append(float(sample))
                wins += int(float(sample) >= 0.5)
        fair_probability = wins / runs if runs else 0.0
        return MonteCarloResult(fair_probability=fair_probability, distribution=outcomes, runs=runs)


@dataclass(slots=True)
class CalibrationBucket:
    predicted_probability: float
    actual_win_rate: float
    count: int


class ModelCalibrationReporter:
    """Measure calibration by probability buckets and phase/league slices."""

    @staticmethod
    def bucket_predictions(predictions: Sequence[float], results: Sequence[bool], bucket_size: float = 0.05) -> list[CalibrationBucket]:
        if len(predictions) != len(results):
            raise ValueError("predictions and results must have the same length")
        buckets: dict[float, list[int]] = defaultdict(list)
        for prediction, result in zip(predictions, results, strict=True):
            bucket = round(prediction / bucket_size) * bucket_size
            buckets[bucket].append(int(result))
        return [
            CalibrationBucket(
                predicted_probability=bucket,
                actual_win_rate=sum(values) / len(values),
                count=len(values),
            )
            for bucket, values in sorted(buckets.items())
            if values
        ]


@dataclass(slots=True)
class NoBetDecision:
    should_skip: bool
    reasons: tuple[str, ...] = ()


class NoBetClassifier:
    """Rule-based no-bet gate for weak or noisy edges."""

    def __init__(
        self,
        *,
        min_edge: float = 0.02,
        min_confidence: float = 0.55,
        max_staleness_prob_gap: float = 0.02,
    ) -> None:
        self.min_edge = min_edge
        self.min_confidence = min_confidence
        self.max_staleness_prob_gap = max_staleness_prob_gap

    def evaluate(
        self,
        *,
        edge: float,
        confidence: float,
        stale_price_gap: float = 0.0,
        info_quality: str = "confirmed",
        clv_history: float | None = None,
        market_state_label: str | None = None,
    ) -> NoBetDecision:
        reasons: list[str] = []
        if edge < self.min_edge:
            reasons.append("edge below threshold")
        if confidence < self.min_confidence:
            reasons.append("confidence below threshold")
        if stale_price_gap > self.max_staleness_prob_gap:
            reasons.append("price is stale")
        if info_quality != "confirmed":
            reasons.append("info quality not confirmed")
        if clv_history is not None and clv_history < 0:
            reasons.append("negative CLV history")
        if market_state_label in {"midday", "live"} and edge < self.min_edge * 1.5:
            reasons.append("insufficient live edge")
        return NoBetDecision(should_skip=bool(reasons), reasons=tuple(reasons))
