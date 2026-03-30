"""Deterministic source health and normalized wrapper management."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .health_models import (
    DiagnosticsReport,
    NormalizedPayloadWrapper,
    SourceHealthReport,
    SourceStatus,
)


class AlphaSourceManager:
    """Shared helper for source-health classification and payload wrapping."""

    def evaluate_source_health(
        self,
        *,
        source: str,
        latency_ms: float,
        auth_ok: bool,
        freshness_seconds: float,
        schema_valid: bool,
        degraded_mode: bool,
        alerts: list[str] | tuple[str, ...],
    ) -> SourceHealthReport:
        alert_set = set(alerts)
        status = self._classify_status(
            auth_ok=auth_ok,
            freshness_seconds=freshness_seconds,
            schema_valid=schema_valid,
            degraded_mode=degraded_mode,
            alerts=alert_set,
        )
        return SourceHealthReport(
            source=source,
            status=status,
            latency_ms=latency_ms,
            auth_ok=auth_ok,
            freshness_seconds=freshness_seconds,
            schema_valid=schema_valid,
            degraded_mode=degraded_mode,
            alerts=list(alerts),
        )

    def wrap_payload(
        self,
        *,
        source_type: str,
        source_id: str,
        schema_version: str,
        normalized_payload: dict[str, Any],
        raw_payload_ref: str,
        health: SourceHealthReport,
        duplicate_count: int = 0,
        payload_sanity_ok: bool = True,
        notes: list[str] | None = None,
    ) -> NormalizedPayloadWrapper:
        diagnostics = DiagnosticsReport(
            source_health=health,
            duplicate_count=duplicate_count,
            payload_sanity_ok=payload_sanity_ok,
            schema_version_detected=schema_version,
            notes=list(notes or []),
        )
        return NormalizedPayloadWrapper(
            source_type=source_type,
            source_id=source_id,
            fetched_at=datetime.now(UTC),
            freshness_seconds=health.freshness_seconds,
            schema_version=schema_version,
            normalized_payload=normalized_payload,
            raw_payload_ref=raw_payload_ref,
            diagnostics=diagnostics,
        )

    @staticmethod
    def _classify_status(
        *,
        auth_ok: bool,
        freshness_seconds: float,
        schema_valid: bool,
        degraded_mode: bool,
        alerts: set[str],
    ) -> SourceStatus:
        if not auth_ok:
            return SourceStatus.AUTH_FAILED
        if "http_429" in alerts or "rate_limited" in alerts:
            return SourceStatus.RATE_LIMITED
        if not schema_valid:
            return SourceStatus.SCHEMA_DRIFT
        if freshness_seconds > 3600:
            return SourceStatus.STALE
        if "partial_outage" in alerts:
            return SourceStatus.PARTIAL_OUTAGE
        if "manual_review_required" in alerts:
            return SourceStatus.MANUAL_REVIEW_REQUIRED
        if degraded_mode:
            return SourceStatus.DEGRADED
        return SourceStatus.HEALTHY
