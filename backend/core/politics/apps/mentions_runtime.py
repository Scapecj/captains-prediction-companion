"""Runtime adapter that merges alpha-agent source payloads for mentions_app."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.shared.alpha_agent.connectors import (
    EventTimingConnector,
    KalshiMarketConnector,
    MeshTranscriptConnector,
)
from core.shared.alpha_agent.health_models import NormalizedPayloadWrapper

from ..models import MentionMarketInput


@dataclass(slots=True)
class MentionRuntimeBundle:
    market: NormalizedPayloadWrapper | None = None
    transcript: NormalizedPayloadWrapper | None = None
    timing: NormalizedPayloadWrapper | None = None

    def merged_context(self, fallback: MentionMarketInput) -> dict[str, Any]:
        context: dict[str, Any] = {
            "market_id": fallback.market_id,
            "title": fallback.title,
            "exact_phrase": fallback.exact_phrase,
            "speaker": fallback.speaker,
            "venue": fallback.venue,
            "close_time": fallback.resolution_window,
            "current_price_yes": fallback.current_price_yes,
            "event_complete": bool(fallback.raw_metadata.get("event_complete", False)),
            "mesh_event_id": fallback.raw_metadata.get("mesh_event_id", ""),
        }

        for wrapper in (self.market, self.transcript, self.timing):
            if wrapper and wrapper.normalized_payload:
                context.update(wrapper.normalized_payload)

        return context

    def source_diagnostics(self) -> dict[str, Any]:
        diagnostics: dict[str, Any] = {}
        for name, wrapper in (
            ("market", self.market),
            ("transcript", self.transcript),
            ("timing", self.timing),
        ):
            if wrapper is None:
                diagnostics[name] = {
                    "status": "NOT_REQUESTED",
                    "notes": [],
                    "payload_sanity_ok": False,
                }
                continue

            health = wrapper.diagnostics.source_health
            diagnostics[name] = {
                "status": health.status.value,
                "source": health.source,
                "alerts": list(health.alerts),
                "auth_ok": health.auth_ok,
                "schema_valid": health.schema_valid,
                "degraded_mode": health.degraded_mode,
                "payload_sanity_ok": wrapper.diagnostics.payload_sanity_ok,
                "notes": list(wrapper.diagnostics.notes),
            }
        return diagnostics


class MentionRuntimeAdapter:
    """Loads normalized alpha-agent inputs needed by mentions_app."""

    def __init__(
        self,
        *,
        market_connector: KalshiMarketConnector | None = None,
        transcript_connector: MeshTranscriptConnector | None = None,
        timing_connector: EventTimingConnector | None = None,
    ) -> None:
        self.market_connector = market_connector or KalshiMarketConnector()
        self.transcript_connector = transcript_connector or MeshTranscriptConnector()
        self.timing_connector = timing_connector or EventTimingConnector()

    def build(self, inp: MentionMarketInput, *, event_type: str) -> MentionRuntimeBundle:
        market_wrapper: NormalizedPayloadWrapper | None = None
        if inp.source == "kalshi" and inp.market_id:
            market_wrapper = self.market_connector.fetch_ticker(inp.market_id)

        merged = MentionRuntimeBundle(market=market_wrapper).merged_context(inp)

        transcript_wrapper: NormalizedPayloadWrapper | None = None
        if merged.get("speaker") and merged.get("exact_phrase"):
            transcript_wrapper = self.transcript_connector.fetch_mentions_context(
                speaker_name=str(merged["speaker"]),
                phrase=str(merged["exact_phrase"]),
                event_type=event_type,
                current_event_id=str(merged.get("mesh_event_id") or "") or None,
                current_event_complete=bool(merged.get("event_complete", False)),
            )

        merged = MentionRuntimeBundle(
            market=market_wrapper,
            transcript=transcript_wrapper,
        ).merged_context(inp)

        timing_wrapper: NormalizedPayloadWrapper | None = None
        if merged.get("close_time"):
            timing_wrapper = self.timing_connector.evaluate_event_state(
                source_id=str(merged.get("market_id") or inp.market_id),
                close_time=str(merged["close_time"]),
                event_complete=bool(merged.get("event_complete", False)),
            )

        return MentionRuntimeBundle(
            market=market_wrapper,
            transcript=transcript_wrapper,
            timing=timing_wrapper,
        )
