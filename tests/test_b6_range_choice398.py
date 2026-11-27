"""§398 explicit range vs ATR compression method, no fallback."""
from dataclasses import replace
from decimal import Decimal as D
import json
import unittest

from swing_trading.b6_baseline_preview387 import B6CompressionPlan396, B6State387
from swing_trading.causal_compression_candidate395 import AtrPercentilePlan395
from swing_trading.causal_range_percentile397 import RangePercentilePlan397
from swing_trading.contracts import Strategy
from swing_trading.engine import BaselinePreviewRequest375, evaluate_baseline_preview
from test_b6_compression_rc396 import model, run, plan as atr_plan
from test_causal_range_percentile397 import fixture
from test_causal_indicators import snap


def plan(index=3):
    return B6CompressionPlan396(index,RangePercentilePlan397(3,D("0.5")))


class B6RangeChoice398Tests(unittest.TestCase):
    def test_both_strategies_explicit_range_only(self):
        for strategy in Strategy:
            row,safe=run(model(fixture()),plan(),strategy=strategy)
            proof=row.private_preview.assessments[0][1]
            self.assertIs(proof.state,B6State387.MATCH)
            self.assertEqual(proof.reason,"RANGE_PERCENTILE_GEOMETRY_ONLY")
            self.assertEqual(proof.compression.target_range_percent,D(2))
            self.assertEqual([p["ingredient_state"] for p in safe["phases"]],
                             ["NOT_REQUESTED","GEOMETRY_MATCH_ONLY","NOT_REQUESTED","NOT_REQUESTED"])

    def test_nonmatch_is_not_atr_fallback(self):
        row,safe=run(model(fixture(D(5))),plan())
        self.assertIs(row.private_preview.assessments[0][1].state,B6State387.NONMATCH)
        self.assertEqual(safe["phases"][1]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_exact_range_and_atr_windows_differ(self):
        data=model(fixture())
        for p in (plan(2),plan(4)):
            row,safe=run(data,p)
            self.assertEqual(row.private_preview.assessments[0][1].reason,"EXACT_RANGE_WINDOW_MISSING")
            self.assertEqual(safe["phases"][1]["ingredient_state"],"MISSING_INPUT")
        row,safe=run(data,replace(atr_plan(),target_index=3))
        self.assertEqual(row.private_preview.assessments[0][1].reason,"EXACT_ATR_WINDOW_MISSING")
        self.assertEqual(safe["phases"][1]["ingredient_state"],"MISSING_INPUT")

    def test_late_reference_and_invalid_method(self):
        rows=list(fixture())
        rows[-2]=snap(replace(rows[-2].selected,verified_at_utc=rows[-1].selected.bar_end_utc))
        _,safe=run(model(tuple(rows)),plan())
        self.assertEqual(safe["phases"][1]["ingredient_state"],"BLOCKED")
        for method in (None,{},RangePercentilePlan397(3,D(0))):
            _,safe=run(model(()),replace(plan(),percentile=method))
            self.assertTrue(all(p["ingredient_state"]=="CONFIG_REJECTED" for p in safe["phases"]))

    def test_independent_strategy_explicit_choices(self):
        data=model(fixture())
        req=(BaselinePreviewRequest375("B6",Strategy.SHORT,"B6/C_COMPRESSION",plan()),
             BaselinePreviewRequest375("B6",Strategy.SWING,"B6/C_COMPRESSION",
                                       B6CompressionPlan396(3,AtrPercentilePlan395(3,D("0.5")))))
        result=evaluate_baseline_preview(data,requests=req)
        rows={r["strategy"]:r for r in result.safe_phase_summary()["zones"] if r["zone_id"]=="B6"}
        self.assertEqual(rows["SHORT"]["phases"][1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")
        self.assertEqual(rows["SWING"]["phases"][1]["ingredient_state"],"MISSING_INPUT")
        self.assertEqual(result.decision,"NO_TRADE")

    def test_legacy_atr_and_no_public_values(self):
        old,_=run()
        self.assertEqual(old.private_preview.assessments[0][1].reason,"ATR_PERCENTILE_GEOMETRY_ONLY")
        row,safe=run(model(fixture()),plan())
        self.assertFalse(row.private_preview.action_eligible)
        self.assertEqual(row.private_preview.safe_rf_volume_summary()["volume_state"],"NOT_REQUESTED")
        for p in safe["phases"]:
            self.assertFalse(p["phase_verified"])
            self.assertFalse(p["action_eligible"])
        for secret in (model(fixture()).instrument_id,"quantile","target_range_percent","reference_count"):
            self.assertNotIn(secret,json.dumps(safe))
