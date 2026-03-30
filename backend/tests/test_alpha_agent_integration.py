import argparse
import unittest

from backend.run_market import run_politics_market
from core.politics.apps.mentions_app import run as mentions_run
from core.politics.apps.mentions_runtime import MentionRuntimeAdapter
from core.politics.models import MentionMarketInput, MentionMarketOutput
from core.scrapers.kalshi_fetcher import MarketSnapshot
from core.shared.alpha_agent.source_manager import AlphaSourceManager


def _wrapped_payload(*, source_type, source_id, schema_version, normalized_payload, source):
    manager = AlphaSourceManager()
    health = manager.evaluate_source_health(
        source=source,
        latency_ms=25.0,
        auth_ok=True,
        freshness_seconds=0.0,
        schema_valid=True,
        degraded_mode=False,
        alerts=[],
    )
    return manager.wrap_payload(
        source_type=source_type,
        source_id=source_id,
        schema_version=schema_version,
        normalized_payload=normalized_payload,
        raw_payload_ref=f"{source}://{source_id}",
        health=health,
        notes=["test_payload"],
    )


class _FakeKalshiMarketConnector:
    def fetch_ticker(self, ticker: str):
        return _wrapped_payload(
            source_type="market",
            source_id=ticker,
            schema_version="mentions_market_v1",
            source="kalshi",
            normalized_payload={
                "market_id": ticker,
                "title": "Will Powell say tariff during remarks at Harvard?",
                "exact_phrase": "tariff",
                "speaker": "Powell",
                "venue": "remarks at Harvard",
                "close_time": "2026-03-30T16:00:00Z",
                "current_price_yes": 0.21,
            },
        )


class _FakeTranscriptConnector:
    def fetch_mentions_context(self, **_: object):
        return _wrapped_payload(
            source_type="transcript",
            source_id="powell:tariff:remarks",
            schema_version="mentions_transcript_v1",
            source="mesh_transcripts",
            normalized_payload={
                "speaker_name": "Powell",
                "speaker_id": "speaker-1",
                "phrase": "tariff",
                "event_type": "remarks",
                "current_event_id": "live-1",
                "current_event_found": True,
                "current_event_complete": False,
                "event_still_live": True,
                "live_word_count": 2,
                "events_analyzed": 3,
                "events_with_phrase": 1,
                "historical_rate": 1 / 3,
                "recent_hits": [1, 0, 0],
                "matching_event_ids": ["hist-1"],
                "data_gaps": [],
            },
        )


class _FakeTimingConnector:
    def evaluate_event_state(self, *, source_id: str, close_time: str, event_complete: bool = False):
        return _wrapped_payload(
            source_type="event_timing",
            source_id=source_id,
            schema_version="mentions_event_timing_v1",
            source="event_timing",
            normalized_payload={
                "source_id": source_id,
                "close_time": close_time,
                "event_complete": event_complete,
                "event_still_live": True,
                "seconds_to_close": 3600.0,
                "evaluated_at": "2026-03-30T15:00:00+00:00",
                "alerts": [],
            },
        )


class _FakeSeriesFetcher:
    def __init__(self, snapshots: list[MarketSnapshot]):
        self._snapshots = snapshots

    def fetch_series(self, series_ticker: str) -> list[MarketSnapshot]:
        return list(self._snapshots)


_STUB_CHILD_CONFIG = {
    "EVENT-A": {"fair_yes": 0.68, "yes_price": 0.58, "word": "alpha"},
    "EVENT-B": {"fair_yes": 0.28, "yes_price": 0.82, "word": "beta"},
}


def _stub_mention_runner(child_input: MentionMarketInput, runtime_adapter: MentionRuntimeAdapter | None = None) -> MentionMarketOutput:
    config = _STUB_CHILD_CONFIG.get(child_input.market_id, {"fair_yes": 0.5, "yes_price": 0.5, "word": child_input.market_id})
    yes_price = config["yes_price"]
    context = {
        "market_id": child_input.market_id,
        "exact_phrase": config["word"],
        "speaker": child_input.speaker or "Speaker",
        "venue": child_input.venue or "venue",
        "current_price_yes": yes_price,
        "bid": max(0.0, yes_price - 0.02),
        "ask": min(1.0, yes_price + 0.02),
        "bid_size": 120.0,
        "ask_size": 110.0,
        "event_still_live": True,
        "event_complete": False,
    }
    return MentionMarketOutput(
        fair_yes=config["fair_yes"],
        confidence="high",
        recommendation="watch",
        reasoning="stub reasoning",
        watch_for=[],
        notes=["stub"],
        source_diagnostics={"market": {"status": "HEALTHY"}},
        runtime_context=context,
    )


