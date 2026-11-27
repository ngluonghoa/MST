"""§413 explicit D1 falling geometry at R0 and later RF cutoff."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b7_support_preview409 import B7TrendWindow413, B7TrendPlan413
from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from test_b7_support_preview409 import run
from test_b7_rf412 import fixture
from test_causal_indicators import make_bar, snap


def setup(*, choch=False, tf=Timeframe.M15, extra=False, late=False, rising=False):
    inputs,p,variant=fixture(choch=choch,tf=tf)
    start=inputs.snapshots_for(Timeframe.M15)[p.target_index].market_bar_key.bar_start_utc
    rows=[]
    for i in range(60+int(extra)):
        close=D(20)-D(i)/5
        high,low=close+1,close-1
        if i in (10,30):
            high=D(23 if i==10 and not rising else 25 if i==30 and rising else 21)
        if i in (20,40):
            low=D(12 if i==20 else 7)
        row=make_bar(i+600,start=start-timedelta(days=60+int(extra)-i),
                     open_price=close,close=close,high=high,low=low)
        if late and i==59:
            row=replace(row,verified_at_utc=start+timedelta(minutes=1))
        rows.append(snap(row))
    inputs=replace(inputs,buckets=tuple((frame,tuple(rows) if frame is Timeframe.D1 else items)
                                       for frame,items in inputs.buckets))
    w=B7TrendWindow413(0,60,(10,30),(20,40))
    trend=B7TrendPlan413(w,w,10,1,1,TiePolicy.STRICT_V1)
    p=replace(p,pivot_start=0,pivot_stop=45,candidate_index=40,atr_start=45,atr_stop=60,trend=trend)
    return inputs,p,variant


def evaluate(*,strategy=Strategy.SHORT,**kwargs):
    inputs,p,variant=setup(**kwargs)
    return run(inputs,p,strategy=strategy,variant=variant)


class B7Trend413Tests(unittest.TestCase):
    def test_both_variants_strategies_and_rf_frames(self):
        for strategy in Strategy:
            for choch in (False,True):
                for tf in (Timeframe.M15,Timeframe.H1):
                    _,safe=evaluate(strategy=strategy,choch=choch,tf=tf)
                    self.assertEqual(safe["phases"][0]["ingredient_state"],"GEOMETRY_MATCH_ONLY")
                    self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_nonfalling_and_late_r0_block_rf(self):
        for kwargs,state in (({"rising":True},"GEOMETRY_NONMATCH_ONLY"),({"late":True},"BLOCKED")):
            _,safe=evaluate(**kwargs)
            self.assertEqual(safe["phases"][0]["ingredient_state"],state)
            self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_skipped_newer_bar_blocks_stale_window(self):
        _,safe=evaluate(extra=True)
        self.assertEqual(safe["phases"][0]["ingredient_state"],"BLOCKED")
        self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_rf_distinct_explicit_window_required(self):
        inputs,p,variant=setup()
        _,safe=run(inputs,replace(p,trend=replace(p.trend,rf=None)),variant=variant)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"MISSING_INPUT")
        _,safe=run(inputs,replace(p,trend=replace(p.trend,rf=replace(p.trend.rf,high_indices=(11,30)))),variant=variant)
        self.assertEqual(safe["phases"][0]["ingredient_state"],"GEOMETRY_MATCH_ONLY")
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_invalid_and_legacy(self):
        inputs,p,variant=setup()
        for trend in (replace(p.trend,lookback=True),replace(p.trend,r0=replace(p.trend.r0,stop=59))):
            _,safe=run(inputs,replace(p,trend=trend),variant=variant)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        _,safe=run(inputs,replace(p,trend=None),variant=variant)
        self.assertEqual(safe["phases"][0]["ingredient_state"],"NOT_REQUESTED")
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_redaction_and_no_authority(self):
        row,safe=evaluate()
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("high_indices","lookback","LH_LL_GEOMETRY",setup()[0].instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
