"""Workflow and output contract for generic event-market research."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from core.event_markets.models import EventMarketContext, EventMarketPipelinePlan


@dataclass(slots=True)
class EventMarketWorkflowStage:
    """One explicit stage in the event-market workflow."""

    stage: str
    purpose: str
    input_focus: str
    output_focus: str


@dataclass(slots=True)
class EventMarketWorkflowSpec:
    """Reusable workflow definition for event-market research."""

    name: str
    stages: tuple[EventMarketWorkflowStage, ...]
    source_order: tuple[str, ...]
    decision_rule: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EventMarketOutputField:
    """One output field in the standard result shape."""

    name: str
    kind: str
    required: bool
    description: str


@dataclass(slots=True)
class EventMarketOutputSpec:
    """Standard output shape for the event-market pipeline."""

    name: str
    sections: tuple[tuple[str, tuple[EventMarketOutputField, ...]], ...]
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "sections": [
                {
                    "section": section_name,
                    "fields": [asdict(field) for field in fields],
                }
                for section_name, fields in self.sections
            ],
            "notes": self.notes,
        }


def build_event_market_workflow_spec(
    context: EventMarketContext,
    plan: EventMarketPipelinePlan,
) -> EventMarketWorkflowSpec:
    """Build the explicit workflow definition for the given market."""
    domain = context.domain or "general"
    notes = (
        f"Market venue: {plan.venue}. "
        f"Domain: {domain}. "
        "Kalshi or the chosen venue is the market source, Perplexity is the research source, and the scraper skill is the evidence source."
    )

    stages = (
        EventMarketWorkflowStage(
            stage="intake",
            purpose="Identify the market, venue, domain, and contract boundary.",
            input_focus="market title, market id, venue, question, domain",
            output_focus="canonical market context",
        ),
        EventMarketWorkflowStage(
            stage="market",
            purpose="Read the venue itself before looking anywhere else.",
            input_focus="contract wording, resolution rules, price, order book",
            output_focus="venue-grounded market snapshot",
        ),
        EventMarketWorkflowStage(
            stage="research",
            purpose="Use Perplexity to find the authoritative outside source.",
            input_focus="what source actually settles the dispute",
            output_focus="ranked source tree and source summary",
        ),
        EventMarketWorkflowStage(
            stage="evidence",
            purpose="Use the scraper skill to extract the exact supporting facts.",
            input_focus="official pages, transcripts, filings, schedules, scoreboards",
            output_focus="verbatim or structured evidence",
        ),
        EventMarketWorkflowStage(
            stage="pricing",
            purpose="Convert the evidence into fair probability and edge.",
            input_focus="market probability vs. fair probability",
            output_focus="EV, confidence, and stake cap",
        ),
        EventMarketWorkflowStage(
            stage="decision",
            purpose="Apply no-bet filters and produce a final action.",
            input_focus="confidence, stale data, CLV, execution risk",
            output_focus="buy_yes, buy_no, or pass",
        ),
        EventMarketWorkflowStage(
            stage="logging",
            purpose="Store the market source tree and final decision for reuse.",
            input_focus="all intermediate outputs",
            output_focus="audit-ready decision record",
        ),
    )

    return EventMarketWorkflowSpec(
        name="event-market-research",
        stages=stages,
        source_order=plan.source_order,
        decision_rule=plan.decision_rule,
        notes=notes,
    )


def build_event_market_output_spec() -> EventMarketOutputSpec:
    """Build the standard output schema for the event-market pipeline."""
    sections = (
        (
            "market",
            (
                EventMarketOutputField(
                    name="venue",
                    kind="string",
                    required=True,
                    description="Market venue or exchange name.",
                ),
                EventMarketOutputField(
                    name="domain",
                    kind="string",
                    required=True,
                    description="High-level event domain such as sports, politics, macro, earnings, mention, or general.",
                ),
                EventMarketOutputField(
                    name="market_id",
                    kind="string",
                    required=False,
                    description="Venue-specific market identifier when available.",
                ),
                EventMarketOutputField(
                    name="title",
                    kind="string",
                    required=False,
                    description="Human-readable title or question for the market.",
                ),
                EventMarketOutputField(
                    name="question",
                    kind="string",
                    required=False,
                    description="Binary proposition or resolution question.",
                ),
                EventMarketOutputField(
                    name="market_type",
                    kind="string",
                    required=False,
                    description="High-level market type such as binary, spread, total, prop, or future.",
                ),
                EventMarketOutputField(
                    name="market_subtype",
                    kind="string",
                    required=False,
                    description="Narrow subtype used for routing and logging.",
                ),
                EventMarketOutputField(
                    name="url",
                    kind="string",
                    required=False,
                    description="Canonical URL for the market or source page.",
                ),
            ),
        ),
        (
            "sources",
            (
                EventMarketOutputField(
                    name="source_order",
                    kind="array[string]",
                    required=True,
                    description="Ordered source stack used by the pipeline.",
                ),
                EventMarketOutputField(
                    name="resolution_source",
                    kind="string",
                    required=False,
                    description="Primary authoritative source that settles the market if known.",
                ),
                EventMarketOutputField(
                    name="primary_evidence",
                    kind="string",
                    required=False,
                    description="The strongest evidence item supporting the decision.",
                ),
                EventMarketOutputField(
                    name="secondary_evidence",
                    kind="array[string]",
                    required=False,
                    description="Supporting evidence items or citations.",
                ),
                EventMarketOutputField(
                    name="falsifier",
                    kind="string",
                    required=False,
                    description="What would invalidate the thesis or force a pass.",
                ),
            ),
        ),
        (
            "pricing",
            (
                EventMarketOutputField(
                    name="fair_probability",
                    kind="number",
                    required=True,
                    description="Model probability for the side being evaluated.",
                ),
                EventMarketOutputField(
                    name="market_probability",
                    kind="number",
                    required=True,
                    description="Market-implied probability from the venue or consensus book.",
                ),
                EventMarketOutputField(
                    name="edge",
                    kind="number",
                    required=True,
                    description="Fair probability minus market probability.",
                ),
                EventMarketOutputField(
                    name="expected_value",
                    kind="number",
                    required=True,
                    description="Expected value per unit stake after simple pricing.",
                ),
                EventMarketOutputField(
                    name="confidence",
                    kind="number",
                    required=True,
                    description="Confidence score for the estimate, normalized to 0-1.",
                ),
            ),
        ),
        (
            "decision",
            (
                EventMarketOutputField(
                    name="decision",
                    kind="string",
                    required=True,
                    description="Final action: buy_yes, buy_no, pass, or watch.",
                ),
                EventMarketOutputField(
                    name="no_bet_flag",
                    kind="boolean",
                    required=True,
                    description="True when the edge does not survive the filters.",
                ),
                EventMarketOutputField(
                    name="recommended_stake_cap",
                    kind="number",
                    required=False,
                    description="Maximum stake recommended after risk sizing.",
                ),
                EventMarketOutputField(
                    name="notes",
                    kind="string",
                    required=False,
                    description="Short rationale and any execution caveats.",
                ),
            ),
        ),
    )

    return EventMarketOutputSpec(
        name="event-market-output",
        sections=sections,
        notes=(
            "Keep the output compact, audit-friendly, and reusable across sports, politics, macro, earnings, and mention markets."
        ),
    )

