"""Independent-oracle and transaction trace contracts for inherited V1 cache.

All tests run in GitHub Actions using fabricated candles and temporary SQLite;
no real sources or Google Drive chunk I/O, no local user environment.
"""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import unittest

from scripts.m2_a02_incremental_cache_oracle_lab import (
    BAR_COUNT, bar, identity, independent_ema_atr_oracle,
    instant, run_cache_oracle_lab,
)
from swing_trading.incremental_cache import (
    CacheIdentity, IndicatorCheckpoint, Provider, full_recompute,
)


class CacheOracleMatrixRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_cache_oracle_lab()
        cls.steps = {x["name"]: x for x in cls.report["scenario_steps"]}

    def test_matrix_accepts_only_synthetic_independent_oracle_subset(self):
        self.assertEqual(
            self.report["status"],
            "V1_INCREMENTAL_COLD_WARM_CORRECTION_ROLLBACK_EQUALS_INDEPENDENT_ORACLE",
        )
        self.assertEqual(self.report["schema"],
                         "mst.a02.incremental-v1-independent-ema20-atr14-synthetic-oracle.v1")
        self.assertEqual(self.report["scenario_step_count"], 10)
        self.assertEqual(len(self.steps), 10)

    def test_initial_36_bar_cold_rebuild(self):
        x = self.steps["COLD_36"]
        self.assertEqual((x["inserted"], x["indicator_bars_recomputed"]), (36, 36))
        self.assertEqual(x["bars"], 36)
        self.assertEqual(x["atr14_first_valid_bar_number"], 14)

    def test_warm_restart_reuses_same_content_without_recomputation(self):
        x = self.steps["REOPEN_WARM_REUSE"]
        self.assertEqual((x["unchanged"], x["indicator_bars_recomputed"]), (2, 0))
        self.assertIsNone(x["first_dirty_utc"])

    def test_metadata_only_revision_changes_lineage_not_indicators(self):
        x = self.steps["METADATA_ONLY_R8"]
        self.assertEqual((x["lineage_only"], x["indicator_bars_recomputed"]), (1, 0))
        self.assertEqual(x["checkpoints"], 36)

    def test_closed_append_recomputes_only_one_checkpoint(self):
        x = self.steps["APPEND_BAR36"]
        self.assertEqual((x["inserted"], x["indicator_bars_recomputed"]), (1, 1))
        self.assertEqual(x["bars"], 37)
        self.assertEqual(x["first_dirty_utc"], instant(36).isoformat())

    def test_old_correction_recomputes_32_checkpoint_tail(self):
        x = self.steps["OLD_CORRECTION_R5_REPLAY_TAIL"]
        self.assertEqual((x["revised"], x["indicator_bars_recomputed"]), (1, 32))
        self.assertEqual(x["first_dirty_utc"], instant(5).isoformat())

    def test_incomplete_page_does_not_delete_missing_rows(self):
        x = self.steps["INCOMPLETE_PAGE_NO_DELETE"]
        self.assertEqual((x["deleted"], x["indicator_bars_recomputed"]), (0, 0))
        self.assertEqual(x["bars"], 37)

    def test_complete_page_deletes_only_missing_range_and_reseeds(self):
        x = self.steps["COMPLETE_SCOPE_DELETE_BAR11"]
        self.assertEqual((x["deleted"], x["indicator_bars_recomputed"]), (1, 25))
        self.assertEqual(x["bars"], 36)
        self.assertEqual(x["first_dirty_utc"], instant(11).isoformat())

    def test_backfill_rebuilds_deleted_history_through_present(self):
        x = self.steps["BACKFILL_BAR11"]
        self.assertEqual((x["inserted"], x["indicator_bars_recomputed"]), (1, 26))
        self.assertEqual(x["bars"], 37)
        self.assertEqual(x["first_dirty_utc"], instant(11).isoformat())

    def test_open_candle_does_not_mutate_indicator_checkpoints(self):
        x = self.steps["OPEN_BAR_IGNORED"]
        self.assertEqual((x["ignored_open"], x["indicator_bars_recomputed"]), (1, 0))
        self.assertEqual(x["bars"], 37)

    def test_invalid_second_write_rolls_back_all_tables(self):
        self.assertTrue(self.report["failed_transaction_all_sqlite_tables_rollback"])
        x = self.steps["REJECT_AND_ROLLBACK_ALL_TABLES"]
        self.assertEqual(x["bars"], 37)
        self.assertEqual((x["inserted"], x["revised"], x["deleted"]), (0, 0, 0))

    def test_all_steps_match_independent_oracle_and_deny_live_rights(self):
        for name, x in self.steps.items():
            with self.subTest(name=name):
                self.assertTrue(x["ema20_atr14_independent_oracle_equal"])
                self.assertTrue(x["fixture_only"])
                self.assertFalse(x["source_authorized"])
                self.assertEqual(x["bars"], x["checkpoints"])
                self.assertEqual(x["atr14_first_valid_bar_number"], 14)

    def test_source_lineage_events_verified_in_order(self):
        self.assertTrue(self.report["source_revision_lineage_order_verified"])

    def test_different_provider_cache_partitions_cannot_alias(self):
        self.assertTrue(self.report["two_provider_partitions_isolated"])
        self.assertNotEqual(identity(Provider.SSI).fingerprint,
                            identity(Provider.DNSE).fingerprint)

    def test_policy_revision_invalidates_namespace_without_source_rights(self):
        self.assertTrue(self.report["revision_rights_namespace_isolated"])
        key = identity()
        revoked = replace(key, source_rights_policy_version="RIGHTS.REVOKED")
        self.assertNotEqual(key.fingerprint, revoked.fingerprint)

    def test_corrupted_database_rejected(self):
        self.assertTrue(self.report["tampered_sqlite_bar_detected"])

    def test_fixture_bar_with_zero_volume_remains_valid(self):
        self.assertTrue(self.steps["COLD_36"]["verified_zero_volume_is_present"])

    def test_report_checksum_is_repeatable_for_identical_cloud_fixtures(self):
        second = run_cache_oracle_lab()
        self.assertEqual(self.report["synthetic_matrix_sha256"],
                         second["synthetic_matrix_sha256"])
        self.assertRegex(self.report["synthetic_matrix_sha256"], "^[0-9a-f]{64}$")

    def test_all_production_authorities_remain_false(self):
        for field in (
            "v2_google_drive_cache_parity_implemented",
            "real_github_witness_cas_proven",
            "vendor_rights_or_source_verified",
            "licensed_drive_cache_read_or_written",
            "owner_a02_a03_signed_off",
            "production_cache_authorized",
            "trading_authorized",
        ):
            with self.subTest(field=field):
                self.assertIs(self.report[field], False)


