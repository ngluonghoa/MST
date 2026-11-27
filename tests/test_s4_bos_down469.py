"""§469 S4 causal post-RC micro-low BOS down, fictional only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.range_baseline_preview385 import RangeState385
from swing_trading.s4_rejection467 import S4BosDownPlan469
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s4_rejection467 import fixture as rejection_fixture,evaluate,VARIANTS
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile

VARIANT=VARIANTS[1]


def fixture(tf=Timeframe.M15,*,cross=False,close=D("104.5"),epsilon=D(0)):
    inputs,p=rejection_fixture(Timeframe.M15 if cross else tf)
    rc=inputs.snapshots_for(p.context.target_tf)[p.rejection_index].selected
    rows=() if cross else inputs.snapshots_for(tf)
    extra=[]
    for i,(c,low) in enumerate(zip((D(108),D(106),D(108),D(108),close),(107,105,107,107,104))):
        start=rc.verified_at_utc+timedelta(minutes=(i+1)*(75 if tf is Timeframe.H1 else 20))
        b=make_bar(4900+i,timeframe=tf,start=start,open_price=c,high=max(D(109),c),
                   low=min(D(low),c),close=c)
        if tf is Timeframe.H1:
            end=start+timedelta(hours=1)
            rev=replace(b.observation_revision,first_known_time_utc=end,retrieved_at_utc=end+timedelta(minutes=1))
            b=replace(b,bar_end_utc=end,retrieved_at_utc=rev.retrieved_at_utc,
                      verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
        extra.append(snap(b))
    start=len(rows)
    return alter(inputs,tf,rows+tuple(extra)),S4BosDownPlan469(p,tf,start+4,start,1,1,1,TiePolicy.STRICT_V1,0,35,epsilon)


def re(inputs,p,strategy=Strategy.SHORT):
    r,s=evaluate(inputs,p,strategy,VARIANT)
    return r.private_preview.assessments[2][1],s


class S4BosDown469Tests(unittest.TestCase):
    def test_both_frames_strategies_and_cross_frame(self):
        for strategy in Strategy:
            for tf,cross in ((Timeframe.M15,False),(Timeframe.H1,False),(Timeframe.H1,True)):
                inputs,p=fixture(tf,cross=cross)
                g,s=re(inputs,p,strategy)
                self.assertIs(g.state,RangeState385.MATCH)
                self.assertEqual(g.distance,D("0.5"))
                r,_=evaluate(inputs,p,strategy,VARIANT)
                self.assertIs(r.private_preview.assessments[2][0].selected_frame,tf)
                self.assertEqual(s["status"],"UNVERIFIED")
                self.assertTrue(all(not x["action_eligible"] for x in s["phases"]))

    def test_close_cross_threshold_and_major_range_loss(self):
        for close,epsilon,state in ((D(105),D(0),RangeState385.NONMATCH),
                                    (D("104.5"),None,RangeState385.DISTANCE),
                                    (D("104.5"),D(10),RangeState385.NONMATCH),
                                    (D(89),D(0),RangeState385.NONMATCH)):
            inputs,p=fixture(close=close,epsilon=epsilon)
            self.assertIs(re(inputs,p)[0].state,state)

    def test_missing_and_prior_rc_not_matched(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(p.timeframe)
        self.assertIs(re(alter(inputs,p.timeframe,rows[:-1]),p)[0].state,RangeState385.MISSING)
        p=replace(p,context=replace(p.context,candidate_k_reject=D(10)))
        self.assertIs(re(inputs,p)[0].state,RangeState385.BLOCKED)

    def test_late_right_witness_and_nonextremum(self):
        inputs,p=fixture()
        rows=list(inputs.snapshots_for(p.timeframe))
        w=p.history_start+2
        rows[w]=snap(replace(rows[w].selected,
                            verified_at_utc=rows[w+1].market_bar_key.bar_start_utc+timedelta(minutes=1)))
        self.assertIs(re(alter(inputs,p.timeframe,tuple(rows)),p)[0].state,RangeState385.BLOCKED)
        inputs,p=fixture()
        self.assertIs(re(inputs,replace(p,low_index=2))[0].state,RangeState385.NONMATCH)

    def test_invalid_scope_and_no_fallback(self):
        inputs,p=fixture()
        for bad,variant in ((p,VARIANTS[0]),(replace(p,history_start=p.target_index),VARIANT),
                            (replace(p,candidate_epsilon=D(-1)),VARIANT)):
            _,s=evaluate(inputs,bad,variant=variant)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_shared_modes_and_redaction_and_legacy(self):
        inputs,p=fixture()
        candidate=profile((request("S4",p,variant=VARIANT),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(r.private_preview,"S4").private_preview.assessments[2][1].state,RangeState385.MATCH)
            s=r.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for private in ("candidate_epsilon","distance","private_range","104.5",inputs.instrument_id):
                self.assertNotIn(private,json.dumps(s))
        r,_=evaluate(inputs,p.context,variant=VARIANT)
        self.assertEqual(len(r.private_preview.assessments),2)
