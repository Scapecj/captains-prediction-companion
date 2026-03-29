"""Sports orchestration layers: Pre-game Planner, Live Executor, Review Analyst.

These coordinate the companion router + app registry + shared infra
across the full pre-game → live → futures lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from core.sports.companion_router import CompanionRouter, RouterInput, RouterOutput
from core.sports.config import DEFAULT_SPORTS_CONFIG, SportsConfig


# ---------------------------------------------------------------------------
# Pre-game Planner
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class PreGamePlan:
    league: str
    app: str
    inputs: list[RouterInput] = field(default_factory=list)
    outputs: list[RouterOutput] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


class SportsPreGamePlanner:
    """Collect candidate markets for a slate of games and run them through
    the companion router, filtering by min EV and Kelly cap.

    Parameters
    ----------
    router:
        Configured CompanionRouter with registered app runners.
    config:
        SportsConfig instance.
    bankroll:
        Current bankroll for Kelly sizing.
    """

    def __init__(
        self,
        router: CompanionRouter,
        *,
        config: SportsConfig = DEFAULT_SPORTS_CONFIG,
        bankroll: float = 1000.0,
    ) -> None:
        self.router = router
        self.config = config
        self.bankroll = bankroll

    def run(self, markets: Iterable[RouterInput]) -> list[PreGamePlan]:
        """Evaluate a set of pre-game markets and return per-league plans."""
        cfg = self.config.pre_game
        plans: dict[str, PreGamePlan] = {}
        bets_per_game: dict[str, int] = {}

        for inp in markets:
            route = self.router.classify(inp)
            league = route.league or "UNKNOWN"
            app = route.app or "unrouted"
            game_key = f"{league}:{inp.market_id or inp.title or 'unknown'}"

            plan = plans.setdefault(league, PreGamePlan(league=league, app=app))

            output = self.router.dispatch(inp)

            if output.no_bet_flag:
                plan.skipped.append(f"no_bet: {inp.market_id or inp.title}")
                continue

            ev = output.expected_value
            if ev < cfg.min_ev_pct:
                plan.skipped.append(f"ev_too_low ({ev:.3f}): {inp.market_id or inp.title}")
                continue

            if bets_per_game.get(game_key, 0) >= cfg.max_bets_per_game:
                plan.skipped.append(f"max_bets_per_game: {inp.market_id or inp.title}")
                continue

            plan.inputs.append(inp)
            plan.outputs.append(output)
            bets_per_game[game_key] = bets_per_game.get(game_key, 0) + 1

        return list(plans.values())


# ---------------------------------------------------------------------------
# Live Executor
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class LiveDecision:
    market_id: str | None
    app: str
    output: RouterOutput
    approved: bool
    reason: str


class SportsLiveExecutor:
    """Process live/in-play markets with tighter EV and exposure constraints."""

    def __init__(
        self,
        router: CompanionRouter,
        *,
        config: SportsConfig = DEFAULT_SPORTS_CONFIG,
        current_live_exposure: float = 0.0,
        bankroll: float = 1000.0,
    ) -> None:
        self.router = router
        self.config = config
        self.current_live_exposure = current_live_exposure
        self.bankroll = bankroll

    def evaluate(self, inp: RouterInput) -> LiveDecision:
        cfg = self.config.live
        route = self.router.classify(inp)
        output = self.router.dispatch(inp)

        # Check drawdown pause
        exposure_pct = self.current_live_exposure / self.bankroll if self.bankroll else 0
        if exposure_pct >= cfg.pause_on_drawdown_pct:
            return LiveDecision(
                market_id=inp.market_id,
                app=route.app or "unrouted",
                output=output,
                approved=False,
                reason=f"live exposure {exposure_pct:.2%} ≥ pause threshold {cfg.pause_on_drawdown_pct:.2%}",
            )

        ev = output.expected_value
        if ev < cfg.min_ev_pct_in_play:
            return LiveDecision(
                market_id=inp.market_id,
                app=route.app or "unrouted",
                output=output,
                approved=False,
                reason=f"live EV {ev:.3f} < min {cfg.min_ev_pct_in_play}",
            )

        if output.no_bet_flag:
            return LiveDecision(
                market_id=inp.market_id,
                app=route.app or "unrouted",
                output=output,
                approved=False,
                reason="app returned no_bet_flag",
            )

        return LiveDecision(
            market_id=inp.market_id,
            app=route.app or "unrouted",
            output=output,
            approved=True,
            reason="passed live EV and exposure checks",
        )


# ---------------------------------------------------------------------------
# Review Analyst (CLV / calibration post-game)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ReviewReport:
    records_evaluated: int
    avg_clv: float | None
    avg_edge: float
    no_bet_rate: float
    notes: list[str] = field(default_factory=list)


class SportsReviewAnalyst:
    """Post-game / end-of-session review layer.

    Accepts a list of RouterOutput objects and produces a summary report
    covering CLV, EV accuracy, and no-bet rate.
    """

    def analyze(self, outputs: list[RouterOutput]) -> ReviewReport:
        if not outputs:
            return ReviewReport(
                records_evaluated=0,
                avg_clv=None,
                avg_edge=0.0,
                no_bet_rate=0.0,
                notes=["No outputs to analyze"],
            )

        edges = [o.edge for o in outputs]
        no_bet_count = sum(1 for o in outputs if o.no_bet_flag)
        avg_edge = sum(edges) / len(edges) if edges else 0.0
        no_bet_rate = no_bet_count / len(outputs)

        notes: list[str] = []
        if avg_edge < 0:
            notes.append("WARNING: average edge is negative — review model inputs")
        if no_bet_rate > 0.7:
            notes.append("High no-bet rate (>70%) — consider loosening filters or reviewing data quality")

        return ReviewReport(
            records_evaluated=len(outputs),
            avg_clv=None,  # Attach CLV after closing prices are known
            avg_edge=avg_edge,
            no_bet_rate=no_bet_rate,
            notes=notes,
        )
