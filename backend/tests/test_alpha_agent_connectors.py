import os
import unittest
from dataclasses import dataclass, field
from datetime import UTC, datetime

from core.shared.alpha_agent.connectors import (
    EventTimingConnector,
    KalshiMarketConnector,
    MeshTranscriptConnector,
)
from core.shared.alpha_agent.health_models import SourceStatus


@dataclass
class FakeSnapshot:
    ticker: str = "KXPOWELLMENTION-26MAR30-TARI"
    series_ticker: str = "KXPOWELLMENTION"
    title: str = "Will Powell say tariff during remarks at Harvard?"
    subtitle: str = "Tariff"
    exact_phrase: str = "tariff"
    speaker: str = "Powell"
    venue: str = "remarks at Harvard"
    resolution_rules: str = "Primary source applies"
    close_time: str = "2026-03-30T16:00:00Z"
    current_price_yes: float | None = 0.21
    yes_bid: int = 20
    yes_ask: int = 22
    last_price: int = 21
    volume: int = 1200
    open_interest: int = 500
    domain: str = "mentions"
    raw: dict = field(
        default_factory=lambda: {
            "yes_bid_size_fp": "80.0",
            "yes_ask_size_fp": "120.0",
            "yes_bid_dollars": "0.20",
            "yes_ask_dollars": "0.22",
            "last_price_dollars": "0.21",
        }
    )
    error: str | None = None


class FakeKalshiFetcher:
    def __init__(self, snapshot: FakeSnapshot | None = None, error: Exception | None = None) -> None:
        self.snapshot = snapshot or FakeSnapshot()
        self.error = error

    def fetch_ticker(self, ticker: str):
        if self.error:
            raise self.error
        return self.snapshot

    def fetch_from_url(self, url: str):
        if self.error:
            raise self.error
        return self.snapshot


class AlphaAgentConnectorTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("MESH_API_KEY", None)

    def test_kalshi_market_connector_wraps_mentions_ready_market_payload(self) -> None:
        connector = KalshiMarketConnector(fetcher=FakeKalshiFetcher())

        wrapped = connector.fetch_ticker("KXPOWELLMENTION-26MAR30-TARI")

        self.assertEqual(wrapped.diagnostics.source_health.status, SourceStatus.HEALTHY)
        self.assertEqual(wrapped.normalized_payload["exact_phrase"], "tariff")
        self.assertEqual(wrapped.normalized_payload["bid"], 0.2)
        self.assertEqual(wrapped.normalized_payload["ask_size"], 120.0)

    def test_kalshi_market_connector_classifies_rate_limit(self) -> None:
        connector = KalshiMarketConnector(fetcher=FakeKalshiFetcher(error=RuntimeError("HTTP 429 rate limit")))

        wrapped = connector.fetch_ticker("KXPOWELLMENTION-26MAR30-TARI")

        self.assertEqual(wrapped.diagnostics.source_health.status, SourceStatus.RATE_LIMITED)
        self.assertFalse(wrapped.diagnostics.payload_sanity_ok)

    def test_mesh_transcript_connector_normalizes_current_and_historical_mentions(self) -> None:
        os.environ["MESH_API_KEY"] = "test-key"

        def get_events(_: str):
            return [
                {"event_id": "hist-1", "event_type": "remarks"},
                {"event_id": "hist-2", "event_type": "remarks"},
                {"event_id": "hist-3", "event_type": "remarks"},
            ]

        def get_segments(event_id: str):
            if event_id == "live-1":
                return [{"sentence_txt": "Tariff tariff", "resolved_speaker_id": "speaker-1"}]
            if event_id == "hist-1":
                return [{"sentence_txt": "Tariff mentioned once", "resolved_speaker_id": "speaker-1"}]
            return [{"sentence_txt": "No keyword here", "resolved_speaker_id": "speaker-1"}]

        connector = MeshTranscriptConnector(
            resolve_speaker_id_fn=lambda _: "speaker-1",
            get_speaker_events_fn=get_events,
            get_segments_fn=get_segments,
            count_word_fn=lambda segments, word, speaker_id: sum(
                segment["sentence_txt"].lower().count(word.lower()) for segment in segments
            ),
        )

        wrapped = connector.fetch_mentions_context(
            speaker_name="Powell",
            phrase="tariff",
            event_type="remarks",
            current_event_id="live-1",
            current_event_complete=False,
        )

        self.assertEqual(wrapped.diagnostics.source_health.status, SourceStatus.HEALTHY)
        self.assertTrue(wrapped.normalized_payload["event_still_live"])
        self.assertEqual(wrapped.normalized_payload["live_word_count"], 2)
        self.assertEqual(wrapped.normalized_payload["events_with_phrase"], 1)
        self.assertAlmostEqual(wrapped.normalized_payload["historical_rate"], 1 / 3, places=4)

    def test_mesh_transcript_connector_marks_missing_auth_as_auth_failed(self) -> None:
        connector = MeshTranscriptConnector(
            resolve_speaker_id_fn=lambda _: "speaker-1",
            get_speaker_events_fn=lambda _: [],
            get_segments_fn=lambda _: [],
        )

        wrapped = connector.fetch_mentions_context(
            speaker_name="Powell",
            phrase="tariff",
            event_type="remarks",
        )

        self.assertEqual(wrapped.diagnostics.source_health.status, SourceStatus.AUTH_FAILED)
        self.assertFalse(wrapped.diagnostics.payload_sanity_ok)

    def test_event_timing_connector_flags_closed_event(self) -> None:
        connector = EventTimingConnector(
            now_fn=lambda: datetime(2026, 3, 30, 18, 0, tzinfo=UTC),
        )

        wrapped = connector.evaluate_event_state(
            source_id="KXPOWELLMENTION-26MAR30-TARI",
            close_time="2026-03-30T16:00:00Z",
            event_complete=False,
        )

        self.assertFalse(wrapped.normalized_payload["event_still_live"])
        self.assertEqual(wrapped.diagnostics.source_health.status, SourceStatus.HEALTHY)


if __name__ == "__main__":
    unittest.main()
