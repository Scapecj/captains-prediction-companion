#!/usr/bin/env python3
"""
run_market.py — CLI entry point to run any market through the companion pipeline.

Usage:
  # Sports market
  python run_market.py \
    --source kalshi \
    --market-id KXNFL-SF-DAL-20261001 \
    --league NFL \
    --market-type spread \
    --phase pre_game \
    --price-yes 0.54

  # Props (requires lineup_confirmed in metadata)
  python run_market.py \
    --source kalshi \
    --market-id KXMLB-OHTANI-HR \
    --league MLB \
    --market-type prop_hr \
    --phase pre_game \
    --meta '{"lineup_confirmed": true, "barrel_rate": 0.11, "opp_fip": 3.9, "hr_park_factor": 1.05, "projected_pas": 4}'

  # Politics market
  python run_market.py \
    --source kalshi \
    --market-id KXELEC-2026-SEN \
    --title "Will Democrats control the Senate after 2026 midterms?" \
    --domain politics \
    --price-yes 0.44

  # Pipe JSON
  echo '{"source":"kalshi","market_id":"X","league":"NBA","market_type":"spread","phase":"pre_game"}' \
    | python run_market.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Ensure backend/ is on path when run from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from core.sports.setup import bootstrap_router
from core.sports.companion_router import RouterInput
from core.sports.kelly import KellyBankrollManager, compute_ev


def run_sports_market(args: argparse.Namespace, meta: dict) -> dict:
    router = bootstrap_router()

    # Normalize meta: compute epa_differential if separate home/away given
    if "epa_home" in meta and "epa_away" in meta and "epa_differential" not in meta:
        meta["epa_differential"] = meta["epa_home"] - meta["epa_away"]

    # Normalize price: apps read market_probability, CLI accepts price_yes
    if args.price_yes is not None:
        meta.setdefault("market_probability", args.price_yes)
        meta.setdefault("current_price_yes", args.price_yes)

    inp = RouterInput(
        source=args.source,
        market_id=args.market_id,
        league=args.league,
        market_type=args.market_type,
        phase=args.phase,
        raw_metadata=meta,
    )

    output = router.dispatch(inp)

    result: dict = {
        "market_id": args.market_id,
        "pipeline": output.pipeline,
        "app": output.pipeline,
        "fair_probability": round(output.fair_probability, 4),
        "edge": round(output.edge, 4),
        "edge_cents": round(output.edge * 100, 2),
        "confidence": round(output.confidence, 4),
        "no_bet_flag": output.no_bet_flag,
        "recommendation": getattr(output, "recommendation", "watch"),
        "notes": output.notes,
        "extra": output.extra,
    }

    # Kelly sizing if we have edge + confidence
    if not output.no_bet_flag and output.edge != 0 and output.confidence > 0:
        bankroll = args.bankroll
        market_prob = output.market_probability if output.market_probability else (args.price_yes or 0.5)
        edge = output.edge  # fair - market
        ev_pct = edge * 100
        # Quarter-Kelly fraction: edge / (1 - market_prob) * 0.25, capped at 25%
        if market_prob > 0 and market_prob < 1:
            full_kelly = edge / (1.0 - market_prob) if edge > 0 else 0.0
            fraction = min(full_kelly * 0.25, 0.25)
        else:
            fraction = 0.0
        dollars = fraction * bankroll
        if args.phase == "live":
            dollars *= 0.5
            fraction *= 0.5
        result["kelly"] = {
            "bankroll": bankroll,
            "fraction": round(fraction, 4),
            "dollars": round(dollars, 2),
            "ev_pct": round(ev_pct, 2),
            "live_scaled": args.phase == "live",
        }

    return result


def _is_event_level_mention_request(args: argparse.Namespace, meta: dict) -> bool:
    if args.child_market:
        return False
    domain = (args.domain or "").lower()
    if domain == "mentions":
        return True
    if args.market_id and "mention" in args.market_id.lower():
        return True
    meta_domain = str(meta.get("domain", "")).lower()
    return meta_domain == "mentions"


def run_politics_market(
    args: argparse.Namespace,
    meta: dict,
    *,
    mention_runner=None,
    event_fetcher=None,
    decision_agent=None,
    runtime_adapter=None,
) -> dict:
    from core.politics.router import get_politics_router
    from core.politics.models import PoliticsRouterInput
    from core.politics.apps.politics_app import run as politics_run
    from core.politics.apps.mentions_app import (
        run as mentions_run,
        MentionMarketInput,
        MentionEventInput,
        run_child_market,
        run_event_board,
    )

    runner = mention_runner or mentions_run
    if args.child_market:
        child_input = MentionMarketInput(
            source=args.source,
            market_id=args.child_market,
            title=args.title or args.child_market,
            exact_phrase=meta.get("exact_phrase", ""),
            speaker=meta.get("speaker", ""),
            venue=meta.get("venue", ""),
            resolution_window=meta.get("resolution_window", ""),
            current_price_yes=args.price_yes,
            raw_metadata=meta,
        )
        return run_child_market(
            child_input,
            mention_runner=runner,
            runtime_adapter=runtime_adapter,
            decision_agent=decision_agent,
            metadata=meta,
        )

    if _is_event_level_mention_request(args, meta):
        event_input = MentionEventInput(
            source=args.source,
            market_id=args.market_id,
            title=args.title or args.market_id,
            speaker=meta.get("speaker", ""),
            venue=meta.get("venue", ""),
            resolution_window=meta.get("resolution_window", ""),
            metadata=meta,
        )
        return run_event_board(
            event_input,
            runtime_adapter=runtime_adapter,
            market_fetcher=event_fetcher,
            mention_runner=runner,
            decision_agent=decision_agent,
        )

    title = args.title or args.market_id
    inp = PoliticsRouterInput(
        source=args.source,
        market_id=args.market_id,
        title=title,
        description=meta.get("description", ""),
        current_price_yes=args.price_yes,
    )

    router = get_politics_router()
    route = router.route(inp)

    if route.target_app == "mentions_app":
        mention_inp = MentionMarketInput(
            source=args.source,
            market_id=args.market_id,
            title=title,
            exact_phrase=meta.get("exact_phrase", ""),
            speaker=meta.get("speaker", ""),
            venue=meta.get("venue", ""),
            resolution_window=meta.get("resolution_window", ""),
            current_price_yes=args.price_yes,
        )
        output = runner(mention_inp)
        return {
            "market_id": args.market_id,
            "routed_to": "mentions_app",
            "fair_yes": round(output.fair_yes, 4),
            "confidence": output.confidence,
            "recommendation": output.recommendation,
            "reasoning": output.reasoning,
            "watch_for": output.watch_for,
            "no_bet_flag": output.no_bet_flag,
            "no_bet_reason": output.no_bet_reason,
            "notes": output.notes,
            "source_diagnostics": output.source_diagnostics,
            "runtime_context": output.runtime_context,
        }
    elif route.target_app == "politics_app":
        inp.market_type = route.market_type
        inp.jurisdiction = route.jurisdiction
        output = politics_run(inp)
        return {
            "market_id": args.market_id,
            "routed_to": "politics_app",
            "market_type": output.market_type.value,
            "fair_probability": round(output.fair_probability, 4),
            "edge": round(output.edge, 4),
            "edge_cents": round(output.edge * 100, 2),
            "confidence": round(output.confidence, 4),
            "recommendation": output.recommendation,
            "no_bet_flag": output.no_bet_flag,
            "no_bet_reason": output.no_bet_reason,
            "notes": output.notes,
            "extra": {k: v for k, v in output.extra.items() if k != "intel_report"},
        }
    else:
        return {
            "market_id": args.market_id,
            "routed_to": "unknown",
            "reject_reason": route.reject_reason,
            "classification_confidence": route.classification_confidence,
        }


def _apply_snapshot(args: argparse.Namespace, snap) -> None:
    """Fill in args from a MarketSnapshot (Kalshi fetch result)."""
    if not args.market_id or args.market_id == "UNKNOWN":
        args.market_id = snap.ticker
    if not args.title:
        args.title = snap.title or snap.ticker
    if args.price_yes is None and snap.current_price_yes is not None:
        args.price_yes = snap.current_price_yes
    if args.domain is None:
        args.domain = snap.domain if snap.domain in ("sports", "politics", "mentions", "macro") else None
    # Inject mention-specific fields into meta
    try:
        meta = json.loads(args.meta) if args.meta != "{}" else {}
    except Exception:
        meta = {}
    if snap.exact_phrase and "exact_phrase" not in meta:
        meta["exact_phrase"] = snap.exact_phrase
    if snap.speaker and "speaker" not in meta:
        meta["speaker"] = snap.speaker
    if snap.venue and "venue" not in meta:
        meta["venue"] = snap.venue
    if snap.close_time and "resolution_window" not in meta:
        meta["resolution_window"] = snap.close_time
    args.meta = json.dumps(meta)
    args.source = "kalshi"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a market through the companion pipeline")
    parser.add_argument("--url", default=None, help="Kalshi market URL (auto-fetches all data)")
    parser.add_argument("--source", default="manual")
    parser.add_argument("--market-id", default="UNKNOWN")
    parser.add_argument("--child-market", default=None, help="Explicit child mention ticker (debug helper mode)")
    parser.add_argument("--title", default=None, help="Market title (required for politics)")
    parser.add_argument("--league", default=None)
    parser.add_argument("--market-type", default=None)
    parser.add_argument("--phase", default="pre_game", choices=["pre_game", "live", "futures"])
    parser.add_argument("--price-yes", type=float, default=None, help="Current market price (0-1)")
    parser.add_argument("--domain", default=None, choices=["sports", "politics", "mentions", "macro"],
                        help="Override domain (auto-detected if omitted)")
    parser.add_argument("--meta", default="{}", help="JSON string of app-specific metadata")
    parser.add_argument("--bankroll", type=float, default=1000.0)
    parser.add_argument("--odds", type=float, default=-110)
    args = parser.parse_args()

    # Auto-fetch from URL if provided
    if args.url:
        try:
            from core.scrapers.kalshi_fetcher import KalshiMarketFetcher
            fetcher = KalshiMarketFetcher()
            snap = fetcher.fetch_from_url(args.url)
            if snap.error:
                print(json.dumps({"error": f"Kalshi fetch failed: {snap.error}"}))
                sys.exit(1)
            _apply_snapshot(args, snap)
            # Print what we fetched
            print(json.dumps({
                "_fetched": {
                    "ticker": snap.ticker,
                    "phrase": snap.exact_phrase,
                    "speaker": snap.speaker,
                    "venue": snap.venue,
                    "price_yes": snap.current_price_yes,
                    "bid": snap.yes_bid,
                    "ask": snap.yes_ask,
                    "volume": snap.volume,
                    "close_time": snap.close_time,
                    "domain": snap.domain,
                }
            }, indent=2), file=sys.stderr)
        except Exception as e:
            print(json.dumps({"error": f"URL fetch failed: {e}"}))
            sys.exit(1)

    # Support piped JSON
    piped = sys.stdin.read().strip() if not sys.stdin.isatty() else ""
    if piped:
        data = json.loads(piped)
        for key, val in data.items():
            attr = key.replace("-", "_")
            if hasattr(args, attr):
                setattr(args, attr, val)
        args.meta = json.dumps(data.get("meta", {}))

    try:
        meta = json.loads(args.meta)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"invalid --meta JSON: {e}"}))
        sys.exit(1)

    # Auto-detect domain
    domain = args.domain
    if domain is None:
        if args.league:
            domain = "sports"
        elif args.title:
            domain = "politics"
        else:
            domain = "sports"
    args.domain = domain

    try:
        if domain == "sports":
            result = run_sports_market(args, meta)
        else:
            result = run_politics_market(args, meta)
    except Exception as e:
        import traceback
        print(json.dumps({"error": str(e), "traceback": traceback.format_exc()}))
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
