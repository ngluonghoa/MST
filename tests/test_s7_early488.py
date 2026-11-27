"""§488 S7 exact M15 closed rejection shapes, fictional only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.s7_retest_evidence import S7EarlyMode
from swing_trading.s7_breakdown486 import S7EarlyPlan488
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s7_retest487 import fixture as retest_fixture
from test_s7_breakdown486 import evaluate
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile

TOUCH=S7EarlyMode.TOUCH_CLOSE_BELOW
LATER=S7EarlyMode.LATER_CLOSE_BELOW


def fixture(tf=Timeframe.H1,mode=TOUCH,*,close=D(4),retest_close=D(6),**kw):
    inputs,p=retest_fixture(tf,**kw)
    rows=inputs.snapshots_for(Timeframe.M15)
    if mode is LATER:
        r=rows[-1].selected
        retest=snap(replace(r,high=max(r.high,retest_close),close=retest_close))
        follow=snap(make_bar(5900,timeframe=Timeframe.M15,start=r.verified_at_utc+timedelta(minutes=20),
            high=max(D(6),close),low=min(D(3),close),open_price=D(6),close=close))
        rows=rows[:-1]+(retest,follow)
        inputs=alter(inputs,Timeframe.M15,rows)
    return inputs,S7EarlyPlan488(p,mode,len(rows)-1,rows[-1].selected.verified_at_utc+timedelta(days=10),
        p.breakdown.bar_start_utc)


def re(inputs,p,strategy=Strategy.SHORT,variant="S7/F_MICRO_BREAK"):
    r,s=evaluate(inputs,p,strategy,variant)
    return r.private_preview.assessments[2][1],s


class S7Early488Tests(unittest.TestCase):
    def test_both_shapes_frames_strategies_and_branches(self):
        for strategy in Strategy:
            for tf in (Timeframe.H1,Timeframe.D1):
                for mode in (TOUCH,LATER):
                    for variant in ("S7/F_MICRO_BREAK","S7/F_CONTINUATION"):
                        inputs,p=fixture(tf,mode)
                        g,s=re(inputs,p,strategy,variant)
                        self.assertIs(g.state,S1State439.MATCH)
                        self.assertEqual(g.private_mode,mode)
                        self.assertEqual(s["status"],"UNVERIFIED")
                        self.assertFalse(s["phases"][2]["action_eligible"])

    def test_no_shape_fallback_or_equality(self):
        for kw in (dict(mode=LATER,close=D(5)),dict(mode=LATER,retest_close=D(5)),
                   dict(mode=LATER,retest_close=D(4)),dict(high=D("4.5"),k=D(1))):
            inputs,p=fixture(**kw)
            self.assertIs(re(inputs,p)[0].state,S1State439.NONMATCH)

    def test_missing_followup_and_unmatched_retest(self):
        inputs,p=fixture(mode=LATER)
        rows=inputs.snapshots_for(Timeframe.M15)
        self.assertIs(re(alter(inputs,Timeframe.M15,rows[:-1]),p)[0].state,S1State439.MISSING)
        self.assertIs(re(inputs,replace(p,retest=replace(p.retest,candidate_max_sessions=1)))[0].state,S1State439.BLOCKED)

    def test_late_witness_and_expiry(self):
        inputs,p=fixture(mode=LATER)
        rows=inputs.snapshots_for(Timeframe.M15)
        late=snap(replace(rows[-2].selected,verified_at_utc=rows[-1].market_bar_key.bar_start_utc+timedelta(seconds=1)))
        self.assertIs(re(alter(inputs,Timeframe.M15,rows[:-2]+(late,rows[-1])),p)[0].state,S1State439.BLOCKED)
        q=replace(p,expires_at_utc=rows[-1].selected.verified_at_utc-timedelta(seconds=1))
        self.assertIs(re(inputs,q)[0].state,S1State439.BLOCKED)

    def test_bad_explicit_policy(self):
        inputs,p=fixture()
        for bad in (replace(p,mode="TOUCH_CLOSE_BELOW"),replace(p,target_index=p.target_index+1),
                    replace(p,policy_known_at_utc=p.policy_known_at_utc+timedelta(seconds=1))):
            _,s=evaluate(inputs,bad)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_shared_modes_redaction_legacy_and_pending_rf(self):
        inputs,p=fixture()
        candidate=profile((request("S7",p,variant="S7/F_MICRO_BREAK"),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(r.private_preview,"S7").private_preview.assessments[2][1].state,S1State439.MATCH)
            s=r.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for key in (p.retest.breakdown.event_id,"private_early_known","private_pivot","private_mode"):
                self.assertNotIn(key,json.dumps(s))
        r,_=evaluate(inputs,p.retest)
        self.assertEqual(len(r.private_preview.assessments),2)
        r,s=evaluate(inputs,p,variant="S7/F_CONTINUATION")
        self.assertEqual(len(r.private_preview.assessments),3)
        self.assertFalse(s["phases"][3]["action_eligible"])
