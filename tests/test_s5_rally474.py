"""§474 S5 first supplied post-transition failed rally, fictional only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.s5_transition473 import S5RallyPlan474
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s5_transition473 import fixture as transition_fixture,evaluate
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def fixture(tf=Timeframe.H1,*,high=D(12),extra=False):
    inputs,p=transition_fixture(tf)
    rows=inputs.snapshots_for(Timeframe.M15)
    start=len(rows)
    prices=[(9,7,8),(8,5,6),(10,7,9),(high,8,11),(10,7,9)]
    if extra:
        prices.extend([(9,6,8),(13,8,11),(10,7,9)])
    added=[]
    for i,(h,l,c) in enumerate(prices):
        begin=p.event_known_at_utc+timedelta(minutes=20*(i+1))
        added.append(snap(make_bar(5400+i,timeframe=Timeframe.M15,start=begin,
            high=D(h),low=D(l),close=D(c),open_price=D(c))))
    inputs=alter(inputs,Timeframe.M15,rows+tuple(added))
    return inputs,S5RallyPlan474(p,start,1,3,1,1,TiePolicy.STRICT_V1)


def rc(inputs,p,strategy=Strategy.SHORT):
    r,s=evaluate(inputs,p,strategy)
    return r.private_preview.assessments[1][1],s


class S5Rally474Tests(unittest.TestCase):
    def test_both_context_frames_and_strategies(self):
        for strategy in Strategy:
            for tf in (Timeframe.D1,Timeframe.H1):
                inputs,p=fixture(tf)
                g,s=rc(inputs,p,strategy)
                self.assertIs(g.state,S1State439.MATCH)
                self.assertEqual((g.private_prior_high,g.private_rally_low,g.private_rally_high),(D(20),D(5),D(12)))
                self.assertEqual(s["status"],"UNVERIFIED")
                self.assertFalse(s["phases"][1]["action_eligible"])

    def test_no_skipped_earlier_rally_or_supplied_bar(self):
        inputs,p=fixture(extra=True)
        self.assertIs(rc(inputs,replace(p,high_index=6))[0].state,S1State439.NONMATCH)
        q=replace(p,history_start=p.history_start+1,low_index=1,high_index=2)
        self.assertIs(rc(inputs,q)[0].state,S1State439.BLOCKED)

    def test_prior_high_preserved_and_exact_transition_required(self):
        inputs,p=fixture(high=D(20))
        self.assertIs(rc(inputs,p)[0].state,S1State439.NONMATCH)
        inputs,p=fixture()
        q=replace(p,context=replace(p.context,event_id="wrong"))
        self.assertIs(rc(inputs,q)[0].state,S1State439.BLOCKED)

    def test_missing_and_late_low_witness(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(Timeframe.M15)
        self.assertIs(rc(alter(inputs,Timeframe.M15,rows[:-1]),p)[0].state,S1State439.MISSING)
        i=p.history_start+2
        late=snap(replace(rows[i].selected,verified_at_utc=rows[i+1].market_bar_key.bar_start_utc+timedelta(seconds=1)))
        self.assertIs(rc(alter(inputs,Timeframe.M15,rows[:i]+(late,)+rows[i+1:]),p)[0].state,S1State439.BLOCKED)

    def test_bad_configuration(self):
        inputs,p=fixture()
        for bad in (replace(p,low_index=True),replace(p,high_index=1),replace(p,right_count=0)):
            _,s=evaluate(inputs,bad)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_shared_modes_and_redaction_and_legacy(self):
        inputs,p=fixture()
        candidate=profile((request("S5",p,variant="S5/BASE"),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(r.private_preview,"S5").private_preview.assessments[1][1].state,S1State439.MATCH)
            s=r.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for key in (p.context.event_id,"private_rally_low","private_rally_high","private_witness_known"):
                self.assertNotIn(key,json.dumps(s))
        r,_=evaluate(inputs,p.context)
        self.assertEqual(len(r.private_preview.assessments),1)
