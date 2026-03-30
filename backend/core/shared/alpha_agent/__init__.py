"""Shared source acquisition, normalization, and diagnostics infrastructure."""

from .health_models import (
    DiagnosticsReport,
    NormalizedPayloadWrapper,
    SourceHealthReport,
    SourceStatus,
)
from .source_manager import AlphaSourceManager
from .connectors import EventTimingConnector, KalshiMarketConnector, MeshTranscriptConnector

__all__ = [
    "AlphaSourceManager",
    "DiagnosticsReport",
    "EventTimingConnector",
    "KalshiMarketConnector",
    "MeshTranscriptConnector",
    "NormalizedPayloadWrapper",
    "SourceHealthReport",
    "SourceStatus",
]
