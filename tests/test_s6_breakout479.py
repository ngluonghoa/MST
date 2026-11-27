"""§479 fictional prior closed breakout event candidate."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.s6_breakout479 import S6BreakoutPlan479
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from swing_trading.engine import evaluate_baseline_preview
from test_b7_support_preview409 import model
from test_causal_indicators import make_bar,snap,START
from test_s2_rally449 import alter
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def fixture(tf=Timeframe.H1,*,close=D(16),epsilon=D(0)):
    inputs=model()
    prefix=15 if tf is Timeframe.D1 else 0
    rows=[]
    for i in range(prefix+5):
        j=i-prefix
        c=close if j==4 else D(10)
        high=max(D(15 if j==1 else 12),c)
        start=START+timedelta(minutes=i*(1440 if tf is Timeframe.D1 else 75),
                             days=0 if tf is Timeframe.D1 else 20)
        b=make_bar(5700+i,timeframe=tf,start=start,open_price=c,high=high,low=min(D(8),c),close=c)
        if tf is Timeframe.H1:
            end=start+timedelta(hours=1)
            rev=replace(b.observation_revision,first_known_time_utc=end,retrieved_at_utc=end+timedelta(minutes=1))
            b=replace(b,bar_end_utc=end,retrieved_at_utc=rev.retrieved_at_utc,
                      verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
        rows.append(snap(b))
    inputs=alter(inputs,tf,tuple(rows))
    b=rows[-1].selected
    return inputs,S6BreakoutPlan479(tf,prefix,len(rows)-1,1,1,1,TiePolicy.STRICT_V1,0,
        len(rows)-1 if tf is Timeframe.D1 else 15,epsilon,b.source_event_ids[0],
        b.observation_revision.source_revision_or_payload_digest,b.market_bar_key.bar_start_utc,b.verified_at_utc,D(15))


def evaluate(inputs,p,strategy=Strategy.SHORT):
    r=evaluate_baseline_preview(inputs,requests=(request("S6",p,strategy=strategy,variant="S6/BASE"),))
    a=next(x for x in r.rows if x.decision.zone_id=="S6" and x.decision.strategy is strategy)
    s=next(x for x in r.safe_phase_summary()["zones"] if x["zone_id"]=="S6" and x["strategy"]==strategy.value)
    return a,s


def r0(inputs,p,strategy=Strategy.SHORT):
    r,s=evaluate(inputs,p,strategy)
    return r.private_preview.assessments[0][1],s


class S6Breakout479Tests(unittest.TestCase):
    def test_both_diagnostic_frames_and_strategies(self):
        for strategy in Strategy:
            for tf in (Timeframe.H1,Timeframe.D1):
                inputs,p=fixture(tf)
                g,s=r0(inputs,p,strategy)
                self.assertIs(g.state,S1State439.MATCH)
                self.assertEqual(g.private_pivot,D(15))
                self.assertEqual(s["status"],"UNVERIFIED")
                self.assertFalse(s["phases"][0]["action_eligible"])

    def test_exact_close_and_threshold(self):
        for kw,state in ((dict(close=D(15)),S1State439.NONMATCH),
                         (dict(epsilon=None),S1State439.DISTANCE),
                         (dict(epsilon=D(10)),S1State439.NONMATCH)):
            inputs,p=fixture(**kw)
            self.assertIs(r0(inputs,p)[0].state,state)

    def test_exact_event_and_pivot(self):
        inputs,p=fixture()
        for bad in (replace(p,event_id="wrong"),replace(p,revision_digest="wrong"),
                    replace(p,bar_start_utc=p.bar_start_utc+timedelta(seconds=1)),
                    replace(p,event_known_at_utc=p.event_known_at_utc-timedelta(seconds=1))):
            self.assertIs(r0(inputs,bad)[0].state,S1State439.BLOCKED)
        self.assertIs(r0(inputs,replace(p,pivot_price=D(14)))[0].state,S1State439.NONMATCH)

    def test_missing_and_late_witness(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(p.timeframe)
        self.assertIs(r0(alter(inputs,p.timeframe,rows[:-1]),p)[0].state,S1State439.MISSING)
        late=snap(replace(rows[-3].selected,verified_at_utc=rows[-2].market_bar_key.bar_start_utc+timedelta(seconds=1)))
        self.assertIs(r0(alter(inputs,p.timeframe,rows[:-3]+(late,)+rows[-2:]),p)[0].state,S1State439.BLOCKED)

    def test_bad_plan_and_stale_atr(self):
        inputs,p=fixture(Timeframe.D1)
        self.assertIs(r0(inputs,replace(p,atr_stop=p.atr_stop-1))[0].state,S1State439.BLOCKED)
        for bad in (replace(p,timeframe=Timeframe.M15),replace(p,pivot_index=True),
                    replace(p,pivot_price=D(0)),replace(p,candidate_epsilon=D(-1))):
            _,s=evaluate(inputs,bad)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_shared_modes_and_redaction(self):
        inputs,p=fixture()
        candidate=profile((request("S6",p,variant="S6/BASE"),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(r.private_preview,"S6").private_preview.assessments[0][1].state,S1State439.MATCH)
            s=r.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for key in (p.event_id,p.revision_digest,"private_pivot","private_event_known"):
                self.assertNotIn(key,json.dumps(s))
