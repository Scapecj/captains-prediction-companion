"""Normalization helpers for mentions_app source payloads."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..diagnostics.connector_diagnostics import safe_float


def normalize_kalshi_market_payload(snapshot: Any) -> dict[str, Any]:
    raw = getattr(snapshot, "raw", {}) or {}
    bid = snapshot.yes_bid / 100.0 if getattr(snapshot, "yes_bid", 0) else safe_float(raw.get("yes_bid_dollars"))
    ask = snapshot.yes_ask / 100.0 if getattr(snapshot, "yes_ask", 0) else safe_float(raw.get("yes_ask_dollars"))
    return {
        "market_id": snapshot.ticker,
        "ticker": snapshot.ticker,
        "series_ticker": snapshot.series_ticker,
        "title": snapshot.title,
        "exact_phrase": snapshot.exact_phrase,
        "speaker": snapshot.speaker,
        "venue": snapshot.venue,
        "resolution_rules": snapshot.resolution_rules,
        "close_time": snapshot.close_time,
        "current_price_yes": snapshot.current_price_yes,
        "bid": bid,
        "ask": ask,
        "bid_size": safe_float(raw.get("yes_bid_size_fp")),
        "ask_size": safe_float(raw.get("yes_ask_size_fp")),
        "last_price": snapshot.last_price / 100.0 if snapshot.last_price else safe_float(raw.get("last_price_dollars")),
        "volume": snapshot.volume,
        "open_interest": snapshot.open_interest,
        "domain": snapshot.domain,
    }


def normalize_transcript_mentions_payload(
    *,
    speaker_name: str,
    speaker_id: str,
    phrase: str,
    event_type: str,
    current_event_id: str | None,
    current_event_found: bool,
    current_event_complete: bool,
    live_word_count: int,
    events_analyzed: int,
    events_with_phrase: int,
    recent_hits: list[int],
    matching_event_ids: list[str],
    data_gaps: list[str],
) -> dict[str, Any]:
    historical_rate = (events_with_phrase / events_analyzed) if events_analyzed else 0.0
    return {
        "speaker_name": speaker_name,
        "speaker_id": speaker_id,
        "phrase": phrase,
        "event_type": event_type,
        "current_event_id": current_event_id or "",
        "current_event_found": current_event_found,
        "current_event_complete": current_event_complete,
        "event_still_live": current_event_found and not current_event_complete,
        "live_word_count": live_word_count,
        "events_analyzed": events_analyzed,
        "events_with_phrase": events_with_phrase,
        "historical_rate": round(historical_rate, 4),
        "recent_hits": list(recent_hits),
        "matching_event_ids": list(matching_event_ids),
        "data_gaps": list(data_gaps),
    }


def normalize_event_timing_payload(
    *,
    source_id: str,
    close_time: str,
    event_complete: bool,
    now: datetime,
) -> dict[str, Any]:
    parsed_close: datetime | None = None
    seconds_to_close: float | None = None
    alerts: list[str] = []
    event_still_live = not event_complete

    if close_time:
        try:
            normalized_close_time = close_time.replace("Z", "+00:00")
            parsed_close = datetime.fromisoformat(normalized_close_time)
            if parsed_close.tzinfo is None:
                parsed_close = parsed_close.replace(tzinfo=UTC)
            seconds_to_close = (parsed_close - now).total_seconds()
            if seconds_to_close <= 0:
                event_still_live = False
        except ValueError:
            alerts.append("manual_review_required")

    return {
        "source_id": source_id,
        "close_time": close_time,
        "event_complete": event_complete,
        "event_still_live": event_still_live,
        "seconds_to_close": seconds_to_close,
        "evaluated_at": now.isoformat(),
        "alerts": alerts,
    }
