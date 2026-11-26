"""§393 B6 bound H1 RF crossing, fictional inputs only."""
from dataclasses import replace
from decimal import Decimal as D
import json
import unittest

from swing_trading.b6_baseline_preview387 import B6H1RFPlan393, B6State387
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import BaselineResolvedInputs
from test_b6_baseline_preview387 import config, evaluate
from test_b6_bound_rf388 import inputs, cfg
from test_causal_cross_tf_candidate392 import h1_pair
from test_causal_indicators import snap


def model(*, h1=None, missing=False, late=False, far=False):
    base=inputs(far=far)
    pair=() if missing else h1_pair() if h1 is None else h1
    m15=base.snapshots_for(Timeframe.M15)
    if late:
        m15=m15[:-1]+(snap(replace(m15[-1].selected,verified_at_utc=pair[-1].selected.bar_end_utc)),)
    return BaselineResolvedInputs(base.instrument_id,base.exchange,base.as_of_utc,False,
        tuple((tf,pair if tf is Timeframe.H1 else m15 if tf is Timeframe.M15 else rows)
              for tf,rows in base.buckets))


def h1_config(index=1, eps=D("0.05")):
    return replace(config(),rf=B6H1RFPlan393(index,eps))


class B6H1RF393Tests(unittest.TestCase):
    def test_both_strategies_same_pivot_h1_route_no_volume_reuse(self):
        for strategy in Strategy:
            row,safe=evaluate(model(),strategy=strategy,cfg=h1_config())
            route,rf=row.private_preview.assessments[-1]
            self.assertIs(route.selected_frame,Timeframe.H1)
            self.assertIs(rf.state,B6State387.MATCH)
            self.assertEqual(rf.reason,"SAME_PIVOT_H1_CROSS_ONLY_VOLUME_RISK_PENDING")
            self.assertEqual(rf.volume_state,"H1_VOLUME_SPEC_PENDING")
            self.assertIsNone(rf.rvol)
            self.assertEqual(safe["phases"][-1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")
            self.assertFalse(rf.action_eligible)

    def test_h1_missing_no_d1_fallback_even_if_d1_crosses(self):
        row,safe=evaluate(model(missing=True),cfg=h1_config())
        self.assertEqual(safe["phases"][-1]["ingredient_state"],"MISSING_INPUT")
        self.assertEqual(row.private_preview.assessments[-1][1].volume_state,"H1_VOLUME_SPEC_PENDING")
        _,d1=evaluate(model(missing=True),cfg=cfg())
        self.assertEqual(d1["phases"][-1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_wick_or_already_crossed_nonmatch(self):
        for pair in (h1_pair(price=D(110)),h1_pair(prior=D(113))):
            row,safe=evaluate(model(h1=pair),cfg=h1_config())
            self.assertIs(row.private_preview.assessments[-1][1].state,B6State387.NONMATCH)
            self.assertEqual(safe["phases"][-1]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_late_or_far_approach_blocks_h1(self):
        for data in (model(late=True),model(far=True)):
            _,safe=evaluate(data,cfg=h1_config())
            self.assertEqual(safe["phases"][-1]["ingredient_state"],"BLOCKED")
            self.assertEqual(safe["phases"][1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_explicit_h1_config_and_missing_target(self):
        for bad in (h1_config(index=True),h1_config(index=0),h1_config(eps=None)):
            _,safe=evaluate(model(),cfg=bad)
            self.assertTrue(all(p["ingredient_state"]=="CONFIG_REJECTED" for p in safe["phases"]))
        _,safe=evaluate(model(),cfg=h1_config(index=2))
        self.assertEqual(safe["phases"][-1]["ingredient_state"],"MISSING_INPUT")

    def test_source_mismatch_redaction_and_old_d1_route(self):
        row,safe=evaluate(model(h1=h1_pair(mixed=True)),cfg=h1_config())
        self.assertEqual(safe["phases"][-1]["ingredient_state"],"BLOCKED")
        self.assertIn("SOURCE_BASIS_MISMATCH",row.private_preview.assessments[-1][1].reason)
        self.assertFalse(row.private_preview.safe_rf_volume_summary()["volume_approved"])
        _,old=evaluate(model(),cfg=cfg())
        self.assertEqual(old["phases"][-1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")
        for secret in (model().instrument_id,"fixture-h1-stream","candidate_epsilon","pivot_price","113"):
            self.assertNotIn(secret,json.dumps(safe))
        self.assertTrue(all(not p["phase_verified"] and not p["action_eligible"] for p in safe["phases"]))
