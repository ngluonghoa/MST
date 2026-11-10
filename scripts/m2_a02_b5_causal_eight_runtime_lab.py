"""A02 third distinct original-V1 runtime tranche: B5 causal/backtest safety.

This engineering-only lab invokes eight REAL original inherited modules:
b5_feature_pack, b5_phase_contract, b5_formula_geometry,
b5_calibration_draft, b5_temporal_split_audit, causal_indicators, causal,
and backtest. It imports ONLY FABRICATED fixture-constructor helpers
from existing tests (PYTHONPATH=tests in hosted CI). No test helper replaces
or mocks the original V1 functions under evaluation.

A passing report is deliberately NOT a B5 detector, trained threshold,
historical backtest, exchange-calendar attestation, market-source license,
owner module signature, V2 parity or trade permission.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path

from swing_trading.backtest import BacktestHarness, ExperimentManifest
from swing_trading.b5_calibration_draft import (
    B5CalibrationAxis, CalibrationDraftState, build_b5_calibration_grid,
)
from swing_trading.b5_feature_pack import B5FeatureState
from swing_trading.b5_formula_geometry import B5GeometryState
from swing_trading.b5_phase_contract import (
    B5Ingredient, B5PhaseReadiness, B5_REQUIRED_INGREDIENTS,
)
from swing_trading.b5_temporal_split_audit import SplitAuditState
from swing_trading.causal import CausalMarketEvent
from swing_trading.causal_indicators import (
    IndicatorState, calculate_rvol_tf20, calculate_wilder_atr14,
)
from swing_trading.contracts import Strategy
from swing_trading.replay import ReplayClock

# REVIEW-ONLY TEST DATA CONSTRUCTORS, not source modules, not a provider.
from test_b5_feature_pack import assessment as feature_assessment
from test_b5_phase_contract import evaluate as phase_assessment, fixture_receipts
from test_b5_formula_geometry import run as geometry_assessment
from test_b5_temporal_split_audit import plan, records, event, inspect
from test_causal_indicators import AS_OF, d1, tf20
from test_backtest import FakeData, FakeRegistry, BrokenData, T0
from test_source_quality import m

SCHEMA = "mst.a02.original-v1-eight-b5-causal-runtime.no-approval.v1"
EIGHT = (
    "b5_feature_pack", "b5_phase_contract", "b5_formula_geometry",
    "b5_calibration_draft", "b5_temporal_split_audit",
    "causal_indicators", "causal", "backtest",
)
STRATEGIES = (Strategy.SHORT, Strategy.SWING)
VARIANTS = ("B5/E_RECLAIM", "B5/E_FAILED_BREAK")
UPSTREAM = "cd90c1babae8912db31490ad614fc2ad2f868042"
MAIN = "4048f91beaaa3410116d97e35896c8b688384e19"


def _require(predicate: bool, name: str):
    if not predicate:
        raise AssertionError(name)


def _deny(func, error: type[Exception], name: str):
    try:
        func()
    except error:
        return True
    raise AssertionError(name)


def execute_b5_causal_matrix() -> dict:
    checks: dict[str, bool] = {}
    # Execute actual inherited B5 feature/phase/geometry functions across
    # each of four strategy x variant branches, not just the registry.
    matrix = []
    for strategy in STRATEGIES:
        before = feature_assessment(asof=m(49), strategy=strategy)
        after = feature_assessment(asof=m(60), strategy=strategy)
        _require(before.state is B5FeatureState.DATA_UNVERIFIED
                 and before.features is None
                 and not before.actionable, "B5_LATE_SOURCE_LOOKAHEAD")
        _require(after.state is B5FeatureState.EXTRACTED_UNCALIBRATED
                 and after.features is not None
                 and not after.actionable, "B5_FEATURES_FALSE_TRADE")
        for variant in VARIANTS:
            phase = phase_assessment(strategy=strategy, variant_id=variant)
            geometry = geometry_assessment(
                strategy=strategy, variant_id=variant,
                failed_break_anchor="use",
            )
            _require(
                phase.state is B5PhaseReadiness.PRESENT_UNCALIBRATED
                and not phase.actionable and not phase.detector_approved
                and geometry.state is B5GeometryState.RAW_GEOMETRY_UNCALIBRATED
                and geometry.geometry is not None and not geometry.actionable
                and not geometry.detector_approved,
                "B5_COMPLETE_RECEIPT_OR_MATH_PROMOTED_TO_DETECTOR",
            )
            matrix.append({
                "strategy": strategy.value, "variant": variant,
                "early": before.state.value, "later": after.state.value,
                "phase": phase.state.value, "geometry": geometry.state.value,
                "actionable": False,
            })
    checks["four_strategies_variants_raw_geometry_never_signal"] = (
        len(matrix) == 4 and all(not row["actionable"] for row in matrix)
    )
    checks["late_verified_M15_bar_blocks_early_B5"] = all(
        row["early"] == B5FeatureState.DATA_UNVERIFIED.value for row in matrix
    )
    p,a,b,receipts = fixture_receipts()
    missing = tuple(r for r in receipts if r.ingredient is not B5Ingredient.RF_VOLUME)
    missing_result = phase_assessment(receipts=missing)
    _require(
        missing_result.state is B5PhaseReadiness.RECEIPTS_MISSING
        and missing_result.missing == (B5Ingredient.RF_VOLUME,)
        and not missing_result.actionable,
        "MISSING_VOLUME_RECEIPT_FALSIFIED_DETECTOR",
    )
    checks["missing_B5_R_F_volume_remains_missing_not_negative"] = True

    # A raw failed-break geometry is not permitted without a known prior bar.
    no_failed = geometry_assessment(variant_id="B5/E_FAILED_BREAK")
    _require(no_failed.state is B5GeometryState.ANCHOR_BLOCKED
             and no_failed.geometry is None and not no_failed.actionable,
             "FAILED_BREAK_BRANCH_REQUIRES_KNOWN_PRIOR_ANCHOR")
    checks["failed_break_requires_prior_closed_anchor"] = True

    # Actual calibration draft: independent strategy+variant slots, no numeric
    # candidate, approved threshold, trained model, or policy release.
    grid = build_b5_calibration_grid()
    _require(
        len(grid.slots) == 24 and len(grid.protocols) == 4
        and grid.state is CalibrationDraftState.PRE_REGISTERED_UNCALIBRATED
        and not grid.approved and not grid.executable and not grid.actionable
        and len({(x.strategy,x.variant_id,x.axis) for x in grid.slots}) == 24
        and all(x.candidate_values is None and x.calibrated_value is None
                and not x.parameter_approved for x in grid.slots)
        and len(B5CalibrationAxis) == 6,
        "B5_CALIBRATION_GRID_FALSELY_APPROVED",
    )
    checks["two_strategies_two_variants_six_parameters_all_unapproved"] = True

    # Actual leakage-safe synthetic split checker: three folds segregated
    conditionally, then a train label that crosses validation MUST block.
    split = plan()
    clean = inspect(split)
    leaked_records = (event(split,"train",18,24),) + records(split)[1:]
    leaked = inspect(split, leaked_records)
    _require(
        clean.state is SplitAuditState.STRUCTURALLY_SEPARATED_UNCERTIFIED
        and (clean.train_count,clean.validation_count,clean.holdout_count)
            == (1,1,1)
        and not clean.actionable
        and leaked.state is SplitAuditState.BLOCKED
        and ("train","TRAIN_LABEL_LEAKS_INTO_VALIDATION") in leaked.violations
        and not leaked.actionable,
        "B5_SPLIT_LABEL_LEAKAGE_NOT_BLOCKED",
    )
    checks["train_validation_holdout_purge_and_leak_rejection"] = True
    checks["official_exchange_calendar_not_attested"] = (
        not clean.trading_calendar_certified and not clean.source_licence_verified
        and not clean.historical_backtest_run and not clean.threshold_approved
    )

    # Actual Wilder ATR14 and RVOL_TF20 calculations use source-qualified
    # fabricated closes/volume. Numeric success cannot authorize a signal.
    atr = calculate_wilder_atr14(d1(), as_of_utc=AS_OF)
    short_atr = calculate_wilder_atr14(d1(13), as_of_utc=AS_OF)
    target, history = tf20()
    rvol = calculate_rvol_tf20(target, history, as_of_utc=AS_OF)
    rvol_missing = calculate_rvol_tf20(target, history[:-1], as_of_utc=AS_OF)
    _require(
        atr.state is IndicatorState.COMPUTED_UNCALIBRATED
        and atr.value == Decimal("4")
        and atr.used_bar_count == 15
        and not atr.actionable and not atr.data_certified
        and short_atr.state is IndicatorState.BLOCKED
        and short_atr.value is None
        and rvol.state is IndicatorState.COMPUTED_UNCALIBRATED
        and rvol.value == Decimal("1")
        and rvol.used_bar_count == 20
        and not rvol.actionable and not rvol.data_certified
        and rvol_missing.state is IndicatorState.BLOCKED
        and rvol_missing.value is None,
        "CAUSAL_ATR_RVOL_MISSING_HISTORY_OR_FALSE_AUTHORIZATION",
    )
    checks["wilder_atr14_exact_four_unapproved"] = True
    checks["rvol_tf20_one_and_missing_history_blocked"] = True

    # ACTUAL CausalMarketEvent + BacktestHarness: revision first known at T+10
    # must not be visible at T0 even if a caller advertises it early.
    harness = BacktestHarness(ReplayClock(T0), FakeData(), FakeRegistry())
    v0 = tuple(e.revision_id for e in harness.visible_events())
    harness.clock.advance_to(T0 + timedelta(minutes=10))
    v10 = tuple(e.revision_id for e in harness.visible_events())
    _require(
        v0 == ("r1",) and v10 == ("r1","r2"),
        "BACKTEST_REPLAY_VISIBLE_FUTURE_REVISION",
    )
    checks["causal_event_revisions_visible_only_at_first_known"] = True
    checks["untyped_backtest_source_rejected"] = _deny(
        lambda: BacktestHarness(ReplayClock(T0), BrokenData(),
                                FakeRegistry()).visible_events(),
        TypeError, "UNTYPED_BACKTEST_EVENT_NOT_REJECTED",
    )
    checks["causal_event_before_event_time_rejected"] = _deny(
        lambda: CausalMarketEvent("case","r1",T0,
                                  T0-timedelta(seconds=1),{}),
        ValueError, "EVENT_FIRST_KNOWN_BEFORE_EVENT_TIME",
    )
    checks["unpinned_experiment_manifest_rejected"] = _deny(
        lambda: ExperimentManifest("fixture",T0,"","v1"),
        ValueError, "BACKTEST_MANIFEST_WITHOUT_SOURCE_PIN",
    )
    _require(all(checks.values()), "B5_CAUSAL_CROSS_MODULE_CASES_NOT_ALL_PASS")
    return {
        "schema": SCHEMA,
        "status": "THIRD_EIGHT_REAL_V1_B5_CAUSAL_RUNTIME_CASES_PASS_OWNER_AND_PRODUCTION_NO_GO",
        "original_upstream_sha": UPSTREAM,
        "protected_main_sha": MAIN,
        "executed_original_modules": list(EIGHT),
        "executed_distinct_count": len(EIGHT),
        "prior_executed_distinct_count": 16,
        "cumulative_executed_distinct_count": 24,
        "still_unreviewed_runtime_modules": 39,
        "strategy_variant_cases": matrix,
        "calibration_parameter_slots": len(grid.slots),
        "validation_protocols": len(grid.protocols),
        "causal_replay_visible_revisions_before": list(v0),
        "causal_replay_visible_revisions_after": list(v10),
        "independent_business_safety_checks": checks,
        "new_business_safety_checks": len(checks),
        "synthetic_B5_detector_approved": False,
        "source_license_verified": False,
        "official_session_calendar_verified": False,
        "OOS_performance_verified": False,
        "real_execution_backtest_performed": False,
        "B5_thresholds_approved": False,
        "a02_owner_signed_module_count": 0,
        "a03_full_v2_abi_behavior_accepted": False,
        "external_signer_root_proven": False,
        "nonresettable_floor_proven": False,
        "real_drive_cache_read_write": False,
        "production_release_authorized": False,
        "trading_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    result = execute_b5_causal_matrix()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, sort_keys=True, indent=2)+"\n",
                            encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k not in
                      ("strategy_variant_cases","independent_business_safety_checks")},
                     sort_keys=True))


if __name__ == "__main__":
    main()
