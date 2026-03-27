"""Canonical sports configuration and league registry."""

from __future__ import annotations

from dataclasses import dataclass, field

CANONICAL_LEAGUES: dict[str, str] = {
    "NFL": "NFL",
    "NCAA_FB": "NCAA_FOOTBALL_MEN",
    "NCAA_BB": "NCAA_BASKETBALL_MEN",
    "NBA": "NBA",
    "MLB": "MLB",
    "NCAA_BASEBALL": "NCAA_BASEBALL_MEN",
    "UFC": "UFC_MMA",
    "NASCAR_TRUCKS": "NASCAR_TRUCKS",
    "NASCAR_OREILLY": "NASCAR_OREILLY",
    "NASCAR_CUP": "NASCAR_CUP",
}

LEAGUE_ID_BY_NAME: dict[str, str] = {value: key for key, value in CANONICAL_LEAGUES.items()}

LEAGUE_ALIASES: dict[str, str] = {
    "NATIONAL FOOTBALL LEAGUE": "NFL",
    "NCAA FOOTBALL": "NCAA_FB",
    "COLLEGE FOOTBALL": "NCAA_FB",
    "NCAA MEN'S BASKETBALL": "NCAA_BB",
    "COLLEGE BASKETBALL": "NCAA_BB",
    "NBA BASKETBALL": "NBA",
    "MAJOR LEAGUE BASEBALL": "MLB",
    "NCAA BASEBALL": "NCAA_BASEBALL",
    "MMA": "UFC",
    "UFC MMA": "UFC",
    "NASCAR TRUCK SERIES": "NASCAR_TRUCKS",
    "TRUCK SERIES": "NASCAR_TRUCKS",
    "NASCAR CUP SERIES": "NASCAR_CUP",
    "CUP SERIES": "NASCAR_CUP",
    "NASCAR AUTO PARTS SERIES": "NASCAR_OREILLY",
    "NASCAR O'REILLY AUTO PARTS SERIES": "NASCAR_OREILLY",
    "NASCAR OREILLY SERIES": "NASCAR_OREILLY",
    "OREILLY SERIES": "NASCAR_OREILLY",
    "XFINITY SERIES": "NASCAR_OREILLY",
    "XFINITY": "NASCAR_OREILLY",
}

DEFAULT_PREFERRED_SPORTS: tuple[str, ...] = (
    "NFL",
    "NCAA_BB",
    "NBA",
    "MLB",
    "UFC",
    "NASCAR_TRUCKS",
    "NASCAR_OREILLY",
    "NASCAR_CUP",
    "NCAA_FB",
    "NCAA_BASEBALL",
)

MARKET_SUBTYPES: tuple[str, ...] = (
    "nfl_moneyline",
    "nfl_spread",
    "nfl_total",
    "ncaa_fb_moneyline",
    "ncaa_fb_spread",
    "ncaa_fb_total",
    "nba_moneyline",
    "nba_spread",
    "nba_total",
    "ncaa_bb_moneyline",
    "ncaa_bb_spread",
    "ncaa_bb_total",
    "mlb_moneyline",
    "mlb_total",
    "mlb_home_run_prop",
    "mlb_pitcher_strikeout_prop",
    "ncaa_baseball_moneyline",
    "ncaa_baseball_total",
    "ufc_moneyline",
    "ufc_method",
    "nascar_race_winner",
    "nascar_top3",
    "nascar_series_champion",
)


@dataclass(frozen=True, slots=True)
class SportsRoutingConfig:
    preferred_sports: tuple[str, ...] = DEFAULT_PREFERRED_SPORTS
    min_games_per_league: int = 1
    max_active_sports: int = 4
    date_range_days: int = 1


@dataclass(frozen=True, slots=True)
class SportsAdvancedConfig:
    clv_tracking: bool = True
    closing_price_capture_minutes_before_lock: int = 5
    cross_market_consensus: bool = True
    stale_price_threshold_prob: float = 0.02
    injury_lineup_weather_gate: bool = True
    news_reaction_mode: str = "event_driven"
    monte_carlo_enabled: bool = True
    monte_carlo_runs_pre_game: int = 20_000
    monte_carlo_runs_live: int = 5_000
    calibration_reporting: bool = True
    no_bet_classifier: bool = True
    save_market_state_labels: bool = True


@dataclass(frozen=True, slots=True)
class SportsPreGameConfig:
    use_active_sports: bool = True
    default_leagues_if_none: tuple[str, ...] = ("MLB", "UFC")
    min_ev_pct: float = 0.02
    max_kelly_frac: float = 0.25
    max_bets_per_game: int = 3


