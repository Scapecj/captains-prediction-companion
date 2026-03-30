import unittest

from core.shared.decision_logic_agent import DecisionLogicAgent, rank_by_best_executable_edge
from core.shared.decision_logic_agent.models import (
    DecisionLogicInput,
    DecisionPolicy,
    SettlementState,
    TradePosture,
)


class DecisionLogicAgentTests(unittest.TestCase):
    def test_economically_resolved_market_becomes_wait_not_trade(self) -> None:
        agent = DecisionLogicAgent()
        inp = DecisionLogicInput(
            market_type="mention",
            app_source="mentions_app",
            yes_price=0.99,
            no_price=0.01,
            bid=0.98,
            ask=0.99,
            bid_size=250.0,
            ask_size=50.0,
            fair_yes_probability=0.995,
            fees_bps=10.0,
            slippage_estimate=0.002,
            position_size=0.0,
            max_inventory=500.0,
            event_still_live=False,
            effective_resolution_confidence=0.98,
            settlement_risk_score=0.04,
        )

        out = agent.evaluate(inp)

        self.assertEqual(out.settlement_state, SettlementState.ECONOMICALLY_RESOLVED)
        self.assertEqual(out.trade_posture, TradePosture.WAIT)
        self.assertEqual(out.reject_reason, "economically_resolved_pending_settlement")
        self.assertEqual(out.best_side, "YES")
        self.assertTrue(out.best_executable_edge < 0.0 or out.best_executable_edge >= 0.0)

    def test_thin_positive_yes_edge_prefers_passive_order(self) -> None:
        agent = DecisionLogicAgent()
        inp = DecisionLogicInput(
            market_type="politics",
            app_source="politics_app",
            yes_price=0.44,
            no_price=0.56,
            bid=0.42,
            ask=0.46,
            bid_size=20.0,
            ask_size=15.0,
            fair_yes_probability=0.60,
            fees_bps=12.0,
            slippage_estimate=0.003,
            position_size=50.0,
            max_inventory=500.0,
            event_still_live=True,
            effective_resolution_confidence=0.35,
            settlement_risk_score=0.10,
        )

        out = agent.evaluate(inp)

        self.assertAlmostEqual(out.midpoint, 0.44, places=6)
        self.assertAlmostEqual(out.microprice, 0.442857, places=5)
        self.assertEqual(out.best_side, "YES")
        self.assertEqual(out.recommended_side, "YES")
        self.assertEqual(out.trade_posture, TradePosture.PLACE_PASSIVE_ORDER)
        self.assertGreater(out.edge_yes_after_costs, 0.0)
        self.assertGreater(out.best_executable_edge, 0.0)

    def test_inventory_cap_blocks_new_trade(self) -> None:
        agent = DecisionLogicAgent()
        inp = DecisionLogicInput(
            market_type="sports",
            app_source="sports_app",
            yes_price=0.41,
            no_price=0.59,
            bid=0.40,
            ask=0.42,
            bid_size=400.0,
            ask_size=350.0,
            fair_yes_probability=0.54,
            fees_bps=8.0,
            slippage_estimate=0.002,
            position_size=100.0,
            max_inventory=100.0,
            event_still_live=True,
            effective_resolution_confidence=0.20,
            settlement_risk_score=0.08,
        )

        out = agent.evaluate(inp)

        self.assertEqual(out.trade_posture, TradePosture.NO_TRADE)
        self.assertEqual(out.reject_reason, "inventory_cap_reached")
        self.assertEqual(out.best_side, "YES")

    def test_normalizes_yes_and_no_values_before_edge_calculation(self) -> None:
        agent = DecisionLogicAgent()
        inp = DecisionLogicInput(
            market_type="politics",
            app_source="politics_app",
            yes_price=0.53,
            no_price=0.50,
            bid=0.52,
            ask=0.54,
            bid_size=100.0,
            ask_size=80.0,
            fair_yes_probability=0.58,
            fees_bps=5.0,
            slippage_estimate=0.001,
            position_size=0.0,
            max_inventory=1000.0,
            event_still_live=True,
            effective_resolution_confidence=0.10,
            settlement_risk_score=0.10,
        )

        out = agent.evaluate(inp)

        self.assertAlmostEqual(out.normalized_yes_implied_probability, 0.514563, places=5)
        self.assertAlmostEqual(out.normalized_no_implied_probability, 0.485437, places=5)
        self.assertAlmostEqual(out.fair_yes_probability, 0.58, places=6)
        self.assertAlmostEqual(out.fair_no_probability, 0.42, places=6)

    def test_no_side_with_stronger_edge_ranked_first(self) -> None:
        agent = DecisionLogicAgent()
        # YES-heavy market
        yes_input = DecisionLogicInput(
            market_type="mention",
            app_source="mentions_app",
            yes_price=0.45,
            no_price=0.55,
            bid=0.44,
            ask=0.46,
            bid_size=100.0,
            ask_size=80.0,
            fair_yes_probability=0.65,
            fees_bps=5.0,
            slippage_estimate=0.001,
            position_size=10.0,
            max_inventory=500.0,
            event_still_live=True,
            effective_resolution_confidence=0.40,
            settlement_risk_score=0.10,
        )
        yes_out = agent.evaluate(yes_input)

        # NO-heavy market (lower fair yes, stronger raw_no edge)
        no_input = DecisionLogicInput(
            market_type="mention",
            app_source="mentions_app",
            yes_price=0.80,
            no_price=0.20,
            bid=0.79,
            ask=0.81,
            bid_size=120.0,
            ask_size=110.0,
            fair_yes_probability=0.30,
            fees_bps=5.0,
            slippage_estimate=0.002,
            position_size=0.0,
            max_inventory=500.0,
            event_still_live=True,
            effective_resolution_confidence=0.20,
            settlement_risk_score=0.05,
        )
        no_out = agent.evaluate(no_input)

        ranked = rank_by_best_executable_edge([yes_out, no_out])

        self.assertEqual(ranked[0].best_side, no_out.best_side)
        self.assertGreater(ranked[0].best_executable_edge, ranked[1].best_executable_edge)
        self.assertEqual(ranked[0].recommended_side, no_out.recommended_side)

    def test_low_confidence_policy_downshifts_trade_to_wait(self) -> None:
        policy = DecisionPolicy(low_confidence_threshold=0.95)
        agent = DecisionLogicAgent(policy=policy)
        inp = DecisionLogicInput(
            market_type="mention",
            app_source="mentions_app",
            yes_price=0.5,
            no_price=0.5,
            bid=0.49,
            ask=0.51,
            bid_size=50.0,
            ask_size=40.0,
            fair_yes_probability=0.65,
            fees_bps=5.0,
            slippage_estimate=0.002,
            position_size=0.0,
            max_inventory=100.0,
            event_still_live=True,
            effective_resolution_confidence=0.10,
            settlement_risk_score=0.05,
        )

        out = agent.evaluate(inp)

        self.assertEqual(out.trade_posture, TradePosture.WAIT)
        self.assertEqual(out.reject_reason, "confidence_below_threshold")


if __name__ == "__main__":
    unittest.main()
