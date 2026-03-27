"""Shared path constants and URLs for the backend."""

from pathlib import Path

# Backend root (where pyproject.toml lives)
BACKEND_ROOT = Path(__file__).parent.parent

# Project root (parent of backend/)
PROJECT_ROOT = BACKEND_ROOT.parent

# Data directory (at project root, shared)
DATA_DIR = PROJECT_ROOT / "data"
LIVE_DIR = DATA_DIR / "_live"
SEED_DIR = DATA_DIR / "_seed"

# =============================================================================
# External API URLs
# =============================================================================

# Polymarket Gamma API (REST)
GAMMA_API_BASE_URL = "https://gamma-api.polymarket.com"

# Polymarket CLOB API (WebSocket)
CLOB_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

# =============================================================================
# Portfolio Configuration
# =============================================================================

# Tier thresholds: (min_coverage, tier_number, label)
# Used by both REST endpoints and WebSocket updates for consistent classification
TIER_THRESHOLDS = [
    (0.95, 1, "HIGH_COVERAGE"),
    (0.90, 2, "GOOD_COVERAGE"),
    (0.85, 3, "MODERATE_COVERAGE"),
    (0.00, 4, "LOW_COVERAGE"),
]

# Minimum coverage for portfolio inclusion in REST API responses
# Portfolios below this threshold are filtered out (tier 4)
MIN_COVERAGE = 0.85
