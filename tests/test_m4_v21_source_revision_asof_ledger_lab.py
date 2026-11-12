"""Negative/positive M3-P0 as-of source event custody, synthetic-only."""
from dataclasses import replace
from datetime import timedelta, timezone
from decimal import Decimal
import unittest

from swing_trading.incremental_cache import full_recompute
from scripts.m2_a02_incremental_cache_oracle_lab import independent_ema_atr_oracle
from scripts.m4_v21_daily_partition_checkpoint_chain_lab import daily_scope
from scripts.m4_v21_multiday_all_tf_atr14_oracle_lab import (
    COLD_AT, CORRECTION_KNOWN, METADATA_KNOWN,
    CHANGE_DAY, CHANGE_M5_IN_DAY, META_DAY, META_M5_IN_DAY,
    materialize_history, TIMEFRAMES,
)
from scripts.m4_v21_source_revision_asof_ledger_lab import (
    SCHEMA, STATUS, GENESIS, ToyAsOfLedger, ToySourceObservation,
    LinkedToyObservation, fabricate_ledger, run_lab,
)


class SourceRevisionAsOfP0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger, cls.original, cls.price, cls.metadata = fabricate_ledger()
        cls.report = run_lab()
        cls.first = cls.ledger.links[0].observation

    def test_01_synthetic_report_schema(self):
        self.assertEqual(self.report["schema"], SCHEMA)
        self.assertEqual(self.report["status"], STATUS)

    def test_02_768_initial_m5_plus_2_revisions(self):
        self.assertEqual(self.report["declared_synthetic_m5_source_rows"], 768)
        self.assertEqual(self.report["untrusted_ledger_events"], 770)

    def test_03_cold_asof_excludes_future_revisions(self):
        self.assertEqual(self.ledger.snapshot(as_of_utc=COLD_AT), self.original)

    def test_04_price_known_asof_reconstructs_history(self):
        self.assertEqual(self.ledger.snapshot(as_of_utc=CORRECTION_KNOWN), self.price)

    def test_05_metadata_known_asof_reconstructs_history(self):
        self.assertEqual(self.ledger.snapshot(as_of_utc=METADATA_KNOWN), self.metadata)

    def test_06_price_invisible_until_first_known_inclusive(self):
        self.assertEqual(self.ledger.snapshot(as_of_utc=CORRECTION_KNOWN-timedelta(microseconds=1)), self.original)
        self.assertEqual(self.ledger.snapshot(as_of_utc=CORRECTION_KNOWN), self.price)

    def test_07_metadata_invisible_until_first_known_inclusive(self):
        self.assertEqual(self.ledger.snapshot(as_of_utc=METADATA_KNOWN-timedelta(microseconds=1)), self.price)
        self.assertEqual(self.ledger.snapshot(as_of_utc=METADATA_KNOWN), self.metadata)

    def test_08_asof_inside_session_is_incomplete(self):
        with self.assertRaisesRegex(PermissionError, "MISSING_UNKNOWN"):
            self.ledger.snapshot(as_of_utc=self.first.first_known_utc)

    def test_09_asof_inside_session_partial_only_known(self):
        rows = self.ledger.snapshot(as_of_utc=self.first.first_known_utc, require_complete=False)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[(0,0)], self.first.bar)

    def test_10_full_snapshot_requires_all_768_slots(self):
        self.assertEqual(len(self.ledger.snapshot(as_of_utc=COLD_AT, require_complete=False)), 768)

    def test_11_source_correction_changes_m5_value_digest(self):
        i, j = CHANGE_DAY, CHANGE_M5_IN_DAY
        self.assertNotEqual(self.original.days[i].m5[j].normalized_digest,
                            self.price.days[i].m5[j].normalized_digest)

    def test_12_metadata_only_preserves_m5_value_digest(self):
        i, j = META_DAY, META_M5_IN_DAY
        self.assertEqual(self.price.days[i].m5[j].normalized_digest,
                         self.metadata.days[i].m5[j].normalized_digest)

    def test_13_metadata_only_changes_revision_evidence(self):
        i,j = META_DAY,META_M5_IN_DAY
        self.assertNotEqual(self.price.days[i].m5[j].revision,
                            self.metadata.days[i].m5[j].revision)

    def test_14_six_tf_oracle_equality_before_correction(self):
        for tf in TIMEFRAMES:
            rows = materialize_history(self.original, tf)
            self.assertEqual(full_recompute(rows), independent_ema_atr_oracle(rows))

    def test_15_six_tf_oracle_equality_after_correction(self):
        for tf in TIMEFRAMES:
            rows = materialize_history(self.price, tf)
            self.assertEqual(full_recompute(rows), independent_ema_atr_oracle(rows))

    def test_16_six_tf_metadata_does_not_change_indicators(self):
        for tf in TIMEFRAMES:
            self.assertEqual(full_recompute(materialize_history(self.price,tf)),
                             full_recompute(materialize_history(self.metadata,tf)))

    def test_17_atr14_seeds_for_h4_and_d1(self):
        for tf in ("H4","D1"):
            cp = full_recompute(materialize_history(self.price,tf))
            self.assertIsNone(cp[12].atr14)
            self.assertIsNotNone(cp[13].atr14)

    def test_18_ledger_sha_chain_local_integrity(self):
        self.ledger.verify()
        self.assertEqual(self.ledger.links[0].previous_sha256, GENESIS)
        self.assertNotEqual(self.ledger.links[-1].sha256, GENESIS)

    def test_19_each_event_uses_prior_link_sha(self):
        a=self.ledger.links
        self.assertTrue(all(y.previous_sha256==x.sha256 for x,y in zip(a,a[1:])))

    def test_20_cannot_assert_official_calendar(self):
        with self.assertRaisesRegex(PermissionError,"SELF_ATTEST"):
            replace(self.first, official_calendar_attested=True)

    def test_21_cannot_assert_vendor_rights(self):
        with self.assertRaisesRegex(PermissionError,"SELF_ATTEST"):
            replace(self.first, vendor_license_attested=True)

    def test_22_cannot_assert_issuer_signature(self):
        with self.assertRaisesRegex(PermissionError,"SELF_ATTEST"):
            replace(self.first, issuer_signature_verified=True)

    def test_23_first_known_before_bar_close_denied(self):
        with self.assertRaisesRegex(PermissionError,"WINDOW_CLOSE_FIRST_KNOWN"):
            replace(self.first,first_known_utc=self.first.bar.start_utc,
                    bar=replace(self.first.bar,first_known_utc=self.first.bar.start_utc))

    def test_24_open_bar_denied(self):
        with self.assertRaisesRegex(PermissionError,"WINDOW_CLOSE"):
            replace(self.first,bar=replace(self.first.bar,closed=False))

    def test_25_wrong_revision_label_denied(self):
        with self.assertRaisesRegex(PermissionError,"REVISION_DRIFT"):
            replace(self.first,revision="r9")

    def test_26_wrong_gap_slot_denied(self):
        with self.assertRaisesRegex(PermissionError,"WINDOW_CLOSE"):
            replace(self.first,bar=replace(self.first.bar,
                    start_utc=self.first.bar.start_utc+timedelta(minutes=5),
                    end_utc=self.first.bar.end_utc+timedelta(minutes=5)))

    def test_27_wrong_timeframe_denied(self):
        with self.assertRaisesRegex(TypeError,"EXACT_M5"):
            replace(self.first,scope=daily_scope("M15",self.original.days[0]))

    def test_28_wrong_day_candidate_denied(self):
        with self.assertRaisesRegex(PermissionError,"TOY_CALENDAR_DATE"):
            replace(self.first,scope=daily_scope("M5",self.original.days[1]))

    def test_29_wrong_provider_without_binding_denied(self):
        old=self.first.scope
        candidate=replace(old.candidate,provider_id="DNSE")
        from scripts.m2_a03_v2_cache_consumer_contract import FixtureV2ConsumerScope
        with self.assertRaisesRegex(ValueError,"SCOPE_MISMATCH_PROVIDER"):
            FixtureV2ConsumerScope(old.legacy,candidate,old.accepted_legacy_instrument,old.mapped_candidate_symbol)

    def test_30_utc_zero_offset_required(self):
        with self.assertRaisesRegex(TypeError,"ZERO_OFFSET"):
            replace(self.first, first_known_utc=self.first.first_known_utc.astimezone(timezone(timedelta(hours=7))))

    def test_31_first_seen_must_have_generation_one(self):
        fresh=ToyAsOfLedger(self.original)
        with self.assertRaisesRegex(ValueError,"GENERATION_ONE"):
            fresh.append(replace(self.first,generation=2))
        self.assertEqual(fresh.links,())

    def test_32_first_seen_cannot_be_price_or_metadata(self):
        fresh=ToyAsOfLedger(self.original)
        with self.assertRaisesRegex(ValueError,"FIRST_SEEN"):
            fresh.append(replace(self.first,event_kind="PRICE"))

    def test_33_duplicate_initial_source_generation_denied(self):
        fresh=ToyAsOfLedger(self.original)
        fresh.append(self.first)
        with self.assertRaisesRegex(ValueError,"SEQUENCE_REPLAY"):
            fresh.append(self.first)
        self.assertEqual(len(fresh.links),1)

    def test_34_global_ledger_cannot_backdate_first_known(self):
        fresh=ToyAsOfLedger(self.original)
        fresh.append(self.ledger.links[1].observation)
        with self.assertRaisesRegex(PermissionError,"LEDGER_CLOCK_REWIND"):
            fresh.append(self.first)

    def test_35_source_rights_policy_mismatch_denied(self):
        altered=replace(self.first.scope.legacy,source_rights_policy_version="RIGHTS.REVOKED")
        from scripts.m2_a03_v2_cache_consumer_contract import FixtureV2ConsumerScope
        wrong=FixtureV2ConsumerScope(altered,self.first.scope.candidate,
                                     self.first.scope.accepted_legacy_instrument,
                                     self.first.scope.mapped_candidate_symbol)
        fresh=ToyAsOfLedger(self.original)
        with self.assertRaisesRegex(PermissionError,"CROSS_SOURCE_RIGHTS"):
            fresh.append(replace(self.first,scope=wrong))

    def test_36_numeric_price_rewrite_cannot_label_metadata(self):
        price=self.ledger.links[-2].observation
        self.assertEqual(price.event_kind,"PRICE")
        fresh=ToyAsOfLedger(self.original)
        old=self.original.days[CHANGE_DAY].m5[CHANGE_M5_IN_DAY]
        fresh.append(ToySourceObservation(price.scope,CHANGE_DAY,CHANGE_M5_IN_DAY,
                                         1,"INITIAL",old.first_known_utc,old.revision,old))
        with self.assertRaisesRegex(PermissionError,"METADATA_REVISION_CANNOT_CHANGE"):
            fresh.append(replace(price,event_kind="METADATA"))

    def test_37_identical_ohlcv_cannot_label_price_change(self):
        price=self.ledger.links[-2].observation
        fresh=ToyAsOfLedger(self.original)
        old=self.original.days[CHANGE_DAY].m5[CHANGE_M5_IN_DAY]
        fresh.append(ToySourceObservation(price.scope,CHANGE_DAY,CHANGE_M5_IN_DAY,
                                         1,"INITIAL",old.first_known_utc,old.revision,old))
        fake=replace(old,revision="r2",first_known_utc=CORRECTION_KNOWN)
        with self.assertRaisesRegex(PermissionError,"PRICE_REVISION_MUST_CHANGE"):
            fresh.append(replace(price,bar=fake))

    def test_38_generation_gap_denied(self):
        meta=self.ledger.links[-1].observation
        later=replace(meta,generation=4, revision="r4",first_known_utc=METADATA_KNOWN+timedelta(minutes=1),
                      bar=replace(meta.bar,revision="r4",first_known_utc=METADATA_KNOWN+timedelta(minutes=1)))
        with self.assertRaisesRegex(ValueError,"SOURCE_SEQUENCE"):
            self.ledger.append(later)

    def test_39_same_revision_label_reuse_denied(self):
        meta=self.ledger.links[-1].observation
        later=replace(meta,generation=3,first_known_utc=METADATA_KNOWN+timedelta(minutes=1),
                      bar=replace(meta.bar,first_known_utc=METADATA_KNOWN+timedelta(minutes=1)))
        with self.assertRaisesRegex(ValueError,"REVISION_ID_MUST_ADVANCE"):
            self.ledger.append(later)

    def test_40_tombstone_requires_no_bar(self):
        meta=self.ledger.links[-1].observation
        with self.assertRaisesRegex(PermissionError,"TOMBSTONE_MUST_HAVE_NO_BAR"):
            replace(meta,generation=3,event_kind="TOMBSTONE",
                    first_known_utc=METADATA_KNOWN+timedelta(minutes=1),
                    revision="r4")

    def test_41_tombstone_removes_visible_slot_asof_and_fails_complete(self):
        ledger,original,price,metadata=fabricate_ledger()
        meta=ledger.links[-1].observation
        when=METADATA_KNOWN+timedelta(minutes=1)
        ledger.append(replace(meta,generation=3,event_kind="TOMBSTONE",bar=None,
                              revision="r4",first_known_utc=when))
        self.assertEqual(ledger.snapshot(as_of_utc=METADATA_KNOWN),metadata)
        self.assertNotIn((META_DAY,META_M5_IN_DAY),ledger.snapshot(as_of_utc=when,require_complete=False))
        with self.assertRaisesRegex(PermissionError,"MISSING_UNKNOWN_OR_RETRACTED"):
            ledger.snapshot(as_of_utc=when)

    def test_42_tombstone_cannot_claim_early_known_time(self):
        meta=self.ledger.links[-1].observation
        with self.assertRaisesRegex(PermissionError,"TOMBSTONE_MUST_HAVE_NO_BAR"):
            replace(meta,generation=3,event_kind="TOMBSTONE",bar=None,
                    revision="r4",first_known_utc=meta.bar.start_utc)

    def test_43_local_sha_receipt_does_not_prove_real_issuer(self):
        proof=self.report["source_proof"]
        self.assertFalse(proof["issuer_signature_authenticated"])
        self.assertFalse(proof["official_market_calendar_attested"])
        self.assertFalse(proof["authorized_real_source_retention"])

    def test_44_no_authenticated_protected_floor_or_drive_write(self):
        proof=self.report["source_proof"]
        self.assertFalse(proof["independent_protected_rollback_floor"])
        self.assertFalse(proof["external_concurrent_writer_cas"])
        self.assertFalse(proof["read_write_real_google_drive_quotes"])

    def test_45_no_live_trading_or_production_permission(self):
        self.assertFalse(self.report["source_proof"]["production_or_trading_permitted"])

    def test_46_asof_unknown_partial_does_not_fabricate_missing(self):
        early=self.first.first_known_utc-timedelta(microseconds=1)
        self.assertEqual(self.ledger.snapshot(as_of_utc=early,require_complete=False),{})

    def test_47_negative_day_or_m5_index_denied(self):
        with self.assertRaisesRegex(ValueError,"FABRICATED_DAY"):
            replace(self.first,day_ordinal=-1)
        with self.assertRaisesRegex(ValueError,"M5_SLOT"):
            replace(self.first,m5_ordinal=48)

if __name__=="__main__":
    unittest.main()
