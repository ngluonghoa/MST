"""§462 unchanged target D1 ATR across previously coupled sell-zone paths."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import unittest

from swing_trading import s1_failed_break441, s1_choch442, s1_confirm443
from swing_trading import s1_major446, s2_context448, s3_context454, s3_tp458
from swing_trading.causal_indicators import calculate_wilder_atr14
from swing_trading.feature_engine460 import inspect_target_d1_atr
from swing_trading.market_data import Timeframe
from swing_trading.unified_mode459 import EngineMode, evaluate_candidate
from test_s1_failed_break441 import fixture as s1_fixture
from test_s3_tp458 import fixture as s3_fixture
from test_s2_rally449 import alter
from test_causal_indicators import snap
from test_baseline_engine375 import request, row
from test_unified_mode459 import profile


class SharedATR462Tests(unittest.TestCase):
    def test_all_seven_consumers_same_function_and_legacy_alias(self):
        for module in (s1_failed_break441, s1_choch442, s1_confirm443,
                       s1_major446, s2_context448, s3_context454, s3_tp458):
            self.assertIs(module._atr441, inspect_target_d1_atr)

    def test_exact_wilder_math_both_target_frames(self):
        for tf in (Timeframe.H1, Timeframe.M15):
            inputs, p = s1_fixture(tf)
            plan = p.failed
            target = inputs.snapshots_for(tf)[plan.target_index].selected
            daily = inputs.snapshots_for(Timeframe.D1)
            expected = calculate_wilder_atr14(daily[plan.atr_start:plan.atr_stop],
                as_of_utc=inputs.as_of_utc, known_before_utc=target.market_bar_key.bar_start_utc)
            actual = inspect_target_d1_atr(inputs, plan, target)
            self.assertEqual(actual, expected.value)
            self.assertGreater(actual, Decimal(0))

    def test_no_stale_window_or_missing_atr(self):
        inputs, p = s1_fixture()
        plan = p.failed
        target = inputs.snapshots_for(plan.timeframe)[plan.target_index].selected
        self.assertIsNone(inspect_target_d1_atr(inputs, replace(plan, atr_start=5, atr_stop=20), target))
        self.assertIsNone(inspect_target_d1_atr(inputs, replace(plan, atr_stop=512), target))

    def test_late_atr_revision_rejected(self):
        inputs,p = s3_fixture()
        plan = p.near
        target = inputs.snapshots_for(Timeframe.M15)[plan.target_index].selected
        daily = inputs.snapshots_for(Timeframe.D1)
        late = snap(replace(daily[0].selected, verified_at_utc=target.market_bar_key.bar_start_utc+timedelta(seconds=1)))
        self.assertIsNone(inspect_target_d1_atr(alter(inputs,Timeframe.D1,(late,)+daily[1:]),plan,target))

    def test_tp_feature_shared_in_both_modes(self):
        inputs, p = s3_fixture()
        candidate = profile((request("S3", p, variant="S3/E_TP"),))
        target = inputs.snapshots_for(Timeframe.M15)[p.near.target_index].selected
        expected = inspect_target_d1_atr(inputs, p.near, target)
        for mode in (EngineMode.RESEARCH, EngineMode.VALIDATION):
            result = evaluate_candidate(inputs, mode=mode, profile=candidate)
            preview = row(result.private_preview, "S3").private_preview
            self.assertEqual(preview.assessments[1][1].private_atr, expected)
            self.assertFalse(preview.action_eligible)

    def test_production_stays_denied(self):
        inputs, p = s3_fixture()
        candidate = profile((request("S3", p, variant="S3/E_TP"),))
        with self.assertRaisesRegex(ValueError, "PRODUCTION_NOT_QUALIFIED"):
            evaluate_candidate(inputs, mode=EngineMode.PRODUCTION, profile=candidate)
