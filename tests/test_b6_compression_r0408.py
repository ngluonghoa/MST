"""§408 compression R0 pre-base D1 trend diagnostics, fictional only."""
from dataclasses import replace
from datetime import timedelta
import json
import unittest

from swing_trading.b6_baseline_preview387 import B6TrendPlan390, B6State387
from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.source_quality import ResolvedBarSnapshotV12
from test_b6_compression_pivot402 import fixture as base_fixture, plan as base_plan
from test_b6_compression_rc396 import model, run
from test_causal_trend_candidate382 import fixture as trend_fixture
from test_causal_indicators import make_bar, snap


def data(direction=1, *, late=False, conflict=False, missing=False, higher=False):
    base=base_fixture(higher=higher)
    begin=base[0].market_bar_key.bar_start_utc-timedelta(days=60)
    prefix=tuple(snap(make_bar(200+i,start=begin+timedelta(days=i),
        open_price=s.selected.open,high=s.selected.high,low=s.selected.low,
        close=s.selected.close)) for i,s in enumerate(trend_fixture(direction)))
    if late:
        prefix=prefix[:-1]+(snap(replace(prefix[-1].selected,
                     verified_at_utc=base[0].selected.bar_end_utc)),)
    if conflict:
        prefix=prefix[:5]+(ResolvedBarSnapshotV12(prefix[5].market_bar_key,None,2,
                         "SOURCE_OR_REVISION_CONFLICT"),)+prefix[6:]
    return model((() if missing else prefix)+base)


def plan(direction=1, offset=60):
    h,l=((10,30),(20,40)) if direction>0 else ((20,40),(10,30))
    return replace(base_plan(),target_index=offset+4,
        r0=B6TrendPlan390(10,h,l,1,1,TiePolicy.STRICT_V1))


class CompressionR0408Tests(unittest.TestCase):
    def test_both_strategies_exact_prior_rise(self):
        for strategy in Strategy:
            row,safe=run(data(),plan(),strategy=strategy)
            route,proof=row.private_preview.assessments[0]
            self.assertIs(route.selected_frame,Timeframe.D1)
            self.assertIs(proof.state,B6State387.MATCH)
            self.assertEqual(proof.reason,"PRIOR_D1_RISE_AND_COMPRESSION_UPPER_PIVOT_ONLY")
            self.assertEqual(safe["phases"][0]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_opposite_trend_keeps_independent_compression(self):
        _,safe=run(data(-1),plan(-1))
        self.assertEqual(safe["phases"][0]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")
        self.assertEqual(safe["phases"][1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_late_conflicting_or_bad_pivot_blocks(self):
        for inputs in (data(late=True),data(conflict=True),data(higher=True)):
            _,safe=run(inputs,plan())
            self.assertEqual(safe["phases"][0]["ingredient_state"],"BLOCKED")
            self.assertEqual(safe["phases"][1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_missing_prefix_or_pivot_never_falls_back(self):
        for inputs,p in ((data(missing=True),plan(offset=0)),
                         (data(),replace(plan(),upper_pivot=None))):
            _,safe=run(inputs,p)
            self.assertEqual(safe["phases"][0]["ingredient_state"],"MISSING_INPUT")
            self.assertEqual(safe["phases"][1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_explicit_plan_validation_and_missing_pairs(self):
        p=plan()
        for bad in (replace(p.r0,lookback=True),{},replace(p.r0,tie_policy="STRICT_V1")):
            _,safe=run(data(),replace(p,r0=bad))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        _,safe=run(data(),replace(p,r0=replace(p.r0,high_indices=())))
        self.assertEqual(safe["phases"][0]["ingredient_state"],"BLOCKED")

    def test_legacy_and_redaction(self):
        _,safe=run(data(),replace(plan(),r0=None))
        self.assertEqual(safe["phases"][0]["ingredient_state"],"NOT_REQUESTED")
        row,safe=run(data(),plan())
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not p["phase_verified"] and not p["action_eligible"] for p in safe["phases"]))
        for secret in (data().instrument_id,"lookback","pivot_price","earlier_sma50"):
            self.assertNotIn(secret,json.dumps(safe))
