"""§376 exercise every existing structural ingredient through engine."""
from dataclasses import replace
import unittest

from swing_trading.contracts import DecisionStatus, Strategy, ZONE_IDS
from swing_trading.engine import (
    PREVIEW_ZONES, STRUCTURAL_PREVIEW_ZONES, BaselinePreviewRequest375,
    StructuralPhasePlan376, StructuralEnginePlan376, evaluate_baseline_preview,
)
from swing_trading.structural_phase_evidence import ROUTES
from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.market_data import Timeframe
import test_bound_structure370 as bound
import test_baseline_engine375 as previous
from decimal import Decimal as D


def plan(phase, tf):
    return StructuralPhasePlan376(phase, tf, 20 if tf is Timeframe.D1 else 5,
        17 if tf is Timeframe.D1 else 2, 1, 1, 0, 15, TiePolicy.STRICT_V1, D(".25"))


def run(key, tf, *, plans=None, strategy=Strategy.SHORT, inputs=None):
    p = StructuralEnginePlan376((plan(key[2],tf),) if plans is None else plans)
    req = BaselinePreviewRequest375(key[0],strategy,key[1],p)
    result = evaluate_baseline_preview(bound.model(key,tf) if inputs is None else inputs,
                                       requests=(req,))
    return previous.row(result,key[0],strategy)


class EngineStructural376Tests(unittest.TestCase):
    def test_all_18_routes_and_every_allowed_frame_exact_legacy_result(self):
        for key,(_,frames) in ROUTES.items():
            for tf in frames:
                for strategy in Strategy:
                    with self.subTest(key=key,tf=tf,strategy=strategy):
                        r=run(key,tf,strategy=strategy)
                        self.assertEqual(r.reason,"PREVIEW_EVALUATED_UNVERIFIED")
                        self.assertEqual(r.private_preview.status,DecisionStatus.UNVERIFIED)
                        expected=bound.run(key,tf,strategy=strategy)
                        self.assertEqual(r.private_preview.assessments,(expected,))
                        self.assertFalse(r.private_preview.action_eligible)
                        self.assertEqual(r.decision.evidence,())

    def test_combined_coverage_all_16_zones_not_detector_approval(self):
        self.assertEqual(set(PREVIEW_ZONES)|set(STRUCTURAL_PREVIEW_ZONES),set(ZONE_IDS))
        self.assertEqual(len(STRUCTURAL_PREVIEW_ZONES),15)
        key=("B1","B1/E_BOS_UP","R_E")
        m=bound.model(key,Timeframe.M15)
        result=evaluate_baseline_preview(m)
        self.assertEqual(len(result.rows),32)
        self.assertTrue(all(x.decision.status is DecisionStatus.UNVERIFIED for x in result.rows))
        self.assertEqual(sum(r["structural_preview_supported"] for r in result.safe_summary()["zones"]),30)

    def test_bad_route_or_phase_denied_without_fallback(self):
        key=("B1","B1/E_BOS_UP","R_E")
        p=plan("R_E",Timeframe.M15)
        for bad in ((),(p,p),(replace(p,phase="R0"),),
                    (replace(p,timeframe=Timeframe.H4),),
                    (replace(p,phase="R_F"),p),[p]):
            r=run(key,Timeframe.M15,plans=bad)
            self.assertEqual(r.reason,"PREVIEW_REJECTED_UNVERIFIED")
            self.assertIsNone(r.private_preview)

    def test_two_explicit_phases_share_variant_and_cutoff(self):
        key=("B1","B1/E_BOS_UP","R_E")
        m=bound.model(key,Timeframe.M15)
        # D1 exists for ATR but has only 15 rows: use a valid explicit
        # index within that bucket. Its mathematical cross need not match.
        p=replace(plan("R_F",Timeframe.D1),breakout_index=10,pivot_index=2)
        r=run(key,Timeframe.M15,inputs=m,plans=(plan("R_E",Timeframe.M15),p))
        self.assertEqual(r.reason,"PREVIEW_EVALUATED_UNVERIFIED")
        self.assertEqual([a.phase for a,_ in r.private_preview.assessments],["R_E","R_F"])
        self.assertFalse(r.private_preview.action_eligible)

    def test_unsupported_variant_not_silently_mapped(self):
        key=("S3","S3/F_TP","R_F")
        valid=("S3","S3/F_MICRO_BREAK","R_F")
        r=run(key,Timeframe.H1,inputs=bound.model(valid,Timeframe.H1))
        self.assertEqual(r.reason,"PREVIEW_REJECTED_UNVERIFIED")

    def test_no_implicit_switch_to_multi_phase_plan(self):
        key=("B2","B2/BASE","R_F")
        r=run(key,Timeframe.M15)
        self.assertIsNotNone(r.private_preview)
        self.assertEqual(len(r.private_preview.assessments),1)
        self.assertEqual(r.private_preview.assessments[0][0].phase,"R_F")
