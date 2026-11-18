"""§205 source-locked 16-zone phase manifest + NEAR v0.3 math regression.

All numbers here are fictional Decimal arithmetic, NOT real market data
or calibrated parameters. No source approval, position, broker or signals.
"""
from dataclasses import replace
from decimal import Decimal
import re
import unittest

from swing_trading.contracts import DecisionStatus, Strategy, ZONE_IDS
from swing_trading.b5_phase_contract import (
    B5_PHASE_PREDICATE_REFS, B5_VARIANTS,
)
from swing_trading.zone_manifest_v03 import (
    BUY_POLICY, EXECUTION_STATUS, MANIFESTS, NEAR_SPEC_REVISION,
    PARAM_STATUS, PHASES, SELL_POLICY, SPEC_REVISION,
    NearArithmeticPreview, SourceLockedZoneManifest, UnverifiedPhaseReadiness,
    ZoneManifestDenied, inspect_near_zone_arithmetic, inspect_phase,
    source_registry_fingerprint,
)

D = Decimal


class LockedManifest205Tests(unittest.TestCase):
    def test_all_16_exact_phase_refs_locked_in_source_order(self):
        self.assertEqual(tuple(MANIFESTS), ZONE_IDS)
        self.assertEqual(len(MANIFESTS), 16)
        self.assertEqual(PHASES, ("R0", "R_C", "R_E", "R_F"))
        expected = {
            "B1": ("DECLINE_CONTEXT","SUPPORT_TEST","RECLAIM_OR_BOS_UP","D1_BOS_HL_VOLUME"),
            "B2": ("D1_UPTREND_SUPPORT","PULLBACK_NEAR_SUPPORT","M15_HL_RECLAIM","MICRO_PIVOT_BREAK"),
            "B3": ("CAUSAL_RANGE","NEAR_LOWER_BOUNDARY","FALSE_BREAK_RECLAIM_OR_BOS","H1_D1_RECLAIM"),
            "B4": ("CAUSAL_BULLISH_TRANSITION","FIRST_POST_EVENT_PULLBACK","M15_HL_RECLAIM","FIRST_HL_MICRO_BREAK"),
            "B5": ("PRIOR_BREAKOUT_EVENT","EXACT_PIVOT_RETEST","M15_RECLAIM_OR_FAILED_BREAK","RETEST_SUPPORT_BREAK"),
            "B6": ("UPTREND_OR_BASE","TWO_CONTRACTIONS_OR_COMPRESSION","M15_UPPER_PIVOT_APPROACH","HIGHER_TF_BREAKOUT_VOLUME"),
            "B7": ("D1_DOWNTREND_CONTEXT","SUPPORT_ATR_STRETCH","M15_RECLAIM_OR_CHOCH","MICRO_HIGH_BREAK_RISK"),
            "B8": ("BASE_RESISTANCE_RS","NEAR_PIVOT","M15_PIVOT_CROSS","HIGHER_TF_BREAKOUT_RS_VOLUME"),
            "S1": ("LONG_UPTREND_RESISTANCE","DISTRIBUTION_CONTEXT","FAILED_BREAK_OR_CHOCH_DOWN","D1_BOS_DOWN_VOLUME"),
            "S2": ("D1_DOWNTREND_RESISTANCE","RALLY_NEAR_RESISTANCE","M15_REJECTION_LH","MICRO_LOW_BREAK"),
            "S3": ("D1_UPTREND_RESISTANCE_OR_TP","NEAR_TARGET_EXTENSION","MICRO_CHOCH_OR_TP","MICRO_BREAK_OR_VERIFIED_TP"),
            "S4": ("CAUSAL_D1_RANGE","UPPER_BOUNDARY_REJECTION","FALSE_BREAK_OR_BOS_DOWN","D1_H1_RANGE_REENTRY"),
            "S5": ("PRIOR_BEARISH_TRANSITION","FIRST_FAILED_RALLY","M15_LH_REJECTION","FIRST_LH_LOW_BREAK"),
            "S6": ("PRIOR_BREAKOUT_EVENT","BREAKOUT_FAILURE_WINDOW","M15_CLOSE_BELOW_PIVOT","H1_D1_PIVOT_FAILURE"),
            "S7": ("PRIOR_BREAKDOWN_EVENT","SUPPORT_RETEST_FROM_BELOW","M15_FAILED_RECLAIM","H1_D1_CONTINUATION"),
            "S8": ("CAUSAL_RETURN_VOL_PERCENTILES","ACCELERATION_EXHAUSTION","M15_MICRO_REVERSAL","HIGHER_TF_REVERSAL_VOLUME"),
        }
        self.assertEqual(set(expected), set(MANIFESTS))
        abbreviations=("R0","RC","RE","RF")
        for zone, m in MANIFESTS.items():
            self.assertEqual(m.zone_id,zone)
            self.assertEqual(m.rule_version,f"{zone}/PRECODE_v0.3")
            self.assertEqual(m.spec_revision,SPEC_REVISION)
            self.assertEqual(
                m.phase_predicates,tuple(
                    f"{zone}.{phase}.{suffix}"
                    for phase,suffix in zip(abbreviations,expected[zone])
                ),
            )
            self.assertEqual(m.parameter_status,PARAM_STATUS)
            self.assertEqual(m.predicate_executable_status,EXECUTION_STATUS)
            self.assertFalse(m.eligible_for_confirmed_action)
            self.assertEqual(m.evaluation_strategies,
                             (Strategy.SHORT,Strategy.SWING))
            self.assertEqual(
                m.strategy_action_policy,
                BUY_POLICY if zone.startswith("B") else SELL_POLICY
            )

    def test_variant_set_from_original_document_with_no_implicit_fallback(self):
        expected={
            "B1":("E_RECLAIM","E_BOS_UP","F_MAJOR_REVERSAL_PENDING"),
            "B2":("BASE",),
            "B3":("E_FALSE_BREAK","E_BOS_UP"),
            "B4":("BASE",),
            "B5":("E_RECLAIM","E_FAILED_BREAK"),
            "B6":("C_TWO_CONTRACTIONS","C_COMPRESSION"),
            "B7":("E_RECLAIM","E_CHOCH"),
            "B8":("BASE","INTRADAY_RVOL_TOD_PENDING"),
            "S1":("E_FAILED_BREAK","E_CHOCH_DOWN","F_MAJOR_CYCLE_TOP_PENDING"),
            "S2":("BASE",),
            "S3":("E_MICRO_CHOCH","E_TP","F_MICRO_BREAK","F_TP"),
            "S4":("E_FALSE_BREAK","E_BOS_DOWN"),
            "S5":("BASE",),
            "S6":("BASE",),
            "S7":("F_MICRO_BREAK","F_CONTINUATION"),
            "S8":("BASE",),
        }
        for zone, variants in expected.items():
            self.assertEqual(
                MANIFESTS[zone].variants,
                tuple(f"{zone}/{suffix}" for suffix in variants),
            )
        self.assertEqual(set(MANIFESTS["B5"].variants),B5_VARIANTS)

    def test_upstream_b5_phase_registry_is_identical(self):
        self.assertEqual(
            MANIFESTS["B5"].phase_predicates,
            B5_PHASE_PREDICATE_REFS,
        )

    def test_both_strategies_all_variants_each_four_phases_are_nontrading(self):
        count=0
        for zone,m in MANIFESTS.items():
            for strategy in (Strategy.SHORT,Strategy.SWING):
                for variant_id in m.variants:
                    for phase in PHASES:
                        r=inspect_phase(zone,strategy=strategy,
                                        variant_id=variant_id,phase=phase)
                        self.assertEqual(r.predicate_ref,m.predicate_for(phase))
                        self.assertEqual(r.reason,EXECUTION_STATUS)
                        self.assertIs(r.status,DecisionStatus.UNVERIFIED)
                        self.assertFalse(r.executable)
                        self.assertFalse(r.action_eligible)
                        count+=1
        self.assertGreater(count,128)

    def test_cannot_infer_sell_action_without_position_or_buy_approval(self):
        for zone in ZONE_IDS:
            m=MANIFESTS[zone]
            self.assertEqual(m.strategy_action_policy,
                             BUY_POLICY if zone[0]=="B" else SELL_POLICY)
            self.assertFalse(m.eligible_for_confirmed_action)

    def test_unknown_variant_phase_strategy_or_zone_denied(self):
        cases=(
            ("B5",Strategy.SHORT,"B5/E_NOT_IN_SOURCE","R0"),
            ("B5",Strategy.SHORT,"B5/E_RECLAIM","R_X"),
            ("S1",Strategy.SHORT,"B5/E_RECLAIM","R0"),
            ("B5","SHORT","B5/E_RECLAIM","R0"),
            ("X5",Strategy.SHORT,"B5/E_RECLAIM","R0"),
            ("B5",Strategy.SHORT,"B5/E_RECLAIM",None),
        )
        for zone,strategy,variant,phase in cases:
            with self.subTest(zone=zone,variant=variant),self.assertRaises(
                ZoneManifestDenied,
            ):
                inspect_phase(zone,strategy=strategy,
                              variant_id=variant,phase=phase)

    def test_manifest_is_immutable_mapping_and_rejects_forged_approval(self):
        with self.assertRaises(TypeError):
            MANIFESTS["B1"] = MANIFESTS["B5"]
        with self.assertRaises(ZoneManifestDenied):
            replace(MANIFESTS["B5"],eligible_for_confirmed_action=True)
        with self.assertRaises(ZoneManifestDenied):
            replace(MANIFESTS["S6"],strategy_action_policy=BUY_POLICY)
        with self.assertRaises(ZoneManifestDenied):
            replace(MANIFESTS["B8"],parameter_status="APPROVED")
        with self.assertRaises(ZoneManifestDenied):
            replace(MANIFESTS["B4"],predicate_executable_status="READY")

    def test_phase_dataclass_cannot_be_relabelled_detected(self):
        original=inspect_phase("S8",strategy=Strategy.SWING,
                               variant_id="S8/BASE",phase="R_F")
        for updates in (
            {"status":DecisionStatus.DETECTED},
            {"status":DecisionStatus.NOT_DETECTED},
            {"reason":"APPROVED"},
            {"action_eligible":True},
            {"executable":True},
            {"predicate_ref":"S8.RF.FAKE"},
        ):
            with self.subTest(updates=updates),self.assertRaises(
                ZoneManifestDenied
            ):
                replace(original,**updates)

    def test_registry_sha_is_deterministic_readonly_not_source_signature(self):
        a=source_registry_fingerprint()
        b=source_registry_fingerprint()
        self.assertEqual(a,b)
        self.assertRegex(a,r"^[0-9a-f]{64}$")
        self.assertNotEqual(a,"0"*64)


