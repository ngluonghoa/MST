"""§480 S6 bounded failure to hold pivot, fictional only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.s6_breakout479 import S6FailurePlan480
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s6_breakout479 import fixture as breakout_fixture,evaluate
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def fixture(tf=Timeframe.H1,*,closes=(D(16),D(15)),window=2):
    inputs,p=breakout_fixture(tf)
    rows=inputs.snapshots_for(tf)
    extra=[]
    begin=p.event_known_at_utc
    for i,c in enumerate(closes):
        start=begin+timedelta(minutes=(i+1)*(1440 if tf is Timeframe.D1 else 75))
        b=make_bar(5800+i,timeframe=tf,start=start,open_price=c,high=max(D(17),c),low=min(D(12),c),close=c)
        if tf is Timeframe.H1:
            end=start+timedelta(hours=1)
            rev=replace(b.observation_revision,first_known_time_utc=end,retrieved_at_utc=end+timedelta(minutes=1))
            b=replace(b,bar_end_utc=end,retrieved_at_utc=rev.retrieved_at_utc,
                      verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
        extra.append(snap(b))
    return alter(inputs,tf,rows+tuple(extra)),S6FailurePlan480(p,len(rows)+len(extra)-1,window)


def rc(inputs,p,strategy=Strategy.SHORT):
    r,s=evaluate(inputs,p,strategy)
    return r.private_preview.assessments[1][1],s


class S6Failure480Tests(unittest.TestCase):
    def test_both_frames_strategies_and_boundary(self):
        for strategy in Strategy:
            for tf,n in ((Timeframe.D1,3),(Timeframe.H1,6)):
                inputs,p=fixture(tf,closes=(D(16),)*(n-1)+(D(15),),window=n)
                g,s=rc(inputs,p,strategy)
                self.assertIs(g.state,S1State439.MATCH)
                self.assertEqual(g.private_supplied_bars,n)
                self.assertEqual(s["status"],"UNVERIFIED")
                self.assertFalse(s["phases"][1]["action_eligible"])

    def test_no_default_expired_or_held_pivot(self):
        for kw,state in ((dict(window=None),S1State439.DISTANCE),
                         (dict(window=1),S1State439.NONMATCH),
                         (dict(closes=(D(16),D(16))),S1State439.NONMATCH),
                         (dict(closes=(D(15),D(14))),S1State439.NONMATCH)):
            inputs,p=fixture(**kw)
            self.assertIs(rc(inputs,p)[0].state,state)

    def test_exact_breakout_and_missing_failure(self):
        inputs,p=fixture()
        self.assertIs(rc(inputs,replace(p,breakout=replace(p.breakout,event_id="wrong")))[0].state,S1State439.BLOCKED)
        rows=inputs.snapshots_for(p.breakout.timeframe)
        self.assertIs(rc(alter(inputs,p.breakout.timeframe,rows[:-1]),p)[0].state,S1State439.MISSING)

    def test_late_event_or_path(self):
        inputs,p=fixture()
        rows=list(inputs.snapshots_for(p.breakout.timeframe))
        known=rows[p.breakout.target_index+1].market_bar_key.bar_start_utc+timedelta(seconds=1)
        self.assertIs(rc(inputs,replace(p,breakout=replace(p.breakout,event_known_at_utc=known)))[0].state,S1State439.BLOCKED)
        rows[-2]=snap(replace(rows[-2].selected,verified_at_utc=rows[-1].market_bar_key.bar_start_utc+timedelta(seconds=1)))
        self.assertIs(rc(alter(inputs,p.breakout.timeframe,tuple(rows)),p)[0].state,S1State439.BLOCKED)

    def test_explicit_candidate_window_validation(self):
        for tf,limit in ((Timeframe.D1,3),(Timeframe.H1,6)):
            inputs,p=fixture(tf)
            for bad in (replace(p,candidate_max_bars=limit+1),replace(p,candidate_max_bars=True),
                        replace(p,candidate_max_bars=0),replace(p,failure_index=p.breakout.target_index)):
                _,s=evaluate(inputs,bad)
                self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_shared_modes_redaction_and_legacy(self):
        inputs,p=fixture()
        candidate=profile((request("S6",p,variant="S6/BASE"),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(r.private_preview,"S6").private_preview.assessments[1][1].state,S1State439.MATCH)
            s=r.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for key in (p.breakout.event_id,"private_failure_start","private_supplied_bars"):
                self.assertNotIn(key,json.dumps(s))
        r,_=evaluate(inputs,p.breakout)
        self.assertEqual(len(r.private_preview.assessments),1)
