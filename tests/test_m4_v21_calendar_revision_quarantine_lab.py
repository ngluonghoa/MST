"""MST P0: synthetic as-of venue-calendar correction, halt and six-TF quarantine."""
from dataclasses import replace
from datetime import timedelta
import unittest

from scripts.m4_v21_multiday_all_tf_atr14_oracle_lab import (
    COLD_AT, fabricated_history, changed, CHANGE_DAY, CHANGE_M5_IN_DAY,
)
from scripts.m4_v21_source_revision_asof_ledger_lab import fabricate_ledger
from scripts.m4_v21_calendar_revision_quarantine_lab import (
    SCHEMA, STATUS, BASE_POLICY, REV_POLICY,
    CALENDAR_KNOWN_1, CALENDAR_KNOWN_2,
    ToyPhase, ToyCalendarDay, ToyCalendarEvent, ToyCalendarLedger,
    make_toy_day, fabricate_calendar_ledger, admission_preview, run_lab,
)


class ToyCalendarRevisionQuarantineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source, cls.original, _, _ = fabricate_ledger()
        cls.calendar = fabricate_calendar_ledger(cls.original)
        cls.receipt = run_lab()

    def test_01_report_schema_and_no_go(self):
        self.assertEqual(self.receipt["schema"], SCHEMA)
        self.assertEqual(self.receipt["status"], STATUS)

    def test_02_sixteen_invented_calendar_days(self):
        self.assertEqual(self.receipt["initial_fabricated_calendar_days"], 16)

    def test_03_eighteen_untrusted_calendar_events(self):
        self.assertEqual(self.receipt["untrusted_calendar_events"], 18)

    def test_04_baseline_accepts_all_only_structurally(self):
        base = self.receipt["baseline_before_calendar_revisions"]
        self.assertEqual(base["structurally_admissible_m5"], 768)
        self.assertEqual(base["quarantined_known_m5"], 0)
        self.assertEqual(base["source_unknown_m5"], 0)
        self.assertFalse(base["real_calendar_issuer_verified"])
        self.assertFalse(base["old_calendar_policy_cache_reuse_authorized"])

    def test_05_fake_holiday_rejects_48_m5(self):
        r=self.receipt["after_fake_holiday_correction"]
        self.assertEqual(r["quarantined_known_m5"], 48)
        self.assertEqual(r["quarantined_day_ordinals"], [3])

    def test_06_fake_halt_rejects_24_additional_m5(self):
        r=self.receipt["after_fake_halt_correction"]
        self.assertEqual(r["quarantined_known_m5"], 72)
        self.assertEqual(r["quarantined_day_ordinals"], [3,8])

    def test_07_asof_before_first_calendar_correction_has_no_future_event(self):
        early=admission_preview(self.source,self.calendar,as_of_utc=CALENDAR_KNOWN_1-timedelta(microseconds=1))
        self.assertEqual(early["quarantined_known_m5"],0)
        self.assertEqual(early["full_policy_rotation_day_ordinals"],[])

    def test_08_first_calendar_correction_visible_at_exact_first_known(self):
        exact=admission_preview(self.source,self.calendar,as_of_utc=CALENDAR_KNOWN_1)
        self.assertEqual(exact["quarantined_known_m5"],48)

    def test_09_second_revision_invisible_before_own_first_known(self):
        before=admission_preview(self.source,self.calendar,as_of_utc=CALENDAR_KNOWN_2-timedelta(microseconds=1))
        self.assertEqual(before["quarantined_known_m5"],48)

    def test_10_second_revision_visible_at_exact_known(self):
        exact=admission_preview(self.source,self.calendar,as_of_utc=CALENDAR_KNOWN_2)
        self.assertEqual(exact["quarantined_known_m5"],72)

    def test_11_final_phase_halt_is_not_a_continuous_source(self):
        day=self.calendar.snapshot(CALENDAR_KNOWN_2)[8]
        self.assertEqual(day.phases[1].kind,"HALTED")
        self.assertTrue(day.eligible(23))
        self.assertFalse(day.eligible(24))

    def test_12_fake_holiday_even_if_fabricated_bars_exist_denied(self):
        day=self.calendar.snapshot(CALENDAR_KNOWN_2)[3]
        self.assertEqual(day.status,"CLOSED")
        self.assertTrue(all(not day.eligible(i) for i in range(48)))

    def test_13_six_tf_impact_counts(self):
        self.assertEqual(self.receipt["six_tf_affected_windows_final"],
                         {"M5":72,"M15":24,"M30":12,"H1":6,"H4":2,"D1":2})

    def test_14_total_quarantined_derived_windows_118(self):
        self.assertEqual(self.receipt["after_fake_halt_correction"]["six_tf_affected_total"],118)

    def test_15_ineligible_higher_tf_group_quarantined_if_any_source_missing(self):
        r=self.receipt["after_fake_halt_correction"]
        self.assertEqual(r["six_tf_affected_windows"]["D1"],2)
        self.assertEqual(r["six_tf_affected_windows"]["H4"],2)

    def test_16_calendar_policy_identity_rotates_without_bare_v2_reuse(self):
        before=self.receipt["baseline_before_calendar_revisions"]["candidate_calendar_policy_digests"]
        after=self.receipt["after_fake_halt_correction"]["candidate_calendar_policy_digests"]
        self.assertNotEqual(before["3"],after["3"])
        self.assertNotEqual(before["8"],after["8"])
        self.assertEqual(before["0"],after["0"])

    def test_17_only_two_changed_days_require_full_policy_rotation(self):
        self.assertEqual(self.receipt["after_fake_halt_correction"]["full_policy_rotation_day_ordinals"],[3,8])

    def test_18_source_late_revision_does_not_qualify_calendar_provenance(self):
        flags=self.receipt["after_fake_halt_correction"]
        self.assertFalse(flags["source_first_known_by_actual_issuer_verified"])
        self.assertTrue(flags["calendar_claim_is_fictional"])

    def test_19_official_venue_issuer_and_holiday_not_authenticated(self):
        flags=self.receipt["after_fake_halt_correction"]
        self.assertFalse(flags["real_calendar_issuer_verified"])
        self.assertFalse(flags["real_holiday_or_halt_verified"])

    def test_20_cloud_rights_and_trading_denied(self):
        flags=self.receipt["after_fake_halt_correction"]
        for k in ("rights_for_live_market_data_or_cloud_cache",
                  "old_calendar_policy_cache_reuse_authorized",
                  "real_gdrive_quote_cache_read_write",
                  "protected_cloud_signer_floor_cas_verified",
                  "production_release_or_trading_permitted"):
            self.assertIs(flags[k],False,k)

    def test_21_all_calendar_event_links_locally_consistent(self):
        self.calendar.verify()
        for before,after in zip(self.calendar.links,self.calendar.links[1:]):
            self.assertEqual(after.parent_sha256,before.sha256)

    def test_22_cannot_self_assert_issuer_verified(self):
        cal=make_toy_day(self.original.days[0])
        with self.assertRaisesRegex(PermissionError,"SELF_ATTEST"):
            replace(cal,issuer_calendar_authenticated=True)

    def test_23_cannot_self_assert_venue_holiday_verified(self):
        cal=make_toy_day(self.original.days[0])
        with self.assertRaisesRegex(PermissionError,"SELF_ATTEST"):
            replace(cal,official_holiday_or_halt_proven=True)

    def test_24_cannot_self_assert_real_source_rights(self):
        ev=self.calendar.links[0].event
        with self.assertRaisesRegex(PermissionError,"SELF_GRANT"):
            replace(ev,real_source_rights_verified=True)

    def test_25_cannot_self_assert_vendor_signature(self):
        ev=self.calendar.links[0].event
        with self.assertRaisesRegex(PermissionError,"SELF_GRANT"):
            replace(ev,vendor_calendar_signature_verified=True)

    def test_26_cannot_self_assert_protected_clock(self):
        ev=self.calendar.links[0].event
        with self.assertRaisesRegex(PermissionError,"SELF_GRANT"):
            replace(ev,independent_protected_clock_verified=True)

    def test_27_auction_is_not_interpreted_as_continuous_m5(self):
        cal=make_toy_day(self.original.days[0],pm="AUCTION")
        self.assertTrue(cal.eligible(0))
        self.assertFalse(cal.eligible(24))

    def test_28_after_hours_is_not_continuous(self):
        cal=make_toy_day(self.original.days[0],pm="AFTER_HOURS")
        self.assertFalse(cal.eligible(30))

    def test_29_unknown_phase_is_quarantined(self):
        cal=make_toy_day(self.original.days[0],am="UNKNOWN")
        self.assertFalse(cal.eligible(10))

    def test_30_unknown_whole_day_quarantines_all(self):
        cal=make_toy_day(self.original.days[0],status="UNKNOWN")
        self.assertTrue(all(not cal.eligible(i) for i in range(48)))

    def test_31_non_declared_m5_slot_denied(self):
        cal=make_toy_day(self.original.days[0])
        with self.assertRaisesRegex(ValueError,"DECLARED_M5_SLOT"):
            cal.eligible(48)

    def test_32_wrong_segment_time_boundary_denied(self):
        cal=make_toy_day(self.original.days[0])
        wrong=replace(cal.phases[0],start_utc=cal.phases[0].start_utc+timedelta(minutes=5),
                      end_utc=cal.phases[0].end_utc+timedelta(minutes=5))
        with self.assertRaisesRegex(ValueError,"TOY_PHASE_BOUNDS"):
            replace(cal,phases=(wrong,cal.phases[1]))

    def test_33_wrong_phase_order_denied(self):
        cal=make_toy_day(self.original.days[0])
        with self.assertRaisesRegex(ValueError,"ORDERED_AM_PM"):
            replace(cal,phases=cal.phases[::-1])

    def test_34_unknown_phase_kind_denied(self):
        cal=make_toy_day(self.original.days[0])
        with self.assertRaisesRegex(ValueError,"TYPED_UNTRUSTED_PHASE"):
            replace(cal.phases[0],kind="MAGICAL_EXCHANGE_APPROVAL")

    def test_35_event_before_declared_local_first_known_denied(self):
        ev=self.calendar.links[0].event
        with self.assertRaisesRegex(PermissionError,"KNOWN_BEFORE_DECLARED"):
            replace(ev,first_known_utc=ev.first_known_utc-timedelta(minutes=1))

    def test_36_genesis_must_start_r1_and_generation_one(self):
        fresh=ToyCalendarLedger(self.original)
        initial=self.calendar.links[0].event
        with self.assertRaisesRegex(ValueError,"GENESIS_VERSION_REQUIRED"):
            fresh.append(replace(initial,generation=2))
        self.assertEqual(fresh.links,())

    def test_37_replaying_existing_calendar_generation_denied(self):
        fresh=ToyCalendarLedger(self.original)
        initial=self.calendar.links[0].event
        fresh.append(initial)
        with self.assertRaisesRegex(ValueError,"REVISION_SEQUENCE_GAP"):
            fresh.append(initial)
        self.assertEqual(len(fresh.links),1)

    def test_38_same_calendar_revision_label_denied(self):
        fresh=ToyCalendarLedger(self.original)
        old=self.calendar.links[0].event
        fresh.append(old)
        replacement=make_toy_day(self.original.days[0],status="UNKNOWN",policy=REV_POLICY)
        with self.assertRaisesRegex(ValueError,"REVISION_ID_REUSE"):
            fresh.append(ToyCalendarEvent(replacement,2,"r1",CALENDAR_KNOWN_1))

    def test_39_calendar_version_rotation_required_for_change(self):
        fresh=ToyCalendarLedger(self.original)
        old=self.calendar.links[0].event
        fresh.append(old)
        replacement=make_toy_day(self.original.days[0],status="UNKNOWN")
        with self.assertRaisesRegex(ValueError,"POLICY_VERSION_ROTATION"):
            fresh.append(ToyCalendarEvent(replacement,2,"r2",CALENDAR_KNOWN_1))

    def test_40_noop_calendar_revision_denied(self):
        fresh=ToyCalendarLedger(self.original)
        old=self.calendar.links[0].event
        fresh.append(old)
        with self.assertRaisesRegex(ValueError,"NO_POLICY_CHANGE"):
            fresh.append(ToyCalendarEvent(old.calendar,2,"r2",CALENDAR_KNOWN_1))

    def test_41_global_calendar_first_known_rewind_denied(self):
        fresh=ToyCalendarLedger(self.original)
        fresh.append(self.calendar.links[1].event)
        with self.assertRaisesRegex(PermissionError,"GLOBAL_CALENDAR_FIRST_KNOWN_REWIND"):
            fresh.append(self.calendar.links[0].event)

    def test_42_previous_calendar_value_not_overwritten_by_later_revision(self):
        before=self.calendar.snapshot(CALENDAR_KNOWN_1-timedelta(microseconds=1))[3]
        after=self.calendar.snapshot(CALENDAR_KNOWN_1)[3]
        self.assertEqual(before.policy_version,BASE_POLICY)
        self.assertEqual(after.policy_version,REV_POLICY)

    def test_43_calendar_not_known_for_future_day_reject_incomplete_snapshot(self):
        early=self.original.days[0].m5[0].start_utc
        with self.assertRaisesRegex(PermissionError,"MISSING_ASOF_DAY_CALENDAR"):
            admission_preview(self.source,self.calendar,as_of_utc=early)

    def test_44_missing_final_source_works_only_as_quarantine_not_complete(self):
        early=COLD_AT-timedelta(minutes=2)
        r=admission_preview(self.source,self.calendar,as_of_utc=early)
        self.assertEqual(r["source_unknown_m5"],1)
        self.assertEqual(r["six_tf_affected_total"],6)
        self.assertTrue(r["any_incomplete_or_quarantined"])
        self.assertFalse(r["production_release_or_trading_permitted"])

    def test_45_cross_history_source_calendar_mix_denied(self):
        altered=changed(self.original,"PRICE",CHANGE_DAY,CHANGE_M5_IN_DAY)
        wrong=fabricate_calendar_ledger(altered)
        with self.assertRaisesRegex(PermissionError,"CROSS_HISTORY_SOURCE_CALENDAR"):
            admission_preview(self.source,wrong,as_of_utc=CALENDAR_KNOWN_2)

    def test_46_forged_local_chain_hash_denied(self):
        fresh=ToyCalendarLedger(self.original)
        fresh.append(self.calendar.links[0].event)
        fresh._links[0]=replace(fresh.links[0],sha256="f"*64)
        with self.assertRaisesRegex(PermissionError,"SHA_TAMPERING"):
            fresh.verify()

    def test_47_forced_calendar_claim_not_an_independent_provider_approval(self):
        self.assertTrue(self.receipt["missing_external_issuer_rights_and_calendar_proof"])
        self.assertFalse(self.receipt["real_storage_trading_or_release_authorized"])

if __name__=="__main__":
    unittest.main()