class IndependentDecimalOracleUnitTests(unittest.TestCase):
    def test_empty_candles_have_no_checkpoint(self):
        self.assertEqual(independent_ema_atr_oracle(()), ())

    def test_first_13_atr_none_14th_atr_seeded(self):
        checkpoints = independent_ema_atr_oracle(tuple(bar(i) for i in range(20)))
        self.assertTrue(all(x.atr14 is None for x in checkpoints[:13]))
        self.assertEqual(checkpoints[13].atr_seen, 14)
        self.assertEqual(checkpoints[13].atr14, D("4"))
        self.assertEqual(checkpoints[13].atr_seed_sum, D("56"))

    def test_two_bar_ema20_recursion_value(self):
        x, y = independent_ema_atr_oracle((bar(0), bar(1)))
        self.assertEqual(x.ema20, bar(0).close)
        expected = (D(2) * bar(1).close + D(19) * bar(0).close) / D(21)
        self.assertEqual(y.ema20, expected)
        self.assertEqual(y.atr_seen, 2)

    def test_true_range_uses_prior_close_on_gap(self):
        candles = (bar(0), bar(1, close=D("200")))
        checkpoint = independent_ema_atr_oracle(candles)[-1]
        self.assertEqual(checkpoint.atr_seed_sum, D("4") + D("102"))
        self.assertIsNone(checkpoint.atr14)

    def test_oracle_matches_legacy_full_recompute_before_and_after_atr_seed(self):
        for count in (1, 13, 14, 15, 20, 36, 37):
            candles = tuple(bar(i) for i in range(count))
            with self.subTest(count=count):
                self.assertEqual(independent_ema_atr_oracle(candles),
                                 full_recompute(candles))

    def test_oracle_responds_to_old_price_correction(self):
        candles = tuple(bar(i) for i in range(36))
        changed = list(candles)
        changed[5] = bar(5, close=D("200"), revision="r2")
        before = independent_ema_atr_oracle(candles)
        after = independent_ema_atr_oracle(tuple(changed))
        self.assertEqual(before[:5], after[:5])
        self.assertNotEqual(before[5:], after[5:])

    def test_metadata_revision_is_semantically_noop_for_indicator_oracle(self):
        candles = list(bar(i) for i in range(36))
        prior = independent_ema_atr_oracle(tuple(candles))
        candles[8] = bar(8, revision="r2")
        self.assertEqual(prior, independent_ema_atr_oracle(tuple(candles)))

    def test_oracle_deletion_and_backfill_do_not_cause_extra_older_changes(self):
        candles = tuple(bar(i) for i in range(36))
        without = tuple(c for i, c in enumerate(candles) if i != 11)
        baseline = independent_ema_atr_oracle(candles)
        deleted = independent_ema_atr_oracle(without)
        self.assertEqual(baseline[:11], deleted[:11])
        restored = list(without)
        restored.insert(11, bar(11))
        self.assertEqual(independent_ema_atr_oracle(tuple(restored)), baseline)

    def test_open_bar_rejected_by_oracle(self):
        with self.assertRaisesRegex(ValueError, "ORACLE_OPEN_BAR_NOT_ALLOWED"):
            independent_ema_atr_oracle((bar(0, closed=False),))

    def test_fixture_rejects_nonfinite_price_in_real_legacy_model(self):
        with self.assertRaises(ValueError):
            bar(0, close=D("NaN"))

    def test_production_cache_identity_cannot_be_enrolled_through_fixture(self):
        with self.assertRaises(PermissionError):
            replace(identity(), environment="PRODUCTION")

    def test_same_fixture_identity_not_source_authority(self):
        key = identity()
        self.assertEqual(key.environment, "SYNTHETIC_TEST_ONLY")
        self.assertEqual(key.source_rights_policy_version, "RIGHTS.UNVERIFIED")
        self.assertNotEqual(key.project_id, "MST")


if __name__ == "__main__":
    unittest.main()
