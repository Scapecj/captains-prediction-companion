"""
TranscriptIntelFetcher — MeshAPI-backed transcript intelligence for mention markets.

Replaces worldmonitor for mention-resolution markets.

Pricing logic:
  1. LIVE: if current event transcript is available and word IS found → P = 0.97
  2. LIVE: if current event transcript is available and word NOT found AND event over → P = 0.02
  3. HISTORICAL: no live transcript → use historical_rate from past same-type events
     P_base = (events_with_word / total_events) with smoothing
     Adjusted by: recency weight (recent events count more)

Usage:
    fetcher = TranscriptIntelFetcher()
    report = fetcher.fetch(
        speaker_name="Powell",
        phrase="Tariff",
        event_type="press_conference",
        current_event_id=None,   # set if live event is known
    )
    # report.implied_probability — use directly in mentions_app
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

from .mesh_client import (
    get_speakers,
    get_speaker_events,
    get_segments,
    count_word_in_segments,
    get_events,
)

# ---------------------------------------------------------------------------
# Known speaker IDs (cache to avoid repeated lookups)
# ---------------------------------------------------------------------------

_KNOWN_SPEAKERS: dict[str, str] = {
    "powell":  "be52c484-cf70-42f7-a89c-48bfc11780de",
    "jerome powell": "be52c484-cf70-42f7-a89c-48bfc11780de",
    "trump":   "381194fe-4856-4945-9e49-9809be82e924",
    "donald trump": "381194fe-4856-4945-9e49-9809be82e924",
    "biden":   "e65f3f72-c7b2-48f2-bf64-1a742839668b",
    "vance":   "b94665da-eff1-44a0-a0f5-cc0bb0672b9c",
    "leavitt": "755b139b-94df-48bd-a03e-3fddf96b02cd",
}


def _resolve_speaker_id(speaker_name: str) -> str | None:
    key = speaker_name.lower().strip()
    if key in _KNOWN_SPEAKERS:
        return _KNOWN_SPEAKERS[key]
    # Try last name
    last = key.split()[-1] if key else ""
    if last in _KNOWN_SPEAKERS:
        return _KNOWN_SPEAKERS[last]
    return None


# ---------------------------------------------------------------------------
# Output model
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class TranscriptIntelReport:
    speaker_name: str
    phrase: str
    event_type: str

    # Historical analysis
    events_analyzed: int = 0
    events_with_phrase: int = 0
    historical_rate: float = 0.0            # events_with_phrase / events_analyzed
    avg_mentions_per_event: float = 0.0     # avg count when present
    recent_rate: float = 0.0               # rate in last 3 events

    # Live transcript (if current event found)
    live_event_found: bool = False
    live_event_id: str = ""
    live_event_title: str = ""
    live_word_count: int = 0
    live_event_complete: bool = False       # True if event is over

    # Pricing output
    implied_probability: float = 0.0
    confidence: str = "low"                 # "low" | "medium" | "high"
    pricing_basis: str = ""                 # explanation of how P was derived
    data_gaps: list[str] = field(default_factory=list)
    error: str | None = None

    # Cache
    cache_hit: bool = False


# ---------------------------------------------------------------------------
# Simple in-memory cache
# ---------------------------------------------------------------------------

_CACHE: dict[str, tuple[TranscriptIntelReport, float]] = {}
_CACHE_TTL = 900  # 15 min for historical; live events use shorter TTL


def _cache_key(speaker: str, phrase: str, event_type: str) -> str:
    return f"{speaker.lower()}:{phrase.lower()}:{event_type}"


# ---------------------------------------------------------------------------
# Main fetcher
# ---------------------------------------------------------------------------

class TranscriptIntelFetcher:

    def fetch(
        self,
        speaker_name: str,
        phrase: str,
        event_type: str = "press_conference",
        current_event_id: str | None = None,
        current_event_complete: bool = False,
        max_historical_events: int = 10,
        ttl: int = _CACHE_TTL,
    ) -> TranscriptIntelReport:
        """
        Fetch transcript intelligence for a mention market.

        Args:
            speaker_name:           e.g. "Powell", "Trump"
            phrase:                 The word/phrase to check (e.g. "Tariff")
            event_type:             Filter to this event type for historical base rate
            current_event_id:       MeshAPI event_id if today's event is already indexed
            current_event_complete: True if the live event is already over
            max_historical_events:  How many past events to analyze
        """
        ck = _cache_key(speaker_name, phrase, event_type)
        if ck in _CACHE:
            report, ts = _CACHE[ck]
            if time.monotonic() - ts < ttl:
                report.cache_hit = True
                return report

        speaker_id = _resolve_speaker_id(speaker_name)
        gaps: list[str] = []

        if not speaker_id:
            gaps.append(f"speaker_id_not_found:{speaker_name}")
            r = TranscriptIntelReport(
                speaker_name=speaker_name, phrase=phrase, event_type=event_type,
                implied_probability=0.5, confidence="low",
                pricing_basis="speaker not indexed in MeshAPI — using flat prior",
                data_gaps=gaps,
            )
            _CACHE[ck] = (r, time.monotonic())
            return r

        # --- Step 1: live event check ---
        live_found = False
        live_count = 0
        live_event_id = ""
        live_event_title = ""

        if current_event_id:
            try:
                segs = get_segments(current_event_id)
                live_count = count_word_in_segments(segs, phrase, speaker_id)
                live_found = True
                live_event_id = current_event_id
            except Exception as e:
                gaps.append(f"live_segment_fetch_failed:{e}")

        # --- Step 2: historical analysis ---
        events_analyzed = 0
        events_with_phrase = 0
        counts_when_present: list[int] = []
        recent_counts: list[int] = []  # last 3 same-type events

        try:
            all_events = get_speaker_events(speaker_id)
            # Filter to same event type
            same_type = [
                e for e in all_events
                if e.get("event_type") == event_type
                and (not current_event_id or e.get("event_id") != current_event_id)
            ][:max_historical_events]

            for i, ev in enumerate(same_type):
                eid = ev["event_id"]
                try:
                    segs = get_segments(eid)
                    count = count_word_in_segments(segs, phrase, speaker_id)
                    events_analyzed += 1
                    if count > 0:
                        events_with_phrase += 1
                        counts_when_present.append(count)
                    if i < 3:
                        recent_counts.append(1 if count > 0 else 0)
                except Exception:
                    gaps.append(f"segment_fetch_failed:{eid[:8]}")
        except Exception as e:
            gaps.append(f"event_list_failed:{e}")

        # --- Step 3: compute implied probability ---
        if live_found and current_event_complete:
            # Hard answer: event is over, transcript exists
            if live_count > 0:
                p = 0.97
                basis = f"live transcript: word found {live_count}x (event complete)"
                conf = "high"
            else:
                p = 0.02
                basis = "live transcript: word NOT found (event complete)"
                conf = "high"

        elif live_found and not current_event_complete:
            # Event in progress — word found so far
            if live_count > 0:
                p = 0.90
                basis = f"live transcript: word found {live_count}x so far (event ongoing)"
                conf = "high"
            else:
                # Not found yet but event isn't over — use historical to estimate remainder
                hist_rate = events_with_phrase / events_analyzed if events_analyzed > 0 else 0.5
                p = hist_rate * 0.6  # discount: part of event already passed without mention
                basis = f"live: not found yet; historical rate {hist_rate:.0%} discounted for elapsed time"
                conf = "medium"

        elif events_analyzed >= 3:
            # No live transcript — use historical base rate with Laplace smoothing
            raw_rate = events_with_phrase / events_analyzed
            # Laplace +1/+2 smoothing
            p = (events_with_phrase + 1) / (events_analyzed + 2)
            recent_rate = sum(recent_counts) / len(recent_counts) if recent_counts else p
            # Blend: 60% historical, 40% recent
            p = 0.60 * p + 0.40 * recent_rate
            basis = f"historical: {events_with_phrase}/{events_analyzed} events ({raw_rate:.0%}), recent {recent_rate:.0%}"
            conf = "medium" if events_analyzed >= 5 else "low"

        elif events_analyzed > 0:
            raw_rate = events_with_phrase / events_analyzed
            p = (events_with_phrase + 1) / (events_analyzed + 2)
            basis = f"limited history: {events_with_phrase}/{events_analyzed} events — low confidence"
            conf = "low"

        else:
            p = 0.50
            basis = "no historical data available — flat prior"
            conf = "low"
            gaps.append("no_historical_events_found")

        hist_rate = events_with_phrase / events_analyzed if events_analyzed > 0 else 0.0
        recent_rate_val = sum(recent_counts) / len(recent_counts) if recent_counts else hist_rate
        avg_when_present = sum(counts_when_present) / len(counts_when_present) if counts_when_present else 0.0

        report = TranscriptIntelReport(
            speaker_name=speaker_name,
            phrase=phrase,
            event_type=event_type,
            events_analyzed=events_analyzed,
            events_with_phrase=events_with_phrase,
            historical_rate=round(hist_rate, 3),
            avg_mentions_per_event=round(avg_when_present, 1),
            recent_rate=round(recent_rate_val, 3),
            live_event_found=live_found,
            live_event_id=live_event_id,
            live_event_title=live_event_title,
            live_word_count=live_count,
            live_event_complete=current_event_complete,
            implied_probability=round(min(0.98, max(0.02, p)), 3),
            confidence=conf,
            pricing_basis=basis,
            data_gaps=gaps,
            error=None,
            cache_hit=False,
        )

        _CACHE[ck] = (report, time.monotonic())
        return report
