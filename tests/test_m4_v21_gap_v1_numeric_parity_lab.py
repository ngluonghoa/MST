"""MST Cache V2.1: real V1 arithmetic against independently coded fixture oracle.

No real provider or official exchange calendar. GitHub Actions temp SQLite only.
"""
from dataclasses import replace
from datetime import timedelta
import unittest

from swing_trading.incremental_cache import Provider, full_recompute
from swing_trading.session_calendar import SessionType
from scripts.m2_a02_incremental_cache_oracle_lab import independent_ema_atr_oracle
from scripts.m2_a03_multi_segment_session_gap_lab import candidate_screen, records_at, vn_utc
from scripts.m2_a03_v2_cache_consumer_contract import fixture_scope
from scripts.m4_v21_layered_invalidation_lab import FullPolicyFixture
from scripts.m4_v21_gap_v1_numeric_parity_lab import (
    SCHEMA, STATUS, AM_START, PM_START, DAY_END, COLD_AT, PRICE_KNOWN, METADATA_KNOWN,
    TIMEFRAMES, COUNT_PER_PHASE, SOURCE_COUNT, SOURCE_MUTATION_INDEX,
    METADATA_MUTATION_INDEX, ToyGapGrid, ToyGroup, legacy_key, full_binding,
    start_for, source_bar, expected_members, aggregate, materialize_tf,
    fabricate_grid, amended_source, actual_v1_numeric_fixture,
)


