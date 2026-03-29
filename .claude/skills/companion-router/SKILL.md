---
name: Companion Router
description: Classify and route any sports/event market to the correct alpha app. Use when receiving a market link, market ID, event title, or raw metadata and you need to identify which alpha pipeline should evaluate it.
triggers:
  - "route this market"
  - "classify this event"
  - "what app handles"
  - "dispatch to"
  - "which pipeline"
---

# Companion Router

The companion router is the dispatcher and normalizer. It accepts raw market data from any source (Kalshi, Polymarket, direct link, title, tags) and routes it to the correct alpha app.

**The router does NOT do heavy modeling.** It classifies, normalizes, and dispatches.

## Architecture

```
RouterInput (any source)
  → CompanionRouter.classify() → RouteResult (league, app, phase, confidence)
  → CompanionRouter.dispatch() → RouterOutput (from the app)
  → Shared layers: EV, Kelly, CLV, logging
```

## Standardized Input

```python
RouterInput(
    source="kalshi",          # "kalshi" | "polymarket" | "manual"
    market_id="...",
    url="...",
    league="NFL",             # raw or canonical — router normalizes
    event_type="...",
    market_type="spread",
    market_subtype="nfl_spread",
    phase="pre_game",         # "pre_game" | "live" | "futures"
    title="Chiefs vs Eagles",
    tags=("nfl", "spread"),
    raw_metadata={},
)
```

## Standardized Output

```python
RouterOutput(
    pipeline="football_game_app",
    classification_confidence=0.92,
    fair_probability=0.54,
    market_probability=0.50,
    edge=0.04,
    expected_value=0.08,
    confidence=0.65,
    no_bet_flag=False,
    primary_signal="epa_diff=2.1",
    notes=["home QB active", "wind 8 mph"],
)
```

## Routing Priority

1. **Kalshi NASCAR futures** — exact market ID match (highest confidence: 0.98)
2. **MLB prop keywords** — "home run", "hr", "strikeout", "k prop" in title/subtype
3. **Futures phase** → NASCAR series futures app
4. **Exact league + market_type match** in app registry
5. **League-only fallback** — first registered app for the league

## App Registry

| App | Leagues | Market Types | Phases |
|-----|---------|-------------|--------|
| football_game_app | NFL, NCAA_FB | moneyline, spread, total, game | pre_game, live |
| basketball_game_app | NBA, NCAA_BB | moneyline, spread, total, game | pre_game, live |
| baseball_game_app | MLB, NCAA_BASEBALL | moneyline, total, game | pre_game |
| mlb_home_run_prop_app | MLB | player_prop, prop | pre_game |
| mlb_strikeout_prop_app | MLB | player_prop, prop | pre_game |
| ufc_fight_app | UFC | moneyline, method, round, fight | pre_game, live |
| nascar_race_app | NASCAR_* | race_winner, top3, race | pre_game, live |
| nascar_series_futures_app | NASCAR_* | futures, series_champion | futures |

## Workflow

### Step 1 — Normalize input

Run `scripts/normalize_market.py` to canonicalize league names and infer phase/market_type from raw metadata.

### Step 2 — Classify

Call `CompanionRouter.classify(inp)` to get a `RouteResult`. Log the classification confidence.

### Step 3 — Validate

If `classification_confidence < 0.70`, surface a warning and ask for more context before dispatching.

### Step 4 — Dispatch

Call `CompanionRouter.dispatch(inp)` which forwards to the registered app runner.

### Step 5 — Post-process

Pass `RouterOutput` to shared layers:
- `ev_calculator`: confirm EV threshold
- `kelly_bankroll_manager`: size the stake
- `closing_line_tracker`: record entry price for CLV
- `no_bet_classifier`: final gate before recommending

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/classify_event.py` | CLI: classify a single market from JSON input |
| `scripts/normalize_market.py` | Normalize league names and infer phase/market_type |
| `scripts/build_context.py` | Build a RouterInput from a URL, market ID, or title |
| `scripts/validate_config.py` | Validate that app registry and routing config are consistent |

## Canon League IDs

Use these exact IDs. Never use aliases in code — always call `normalize_league_name()` first.

```
NFL, NCAA_FB, NCAA_BB, NBA, MLB, NCAA_BASEBALL, UFC,
NASCAR_TRUCKS, NASCAR_OREILLY, NASCAR_CUP
```
