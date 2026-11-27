"""§418 B8 later higher-frame closed same-resistance cross."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b8_base_preview415 import B8ConfirmPlan418, B8State415
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from test_b8_early417 import fixture as early_fixture
from test_b8_base415 import run
from test_causal_indicators import make_bar, snap


def fixture(base_tf=Timeframe.D1, *, tf=Timeframe.H1, close=D(17),
            prior=D(14), late=False, missing=False, early_bad=False):
    inputs,p=early_fixture(base_tf,close=D(14) if early_bad else D(17))
    m15=inputs.snapshots_for(Timeframe.M15)
    start=m15[-1].selected.bar_end_utc+timedelta(days=2)
    existing=inputs.snapshots_for(tf)
    rows=[]
    for i,price in enumerate((prior,close)):
        begin=start+timedelta(days=i)
        bar=make_bar(1300+i,timeframe=tf,start=begin,open_price=price,
                     high=max(D(18),price),low=D(8),close=price)
        if tf is Timeframe.H1:
            end=begin+timedelta(hours=1)
            rev=replace(bar.observation_revision,first_known_time_utc=end,
                        retrieved_at_utc=end+timedelta(minutes=1))
            bar=replace(bar,bar_end_utc=end,retrieved_at_utc=rev.retrieved_at_utc,
                        verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
        rows.append(snap(bar))
    if late:
        m15=m15[:-1]+(snap(replace(m15[-1].selected,verified_at_utc=rows[-1].selected.bar_end_utc)),)
    series=existing+tuple(rows[:1] if missing else rows)
    inputs=replace(inputs,buckets=tuple((frame,series if frame is tf
                   else m15 if frame is Timeframe.M15 else items) for frame,items in inputs.buckets))
    return inputs,replace(p,rf=B8ConfirmPlan418(tf,len(existing)+1,D("0.1")))


class B8RF418Tests(unittest.TestCase):
    def test_both_strategies_variants_and_frame_choices(self):
        for strategy in Strategy:
            for variant in ("B8/BASE","B8/INTRADAY_RVOL_TOD_PENDING"):
                for base_tf in (Timeframe.D1,Timeframe.H1):
                    for tf in (Timeframe.D1,Timeframe.H1):
                        inputs,p=fixture(base_tf,tf=tf)
                        row,safe=run(inputs,p,strategy=strategy,variant=variant)
                        route,proof=row.private_preview.assessments[-1]
                        self.assertIs(route.selected_frame,tf)
                        self.assertIs(proof.state,B8State415.MATCH)
                        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_wick_touch_and_already_above_nonmatch(self):
        for args in ({"close":D(15)},{"close":D("15.01")},{"prior":D(16)}):
            inputs,p=fixture(**args)
            row,_=run(inputs,p)
            self.assertIs(row.private_preview.assessments[-1][1].state,B8State415.NONMATCH)

    def test_late_or_nonmatching_early_blocks(self):
        for args in ({"late":True},{"early_bad":True}):
            inputs,p=fixture(**args)
            _,safe=run(inputs,p)
            self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_missing_no_fallback(self):
        for tf in (Timeframe.H1,Timeframe.D1):
            inputs,p=fixture(tf=tf,missing=True)
            _,safe=run(inputs,p)
            self.assertEqual(safe["phases"][3]["ingredient_state"],"MISSING_INPUT")
        inputs,p=fixture()
        _,safe=run(inputs,replace(p,early=None))
        self.assertEqual(safe["phases"][3]["ingredient_state"],"MISSING_INPUT")

    def test_explicit_config_and_legacy(self):
        inputs,p=fixture()
        for rf in (replace(p.rf,timeframe=Timeframe.M15),replace(p.rf,breakout_index=True),
                   replace(p.rf,candidate_epsilon=None),replace(p.rf,candidate_epsilon=D("-1"))):
            _,safe=run(inputs,replace(p,rf=rf))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        _,safe=run(inputs,replace(p,rf=None))
        self.assertEqual(safe["phases"][3]["ingredient_state"],"NOT_REQUESTED")

    def test_no_authority_or_raw_leakage(self):
        inputs,p=fixture()
        row,safe=run(inputs,p)
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in (inputs.instrument_id,"private_resistance","candidate_epsilon","breakout_index"):
            self.assertNotIn(secret,json.dumps(safe))
