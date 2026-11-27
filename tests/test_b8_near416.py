"""§416 B8 same resistance M15 approach, synthetic only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b8_base_preview415 import B8NearPlan416, B8State415
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from test_b8_base415 import fixture, run
from test_causal_indicators import make_bar, snap


def setup(tf=Timeframe.D1, *, close=D(14), prior=D(10), late=False, missing=False):
    inputs,p=fixture(tf)
    old=inputs.snapshots_for(Timeframe.M15)[0].selected
    start=old.market_bar_key.bar_start_utc
    old=replace(old,close=prior,high=max(old.high,prior))
    nxt=make_bar(1101,timeframe=Timeframe.M15,start=start+timedelta(minutes=30),
                 open_price=close,close=close,high=max(D(16),close),low=D(8))
    if late:
        old=replace(old,verified_at_utc=nxt.bar_end_utc)
    rows=(snap(old),) if missing else (snap(old),snap(nxt))
    inputs=replace(inputs,buckets=tuple((frame,rows if frame is Timeframe.M15 else items)
                                       for frame,items in inputs.buckets))
    return inputs,replace(p,near=B8NearPlan416(D(1)))


class B8Near416Tests(unittest.TestCase):
    def test_both_strategies_variants_and_frames(self):
        for strategy in Strategy:
            for variant in ("B8/BASE","B8/INTRADAY_RVOL_TOD_PENDING"):
                for tf in (Timeframe.D1,Timeframe.H1):
                    inputs,p=setup(tf)
                    row,safe=run(inputs,p,strategy=strategy,variant=variant)
                    self.assertIs(row.private_preview.assessments[1][1].state,B8State415.MATCH)
                    self.assertEqual(safe["phases"][1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_above_or_falling_or_far_nonmatch(self):
        for args in ({"close":D(16)},{"prior":D(15)},{"close":D(11)}):
            inputs,p=setup(**args)
            p=replace(p,near=B8NearPlan416(D("0.5")))
            row,_=run(inputs,p)
            self.assertIs(row.private_preview.assessments[1][1].state,B8State415.NONMATCH)

    def test_exact_touch_and_no_default(self):
        inputs,p=setup(close=D(15))
        row,_=run(inputs,replace(p,near=B8NearPlan416(D(0))))
        self.assertIs(row.private_preview.assessments[1][1].state,B8State415.MATCH)
        row,safe=run(inputs,replace(p,near=B8NearPlan416(None)))
        self.assertIs(row.private_preview.assessments[1][1].state,B8State415.DISTANCE)
        self.assertEqual(safe["phases"][1]["ingredient_state"],"DISTANCE_ONLY")

    def test_missing_late_and_unmatched_base(self):
        for args,state in (({"missing":True},"MISSING_INPUT"),({"late":True},"BLOCKED")):
            inputs,p=setup(**args)
            _,safe=run(inputs,p)
            self.assertEqual(safe["phases"][1]["ingredient_state"],state)
        inputs,p=setup()
        for k in (None,D(0)):
            _,safe=run(inputs,replace(p,candidate_max_width_atr=k))
            self.assertEqual(safe["phases"][1]["ingredient_state"],"BLOCKED")

    def test_invalid_and_legacy(self):
        inputs,p=setup()
        for near in (B8NearPlan416(D("-1")),B8NearPlan416(D("NaN")),B8NearPlan416(True)):
            _,safe=run(inputs,replace(p,near=near))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        _,safe=run(inputs,replace(p,near=None))
        self.assertEqual(safe["phases"][1]["ingredient_state"],"NOT_REQUESTED")

    def test_redacted_no_authority(self):
        inputs,p=setup()
        row,safe=run(inputs,p)
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for forbidden in (inputs.instrument_id,"distance_atr","candidate_k_near","private_resistance"):
            self.assertNotIn(forbidden,json.dumps(safe))
