import unittest

from core.shared.alpha_agent.health_models import SourceStatus
from core.shared.alpha_agent.source_manager import AlphaSourceManager


class AlphaSourceManagerTests(unittest.TestCase):
    def test_rate_limited_source_status_overrides_generic_health(self) -> None:
        manager = AlphaSourceManager()

        report = manager.evaluate_source_health(
            source="kalshi",
            latency_ms=850.0,
            auth_ok=True,
            freshness_seconds=4.0,
            schema_valid=True,
            degraded_mode=False,
            alerts=["http_429"],
        )

        self.assertEqual(report.status, SourceStatus.RATE_LIMITED)
        self.assertIn("http_429", report.alerts)

    def test_wrap_payload_includes_required_diagnostics(self) -> None:
        manager = AlphaSourceManager()
        health = manager.evaluate_source_health(
            source="mesh_transcripts",
            latency_ms=120.0,
            auth_ok=True,
            freshness_seconds=30.0,
            schema_valid=True,
            degraded_mode=False,
            alerts=[],
        )

        wrapped = manager.wrap_payload(
            source_type="transcript",
            source_id="mesh:powell:event-1",
            schema_version="v1",
            normalized_payload={"segments": 201},
            raw_payload_ref="mesh://event-1",
            health=health,
        )

        self.assertEqual(wrapped.source_type, "transcript")
        self.assertEqual(wrapped.source_id, "mesh:powell:event-1")
        self.assertEqual(wrapped.raw_payload_ref, "mesh://event-1")
        self.assertEqual(wrapped.diagnostics.source_health.status, SourceStatus.HEALTHY)
        self.assertGreaterEqual(wrapped.freshness_seconds, 0.0)


if __name__ == "__main__":
    unittest.main()
