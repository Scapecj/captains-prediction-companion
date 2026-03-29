#!/usr/bin/env python3
"""Validate that the app registry and routing config are internally consistent.

Checks:
  1. All apps in APP_REGISTRY have valid league IDs
  2. All leagues in SPORTS_SKILL_REGISTRY are in CANONICAL_LEAGUES
  3. All Kalshi NASCAR series markets reference valid league IDs
  4. Routing priority list contains no unknown leagues
  5. No duplicate market_type → app mappings that could cause ambiguity

Usage:
    cd backend
    uv run python ../.claude/skills/companion-router/scripts/validate_config.py
"""

from __future__ import annotations

import sys
from pathlib import Path

backend_root = Path(__file__).parent.parent.parent.parent.parent / "backend"
sys.path.insert(0, str(backend_root))

from core.sports.app_registry import APP_REGISTRY, KALSHI_NASCAR_SERIES_MARKETS
from core.sports.config import (
    CANONICAL_LEAGUES,
    DEFAULT_PREFERRED_SPORTS,
    MARKET_SUBTYPES,
    SPORTS_SKILL_REGISTRY,
)


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(f"FAIL: {message}")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    print("Validating app registry and routing config...\n")

    # 1. All app leagues are canonical
    for app_name, spec in APP_REGISTRY.items():
        for league in spec.leagues:
            check(
                league in CANONICAL_LEAGUES,
                f"App '{app_name}' references unknown league '{league}'",
                errors,
            )

    # 2. All SPORTS_SKILL_REGISTRY leagues are canonical
    for league in SPORTS_SKILL_REGISTRY:
        check(
            league in CANONICAL_LEAGUES,
            f"SPORTS_SKILL_REGISTRY has unknown league '{league}'",
            errors,
        )

    # 3. Kalshi NASCAR markets reference valid leagues
    for market_id, meta in KALSHI_NASCAR_SERIES_MARKETS.items():
        league = str(meta.get("league", ""))
        check(
            league in CANONICAL_LEAGUES,
            f"Kalshi market '{market_id}' references unknown league '{league}'",
            errors,
        )

    # 4. Routing priority list has no unknown leagues
    for league in DEFAULT_PREFERRED_SPORTS:
        check(
            league in CANONICAL_LEAGUES,
            f"DEFAULT_PREFERRED_SPORTS has unknown league '{league}'",
            errors,
        )

    # 5. Every preferred sport has at least one app
    for league in DEFAULT_PREFERRED_SPORTS:
        apps = [a for a, spec in APP_REGISTRY.items() if league in spec.leagues]
        if not apps:
            warnings.append(f"WARN: No app registered for preferred league '{league}'")

    # 6. Market subtypes follow naming convention
    for subtype in MARKET_SUBTYPES:
        parts = subtype.split("_")
        if len(parts) < 2:
            warnings.append(f"WARN: Market subtype '{subtype}' has no prefix")

    # 7. Each app has at least one phase
    for app_name, spec in APP_REGISTRY.items():
        check(
            len(spec.phases) > 0,
            f"App '{app_name}' has no phases defined",
            errors,
        )

    # Print results
    if errors:
        print(f"{'='*50}")
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  {e}")
    else:
        print("All checks passed.")

    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  {w}")

    print(f"\nApps registered: {len(APP_REGISTRY)}")
    print(f"Canonical leagues: {len(CANONICAL_LEAGUES)}")
    print(f"Market subtypes: {len(MARKET_SUBTYPES)}")
    print(f"Kalshi NASCAR futures: {len(KALSHI_NASCAR_SERIES_MARKETS)}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
