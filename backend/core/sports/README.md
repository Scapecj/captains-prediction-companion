# Sports intelligence layer

This package scaffolds the sports section of the prediction-market agent.

It currently provides:

- Canonical league IDs and alias normalization
- Season-aware active-sport routing
- Typed market and decision models
- Generic helpers for:
  - CLV tracking
  - Consensus price building
  - Injury / lineup / weather gating
  - Monte Carlo pricing
  - Calibration reporting
  - No-bet classification

Recommended source stack:

- `Perplexity` first for research, discovery, and source-finding
- built-in `Playwright Scraper Skill` second for public pages, official docs, and source verification without another paid API
- `The Odds API` for cross-book consensus odds and implied probabilities
- `nflverse` for public NFL historical data
- `MLB Stats API` and `Baseball Savant` for MLB schedules, game state, and prop modeling
- `Sportradar` and `SportsDataIO` for premium multi-league live feeds, injuries, and odds
- `NCAA Official` as a limited fallback for NCAA schedules and game context
- `Weather API` as an auxiliary gate for weather-sensitive leagues and MLB props

Fallback order is encoded in `core.sports.providers`:

- `research` routes start with `Perplexity`, then the built-in scraper skill
- league-level `SPORTS_PROVIDER_MATRIX`
- MLB prop-specific overrides in `SPORTS_PROP_FALLBACKS`
- flattened `SPORTS_FALLBACK_ORDER` for UI/debugging

Planned next steps are to connect real schedule, market, and live-data providers for:

- pre-game modeling
- live / in-play execution
- futures handling
- MLB prop specialization
