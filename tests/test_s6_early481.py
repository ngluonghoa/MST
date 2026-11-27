"""§481 S6 later causal M15 closed failed reclaim; fictional only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.s6_breakout479 import S6EarlyPlan481
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s6_failure480 import fixture as failure_fixture
from test_s6_breakout479 import evaluate
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def fixture(tf=Timeframe.H1,*,close=D(14),epsilon=D(0),prior=D(15)):
    inputs,p=failure_fixture(tf)
    rows=inputs.snapshots_for(Timeframe.M15)
    failure=inputs.snapshots_for(tf)[p.failure_index].selected
    extra=[]
    for i,c in enumerate((prior,close)):
        start=failure.verified_at_utc+timedelta(minutes=20*(i+1))
        extra.append(snap(make_bar(5900+i,timeframe=Timeframe.M15,start=start,
            open_price=c,high=max(D(16),c),low=min(D(13),c),close=c)))
    daily=inputs.snapshots_for(Timeframe.D1)
    return alter(inputs,Timeframe.M15,rows+tuple(extra)),S6EarlyPlan481(
        p,len(rows)+1,0,len(daily),epsilon,p.breakout.bar_start_utc,extra[-1].selected.verified_at_utc)


def re(inputs,p,strategy=Strategy.SHORT):
    r,s=evaluate(inputs,p,strategy)
    return r.private_preview.assessments[2][1],s


class S6Early481Tests(unittest.TestCase):
    def test_both_origin_frames_and_strategies(self):
        for strategy in Strategy:
            for tf in (Timeframe.H1,Timeframe.D1):
                inputs,p=fixture(tf)
                g,s=re(inputs,p,strategy)
                self.assertIs(g.state,S1State439.MATCH)
                self.assertEqual(g.private_pivot,D(15))
                self.assertEqual(s["status"],"UNVERIFIED")
                self.assertFalse(s["phases"][2]["action_eligible"])

    def test_closed_cross_and_explicit_threshold(self):
        for kw,state in ((dict(close=D(15)),S1State439.NONMATCH),
                         (dict(prior=D(14)),S1State439.NONMATCH),
                         (dict(epsilon=None),S1State439.DISTANCE),
                         (dict(epsilon=D(10)),S1State439.NONMATCH)):
            inputs,p=fixture(**kw)
            self.assertIs(re(inputs,p)[0].state,state)

    def test_missing_and_prior_failure_required(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(Timeframe.M15)
        self.assertIs(re(alter(inputs,Timeframe.M15,rows[:-1]),p)[0].state,S1State439.MISSING)
        q=replace(p,failure=replace(p.failure,candidate_max_bars=1))
        self.assertIs(re(inputs,q)[0].state,S1State439.BLOCKED)

    def test_expiry_and_late_witness(self):
        inputs,p=fixture()
        for q in (replace(p,expires_at_utc=p.expires_at_utc-timedelta(seconds=1)),
                  replace(p,window_known_at_utc=p.window_known_at_utc+timedelta(seconds=1))):
            self.assertIs(re(inputs,q)[0].state,S1State439.BLOCKED)
        rows=inputs.snapshots_for(Timeframe.M15)
        late=snap(replace(rows[-2].selected,verified_at_utc=rows[-1].market_bar_key.bar_start_utc+timedelta(seconds=1)))
        self.assertIs(re(alter(inputs,Timeframe.M15,rows[:-2]+(late,rows[-1])),p)[0].state,S1State439.BLOCKED)

    def test_stale_atr_and_bad_plan(self):
        inputs,p=fixture(Timeframe.D1)
        self.assertIs(re(inputs,replace(p,atr_stop=p.atr_stop-1))[0].state,S1State439.BLOCKED)
        for bad in (replace(p,target_index=True),replace(p,candidate_epsilon=D(-1)),
                    replace(p,expires_at_utc=p.window_known_at_utc)):
            _,s=evaluate(inputs,bad)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_shared_modes_and_redaction_and_legacy(self):
        inputs,p=fixture()
        candidate=profile((request("S6",p,variant="S6/BASE"),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(r.private_preview,"S6").private_preview.assessments[2][1].state,S1State439.MATCH)
            s=r.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for key in (p.failure.breakout.event_id,"private_early_start","private_early_known"):
                self.assertNotIn(key,json.dumps(s))
        r,_=evaluate(inputs,p.failure)
        self.assertEqual(len(r.private_preview.assessments),2)
