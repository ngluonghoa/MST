"""§390 B6 pre-contraction D1 rising context, fictional only."""
from dataclasses import replace
from decimal import Decimal as D
import json
import unittest

from swing_trading.b6_baseline_preview387 import B6TrendPlan390, B6State387
from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import BaselineResolvedInputs
from swing_trading.source_quality import ResolvedBarSnapshotV12
from test_b6_baseline_preview387 import model, config, evaluate
from test_causal_trend_candidate382 import fixture
from test_causal_indicators import snap


def data(direction=1, *, late=False, conflict=False, missing=False):
    original=model()
    prefix=fixture(direction)
    tail=original.snapshots_for(Timeframe.D1)
    if late:
        prefix=prefix[:-1]+(snap(replace(prefix[-1].selected,
                     verified_at_utc=tail[0].selected.bar_end_utc)),)
    if conflict:
        prefix=prefix[:5]+(ResolvedBarSnapshotV12(prefix[5].market_bar_key,None,2,
                         "SOURCE_OR_REVISION_CONFLICT"),)+prefix[6:]
    if missing:
        prefix=()
    return BaselineResolvedInputs(original.instrument_id, original.exchange,
        original.as_of_utc,False,tuple((tf,prefix+tail if tf is Timeframe.D1 else rows)
                                       for tf,rows in original.buckets))


def plan(direction=1, offset=60):
    h,l=((10,30),(20,40)) if direction>0 else ((20,40),(10,30))
    return replace(config(),d1_start=offset,d1_stop=offset+26,
        atr_start=offset,atr_stop=offset+15,
        r0=B6TrendPlan390(10,h,l,1,1,TiePolicy.STRICT_V1))


class B6Trend390Tests(unittest.TestCase):
    def test_both_strategies_prior_rising_context(self):
        for strategy in Strategy:
            row,safe=evaluate(data(),strategy=strategy,cfg=plan())
            self.assertEqual([p["ingredient_state"] for p in safe["phases"]],
                ["GEOMETRY_MATCH_ONLY","GEOMETRY_MATCH_ONLY","DISTANCE_ONLY","NOT_REQUESTED"])
            r0,proof=row.private_preview.assessments[0]
            self.assertIs(r0.selected_frame,Timeframe.D1)
            self.assertEqual(proof.reason,"PRIOR_D1_RISE_AND_CONTRACTION_PIVOTS_ONLY")
            self.assertFalse(proof.action_eligible)

    def test_opposite_direction_does_not_erase_contraction(self):
        _,safe=evaluate(data(-1),cfg=plan(-1))
        self.assertEqual(safe["phases"][0]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")
        self.assertEqual(safe["phases"][1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")
        self.assertEqual(safe["status"],"UNVERIFIED")

    def test_late_or_conflicting_prefix_blocked_no_fallback(self):
        for inputs in (data(late=True),data(conflict=True)):
            _,safe=evaluate(inputs,cfg=plan())
            self.assertEqual(safe["phases"][0]["ingredient_state"],"BLOCKED")
            self.assertEqual(safe["phases"][1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_missing_window_does_not_use_contraction_bars(self):
        _,safe=evaluate(data(missing=True),cfg=plan(offset=0))
        self.assertEqual(safe["phases"][0]["ingredient_state"],"MISSING_INPUT")
        self.assertEqual(safe["phases"][1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_missing_pair_and_bad_explicit_plan(self):
        p=plan()
        _,safe=evaluate(data(),cfg=replace(p,r0=replace(p.r0,high_indices=())))
        self.assertEqual(safe["phases"][0]["ingredient_state"],"BLOCKED")
        for invalid in (replace(p.r0,lookback=True),{},replace(p.r0,tie_policy="STRICT_V1")):
            _,safe=evaluate(data(),cfg=replace(p,r0=invalid))
            self.assertTrue(all(p["ingredient_state"]=="CONFIG_REJECTED" for p in safe["phases"]))

    def test_old_plan_unchanged_and_redaction(self):
        _,old=evaluate(model(),cfg=config())
        self.assertEqual(old["phases"][0]["ingredient_state"],"NOT_REQUESTED")
        _,safe=evaluate(data(),cfg=plan())
        for secret in (data().instrument_id,"lookback","pivot_price","earlier_sma50","180"):
            self.assertNotIn(secret,json.dumps(safe))
        self.assertTrue(all(not p["phase_verified"] and not p["action_eligible"] for p in safe["phases"]))
