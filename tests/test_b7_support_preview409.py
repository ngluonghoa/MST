"""§409 fictional same-input B7 R_C regression."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b7_support_preview409 import B7SupportPlan409, B7SupportState409
from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.engine import BaselinePreviewRequest375, evaluate_baseline_preview
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import BASELINE_CORE_TF, BaselineResolvedInputs
from test_causal_indicators import AS_OF, START, make_bar, snap


def model(*, low=D("7"), late=False, missing=False, pivot_tf=Timeframe.D1):
    start = START + timedelta(days=16)
    daily = tuple(snap(make_bar(i, low=D("7") if i == 5 else D("8")))
                  for i in range(15))
    if late:
        daily = daily[:-1] + (snap(replace(daily[-1].selected, verified_at_utc=start+timedelta(hours=1))),)
    hourly = tuple(snap(make_bar(i+50, timeframe=Timeframe.H1,
                   low=D("7") if i == 1 else D("8"),
                   start=START+timedelta(hours=i))) for i in range(3))
    target = snap(make_bar(100, timeframe=Timeframe.M15, start=start, low=low))
    key = daily[0].market_bar_key
    buckets = {Timeframe.D1: daily, Timeframe.H1: hourly,
               Timeframe.M15: () if missing else (target,)}
    return BaselineResolvedInputs(key.instrument_id,key.exchange,AS_OF,False,
        tuple((tf,buckets.get(tf,())) for tf in BASELINE_CORE_TF))


def plan(**kwargs):
    p = B7SupportPlan409(0,Timeframe.D1,0,15,5,1,1,TiePolicy.STRICT_V1,0,15,D("0.4"))
    return replace(p,**kwargs)


def run(data=None, p=None, strategy=Strategy.SHORT, variant="B7/E_RECLAIM"):
    inputs = model() if data is None else data
    req = BaselinePreviewRequest375("B7",strategy,variant,plan() if p is None else p)
    result = evaluate_baseline_preview(inputs,requests=(req,))
    row = next(r for r in result.rows if r.decision.zone_id=="B7" and r.decision.strategy is strategy)
    safe = next(r for r in result.safe_phase_summary()["zones"]
                if r["zone_id"]=="B7" and r["strategy"]==strategy.value)
    return row,safe


class B7Support409Tests(unittest.TestCase):
    def test_both_strategies_and_explicit_variants(self):
        for strategy in Strategy:
            for variant in ("B7/E_RECLAIM","B7/E_CHOCH"):
                row,safe = run(strategy=strategy,variant=variant)
                route,proof = row.private_preview.assessments[0]
                self.assertEqual(route.variant_id,variant)
                self.assertIs(proof.state,B7SupportState409.DISTANCE)
                self.assertEqual(proof.distance_atr,D(0))
                self.assertTrue(proof.near_candidate)
                self.assertEqual([x["ingredient_state"] for x in safe["phases"]],
                                 ["NOT_REQUESTED","DISTANCE_ONLY","NOT_REQUESTED","NOT_REQUESTED"])

    def test_far_is_still_only_distance_and_no_default_k(self):
        row,_ = run(model(low=D("1")))
        self.assertFalse(row.private_preview.assessments[0][1].near_candidate)
        row,_ = run(p=plan(candidate_k_near=None))
        self.assertIsNone(row.private_preview.assessments[0][1].near_candidate)

    def test_explicit_h1_support_and_nonextremum(self):
        row,_ = run(p=plan(pivot_tf=Timeframe.H1,pivot_stop=3,candidate_index=1))
        self.assertIs(row.private_preview.assessments[0][1].state,B7SupportState409.DISTANCE)
        row,_ = run(p=plan(candidate_index=4))
        self.assertIs(row.private_preview.assessments[0][1].state,B7SupportState409.BLOCKED)

    def test_late_history_blocks_without_shortcut(self):
        for p in (plan(),plan(pivot_stop=10)):
            _,safe = run(model(late=True),p)
            self.assertEqual(safe["phases"][1]["ingredient_state"],"BLOCKED")

    def test_missing_exact_window_and_invalid_config(self):
        for data,p in ((model(missing=True),plan()),(model(),plan(atr_stop=16)),
                       (model(),plan(target_index=1))):
            _,safe=run(data,p)
            self.assertEqual(safe["phases"][1]["ingredient_state"],"MISSING_INPUT")
        for p in (plan(target_index=True),plan(candidate_k_near=D("-1")),
                  plan(pivot_tf=Timeframe.M15),plan(pivot_stop=513)):
            _,safe=run(p=p)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_redaction_and_no_authority(self):
        row,safe=run()
        self.assertFalse(row.private_preview.action_eligible)
        self.assertEqual(safe["status"],"UNVERIFIED")
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for forbidden in (model().instrument_id,"distance_atr","candidate_k_near","near_candidate"):
            self.assertNotIn(forbidden,json.dumps(safe))
