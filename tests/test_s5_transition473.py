"""§473 fictional S5 prior rising geometry and bearish transition."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.s5_transition473 import S5TransitionPlan473
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from swing_trading.engine import evaluate_baseline_preview
from test_b7_support_preview409 import model
from test_causal_indicators import make_bar,snap,START
from test_s2_rally449 import alter
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def fixture(tf=Timeframe.H1,*,close=D(7),fall=False,epsilon=D(0)):
    inputs=model()
    rows=[]
    # For D1, ATR includes the same supplied pre-transition history.
    prefix=15 if tf is Timeframe.D1 else 0
    for i in range(prefix+11):
        j=i-prefix
        high=D(16 if j==1 else (14 if fall else 20) if j==5 else 12)
        low=D(6 if j==3 else 8 if j==7 else 9)
        c=close if j==10 else D(10)
        low=min(low,c)
        start=START+timedelta(minutes=i*(1440 if tf is Timeframe.D1 else 75),
                              days=0 if tf is Timeframe.D1 else 20)
        b=make_bar(5300+i,timeframe=tf,start=start,open_price=c,high=high,low=low,close=c)
        if tf is Timeframe.H1:
            end=start+timedelta(hours=1)
            rev=replace(b.observation_revision,first_known_time_utc=end,retrieved_at_utc=end+timedelta(minutes=1))
            b=replace(b,bar_end_utc=end,retrieved_at_utc=rev.retrieved_at_utc,
                      verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
        rows.append(snap(b))
    inputs=alter(inputs,tf,tuple(rows))
    target=rows[-1].selected
    p=S5TransitionPlan473(tf,prefix,len(rows)-1,(1,5),(3,7),1,1,TiePolicy.STRICT_V1,0,
        len(rows)-1 if tf is Timeframe.D1 else 15,epsilon,target.source_event_ids[0],
        target.observation_revision.source_revision_or_payload_digest,target.market_bar_key.bar_start_utc,target.verified_at_utc)
    return inputs,p


def evaluate(inputs,p,strategy=Strategy.SHORT):
    result=evaluate_baseline_preview(inputs,requests=(request("S5",p,strategy=strategy,variant="S5/BASE"),))
    r=next(r for r in result.rows if r.decision.zone_id=="S5" and r.decision.strategy is strategy)
    s=next(r for r in result.safe_phase_summary()["zones"] if r["zone_id"]=="S5" and r["strategy"]==strategy.value)
    return r,s


def r0(inputs,p,strategy=Strategy.SHORT):
    r,s=evaluate(inputs,p,strategy)
    return r.private_preview.assessments[0][1],s


class S5Transition473Tests(unittest.TestCase):
    def test_both_frames_strategies(self):
        for strategy in Strategy:
            for tf in (Timeframe.D1,Timeframe.H1):
                inputs,p=fixture(tf)
                g,s=r0(inputs,p,strategy)
                self.assertIs(g.state,S1State439.MATCH)
                self.assertEqual((g.private_prior_high,g.private_prior_hl),(D(20),D(8)))
                self.assertEqual(s["status"],"UNVERIFIED")
                self.assertFalse(s["phases"][0]["action_eligible"])

    def test_no_rising_or_wick_or_threshold_default(self):
        for kw,state in ((dict(fall=True),S1State439.NONMATCH),(dict(close=D(8)),S1State439.NONMATCH),
                         (dict(epsilon=None),S1State439.DISTANCE),(dict(epsilon=D(10)),S1State439.NONMATCH)):
            inputs,p=fixture(**kw)
            self.assertIs(r0(inputs,p)[0].state,state)

    def test_exact_identity_and_known_clock(self):
        inputs,p=fixture()
        for bad in (replace(p,event_id="wrong"),replace(p,revision_digest="wrong"),
                    replace(p,bar_start_utc=p.bar_start_utc+timedelta(seconds=1)),
                    replace(p,event_known_at_utc=p.event_known_at_utc-timedelta(seconds=1)),
                    replace(p,event_known_at_utc=inputs.as_of_utc+timedelta(seconds=1))):
            self.assertIs(r0(inputs,bad)[0].state,S1State439.BLOCKED)

    def test_missing_and_late_witness(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(p.timeframe)
        self.assertIs(r0(alter(inputs,p.timeframe,rows[:-1]),p)[0].state,S1State439.MISSING)
        late=snap(replace(rows[-3].selected,verified_at_utc=p.bar_start_utc+timedelta(seconds=1)))
        self.assertIs(r0(alter(inputs,p.timeframe,rows[:-3]+(late,)+rows[-2:]),p)[0].state,S1State439.BLOCKED)

    def test_bad_config_and_stale_atr(self):
        inputs,p=fixture(Timeframe.D1)
        self.assertIs(r0(inputs,replace(p,atr_stop=p.atr_stop-1))[0].state,S1State439.BLOCKED)
        for bad in (replace(p,timeframe=Timeframe.M15),replace(p,history_start=p.target_index),replace(p,candidate_epsilon=D(-1))):
            _,s=evaluate(inputs,bad)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_same_modes_no_publication_or_private_data(self):
        inputs,p=fixture()
        candidate=profile((request("S5",p,variant="S5/BASE"),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            result=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(result.private_preview,"S5").private_preview.assessments[0][1].state,S1State439.MATCH)
            s=result.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for key in (p.event_id,p.revision_digest,"private_prior_high","private_event_start"):
                self.assertNotIn(key,json.dumps(s))
