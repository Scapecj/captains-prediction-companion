"""Concrete Kalshi connector for mentions-app market inputs."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from core.scrapers.kalshi_fetcher import KalshiMarketFetcher, MarketSnapshot

from ..health_models import NormalizedPayloadWrapper
from ..normalizers.mentions import normalize_kalshi_market_payload
from ..source_manager import AlphaSourceManager
from ..diagnostics.connector_diagnostics import classify_exception


class _KalshiFetcherProtocol(Protocol):
    def fetch_ticker(self, ticker: str) -> MarketSnapshot: ...
    def fetch_from_url(self, url: str) -> MarketSnapshot: ...


@dataclass(slots=True)
class KalshiMarketConnector:
    source_manager: AlphaSourceManager | None = None
    fetcher: _KalshiFetcherProtocol | None = None

    def __post_init__(self) -> None:
        if self.source_manager is None:
            self.source_manager = AlphaSourceManager()
        if self.fetcher is None:
            self.fetcher = KalshiMarketFetcher()

    def fetch_ticker(self, ticker: str) -> NormalizedPayloadWrapper:
        return self._fetch(source_id=ticker, fetch_fn=lambda: self.fetcher.fetch_ticker(ticker))

    def fetch_url(self, url: str) -> NormalizedPayloadWrapper:
        return self._fetch(source_id=url, fetch_fn=lambda: self.fetcher.fetch_from_url(url))

    def _fetch(self, *, source_id: str, fetch_fn) -> NormalizedPayloadWrapper:
        started = time.monotonic()
        try:
            snapshot = fetch_fn()
            if snapshot.error:
                raise RuntimeError(snapshot.error)
            normalized = normalize_kalshi_market_payload(snapshot)
            latency_ms = (time.monotonic() - started) * 1000.0
            schema_valid = self._is_schema_valid(normalized)
            health = self.source_manager.evaluate_source_health(
                source="kalshi",
                latency_ms=latency_ms,
                auth_ok=True,
                freshness_seconds=0.0,
                schema_valid=schema_valid,
                degraded_mode=False,
                alerts=[],
            )
            return self.source_manager.wrap_payload(
                source_type="market",
                source_id=normalized["market_id"],
                schema_version="mentions_market_v1",
                normalized_payload=normalized,
                raw_payload_ref=f"kalshi://{normalized['market_id']}",
                health=health,
                notes=["mentions_ready_market_payload"],
            )
        except Exception as exc:
            latency_ms = (time.monotonic() - started) * 1000.0
            auth_ok, alerts, degraded_mode = classify_exception(exc)
            health = self.source_manager.evaluate_source_health(
                source="kalshi",
                latency_ms=latency_ms,
                auth_ok=auth_ok,
                freshness_seconds=0.0,
                schema_valid=False,
                degraded_mode=degraded_mode,
                alerts=alerts,
            )
            return self.source_manager.wrap_payload(
                source_type="market",
                source_id=source_id,
                schema_version="mentions_market_v1",
                normalized_payload={},
                raw_payload_ref=f"kalshi://{source_id}",
                health=health,
                payload_sanity_ok=False,
                notes=[str(exc)],
            )

    @staticmethod
    def _is_schema_valid(payload: dict[str, object]) -> bool:
        required = (
            "market_id",
            "title",
            "exact_phrase",
            "speaker",
            "venue",
            "current_price_yes",
            "bid",
            "ask",
            "bid_size",
            "ask_size",
            "close_time",
        )
        return all(key in payload for key in required)
