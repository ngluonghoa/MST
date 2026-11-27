"""§404 B6 compression same-pivot D1 RF fictional regressions."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_compression_breakout404 import CompressionD1RFPlan404
from swing_trading.b6_baseline_preview387 import B6State387
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import BaselineResolvedInputs
from test_b6_compression_early403 import fixture, plan, re
from test_b6_compression_rc396 import run
from test_causal_indicators import make_bar, snap


def data(*, price=D(113), prior=D(109), late=False, missing=False, **kwargs):
    original=fixture(**kwargs)
    rows=original.snapshots_for(Timeframe.D1)
    m15=original.snapshots_for(Timeframe.M15)
    start=rows[-1].market_bar_key.bar_start_utc
    before=make_bar(20,start=start+timedelta(days=1),open_price=prior,
                    close=prior,high=prior+1,low=prior-1)
    target=make_bar(21,start=start+timedelta(days=2),open_price=price,
                    close=price,high=max(D(114),price+1),low=price-1)
    if late:
        m15=m15[:-1]+(snap(replace(m15[-1].selected,verified_at_utc=target.bar_end_utc)),)
    d1=rows if missing else rows+(snap(before),snap(target))
    return BaselineResolvedInputs(original.instrument_id,original.exchange,original.as_of_utc,False,
        tuple((tf,d1 if tf is Timeframe.D1 else m15 if tf is Timeframe.M15 else bucket)
              for tf,bucket in original.buckets))


def config(index=21, eps=D("0.05")):
    return replace(plan(),rf=CompressionD1RFPlan404(index,eps))


def rf(row):
    return next(e for r,e in row.private_preview.assessments if r.phase=="R_F")


class CompressionD1RF404Tests(unittest.TestCase):
    def test_both_strategies_bound_closed_d1_cross(self):
        for strategy in Strategy:
            row,safe=run(data(),config(),strategy=strategy)
            route,proof=row.private_preview.assessments[-1]
            self.assertIs(route.selected_frame,Timeframe.D1)
            self.assertIs(proof.state,B6State387.MATCH)
            self.assertEqual(proof.reason,"COMPRESSION_SAME_PIVOT_D1_CROSS_ONLY")
            self.assertEqual(proof.volume_state,"D1_VOLUME_SPEC_PENDING")
            self.assertEqual(safe["phases"][-1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")
            self.assertFalse(proof.action_eligible)

    def test_wick_only_and_already_crossed_are_nonmatch(self):
        for inputs in (data(price=D(110)),data(prior=D(113))):
            row,safe=run(inputs,config())
            self.assertIs(rf(row).state,B6State387.NONMATCH)
            self.assertEqual(safe["phases"][-1]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_late_m15_and_far_approach_do_not_confirm(self):
        for inputs in (data(late=True),data(far=True),data(mixed=True),data(higher=True)):
            row,safe=run(inputs,config())
            self.assertIs(rf(row).state,B6State387.BLOCKED)
            self.assertEqual(rf(row).reason,"M15_APPROACH_NOT_AVAILABLE_BEFORE_D1_BREAKOUT")
            self.assertEqual(safe["phases"][-1]["ingredient_state"],"BLOCKED")
        row,_=run(data(late=True),config())
        self.assertTrue(re(row).approach)

    def test_missing_d1_or_explicit_early_plan(self):
        for inputs,p in ((data(missing=True),config()),(data(),replace(config(),early=None)),
                         (data(),replace(config(),upper_pivot=None))):
            row,safe=run(inputs,p)
            self.assertIs(rf(row).state,B6State387.MISSING)
            self.assertEqual(safe["phases"][-1]["ingredient_state"],"MISSING_INPUT")

    def test_invalid_plan_and_exact_base_order(self):
        for p in (config(index=True),config(index=20),config(eps=None),config(eps=D(-1))):
            _,safe=run(data(),p)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_old_early_only_and_redacted_summary(self):
        row,safe=run(data(),plan())
        self.assertEqual(safe["phases"][-1]["ingredient_state"],"NOT_REQUESTED")
        row,safe=run(data(),config())
        self.assertFalse(row.private_preview.safe_rf_volume_summary()["volume_approved"])
        self.assertFalse(row.private_preview.action_eligible)
        for secret in ("candidate_epsilon","113","pivot_price","breakout_index","boundary"):
            self.assertNotIn(secret,json.dumps(safe))
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
