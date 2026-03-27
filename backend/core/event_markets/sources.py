"""Source ordering for event-market research."""

from __future__ import annotations

from core.event_markets.config import (
    DEFAULT_EVENT_MARKET_SOURCE_STACK,
    EVENT_DOMAIN_ALIASES,
    MARKET_VENUE_ALIASES,
)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def canonicalize_market_venue(venue: str | None) -> str | None:
    """Normalize a venue name to its canonical label."""
    cleaned = _clean(venue)
    if not cleaned:
        return None
    alias = MARKET_VENUE_ALIASES.get(cleaned.upper())
    return alias or cleaned


def normalize_event_domain(domain: str | None) -> str | None:
    """Normalize a domain name into the generic event-market taxonomy."""
    cleaned = _clean(domain)
    if not cleaned:
        return None
    alias = EVENT_DOMAIN_ALIASES.get(cleaned.upper())
    return alias or cleaned.lower()


def build_market_source_order(
    venue: str | None,
    *,
    default_source_stack: tuple[str, str, str] = DEFAULT_EVENT_MARKET_SOURCE_STACK,
) -> tuple[str, str, str]:
    """
    Build the source order for an event market.

    The usable default is:
    1. venue market source
    2. Perplexity
    3. Playwright Scraper Skill
    """
    canonical_venue = canonicalize_market_venue(venue) or default_source_stack[0]
    return (
        canonical_venue,
        default_source_stack[1],
        default_source_stack[2],
    )

