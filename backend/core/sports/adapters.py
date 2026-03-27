"""Adapter descriptors for sports data integrations."""

from __future__ import annotations

from dataclasses import dataclass

from core.sports.providers import DataKind, PROVIDER_ADAPTERS


@dataclass(frozen=True, slots=True)
class SportsProviderSelection:
    league: str
    data_kind: DataKind
    provider_stack: tuple[str, ...]
    market_subtype: str | None = None


@dataclass(frozen=True, slots=True)
class SportsProviderAdapter:
    """Descriptor for a configured provider adapter.

    This is intentionally light: it gives the codebase a typed place to hang
    future fetch logic without forcing live network calls before credentials are
    wired in.
    """

    name: str
    provider_type: str
    data_kinds: tuple[DataKind, ...]
    leagues: tuple[str, ...]
    auth_env_vars: tuple[str, ...] = ()
    notes: str = ""
    url: str | None = None
    capabilities: tuple[str, ...] = ()

    def is_configured(self) -> bool:
        return PROVIDER_ADAPTERS[self.name].is_configured()

    def supports(self, league: str, data_kind: DataKind) -> bool:
        return league in self.leagues and data_kind in self.data_kinds


SPORTS_PROVIDER_ADAPTERS: dict[str, SportsProviderAdapter] = {
    name: SportsProviderAdapter(
        name=spec.name,
        provider_type=spec.provider_type,
        data_kinds=spec.data_kinds,
        leagues=spec.leagues,
        auth_env_vars=spec.auth_env_vars,
        notes=spec.notes,
        url=spec.url,
        capabilities=tuple(
            capability
            for capability, enabled in {
                "live": spec.supports_live,
                "historical": spec.supports_historical,
                "props": spec.supports_props,
                "schedule": spec.supports_schedule,
                "odds": spec.supports_odds,
            }.items()
            if enabled
        ),
    )
    for name, spec in PROVIDER_ADAPTERS.items()
}


def get_provider_selection(
    league: str,
    data_kind: DataKind,
    *,
    market_subtype: str | None = None,
) -> SportsProviderSelection:
    from core.sports.providers import get_provider_stack

    return SportsProviderSelection(
        league=league,
        data_kind=data_kind,
        provider_stack=get_provider_stack(league, data_kind, market_subtype=market_subtype),
        market_subtype=market_subtype,
    )


def get_research_selection(league: str) -> SportsProviderSelection:
    """Return the Perplexity-first research selection for a league."""
    return get_provider_selection(league, "research")
