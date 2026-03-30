"""
mentions_app — alpha pipeline for mention-resolution markets.

Handles markets that resolve on WHETHER a specific phrase/word was SAID
in a defined venue (debate, speech, press conference, rally, interview).

Examples:
  "Will Trump say 'tariff' during the State of the Union?"
  "Will Biden mention Ukraine in tonight's debate?"
  "Does Powell say 'recession' at the FOMC press conference?"

Pricing model (TranscriptIntel-first):
  1. LIVE:       If current event transcript is available in MeshAPI:
                   - word found + event over  → P = 0.97
                   - word not found + over    → P = 0.02
                   - word found + in progress → P = 0.90
                   - not found + in progress  → historical_rate × 0.6 (elapsed discount)
  2. HISTORICAL: No live transcript:
                   - Laplace-smoothed rate from past same-type events (MeshAPI)
                   - Blended 60/40 with recent-3 rate
  3. FALLBACK:   MeshAPI unavailable or speaker not indexed:
                   - venue prior only (flat, no edge)

worldmonitor is NOT used in this app. Transcript frequency is the signal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from core.scrapers.kalshi_fetcher import KalshiMarketFetcher, MarketSnapshot
from core.shared.decision_logic_agent import (
    DecisionLogicAgent,
    DecisionLogicInput,
    DecisionLogicOutput,
    rank_by_best_executable_edge,
)

from ..models import MentionMarketInput, MentionMarketOutput
from .mentions_runtime import MentionRuntimeAdapter

MentionRunner = Callable[[MentionMarketInput, MentionRuntimeAdapter | None], MentionMarketOutput]


@dataclass(slots=True)
class MentionEventInput:
    source: str
    market_id: str
    title: str = ""
    speaker: str = ""
    venue: str = ""
    resolution_window: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

# MeshAPI event type mapping from venue strings
_VENUE_TO_EVENT_TYPE: dict[str, str] = {
    "press conference": "press_conference",
    "federal reserve": "press_conference",
    "fomc": "press_conference",
    "press briefing": "press_briefing",
    "state of the union": "address_to_congress",
    "sotu": "address_to_congress",
    "debate": "debate",
    "rally": "rally",
    "speech": "speech",
    "remarks": "remarks",
    "interview": "interview",
    "hearing": "hearing",
    "executive order": "executive_order_announcement",
    "gaggle": "press_gaggle",
}

_DEFAULT_EVENT_TYPE = "remarks"

# Fallback venue priors (used when MeshAPI unavailable)
_VENUE_PRIORS: dict[str, float] = {
    "state of the union": 0.70,
    "sotu": 0.70,
    "press conference": 0.55,
    "debate": 0.55,
    "rally": 0.65,
    "interview": 0.45,
    "speech": 0.50,
    "hearing": 0.40,
    "remarks": 0.45,
}


def _venue_to_event_type(venue: str) -> str:
    lower = venue.lower()
    for key, etype in _VENUE_TO_EVENT_TYPE.items():
        if key in lower:
            return etype
    return _DEFAULT_EVENT_TYPE


def _fallback_venue_prior(venue: str) -> float:
    lower = venue.lower()
    for key, prior in _VENUE_PRIORS.items():
        if key in lower:
            return prior
    return 0.45


def _is_usable_transcript_context(payload: dict[str, Any], diagnostics: dict[str, Any]) -> bool:
    return (
        diagnostics.get("payload_sanity_ok", False)
        and payload.get("events_analyzed", 0) > 0
    )


def _compute_transcript_probability(payload: dict[str, Any]) -> tuple[float, str, str]:
    events_analyzed = int(payload.get("events_analyzed", 0) or 0)
    events_with_phrase = int(payload.get("events_with_phrase", 0) or 0)
    live_event_found = bool(payload.get("current_event_found", False))
    live_word_count = int(payload.get("live_word_count", 0) or 0)
    event_still_live = bool(payload.get("event_still_live", False))
    recent_hits = list(payload.get("recent_hits", []))

    if live_event_found and not event_still_live:
        if live_word_count > 0:
            return 0.97, "high", f"live transcript: word found {live_word_count}x (event complete)"
        return 0.02, "high", "live transcript: word NOT found (event complete)"

    if live_event_found and event_still_live:
        if live_word_count > 0:
            return 0.90, "high", f"live transcript: word found {live_word_count}x so far (event ongoing)"
        hist_rate = events_with_phrase / events_analyzed if events_analyzed > 0 else 0.5
        return hist_rate * 0.6, "medium", (
            f"live: not found yet; historical rate {hist_rate:.0%} discounted for elapsed time"
        )

    if events_analyzed >= 3:
        raw_rate = events_with_phrase / events_analyzed
        smoothed_rate = (events_with_phrase + 1) / (events_analyzed + 2)
        recent_rate = sum(recent_hits) / len(recent_hits) if recent_hits else smoothed_rate
        implied_probability = 0.60 * smoothed_rate + 0.40 * recent_rate
        confidence = "medium" if events_analyzed >= 5 else "low"
        return implied_probability, confidence, (
            f"historical: {events_with_phrase}/{events_analyzed} events ({raw_rate:.0%}), "
            f"recent {recent_rate:.0%}"
        )

    if events_analyzed > 0:
        implied_probability = (events_with_phrase + 1) / (events_analyzed + 2)
        return implied_probability, "low", (
            f"limited history: {events_with_phrase}/{events_analyzed} events — low confidence"
        )

    return 0.50, "low", "no historical data available — flat prior"


def run(
    inp: MentionMarketInput,
    *,
    runtime_adapter: MentionRuntimeAdapter | None = None,
) -> MentionMarketOutput:
    """Full mentions_app pipeline with alpha-agent runtime acquisition."""
    notes: list[str] = []

    if not inp.exact_phrase and not inp.venue and not inp.title:
        return MentionMarketOutput(
            pipeline="mentions_app",
            fair_yes=0.5,
            confidence="low",
            recommendation="watch",
            reasoning="Insufficient market data — no phrase or venue provided.",
            no_bet_flag=True,
            no_bet_reason="missing_phrase_and_venue",
        )

    runtime = runtime_adapter or MentionRuntimeAdapter()
    event_type = _venue_to_event_type(inp.venue)
    bundle = runtime.build(inp, event_type=event_type)
    context = bundle.merged_context(inp)
    source_diagnostics = bundle.source_diagnostics()

    phrase = str(context.get("exact_phrase") or inp.exact_phrase)
    speaker = str(context.get("speaker") or inp.speaker)
    venue = str(context.get("venue") or inp.venue)
    resolution_window = str(context.get("close_time") or inp.resolution_window)
    market_price = context.get("current_price_yes")
    if market_price is None:
        market_price = inp.current_price_yes

    transcript_payload = bundle.transcript.normalized_payload if bundle.transcript else {}
    transcript_diag = source_diagnostics["transcript"]

    if _is_usable_transcript_context(transcript_payload, transcript_diag):
        p_fair, confidence_str, pricing_basis = _compute_transcript_probability(transcript_payload)
        p_fair = max(0.02, min(0.98, p_fair))
        pricing_source = "transcript_connector"
        notes.append(f"transcript_intel: {pricing_basis}")
        notes.append(
            "history="
            f"{transcript_payload['events_with_phrase']}/{transcript_payload['events_analyzed']} events "
            f"| recent={transcript_payload['historical_rate']:.0%}"
        )
        if transcript_payload.get("current_event_found"):
            notes.append(f"live_transcript: {transcript_payload.get('live_word_count', 0)} occurrences so far")
        if transcript_payload.get("data_gaps"):
            notes.append(f"gaps: {', '.join(transcript_payload['data_gaps'])}")
    else:
        p_fair = _fallback_venue_prior(venue)
        confidence_str = "low"
        pricing_source = "venue_prior_fallback"
        notes.append(f"venue_prior={p_fair:.2f}")
        if transcript_diag["status"] != "NOT_REQUESTED":
            notes.append(f"transcript_status={transcript_diag['status']}")
        market_diag = source_diagnostics["market"]
        if market_diag["status"] not in {"HEALTHY", "NOT_REQUESTED"}:
            notes.append(f"market_status={market_diag['status']}")

    if market_price is not None and pricing_source == "venue_prior_fallback":
        anchor_pull = (market_price - p_fair) * 0.25
        p_fair = max(0.02, min(0.98, p_fair + anchor_pull))
        notes.append(f"market_anchor: price={market_price:.0%} pull={anchor_pull:+.2f}")

    if market_price is not None:
        edge_cents = (p_fair - market_price) * 100
        recommendation = "bet_yes" if edge_cents >= 3 else "bet_no" if edge_cents <= -3 else "watch"
    else:
        recommendation = "watch"

    watch_for: list[str] = []
    if context.get("event_still_live") and transcript_payload.get("current_event_found"):
        watch_for.append("live event in progress — transcript updating")
    if resolution_window:
        watch_for.append(f"resolution window: {resolution_window}")
    if phrase:
        watch_for.append(f"exact phrase required: '{phrase}'")
    watch_for = watch_for[:3]

    if _is_usable_transcript_context(transcript_payload, transcript_diag):
        reasoning = (
            f"{speaker or 'Speaker'} said '{phrase}' in "
            f"{transcript_payload['events_with_phrase']}/{transcript_payload['events_analyzed']} "
            f"past {event_type.replace('_', ' ')} events. {notes[0].split(': ', 1)[1]}."
        )
    else:
        reasoning = (
            f"Fair probability for {speaker or 'speaker'} saying '{phrase}' "
            f"at {venue or 'event'} estimated at {p_fair:.0%} (venue prior — no transcript history)."
        )

    return MentionMarketOutput(
        pipeline="mentions_app",
        fair_yes=round(p_fair, 3),
        confidence=confidence_str,
        recommendation=recommendation,
        reasoning=reasoning,
        watch_for=watch_for,
        no_bet_flag=False,
        no_bet_reason="",
        notes=notes,
        source_diagnostics=source_diagnostics,
        runtime_context=context,
    )


def _clamp_probability(value: float | None, default: float) -> float:
    if value is None:
        return default
    try:
        val = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, val))


def _build_decision_input(
    market_id: str,
    mention_output: MentionMarketOutput,
    metadata: dict[str, Any],
) -> DecisionLogicInput:
    context = mention_output.runtime_context or {}
    base_yes = _clamp_probability(
        context.get("current_price_yes"),
        mention_output.fair_yes or 0.5,
    )
    yes_price = base_yes
    no_price = _clamp_probability(1.0 - yes_price, 1.0 - yes_price)
    bid = context.get("bid")
    ask = context.get("ask")
    bid_size = context.get("bid_size") or 0.0
    ask_size = context.get("ask_size") or 0.0
    fees_bps = float(metadata.get("fees_bps", 10.0))
    slippage_estimate = float(metadata.get("slippage_estimate", 0.003))
    position_size = float(metadata.get("position_size", 0.0))
    max_inventory = float(metadata.get("max_inventory", 1.0))
    if max_inventory <= 0:
        max_inventory = 1.0
    event_still_live = bool(context.get("event_still_live"))
    event_complete = bool(context.get("event_complete"))
    effective_confidence = metadata.get("effective_resolution_confidence")
    if effective_confidence is None:
        effective_confidence = 0.95 if not event_still_live else 0.15
    settlement_risk = float(metadata.get("settlement_risk_score", 0.05))
    official_settlement = bool(metadata.get("official_settlement_confirmed", event_complete))
    raw_notes = metadata.get("notes", ("mention_event", market_id))
    if isinstance(raw_notes, str):
        notes = (raw_notes,)
    else:
        notes = tuple(raw_notes)

    return DecisionLogicInput(
        market_type="mention",
        app_source="mentions_app",
        yes_price=yes_price,
        no_price=no_price,
        bid=float(bid) if bid is not None else yes_price,
        ask=float(ask) if ask is not None else yes_price,
        bid_size=float(bid_size),
        ask_size=float(ask_size),
        fair_yes_probability=mention_output.fair_yes,
        fees_bps=fees_bps,
        slippage_estimate=slippage_estimate,
        position_size=position_size,
        max_inventory=max_inventory,
        event_still_live=event_still_live,
        effective_resolution_confidence=effective_confidence,
        settlement_risk_score=settlement_risk,
        official_settlement_confirmed=official_settlement,
        market_id=market_id,
        notes=notes,
    )


def _child_summary_from_decision(
    market_id: str,
    snapshot: MarketSnapshot | None,
    mention_output: MentionMarketOutput,
    decision_output: DecisionLogicOutput,
) -> dict[str, Any]:
    context = mention_output.runtime_context or {}
    word = str(context.get("exact_phrase") or (snapshot and snapshot.exact_phrase) or "")
    yes_price = context.get("current_price_yes")
    if yes_price is None:
        yes_price = mention_output.fair_yes
    yes_price = _clamp_probability(yes_price, 0.5)
    return {
        "child_ticker": market_id,
        "word": word,
        "fair_yes_probability": decision_output.fair_yes_probability,
        "fair_no_probability": decision_output.fair_no_probability,
        "market_yes_price": yes_price,
        "market_no_price": _clamp_probability(1.0 - yes_price, 1.0 - yes_price),
        "edge_yes_after_costs": decision_output.edge_yes_after_costs,
        "edge_no_after_costs": decision_output.edge_no_after_costs,
        "best_side": decision_output.best_side,
        "best_executable_edge": decision_output.best_executable_edge,
        "market_state": decision_output.market_state.value,
        "trade_posture": decision_output.trade_posture.value,
        "confidence": decision_output.confidence,
        "settlement_state": decision_output.settlement_state.value,
        "reject_reason": decision_output.reject_reason,
    }


def run_child_market(
    child_input: MentionMarketInput,
    *,
    mention_runner: MentionRunner | None = None,
    runtime_adapter: MentionRuntimeAdapter | None = None,
    decision_agent: DecisionLogicAgent | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runner = mention_runner or run
    adapter = runtime_adapter
    agent = decision_agent or DecisionLogicAgent()
    output = runner(child_input, runtime_adapter=adapter)
    metadata = metadata or {}
    decision_input = _build_decision_input(child_input.market_id, output, metadata)
    decision_output = agent.evaluate(decision_input)

    child_decision = {
        "best_side": decision_output.best_side,
        "recommended_side": decision_output.recommended_side,
        "best_executable_edge": decision_output.best_executable_edge,
        "edge_yes_after_costs": decision_output.edge_yes_after_costs,
        "edge_no_after_costs": decision_output.edge_no_after_costs,
        "market_state": decision_output.market_state.value,
        "trade_posture": decision_output.trade_posture.value,
        "confidence": decision_output.confidence,
        "settlement_state": decision_output.settlement_state.value,
        "reject_reason": decision_output.reject_reason,
    }

    return {
        "child_ticker": child_input.market_id,
        "market_id": child_input.market_id,
        "mentions": {
            "fair_yes": output.fair_yes,
            "confidence": output.confidence,
            "recommendation": output.recommendation,
            "reasoning": output.reasoning,
        },
        "decision": child_decision,
        "source_diagnostics": output.source_diagnostics,
        "runtime_context": output.runtime_context,
        "market_state": decision_output.market_state.value,
        "trade_posture": decision_output.trade_posture.value,
        "recommended_side": decision_output.recommended_side,
        "best_executable_edge": decision_output.best_executable_edge,
    }


def run_event_board(
    event_input: MentionEventInput,
    *,
    runtime_adapter: MentionRuntimeAdapter | None = None,
    market_fetcher: KalshiMarketFetcher | None = None,
    mention_runner: MentionRunner | None = None,
    decision_agent: DecisionLogicAgent | None = None,
) -> dict[str, Any]:
    runner = mention_runner or run
    adapter = runtime_adapter or MentionRuntimeAdapter()
    agent = decision_agent or DecisionLogicAgent()
    fetcher = market_fetcher or KalshiMarketFetcher()

    try:
        snapshots = fetcher.fetch_series(event_input.market_id)
    except Exception as exc:
        return {
            "parent_event_ticker": event_input.market_id,
            "children": [],
            "ranked_summary": [],
            "source_diagnostics": {
                "event_fetch": {"error": str(exc)},
            },
            "runtime_context": {
                "event_market_id": event_input.market_id,
                "child_count": 0,
            },
        }

    children: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for snapshot in snapshots:
        if snapshot.ticker == event_input.market_id:
            continue
        if not snapshot.exact_phrase:
            continue
        child_input = MentionMarketInput(
            source=event_input.source,
            market_id=snapshot.ticker,
            title=snapshot.title or event_input.title,
            exact_phrase=snapshot.exact_phrase,
            speaker=snapshot.speaker or event_input.speaker,
            venue=snapshot.venue or event_input.venue,
            resolution_window=snapshot.close_time or event_input.resolution_window,
            current_price_yes=snapshot.current_price_yes,
            raw_metadata=event_input.metadata,
        )
        mention_output = runner(child_input, runtime_adapter=adapter)
        decision_input = _build_decision_input(snapshot.ticker, mention_output, event_input.metadata)
        decision_output = agent.evaluate(decision_input)
        records.append({
            "ticker": snapshot.ticker,
            "snapshot": snapshot,
            "mention_output": mention_output,
            "decision_output": decision_output,
        })
        children.append({"child_ticker": snapshot.ticker})

    if not records:
        return {
            "parent_event_ticker": event_input.market_id,
            "children": [],
            "ranked_summary": [],
            "source_diagnostics": {
                "event_fetch": {"child_count": 0},
            },
            "runtime_context": {
                "event_market_id": event_input.market_id,
                "child_count": 0,
            },
        }

    decision_map = {id(rec["decision_output"]): rec for rec in records}
    ranked = rank_by_best_executable_edge([rec["decision_output"] for rec in records])
    summary: list[dict[str, Any]] = []
    child_sources: list[dict[str, Any]] = []
    for decision in ranked:
        rec = decision_map[id(decision)]
        summary.append(_child_summary_from_decision(
            market_id=rec["ticker"],
            snapshot=rec["snapshot"],
            mention_output=rec["mention_output"],
            decision_output=decision,
        ))
        child_sources.append({
            "market_id": rec["ticker"],
            "diagnostics": rec["mention_output"].source_diagnostics,
        })

    return {
        "parent_event_ticker": event_input.market_id,
        "children": [child["child_ticker"] for child in children],
        "ranked_summary": summary,
        "source_diagnostics": {
            "event_fetch": {"child_count": len(records)},
            "children": child_sources,
        },
        "runtime_context": {
            "event_market_id": event_input.market_id,
            "child_count": len(records),
        },
    }