class CacheGapV1NumericParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grid=fabricate_grid()
        cls.report=actual_v1_numeric_fixture()

    def altered(self, **kw):
        return replace(self.grid,**kw)

    def source_altered(self, index, **kw):
        rows=list(self.grid.source)
        rows[index]=replace(rows[index],**kw)
        return self.altered(source=tuple(rows))

    def group_altered(self,index,**kw):
        groups=list(self.grid.groups)
        groups[index]=replace(groups[index],**kw)
        return self.altered(groups=tuple(groups))

    def test_01_exact_six_timeframes(self):
        self.assertEqual(TIMEFRAMES,("M5","M15","M30","H1","H4","D1"))

    def test_02_exact_48_closed_m5_two_segments(self):
        self.assertEqual(len(self.grid.source),48)
        self.assertTrue(all(b.closed for b in self.grid.source))

    def test_03_two_explicit_am_pm_continuous_segments(self):
        self.assertEqual([x.label for x in self.grid.day.segments],["AM","PM"])
        self.assertTrue(all(x.kind is SessionType.CONTINUOUS for x in self.grid.day.segments))

    def test_04_two_hour_nontrading_gap(self):
        self.assertEqual(PM_START-AM_START-COUNT_PER_PHASE*timedelta(minutes=5),timedelta(hours=2))
        self.assertEqual(self.report["nontrading_break_minutes"],120)

    def test_05_six_tf_group_counts(self):
        self.assertEqual(self.report["toy_tf_window_counts"],{
            "M5":48,"M15":16,"M30":8,"H1":4,"H4":1,"D1":1})

    def test_06_total_synthetic_grouped_windows_78(self):
        self.assertEqual(len(self.grid.groups),78)
        self.assertEqual(self.report["toy_grouped_window_count"],78)

    def test_07_intraday_groups_never_cross_am_pm_break(self):
        for tf in ("M5","M15","M30","H1"):
            for g in self.grid.for_tf(tf):
                self.assertFalse(g.crosses_declared_break)
                self.assertTrue(all(i<24 for i in g.members) or
                                all(i>=24 for i in g.members))

    def test_08_h4_and_d1_are_explicit_fake_stitches(self):
        for tf in ("H4","D1"):
            g=self.grid.for_tf(tf)[0]
            self.assertTrue(g.crosses_declared_break)
            self.assertEqual(g.members,tuple(range(48)))
        self.assertTrue(self.report["h4_and_d1_purely_artificial_stitched_trade_minutes"])

    def test_09_valid_m5_membership_has_gap_not_wallclock_rounding(self):
        self.assertEqual(start_for(23)+timedelta(minutes=5),AM_START+timedelta(hours=2))
        self.assertEqual(start_for(24),PM_START)
        self.assertGreater(start_for(24)-start_for(23),timedelta(minutes=5))

    def test_10_source_verified_time_never_claimed(self):
        self.assertFalse(self.grid.official_source_calendar_verified)
        self.assertFalse(self.grid.day.calendar_source_issuer_authenticated)
        self.assertFalse(self.report["official_hose_hnx_upcom_historical_calendar_verified"])

    def test_11_full_policy_binding_per_tf_not_identical(self):
        self.assertEqual(len({full_binding(tf) for tf in TIMEFRAMES}),6)
        for group in self.grid.groups:
            self.assertEqual(group.binding_sha256,full_binding(group.tf))

    def test_12_actual_v1_cold_ema_numeric_equals_independent_oracle(self):
        for evidence in self.report["tf_evidence"].values():
            self.assertTrue(evidence["cold_indicator_values_equal_independent_oracle"])

    def test_13_atr14_valid_only_after_14_toy_windows(self):
        for tf in TIMEFRAMES:
            result=full_recompute(materialize_tf(self.grid,tf))
            independent=independent_ema_atr_oracle(materialize_tf(self.grid,tf))
            self.assertEqual(result,independent)
            self.assertEqual(result[-1].atr14 is not None,len(result)>=14,tf)

    def test_14_single_am_m5_correction_affects_each_tf_numeric_bar(self):
        self.assertEqual({k:v["revised_group_index"] for k,v in self.report["tf_evidence"].items()},
                         {"M5":20,"M15":6,"M30":3,"H1":1,"H4":0,"D1":0})

    def test_15_exact_48_changed_numeric_checkpoint_suffix_positions(self):
        self.assertEqual({k:v["price_correction_checkpoint_suffix_count"]
                          for k,v in self.report["tf_evidence"].items()},
                         {"M5":28,"M15":10,"M30":5,"H1":3,"H4":1,"D1":1})
        self.assertEqual(self.report["total_price_correction_checkpoint_suffix_positions"],48)

    def test_16_actual_v1_incremental_equals_independent_after_repricing(self):
        for v in self.report["tf_evidence"].values():
            self.assertTrue(v["corrected_numeric_indicators_equal_independent_oracle"])

    def test_17_metadata_lineage_only_recomputes_zero_numeric_checkpoints(self):
        self.assertTrue(all(x["metadata_only_zero_recompute"] for x in self.report["tf_evidence"].values()))

    def test_18_final_v1_checkpoints_still_equal_independent_oracle(self):
        self.assertTrue(all(x["final_ema_atr_equal_independent_oracle"] for x in self.report["tf_evidence"].values()))

    def test_19_a03_existing_am_pm_bar_screens_composed(self):
        self.assertTrue(self.report["two_existing_a03_fake_segment_screens_passed"])

    def test_20_missing_single_m5_closed_bar_denied(self):
        with self.assertRaisesRegex(ValueError,"EXACT_48_TYPED"):
            self.altered(source=self.grid.source[:-1])

    def test_21_duplicate_m5_timestamp_denied(self):
        with self.assertRaisesRegex(ValueError,"M5_BAR_NOT_DECLARED"):
            b=self.grid.source[24]
            self.source_altered(25,start_utc=b.start_utc,end_utc=b.end_utc,
                                first_known_utc=b.first_known_utc)

    def test_22_source_bar_inside_lunch_gap_denied(self):
        start=vn_utc(12,0)
        with self.assertRaisesRegex(ValueError,"M5_BAR_NOT_DECLARED"):
            self.source_altered(24,start_utc=start,end_utc=start+timedelta(minutes=5),
                                first_known_utc=start+timedelta(minutes=5))

    def test_23_source_end_that_crosses_break_denied(self):
        with self.assertRaisesRegex(ValueError,"M5_BAR_NOT_DECLARED"):
            self.source_altered(23,end_utc=PM_START)

    def test_24_open_m5_bar_denied(self):
        with self.assertRaisesRegex(ValueError,"M5_BAR_NOT_DECLARED"):
            self.source_altered(0,closed=False)

    def test_25_first_known_before_m5_bar_close_denied(self):
        b=self.grid.source[0]
        with self.assertRaisesRegex(ValueError,"M5_BAR_NOT_DECLARED"):
            self.source_altered(0,first_known_utc=b.start_utc+timedelta(minutes=1))

    def test_26_partial_higher_tf_member_denied(self):
        g=next(i for i,x in enumerate(self.grid.groups) if x.tf=="M15")
        with self.assertRaisesRegex(PermissionError,"PARTIAL_OR_OPEN"):
            self.group_altered(g,closed_complete=False)

    def test_27_missing_aggregated_group_denied(self):
        with self.assertRaisesRegex(ValueError,"INCOMPLETE_DUPLICATE"):
            self.altered(groups=self.grid.groups[:-1])

    def test_28_duplicate_group_denied(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE_DERIVED"):
            self.altered(groups=self.grid.groups+(self.grid.groups[0],))

    def test_29_m15_group_crossing_break_denied(self):
        n=next(i for i,x in enumerate(self.grid.groups) if x.tf=="M15" and x.ordinal==7)
        with self.assertRaisesRegex(ValueError,"INCOMPLETE_DUPLICATE_OR_CROSS_GAP"):
            self.group_altered(n,members=(22,23,24))

    def test_30_h4_bridge_flag_cannot_be_silently_removed(self):
        n=next(i for i,x in enumerate(self.grid.groups) if x.tf=="H4")
        with self.assertRaisesRegex(PermissionError,"UNATTESTED_CROSS_BREAK"):
            self.group_altered(n,crosses_declared_break=False)

    def test_31_foreign_full_policy_binding_denied(self):
        with self.assertRaisesRegex(PermissionError,"INHERITED_V1_RIGHTS"):
            self.group_altered(0,binding_sha256=full_binding("M15"))

    def test_32_calendar_policy_version_changes_full_binding(self):
        key=legacy_key("M5")
        changed=replace(key,calendar_version="FAKEGAPCAL2")
        new_binding=FullPolicyFixture(fixture_scope(changed)).binding
        self.assertNotEqual(new_binding,full_binding("M5"))
        with self.assertRaisesRegex(PermissionError,"INHERITED_V1_RIGHTS"):
            self.group_altered(0,binding_sha256=new_binding)

    def test_33_source_rights_revocation_changes_full_binding(self):
        key=legacy_key("M5")
        denied=replace(key,source_rights_policy_version="RIGHTS.REVOKED")
        self.assertNotEqual(FullPolicyFixture(fixture_scope(denied)).binding,full_binding("M5"))

    def test_34_caller_cannot_self_authorize_calendar(self):
        with self.assertRaisesRegex(PermissionError,"CALLER_MAY_NOT_DECLARE"):
            self.altered(official_source_calendar_verified=True)

    def test_35_auction_phase_cannot_masquerade_as_continuous(self):
        a,b=self.grid.day.segments
        changed=replace(self.grid.day,segments=(a,replace(b,kind=SessionType.AUCTION)))
        with self.assertRaisesRegex(PermissionError,"AUCTION_OR_AFTER_HOURS"):
            self.altered(day=changed)

    def test_36_wrong_venue_phase_denied_by_prior_a03_envelope(self):
        a,b=self.grid.day.segments
        with self.assertRaisesRegex(ValueError,"CROSS_EXCHANGE"):
            replace(self.grid.day,segments=(a,replace(b,venue="HNX")))

    def test_37_unknown_source_phase_denied_by_prior_a03_screen(self):
        b=records_at(start_for(24),self.grid.day.scope,event="PM_EXAMPLE")
        with self.assertRaisesRegex(ValueError,"UNKNOWN_SEGMENT"):
            candidate_screen(self.grid.day,(b,),claimed_segment="NOT_A_SEGMENT",
                             as_of_utc=b.bar.first_known_utc)

    def test_38_inherited_v1_provider_isolation(self):
        from dataclasses import replace
        old=legacy_key("M5")
        other=replace(old,provider=Provider.DNSE)
        self.assertNotEqual(old.fingerprint,other.fingerprint)

    def test_39_invalid_extra_source_index_denied(self):
        with self.assertRaisesRegex(ValueError,"SOURCE_M5_INDEX"):
            start_for(48)

    def test_40_invalid_timeframe_denied(self):
        with self.assertRaisesRegex(ValueError,"SIX_TYPED_TIMEFRAMES"):
            legacy_key("M1")

    def test_41_unknown_source_event_kind_denied(self):
        with self.assertRaisesRegex(ValueError,"TYPED_TEST_REVISION_KIND"):
            amended_source(self.grid,"UNAUTHORIZED",20)

    def test_42_invalid_revision_source_index_denied(self):
        with self.assertRaisesRegex(ValueError,"DECLARED_SOURCE_INDEX"):
            amended_source(self.grid,"PRICE",-1)

    def test_43_price_revision_known_after_closed_session(self):
        self.assertTrue(DAY_END<COLD_AT<PRICE_KNOWN<METADATA_KNOWN)
        changed=amended_source(self.grid,"PRICE",SOURCE_MUTATION_INDEX)
        self.assertEqual(changed.source[SOURCE_MUTATION_INDEX].first_known_utc,PRICE_KNOWN)

    def test_44_metadata_revision_changes_only_lineage_not_price_digest(self):
        priced=amended_source(self.grid,"PRICE",SOURCE_MUTATION_INDEX)
        metadata=amended_source(priced,"METADATA",METADATA_MUTATION_INDEX)
        before=priced.source[METADATA_MUTATION_INDEX]
        after=metadata.source[METADATA_MUTATION_INDEX]
        self.assertEqual(before.normalized_digest,after.normalized_digest)
        self.assertNotEqual(before.revision,after.revision)

    def test_45_no_live_source_drive_or_release_authorization(self):
        for key in ("source_license_verified","official_hose_hnx_upcom_historical_calendar_verified",
                    "real_provider_aggregation_and_correction_proven",
                    "real_source_first_known_verified","physical_google_drive_quote_cache_read_write",
                    "cross_run_authenticated_writer_or_protected_cas_floor",
                    "live_signal_release_or_trading_authorized"):
            self.assertIs(self.report[key],False,key)

    def test_46_reproducible_real_v1_oracle_fixture_report(self):
        self.assertEqual(self.report,actual_v1_numeric_fixture())
        self.assertEqual(self.report["schema"],SCHEMA)
        self.assertEqual(self.report["status"],STATUS)
