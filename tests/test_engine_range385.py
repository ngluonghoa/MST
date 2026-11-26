"""§385 fictional routed B3/S4 range/near, both strategies."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.engine import BaselinePreviewRequest375, evaluate_baseline_preview
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import BASELINE_CORE_TF, BaselineResolvedInputs
from swing_trading.range_baseline_preview385 import RangeSlice385, RangeEnginePlan385, RangeState385
from swing_trading.source_quality import ObservationOrigin
from test_causal_range_candidate384 import fixture
from test_causal_indicators import AS_OF, make_bar, snap


def model(zone="B3", *, missing=False, early=False, mixed=False, rows=None, far=False):
    history = fixture() if rows is None else rows
    price = D(100) if far else D("90.5") if zone=="B3" else D("109.5")
    start = fixture()[24 if early else -1].market_bar_key.bar_start_utc
    start += timedelta(days=0 if early else 1, hours=7)
    row = make_bar(100, timeframe=Timeframe.M15, start=start,
                   open_price=price, close=price, high=price+1, low=price-1)
    if mixed:
        obs = replace(row.observation_key,origin=ObservationOrigin.IMPORT)
        row = replace(row,observation_key=obs,observation_revision=replace(row.observation_revision,observation_key=obs))
    k = fixture()[0].market_bar_key
    frames={Timeframe.D1:history,Timeframe.M15:() if missing else (snap(row),)}
    return BaselineResolvedInputs(k.instrument_id,k.exchange,AS_OF,False,
                                  tuple((tf,frames.get(tf,())) for tf in BASELINE_CORE_TF))


def plan():
    return RangeEnginePlan385(RangeSlice385(0,35,(17,25),(19,27),1,1,
                               TiePolicy.STRICT_V1,15,D("0.25"),D(2)),Timeframe.M15,0,D("0.25"))


def evaluate(zone="B3", strategy=Strategy.SHORT, inputs=None, config=None):
    req=BaselinePreviewRequest375(zone,strategy,"B3/E_BOS_UP" if zone=="B3" else "S4/E_BOS_DOWN",
                                 plan() if config is None else config)
    result=evaluate_baseline_preview(model(zone) if inputs is None else inputs,requests=(req,))
    row=next(r for r in result.rows if r.decision.zone_id==zone and r.decision.strategy is strategy)
    safe=next(r for r in result.safe_phase_summary()["zones"] if r["zone_id"]==zone and r["strategy"]==strategy.value)
    return row,safe


class RoutedRange385Tests(unittest.TestCase):
    def test_both_mirrors_both_strategies_and_private_distance(self):
        for zone in ("B3","S4"):
            for strategy in Strategy:
                row,safe=evaluate(zone,strategy)
                r0,rc=(e for _,e in row.private_preview.assessments)
                self.assertEqual(r0.state,RangeState385.MATCH)
                self.assertEqual(rc.state,RangeState385.DISTANCE)
                self.assertEqual(rc.distance,D("0.5"))
                self.assertIs(rc.near_candidate,True)
                self.assertEqual([p["ingredient_state"] for p in safe["phases"]],
                                 ["GEOMETRY_MATCH_ONLY","DISTANCE_ONLY","NOT_REQUESTED","NOT_REQUESTED"])
                self.assertTrue(all(not p["phase_verified"] and not p["action_eligible"] for p in safe["phases"]))

    def test_missing_target_keeps_independent_r0(self):
        row,safe=evaluate(inputs=model(missing=True))
        self.assertEqual([p["ingredient_state"] for p in safe["phases"]][:2],
                         ["GEOMETRY_MATCH_ONLY","MISSING_INPUT"])
        self.assertEqual(row.private_preview.assessments[1][1].state,RangeState385.MISSING)

    def test_range_not_available_before_target_and_origin_mismatch(self):
        for inputs in (model(early=True), model(mixed=True)):
            row,safe=evaluate(inputs=inputs)
            self.assertEqual([p["ingredient_state"] for p in safe["phases"]][:2],
                             ["GEOMETRY_MATCH_ONLY","BLOCKED"])
            self.assertIsNone(row.private_preview.assessments[1][1].distance)

    def test_nonmatch_and_far_are_not_negative_zone_decisions(self):
        row,safe=evaluate(inputs=model(rows=fixture(upper="112")))
        self.assertEqual(safe["phases"][0]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")
        self.assertEqual(safe["status"],"UNVERIFIED")
        row,safe=evaluate(inputs=model(far=True))
        self.assertIs(row.private_preview.assessments[1][1].near_candidate,False)
        self.assertEqual(safe["phases"][1]["ingredient_state"],"DISTANCE_ONLY")

    def test_missing_d1_and_bad_plan_remain_fail_closed(self):
        _,safe=evaluate(inputs=model(rows=()))
        self.assertEqual([p["ingredient_state"] for p in safe["phases"]][:2],
                         ["MISSING_INPUT","MISSING_INPUT"])
        _,bad=evaluate(config=replace(plan(),target_tf=Timeframe.H4))
        self.assertTrue(all(p["ingredient_state"]=="CONFIG_REJECTED" for p in bad["phases"]))

    def test_redaction_and_no_full_analysis(self):
        inputs=model()
        _,safe=evaluate(inputs=inputs)
        for forbidden in (inputs.instrument_id,"distance","candidate_k","pivot_price","90.5","110"):
            self.assertNotIn(forbidden,json.dumps(safe))
        self.assertEqual(safe["status"],"UNVERIFIED")
