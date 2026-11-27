"""§428 fictional causal raw D1 liquidity regression."""
from dataclasses import replace
from decimal import Decimal as D
import json
import unittest

from swing_trading.b8_liquidity428 import B8LiquidityPlan428
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from test_b8_rf418 import fixture
from test_b8_base415 import run
from test_causal_indicators import snap


def bind(inputs,p,strategy=Strategy.SHORT,*,turnover=D(1000),volume=100,**kw):
    daily=inputs.snapshots_for(Timeframe.D1)
    target=inputs.snapshots_for(p.rf.timeframe)[p.rf.breakout_index].selected
    stop=sum(s.market_bar_key.bar_start_utc<target.market_bar_key.bar_start_utc for s in daily)
    daily=tuple(snap(replace(s.selected,matched_value=turnover,volume=volume))
                if i<stop else s for i,s in enumerate(daily))
    inputs=replace(inputs,buckets=tuple((f,daily if f is Timeframe.D1 else rows)
                                       for f,rows in inputs.buckets))
    plan=B8LiquidityPlan428(strategy,stop-3,stop,10,"fixture-shares-value-v1",D(1000),D(".1"))
    return inputs,replace(p,rf=replace(p.rf,liquidity=replace(plan,**kw)))


class B8Liquidity428Tests(unittest.TestCase):
    def test_both_frames_strategies_variants(self):
        for tf in (Timeframe.H1,Timeframe.D1):
            for strategy in Strategy:
                for variant in ("B8/BASE","B8/INTRADAY_RVOL_TOD_PENDING"):
                    inputs,p=bind(*fixture(tf=tf),strategy)
                    row,safe=run(inputs,p,strategy=strategy,variant=variant)
                    proof=row.private_preview.assessments[-1][1].liquidity
                    self.assertEqual((proof.mean_turnover,proof.mean_volume,proof.volume_fraction),
                                     (D(1000),D(100),D(".1")))
                    self.assertTrue(proof.candidate_match)
                    self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_size_or_turnover_nonmatch(self):
        for kw in ({"order_shares":11},{"turnover":D(999)}):
            inputs,p=bind(*fixture(),**kw)
            _,safe=run(inputs,p)
            self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_missing_and_zero(self):
        inputs,p=bind(*fixture(),turnover=None)
        _,safe=run(inputs,p)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"MISSING_INPUT")
        inputs,p=bind(*fixture(),volume=0,turnover=D(0))
        _,safe=run(inputs,p)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_stale_future_or_wrong_strategy(self):
        inputs,p=bind(*fixture())
        plan=p.rf.liquidity
        for changed in (replace(plan,start=plan.start-1,stop=plan.stop-1),
                        replace(plan,strategy=Strategy.SWING)):
            _,safe=run(inputs,replace(p,rf=replace(p.rf,liquidity=changed)))
            self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_uncalibrated_and_invalid(self):
        inputs,p=bind(*fixture(),candidate_min_mean_turnover=None)
        _,safe=run(inputs,p)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"DISTANCE_ONLY")
        for kw in ({"order_shares":True},{"units_policy":""},{"candidate_max_volume_fraction":D(2)}):
            inputs,p=bind(*fixture(),**kw)
            _,safe=run(inputs,p)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_legacy_and_redaction(self):
        inputs,p=fixture()
        row,_=run(inputs,p)
        self.assertIsNone(row.private_preview.assessments[-1][1].liquidity)
        inputs,p=bind(inputs,p)
        row,safe=run(inputs,p)
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("mean_turnover","volume_fraction","fixture-shares-value-v1",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
