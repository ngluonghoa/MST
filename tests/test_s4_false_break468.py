"""§468 closed false-break reentry candidates, fictional only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.range_baseline_preview385 import RangeState385
from swing_trading.s4_rejection467 import S4FalseBreakPlan468
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s4_rejection467 import fixture as rejection_fixture,evaluate,VARIANTS
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile

VARIANT=VARIANTS[0]


def fixture(tf=Timeframe.M15,*,cross=False,breakout=D(112),close=D("107.5"),epsilon=D("0.5")):
    inputs,p=rejection_fixture(Timeframe.M15 if cross else tf)
    rc=inputs.snapshots_for(p.context.target_tf)[p.rejection_index].selected
    rows=() if cross else inputs.snapshots_for(tf)
    prices=(D(108),breakout,close) if cross else (breakout,close)
    begin=rc.verified_at_utc
    extra=[]
    for i,c in enumerate(prices):
        b=make_bar(4800+i,timeframe=tf,start=begin+timedelta(minutes=(i+1)*(75 if tf is Timeframe.H1 else 20)),
                   open_price=c,high=max(D(113),c),low=min(D(106),c),close=c)
        if tf is Timeframe.H1:
            end=b.market_bar_key.bar_start_utc+timedelta(hours=1)
            rev=replace(b.observation_revision,first_known_time_utc=end,retrieved_at_utc=end+timedelta(minutes=1))
            b=replace(b,bar_end_utc=end,retrieved_at_utc=rev.retrieved_at_utc,
                      verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
        extra.append(snap(b))
    start=len(rows)+(1 if cross else 0)
    return alter(inputs,tf,rows+tuple(extra)),S4FalseBreakPlan468(p,tf,start,start+1,epsilon)


def re(inputs,p,strategy=Strategy.SHORT):
    r,s=evaluate(inputs,p,strategy,VARIANT)
    return r.private_preview.assessments[2][1],s


class S4FalseBreak468Tests(unittest.TestCase):
    def test_both_frames_strategies_and_cross_frame(self):
        for strategy in Strategy:
            for tf,cross in ((Timeframe.M15,False),(Timeframe.H1,False),(Timeframe.H1,True)):
                inputs,p=fixture(tf,cross=cross)
                g,s=re(inputs,p,strategy)
                self.assertIs(g.state,RangeState385.MATCH)
                self.assertEqual(g.distance,D("2.5"))
                self.assertEqual(s["status"],"UNVERIFIED")
                r,_=evaluate(inputs,p,strategy,VARIANT)
                self.assertIs(r.private_preview.assessments[2][0].selected_frame,tf)
                self.assertTrue(all(not x["action_eligible"] for x in s["phases"]))

    def test_strict_close_boundary_and_missing_threshold(self):
        for breakout,close,epsilon,state in (
            (D(110),D(107),D(0),RangeState385.NONMATCH),
            (D(112),D(108),D("0.5"),RangeState385.NONMATCH),
            (D(112),D(110),D(0),RangeState385.NONMATCH),
            (D(112),D(89),D(0),RangeState385.NONMATCH),
            (D(112),D("107.5"),None,RangeState385.DISTANCE)):
            inputs,p=fixture(breakout=breakout,close=close,epsilon=epsilon)
            self.assertIs(re(inputs,p)[0].state,state)

    def test_missing_bar_and_rejection_prerequisite(self):
        inputs,p=fixture()
        self.assertIs(re(inputs,replace(p,reentry_index=p.reentry_index+1))[0].state,RangeState385.MISSING)
        p=replace(p,context=replace(p.context,candidate_k_reject=D(10)))
        self.assertIs(re(inputs,p)[0].state,RangeState385.BLOCKED)

    def test_late_breakout_and_prebreak_known_clock(self):
        inputs,p=fixture()
        rows=list(inputs.snapshots_for(p.timeframe))
        rows[p.breakout_index]=snap(replace(rows[p.breakout_index].selected,
            verified_at_utc=rows[p.reentry_index].market_bar_key.bar_start_utc+timedelta(minutes=1)))
        self.assertIs(re(alter(inputs,p.timeframe,tuple(rows)),p)[0].state,RangeState385.BLOCKED)
        inputs,p=fixture(Timeframe.H1,cross=True)
        rows=list(inputs.snapshots_for(p.timeframe))
        rows[0]=snap(replace(rows[0].selected,
            verified_at_utc=rows[1].market_bar_key.bar_start_utc+timedelta(minutes=1)))
        self.assertIs(re(alter(inputs,p.timeframe,tuple(rows)),p)[0].state,RangeState385.BLOCKED)

    def test_exact_variant_and_bad_plan(self):
        inputs,p=fixture()
        for bad,variant in ((p,VARIANTS[1]),(replace(p,breakout_index=p.reentry_index),VARIANT),
                            (replace(p,candidate_epsilon=D(-1)),VARIANT)):
            _,s=evaluate(inputs,bad,variant=variant)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_shared_modes_and_legacy_redaction(self):
        inputs,p=fixture()
        candidate=profile((request("S4",p,variant=VARIANT),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(r.private_preview,"S4").private_preview.assessments[2][1].state,RangeState385.MATCH)
            s=r.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for private in ("candidate_epsilon","distance","private_range","107.5",inputs.instrument_id):
                self.assertNotIn(private,json.dumps(s))
        r,_=evaluate(inputs,p.context,variant=VARIANT)
        self.assertEqual(len(r.private_preview.assessments),2)
