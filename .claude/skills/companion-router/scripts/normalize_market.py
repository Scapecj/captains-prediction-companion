#!/usr/bin/env python3
"""Normalize raw market metadata into a canonical RouterInput.

Handles league alias resolution, phase inference, and market_type coercion.

Usage:
    cd backend
    echo '{"league":"NATIONAL FOOTBALL LEAGUE","market_type":"game spread"}' \
        | uv run python ../.claude/skills/companion-router/scripts/normalize_market.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

backend_root = Path(__file__).parent.parent.parent.parent.parent / "backend"
sys.path.insert(0, str(backend_root))

from core.sports.config import normalize_league_name, LEAGUE_ALIASES
from core.sports.app_registry import KALSHI_NASCAR_SERIES_MARKETS


MARKET_TYPE_NORMALIZATIONS: dict[str, str] = {
    "game spread": "spread",
    "point spread": "spread",
    "puck line": "spread",
    "run line": "spread",
    "game total": "total",
    "over under": "total",
    "o/u": "total",
    "game moneyline": "moneyline",
    "money line": "moneyline",
    "ml": "moneyline",
    "race winner": "race_winner",
    "win outright": "race_winner",
    "top 3": "top3",
    "podium": "top3",
    "series champion": "series_champion",
    "championship winner": "series_champion",
    "futures": "futures",
    "player prop": "player_prop",
    "player props": "player_prop",
    "home run": "player_prop",
    "strikeout": "player_prop",
}

PHASE_KEYWORDS: dict[str, str] = {
    "live": "live",
    "in_play": "live",
    "in-play": "live",
    "inplay": "live",
    "futures": "futures",
    "champion": "futures",
    "series": "futures",
    "season": "futures",
}


def normalize_market_type(raw: str) -> str:
    clean = raw.strip().lower()
    return MARKET_TYPE_NORMALIZATIONS.get(clean, clean.replace(" ", "_"))


def infer_phase(raw_phase: str | None, market_type: str, title: str) -> str:
    if raw_phase:
        rp = raw_phase.lower()
        if rp in ("live", "in_play", "futures", "pre_game"):
            return rp
    combined = f"{market_type} {title}".lower()
    for kw, phase in PHASE_KEYWORDS.items():
        if kw in combined:
            return phase
    return "pre_game"


def normalize(raw: dict) -> dict:
    """Return a normalized metadata dict ready for RouterInput construction."""
    league_raw = raw.get("league") or raw.get("sport") or ""
    league = normalize_league_name(league_raw) or league_raw

    market_type_raw = raw.get("market_type") or ""
    market_type = normalize_market_type(market_type_raw)

    title = raw.get("title") or raw.get("name") or ""
    phase_raw = raw.get("phase")
    phase = infer_phase(phase_raw, market_type, title)

    market_id = raw.get("market_id") or raw.get("id") or ""
    is_kalshi_nascar = market_id.upper() in {k.upper() for k in KALSHI_NASCAR_SERIES_MARKETS}
    if is_kalshi_nascar:
        phase = "futures"
        market_type = "futures"

    return {
        "source": raw.get("source", "manual"),
        "market_id": market_id,
        "url": raw.get("url"),
        "league": league,
        "event_type": raw.get("event_type"),
        "market_type": market_type,
        "market_subtype": raw.get("market_subtype"),
        "phase": phase,
        "title": title,
        "is_kalshi_nascar_futures": is_kalshi_nascar,
    }


def main() -> None:
    raw = json.load(sys.stdin)
    result = normalize(raw)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
