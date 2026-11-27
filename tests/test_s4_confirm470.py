"""§470 S4 later H1/D1 range micro-low confirmation, fictional only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.range_baseline_preview385 import RangeState385
from swing_trading.s4_rejection467 import S4ConfirmPlan470,S4FalseBreakPlan468
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s4_rejection467 import evaluate,VARIANTS
from test_s4_false_break468 import fixture as false_fixture
from test_s4_bos_down469 import fixture as bos_fixture
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def fixture(variant=VARIANTS[0],tf=Timeframe.H1,*,close=D("100.5"),epsilon=D(0)):
    inputs,p=(false_fixture() if variant==VARIANTS[0] else bos_fixture())
    i=p.reentry_index if type(p) is S4FalseBreakPlan468 else p.target_index
    early=inputs.snapshots_for(p.timeframe)[i].selected
    rows=inputs.snapshots_for(tf)
    extra=[]
    for j,(c,low) in enumerate(zip((D(104),D(102),D(104),D(104),close),(103,101,103,103,100))):
        start=early.verified_at_utc+timedelta(minutes=(j+1)*(1440 if tf is Timeframe.D1 else 75))
        b=make_bar(5000+j,timeframe=tf,start=start,open_price=c,high=max(D(106),c),
                   low=min(D(low),c),close=c)
        if tf is Timeframe.H1:
            end=start+timedelta(hours=1)
            rev=replace(b.observation_revision,first_known_time_utc=end,retrieved_at_utc=end+timedelta(minutes=1))
            b=replace(b,bar_end_utc=end,retrieved_at_utc=rev.retrieved_at_utc,
                      verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
        extra.append(snap(b))
    start=len(rows)
    stop=start+4 if tf is Timeframe.D1 else 35
    return alter(inputs,tf,rows+tuple(extra)),S4ConfirmPlan470(p,tf,start+4,start,1,1,1,TiePolicy.STRICT_V1,0,stop,epsilon)


def rf(inputs,p,strategy=Strategy.SHORT,variant=VARIANTS[0]):
    r,s=evaluate(inputs,p,strategy,variant)
    return r.private_preview.assessments[3][1],s


class S4Confirm470Tests(unittest.TestCase):
    def test_both_early_variants_frames_and_strategies(self):
        for strategy in Strategy:
            for variant in VARIANTS:
                for tf in (Timeframe.H1,Timeframe.D1):
                    inputs,p=fixture(variant,tf)
                    g,s=rf(inputs,p,strategy,variant)
                    self.assertIs(g.state,RangeState385.MATCH)
                    self.assertEqual(g.distance,D("0.5"))
                    r,_=evaluate(inputs,p,strategy,variant)
                    self.assertIs(r.private_preview.assessments[3][0].selected_frame,tf)
                    self.assertEqual(s["status"],"UNVERIFIED")
                    self.assertTrue(all(not x["action_eligible"] for x in s["phases"]))

    def test_close_threshold_and_original_range(self):
        for close,epsilon,state in ((D(101),D(0),RangeState385.NONMATCH),
                                    (D("100.5"),None,RangeState385.DISTANCE),
                                    (D("100.5"),D(10),RangeState385.NONMATCH),
                                    (D(89),D(0),RangeState385.NONMATCH)):
            inputs,p=fixture(close=close,epsilon=epsilon)
            self.assertIs(rf(inputs,p)[0].state,state)

    def test_early_required_and_missing_confirmation(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(p.timeframe)
        self.assertIs(rf(alter(inputs,p.timeframe,rows[:-1]),p)[0].state,RangeState385.MISSING)
        self.assertIs(rf(inputs,replace(p,early=replace(p.early,candidate_epsilon=D(10))))[0].state,
                      RangeState385.BLOCKED)

    def test_late_pivot_and_intervening_other_frame_break(self):
        inputs,p=fixture()
        rows=list(inputs.snapshots_for(p.timeframe))
        w=p.history_start+2
        rows[w]=snap(replace(rows[w].selected,
                            verified_at_utc=rows[w+1].market_bar_key.bar_start_utc+timedelta(minutes=1)))
        self.assertIs(rf(alter(inputs,p.timeframe,tuple(rows)),p)[0].state,RangeState385.BLOCKED)
        inputs,p=fixture()
        m15=inputs.snapshots_for(Timeframe.M15)
        start=m15[-1].selected.verified_at_utc+timedelta(minutes=20)
        bad=snap(make_bar(5090,timeframe=Timeframe.M15,start=start,open_price=D(111),
                          high=D(112),low=D(110),close=D(111)))
        self.assertIs(rf(alter(inputs,Timeframe.M15,m15+(bad,)),p)[0].state,RangeState385.NONMATCH)

    def test_stale_atr_and_invalid_scope(self):
        inputs,p=fixture(tf=Timeframe.D1)
        self.assertIs(rf(inputs,replace(p,atr_stop=p.atr_stop-1))[0].state,RangeState385.BLOCKED)
        for bad,variant in ((p,VARIANTS[1]),(replace(p,timeframe=Timeframe.M15),VARIANTS[0]),
                            (replace(p,history_start=p.target_index),VARIANTS[0])):
            _,s=evaluate(inputs,bad,variant=variant)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_shared_modes_redaction_and_legacy(self):
        inputs,p=fixture()
        candidate=profile((request("S4",p,variant=VARIANTS[0]),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(r.private_preview,"S4").private_preview.assessments[3][1].state,RangeState385.MATCH)
            s=r.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for private in ("candidate_epsilon","distance","private_range","100.5",inputs.instrument_id):
                self.assertNotIn(private,json.dumps(s))
        r,_=evaluate(inputs,p.early,variant=VARIANTS[0])
        self.assertEqual(len(r.private_preview.assessments),3)
