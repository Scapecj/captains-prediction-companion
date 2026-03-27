"""Configuration for the generic event-market pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_EVENT_MARKET_SOURCE_STACK: tuple[str, str, str] = (
    "Kalshi",
    "Perplexity",
    "Playwright Scraper Skill",
)

MARKET_VENUE_ALIASES: dict[str, str] = {
    "KALSHI": "Kalshi",
    "KALSHI EXCHANGE": "Kalshi",
    "POLYMARKET": "Polymarket",
    "POLYMARKET EXCHANGE": "Polymarket",
}

EVENT_DOMAIN_ALIASES: dict[str, str] = {
    "SPORTS": "sports",
    "POLITICS": "politics",
    "MACRO": "macro",
    "ECONOMICS": "macro",
    "EARNINGS": "earnings",
    "CORPORATE": "earnings",
    "MENTION": "mention",
    "MENTIONS": "mention",
    "MEDIA": "mention",
    "GENERAL": "general",
}

DEFAULT_EVENT_DOMAINS: tuple[str, ...] = (
    "sports",
    "politics",
    "macro",
    "earnings",
    "mention",
    "general",
)


@dataclass(frozen=True, slots=True)
class EventMarketPipelineConfig:
    """Config for the generic event-market research workflow."""

    default_source_stack: tuple[str, str, str] = DEFAULT_EVENT_MARKET_SOURCE_STACK
    market_venue_aliases: dict[str, str] = field(
        default_factory=lambda: dict(MARKET_VENUE_ALIASES)
    )
    event_domain_aliases: dict[str, str] = field(
        default_factory=lambda: dict(EVENT_DOMAIN_ALIASES)
    )
    default_domains: tuple[str, ...] = DEFAULT_EVENT_DOMAINS

