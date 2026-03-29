#!/usr/bin/env python3
"""CLI: Classify a single market event through the companion router.

Usage:
    cd backend
    uv run python ../.claude/skills/companion-router/scripts/classify_event.py \
        --source kalshi \
        --market-id KXNASCARCUPSERIES-NCS26 \
        --league "NASCAR Cup Series" \
        --phase futures

    # Or pipe JSON:
    echo '{"source":"kalshi","market_id":"NFL_CHIEFS_EAGLES","league":"NFL","market_type":"spread"}' \
        | uv run python ../.claude/skills/companion-router/scripts/classify_event.py --stdin
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add backend to path so imports work
backend_root = Path(__file__).parent.parent.parent.parent.parent / "backend"
sys.path.insert(0, str(backend_root))

from core.sports.companion_router import CompanionRouter, RouterInput


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Classify a market event through the companion router")
    p.add_argument("--source", default="manual", help="Source: kalshi|polymarket|manual")
    p.add_argument("--market-id", help="Market ID")
    p.add_argument("--url", help="Market URL")
    p.add_argument("--league", help="League name (raw or canonical)")
    p.add_argument("--market-type", help="Market type: spread|moneyline|total|prop|futures")
    p.add_argument("--market-subtype", help="Market subtype e.g. nfl_spread")
    p.add_argument("--phase", help="Phase: pre_game|live|futures")
    p.add_argument("--title", help="Market title or event description")
    p.add_argument("--stdin", action="store_true", help="Read JSON from stdin")
    p.add_argument("--json", action="store_true", help="Output as JSON")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.stdin:
        data = json.load(sys.stdin)
        inp = RouterInput(
            source=data.get("source", "manual"),
            market_id=data.get("market_id"),
            url=data.get("url"),
            league=data.get("league"),
            event_type=data.get("event_type"),
            market_type=data.get("market_type"),
            market_subtype=data.get("market_subtype"),
            phase=data.get("phase"),
            title=data.get("title"),
            raw_metadata=data.get("raw_metadata", {}),
        )
    else:
        inp = RouterInput(
            source=args.source,
            market_id=args.market_id,
            url=args.url,
            league=args.league,
            market_type=args.market_type,
            market_subtype=args.market_subtype,
            phase=args.phase,
            title=args.title,
        )

    router = CompanionRouter()
    route = router.classify(inp)

    result = {
        "app": route.app,
        "league": route.league,
        "market_type": route.market_type,
        "phase": route.phase,
        "classification_confidence": route.classification_confidence,
        "notes": route.notes,
        "kalshi_nascar_meta": route.kalshi_nascar_meta,
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"App:           {route.app or 'UNROUTED'}")
        print(f"League:        {route.league}")
        print(f"Market type:   {route.market_type}")
        print(f"Phase:         {route.phase}")
        print(f"Confidence:    {route.classification_confidence:.2%}")
        if route.notes:
            print("Notes:")
            for note in route.notes:
                print(f"  - {note}")
        if route.kalshi_nascar_meta:
            print(f"NASCAR meta:   {route.kalshi_nascar_meta}")


if __name__ == "__main__":
    main()
