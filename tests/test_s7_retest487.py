"""§487 S7 exact observed-session retest candidate; synthetic only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.s7_breakdown486 import S7RetestPlan487
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s7_breakdown486 import fixture as breakdown_fixture,evaluate
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def fixture(tf=Timeframe.H1,*,high=D(5),prior=D(4),window=2,k=D(0)):
    inputs,p=breakdown_fixture(tf)
    rows=inputs.snapshots_for(Timeframe.M15)
    start=len(rows)
    extra=[]
    for i,(h,c) in enumerate(((max(D("4.5"),prior),prior),(high,D(4)))):
        extra.append(snap(make_bar(5800+i,timeframe=Timeframe.M15,start=p.event_known_at_utc+timedelta(minutes=20*(i+1)),
            high=h,low=D(3),close=c,open_price=c)))
    inputs=alter(inputs,Timeframe.M15,rows+tuple(extra))
    return inputs,S7RetestPlan487(p,start,start+1,0,len(inputs.snapshots_for(Timeframe.D1)),window,k)


def rc(inputs,p,strategy=Strategy.SHORT,variant="S7/F_MICRO_BREAK"):
    r,s=evaluate(inputs,p,strategy,variant)
    return r.private_preview.assessments[1][1],s


class S7Retest487Tests(unittest.TestCase):
    def test_both_frames_strategies_and_shared_rc(self):
        for strategy in Strategy:
            for tf in (Timeframe.H1,Timeframe.D1):
                for variant in ("S7/F_MICRO_BREAK","S7/F_CONTINUATION"):
                    inputs,p=fixture(tf)
                    g,s=rc(inputs,p,strategy,variant)
                    self.assertIs(g.state,S1State439.MATCH)
                    self.assertEqual((g.private_sessions,g.private_range_distance_atr),(2,D(0)))
                    self.assertEqual(s["status"],"UNVERIFIED")
                    self.assertFalse(s["phases"][1]["action_eligible"])

    def test_window_near_and_approach(self):
        for kw,state in ((dict(window=1),S1State439.NONMATCH),(dict(k=None),S1State439.DISTANCE),
                         (dict(window=None),S1State439.DISTANCE),(dict(high=D("4.5")),S1State439.NONMATCH),
                         (dict(prior=D(5)),S1State439.NONMATCH)):
            inputs,p=fixture(**kw)
            self.assertIs(rc(inputs,p)[0].state,state)

    def test_missing_and_origin_required(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(Timeframe.M15)
        self.assertIs(rc(alter(inputs,Timeframe.M15,rows[:-1]),p)[0].state,S1State439.MISSING)
        q=replace(p,breakdown=replace(p.breakdown,event_id="wrong"))
        self.assertIs(rc(inputs,q)[0].state,S1State439.BLOCKED)

    def test_late_path_and_stale_atr(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(Timeframe.M15)
        late=snap(replace(rows[-2].selected,verified_at_utc=rows[-1].market_bar_key.bar_start_utc+timedelta(seconds=1)))
        self.assertIs(rc(alter(inputs,Timeframe.M15,rows[:-2]+(late,rows[-1])),p)[0].state,S1State439.BLOCKED)
        inputs,p=fixture(Timeframe.D1)
        self.assertIs(rc(inputs,replace(p,atr_stop=p.atr_stop-1))[0].state,S1State439.BLOCKED)

    def test_bad_explicit_plan(self):
        inputs,p=fixture()
        for bad in (replace(p,candidate_max_sessions=16),replace(p,candidate_max_sessions=True),
                    replace(p,candidate_near_atr=D(-1)),replace(p,target_index=p.history_start)):
            _,s=evaluate(inputs,bad)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_shared_modes_redaction_and_legacy(self):
        inputs,p=fixture()
        candidate=profile((request("S7",p,variant="S7/F_MICRO_BREAK"),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(r.private_preview,"S7").private_preview.assessments[1][1].state,S1State439.MATCH)
            s=r.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for key in (p.breakdown.event_id,"private_sessions","private_range_distance_atr","private_pivot"):
                self.assertNotIn(key,json.dumps(s))
        r,_=evaluate(inputs,p.breakdown)
        self.assertEqual(len(r.private_preview.assessments),1)