class LockedNearGeometry205Tests(unittest.TestCase):
    def test_inside_zone_distance_zero_with_unknown_candidate_threshold(self):
        r=inspect_near_zone_arithmetic(
            price=D("105"),zone_lower=D("100"),zone_upper=D("110"),
            atr_d1=D("5"),
        )
        self.assertEqual(r.distance,D("0"))
        self.assertEqual(r.normalized_by_atr,D("0"))
        self.assertIsNone(r.candidate_threshold_distance)
        self.assertIsNone(r.in_candidate_band)
        self.assertIs(r.status,DecisionStatus.UNVERIFIED)
        self.assertFalse(r.action_eligible)

    def test_left_and_right_outside_same_distance(self):
        def calc(p):
            return inspect_near_zone_arithmetic(
                price=D(p),zone_lower=D("100"),zone_upper=D("110"),
                atr_d1=D("5"),candidate_k_near=D("0.4"),
            )
        left,right=calc("98"),calc("112")
        for x in (left,right):
            self.assertEqual(x.distance,D("2"))
            self.assertEqual(x.normalized_by_atr,D("0.4"))
            self.assertEqual(x.candidate_threshold_distance,D("2.0"))
            self.assertIs(x.in_candidate_band,True)
            self.assertFalse(x.parameter_calibrated)
            self.assertFalse(x.source_qualified)
            self.assertIs(x.status,DecisionStatus.UNVERIFIED)

    def test_not_near_is_not_equivalent_to_not_detected(self):
        r=inspect_near_zone_arithmetic(
            price=D("96"),zone_lower=D("100"),zone_upper=D("110"),
            atr_d1=D("5"),candidate_k_near=D("0.4"),
        )
        self.assertEqual(r.distance,D("4"))
        self.assertIs(r.in_candidate_band,False)
        self.assertIs(r.status,DecisionStatus.UNVERIFIED)
        self.assertFalse(r.action_eligible)

    def test_candidate_k_zero_only_counts_in_range_but_not_a_signal(self):
        r=inspect_near_zone_arithmetic(
            price=D("100"),zone_lower=D("100"),zone_upper=D("110"),
            atr_d1=D("5"),candidate_k_near=D("0"),
        )
        self.assertEqual(r.candidate_threshold_distance,D("0"))
        self.assertIs(r.in_candidate_band,True)
        self.assertIs(r.status,DecisionStatus.UNVERIFIED)

    def test_canonical_math_is_distance_to_interval_not_to_zone_midpoint(self):
        r=inspect_near_zone_arithmetic(
            price=D("108"),zone_lower=D("100"),zone_upper=D("110"),
            atr_d1=D("5"),candidate_k_near=D("0.1"),
        )
        self.assertEqual(r.distance,D("0"))
        self.assertIs(r.in_candidate_band,True)

    def test_invalid_atr_unknown_zone_nonfinite_or_type_denied_not_false(self):
        baseline={"price":D("102"),"zone_lower":D("100"),
                  "zone_upper":D("110"),"atr_d1":D("5")}
        cases=(
            {"atr_d1":D("0")},{"atr_d1":D("-1")},
            {"atr_d1":None},{"atr_d1":float("nan")},
            {"zone_lower":D("111")},
            {"zone_lower":D("-1")},{"zone_upper":D("NaN")},
            {"price":D("-1")},{"price":True},{"price":"102"},
        )
        for updates in cases:
            with self.subTest(updates=repr(updates)),self.assertRaisesRegex(
                ZoneManifestDenied,"NEAR_INPUT_UNVERIFIED"
            ):
                inspect_near_zone_arithmetic(**dict(baseline,**updates))

    def test_invalid_candidate_k_denied_not_promoted(self):
        baseline={"price":D("102"),"zone_lower":D("100"),
                  "zone_upper":D("110"),"atr_d1":D("5")}
        for bad in (D("-0.001"),D("Infinity"),D("NaN"),True,
                    0.4,"0.40",float("inf")):
            with self.subTest(bad=repr(bad)),self.assertRaisesRegex(
                ZoneManifestDenied,"NEAR_CANDIDATE_K_INVALID"
            ):
                inspect_near_zone_arithmetic(**dict(
                    baseline,candidate_k_near=bad
                ))

    def test_no_automatic_p03_point_4_threshold_is_applied(self):
        r=inspect_near_zone_arithmetic(
            price=D("99"),zone_lower=D("100"),zone_upper=D("110"),
            atr_d1=D("5"),
        )
        self.assertEqual(r.distance,D("1"))
        self.assertIsNone(r.in_candidate_band)
        self.assertIsNone(r.candidate_threshold_distance)

    def test_cannot_relabel_arithmetic_preview_as_approved_rule(self):
        original=inspect_near_zone_arithmetic(
            price=D("111"),zone_lower=D("100"),zone_upper=D("110"),
            atr_d1=D("5"),candidate_k_near=D("0.4"),
        )
        for updates in (
            {"status":DecisionStatus.DETECTED},
            {"status":DecisionStatus.NOT_DETECTED},
            {"source_qualified":True},
            {"parameter_calibrated":True},
            {"action_eligible":True},
            {"specification":"custom"},
        ):
            with self.subTest(updates=updates),self.assertRaises(
                ZoneManifestDenied
            ):
                replace(original,**updates)

    def test_preview_instance_incomplete_or_fake_geometry_rejected(self):
        baseline=inspect_near_zone_arithmetic(
            price=D("100"),zone_lower=D("100"),zone_upper=D("110"),
            atr_d1=D("5"),candidate_k_near=D("0.4"),
        )
        for updates in (
            {"distance":D("-1")},
            {"normalized_by_atr":float("nan")},
            {"candidate_threshold_distance":None},
            {"in_candidate_band":None},
        ):
            with self.subTest(updates=repr(updates)),self.assertRaises(
                ZoneManifestDenied
            ):
                replace(baseline,**updates)


if __name__=="__main__":
    unittest.main()
