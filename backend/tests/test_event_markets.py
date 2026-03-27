from core.event_markets import (
    EventMarketContext,
    build_event_market_output_spec,
    build_event_market_pipeline,
    build_event_market_workflow_spec,
    build_market_source_order,
    canonicalize_market_venue,
    normalize_event_domain,
)


def test_event_market_source_order_defaults_to_kalshi_then_research_then_scraper():
    assert build_market_source_order("Kalshi") == (
        "Kalshi",
        "Perplexity",
        "Playwright Scraper Skill",
    )
    assert build_market_source_order("  polymarket  ") == (
        "Polymarket",
        "Perplexity",
        "Playwright Scraper Skill",
    )


def test_event_market_name_normalization_is_cheap_and_generic():
    assert canonicalize_market_venue("KALSHI EXCHANGE") == "Kalshi"
    assert normalize_event_domain("MENTIONS") == "mention"
    assert normalize_event_domain("ECONOMICS") == "macro"


def test_event_market_pipeline_keeps_the_process_simple():
    plan = build_event_market_pipeline(
        EventMarketContext(
            venue="Kalshi",
            market_id="KXTEST123",
            title="Will the event resolve YES?",
            question="Will the event resolve YES?",
            domain="politics",
            market_type="binary",
            market_subtype="general_event",
            url="https://example.com/market",
            metadata={"notes": "keep it cheap", "source_hint": "official"},
        )
    )

    assert plan.venue == "Kalshi"
    assert plan.domain == "politics"
    assert plan.source_order == (
        "Kalshi",
        "Perplexity",
        "Playwright Scraper Skill",
    )
    assert [step.stage for step in plan.steps] == [
        "market",
        "research",
        "evidence",
        "decision",
    ]
    assert plan.primary_source == "Kalshi"
    assert plan.research_source == "Perplexity"
    assert plan.evidence_source == "Playwright Scraper Skill"
    assert "Market first" in plan.decision_rule
    assert plan.metadata["context"]["source_hint"] == "official"


def test_event_market_workflow_and_output_contract_are_explicit():
    context = EventMarketContext(
        venue="Kalshi",
        domain="sports",
        market_id="KXSPORTS42",
        title="Will the home team win?",
        question="Will the home team win?",
        market_type="binary",
        market_subtype="sports_moneyline",
        metadata={"notes": "Use the cheapest usable truth source."},
    )
    plan = build_event_market_pipeline(context)
    workflow = build_event_market_workflow_spec(context, plan)
    output_contract = build_event_market_output_spec()

    assert workflow.name == "event-market-research"
    assert [stage.stage for stage in workflow.stages] == [
        "intake",
        "market",
        "research",
        "evidence",
        "pricing",
        "decision",
        "logging",
    ]
    assert output_contract.name == "event-market-output"
    first_section = output_contract.sections[0][1]
    assert first_section[0].name == "venue"
    assert output_contract.sections[2][1][0].name == "fair_probability"
