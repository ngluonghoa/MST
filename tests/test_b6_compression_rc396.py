"""§396 exact same-input B6 compression R_C, fictional data."""
from dataclasses import replace
from decimal import Decimal as D
import json
import unittest

from swing_trading.b6_baseline_preview387 import B6CompressionPlan396, B6State387
from swing_trading.causal_compression_candidate395 import AtrPercentilePlan395
from swing_trading.contracts import Strategy
from swing_trading.engine import BaselinePreviewRequest375, evaluate_baseline_preview
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import BASELINE_CORE_TF, BaselineResolvedInputs
from test_causal_compression_candidate395 import fixture
from test_causal_indicators import AS_OF, snap
from test_b6_baseline_preview387 import config


def model(rows=None):
    bars=fixture() if rows is None else rows
    k=fixture()[0].market_bar_key
    return BaselineResolvedInputs(k.instrument_id,k.exchange,AS_OF,False,
        tuple((tf,bars if tf is Timeframe.D1 else ()) for tf in BASELINE_CORE_TF))


def plan(index=17):
    return B6CompressionPlan396(index,AtrPercentilePlan395(3,D("0.2")))


def run(data=None, p=None, *, strategy=Strategy.SHORT, variant="B6/C_COMPRESSION"):
    inputs=model() if data is None else data
    req=BaselinePreviewRequest375("B6",strategy,variant,plan() if p is None else p)
    result=evaluate_baseline_preview(inputs,requests=(req,))
    row=next(r for r in result.rows if r.decision.zone_id=="B6" and r.decision.strategy is strategy)
    safe=next(r for r in result.safe_phase_summary()["zones"]
              if r["zone_id"]=="B6" and r["strategy"]==strategy.value)
    return row,safe


class B6Compression396Tests(unittest.TestCase):
    def test_both_strategies_only_rc(self):
        for strategy in Strategy:
            row,safe=run(strategy=strategy)
            route,proof=row.private_preview.assessments[0]
            self.assertEqual(route.variant_id,"B6/C_COMPRESSION")
            self.assertIs(proof.state,B6State387.MATCH)
            self.assertTrue(proof.compression.at_or_below)
            self.assertEqual([p["ingredient_state"] for p in safe["phases"]],
                             ["NOT_REQUESTED","GEOMETRY_MATCH_ONLY","NOT_REQUESTED","NOT_REQUESTED"])
            self.assertEqual(safe["status"],"UNVERIFIED")

    def test_nonmatch_no_contraction_fallback(self):
        row,safe=run(model(fixture(D(10))))
        self.assertIs(row.private_preview.assessments[0][1].state,B6State387.NONMATCH)
        self.assertEqual(safe["phases"][1]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_missing_exact_target_or_reference(self):
        for data,p in ((model(()),plan()),(model(),plan(16)),(model(),plan(18))):
            row,safe=run(data,p)
            self.assertEqual(safe["phases"][1]["ingredient_state"],"MISSING_INPUT")

    def test_late_prior_blocks_and_invalid_config_isolated(self):
        rows=list(fixture())
        rows[-2]=snap(replace(rows[-2].selected,verified_at_utc=rows[-1].selected.bar_end_utc))
        _,safe=run(model(tuple(rows)))
        self.assertEqual(safe["phases"][1]["ingredient_state"],"BLOCKED")
        for p in (plan(True),replace(plan(),percentile=AtrPercentilePlan395(3,D(0)))):
            _,safe=run(model(),p)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_exact_variant_and_wrong_plan_rejected(self):
        for p,variant in ((plan(),"B6/C_TWO_CONTRACTIONS"),(config(),"B6/C_COMPRESSION")):
            _,safe=run(p=p,variant=variant)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        req=BaselinePreviewRequest375("B2",Strategy.SHORT,"B2/E_RECLAIM",plan())
        with self.assertRaises(ValueError):
            evaluate_baseline_preview(model(),requests=(req,))

    def test_redacted_no_authority(self):
        row,safe=run()
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        self.assertEqual(row.private_preview.safe_rf_volume_summary()["volume_state"],"NOT_REQUESTED")
        for forbidden in (model().instrument_id,"quantile","target_atr_percent","reference_count"):
            self.assertNotIn(forbidden,json.dumps(safe))
