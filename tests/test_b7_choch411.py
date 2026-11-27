"""§411 B7 explicit prior M15 LH/LL and closed micro-high cross."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b7_support_preview409 import B7ChochPlan411, B7ReclaimPlan410, B7SupportState409
from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from test_b7_support_preview409 import model, plan, run
from test_causal_indicators import make_bar, snap


def data(*, close=D("13"), prior=D("10"), rising=False, late=False, missing=False):
    base = model()
    start = base.snapshots_for(Timeframe.M15)[0].market_bar_key.bar_start_utc
    highs = [10,11 if rising else 14,10,10,10,12,10,9,10,14,15]
    lows = [9,9,9,8,9,9,8,6,8,7,7]
    rows = []
    for i,(high,low) in enumerate(zip(highs,lows)):
        price = (D(high)+D(low))/2 if i < 9 else prior if i == 9 else close
        row = make_bar(200+i,timeframe=Timeframe.M15,start=start+timedelta(minutes=30*i),
                       open_price=price,close=price,high=D(high),low=D(low))
        rows.append(row)
    if late:
        rows[8] = replace(rows[8],verified_at_utc=rows[9].bar_end_utc)
    if missing:
        rows.pop()
    return replace(base,buckets=tuple((tf,tuple(map(snap,rows)) if tf is Timeframe.M15 else items)
                                      for tf,items in base.buckets))


def config(**kwargs):
    p = B7ChochPlan411(0,9,(1,5),(3,7),1,1,TiePolicy.STRICT_V1,D("0.1"))
    return replace(plan(target_index=9),choch=replace(p,**kwargs))


def evaluate(inputs=None,p=None,strategy=Strategy.SHORT,variant="B7/E_CHOCH"):
    return run(data() if inputs is None else inputs,config() if p is None else p,
               strategy=strategy,variant=variant)


class B7Choch411Tests(unittest.TestCase):
    def test_both_strategies_micro_structure_and_cross(self):
        for strategy in Strategy:
            row,safe=evaluate(strategy=strategy)
            self.assertIs(row.private_preview.assessments[1][1].state,B7SupportState409.MATCH)
            self.assertEqual(safe["phases"][2]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_wick_nonfalling_and_already_above_nonmatch(self):
        for inputs in (data(close=D("11")),data(rising=True),data(prior=D("13"))):
            row,_=evaluate(inputs)
            self.assertIs(row.private_preview.assessments[1][1].state,B7SupportState409.NONMATCH)

    def test_missing_late_or_invalid_pivot(self):
        for inputs,p,state in ((data(missing=True),config(),"MISSING_INPUT"),
                (data(late=True),config(),"BLOCKED"),(data(),config(high_indices=(2,5)),"BLOCKED")):
            _,safe=evaluate(inputs,p)
            self.assertEqual(safe["phases"][2]["ingredient_state"],state)

    def test_explicit_variants_and_invalid_plan(self):
        for p in (config(high_indices=(5,1)),config(history_stop=10),
                  config(candidate_epsilon=None),config(right_count=True),
                  replace(config(),reclaim=B7ReclaimPlan410(D(0)))):
            _,safe=evaluate(p=p)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        _,safe=evaluate(variant="B7/E_RECLAIM")
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_rc_independent_and_old_plan_unchanged(self):
        _,safe=evaluate(p=replace(config(),candidate_index=4))
        self.assertEqual(safe["phases"][1]["ingredient_state"],"BLOCKED")
        self.assertEqual(safe["phases"][2]["ingredient_state"],"GEOMETRY_MATCH_ONLY")
        _,safe=evaluate(p=replace(config(),choch=None))
        self.assertEqual(safe["phases"][2]["ingredient_state"],"NOT_REQUESTED")

    def test_redaction_and_no_authority(self):
        row,safe=evaluate()
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in (data().instrument_id,"high_indices","candidate_epsilon","pivot_price"):
            self.assertNotIn(secret,json.dumps(safe))
