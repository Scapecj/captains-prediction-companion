"""Health, diagnostics, and normalized wrapper models for alpha_agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class SourceStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    AUTH_FAILED = "AUTH_FAILED"
    RATE_LIMITED = "RATE_LIMITED"
    PARTIAL_OUTAGE = "PARTIAL_OUTAGE"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


@dataclass(slots=True)
class SourceHealthReport:
    source: str
    status: SourceStatus
    latency_ms: float
    auth_ok: bool
    freshness_seconds: float
    schema_valid: bool
    degraded_mode: bool
    alerts: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")
        if self.freshness_seconds < 0:
            raise ValueError("freshness_seconds must be non-negative")
        if not self.source:
            raise ValueError("source is required")


@dataclass(slots=True)
class DiagnosticsReport:
    source_health: SourceHealthReport
    duplicate_count: int = 0
    payload_sanity_ok: bool = True
    schema_version_detected: str = "v1"
    notes: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class NormalizedPayloadWrapper:
    source_type: str
    source_id: str
    fetched_at: datetime
    freshness_seconds: float
    schema_version: str
    normalized_payload: dict[str, Any]
    raw_payload_ref: str
    diagnostics: DiagnosticsReport

    def __post_init__(self) -> None:
        if not self.source_type:
            raise ValueError("source_type is required")
        if not self.source_id:
            raise ValueError("source_id is required")
        if self.freshness_seconds < 0:
            raise ValueError("freshness_seconds must be non-negative")
        if not self.schema_version:
            raise ValueError("schema_version is required")
