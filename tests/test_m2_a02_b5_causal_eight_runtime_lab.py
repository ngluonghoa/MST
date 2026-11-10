"""Executed third DISTINCT inherited A02 tranche: B5, causal, replay backtest.

Fabricated market data only; these tests call the ORIGINAL inherited V1
functions and existing fixture builders. Zero actual B5 signal, calibrated
parameter, trusted first-known feed, vendor licence, trained OOS backtest,
independent signer or broker action.
"""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import unittest

from scripts.m2_a02_b5_causal_eight_runtime_lab import (
    EIGHT, SCHEMA, execute_b5_causal_matrix,
)
from swing_trading.b5_feature_pack import (
    B5FeatureState, extract_b5_features,
)
from swing_trading.b5_phase_contract import (
    B5Ingredient, B5PhaseReadiness,
)
from swing_trading.b5_formula_geometry import (
    B5GeometryState, draft_for,
)
from swing_trading.b5_calibration_draft import (
    B5CalibrationAxis, B5CalibrationSlot,
    CalibrationDraftState, build_b5_calibration_grid,
)
from swing_trading.b5_temporal_split_audit import (
    SplitAuditState, audit_b5_temporal_split,
)
from swing_trading.causal_indicators import (
    IndicatorState, calculate_wilder_atr14, calculate_rvol_tf20,
)
from swing_trading.causal import CausalMarketEvent
from swing_trading.backtest import BacktestHarness, ExperimentManifest
from swing_trading.contracts import Strategy
from swing_trading.replay import ReplayClock
from swing_trading.source_quality import resolve_as_known
from test_b5_feature_pack import assessment, fixtures
from test_b5_phase_contract import (
    fixture_receipts, evaluate as phase_evaluate,
)
from test_b5_formula_geometry import run as geometry_run, anchors
from test_b5_temporal_split_audit import (
    inspect, plan, event, records,
)
from test_causal_indicators import AS_OF, d1, tf20
from test_backtest import FakeData, FakeRegistry, BrokenData, T0
from test_source_quality import m


class B5CausalThirdOriginalTrancheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = execute_b5_causal_matrix()

    def test_01_eight_distinct_unmodified_original_modules(self):
        self.assertEqual(self.report["executed_original_modules"],list(EIGHT))
        self.assertEqual(self.report["executed_distinct_count"],8)
        self.assertEqual(len(set(EIGHT)),8)

    def test_02_prior_16_plus_current_8_equals_24(self):
        self.assertEqual(self.report["prior_executed_distinct_count"],16)
        self.assertEqual(self.report["cumulative_executed_distinct_count"],24)
        self.assertEqual(self.report["still_unreviewed_runtime_modules"],39)

    def test_03_no_go_schema(self):
        self.assertEqual(self.report["schema"],SCHEMA)
        self.assertIn("PRODUCTION_NO_GO",self.report["status"])

    def test_04_all_security_checks_true(self):
        self.assertTrue(self.report["independent_business_safety_checks"])
        self.assertTrue(all(self.report["independent_business_safety_checks"].values()))

    def test_05_all_trading_owner_rights_false(self):
        for field in (
            "synthetic_B5_detector_approved","source_license_verified",
            "official_session_calendar_verified","OOS_performance_verified",
            "real_execution_backtest_performed","B5_thresholds_approved",
            "a03_full_v2_abi_behavior_accepted","external_signer_root_proven",
            "nonresettable_floor_proven","real_drive_cache_read_write",
            "production_release_authorized","trading_authorized",
        ):
            with self.subTest(field=field):
                self.assertFalse(self.report[field])

    def test_06_zero_owner_module_signatures(self):
        self.assertEqual(self.report["a02_owner_signed_module_count"],0)

    def test_07_four_strategy_variant_cases_present(self):
        self.assertEqual(len(self.report["strategy_variant_cases"]),4)
        self.assertEqual(
            {(x["strategy"],x["variant"]) for x in self.report["strategy_variant_cases"]},
            {(s.value,v) for s in Strategy
             for v in ("B5/E_RECLAIM","B5/E_FAILED_BREAK")},
        )

    def test_08_no_B5_variant_can_be_actionable(self):
        self.assertTrue(all(x["actionable"] is False for x in self.report["strategy_variant_cases"]))

    def test_09_before_M15_verified_B5_is_data_unverified(self):
        self.assertEqual(assessment(asof=m(49)).state,B5FeatureState.DATA_UNVERIFIED)

    def test_10_after_M15_verified_B5_only_uncalibrated_features(self):
        f=assessment(asof=m(60))
        self.assertEqual(f.state,B5FeatureState.EXTRACTED_UNCALIBRATED)
        self.assertFalse(f.actionable)
        self.assertIsNotNone(f.features)

    def test_11_b5_prior_pivot_late_known_blocks(self):
        p,a,b=fixtures()
        late=replace(p,first_known_time_utc=m(121))
        result=extract_b5_features(
            late,resolve_as_known(a.market_bar_key,(a,),m(120)),
            resolve_as_known(b.market_bar_key,(b,),m(120)),
            strategy=Strategy.SHORT,as_of_utc=m(120),
        )
        self.assertEqual(result.state,B5FeatureState.DATA_UNVERIFIED)

    def test_12_b5_wrong_instrument_source_identity_blocks(self):
        p,a,b=fixtures()
        wrong=replace(p,instrument_id="FAKEOTHER")
        result=extract_b5_features(
            wrong,resolve_as_known(a.market_bar_key,(a,),m(120)),
            resolve_as_known(b.market_bar_key,(b,),m(120)),
            strategy=Strategy.SWING,as_of_utc=m(120),
        )
        self.assertEqual(result.state,B5FeatureState.INPUT_BLOCKED)

    def test_13_phase_receipts_present_are_not_detected(self):
        x=phase_evaluate()
        self.assertEqual(x.state,B5PhaseReadiness.PRESENT_UNCALIBRATED)
        self.assertFalse(x.actionable)
        self.assertFalse(x.detector_approved)

    def test_14_missing_RF_VOLUME_receipt_is_not_no_signal(self):
        p,a,b,receipts=fixture_receipts()
        missing=tuple(x for x in receipts if x.ingredient is not B5Ingredient.RF_VOLUME)
        r=phase_evaluate(receipts=missing)
        self.assertEqual(r.state,B5PhaseReadiness.RECEIPTS_MISSING)
        self.assertEqual(r.missing,(B5Ingredient.RF_VOLUME,))

    def test_15_missing_all_phase_receipts_does_not_count_as_negative_detector(self):
        r=phase_evaluate(receipts=())
        self.assertEqual(r.state,B5PhaseReadiness.RECEIPTS_MISSING)
        self.assertFalse(r.actionable)

    def test_16_duplicate_B5_receipt_blocks(self):
        p,a,b,receipts=fixture_receipts()
        r=phase_evaluate(receipts=receipts+(receipts[0],))
        self.assertEqual(r.state,B5PhaseReadiness.RECEIPTS_UNVERIFIED)

    def test_17_geometry_reclaim_raw_arithmetic_not_a_trade(self):
        g=geometry_run()
        self.assertEqual(g.state,B5GeometryState.RAW_GEOMETRY_UNCALIBRATED)
        self.assertFalse(g.actionable)
        self.assertEqual(g.geometry.retest_recovery_from_low_atr,Decimal("0.7"))

    def test_18_geometry_failed_break_needs_independent_anchor(self):
        g=geometry_run(variant_id="B5/E_FAILED_BREAK")
        self.assertEqual(g.state,B5GeometryState.ANCHOR_BLOCKED)
        self.assertIsNone(g.geometry)

    def test_19_geometry_failed_break_with_anchor_still_uncalibrated(self):
        g=geometry_run(variant_id="B5/E_FAILED_BREAK",failed_break_anchor="use")
        self.assertEqual(g.state,B5GeometryState.RAW_GEOMETRY_UNCALIBRATED)
        self.assertFalse(g.detector_approved)
        self.assertFalse(g.actionable)

    def test_20_formula_draft_thresholds_unset(self):
        for s in Strategy:
            d=draft_for(s)
            self.assertIsNone(d.rc_window_sessions)
            self.assertIsNone(d.rc_tolerance_atr)
            self.assertFalse(d.risk_policy_approved)

    def test_21_calibration_grid_24_slots_four_protocols(self):
        g=build_b5_calibration_grid()
        self.assertEqual((len(g.slots),len(g.protocols)),(24,4))
        self.assertEqual(g.state,CalibrationDraftState.PRE_REGISTERED_UNCALIBRATED)
        self.assertFalse(g.actionable)

    def test_22_all_grid_parameters_none_and_unapproved(self):
        g=build_b5_calibration_grid()
        for item in g.slots:
            self.assertIsNone(item.candidate_values)
            self.assertIsNone(item.calibrated_value)
            self.assertFalse(item.parameter_approved)

    def test_23_numeric_calibration_injection_fails_closed(self):
        g=build_b5_calibration_grid()
        with self.assertRaises(ValueError):
            replace(g.slots[0],calibrated_value=Decimal("1"))

    def test_24_split_usable_structure_not_certified(self):
        r=inspect(plan())
        self.assertEqual(r.state,SplitAuditState.STRUCTURALLY_SEPARATED_UNCERTIFIED)
        self.assertFalse(r.source_licence_verified)
        self.assertFalse(r.trading_calendar_certified)
        self.assertFalse(r.actionable)

    def test_25_train_label_leak_to_validation_detected(self):
        p=plan()
        rows=(event(p,"train",18,24),)+records(p)[1:]
        r=inspect(p,rows)
        self.assertEqual(r.state,SplitAuditState.BLOCKED)
        self.assertIn(("train","TRAIN_LABEL_LEAKS_INTO_VALIDATION"),r.violations)

    def test_26_validation_label_leak_into_holdout_detected(self):
        p=plan()
        old=records(p)
        rows=(old[0],event(p,"validation",38,44),old[2])
        r=inspect(p,rows)
        self.assertEqual(r.state,SplitAuditState.BLOCKED)
        self.assertIn(("validation","VALIDATION_LABEL_LEAKS_INTO_HOLDOUT"),r.violations)

    def test_27_duplicate_fold_event_ids_blocked(self):
        p=plan()
        old=records(p)
        r=inspect(p,old+(old[0],))
        self.assertEqual(r.state,SplitAuditState.BLOCKED)
        self.assertIn(("train","DUPLICATE_EVENT_ID"),r.violations)

    def test_28_calibration_and_split_both_not_OOS(self):
        grid=build_b5_calibration_grid()
        clean=inspect(plan())
        self.assertFalse(grid.approved)
        self.assertFalse(clean.historical_backtest_run)

    def test_29_atr14_wilder_constant_range_exact_four(self):
        r=calculate_wilder_atr14(d1(),as_of_utc=AS_OF)
        self.assertEqual(r.value,Decimal("4"))
        self.assertEqual(r.state,IndicatorState.COMPUTED_UNCALIBRATED)
        self.assertFalse(r.actionable)

    def test_30_atr_insufficient_13_bars_blocked(self):
        r=calculate_wilder_atr14(d1(13),as_of_utc=AS_OF)
        self.assertEqual(r.state,IndicatorState.BLOCKED)
        self.assertIsNone(r.value)

    def test_31_rvol_exact_20_prior_is_one(self):
        target,prior=tf20()
        r=calculate_rvol_tf20(target,prior,as_of_utc=AS_OF)
        self.assertEqual(r.value,Decimal("1"))
        self.assertFalse(r.data_certified)
        self.assertFalse(r.actionable)

    def test_32_rvol_missing_one_comparator_blocks(self):
        target,prior=tf20()
        r=calculate_rvol_tf20(target,prior[:-1],as_of_utc=AS_OF)
        self.assertEqual(r.state,IndicatorState.BLOCKED)
        self.assertIsNone(r.value)

    def test_33_atr_and_rvol_not_detector_parameters(self):
        a=calculate_wilder_atr14(d1(),as_of_utc=AS_OF)
        target,prior=tf20()
        v=calculate_rvol_tf20(target,prior,as_of_utc=AS_OF)
        self.assertFalse(a.parameter_approved)
        self.assertFalse(v.parameter_approved)

    def test_34_backtest_future_revision_hidden_until_first_known(self):
        h=BacktestHarness(ReplayClock(T0),FakeData(),FakeRegistry())
        self.assertEqual([e.revision_id for e in h.visible_events()],["r1"])
        h.clock.advance_to(T0+timedelta(minutes=10))
        self.assertEqual([e.revision_id for e in h.visible_events()],["r1","r2"])

    def test_35_backtest_untyped_data_blocked(self):
        h=BacktestHarness(ReplayClock(T0),BrokenData(),FakeRegistry())
        with self.assertRaises(TypeError):
            h.visible_events()

    def test_36_causal_market_event_before_event_time_denied(self):
        with self.assertRaises(ValueError):
            CausalMarketEvent("a","r1",T0,T0-timedelta(seconds=1),{})

    def test_37_manifest_requires_source_snapshot(self):
        with self.assertRaises(ValueError):
            ExperimentManifest("id",T0,"","v1")

    def test_38_backtest_no_pnl_or_trade_activation(self):
        h=BacktestHarness(ReplayClock(T0),FakeData(),FakeRegistry())
        self.assertEqual(len(h.visible_events()),1)
        self.assertFalse(self.report["real_execution_backtest_performed"])
        self.assertFalse(self.report["trading_authorized"])

    def test_39_synthetic_report_deterministic(self):
        self.assertEqual(execute_b5_causal_matrix(),self.report)

    def test_40_receipt_never_contains_owner_approval(self):
        self.assertNotIn("owner_signature",self.report)
        self.assertEqual(self.report["a02_owner_signed_module_count"],0)


if __name__=="__main__":
    unittest.main()
