"""§475 fictional S5 first LH later M15 closed rejection."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.s5_transition473 import S5EarlyPlan475
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s5_rally474 import fixture as rally_fixture
from test_s5_transition473 import evaluate
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def fixture(tf=Timeframe.H1,*,high=D("11.5"),close=D(8),k=D(1)):
    inputs,p=rally_fixture(tf)
    rows=inputs.snapshots_for(Timeframe.M15)
    start=rows[-1].selected.verified_at_utc+timedelta(minutes=20)
    target=snap(make_bar(5500,timeframe=Timeframe.M15,start=start,high=high,
        low=min(D(7),close),open_price=D(9),close=close))
    daily=inputs.snapshots_for(Timeframe.D1)
    return alter(inputs,Timeframe.M15,rows+(target,)),S5EarlyPlan475(p,len(rows),0,len(daily),k)


def re(inputs,p,strategy=Strategy.SHORT):
    r,s=evaluate(inputs,p,strategy)
    return r.private_preview.assessments[2][1],s


class S5Early475Tests(unittest.TestCase):
    def test_both_origin_frames_and_strategies(self):
        for strategy in Strategy:
            for tf in (Timeframe.D1,Timeframe.H1):
                inputs,p=fixture(tf)
                g,s=re(inputs,p,strategy)
                self.assertIs(g.state,S1State439.MATCH)
                self.assertEqual((g.private_rally_high,g.private_distance),(D(12),D("0.5")))
                self.assertEqual(s["status"],"UNVERIFIED")
                self.assertFalse(s["phases"][2]["action_eligible"])

    def test_no_default_or_wick_only_or_invalidated_lh(self):
        for kw,state in ((dict(k=None),S1State439.DISTANCE),(dict(k=D(0)),S1State439.NONMATCH),
                         (dict(high=D(13)),S1State439.NONMATCH),(dict(close=D(9)),S1State439.NONMATCH)):
            inputs,p=fixture(**kw)
            self.assertIs(re(inputs,p)[0].state,state)

    def test_rally_required_and_missing_target(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(Timeframe.M15)
        self.assertIs(re(alter(inputs,Timeframe.M15,rows[:-1]),p)[0].state,S1State439.MISSING)
        q=replace(p,rally=replace(p.rally,context=replace(p.rally.context,event_id="wrong")))
        self.assertIs(re(inputs,q)[0].state,S1State439.BLOCKED)

    def test_late_witness_and_stale_atr(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(Timeframe.M15)
        late=snap(replace(rows[-2].selected,verified_at_utc=rows[-1].market_bar_key.bar_start_utc+timedelta(seconds=1)))
        self.assertIs(re(alter(inputs,Timeframe.M15,rows[:-2]+(late,rows[-1])),p)[0].state,S1State439.BLOCKED)
        inputs,p=fixture(Timeframe.D1)
        self.assertIs(re(inputs,replace(p,atr_stop=p.atr_stop-1))[0].state,S1State439.BLOCKED)

    def test_bad_explicit_plan(self):
        inputs,p=fixture()
        for bad in (replace(p,target_index=p.target_index-1),replace(p,candidate_k_rejection=D(-1)),
                    replace(p,atr_start=True)):
            _,s=evaluate(inputs,bad)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_shared_modes_redaction_and_legacy(self):
        inputs,p=fixture()
        candidate=profile((request("S5",p,variant="S5/BASE"),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(r.private_preview,"S5").private_preview.assessments[2][1].state,S1State439.MATCH)
            s=r.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for key in (p.rally.context.event_id,"private_rally_high","private_target_start","private_distance"):
                self.assertNotIn(key,json.dumps(s))
        r,_=evaluate(inputs,p.rally)
        self.assertEqual(len(r.private_preview.assessments),2)
