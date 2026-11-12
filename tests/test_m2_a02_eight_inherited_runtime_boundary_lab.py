"""Executed real original V1 behavior, not ABI-only static inspection.

Fixture-only: all 8 inherited high-impact V1 modules are actually invoked,
including legacy permissive holes retained for ABI compatibility.
"""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
import unittest

from scripts.m2_a02_eight_inherited_runtime_boundary_lab import (
    EIGHT, MOMENTS, SCHEMA, evaluate_behavior_matrix, expected_unverified_zone_decisions,
)
from scripts.m2_a02_market_cache_execution_boundary_lab import build_candles, minute
from scripts.m2_a02_incremental_cache_oracle_lab import (
    bar, independent_ema_atr_oracle,
)
from swing_trading.contracts import Evidence, SignalDecision, DecisionStatus, Strategy, ZONE_IDS
from swing_trading.engine import evaluate_unimplemented_zones
from swing_trading.replay import ReplayClock, require_utc
from swing_trading.market_data import BarClosure, Quality, PriceBasis
from swing_trading.source_quality import QualityState
from swing_trading.cache_fetch_planner import (
    SourceCapability, SourceCursor, RefreshAction, plan_refresh,
)
from swing_trading.vn_backtest_execution_fixture import (
    VNBarVerdict, inspect_fixture_vn_long_exit_bar, require_vn_backtest_release,
)


class EightInheritedRuntimeMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = evaluate_behavior_matrix()
        cls.s = {row["minute"]: row for row in cls.receipt["snapshots"]}

    def test_all_eight_original_modules_exercised_not_v2(self):
        self.assertEqual(self.receipt["actual_module_count"], 8)
        self.assertEqual(self.receipt["actual_modules_exercised"], list(EIGHT))
        self.assertTrue(all(not name.startswith("v2_") for name in EIGHT))

    def test_schema_is_legacy_behavior_and_explicit_no_go(self):
        self.assertEqual(self.receipt["schema"], SCHEMA)
        self.assertIn("SYNTHETIC_GAPS_EXPLICIT_NO_GO", self.receipt["status"])

    def test_six_asof_snapshots_are_exact(self):
        self.assertEqual(self.receipt["six_asof_minutes"], list(MOMENTS))
        self.assertEqual(len(self.receipt["snapshots"]), 6)

    def test_six_times_two_strategies_sixteen_zone_decisions(self):
        self.assertEqual(self.receipt["six_snapshots_two_strategies_sixteen_zones"], 192)

    def test_both_original_strategies_present_at_every_time(self):
        for s in self.s.values():
            self.assertEqual([x["strategy"] for x in s["strategies"]],
                             [Strategy.SHORT.value, Strategy.SWING.value])

    def test_all_zone_decisions_keep_original_order(self):
        for s in self.s.values():
            for strat in s["strategies"]:
                self.assertEqual(strat["zones"], list(ZONE_IDS))
                self.assertEqual(strat["count"],16)

    def test_all_original_evaluators_keep_safe_unverified(self):
        for s in self.s.values():
            for strat in s["strategies"]:
                self.assertTrue(strat["all_unverified"])
                self.assertTrue(strat["all_evidence_empty"])

    def test_legacy_known_timestamp_boundary(self):
        self.assertEqual([self.s[x]["first_known_revision_visible"] for x in MOMENTS],
                         [False, True, True, True, True, True])

    def test_rich_verified_timestamp_boundary(self):
        self.assertEqual([self.s[x]["verification_timestamp_reached"] for x in MOMENTS],
                         [False, False, False, False, True, True])

    def test_v1_quality_necessary_is_not_v12_full_source_prerequisite(self):
        self.assertEqual([self.s[x]["v1_simple_eligible"] for x in MOMENTS],
                         [False, True, True, True, True, True])
        self.assertEqual([self.s[x]["v12_source_prerequisites"] for x in MOMENTS],
                         [False, False, False, False, True, True])

    def test_candle_quality_true_never_implies_trade(self):
        for s in self.s.values():
            self.assertTrue(s["not_full_trade_authorization"])
            self.assertTrue(all(x["all_unverified"] for x in s["strategies"]))

    def test_verified_zero_volume_is_known_not_missing(self):
        self.assertTrue(self.receipt["quality_guard_rejections"]["v1_zero_volume_is_known_not_missing"])

    def test_v1_missing_volume_blocks(self):
        self.assertTrue(self.receipt["quality_guard_rejections"]["v1_missing_volume_rejected"])

    def test_v1_open_candle_blocks(self):
        self.assertTrue(self.receipt["quality_guard_rejections"]["v1_open_bar_rejected"])

    def test_v1_unverified_quality_blocks(self):
        self.assertTrue(self.receipt["quality_guard_rejections"]["v1_unverified_quality_rejected"])

    def test_v12_untrusted_entitlement_claim_blocks(self):
        self.assertTrue(self.receipt["quality_guard_rejections"]["v12_missing_entitlement_claim_rejected"])

    def test_v12_quality_warning_flag_blocks(self):
        self.assertTrue(self.receipt["quality_guard_rejections"]["v12_source_quality_flag_rejected"])

    def test_v12_unverified_quality_blocks(self):
        self.assertTrue(self.receipt["quality_guard_rejections"]["v12_unverified_quality_rejected"])

    def test_replay_advance_method_refuses_backstep(self):
        self.assertTrue(self.receipt["legacy_replay_clock_method_prevents_backstep"])

    def test_replay_legacy_direct_assignment_can_rewind_documented_gap(self):
        self.assertTrue(self.receipt["legacy_replay_clock_public_field_assignment_can_rewind"])

    def test_replay_utc_required(self):
        with self.assertRaises(ValueError):
            require_utc(datetime(2026,11,6,2,0))

    def test_replay_known_no_future(self):
        c=ReplayClock(minute(14))
        self.assertFalse(c.known(minute(15)))
        c.advance_to(minute(15))
        self.assertTrue(c.known(minute(15)))

    def test_contract_legacy_verified_untyped_gap_explicit(self):
        self.assertTrue(self.receipt["legacy_evidence_verified_accepts_truthy_string"])

    def test_contract_unknown_zone_is_rejected(self):
        self.assertTrue(self.receipt["legacy_zone_identity_guard_denies_unknown_zone"])

    def test_contract_non_unverified_without_evidence_denied(self):
        with self.assertRaises(ValueError):
            SignalDecision("B1", Strategy.SHORT, DecisionStatus.DETECTED)

    def test_contract_evidence_rejects_non_utc(self):
        with self.assertRaises(ValueError):
            Evidence("SYNTHETIC",datetime(2026,11,6,2,0),True)

    def test_engine_rejects_non_utc_asof(self):
        with self.assertRaises(ValueError):
            evaluate_unimplemented_zones(Strategy.SWING,datetime(2026,11,6,2,0))

    def test_engine_unverified_at_source_prerequisite_true(self):
        self.assertTrue(self.s[30]["v12_source_prerequisites"])
        d=expected_unverified_zone_decisions(when_utc=minute(30),strategy=Strategy.SWING)
        self.assertTrue(all(x.status is DecisionStatus.UNVERIFIED for x in d))

    def test_planner_readonly_reuse_before_five_minute_cadence(self):
        self.assertEqual(self.receipt["refresh_actions"]["before_cadence"],"REUSE_CLOSED")

    def test_planner_requests_window_at_cadence(self):
        self.assertEqual(self.receipt["refresh_actions"]["at_cadence"],"REQUEST_WINDOW")

    def test_planner_reconciles_old_corrections(self):
        self.assertEqual(self.receipt["refresh_actions"]["correction_reconcile"],"REQUEST_FULL_SESSION")

    def test_planner_unknown_capability_does_not_invent_delta(self):
        self.assertEqual(self.receipt["refresh_actions"]["unknown_capability"],"BLOCKED")

    def test_planner_never_certifies_data(self):
        self.assertTrue(self.receipt["refresh_outputs_all_uncertified"])
        self.assertTrue(self.receipt["synthetic_finality_flag_did_not_certify_source"])

    def test_planner_future_lookahead_cursor_rejected(self):
        cursor=SourceCursor(minute(0),minute(40),minute(20))
        with self.assertRaises(ValueError):
            plan_refresh(
                now_utc=minute(30),session_start_utc=minute(0),
                latest_expected_closed_start_utc=minute(0),
                bar_duration=timedelta(minutes=15),
                capability=SourceCapability.WINDOWED,cursor=cursor,
            )

    def test_planner_unclosed_expected_bar_denied(self):
        with self.assertRaises(ValueError):
            plan_refresh(
                now_utc=minute(14),session_start_utc=minute(0),
                latest_expected_closed_start_utc=minute(0),
                bar_duration=timedelta(minutes=15),
                capability=SourceCapability.FULL_SESSION,cursor=None,
            )

    def test_cache_ten_transitions_executed_on_real_sqlite(self):
        self.assertEqual(self.receipt["existing_cache_oracle_scenario_steps"],10)
        self.assertEqual(self.receipt["existing_cache_oracle_final_bars"],37)

    def test_cache_warm_then_dirty_tail_32(self):
        self.assertEqual(self.receipt["cache_old_revision_recompute_count"],32)

    def test_cache_independent_ema_and_atr(self):
        self.assertTrue(self.receipt["existing_cache_independent_ema_atr"])

    def test_cache_rejected_update_keeps_transaction_atomic(self):
        self.assertTrue(self.receipt["cache_rejected_transaction_atomic"])

    def test_cache_oracle_independent_atr_seed(self):
        checkpoints=independent_ema_atr_oracle(tuple(bar(i) for i in range(15)))
        self.assertIsNone(checkpoints[12].atr14)
        self.assertIsNotNone(checkpoints[13].atr14)

    def test_vn_both_stop_and_target_touched_is_ambiguous(self):
        self.assertEqual(self.receipt["ambiguous_both_stop_and_target_exit"],VNBarVerdict.AMBIGUOUS_BOTH.value)

    def test_vn_synthetic_metric_not_verified_profit(self):
        self.assertEqual(self.receipt["vn_synthetic_pnl"],"196.600")

    def test_vn_open_asof_rejected(self):
        with self.assertRaises(ValueError):
            inspect_fixture_vn_long_exit_bar(
                entry=D("10"), stop=D("9"),target=D("11"),
                low=D("8.5"),high=D("11.5"),bar_closed_utc=minute(15),
                bar_known_utc=minute(25),decision_utc=minute(20),
            )

    def test_vn_release_is_always_blocked(self):
        self.assertTrue(self.receipt["vn_release_blocked"])
        with self.assertRaises(PermissionError):
            require_vn_backtest_release()

    def test_source_rights_and_final_abi_remain_unsigned(self):
        self.assertFalse(self.receipt["external_market_entitlements_verified"])
        self.assertFalse(self.receipt["v1_v2_full_parity_claimed"])
        self.assertFalse(self.receipt["owner_a03_full_abi_approved"])
        self.assertEqual(self.receipt["owner_a02_module_dispositions_approved"],0)

    def test_cache_trading_and_physical_drive_remain_blocked(self):
        for k in ("physical_drive_cache_read_or_written",
                  "production_cache_read_authorized",
                  "production_cache_write_authorized",
                  "production_release_authorized",
                  "trading_authorized","external_g01_g08_gates_closed"):
            with self.subTest(k=k):
                self.assertFalse(self.receipt[k])

    def test_receipt_deterministic(self):
        fresh=evaluate_behavior_matrix()
        self.assertEqual(fresh["deterministic_synthetic_digest"],self.receipt["deterministic_synthetic_digest"])

    def test_fingerprint_not_owner_signature(self):
        self.assertEqual(len(self.receipt["deterministic_synthetic_digest"]),64)
        self.assertNotIn("owner_signature",self.receipt)
        self.assertEqual(self.receipt["owner_a02_module_dispositions_approved"],0)


if __name__=="__main__":
    unittest.main()
