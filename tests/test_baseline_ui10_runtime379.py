"""§379 same-input UI binding regressions with fictional inputs."""
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.engine import evaluate_baseline_preview
from swing_trading.baseline_ui10_runtime379 import build_baseline_ui10_runtime
from swing_trading.locked_ui10_binding import SECTION_IDS, ZONE_LEGEND, PIPELINE_STEPS, AUDIT_TOPICS
import test_baseline_engine375 as prev


class BaselineUi10Runtime379Tests(unittest.TestCase):
    def test_locked_order_and_all_zone_strategy_slots(self):
        result = build_baseline_ui10_runtime(prev.b2.model("B2"))
        self.assertEqual(result["section_ids"], SECTION_IDS)
        self.assertEqual(tuple((r["zone_id"], r["locked_legend"]) for r in result["zone_rows"]),
                         ZONE_LEGEND)
        self.assertEqual(tuple(r[1] for r in result["pipeline_steps"]), PIPELINE_STEPS)
        self.assertEqual(tuple(r[1] for r in result["audit_topics"]), AUDIT_TOPICS)
        self.assertEqual(sum(len(d["phases"]) for r in result["zone_rows"]
                             for d in r["phase_diagnostics"]), 128)

    def test_exact_execution_and_no_cross_strategy_reuse(self):
        inputs = prev.b2.model("B2", missing_h1=True)
        requests = (prev.request("B2", prev.b2.config(), Strategy.SHORT),)
        actual = build_baseline_ui10_runtime(inputs, requests=requests)
        expected = evaluate_baseline_preview(inputs, requests=requests).safe_phase_summary()
        rows = {(r["zone_id"], r["strategy"]): r["phases"] for r in expected["zones"]}
        for zone in actual["zone_rows"]:
            for branch in zone["phase_diagnostics"]:
                self.assertEqual(list(branch["phases"]), rows[(zone["zone_id"], branch["strategy"])])

    def test_detached_summary_not_accepted(self):
        inputs = prev.b2.model("B2")
        detached = evaluate_baseline_preview(inputs).safe_phase_summary()
        with self.assertRaises(TypeError):
            build_baseline_ui10_runtime(detached)
        with self.assertRaises(TypeError):
            build_baseline_ui10_runtime(inputs, phase_summary=detached)

    def test_fail_closed_and_redacted(self):
        inputs = prev.b2.model("B2")
        result = build_baseline_ui10_runtime(inputs, requests=(prev.request("B2", prev.b2.config()),))
        self.assertEqual(result["publication_state"], "INCOMPLETE_REPORT")
        self.assertEqual(result["decision"], "NO_TRADE")
        for key in ("action_eligible", "report_published", "rendered_ui", "source_released",
                    "detector_parity_verified", "step08_committed"):
            self.assertIs(result[key], False)
        for row in result["zone_rows"]:
            self.assertEqual(row["evidence"], [])
            self.assertFalse(row["eligible_for_signal"])
            self.assertEqual(row["status"], "UNVERIFIED")
        wire = json.dumps(result)
        for secret in (inputs.instrument_id, "raw_digest", "preview_id", "candidate_epsilon"):
            self.assertNotIn(secret, wire)

    def test_fresh_projection_and_readiness_from_same_input(self):
        inputs = prev.b2.model("B2", missing_h1=True)
        result = build_baseline_ui10_runtime(inputs)
        result["zone_rows"][0]["evidence"].append("fabricated")
        fresh = build_baseline_ui10_runtime(inputs)
        self.assertEqual(fresh["zone_rows"][0]["evidence"], [])
        self.assertEqual(fresh["timeframes"], inputs.safe_readiness()["timeframes"])
        self.assertEqual(fresh["source_relation"], "SAME_RESOLVED_INPUT_EXECUTION_ONLY")
