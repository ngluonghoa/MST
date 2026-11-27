"""§467 causal upper-boundary closed rejection, fictional S4 only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.range_baseline_preview385 import RangeState385
from swing_trading.s4_rejection467 import S4RejectionPlan467
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_engine_range385 import model,plan
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile
from swing_trading.engine import evaluate_baseline_preview

VARIANTS=("S4/E_FALSE_BREAK","S4/E_BOS_DOWN")


def fixture(tf=Timeframe.M15,*,close=D("107.5"),k=D("0.5"),far=False):
    inputs=model("S4",far=far)
    near=inputs.snapshots_for(Timeframe.M15)[0].selected
    start=near.market_bar_key.bar_start_utc
    bars=[]
    for i,c in enumerate((near.close,close)):
        b=make_bar(4700+i,timeframe=tf,start=start+timedelta(minutes=i*(20 if tf is Timeframe.M15 else 75)),
                   open_price=c,high=max(D("110.5"),c),low=min(D(106),c),close=c)
        if tf is Timeframe.H1:
            end=b.market_bar_key.bar_start_utc+timedelta(hours=1)
            rev=replace(b.observation_revision,first_known_time_utc=end,retrieved_at_utc=end+timedelta(minutes=1))
            b=replace(b,bar_end_utc=end,retrieved_at_utc=rev.retrieved_at_utc,
                      verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
        bars.append(snap(b))
    return alter(inputs,tf,tuple(bars)),S4RejectionPlan467(replace(plan(),target_tf=tf),1,k)


def evaluate(inputs,p,strategy=Strategy.SHORT,variant=VARIANTS[0]):
    result=evaluate_baseline_preview(inputs,requests=(request("S4",p,strategy=strategy,variant=variant),))
    r=next(x for x in result.rows if x.decision.zone_id=="S4" and x.decision.strategy is strategy)
    s=next(x for x in result.safe_phase_summary()["zones"] if x["zone_id"]=="S4" and x["strategy"]==strategy.value)
    return r,s


def rc(inputs,p,strategy=Strategy.SHORT,variant=VARIANTS[0]):
    r,s=evaluate(inputs,p,strategy,variant)
    return r.private_preview.assessments[1][1],s


class S4Rejection467Tests(unittest.TestCase):
    def test_both_strategies_variants_frames_and_exact_edge(self):
        for strategy in Strategy:
            for variant in VARIANTS:
                for tf in (Timeframe.M15,Timeframe.H1):
                    inputs,p=fixture(tf)
                    proof,s=rc(inputs,p,strategy,variant)
                    self.assertIs(proof.state,RangeState385.MATCH)
                    self.assertEqual(proof.distance,D(2))
                    self.assertEqual(s["status"],"UNVERIFIED")
                    self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in s["phases"]))

    def test_no_inferred_threshold_or_wick_only(self):
        for close,k,state in ((D("107.5"),None,RangeState385.DISTANCE),
                              (D("107.5"),D("0.51"),RangeState385.NONMATCH),
                              (D("109.5"),D(0),RangeState385.NONMATCH),
                              (D(89),D(0),RangeState385.NONMATCH),
                              (D(111),D(0),RangeState385.NONMATCH)):
            inputs,p=fixture(close=close,k=k)
            self.assertIs(rc(inputs,p)[0].state,state)

    def test_near_required_and_missing_later_bar(self):
        inputs,p=fixture(far=True)
        self.assertIs(rc(inputs,p)[0].state,RangeState385.NONMATCH)
        inputs,p=fixture()
        self.assertIs(rc(inputs,replace(p,rejection_index=2))[0].state,RangeState385.MISSING)

    def test_prior_path_late_and_daily_tail(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(Timeframe.M15)
        late=snap(replace(rows[0].selected,verified_at_utc=rows[1].market_bar_key.bar_start_utc+timedelta(minutes=1)))
        self.assertIs(rc(alter(inputs,Timeframe.M15,(late,rows[1])),p)[0].state,RangeState385.BLOCKED)
        daily=inputs.snapshots_for(Timeframe.D1)
        extra=snap(make_bar(4799,start=daily[-1].market_bar_key.bar_start_utc+timedelta(days=1),
                            open_price=D(100),high=D(102),low=D(98),close=D(100)))
        self.assertIs(rc(alter(inputs,Timeframe.D1,daily+(extra,)),p)[0].state,RangeState385.BLOCKED)

    def test_bad_plan_rejected_and_legacy_distance_unchanged(self):
        inputs,p=fixture()
        for bad in (replace(p,rejection_index=0),replace(p,candidate_k_reject=D(-1)),
                    replace(p,context=replace(p.context,target_tf=Timeframe.H4))):
            _,s=evaluate(inputs,bad)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))
        r,_=evaluate(inputs,p.context)
        self.assertIs(r.private_preview.assessments[1][1].state,RangeState385.DISTANCE)

    def test_shared_modes_and_redacted_output(self):
        inputs,p=fixture()
        candidate=profile((request("S4",p,variant=VARIANTS[0]),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(r.private_preview,"S4").private_preview.assessments[1][1].state,RangeState385.MATCH)
            safe=r.safe_summary()
            self.assertFalse(safe["publication_allowed"])
            for private in ("candidate_k_reject","distance","private_range","107.5",inputs.instrument_id):
                self.assertNotIn(private,json.dumps(safe))
