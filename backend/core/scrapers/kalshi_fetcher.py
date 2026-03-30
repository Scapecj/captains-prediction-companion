"""
KalshiMarketFetcher — authenticated Kalshi market data fetcher.

Resolves a Kalshi URL or ticker to a normalized MarketSnapshot
ready for injection into run_market.py / RouterInput.

Uses the KalshiClient from the openclaw workspace (RSA-signed requests).
Falls back to unauthenticated public API on key errors.

Usage:
    fetcher = KalshiMarketFetcher()
    snap = fetcher.fetch_from_url("https://kalshi.com/markets/.../KXPOWELLMENTION-26MAR30")
    snap = fetcher.fetch_ticker("KXPOWELLMENTION-26MAR30-TARI")
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Inject openclaw path for KalshiClient
# ---------------------------------------------------------------------------

_OPENCLAW_PATH = os.path.expanduser("~/.openclaw/workspace")
if _OPENCLAW_PATH not in sys.path:
    sys.path.insert(0, _OPENCLAW_PATH)

_KALSHI_KEY_PATH = os.path.join(_OPENCLAW_PATH, "kalshi_private_key.pem")
_KALSHI_API_KEY  = "cb381ed7-e44b-4e98-903e-762257d78ac6"
_KALSHI_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"


# ---------------------------------------------------------------------------
# Output model
# ---------------------------------------------------------------------------

@dataclass
class MarketSnapshot:
    """Normalized market data ready for the companion pipeline."""
    ticker: str
    series_ticker: str
    title: str
    subtitle: str                           # often the phrase/word for mention markets
    exact_phrase: str                       # extracted from custom_strike.Word if present
    speaker: str                            # inferred from series (e.g. "Powell")
    venue: str                              # inferred from event/series description
    resolution_rules: str
    close_time: str
    current_price_yes: float | None         # midpoint of bid/ask, or last_price
    yes_bid: int
    yes_ask: int
    last_price: int
    volume: int
    open_interest: int
    domain: str                             # "mentions" | "sports" | "politics" | "macro"
    raw: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


# ---------------------------------------------------------------------------
# Kalshi client loader
# ---------------------------------------------------------------------------

def _get_client():
    try:
        import kalshi_url as ku
        cfg = ku.Config(
            api_key=_KALSHI_API_KEY,
            key_path=_KALSHI_KEY_PATH,
            base_url=_KALSHI_BASE_URL,
        )
        return ku.KalshiClient(cfg)
    except Exception as e:
        raise RuntimeError(f"Could not initialize KalshiClient: {e}")


# ---------------------------------------------------------------------------
# Domain + speaker/venue inference
# ---------------------------------------------------------------------------

_MENTION_SERIES_SPEAKERS = {
    "KXPOWELLMENTION": "Powell",
    "KXTRUMPMENTION":  "Trump",
    "KXBIDENMENTION":  "Biden",
    "KXHARRIS":        "Harris",
}

_MACRO_KEYWORDS = ("fomc", "fed", "powell", "cpi", "inflation", "gdp", "jobs", "treasury")
_POLITICS_KEYWORDS = ("election", "senate", "congress", "president", "vote", "trump", "biden")
_SPORTS_KEYWORDS = ("nfl", "nba", "mlb", "ufc", "nascar", "game", "score", "team")


def _infer_domain(series: str, title: str) -> str:
    s = (series + " " + title).lower()
    if "mention" in series.lower():
        return "mentions"
    if any(k in s for k in _MACRO_KEYWORDS):
        return "macro"
    if any(k in s for k in _POLITICS_KEYWORDS):
        return "politics"
    if any(k in s for k in _SPORTS_KEYWORDS):
        return "sports"
    return "general"


def _infer_speaker(series: str) -> str:
    for prefix, speaker in _MENTION_SERIES_SPEAKERS.items():
        if series.upper().startswith(prefix):
            return speaker
    return ""


def _infer_venue_from_title(title: str) -> str:
    """Extract venue from market title like 'What will X say during remarks at Harvard University?'"""
    t = title.lower()
    # Look for "during <venue>" or "at <venue>" patterns
    import re as _re
    m = _re.search(r"during\s+(.+?)(?:\?|$)", t)
    if m:
        return m.group(1).strip().rstrip("?").strip()
    m = _re.search(r"\bat\s+(.+?)(?:\?|$)", t)
    if m:
        venue_str = m.group(1).strip().rstrip("?").strip()
        # Exclude very short matches like "at a"
        if len(venue_str) > 4:
            return venue_str
    # Fallback: known patterns
    for kw, venue in [
        ("press conference", "press conference"),
        ("fomc", "Federal Reserve press conference"),
        ("state of the union", "State of the Union"),
        ("debate", "debate"),
        ("rally", "rally"),
        ("hearing", "hearing"),
        ("interview", "interview"),
        ("speech", "speech"),
        ("remarks", "remarks"),
    ]:
        if kw in t:
            return venue
    return "speech or remarks"


def _extract_phrase(market: dict) -> str:
    """Extract the exact phrase from custom_strike or subtitle."""
    cs = market.get("custom_strike") or {}
    if isinstance(cs, dict):
        word = cs.get("Word") or cs.get("phrase") or cs.get("word") or ""
        if word:
            return word
    return market.get("subtitle", "")


def _mid_price(market: dict) -> float | None:
    """Return midpoint of bid/ask in 0-1 range, or last_price."""
    # Try integer cent fields first (some endpoints), then dollar string fields
    bid = market.get("yes_bid", 0)
    ask = market.get("yes_ask", 0)
    if bid and ask:
        return (bid + ask) / 200.0   # cents → 0-1

    # Dollar string fields (common in elections API)
    try:
        bid_d = float(market.get("yes_bid_dollars") or 0)
        ask_d = float(market.get("yes_ask_dollars") or 0)
        bid_size = float(market.get("yes_bid_size_fp") or 0)
        ask_size = float(market.get("yes_ask_size_fp") or 0)
        if bid_d and ask_d and bid_size > 0 and ask_size > 0:
            return (bid_d + ask_d) / 2.0
        if ask_d and ask_size > 0:
            return ask_d
        if bid_d and bid_size > 0:
            return bid_d
    except (TypeError, ValueError):
        pass

    # Last price fallbacks
    last = market.get("last_price", 0)
    if last:
        return last / 100.0
    try:
        last_d = float(market.get("last_price_dollars") or 0)
        if last_d:
            return last_d
    except (TypeError, ValueError):
        pass
    return None


def _extract_resolution_rules(market: dict) -> str:
    rules = market.get("rules_primary", "") or ""
    condition = market.get("early_close_condition", "") or ""
    parts = [p for p in [rules, condition] if p]
    return " | ".join(parts)[:500]


# ---------------------------------------------------------------------------
# Parse ticker from URL
# ---------------------------------------------------------------------------

def _ticker_from_url(url: str) -> str:
    """
    Extract market ticker from a Kalshi URL.
    e.g. https://kalshi.com/markets/kxpowellmention/powell-mention-general-/KXPOWELLMENTION-26MAR30
    → KXPOWELLMENTION-26MAR30
    """
    m = re.search(r"/([A-Z][A-Z0-9\-]+)(?:\?|$)", url)
    if m:
        return m.group(1)
    # Try last path segment
    path = url.split("?")[0].rstrip("/")
    last = path.split("/")[-1]
    if re.match(r"[A-Z][A-Z0-9\-]{4,}", last):
        return last
    raise ValueError(f"Could not extract market ticker from URL: {url}")


# ---------------------------------------------------------------------------
# Main fetcher
# ---------------------------------------------------------------------------

class KalshiMarketFetcher:

    def __init__(self) -> None:
        self._client = None

    def _client_or_raise(self):
        if self._client is None:
            self._client = _get_client()
        return self._client

    def fetch_from_url(self, url: str) -> MarketSnapshot:
        """Fetch market data from a Kalshi URL."""
        ticker = _ticker_from_url(url)
        return self.fetch_ticker(ticker)

    def fetch_ticker(self, ticker: str) -> MarketSnapshot:
        """Fetch a single market by ticker."""
        client = self._client_or_raise()
        try:
            market = client.fetch_market(ticker)
        except Exception as e:
            # Try series search fallback
            series = re.sub(r"-\w+$", "", ticker)
            try:
                result = client.get("/markets", {"series_ticker": series, "limit": "50"})
                markets = result.get("markets", [])
                market = next((m for m in markets if m.get("ticker") == ticker), None)
                if not market:
                    return MarketSnapshot(
                        ticker=ticker, series_ticker=series, title=ticker,
                        subtitle="", exact_phrase="", speaker="", venue="",
                        resolution_rules="", close_time="",
                        current_price_yes=None, yes_bid=0, yes_ask=0,
                        last_price=0, volume=0, open_interest=0,
                        domain="general", error=str(e),
                    )
            except Exception as e2:
                return MarketSnapshot(
                    ticker=ticker, series_ticker="", title=ticker,
                    subtitle="", exact_phrase="", speaker="", venue="",
                    resolution_rules="", close_time="",
                    current_price_yes=None, yes_bid=0, yes_ask=0,
                    last_price=0, volume=0, open_interest=0,
                    domain="general", error=str(e2),
                )

        series_ticker = market.get("event_ticker", "")
        phrase = _extract_phrase(market)
        speaker = _infer_speaker(series_ticker)
        venue = _infer_venue_from_title(market.get("title", ""))
        domain = _infer_domain(series_ticker, market.get("title", ""))

        return MarketSnapshot(
            ticker=market.get("ticker", ticker),
            series_ticker=series_ticker,
            title=market.get("title", ""),
            subtitle=market.get("subtitle", ""),
            exact_phrase=phrase,
            speaker=speaker,
            venue=venue,
            resolution_rules=_extract_resolution_rules(market),
            close_time=market.get("close_time", ""),
            current_price_yes=_mid_price(market),
            yes_bid=market.get("yes_bid", 0),
            yes_ask=market.get("yes_ask", 0),
            last_price=market.get("last_price", 0),
            volume=market.get("volume", 0),
            open_interest=market.get("open_interest", 0),
            domain=domain,
            raw=market,
        )

    def fetch_series(self, series_ticker: str) -> list[MarketSnapshot]:
        """Fetch all markets in a series."""
        client = self._client_or_raise()
        result = client.get("/markets", {"series_ticker": series_ticker, "limit": "50"})
        markets = result.get("markets", [])
        snaps = []
        for m in markets:
            ticker = m.get("ticker", "")
            series_t = m.get("event_ticker", series_ticker)
            phrase = _extract_phrase(m)
            speaker = _infer_speaker(series_t)
            venue = _infer_venue_from_title(m.get("title", ""))
            domain = _infer_domain(series_t, m.get("title", ""))
            snaps.append(MarketSnapshot(
                ticker=ticker,
                series_ticker=series_t,
                title=m.get("title", ""),
                subtitle=m.get("subtitle", ""),
                exact_phrase=phrase,
                speaker=speaker,
                venue=venue,
                resolution_rules=_extract_resolution_rules(m),
                close_time=m.get("close_time", ""),
                current_price_yes=_mid_price(m),
                yes_bid=m.get("yes_bid", 0),
                yes_ask=m.get("yes_ask", 0),
                last_price=m.get("last_price", 0),
                volume=m.get("volume", 0),
                open_interest=m.get("open_interest", 0),
                domain=domain,
                raw=m,
            ))
        return snaps
