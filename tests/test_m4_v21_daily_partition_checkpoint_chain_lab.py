"""P0 cross-day synthetic V1 checkpoint carry -> per-date candidate V2 identity."""
from dataclasses import replace
from datetime import timedelta, timezone
from decimal import Decimal
import unittest

from swing_trading.incremental_cache import full_recompute
from swing_trading.v2_cache_partition_plan import FixturePartitionV2
from scripts.m2_a02_incremental_cache_oracle_lab import independent_ema_atr_oracle
from scripts.m2_a03_v2_cache_consumer_contract import FixtureV2ConsumerScope, fixture_scope
from scripts.m4_v21_multiday_all_tf_atr14_oracle_lab import (
    TIMEFRAMES, FAKE_DAYS, EXPECTED_TOTAL, EXPECTED_SUFFIX, KIND_PER_DAY,
    CHANGE_DAY, CHANGE_M5_IN_DAY, META_DAY, META_M5_IN_DAY,
    COLD_AT, CORRECTION_KNOWN, METADATA_KNOWN,
    fabricated_history, changed, multi_key, materialize_history, changed_group,
)
from scripts.m4_v21_daily_partition_checkpoint_chain_lab import (
    SCHEMA, STATUS, DayLink, daily_scope, daily_bars,
    build_chain, verify_chain, make_link, run_lab, state_digest,
)


