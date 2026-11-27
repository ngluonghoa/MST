"""§403 B6 compression M15 approach to same upper pivot, fictional data."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_compression_approach403 import CompressionEarlyPlan403
from swing_trading.causal_compression_pivot402 import CompressionPivotPlan402
from swing_trading.causal_range_percentile397 import RangePercentilePlan397
from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.b6_baseline_preview387 import B6CompressionPlan396, B6State387
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import BaselineResolvedInputs
from swing_trading.source_quality import ObservationOrigin
from test_b6_compression_rc396 import model, run
from test_causal_indicators import make_bar, snap


def fixture(*, early=False, far=False, falling=False, mixed=False, higher=False, wide=False, missing=False):
    highs=[104]*15+[105,110,104,115 if higher else 103,108 if wide else 101]
    rows=tuple(snap(make_bar(i,open_price=D(100),close=D(100),high=D(h),low=D(99)))
               for i,h in enumerate(highs))
    start=rows[-2 if early else -1].market_bar_key.bar_start_utc+timedelta(days=1,hours=7)
    if early:
        start-=timedelta(hours=24)
    price=D(100) if far else D("109.5")
    prev=price+1 if falling else price-1
    m15=tuple(make_bar(100+i,timeframe=Timeframe.M15,start=start+timedelta(minutes=30*i),
                       open_price=p,close=p,high=p+1,low=p-1) for i,p in enumerate((prev,price)))
    if mixed:
        def changed(row):
            obs=replace(row.observation_key,origin=ObservationOrigin.IMPORT)
            return replace(row,observation_key=obs,observation_revision=replace(row.observation_revision,observation_key=obs))
        m15=tuple(changed(r) for r in m15)
    data=model(rows)
    return BaselineResolvedInputs(data.instrument_id,data.exchange,data.as_of_utc,False,
        tuple((tf,() if missing else tuple(snap(r) for r in m15)) if tf is Timeframe.M15
              else (tf,bucket) for tf,bucket in data.buckets))


def plan():
    return B6CompressionPlan396(19,RangePercentilePlan397(3,D("0.5")),
        upper_pivot=CompressionPivotPlan402(5,1,1,1,TiePolicy.STRICT_V1),
        early=CompressionEarlyPlan403(1,0,15,D("0.25")))


def re(row):
    return next(e for route,e in row.private_preview.assessments if route.phase=="R_E")


class CompressionEarly403Tests(unittest.TestCase):
    def test_both_strategies_same_pivot_approach(self):
        for strategy in Strategy:
            row,safe=run(fixture(),plan(),strategy=strategy)
            self.assertIs(re(row).state,B6State387.DISTANCE)
            self.assertEqual(re(row).distance,D("0.5"))
            self.assertTrue(re(row).approach)
            self.assertEqual(safe["phases"][2]["ingredient_state"],"DISTANCE_ONLY")
            self.assertEqual(safe["phases"][3]["ingredient_state"],"NOT_REQUESTED")

    def test_far_and_falling_not_approach(self):
        for data in (fixture(far=True),fixture(falling=True)):
            row,_=run(data,plan())
            self.assertIs(re(row).state,B6State387.DISTANCE)
            self.assertFalse(re(row).approach)

    def test_future_base_nonmatch_and_wrong_pivot_block(self):
        for data in (fixture(early=True),fixture(higher=True),fixture(wide=True)):
            row,safe=run(data,plan())
            self.assertIs(re(row).state,B6State387.BLOCKED)
            self.assertIsNone(re(row).distance)
            self.assertEqual(safe["phases"][2]["ingredient_state"],"BLOCKED")

    def test_mixed_source_and_missing_pair_or_pivot(self):
        row,_=run(fixture(mixed=True),plan())
        self.assertEqual(re(row).reason,"CROSS_TF_SOURCE_MISMATCH")
        for data,p in ((fixture(missing=True),plan()),(fixture(),replace(plan(),upper_pivot=None))):
            row,_=run(data,p)
            self.assertIs(re(row).state,B6State387.MISSING)

    def test_invalid_explicit_configuration_and_short_atr(self):
        p=plan()
        for early in (replace(p.early,m15_index=True),replace(p.early,atr_stop=21),
                      replace(p.early,candidate_k_near=D("NaN"))):
            _,safe=run(fixture(),replace(p,early=early))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        row,_=run(fixture(),replace(p,early=replace(p.early,atr_stop=14)))
        self.assertEqual(re(row).reason,"ATR_PREFIX_BLOCKED")

    def test_old_rc_only_and_redaction(self):
        p=plan()
        row,safe=run(fixture(),replace(p,early=None))
        self.assertEqual(safe["phases"][2]["ingredient_state"],"NOT_REQUESTED")
        row,safe=run(fixture(),p)
        self.assertFalse(row.private_preview.action_eligible)
        for secret in ("candidate_k_near","109.5","pivot_price","distance","0.5"):
            self.assertNotIn(secret,json.dumps(safe))
        self.assertTrue(all(not p["phase_verified"] and not p["action_eligible"] for p in safe["phases"]))
