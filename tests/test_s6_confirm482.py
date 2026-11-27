"""§482 S6 later corresponding H1/D1 micro-support failure, fictional only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.s6_breakout479 import S6ConfirmPlan482
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s6_early481 import fixture as early_fixture
from test_s6_breakout479 import evaluate
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def fixture(tf=Timeframe.H1,*,close=D("10.5"),epsilon=D(0)):
    inputs,p=early_fixture(tf)
    early=inputs.snapshots_for(Timeframe.M15)[p.target_index].selected
    rows=inputs.snapshots_for(tf)
    extra=[]
    for i,(c,low) in enumerate(((D(14),12),(D(13),11),(D(14),12),(D(14),12),(close,10))):
        start=early.verified_at_utc+timedelta(minutes=(i+1)*(1440 if tf is Timeframe.D1 else 75))
        b=make_bar(6000+i,timeframe=tf,start=start,open_price=c,high=max(D(15),c),low=min(D(low),c),close=c)
        if tf is Timeframe.H1:
            end=start+timedelta(hours=1)
            rev=replace(b.observation_revision,first_known_time_utc=end,retrieved_at_utc=end+timedelta(minutes=1))
            b=replace(b,bar_end_utc=end,retrieved_at_utc=rev.retrieved_at_utc,
                      verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
        extra.append(snap(b))
    start=len(rows)
    p=replace(p,expires_at_utc=extra[-1].selected.verified_at_utc)
    return alter(inputs,tf,rows+tuple(extra)),S6ConfirmPlan482(
        p,tf,start+4,start,1,1,1,TiePolicy.STRICT_V1,0,start+4 if tf is Timeframe.D1 else p.atr_stop,epsilon)


def rf(inputs,p,strategy=Strategy.SHORT):
    r,s=evaluate(inputs,p,strategy)
    return r.private_preview.assessments[3][1],s


class S6Confirm482Tests(unittest.TestCase):
    def test_both_origin_frames_and_strategies(self):
        for strategy in Strategy:
            for tf in (Timeframe.H1,Timeframe.D1):
                inputs,p=fixture(tf)
                g,s=rf(inputs,p,strategy)
                self.assertIs(g.state,S1State439.MATCH)
                self.assertEqual((g.private_pivot,g.private_micro_low),(D(15),D(11)))
                self.assertEqual(s["status"],"UNVERIFIED")
                self.assertFalse(s["phases"][3]["action_eligible"])

    def test_both_pivots_and_explicit_threshold(self):
        for kw,state in ((dict(close=D(11)),S1State439.NONMATCH),
                         (dict(close=D(15)),S1State439.NONMATCH),
                         (dict(epsilon=None),S1State439.DISTANCE),
                         (dict(epsilon=D(10)),S1State439.NONMATCH)):
            inputs,p=fixture(**kw)
            self.assertIs(rf(inputs,p)[0].state,state)

    def test_missing_and_prior_early_required(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(p.timeframe)
        self.assertIs(rf(alter(inputs,p.timeframe,rows[:-1]),p)[0].state,S1State439.MISSING)
        q=replace(p,early=replace(p.early,candidate_epsilon=D(10)))
        self.assertIs(rf(inputs,q)[0].state,S1State439.BLOCKED)

    def test_expiry_recovery_and_late_witness(self):
        inputs,p=fixture()
        q=replace(p,early=replace(p.early,expires_at_utc=p.early.expires_at_utc-timedelta(seconds=1)))
        self.assertIs(rf(inputs,q)[0].state,S1State439.BLOCKED)
        rows=list(inputs.snapshots_for(p.timeframe))
        rows[-2]=snap(replace(rows[-2].selected,close=D(15)))
        self.assertIs(rf(alter(inputs,p.timeframe,tuple(rows)),p)[0].state,S1State439.NONMATCH)
        inputs,p=fixture()
        rows=list(inputs.snapshots_for(p.timeframe))
        rows[-3]=snap(replace(rows[-3].selected,verified_at_utc=rows[-2].market_bar_key.bar_start_utc+timedelta(seconds=1)))
        self.assertIs(rf(alter(inputs,p.timeframe,tuple(rows)),p)[0].state,S1State439.BLOCKED)

    def test_bad_frame_scope_and_stale_atr(self):
        inputs,p=fixture(Timeframe.D1)
        self.assertIs(rf(inputs,replace(p,atr_stop=p.atr_stop-1))[0].state,S1State439.BLOCKED)
        for bad in (replace(p,timeframe=Timeframe.H1),replace(p,low_index=True),replace(p,candidate_epsilon=D(-1))):
            _,s=evaluate(inputs,bad)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_shared_modes_redaction_and_legacy(self):
        inputs,p=fixture()
        candidate=profile((request("S6",p,variant="S6/BASE"),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(r.private_preview,"S6").private_preview.assessments[3][1].state,S1State439.MATCH)
            s=r.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for key in (p.early.failure.breakout.event_id,"private_micro_low","private_pivot"):
                self.assertNotIn(key,json.dumps(s))
        r,_=evaluate(inputs,p.early)
        self.assertEqual(len(r.private_preview.assessments),3)
