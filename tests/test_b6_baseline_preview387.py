"""§387 B6 same-input causal preview, synthetic only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b6_baseline_preview387 import B6EnginePlan387, B6State387
from swing_trading.contracts import Strategy
from swing_trading.engine import BaselinePreviewRequest375, evaluate_baseline_preview
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import BASELINE_CORE_TF, BaselineResolvedInputs
from swing_trading.source_quality import ObservationOrigin
from test_causal_contraction_candidate386 import fixture, plan
from test_causal_indicators import AS_OF, make_bar, snap


def model(*, missing=False, early=False, mixed=False, far=False, declining=False, history=None):
    d1=fixture() if history is None else history
    base=fixture()[22 if early else -1].market_bar_key.bar_start_utc
    start=base+timedelta(days=1,hours=7)
    price=D(100) if far else D("109.5")
    prev=price+1 if declining else price-1
    a=make_bar(100,timeframe=Timeframe.M15,start=start,open_price=prev,close=prev,high=prev+1,low=prev-1)
    b=make_bar(101,timeframe=Timeframe.M15,start=start+timedelta(minutes=30),open_price=price,close=price,high=price+1,low=price-1)
    if mixed:
        def imported(row):
            obs=replace(row.observation_key,origin=ObservationOrigin.IMPORT)
            return replace(row,observation_key=obs,observation_revision=replace(row.observation_revision,observation_key=obs))
        a,b=imported(a),imported(b)
    k=fixture()[0].market_bar_key
    frames={Timeframe.D1:d1,Timeframe.M15:() if missing else (snap(a),snap(b))}
    return BaselineResolvedInputs(k.instrument_id,k.exchange,AS_OF,False,
                                  tuple((tf,frames.get(tf,())) for tf in BASELINE_CORE_TF))


def config():
    return B6EnginePlan387(0,26,plan(),0,15,1,D("0.25"))


def evaluate(inputs=None, strategy=Strategy.SHORT, cfg=None, variant="B6/C_TWO_CONTRACTIONS"):
    req=BaselinePreviewRequest375("B6",strategy,variant,config() if cfg is None else cfg)
    result=evaluate_baseline_preview(model() if inputs is None else inputs,requests=(req,))
    row=next(r for r in result.rows if r.decision.zone_id=="B6" and r.decision.strategy is strategy)
    safe=next(r for r in result.safe_phase_summary()["zones"] if r["zone_id"]=="B6" and r["strategy"]==strategy.value)
    return row,safe


class B6Preview387Tests(unittest.TestCase):
    def test_both_strategies_rc_and_re_only(self):
        for strategy in Strategy:
            row,safe=evaluate(strategy=strategy)
            rc,re=(x for _,x in row.private_preview.assessments)
            self.assertIs(rc.state,B6State387.MATCH)
            self.assertIs(re.state,B6State387.DISTANCE)
            self.assertEqual(re.distance,D("0.5"))
            self.assertIs(re.approach,True)
            self.assertEqual([p["ingredient_state"] for p in safe["phases"]],
                             ["NOT_REQUESTED","GEOMETRY_MATCH_ONLY","DISTANCE_ONLY","NOT_REQUESTED"])
            self.assertTrue(all(not p["phase_verified"] and not p["action_eligible"] for p in safe["phases"]))

    def test_missing_m15_does_not_erase_rc(self):
        _,safe=evaluate(model(missing=True))
        self.assertEqual([p["ingredient_state"] for p in safe["phases"]][1:3],
                         ["GEOMETRY_MATCH_ONLY","MISSING_INPUT"])

    def test_future_contraction_and_cross_tf_origin_mismatch_are_blocked(self):
        for inputs in (model(early=True),model(mixed=True)):
            row,safe=evaluate(inputs)
            self.assertEqual(safe["phases"][1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")
            self.assertEqual(safe["phases"][2]["ingredient_state"],"BLOCKED")
            self.assertIsNone(row.private_preview.assessments[1][1].distance)

    def test_far_or_falling_close_never_approach(self):
        for inputs in (model(far=True),model(declining=True)):
            row,safe=evaluate(inputs)
            self.assertIs(row.private_preview.assessments[1][1].approach,False)
            self.assertEqual(safe["phases"][2]["ingredient_state"],"DISTANCE_ONLY")
            self.assertEqual(safe["status"],"UNVERIFIED")

    def test_no_compression_variant_fallback_and_missing_history(self):
        _,safe=evaluate(variant="B6/C_COMPRESSION")
        self.assertTrue(all(p["ingredient_state"]=="CONFIG_REJECTED" for p in safe["phases"]))
        _,safe=evaluate(model(history=()))
        self.assertEqual([p["ingredient_state"] for p in safe["phases"]][1:3],
                         ["MISSING_INPUT","MISSING_INPUT"])

    def test_nonmatch_and_redaction(self):
        row,safe=evaluate(model(history=fixture(((120,90),(128,96),(112,84)))))
        self.assertEqual(safe["phases"][1]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")
        self.assertEqual(safe["phases"][2]["ingredient_state"],"BLOCKED")
        for forbidden in (model().instrument_id,"109.5","candidate_k","depths","distance"):
            self.assertNotIn(forbidden,json.dumps(safe))
