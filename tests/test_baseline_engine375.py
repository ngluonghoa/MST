"""§375 engine-level explicit private dispatch, synthetic-only fixtures."""
from dataclasses import replace
import json
import unittest

from swing_trading.contracts import DecisionStatus, Strategy, ZONE_IDS
from swing_trading.engine import (
    PREVIEW_ZONES, BaselinePreviewRequest375, B5EnginePlan375, S7EnginePlan375,
    evaluate_baseline_preview, evaluate_unimplemented_zones,
)
from swing_trading.b2s2_swing_evidence215 import inspect_b2s2_baseline_preview
from swing_trading.b5_formula_geometry import inspect_b5_baseline_confirmation
from swing_trading.s7_retest_evidence import inspect_s7_baseline_preview
import test_b2s2_baseline_preview371 as b2
import test_b5_baseline_confirmation373 as b5
import test_s7_baseline_preview374 as s7


def request(zone, plan, strategy=Strategy.SHORT, variant=None):
    return BaselinePreviewRequest375(zone, strategy, variant or zone+"/BASE", plan)


def row(result, zone, strategy=Strategy.SHORT):
    return next(r for r in result.rows if (r.decision.zone_id, r.decision.strategy)==(zone,strategy))


class BaselineEngine375Tests(unittest.TestCase):
    def test_all_32_rows_order_and_legacy_interface_unchanged(self):
        m=b2.model("B2")
        r=evaluate_baseline_preview(m)
        self.assertEqual(tuple(x.decision for x in r.rows), tuple(
            d for strategy in Strategy for d in evaluate_unimplemented_zones(strategy,m.as_of_utc)))
        self.assertEqual([x.decision.zone_id for x in r.rows], list(ZONE_IDS)*2)
        self.assertEqual(sum(x.reason=="PREVIEW_NOT_CONFIGURED" for x in r.rows),8)
        self.assertEqual(sum(x.reason=="FULL_DETECTOR_SPEC_PENDING" for x in r.rows),24)
        self.assertEqual(r.decision,"NO_TRADE")
        self.assertEqual(r.publication_state,"INCOMPLETE_REPORT")

    def test_b2_and_s2_both_strategies_exact_existing_math(self):
        for zone in ("B2","S2"):
            m,p=b2.model(zone),b2.config()
            reqs=tuple(request(zone,p,strategy) for strategy in Strategy)
            result=evaluate_baseline_preview(m,requests=reqs)
            for strategy in Strategy:
                r=row(result,zone,strategy)
                self.assertEqual(r.private_preview,inspect_b2s2_baseline_preview(
                    m,zone_id=zone,strategy=strategy,plan=p))
                self.assertEqual(r.reason,"PREVIEW_EVALUATED_UNVERIFIED")
                self.assertEqual(r.decision.status,DecisionStatus.UNVERIFIED)
                self.assertEqual(r.decision.evidence,())

    def test_b5_variants_exact_bound_path(self):
        for variant in (b5.RECLAIM,b5.FAILED):
            m,p,f=b5.fixture(variant)
            cfg=B5EnginePlan375(p,f)
            r=row(evaluate_baseline_preview(m,requests=(request("B5",cfg,variant=variant),)),"B5")
            self.assertEqual(r.private_preview,inspect_b5_baseline_confirmation(
                m,strategy=Strategy.SHORT,variant_id=variant,retest_plan=p,rf_plan=f))
            self.assertEqual(r.reason,"PREVIEW_EVALUATED_UNVERIFIED")
            self.assertFalse(r.private_preview.action_eligible)

    def test_s7_micro_and_pending_continuation_are_distinct(self):
        m,o,f,_=s7.fixture()
        for variant,micro in ((s7.MICRO,f),(s7.CONT,None)):
            r=row(evaluate_baseline_preview(m,requests=(
                request("S7",S7EnginePlan375(o,micro),variant=variant),)),"S7")
            self.assertEqual(r.private_preview,inspect_s7_baseline_preview(
                m,strategy=Strategy.SHORT,variant_id=variant,origin_plan=o,micro_plan=micro))
            self.assertEqual(r.decision.status,DecisionStatus.UNVERIFIED)

    def test_bad_plan_isolated_and_not_negative_signal(self):
        m,p=b2.model("B2"),b2.config()
        r=evaluate_baseline_preview(m,requests=(
            request("B2",p),request("B2",object(),Strategy.SWING),
            request("S2",p,variant="B2/BASE")))
        self.assertIsNotNone(row(r,"B2").private_preview)
        for zone,strategy in (("B2",Strategy.SWING),("S2",Strategy.SHORT)):
            x=row(r,zone,strategy)
            self.assertEqual(x.reason,"PREVIEW_REJECTED_UNVERIFIED")
            self.assertIsNone(x.private_preview)
            self.assertEqual(x.decision.status,DecisionStatus.UNVERIFIED)
        self.assertTrue(all(x.decision.status is DecisionStatus.UNVERIFIED for x in r.rows))

    def test_invalid_batch_scope_duplicate_and_unsupported_are_rejected(self):
        m,p=b2.model("B2"),b2.config()
        q=request("B2",p)
        for bad in ([q],(q,q),(request("B1",p),),(replace(q,strategy="SHORT"),)):
            with self.assertRaises(ValueError):
                evaluate_baseline_preview(m,requests=bad)
        with self.assertRaises(TypeError):
            evaluate_baseline_preview({})

    def test_safe_summary_never_exports_input_rows_or_candidate_values(self):
        m,p=b2.model("B2"),b2.config()
        r=evaluate_baseline_preview(m,requests=(request("B2",p),))
        s=r.safe_summary()
        self.assertEqual(len(s["zones"]),32)
        self.assertFalse(s["source_released"])
        self.assertFalse(s["detector_parity_verified"])
        self.assertEqual(s["trade_orders"],0)
        wire=json.dumps(s)
        for forbidden in (m.instrument_id,"raw_digest_sha256","candidate_epsilon",
                          "candidate_k_near","MST_BOS_PREVIEW","private_preview"):
            self.assertNotIn(forbidden,wire)
