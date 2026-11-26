"""§383 shared D1 context is separate from real baseline phase projection."""
from dataclasses import replace
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.engine import D1ContextPlan383, evaluate_baseline_context_preview, evaluate_baseline_preview
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import BASELINE_CORE_TF, BaselineResolvedInputs
from swing_trading.source_quality import ResolvedBarSnapshotV12
from test_causal_trend_candidate382 import fixture
from test_causal_indicators import AS_OF
import test_baseline_engine375 as prev


def model(rows):
    k = fixture()[0].market_bar_key
    return BaselineResolvedInputs(k.instrument_id, k.exchange, AS_OF, False,
        tuple((tf, rows if tf is Timeframe.D1 else ()) for tf in BASELINE_CORE_TF))


def plan(direction=1):
    highs, lows = ((10,30),(20,40)) if direction > 0 else ((20,40),(10,30))
    return D1ContextPlan383(10, highs, lows, 1, 1, TiePolicy.STRICT_V1)


class SharedD1Context383Tests(unittest.TestCase):
    def test_only_source_traced_current_context_and_no_strategy_duplicate(self):
        expected = {("B2","R0"),("B2","R_F"),("B7","R0"),("B7","R_F"),
                    ("S2","R0"),("S2","R_F"),("S3","R0")}
        for direction in (1,-1):
            result = evaluate_baseline_context_preview(model(fixture(direction)), trend_plan=plan(direction))
            rows = result["d1_context_phase_references"]
            self.assertEqual(len(rows), 7)
            self.assertEqual({(r["zone_id"],r["phase"]) for r in rows}, expected)
            for r in rows:
                aligned = (r["expected_direction"] == ("UP" if direction > 0 else "DOWN"))
                self.assertEqual(r["observation"], "DIRECTION_ALIGNED_ONLY" if aligned else "OPPOSITE_DIRECTION_ONLY")
                self.assertFalse(r["phase_verified"])
                self.assertFalse(r["historical_trend_preserved"])
                self.assertFalse(r["action_eligible"])
                self.assertNotIn("strategy",r)

    def test_existing_phase_projection_and_authority_unchanged(self):
        inputs = model(fixture())
        requests = (prev.request("B2",object()),)
        original = evaluate_baseline_preview(inputs, requests=requests).safe_phase_summary()
        projected = evaluate_baseline_context_preview(inputs, trend_plan=plan(), requests=requests)
        self.assertEqual(original["zones"],projected["zones"])
        self.assertEqual(projected["decision"],"NO_TRADE")
        self.assertEqual(projected["publication_state"],"INCOMPLETE_REPORT")
        self.assertFalse(projected["detector_parity_verified"])
        self.assertFalse(projected["source_released"])
        self.assertEqual(projected["trade_orders"],0)

    def test_missing_and_conflict_no_older_window_fallback(self):
        rows = fixture()
        conflict = ResolvedBarSnapshotV12(rows[-1].market_bar_key,None,2,"SOURCE_OR_REVISION_CONFLICT")
        for sequence in ((), rows[:-1], rows[:-1]+(conflict,)):
            result = evaluate_baseline_context_preview(model(sequence),trend_plan=plan())
            self.assertEqual(result["shared_d1_context"]["relation"],"BLOCKED_INPUT")
            self.assertTrue(all(r["observation"]=="CONTEXT_UNRESOLVED"
                                for r in result["d1_context_phase_references"]))

    def test_detached_plan_rejected_and_no_secret_output(self):
        inputs = model(fixture())
        result = evaluate_baseline_context_preview(inputs,trend_plan=plan())
        with self.assertRaises(TypeError):
            evaluate_baseline_context_preview(inputs,trend_plan=result["shared_d1_context"])
        with self.assertRaises(ValueError):
            evaluate_baseline_context_preview(inputs,trend_plan=replace(plan(),lookback=True))
        for forbidden in (inputs.instrument_id,"pivot_price","candidate_index","raw_digest","source_revision","lookback"):
            self.assertNotIn(forbidden,json.dumps(result))

    def test_latest_suffix_and_missing_pivot_context_independent(self):
        rows = fixture()
        result = evaluate_baseline_context_preview(model(rows),trend_plan=replace(plan(),high_indices=()))
        self.assertEqual(result["shared_d1_context"]["structure"],"MISSING_PAIR")
        self.assertEqual(result["shared_d1_context"]["sma50_delta_direction"],"RISING")
        self.assertTrue(all(r["observation"]=="CONTEXT_UNRESOLVED"
                            for r in result["d1_context_phase_references"]))
