"""§495 S8 higher-frame reversal candidate, fictional only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.s8_context492 import S8ConfirmPlan495
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s8_early494 import fixture as early_fixture
from test_s8_exhaustion493 import RANGE,VOLUME
from test_s8_context492 import evaluate
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def fixture(tf=Timeframe.H1,mode=VOLUME,*,close=D(8),epsilon=D(0),high=D(13)):
    inputs,p=early_fixture(mode)
    early=inputs.snapshots_for(Timeframe.M15)[p.target_index].selected
    rows=inputs.snapshots_for(tf)
    extra=[]
    for i in range(5):
        start=early.verified_at_utc+timedelta(minutes=(i+1)*(1440 if tf is Timeframe.D1 else 75))
        c=close if i==4 else D(12)
        b=make_bar(7600+i,timeframe=tf,start=start,open_price=D(12),high=high if i==4 else D(13),
            low=min(c,D(7)) if i==4 else D((11,9,11,11)[i]),close=c)
        if tf is Timeframe.H1:
            end=start+timedelta(hours=1)
            rev=replace(b.observation_revision,first_known_time_utc=end,retrieved_at_utc=end+timedelta(minutes=1))
            b=replace(b,bar_end_utc=end,retrieved_at_utc=rev.retrieved_at_utc,
                      verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
        extra.append(snap(b))
    start=len(rows)
    return alter(inputs,tf,rows+tuple(extra)),S8ConfirmPlan495(p,tf,start+4,start,1,1,1,
        TiePolicy.STRICT_V1,0,start+4 if tf is Timeframe.D1 else p.atr_stop,epsilon)


def rf(inputs,p,strategy=Strategy.SHORT):
    r,s=evaluate(inputs,p,strategy)
    return r.private_preview.assessments[3][1],s


class S8Confirm495Tests(unittest.TestCase):
    def test_frames_modes_strategies(self):
        for strategy in Strategy:
            for tf in (Timeframe.H1,Timeframe.D1):
                for mode in (RANGE,VOLUME):
                    inputs,p=fixture(tf,mode)
                    g,s=rf(inputs,p,strategy)
                    self.assertIs(g.state,S1State439.MATCH)
                    self.assertEqual((g.private_early_low,g.private_key_low),(D(14),D(9)))
                    self.assertEqual(s["status"],"UNVERIFIED")
                    self.assertFalse(s["phases"][3]["action_eligible"])

    def test_strict_cross_and_explicit_threshold(self):
        for kw,state in ((dict(close=D(9)),S1State439.NONMATCH),
                         (dict(close=D(12)),S1State439.NONMATCH),
                         (dict(epsilon=None),S1State439.DISTANCE),
                         (dict(epsilon=D(10)),S1State439.NONMATCH),
                         (dict(high=D(21)),S1State439.NONMATCH)):
            inputs,p=fixture(**kw)
            self.assertIs(rf(inputs,p)[0].state,state)

    def test_missing_and_no_early_bypass(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(p.timeframe)
        self.assertIs(rf(alter(inputs,p.timeframe,rows[:-1]),p)[0].state,S1State439.MISSING)
        self.assertIs(rf(inputs,replace(p,early=replace(p.early,candidate_epsilon=D(10))))[0].state,S1State439.BLOCKED)

    def test_expiry_late_witness_and_m15_recovery(self):
        inputs,p=fixture()
        q=replace(p,early=replace(p.early,exhaustion=replace(p.early.exhaustion,
            expires_at_utc=inputs.snapshots_for(Timeframe.M15)[p.early.target_index].selected.verified_at_utc)))
        self.assertIs(rf(inputs,q)[0].state,S1State439.BLOCKED)
        rows=inputs.snapshots_for(p.timeframe)
        late=snap(replace(rows[-3].selected,verified_at_utc=rows[-2].market_bar_key.bar_start_utc+timedelta(seconds=1)))
        self.assertIs(rf(alter(inputs,p.timeframe,rows[:-3]+(late,)+rows[-2:]),p)[0].state,S1State439.BLOCKED)
        m15=inputs.snapshots_for(Timeframe.M15)
        b=make_bar(7699,timeframe=Timeframe.M15,start=m15[-1].selected.verified_at_utc+timedelta(minutes=5),high=D(21))
        self.assertIs(rf(alter(inputs,Timeframe.M15,m15+(snap(b),)),p)[0].state,S1State439.NONMATCH)

    def test_invalid_scope_and_stale_atr(self):
        inputs,p=fixture(Timeframe.D1)
        self.assertIs(rf(inputs,replace(p,atr_stop=p.atr_stop-1))[0].state,S1State439.BLOCKED)
        for q in (replace(p,timeframe=Timeframe.M15),replace(p,low_index=True),replace(p,candidate_epsilon=D(-1))):
            _,s=evaluate(inputs,q)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_shared_engine_and_redaction(self):
        inputs,p=fixture()
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=profile((request("S8",p),)))
            self.assertIs(row(r.private_preview,"S8").private_preview.assessments[3][1].state,S1State439.MATCH)
            s=r.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for key in (p.early.exhaustion.event_id,"private_key_low","private_rf_known"):
                self.assertNotIn(key,json.dumps(s))
        r,_=evaluate(inputs,p.early)
        self.assertEqual(len(r.private_preview.assessments),3)
