---
name: Basketball Game App
description: Alpha pipeline for NBA and NCAA Men's Basketball game markets (spreads, totals, moneylines, live). Invoked automatically by the companion router for NBA and NCAA_BB leagues.
triggers:
  - "analyze NBA game"
  - "basketball spread"
  - "basketball total"
  - "NCAA basketball"
  - "basketball moneyline"
---

# Basketball Game App

Handles: **NBA** and **NCAA_BB** — sides, spreads, totals, and live game-state pricing.

## Input Signals

### Pre-game
| Signal | Field | Notes |
|--------|-------|-------|
| Pace (home) | `pace_home` | Possessions per 40 min |
| Pace (away) | `pace_away` | |
| Net rating diff | `ortg_differential` | Home - Away offensive net rating |
| Rest days (home) | `rest_days_home` | Days since last game |
| Rest days (away) | `rest_days_away` | |
| Back-to-back home | `back_to_back_home` | Bool |
| Back-to-back away | `back_to_back_away` | Bool |
| Lineup flag | `lineup_flag` | True if key players missing |
| Market total | `market_total` | |

### Live
| Signal | Field | Notes |
|--------|-------|-------|
| Score | `score_home`, `score_away` | |
| Foul trouble | `foul_trouble_home`, `foul_trouble_away` | Bool |

## Standard Output

```python
RouterOutput(
    fair_probability=0.56,
    edge=0.06,
    confidence=0.62,
    extra={
        "fair_total": 228.5,
        "volatility_flag": False,
    }
)
```

## Workflow

1. Router dispatches to `basketball_game_app.run(inp)`
2. Build context via `build_context(inp)`
3. Apply rest/travel adjustment (~0.8pp per extra rest day, -3pp for back-to-back)
4. Estimate total from pace data
5. Return RouterOutput with fair_total and volatility_flag

## Key Rules

- **Back-to-back** → -3pp for team on B2B, +3pp for fresh opponent
- **Key lineup absence** → confidence -12pp
- **Foul trouble live** → volatility_flag = True
- **Min edge** = 0.02, **confidence floor** = 0.45
