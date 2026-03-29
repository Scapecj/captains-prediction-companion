---
name: Football Game App
description: Alpha pipeline for NFL and NCAA Football game markets (spreads, totals, moneylines, live). Use when analyzing or pricing a football game market. Invoked automatically by the companion router for NFL and NCAA_FB leagues.
triggers:
  - "analyze NFL game"
  - "football spread"
  - "football total"
  - "NCAA football"
  - "football moneyline"
---

# Football Game App

Handles: **NFL** and **NCAA_FB** — sides, spreads, totals, and live game-state pricing.

## Input Signals

### Pre-game
| Signal | Field | Notes |
|--------|-------|-------|
| EPA differential | `epa_differential` | Home - Away EPA per play |
| Offensive/defensive efficiency | `efficiency_differential` | Net rating |
| QB status (home) | `qb_status_home` | "active" / "questionable" / "out" |
| QB status (away) | `qb_status_away` | Same |
| Injury flag | `injury_flag` | True if key skill positions affected |
| Wind speed | `weather_wind_mph` | MPH — >20 discounts total |
| Precipitation | `weather_precipitation` | Bool |
| Market spread | `market_spread` | Book's spread for calibration |
| Market total | `market_total` | Book's total for calibration |

### Live
| Signal | Field | Notes |
|--------|-------|-------|
| Score | `score_home`, `score_away` | Current score |
| Clock | `clock_seconds_remaining` | Seconds left in game |
| Possession | `possession` | "home" / "away" |

## Standard Output

```python
RouterOutput(
    fair_probability=0.54,
    edge=0.04,
    confidence=0.65,
    extra={
        "fair_spread": -3.5,
        "fair_total": 44.2,
        "injury_adjusted_edge": 0.04,
    }
)
```

## Workflow

1. Router dispatches to `football_game_app.run(inp)` from `backend/core/sports/apps/football_game_app.py`
2. Build context via `build_context(inp)` — extracts all signals from `raw_metadata`
3. Price via `_price_pregame()` or `_price_live()` depending on `phase`
4. Apply QB injury adjustment and weather discount to total
5. Return `RouterOutput` with edge, confidence, and extra fields

## Data Sources

- **The Odds API** — consensus market odds
- **nflverse** — NFL EPA, efficiency, schedule (NFL only)
- **Perplexity** — injury/weather confirmation
- **Playwright Scraper** — official injury reports

## Key Rules

- **QB out on home team** → subtract ~4pp from home edge
- **Wind > 20 mph** → discount total by 0.15 × (wind - 20), max 3 pts
- **Precipitation** → additional 1.5 pt discount to total
- **Confidence floor** = 0.45 — below this, `no_bet_flag = True`
- **Min edge** = 0.02 — below this, `no_bet_flag = True`

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/run_pipeline_stub.py` | Test the pipeline with sample data |
| `scripts/extract_market_metadata.py` | Extract Kalshi/Polymarket football market fields |
