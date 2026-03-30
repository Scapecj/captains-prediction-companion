"""Concrete Mesh transcript connector for mention evidence inputs."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Callable

from core.scrapers.transcript_intel import _resolve_speaker_id
from core.scrapers.mesh_client import get_segments, get_speaker_events, count_word_in_segments

from ..health_models import NormalizedPayloadWrapper
from ..normalizers.mentions import normalize_transcript_mentions_payload
from ..source_manager import AlphaSourceManager
from ..diagnostics.connector_diagnostics import classify_exception


@dataclass(slots=True)
class MeshTranscriptConnector:
    source_manager: AlphaSourceManager | None = None
    resolve_speaker_id_fn: Callable[[str], str | None] = _resolve_speaker_id
    get_speaker_events_fn: Callable[[str], list[dict]] = get_speaker_events
    get_segments_fn: Callable[[str], list[dict]] = get_segments
    count_word_fn: Callable[[list[dict], str, str | None], int] = count_word_in_segments
    auth_key_env: str = "MESH_API_KEY"

    def __post_init__(self) -> None:
        if self.source_manager is None:
            self.source_manager = AlphaSourceManager()

    def fetch_mentions_context(
        self,
        *,
        speaker_name: str,
        phrase: str,
        event_type: str,
        current_event_id: str | None = None,
        current_event_complete: bool = False,
        max_historical_events: int = 10,
    ) -> NormalizedPayloadWrapper:
        started = time.monotonic()
        source_id = f"{speaker_name}:{phrase}:{event_type}"

        if not os.environ.get(self.auth_key_env):
            health = self.source_manager.evaluate_source_health(
                source="mesh_transcripts",
                latency_ms=0.0,
                auth_ok=False,
                freshness_seconds=0.0,
                schema_valid=False,
                degraded_mode=False,
                alerts=[],
            )
            return self.source_manager.wrap_payload(
                source_type="transcript",
                source_id=source_id,
                schema_version="mentions_transcript_v1",
                normalized_payload={},
                raw_payload_ref=f"mesh://{source_id}",
                health=health,
                payload_sanity_ok=False,
                notes=[f"{self.auth_key_env} not set"],
            )

        try:
            speaker_id = self.resolve_speaker_id_fn(speaker_name)
            if not speaker_id:
                raise RuntimeError(f"speaker_id_not_found:{speaker_name}")

            all_events = self.get_speaker_events_fn(speaker_id)
            same_type = [
                event
                for event in all_events
                if event.get("event_type") == event_type
                and (not current_event_id or event.get("event_id") != current_event_id)
            ][:max_historical_events]

            current_event_found = False
            live_word_count = 0
            if current_event_id:
                segments = self.get_segments_fn(current_event_id)
                live_word_count = self.count_word_fn(segments, phrase, speaker_id)
                current_event_found = True

            events_analyzed = 0
            events_with_phrase = 0
            recent_hits: list[int] = []
            matching_event_ids: list[str] = []
            data_gaps: list[str] = []

            for idx, event in enumerate(same_type):
                event_id = event.get("event_id")
                if not event_id:
                    continue
                try:
                    segments = self.get_segments_fn(event_id)
                    count = self.count_word_fn(segments, phrase, speaker_id)
                    events_analyzed += 1
                    if count > 0:
                        events_with_phrase += 1
                        matching_event_ids.append(event_id)
                    if idx < 3:
                        recent_hits.append(1 if count > 0 else 0)
                except Exception:
                    data_gaps.append(f"segment_fetch_failed:{event_id}")

            normalized = normalize_transcript_mentions_payload(
                speaker_name=speaker_name,
                speaker_id=speaker_id,
                phrase=phrase,
                event_type=event_type,
                current_event_id=current_event_id,
                current_event_found=current_event_found,
                current_event_complete=current_event_complete,
                live_word_count=live_word_count,
                events_analyzed=events_analyzed,
                events_with_phrase=events_with_phrase,
                recent_hits=recent_hits,
                matching_event_ids=matching_event_ids,
                data_gaps=data_gaps,
            )
            alerts = ["partial_outage"] if data_gaps else []
            latency_ms = (time.monotonic() - started) * 1000.0
            health = self.source_manager.evaluate_source_health(
                source="mesh_transcripts",
                latency_ms=latency_ms,
                auth_ok=True,
                freshness_seconds=0.0,
                schema_valid=self._is_schema_valid(normalized),
                degraded_mode=bool(data_gaps),
                alerts=alerts,
            )
            return self.source_manager.wrap_payload(
                source_type="transcript",
                source_id=source_id,
                schema_version="mentions_transcript_v1",
                normalized_payload=normalized,
                raw_payload_ref=f"mesh://speaker/{speaker_id}",
                health=health,
                notes=["mentions_ready_transcript_payload"],
            )
        except Exception as exc:
            latency_ms = (time.monotonic() - started) * 1000.0
            auth_ok, alerts, degraded_mode = classify_exception(exc)
            health = self.source_manager.evaluate_source_health(
                source="mesh_transcripts",
                latency_ms=latency_ms,
                auth_ok=auth_ok,
                freshness_seconds=0.0,
                schema_valid=False,
                degraded_mode=degraded_mode,
                alerts=alerts,
            )
            return self.source_manager.wrap_payload(
                source_type="transcript",
                source_id=source_id,
                schema_version="mentions_transcript_v1",
                normalized_payload={},
                raw_payload_ref=f"mesh://{source_id}",
                health=health,
                payload_sanity_ok=False,
                notes=[str(exc)],
            )

    @staticmethod
    def _is_schema_valid(payload: dict[str, object]) -> bool:
        required = (
            "speaker_name",
            "speaker_id",
            "phrase",
            "event_type",
            "current_event_found",
            "event_still_live",
            "live_word_count",
            "events_analyzed",
            "events_with_phrase",
            "historical_rate",
        )
        return all(key in payload for key in required)