class TestAlphaAgentIntegration(unittest.TestCase):
    def test_mentions_runtime_merges_alpha_agent_payloads(self):
        adapter = MentionRuntimeAdapter(
            market_connector=_FakeKalshiMarketConnector(),
            transcript_connector=_FakeTranscriptConnector(),
            timing_connector=_FakeTimingConnector(),
        )
        inp = MentionMarketInput(
            source="kalshi",
            market_id="KXPOWELLMENTION-26MAR30-TARI",
            title="Will Powell say tariff during remarks at Harvard?",
        )

        output = mentions_run(inp, runtime_adapter=adapter)

        self.assertEqual(output.confidence, "high")
        self.assertEqual(output.recommendation, "bet_yes")
        self.assertAlmostEqual(output.fair_yes, 0.9, places=3)
        self.assertEqual(output.runtime_context["exact_phrase"], "tariff")
        self.assertEqual(output.runtime_context["speaker"], "Powell")
        self.assertTrue(output.runtime_context["event_still_live"])
        self.assertEqual(output.source_diagnostics["market"]["status"], "HEALTHY")
        self.assertEqual(output.source_diagnostics["transcript"]["status"], "HEALTHY")
        self.assertEqual(output.source_diagnostics["timing"]["status"], "HEALTHY")

    def test_event_level_runner_sorts_children_by_best_edge(self):
        snapshots = [
            MarketSnapshot(
                ticker="EVENTPARENT-01",
                series_ticker="EVENTPARENT-01",
                title="Parent event",
                subtitle="parent",
                exact_phrase="",
                speaker="Leader",
                venue="Main Hall",
                resolution_rules="",
                close_time="2026-04-01T00:00:00Z",
                current_price_yes=0.5,
                yes_bid=50,
                yes_ask=60,
                last_price=0,
                volume=0,
                open_interest=0,
                domain="mentions",
            ),
            MarketSnapshot(
                ticker="EVENT-A",
                series_ticker="EVENTPARENT-01",
                title="Child alpha",
                subtitle="alpha",
                exact_phrase="alpha",
                speaker="Leader",
                venue="Main Hall",
                resolution_rules="",
                close_time="2026-04-01T00:00:00Z",
                current_price_yes=0.58,
                yes_bid=52,
                yes_ask=64,
                last_price=0,
                volume=0,
                open_interest=0,
                domain="mentions",
            ),
            MarketSnapshot(
                ticker="EVENT-B",
                series_ticker="EVENTPARENT-01",
                title="Child beta",
                subtitle="beta",
                exact_phrase="beta",
                speaker="Leader",
                venue="Main Hall",
                resolution_rules="",
                close_time="2026-04-01T00:00:00Z",
                current_price_yes=0.82,
                yes_bid=80,
                yes_ask=90,
                last_price=0,
                volume=0,
                open_interest=0,
                domain="mentions",
            ),
        ]
        args = argparse.Namespace(
            source="kalshi",
            market_id="EVENTPARENT-01",
            child_market=None,
            title="Parent mention board",
            league=None,
            market_type=None,
            phase="pre_game",
            price_yes=None,
            domain="mentions",
        )
        meta = {"speaker": "Leader", "venue": "Main Hall"}

        output = run_politics_market(
            args,
            meta,
            mention_runner=_stub_mention_runner,
            event_fetcher=_FakeSeriesFetcher(snapshots),
        )

        self.assertEqual(output["parent_event_ticker"], args.market_id)
        ranked = output["ranked_summary"]
        self.assertGreaterEqual(len(ranked), 2)
        self.assertGreater(
            ranked[0]["best_executable_edge"],
            ranked[1]["best_executable_edge"],
        )
        self.assertEqual(ranked[0]["best_side"], "NO")
        self.assertIn("source_diagnostics", output)

    def test_child_only_mode_exposes_decision_metadata(self):
        args = argparse.Namespace(
            source="kalshi",
            market_id="EVENTPARENT-01",
            child_market="EVENT-A",
            title="Parent mention board",
            league=None,
            market_type=None,
            phase="pre_game",
            price_yes=None,
            domain="mentions",
        )
        meta = {"speaker": "Leader", "venue": "Main Hall"}

        result = run_politics_market(
            args,
            meta,
            mention_runner=_stub_mention_runner,
        )

        self.assertEqual(result["child_ticker"], args.child_market)
        self.assertEqual(result["market_id"], args.child_market)
        self.assertIn("mentions", result)
        self.assertIn("decision", result)
        self.assertEqual(result["market_state"], result["decision"]["market_state"])
        self.assertEqual(result["recommended_side"], result["decision"]["recommended_side"])
        self.assertGreater(result["best_executable_edge"], 0.0)


if __name__ == "__main__":
    unittest.main()
