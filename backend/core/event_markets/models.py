"""Typed models for generic event-market research plans."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class EventMarketContext:
    """Minimal context needed to build a research plan."""

    venue: str
    market_id: str | None = None
    title: str | None = None
    question: str | None = None
    domain: str | None = None
    market_type: str | None = None
    market_subtype: str | None = None
    url: str | None = None
    resolution_source: str | None = None
    resolution_time: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EventMarketPipelineStep:
    """One stage in the event-market process."""

    stage: str
    source: str
    purpose: str
    notes: str = ""


@dataclass(slots=True)
class EventMarketPipelinePlan:
    """Reusable research plan for an event market."""

    venue: str
    domain: str
    source_order: tuple[str, ...]
    steps: tuple[EventMarketPipelineStep, ...]
    primary_source: str
    research_source: str
    evidence_source: str
    decision_rule: str
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain data for APIs and prompts."""
        return asdict(self)
