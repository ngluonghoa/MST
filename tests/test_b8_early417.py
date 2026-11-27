"""§417 B8 same-resistance closed cross after approach, synthetic only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b8_base_preview415 import B8EarlyPlan417, B8NearPlan416, B8State415
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from test_b8_near416 import setup
from test_b8_base415 import run
from test_causal_indicators import make_bar, snap


def fixture(tf=Timeframe.D1, *, close=D(17), near_close=D(14), late=False, missing=False):
    inputs,p=setup(tf,close=near_close)
    rows=inputs.snapshots_for(Timeframe.M15)
    start=rows[-1].market_bar_key.bar_start_utc+timedelta(minutes=30)
    bar=make_bar(1200,timeframe=Timeframe.M15,start=start,open_price=close,
                 close=close,high=max(D(18),close),low=D(8))
    if late:
        rows=rows[:-1]+(snap(replace(rows[-1].selected,verified_at_utc=bar.bar_end_utc)),)
    if not missing:
        rows+=(snap(bar),)
    inputs=replace(inputs,buckets=tuple((frame,rows if frame is Timeframe.M15 else items)
                                       for frame,items in inputs.buckets))
    return inputs,replace(p,early=B8EarlyPlan417(D("0.1")))


class B8Early417Tests(unittest.TestCase):
    def test_both_variants_strategies_and_frames(self):
        for strategy in Strategy:
            for variant in ("B8/BASE","B8/INTRADAY_RVOL_TOD_PENDING"):
                for tf in (Timeframe.D1,Timeframe.H1):
                    inputs,p=fixture(tf)
                    row,safe=run(inputs,p,strategy=strategy,variant=variant)
                    self.assertIs(row.private_preview.assessments[-1][1].state,B8State415.MATCH)
                    self.assertEqual(safe["phases"][2]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_wick_touch_or_buffer_nonmatch(self):
        for close in (D(14),D(15),D("15.01")):
            inputs,p=fixture(close=close)
            row,_=run(inputs,p)
            self.assertIs(row.private_preview.assessments[-1][1].state,B8State415.NONMATCH)

    def test_zero_explicit_epsilon_and_strict_close(self):
        inputs,p=fixture(close=D("15.01"))
        row,_=run(inputs,replace(p,early=B8EarlyPlan417(D(0))))
        self.assertIs(row.private_preview.assessments[-1][1].state,B8State415.MATCH)

    def test_late_missing_or_unmatched_approach(self):
        for args,state in (({"late":True},"BLOCKED"),({"missing":True},"MISSING_INPUT"),
                           ({"near_close":D(16)},"BLOCKED")):
            inputs,p=fixture(**args)
            _,safe=run(inputs,p)
            self.assertEqual(safe["phases"][2]["ingredient_state"],state)
        inputs,p=fixture()
        for near,state in ((None,"MISSING_INPUT"),(B8NearPlan416(None),"BLOCKED")):
            _,safe=run(inputs,replace(p,near=near))
            self.assertEqual(safe["phases"][2]["ingredient_state"],state)

    def test_invalid_and_legacy(self):
        inputs,p=fixture()
        for e in (None,True,D("-1"),D("NaN")):
            _,safe=run(inputs,replace(p,early=B8EarlyPlan417(e)))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        _,safe=run(inputs,replace(p,early=None))
        self.assertEqual(safe["phases"][2]["ingredient_state"],"NOT_REQUESTED")

    def test_pending_volume_and_no_authority(self):
        inputs,p=fixture()
        row,safe=run(inputs,p,variant="B8/INTRADAY_RVOL_TOD_PENDING")
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in (inputs.instrument_id,"candidate_epsilon","private_resistance"):
            self.assertNotIn(secret,json.dumps(safe))
