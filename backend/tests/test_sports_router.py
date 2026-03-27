from core.sports.adapters import get_provider_selection
from core.sports.advanced import ConsensusPriceEngine, NoBetClassifier
from core.sports.config import DEFAULT_SPORTS_CONFIG, normalize_league_name
from core.sports.models import SportEvent, SportsMarketQuote
from core.sports.providers import SPORTS_FALLBACK_ORDER, SPORTS_PROVIDER_MATRIX, get_provider_stack
from core.sports.router import sports_calendar_router


def test_normalize_league_name_aliases():
    assert normalize_league_name("NCAA Men's Basketball") == "NCAA_BB"
    assert normalize_league_name("NASCAR O'Reilly Auto Parts Series") == "NASCAR_OREILLY"
    assert normalize_league_name("MMA") == "UFC"


def test_sports_calendar_router_prefers_order_and_caps():
    events = [
        SportEvent(league="MLB", event_id="mlb-1"),
        SportEvent(league="MLB", event_id="mlb-2"),
        SportEvent(league="NBA", event_id="nba-1"),
        SportEvent(league="NFL", event_id="nfl-1"),
        SportEvent(league="NASCAR_CUP", event_id="nascar-1"),
    ]

    route = sports_calendar_router(lambda _days: events, config=DEFAULT_SPORTS_CONFIG)

    assert route.active_sports == ("NFL", "NBA", "MLB", "NASCAR_CUP")
    assert route.counts_by_league["MLB"] == 2
    assert route.counts_by_league["NBA"] == 1
    assert route.fallback_used is False


def test_sports_calendar_router_falls_back_when_empty():
    route = sports_calendar_router(lambda _days: [], config=DEFAULT_SPORTS_CONFIG)

    assert route.active_sports == ("MLB", "UFC")
    assert route.fallback_used is True


def test_consensus_price_engine_flags_stale_quotes():
    engine = ConsensusPriceEngine(stale_price_threshold_prob=0.02)
    quotes = [
        SportsMarketQuote(venue="A", market_id="m1", price=0.62, implied_probability=0.62),
        SportsMarketQuote(venue="B", market_id="m1", price=0.61, implied_probability=0.61),
        SportsMarketQuote(venue="C", market_id="m1", price=0.70, implied_probability=0.70),
    ]

    result = engine.build_consensus(quotes)

    assert result.consensus_probability == 0.62
    assert result.stale_venues == ("C",)
    assert result.spread == 0.09


def test_no_bet_classifier_blocks_weak_and_stale_edges():
    classifier = NoBetClassifier(min_edge=0.02, min_confidence=0.55)
    skip = classifier.evaluate(
        edge=0.01,
        confidence=0.50,
        stale_price_gap=0.03,
        info_quality="unconfirmed",
        clv_history=-0.01,
        market_state_label="live",
    )

    assert skip.should_skip is True
    assert "edge below threshold" in skip.reasons
    assert "confidence below threshold" in skip.reasons


def test_provider_matrix_prioritizes_the_right_sources():
    assert get_provider_stack("NFL", "research") == ("Perplexity", "Playwright Scraper Skill")
    assert get_provider_stack("NFL", "odds")[0] == "The Odds API"
    assert get_provider_stack("NFL", "schedule")[0] == "nflverse"
    assert get_provider_stack("MLB", "historical")[0] == "Baseball Savant"
    assert get_provider_stack("MLB", "props", market_subtype="mlb_home_run_prop")[0] == "Baseball Savant"
    assert SPORTS_PROVIDER_MATRIX["MLB"]["props"][0] == "Baseball Savant"
    assert SPORTS_FALLBACK_ORDER["MLB"]["mlb_pitcher_strikeout_prop"][0] == "MLB Stats API"


def test_provider_selection_wraps_provider_stack():
    selection = get_provider_selection("MLB", "live")
    assert selection.provider_stack[0] == "MLB Stats API"
    assert selection.league == "MLB"


def test_research_selection_points_at_perplexity():
    from core.sports.adapters import get_research_selection

    selection = get_research_selection("MLB")
    assert selection.provider_stack == ("Perplexity", "Playwright Scraper Skill")


def test_unsupported_high_cost_live_data_is_explicitly_unavailable():
    import pytest

    with pytest.raises(KeyError):
        get_provider_stack("NBA", "live")
