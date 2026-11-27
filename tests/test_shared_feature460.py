"""§460 shared feature and signal path; preserve §383 compatibility."""
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from swing_trading.engine import evaluate_baseline_context_preview
from swing_trading.feature_engine460 import inspect_current_d1_context
from swing_trading.unified_mode459 import (
    CandidateProfile459, EngineMode, configuration_digest, evaluate_candidate,
)
from test_engine_d1_context383 import model, plan
from test_causal_trend_candidate382 import fixture


def profile(trend):
    return CandidateProfile459("synthetic", "v2", "a"*40,
        configuration_digest((), trend_plan=trend), (), trend)


class SharedFeature460Tests(unittest.TestCase):
    def test_both_modes_exact_legacy_context(self):
        for direction in (1,-1):
            inputs = model(fixture(direction))
            p = profile(plan(direction))
            old = evaluate_baseline_context_preview(inputs, trend_plan=p.trend_plan)
            for mode in (EngineMode.RESEARCH, EngineMode.VALIDATION):
                s = evaluate_candidate(inputs, mode=mode, profile=p).safe_summary()
                for field in ("zones", "shared_d1_context", "d1_context_phase_references"):
                    self.assertEqual(s[field], old[field])
                self.assertFalse(s["validation_qualified"])
                self.assertFalse(s["production_qualified"])

    def test_no_missing_latest_window_fallback(self):
        inputs = model(fixture()[:-1])
        for mode in (EngineMode.RESEARCH, EngineMode.VALIDATION):
            s = evaluate_candidate(inputs, mode=mode, profile=profile(plan())).safe_summary()
            self.assertEqual(s["shared_d1_context"]["relation"], "BLOCKED_INPUT")

    def test_plan_bound_to_configuration_and_explicit(self):
        p = profile(plan())
        self.assertNotEqual(p.configuration_sha256, configuration_digest(()))
        with self.assertRaisesRegex(ValueError, "PROFILE_DIGEST_MISMATCH"):
            replace(p, trend_plan=plan(-1))
        with self.assertRaises(ValueError):
            configuration_digest((), trend_plan={})

    def test_feature_computed_once_no_duplicate_signal_or_feature(self):
        inputs = model(fixture())
        with patch("swing_trading.feature_engine460.inspect_d1_paired_trend_candidate",
                   wraps=__import__("swing_trading.causal_trend_candidate382", fromlist=["inspect_d1_paired_trend_candidate"]).inspect_d1_paired_trend_candidate) as f:
            r = evaluate_candidate(inputs, mode=EngineMode.VALIDATION, profile=profile(plan()))
            self.assertEqual(r.safe_summary(), r.safe_summary())
            self.assertEqual(f.call_count, 1)

    def test_no_feature_implicit_or_production_execution(self):
        inputs = model(fixture())
        p = profile(None)
        with patch("swing_trading.unified_mode459._current_d1_context383") as f:
            self.assertNotIn("shared_d1_context", evaluate_candidate(inputs,
                mode=EngineMode.RESEARCH, profile=p).safe_summary())
            with self.assertRaisesRegex(ValueError, "PRODUCTION_NOT_QUALIFIED"):
                evaluate_candidate(inputs, mode=EngineMode.PRODUCTION, profile=profile(plan()))
            f.assert_not_called()

    def test_direct_feature_invalid_window_and_redacted_summary(self):
        from dataclasses import asdict
        inputs = model(fixture())
        with self.assertRaisesRegex(ValueError, "MST_383_BOUNDED_LOOKBACK"):
            inspect_current_d1_context(inputs, **asdict(replace(plan(), lookback=True)))
        result = evaluate_candidate(inputs, mode=EngineMode.RESEARCH, profile=profile(plan())).safe_summary()
        for private in (inputs.instrument_id, "high_indices", "low_indices", "candidate_epsilon"):
            self.assertNotIn(private, json.dumps(result))
