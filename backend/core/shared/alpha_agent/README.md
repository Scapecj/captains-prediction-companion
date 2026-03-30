# Alpha Agent

`alpha_agent` is the shared deterministic source-acquisition and diagnostics layer for Captain Companion.

It owns:

- API connectors for exchanges, transcripts, schedules, stats feeds, and news/event endpoints
- scraping fallbacks when stable APIs are missing
- retries, backoff, auth checks, and rate-limit handling
- schema validation
- freshness and latency tracking
- degraded mode, stale mode, and outage detection
- duplicate detection and payload sanity checks
- source health reporting

It does not own:

- fair value estimation
- trade decisioning
- sizing
- final execution decisions

## Layout

- `connectors/` — venue and feed adapters
- `scrapers/` — scraping fallbacks
- `normalizers/` — raw-to-normalized transforms
- `diagnostics/` — quality and health helpers
- `cache/` — payload and health cache support
- `health_models.py` — strict status and payload wrapper schemas
- `source_manager.py` — deterministic health classification and wrapper assembly

## Supported source categories

The current design is extensible for:

- Polymarket
- Kalshi
- transcript sources
- sports schedules
- lineups and injuries
- political event schedules
- general news and event endpoints
