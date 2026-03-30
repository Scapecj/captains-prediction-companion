"""Minimal event timing connector for mention-market live-state checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import time
from typing import Callable

from ..health_models import NormalizedPayloadWrapper
from ..normalizers.mentions import normalize_event_timing_payload
from ..source_manager import AlphaSourceManager


@dataclass(slots=True)
class EventTimingConnector:
    source_manager: AlphaSourceManager | None = None
    now_fn: Callable[[], datetime] = field(default=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.source_manager is None:
            self.source_manager = AlphaSourceManager()

    def evaluate_event_state(
        self,
        *,
        source_id: str,
        close_time: str,
        event_complete: bool = False,
    ) -> NormalizedPayloadWrapper:
        started = time.monotonic()
        now = self.now_fn()
        normalized = normalize_event_timing_payload(
            source_id=source_id,
            close_time=close_time,
            event_complete=event_complete,
            now=now,
        )
        alerts = list(normalized["alerts"])
        health = self.source_manager.evaluate_source_health(
            source="event_timing",
            latency_ms=(time.monotonic() - started) * 1000.0,
            auth_ok=True,
            freshness_seconds=0.0,
            schema_valid=self._is_schema_valid(normalized),
            degraded_mode="manual_review_required" in alerts,
            alerts=alerts,
        )
        return self.source_manager.wrap_payload(
            source_type="event_timing",
            source_id=source_id,
            schema_version="mentions_event_timing_v1",
            normalized_payload=normalized,
            raw_payload_ref=f"timing://{source_id}",
            health=health,
            notes=["mentions_ready_event_timing"],
        )

    @staticmethod
    def _is_schema_valid(payload: dict[str, object]) -> bool:
        required = (
            "source_id",
            "close_time",
            "event_complete",
            "event_still_live",
            "evaluated_at",
            "alerts",
        )
        return all(key in payload for key in required)
