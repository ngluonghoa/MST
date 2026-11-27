"""§494 S8 fictional closed M15 micro-support reversal candidate."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.s8_context492 import S8EarlyPlan494
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s8_exhaustion493 import fixture as exhaustion,RANGE,VOLUME
from test_s8_context492 import evaluate
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def fixture(mode=VOLUME,*,close=D(13),high=D(19),epsilon=D(0)):
    inputs,p=exhaustion(mode)
    start=p.event_known_at_utc+timedelta(minutes=5)
    rows=tuple(snap(make_bar(7500+i,timeframe=Timeframe.M15,start=start+timedelta(minutes=20*i),
        open_price=D(17),high=high if i==4 else D(19),
        low=min(close,D(12)) if i==4 else D((16,14,16,15)[i]),
        close=close if i==4 else D(17))) for i in range(5))
    return alter(inputs,Timeframe.M15,rows),S8EarlyPlan494(p,0,4,1,1,1,TiePolicy.STRICT_V1,0,26,epsilon)


def early(inputs,p,strategy=Strategy.SHORT):
    r,s=evaluate(inputs,p,strategy)
    return r.private_preview.assessments[2][1],s


class S8Early494Tests(unittest.TestCase):
    def test_both_exhaustion_modes_and_strategies(self):
        for strategy in Strategy:
            for mode in (RANGE,VOLUME):
                inputs,p=fixture(mode)
                g,s=early(inputs,p,strategy)
                self.assertIs(g.state,S1State439.MATCH)
                self.assertEqual(g.private_micro_low,D(14))
                self.assertEqual(s["status"],"UNVERIFIED")
                self.assertFalse(s["phases"][2]["action_eligible"])

    def test_strict_closed_cross_and_recovery(self):
        for kw in (dict(close=D(14)),dict(close=D(17)),dict(high=D(21)),dict(epsilon=D(10))):
            inputs,p=fixture(**kw)
            self.assertIs(early(inputs,p)[0].state,S1State439.NONMATCH)
        inputs,p=fixture(epsilon=None)
        self.assertIs(early(inputs,p)[0].state,S1State439.DISTANCE)

    def test_missing_and_late_witness(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(Timeframe.M15)
        self.assertIs(early(alter(inputs,Timeframe.M15,rows[:-1]),p)[0].state,S1State439.MISSING)
        late=snap(replace(rows[2].selected,verified_at_utc=rows[3].market_bar_key.bar_start_utc+timedelta(seconds=1)))
        self.assertIs(early(alter(inputs,Timeframe.M15,rows[:2]+(late,)+rows[3:]),p)[0].state,S1State439.BLOCKED)

    def test_no_rc_bypass_or_expired_event(self):
        inputs,p=fixture()
        for q in (replace(p.exhaustion,event_id="wrong"),replace(p.exhaustion,candidate_min_return=D(10)),
                  replace(p.exhaustion,expires_at_utc=p.exhaustion.event_known_at_utc)):
            self.assertIs(early(inputs,replace(p,exhaustion=q))[0].state,S1State439.BLOCKED)

    def test_invalid_config_and_stale_atr(self):
        inputs,p=fixture()
        self.assertIs(early(inputs,replace(p,atr_stop=25))[0].state,S1State439.BLOCKED)
        for q in (replace(p,low_index=True),replace(p,candidate_epsilon=D(-1)),replace(p,target_index=3)):
            _,s=evaluate(inputs,q)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_shared_modes_and_private_receipt(self):
        inputs,p=fixture()
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=profile((request("S8",p),)))
            self.assertIs(row(r.private_preview,"S8").private_preview.assessments[2][1].state,S1State439.MATCH)
            s=r.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for key in (p.exhaustion.event_id,"private_micro_low","private_early_known"):
                self.assertNotIn(key,json.dumps(s))
        old,_=evaluate(inputs,p.exhaustion)
        self.assertEqual(len(old.private_preview.assessments),2)