class DailyPartitionCarryP0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = fabricated_history()
        cls.corrected = changed(cls.original, "PRICE", CHANGE_DAY, CHANGE_M5_IN_DAY)
        cls.metadata = changed(cls.corrected, "METADATA", META_DAY, META_M5_IN_DAY)
        cls.initial = {}
        cls.price = {}
        cls.lineage = {}
        cls.counts = {}
        for tf in TIMEFRAMES:
            initial, cold = build_chain(cls.original, tf, as_of_utc=COLD_AT)
            local = changed_group(tf, CHANGE_DAY, CHANGE_M5_IN_DAY) - CHANGE_DAY * KIND_PER_DAY[tf]
            price, recomputed = build_chain(
                cls.corrected, tf, as_of_utc=CORRECTION_KNOWN,
                previous=initial, dirty_day=CHANGE_DAY, kind="PRICE",
                dirty_group_index=local)
            lineage, meta = build_chain(
                cls.metadata, tf, as_of_utc=METADATA_KNOWN,
                previous=price, dirty_day=META_DAY, kind="METADATA")
            cls.initial[tf], cls.price[tf], cls.lineage[tf] = initial, price, lineage
            cls.counts[tf] = (cold, recomputed, meta)
        cls.receipt = run_lab()

    def test_01_receipt_is_synthetic_no_go(self):
        self.assertEqual(self.receipt["schema"], SCHEMA)
        self.assertEqual(self.receipt["status"], STATUS)

    def test_02_sixteen_distinct_daily_partitions_for_each_tf(self):
        self.assertEqual(self.receipt["candidate_single_date_partition_links"], 96)
        for tf in TIMEFRAMES:
            self.assertEqual(len({x.scope.candidate.digest for x in self.initial[tf]}), 16)

    def test_03_no_unqualified_multiday_v2_partition(self):
        for tf in TIMEFRAMES:
            with self.assertRaisesRegex(ValueError, "V1_V2_SESSION_MAP_NOT_EXPLICITLY_LOCKED"):
                fixture_scope(multi_key(tf))
        self.assertFalse(self.receipt["multi_day_composite_v2_scope_allowed"])

    def test_04_one_session_binding_exact_each_day(self):
        for tf in TIMEFRAMES:
            for index, link in enumerate(self.initial[tf]):
                self.assertEqual(link.scope, daily_scope(tf, self.original.days[index]))
                self.assertEqual(link.scope.candidate.session_date_local,
                                 self.original.days[index].m5[0].start_utc.date())
                self.assertEqual(link.scope.legacy.session_id,
                                 "SYNTHETIC." + link.scope.candidate.session_date_local.strftime("%Y%m%d"))

    def test_05_full_legacy_policy_binding_not_just_partition(self):
        old = self.initial["M5"][0].scope
        changed_rights = replace(old.legacy, source_rights_policy_version="RIGHTS.REVOKED")
        candidate = FixtureV2ConsumerScope(changed_rights, old.candidate,
                                           old.accepted_legacy_instrument, old.mapped_candidate_symbol)
        self.assertEqual(candidate.candidate.digest, old.candidate.digest)
        self.assertNotEqual(candidate.binding_sha256, old.binding_sha256)

    def test_06_all_1248_cold_checkpoints(self):
        self.assertEqual(sum(x[0] for x in self.counts.values()), 1248)
        self.assertEqual({k: self.counts[k][0] for k in TIMEFRAMES}, EXPECTED_TOTAL)

    def test_07_cross_date_numerical_equals_independent_decimal(self):
        for tf in TIMEFRAMES:
            checkpoints = tuple(cp for d in self.initial[tf] for cp in d.checkpoints)
            oracle = independent_ema_atr_oracle(materialize_history(self.original, tf))
            self.assertEqual(checkpoints, oracle)
            self.assertEqual(checkpoints, full_recompute(materialize_history(self.original, tf)))

    def test_08_atr14_seed_across_h4_d1_daily_boundaries(self):
        for tf in ("H4", "D1"):
            self.assertIsNone(self.initial[tf][12].checkpoints[-1].atr14)
            self.assertIsNotNone(self.initial[tf][13].checkpoints[-1].atr14)
            self.assertIsNotNone(self.initial[tf][15].checkpoints[-1].atr14)

    def test_09_cross_day_carry_equals_preceding_last(self):
        for tf in TIMEFRAMES:
            chain = self.initial[tf]
            for old, new in zip(chain, chain[1:]):
                self.assertEqual(new.incoming_checkpoint_sha256,
                                 state_digest(old.checkpoints[-1]))
                self.assertEqual(new.parent_link_sha256, old.self_sha256)

    def test_10_price_revises_only_204_causal_checkpoint_positions(self):
        self.assertEqual({tf: self.counts[tf][1] for tf in TIMEFRAMES}, EXPECTED_SUFFIX)
        self.assertEqual(sum(x[1] for x in self.counts.values()), 204)

    def test_11_before_dirty_day_same_links(self):
        for tf in TIMEFRAMES:
            self.assertEqual(self.initial[tf][:CHANGE_DAY], self.price[tf][:CHANGE_DAY])

    def test_12_price_revised_links_carry_forward(self):
        for tf in TIMEFRAMES:
            self.assertNotEqual(self.initial[tf][CHANGE_DAY].self_sha256,
                                self.price[tf][CHANGE_DAY].self_sha256)
            self.assertNotEqual(self.initial[tf][CHANGE_DAY + 1].parent_link_sha256,
                                self.price[tf][CHANGE_DAY + 1].parent_link_sha256)

    def test_13_price_final_checkpoint_parity_six_tf(self):
        for tf in TIMEFRAMES:
            got = tuple(cp for link in self.price[tf] for cp in link.checkpoints)
            expected = materialize_history(self.corrected, tf)
            self.assertEqual(got, independent_ema_atr_oracle(expected))

    def test_14_metadata_revision_zero_numeric_recompute(self):
        self.assertTrue(all(self.counts[tf][2] == 0 for tf in TIMEFRAMES))
        self.assertEqual(self.receipt["metadata_only_replayed_checkpoint_positions"], 0)

    def test_15_metadata_changes_lineage_not_numeric_bars(self):
        for tf in TIMEFRAMES:
            old, new = self.price[tf][META_DAY], self.lineage[tf][META_DAY]
            self.assertEqual(old.normalized_bars_sha256, new.normalized_bars_sha256)
            self.assertNotEqual(old.source_revision_lineage_sha256,
                                new.source_revision_lineage_sha256)
            self.assertEqual(old.checkpoints, new.checkpoints)

    def test_16_metadata_relinks_audit_provenance_forward(self):
        for tf in TIMEFRAMES:
            self.assertEqual(self.price[tf][:META_DAY], self.lineage[tf][:META_DAY])
            self.assertNotEqual(self.price[tf][META_DAY+1].parent_link_sha256,
                                self.lineage[tf][META_DAY+1].parent_link_sha256)

    def test_17_metadata_final_equals_original_v1_numerical(self):
        for tf in TIMEFRAMES:
            got = tuple(cp for day in self.lineage[tf] for cp in day.checkpoints)
            self.assertEqual(got, full_recompute(materialize_history(self.metadata, tf)))

    def test_18_wrong_predecessor_timeframe_denied(self):
        with self.assertRaisesRegex(ValueError, "WRONG_TF_OR_NONCONSECUTIVE"):
            make_link("M5", self.original.days[1], self.initial["D1"][0], as_of_utc=COLD_AT)

    def test_19_skipped_day_denied(self):
        with self.assertRaisesRegex(ValueError, "WRONG_TF_OR_NONCONSECUTIVE"):
            make_link("M5", self.original.days[3], self.initial["M5"][0], as_of_utc=COLD_AT)

    def test_20_missing_genesis_denied(self):
        with self.assertRaisesRegex(ValueError, "MISSING_GENESIS"):
            make_link("M5", self.original.days[2], None, as_of_utc=COLD_AT)

    def test_21_mutated_parent_hash_denied(self):
        bad = list(self.initial["M5"])
        bad[1] = replace(bad[1], parent_link_sha256="0"*64)
        with self.assertRaisesRegex(PermissionError, "PARENT_LINK"):
            verify_chain(self.original, "M5", tuple(bad), as_of_utc=COLD_AT)

    def test_22_mutated_checkpoint_denied(self):
        bad = list(self.initial["M5"])
        c = bad[0].checkpoints[0]
        bad[0] = replace(bad[0], checkpoints=(replace(c, ema20=c.ema20 + Decimal(1)),)
                         + bad[0].checkpoints[1:])
        with self.assertRaisesRegex(ValueError, "NONCAUSAL_OR_TAMPERED_INDICATOR_CARRY"):
            verify_chain(self.original, "M5", tuple(bad), as_of_utc=COLD_AT)

    def test_23_mutated_revision_lineage_hash_denied(self):
        bad = list(self.initial["M5"])
        bad[0] = replace(bad[0], source_revision_lineage_sha256="0"*64)
        with self.assertRaisesRegex(PermissionError, "CONTENT_LINEAGE"):
            verify_chain(self.original, "M5", tuple(bad), as_of_utc=COLD_AT)

    def test_24_mutated_full_policy_binding_denied(self):
        old = self.initial["M5"][0].scope
        changed_rights = replace(old.legacy, source_rights_policy_version="RIGHTS.REVOKED")
        bad_scope = FixtureV2ConsumerScope(changed_rights, old.candidate,
                                           old.accepted_legacy_instrument, old.mapped_candidate_symbol)
        bad = list(self.initial["M5"])
        bad[0] = replace(bad[0], scope=bad_scope)
        with self.assertRaisesRegex(PermissionError, "FULL_LEGACY_POLICY"):
            verify_chain(self.original, "M5", tuple(bad), as_of_utc=COLD_AT)

    def test_25_different_provider_scope_denied(self):
        old = self.initial["M5"][0].scope
        candidate = replace(old.candidate, provider_id="DNSE")
        with self.assertRaisesRegex(ValueError, "V1_V2_CACHE_SCOPE_MISMATCH_PROVIDER"):
            FixtureV2ConsumerScope(old.legacy, candidate,
                                   old.accepted_legacy_instrument, old.mapped_candidate_symbol)

    def test_26_first_known_after_asof_denied(self):
        with self.assertRaisesRegex(PermissionError, "CLOSED_KNOWN"):
            make_link("M5", self.corrected.days[CHANGE_DAY],
                      self.initial["M5"][CHANGE_DAY-1], as_of_utc=COLD_AT,
                      old=self.initial["M5"][CHANGE_DAY], numeric_start_index=CHANGE_M5_IN_DAY)

    def test_27_backdated_asof_cannot_use_later_metadata(self):
        with self.assertRaises(PermissionError):
            verify_chain(self.metadata, "M5", self.lineage["M5"], as_of_utc=COLD_AT)

    def test_28_metadata_only_numeric_change_denied(self):
        with self.assertRaisesRegex(PermissionError, "NUMERIC_OR_CARRY_DRIFT"):
            make_link("M5", self.corrected.days[CHANGE_DAY],
                      self.initial["M5"][CHANGE_DAY-1], as_of_utc=CORRECTION_KNOWN,
                      old=self.initial["M5"][CHANGE_DAY], lineage_only=True)

    def test_29_missing_full_previous_chain_denied(self):
        with self.assertRaisesRegex(ValueError, "COMPLETE_PRIOR_CHAIN"):
            build_chain(self.corrected, "M5", as_of_utc=CORRECTION_KNOWN,
                        previous=self.initial["M5"][:-1], dirty_day=CHANGE_DAY,
                        kind="PRICE", dirty_group_index=20)

    def test_30_utc_asof_required(self):
        with self.assertRaisesRegex(TypeError, "EXPLICIT_UTC"):
            make_link("M5", self.original.days[0], None,
                      as_of_utc=COLD_AT.astimezone(timezone(timedelta(hours=7))))

    def test_31_wrong_price_start_boundary_denied(self):
        with self.assertRaisesRegex(PermissionError, "UNPROVEN_CAUSAL_PREFIX"):
            make_link("M5", self.corrected.days[CHANGE_DAY],
                      self.initial["M5"][CHANGE_DAY-1], as_of_utc=CORRECTION_KNOWN,
                      old=self.initial["M5"][CHANGE_DAY], numeric_start_index=21)

    def test_32_replay_from_scratch_must_not_claim_existing_v2_storage(self):
        for key in ("official_exchange_calendar_authenticated",
                    "provider_issued_first_known_revision_authenticated",
                    "market_data_or_cloud_retention_licensed",
                    "physical_google_drive_market_cache_read_write",
                    "protected_external_monotonic_floor_or_two_writer_cas",
                    "production_release_or_trading_authorized"):
            self.assertIs(self.receipt[key], False)

    def test_33_immutable_h4_d1_fictional_source_is_explicit(self):
        for tf in ("H4", "D1"):
            self.assertTrue(all(len(daily_bars(day, tf)) == 1 for day in self.original.days))
        self.assertFalse(self.receipt["official_exchange_calendar_authenticated"])

    def test_34_cannot_authorize_source_by_self_supplied_digest(self):
        self.assertTrue(self.receipt["full_policy_and_source_revision_linked"])
        self.assertFalse(self.receipt["provider_issued_first_known_revision_authenticated"])

    def test_35_no_date_or_price_basis_cross_partition_reuse(self):
        self.assertNotEqual(self.initial["M5"][0].scope.candidate.digest,
                            self.initial["M5"][1].scope.candidate.digest)
        first = self.initial["M5"][0].scope
        self.assertNotEqual(first.candidate.digest,
                            replace(first.candidate, price_basis="ADJUSTED").digest)

if __name__ == "__main__":
    unittest.main()
