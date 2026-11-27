"""§476 S5 first LH and later causal M15 low-cross; fictional only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.s5_transition473 import S5ConfirmPlan476
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s5_early475 import fixture as early_fixture
from test_s5_transition473 import evaluate
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def fixture(tf=Timeframe.H1,*,close=D(6),epsilon=D(0)):
    inputs,p=early_fixture(tf)
    rows=inputs.snapshots_for(Timeframe.M15)
    begin=rows[-1].selected.verified_at_utc
    extra=[]
    for i,(h,l,c) in enumerate(((10,D("6.5"),8),(10,7,8),(10,7,8),(10,5,close))):
        extra.append(snap(make_bar(5600+i,timeframe=Timeframe.M15,start=begin+timedelta(minutes=20*(i+1)),
            high=D(h),low=min(D(l),D(c)),open_price=D(c),close=D(c))))
    return alter(inputs,Timeframe.M15,rows+tuple(extra)),S5ConfirmPlan476(
        p,len(rows)+3,1,1,1,TiePolicy.STRICT_V1,0,p.atr_stop,epsilon)


def rf(inputs,p,strategy=Strategy.SHORT):
    r,s=evaluate(inputs,p,strategy)
    return r.private_preview.assessments[3][1],s


class S5Confirm476Tests(unittest.TestCase):
    def test_both_origin_frames_and_strategies(self):
        for strategy in Strategy:
            for tf in (Timeframe.D1,Timeframe.H1):
                inputs,p=fixture(tf)
                g,s=rf(inputs,p,strategy)
                self.assertIs(g.state,S1State439.MATCH)
                self.assertEqual((g.private_rally_high,g.private_micro_low,g.private_distance),(D(12),D("6.5"),D("0.5")))
                self.assertEqual(s["status"],"UNVERIFIED")
                self.assertFalse(s["phases"][3]["action_eligible"])

    def test_closed_cross_and_threshold(self):
        for kw,state in ((dict(close=D("6.5")),S1State439.NONMATCH),
                         (dict(close=D(7)),S1State439.NONMATCH),
                         (dict(epsilon=None),S1State439.DISTANCE),
                         (dict(epsilon=D(10)),S1State439.NONMATCH)):
            inputs,p=fixture(**kw)
            self.assertIs(rf(inputs,p)[0].state,state)

    def test_missing_and_unmatched_early(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(Timeframe.M15)
        self.assertIs(rf(alter(inputs,Timeframe.M15,rows[:-1]),p)[0].state,S1State439.MISSING)
        q=replace(p,early=replace(p.early,candidate_k_rejection=D(0)))
        self.assertIs(rf(inputs,q)[0].state,S1State439.BLOCKED)

    def test_late_witness_and_invalidated_lh(self):
        inputs,p=fixture()
        rows=list(inputs.snapshots_for(Timeframe.M15))
        i=p.early.target_index+2
        rows[i]=snap(replace(rows[i].selected,verified_at_utc=rows[i+1].market_bar_key.bar_start_utc+timedelta(seconds=1)))
        self.assertIs(rf(alter(inputs,Timeframe.M15,tuple(rows)),p)[0].state,S1State439.BLOCKED)
        inputs,p=fixture()
        rows=list(inputs.snapshots_for(Timeframe.M15))
        rows[-2]=snap(replace(rows[-2].selected,high=D(13)))
        self.assertIs(rf(alter(inputs,Timeframe.M15,tuple(rows)),p)[0].state,S1State439.NONMATCH)

    def test_bad_plan_and_stale_atr(self):
        inputs,p=fixture(Timeframe.D1)
        self.assertIs(rf(inputs,replace(p,atr_stop=p.atr_stop-1))[0].state,S1State439.BLOCKED)
        for bad in (replace(p,target_index=p.early.target_index),replace(p,low_index=True),
                    replace(p,candidate_epsilon=D(-1))):
            _,s=evaluate(inputs,bad)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_shared_modes_and_redaction_and_legacy(self):
        inputs,p=fixture()
        candidate=profile((request("S5",p,variant="S5/BASE"),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(r.private_preview,"S5").private_preview.assessments[3][1].state,S1State439.MATCH)
            s=r.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for key in ("private_micro_low","private_rally_high","private_distance",p.early.rally.context.event_id):
                self.assertNotIn(key,json.dumps(s))
        r,_=evaluate(inputs,p.early)
        self.assertEqual(len(r.private_preview.assessments),3)