@dataclass(frozen=True, slots=True)
class SportsLiveConfig:
    use_active_sports: bool = True
    min_ev_pct_in_play: float = 0.05
    max_live_exposure_pct: float = 0.30
    polling_interval_seconds: int = 20
    pause_on_drawdown_pct: float = 0.15


@dataclass(frozen=True, slots=True)
class SportsFuturesConfig:
    enabled: bool = True
    min_ev_pct_futures: float = 0.03
    max_kelly_frac_futures: float = 0.15
    max_open_series_markets: int = 3


@dataclass(frozen=True, slots=True)
class SportSkillSpec:
    skill: str
    features: tuple[str, ...]
    child_skills: tuple[str, ...] = ()


SPORTS_SKILL_REGISTRY: dict[str, SportSkillSpec] = {
    "NFL": SportSkillSpec(
        skill="football_efficiency_skill",
        features=("epa", "efficiency", "qb_status", "injuries", "weather"),
    ),
    "NCAA_FB": SportSkillSpec(
        skill="football_efficiency_skill",
        features=("epa", "efficiency", "qb_status", "injuries", "weather"),
    ),
    "NBA": SportSkillSpec(
        skill="basketball_tempo_rotation_skill",
        features=("pace", "efficiency", "rest", "travel", "lineup_status"),
    ),
    "NCAA_BB": SportSkillSpec(
        skill="basketball_tempo_rotation_skill",
        features=("pace", "efficiency", "availability", "travel", "tempo"),
    ),
    "MLB": SportSkillSpec(
        skill="baseball_pitcher_weather_skill",
        child_skills=("mlb_home_run_prop_skill", "mlb_strikeout_prop_skill"),
        features=(
            "starter_projection",
            "lineup_handedness",
            "weather",
            "bullpen_state",
            "park_factor",
        ),
    ),
    "NCAA_BASEBALL": SportSkillSpec(
        skill="baseball_pitcher_weather_skill",
        features=("starter_projection", "lineup_handedness", "weather", "bullpen_state"),
    ),
    "UFC": SportSkillSpec(
        skill="ufc_style_matchup_skill",
        features=("striking", "defense", "grappling", "takedowns", "form"),
    ),
    "NASCAR_CUP": SportSkillSpec(
        skill="nascar_practice_track_skill",
        features=("practice_speed", "lap_averages", "tire_falloff", "track_type", "season_form"),
    ),
    "NASCAR_TRUCKS": SportSkillSpec(
        skill="nascar_practice_track_skill",
        features=("practice_speed", "lap_averages", "tire_falloff", "track_type", "season_form"),
    ),
    "NASCAR_OREILLY": SportSkillSpec(
        skill="nascar_practice_track_skill",
        features=("practice_speed", "lap_averages", "tire_falloff", "track_type", "season_form"),
    ),
}

SPORTS_ROUTING_CONFIG = SportsRoutingConfig()
SPORTS_ADVANCED_CONFIG = SportsAdvancedConfig()
SPORTS_PRE_GAME_CONFIG = SportsPreGameConfig()
SPORTS_LIVE_CONFIG = SportsLiveConfig()
SPORTS_FUTURES_CONFIG = SportsFuturesConfig()


@dataclass(frozen=True, slots=True)
class SportsConfig:
    routing: SportsRoutingConfig = SPORTS_ROUTING_CONFIG
    advanced: SportsAdvancedConfig = SPORTS_ADVANCED_CONFIG
    pre_game: SportsPreGameConfig = SPORTS_PRE_GAME_CONFIG
    live: SportsLiveConfig = SPORTS_LIVE_CONFIG
    futures: SportsFuturesConfig = SPORTS_FUTURES_CONFIG


DEFAULT_SPORTS_CONFIG = SportsConfig()


def canonicalize_league(league: str | None) -> str | None:
    """Return the canonical league ID if known."""
    if league is None:
        return None
    normalized = league.strip().upper()
    if normalized in CANONICAL_LEAGUES:
        return normalized
    if normalized in LEAGUE_ID_BY_NAME:
        return LEAGUE_ID_BY_NAME[normalized]
    return normalized


def normalize_league_name(raw_name: str | None) -> str | None:
    """Normalize schedule or market titles into canonical league IDs."""
    if raw_name is None:
        return None
    normalized = " ".join(raw_name.upper().replace("’", "'").split())
    return LEAGUE_ALIASES.get(normalized, canonicalize_league(normalized))
