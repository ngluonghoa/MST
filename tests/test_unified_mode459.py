"""§459 identical candidate dispatch and fail-closed mode boundary."""
from dataclasses import replace
from decimal import Decimal
import json
import unittest
from unittest.mock import patch

from swing_trading.contracts import Strategy
from swing_trading.engine import evaluate_baseline_preview
from swing_trading.unified_mode459 import (
    CandidateProfile459, EngineMode, configuration_digest, evaluate_candidate,
)
import test_baseline_engine375 as prev
import test_b2s2_baseline_preview371 as b2


def profile(requests):
    return CandidateProfile459("synthetic", "v1", "a"*40,
                               configuration_digest(requests), requests)


class UnifiedMode459Tests(unittest.TestCase):
    def test_same_candidate_for_both_modes_all_32_rows(self):
        for zone in ("B2", "S2"):
            inputs = b2.model(zone)
            p = profile(tuple(prev.request(zone, b2.config(), s) for s in Strategy))
            baseline = evaluate_baseline_preview(inputs, requests=p.requests)
            for mode in (EngineMode.RESEARCH, EngineMode.VALIDATION):
                r = evaluate_candidate(inputs, mode=mode, profile=p)
                self.assertEqual(r.private_preview, baseline)
                self.assertEqual(len(r.private_preview.rows), 32)
                self.assertIs(r.private_profile, p)

    def test_production_denied_before_engine(self):
        with patch("swing_trading.unified_mode459.evaluate_baseline_preview") as engine:
            with self.assertRaisesRegex(ValueError, "PRODUCTION_NOT_QUALIFIED"):
                evaluate_candidate(None, mode=EngineMode.PRODUCTION, profile=profile(()))
            engine.assert_not_called()

    def test_exact_mode_profile_required(self):
        for mode, p in (("RESEARCH", profile(())), (EngineMode.RESEARCH, {})):
            with self.assertRaises(ValueError):
                evaluate_candidate(None, mode=mode, profile=p)

    def test_profile_digest_binds_request_variant_and_strategy(self):
        req = prev.request("B2", b2.config())
        p = profile((req,))
        for other in (replace(req, strategy=Strategy.SWING),
                      replace(req, variant_id="S2/BASE")):
            self.assertNotEqual(configuration_digest((other,)), p.configuration_sha256)
            with self.assertRaisesRegex(ValueError, "PROFILE_DIGEST_MISMATCH"):
                replace(p, requests=(other,))

    def test_deterministic_configuration_and_no_mutable_or_invalid_input(self):
        req = prev.request("B2", b2.config())
        self.assertEqual(configuration_digest((req,)), configuration_digest((replace(req),)))
        for bad in ([req], (replace(req, plan={}),), (replace(req, plan=Decimal("NaN")),)):
            with self.assertRaises(ValueError):
                configuration_digest(bad)

    def test_summary_redacted_and_no_promotion(self):
        inputs = b2.model("B2")
        p = profile((prev.request("B2", b2.config()),))
        for mode in (EngineMode.RESEARCH, EngineMode.VALIDATION):
            s = evaluate_candidate(inputs, mode=mode, profile=p).safe_summary()
            self.assertEqual(s["mode"], mode.value)
            self.assertEqual(s["decision"], "NO_TRADE")
            for flag in ("validation_qualified", "production_qualified", "publication_allowed",
                         "source_released", "detector_parity_verified", "code_identity_attested"):
                self.assertIs(s[flag], False)
            self.assertEqual(s["trade_orders"], 0)
            for private in (inputs.instrument_id, p.configuration_sha256, p.code_git_sha,
                            "candidate_epsilon", "private_profile"):
                self.assertNotIn(private, json.dumps(s))
