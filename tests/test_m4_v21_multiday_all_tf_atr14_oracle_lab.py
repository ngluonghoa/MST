"""Cache V2.1 16 consecutive wholly fictional dates, numeric ATR14 on six TFs."""
from dataclasses import replace
from datetime import timedelta
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest

from swing_trading.incremental_cache import (
    Provider, SyntheticIncrementalStore, full_recompute,
)
from scripts.m2_a02_incremental_cache_oracle_lab import independent_ema_atr_oracle
from scripts.m2_a03_v2_cache_consumer_contract import fixture_scope
from scripts.m4_v21_layered_invalidation_lab import FullPolicyFixture
from scripts.m4_v21_gap_v1_numeric_parity_lab import aggregate
from scripts.m4_v21_multiday_all_tf_atr14_oracle_lab import (
    SCHEMA,STATUS,FAKE_DAYS,CHANGE_DAY,CHANGE_M5_IN_DAY,META_DAY,
    META_M5_IN_DAY,EXPECTED_TOTAL,EXPECTED_SUFFIX,TIMEFRAMES,
    KIND_PER_DAY,SOURCE_COUNT,COLD_AT,CORRECTION_KNOWN,METADATA_KNOWN,
    FakeDay,FakeHistory,fabricated_history,multi_key,binding,per_day_groups,
    materialize_history,changed_group,changed,execute_oracle,
)


class MultidayAllSixTFATROracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=fabricated_history()
        cls.report=execute_oracle()

    def test_01_six_explicit_timeframes(self):
        self.assertEqual(TIMEFRAMES,("M5","M15","M30","H1","H4","D1"))
    def test_02_sixteen_fictional_days_even_weekends(self):
        self.assertEqual(len(self.original.days),16)
        self.assertEqual(self.report["fake_consecutive_calendar_days_including_weekends"],16)
        self.assertFalse(self.original.official_historical_exchange_calendar_verified)
    def test_03_day_count_48_m5_source_bars(self):
        self.assertTrue(all(len(d.m5)==48 for d in self.original.days))
    def test_04_total_768_source_bars(self):
        self.assertEqual(self.report["source_m5_total"],768)
    def test_05_all_six_tf_window_counts(self):
        self.assertEqual(EXPECTED_TOTAL,{"M5":768,"M15":256,"M30":128,"H1":64,"H4":16,"D1":16})
        self.assertEqual(self.report["window_counts"],EXPECTED_TOTAL)
    def test_06_total_1248_qualified_toy_windows(self):
        self.assertEqual(self.report["total_toy_closed_derived_windows"],1248)
    def test_07_gap_is_two_hours_on_every_fake_date(self):
        self.assertEqual(self.report["toy_nontrading_gap_minutes_each_day"],120)
    def test_08_consecutive_dates_are_24_hours_apart(self):
        for x,y in zip(self.original.days,self.original.days[1:]):
            self.assertEqual(y.m5[0].start_utc-x.m5[0].start_utc,timedelta(days=1))
    def test_09_m15_m30_h1_never_group_across_lunch(self):
        for tf in ("M5","M15","M30","H1"):
            self.assertTrue(all(not g.crosses_declared_break for g in per_day_groups(tf)))
    def test_10_h4_d1_gap_stitch_is_explicitly_fictional(self):
        for tf in ("H4","D1"):
            self.assertTrue(all(g.crosses_declared_break for g in per_day_groups(tf)))
        self.assertFalse(self.report["official_h4_d1_provider_aggregation_verified"])
    def test_11_d1_has_sixteen_real_decimal_atr14_points(self):
        rows=materialize_history(self.original,"D1")
        cp=full_recompute(rows)
        self.assertEqual(len(cp),16)
        self.assertIsNone(cp[12].atr14)
        self.assertIsNotNone(cp[13].atr14)
        self.assertIsNotNone(cp[-1].atr14)
    def test_12_h4_has_sixteen_real_decimal_atr14_points(self):
        cp=full_recompute(materialize_history(self.original,"H4"))
        self.assertIsNone(cp[12].atr14)
        self.assertIsNotNone(cp[13].atr14)
    def test_13_all_six_tf_atr14_numerically_seeded(self):
        for tf in TIMEFRAMES:
            self.assertTrue(self.report["per_tf"][tf]["atr14_actual_numeric_seed_and_last_value_verified"])
    def test_14_all_six_atr14_seed_exact_bar_number_14(self):
        for tf in TIMEFRAMES:
            self.assertEqual(self.report["per_tf"][tf]["first_atr14_ordinal_zero_based"],13)
    def test_15_original_v1_cold_equals_independent_decimal_oracle(self):
        for tf in TIMEFRAMES:
            self.assertTrue(self.report["per_tf"][tf]["cold_v1_incremental_equals_full_and_independent_decimal_oracle"])
    def test_16_original_v1_cold_h4_equals_independent_oracle(self):
        bars=materialize_history(self.original,"H4")
        self.assertEqual(full_recompute(bars),independent_ema_atr_oracle(bars))
    def test_17_original_v1_cold_d1_equals_independent_oracle(self):
        bars=materialize_history(self.original,"D1")
        self.assertEqual(full_recompute(bars),independent_ema_atr_oracle(bars))
    def test_18_replay_has_right_expected_checkpoint_suffix_counts(self):
        self.assertEqual(EXPECTED_SUFFIX,{"M5":124,"M15":42,"M30":21,"H1":11,"H4":3,"D1":3})
        self.assertEqual({tf:self.report["per_tf"][tf]["numeric_checkpoint_suffix_recomputed"] for tf in TIMEFRAMES},EXPECTED_SUFFIX)
    def test_19_total_204_true_v1_checkpoints_recomputed(self):
        self.assertEqual(self.report["actual_v1_indicator_checkpoint_suffix_recomputed"],204)
    def test_20_revision_is_fourteenth_fake_day(self):
        self.assertEqual(CHANGE_DAY,13)
        self.assertEqual(self.report["price_revision_day_ordinal"],13)
    def test_21_revision_is_am_index_20(self):
        self.assertEqual(CHANGE_M5_IN_DAY,20)
        self.assertEqual(self.report["price_revision_m5_ordinal_within_day"],20)
    def test_22_mutated_group_ordinal_exact_per_tf(self):
        self.assertEqual({tf:changed_group(tf,CHANGE_DAY,CHANGE_M5_IN_DAY) for tf in TIMEFRAMES},
                         {"M5":644,"M15":214,"M30":107,"H1":53,"H4":13,"D1":13})
    def test_23_h4_and_d1_atr14_changes_after_seed_day(self):
        for tf in ("H4","D1"):
            self.assertTrue(self.report["per_tf"][tf]["atr14_numerically_verified_after_correction"])
    def test_24_every_tf_actual_v1_after_correction_equals_oracle(self):
        for tf in TIMEFRAMES:
            self.assertTrue(self.report["per_tf"][tf]["late_history_revision_v1_full_and_independent_oracle_equal"])
    def test_25_older_indicator_checkpoint_prefix_retained(self):
        self.assertTrue(all(v["unaffected_older_checkpoints_preserved"] for v in self.report["per_tf"].values()))
    def test_26_metadata_only_updates_zero_numeric_indicators(self):
        self.assertTrue(self.report["metadata_only_zero_numeric_indicator_recompute_all_six"])
    def test_27_metadata_only_zero_recompute_per_tf(self):
        self.assertTrue(all(v["metadata_only_indicator_recompute_zero"] for v in self.report["per_tf"].values()))
    def test_28_ephemeral_sqlite_reopen_checkpoint_parity(self):
        self.assertTrue(all(v["reopened_sqlite_checkpoint_numeric_parity"] for v in self.report["per_tf"].values()))
    def test_29_change_metadata_keeps_bar_numeric_sha(self):
        prices=changed(self.original,"PRICE",CHANGE_DAY,CHANGE_M5_IN_DAY)
        meta=changed(prices,"METADATA",META_DAY,META_M5_IN_DAY)
        old=prices.days[META_DAY].m5[META_M5_IN_DAY]
        new=meta.days[META_DAY].m5[META_M5_IN_DAY]
        self.assertEqual(old.normalized_digest,new.normalized_digest)
        self.assertNotEqual(old.first_known_utc,new.first_known_utc)
    def test_30_correction_and_metadata_are_after_cold(self):
        self.assertTrue(COLD_AT<CORRECTION_KNOWN<METADATA_KNOWN)
    def test_31_callers_cannot_self_assert_official_calendar(self):
        with self.assertRaisesRegex(PermissionError,"NO_INDEPENDENT_HISTORICAL"):
            replace(self.original,official_historical_exchange_calendar_verified=True)
    def test_32_callers_cannot_self_assert_individual_day(self):
        with self.assertRaisesRegex(PermissionError,"NO_CALLER_OFFICIAL"):
            replace(self.original.days[0],official_day_provenance=True)
    def test_33_missing_fabricated_day_denied(self):
        with self.assertRaisesRegex(TypeError,"SIXTEEN_TYPED"):
            replace(self.original,days=self.original.days[:-1])
    def test_34_duplicate_fabricated_day_denied(self):
        with self.assertRaisesRegex(ValueError,"NONCONSECUTIVE"):
            replace(self.original,days=(self.original.days[0],)+self.original.days[:-1])
    def test_35_reversed_day_sequence_denied(self):
        with self.assertRaisesRegex(ValueError,"NONCONSECUTIVE"):
            replace(self.original,days=tuple(reversed(self.original.days)))
    def test_36_missing_m5_in_day_denied(self):
        with self.assertRaisesRegex(TypeError,"EXACT_48_TYPED"):
            replace(self.original.days[1],m5=self.original.days[1].m5[:-1])
    def test_37_duplicate_m5_clock_in_day_denied(self):
        day=self.original.days[1];arr=list(day.m5)
        arr[1]=replace(arr[1],start_utc=day.m5[0].start_utc,end_utc=day.m5[0].end_utc,
                       first_known_utc=day.m5[0].first_known_utc)
        with self.assertRaisesRegex(ValueError,"BROKEN_GAPPED"):
            replace(day,m5=tuple(arr))
    def test_38_open_m5_in_fake_day_denied(self):
        day=self.original.days[2];arr=list(day.m5)
        arr[2]=replace(arr[2],closed=False)
        with self.assertRaisesRegex(ValueError,"BROKEN_GAPPED"):
            replace(day,m5=tuple(arr))
    def test_39_first_known_before_fake_m5_close_denied(self):
        day=self.original.days[3];arr=list(day.m5);old=arr[4]
        arr[4]=replace(old,first_known_utc=old.start_utc+timedelta(minutes=1))
        with self.assertRaisesRegex(ValueError,"BROKEN_GAPPED"):
            replace(day,m5=tuple(arr))
    def test_40_gap_m5_insertion_denied(self):
        day=self.original.days[4];arr=list(day.m5);old=arr[24]
        from scripts.m4_v21_multiday_all_tf_atr14_oracle_lab import FIVE
        gap=old.start_utc-timedelta(minutes=30)
        arr[24]=replace(old,start_utc=gap,end_utc=gap+FIVE,first_known_utc=gap+FIVE)
        with self.assertRaisesRegex(ValueError,"BROKEN_GAPPED"):
            replace(day,m5=tuple(arr))
    def test_41_full_policy_binding_distinct_per_tf(self):
        self.assertEqual(len({binding(tf) for tf in TIMEFRAMES}),6)
        self.assertEqual(len({multi_key(tf).fingerprint for tf in TIMEFRAMES}),6)
    def test_42_full_policy_rights_epoch_revocation_denied(self):
        original=multi_key("M5")
        changedrights=replace(original,source_rights_policy_version="RIGHTS.REVOKED")
        self.assertNotEqual(changedrights.fingerprint,binding("M5"))
    def test_43_full_policy_calendar_revision_denied(self):
        old=multi_key("H4")
        newer=replace(old,calendar_version="FAKE.16D.NEW")
        self.assertNotEqual(newer.fingerprint,binding("H4"))
    def test_44_full_policy_indicator_parameter_revision_denied(self):
        old=multi_key("D1")
        newer=replace(old,indicator_parameter_version="ATR14.EMA20.REVISED")
        self.assertNotEqual(newer.fingerprint,binding("D1"))
    def test_45_bad_source_revision_type_denied(self):
        with self.assertRaisesRegex(ValueError,"ONLY_TYPED_FAKE"):
            changed(self.original,"LIVE",CHANGE_DAY,CHANGE_M5_IN_DAY)
    def test_46_bad_source_ordinal_denied(self):
        with self.assertRaisesRegex(ValueError,"DECLARED_DAY"):
            changed(self.original,"PRICE",FAKE_DAYS,0)
    def test_47_unauthorized_timeframe_denied(self):
        with self.assertRaisesRegex(ValueError,"SIX_EXPLICIT"):
            multi_key("M1")
    def test_48_no_real_market_or_google_drive_or_trading_promotion(self):
        for field in ("history_source_issuer_verified",
                      "official_vn_exchange_historical_calendar_verified",
                      "official_h4_d1_provider_aggregation_verified",
                      "licensed_market_data_retention_or_cache_approved",
                      "google_drive_market_ohlcv_io_performed",
                      "independent_multiwriter_cas_signer_highwater_floor_verified",
                      "release_or_trading_authorized"):
            self.assertIs(self.report[field],False,field)
    def test_49_report_schema_and_synthetic_status_fixed(self):
        self.assertEqual(self.report["schema"],SCHEMA)
        self.assertEqual(self.report["status"],STATUS)
    def test_50_all_fake_daily_bars_preserve_independent_ordering(self):
        for tf in TIMEFRAMES:
            bars=materialize_history(self.original,tf)
            self.assertEqual(tuple(sorted(x.start_utc for x in bars)),tuple(x.start_utc for x in bars))
    def test_51_h4_d1_toy_stitch_is_not_native_market_ohlcv(self):
        self.assertFalse(self.report["official_h4_d1_provider_aggregation_verified"])
        self.assertFalse(self.report["history_source_issuer_verified"])
    def test_52_cross_provider_never_reused(self):
        self.assertNotEqual(multi_key("M5").fingerprint,replace(multi_key("M5"),provider=Provider.DNSE).fingerprint)
    def test_53_reject_production_environment_on_inherited_v1_key(self):
        with self.assertRaises(PermissionError):
            replace(multi_key("M5"),environment="PRODUCTION")
    def test_54_reject_incorrect_complete_source_after_known_clock(self):
        day=self.original.days[-1]
        # Inherited store cannot accept a candle which the as-of clock does
        # not yet know, even when the toy scope is otherwise complete.
        sample=day.m5[-1]
        future=replace(sample,revision="r2",first_known_utc=COLD_AT+timedelta(minutes=20))
        with TemporaryDirectory(prefix="mst-ci-multiday-stale-known-") as path:
            db=SyntheticIncrementalStore(Path(path)/"future-synthetic.sqlite")
            db.initialize()
            key=multi_key("M5")
            with self.assertRaisesRegex(ValueError,"unknown at observation clock"):
                db.apply_fixture_window(key,(future,),observed_at_utc=COLD_AT,
                    scope_start_utc=future.start_utc,scope_end_utc=future.end_utc,
                    complete_scope=False)
            self.assertEqual(db.read_bars(key),())

    def test_55_multiday_must_not_bypass_singlesession_v1_to_v2_mapping(self):
        with self.assertRaisesRegex(ValueError,"V1_V2_SESSION_MAP_NOT_EXPLICITLY_LOCKED"):
            fixture_scope(multi_key("D1"))
        self.assertFalse(self.report["v2_multiday_candidate_scope_approved"])
        self.assertTrue(self.report["sixteen_day_v1_fingerprint_only_not_v2_manifest"])
