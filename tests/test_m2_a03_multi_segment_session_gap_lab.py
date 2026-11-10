"""Gapped multi-segment test-only M5 admissions, never official calendar rights."""
from dataclasses import replace
from datetime import date, timedelta
from unittest import TestCase

from swing_trading.session_calendar import SessionType
from scripts import m2_a03_multi_segment_session_gap_lab as m


class SessionGapLabTests(TestCase):
    @classmethod
    def setUpClass(cls):
        (cls.day,cls.am,cls.pm,cls.late,
         cls.gap,cls.cross,cls.known)=m.fixtures_day()
        cls.report=m.build()

    def view(self,rows,phase="AM_LAST",at=None,day=None):
        return m.candidate_screen(self.day if day is None else day,rows,
          claimed_segment=phase,
          as_of_utc=self.known if at is None else at)

    def test_01_sixteen_independent_scenarios(self):
        self.assertEqual(self.report["assertion_count"],16)

    def test_02_two_distinct_segments(self):
        self.assertEqual(self.report["untrusted_segments"],2)

    def test_03_ninety_minute_lunch_gap(self):
        self.assertEqual(self.report["modeled_lunch_gap_minutes"],90)

    def test_04_am_before_known_revision_r1(self):
        self.assertEqual(self.view((self.am,self.late),
            at=self.known-timedelta(microseconds=1))["candidate_revision_id"],"r1")

    def test_05_am_at_known_revision_r2(self):
        self.assertEqual(self.view((self.am,self.late))["candidate_revision_id"],"r2")

    def test_06_afternoon_independent_bar_accepted(self):
        self.assertEqual(self.view((self.pm,),phase="PM_FIRST",
            at=self.pm.bar.first_known_utc)["candidate_revision_id"],"r1")

    def test_07_am_late_revision_may_be_known_next_day(self):
        self.assertGreater(self.known,self.day.segments[-1].slot.ends_at_utc)

    def test_08_candle_during_gap_denied(self):
        with self.assertRaisesRegex(ValueError,"OUTSIDE_CLAIMED"):
            self.view((self.gap,),at=self.gap.bar.first_known_utc)

    def test_09_crosses_am_close_into_lunch_denied(self):
        with self.assertRaisesRegex(ValueError,"OUTSIDE_CLAIMED"):
            self.view((self.cross,),at=self.cross.bar.first_known_utc)

    def test_10_pm_bar_misclaimed_am_denied(self):
        with self.assertRaisesRegex(ValueError,"OUTSIDE_CLAIMED"):
            self.view((self.pm,),at=self.pm.bar.first_known_utc)

    def test_11_am_bar_misclaimed_pm_denied(self):
        with self.assertRaisesRegex(ValueError,"OUTSIDE_CLAIMED"):
            self.view((self.am,),phase="PM_FIRST",at=self.am.bar.first_known_utc)

    def test_12_unknown_segment_id_denied(self):
        with self.assertRaisesRegex(ValueError,"UNKNOWN_SEGMENT"):
            self.view((self.am,),phase="WRONG",at=self.am.bar.first_known_utc)

    def test_13_calendar_self_claim_denied(self):
        with self.assertRaises(PermissionError):
            replace(self.day,calendar_source_issuer_authenticated=True)

    def test_14_auction_not_auto_interpreted_as_m5_continuous(self):
        changed=replace(self.day,segments=(self.day.segments[0],
            replace(self.day.segments[1],kind=SessionType.AUCTION)))
        with self.assertRaisesRegex(PermissionError,"NONCONTINUOUS"):
            self.view((self.pm,),phase="PM_FIRST",
                at=self.pm.bar.first_known_utc,day=changed)

    def test_15_after_hours_not_auto_interpreted_as_continuous(self):
        changed=replace(self.day,segments=(self.day.segments[0],
            replace(self.day.segments[1],kind=SessionType.AFTER_HOURS)))
        with self.assertRaisesRegex(PermissionError,"NONCONTINUOUS"):
            self.view((self.pm,),phase="PM_FIRST",
                at=self.pm.bar.first_known_utc,day=changed)

    def test_16_overlapping_segments_denied(self):
        with self.assertRaisesRegex(ValueError,"OVERLAPPING_OR_UNORDERED"):
            replace(self.day,segments=(self.day.segments[0],
                replace(self.day.segments[1],slot=replace(
                  self.day.segments[1].slot,
                  starts_at_utc=self.day.segments[0].slot.starts_at_utc,
                  ends_at_utc=self.day.segments[0].slot.ends_at_utc,
                  permitted_bar_starts_utc=self.day.segments[0].slot.permitted_bar_starts_utc))))

    def test_17_reversed_segments_denied(self):
        with self.assertRaisesRegex(ValueError,"OVERLAPPING_OR_UNORDERED"):
            replace(self.day,segments=self.day.segments[::-1])

    def test_18_wrong_venue_denied(self):
        with self.assertRaisesRegex(ValueError,"CROSS_EXCHANGE"):
            replace(self.day,segments=(self.day.segments[0],
                replace(self.day.segments[1],venue="HNX")))

    def test_19_duplicate_label_denied(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE"):
            replace(self.day,segments=(self.day.segments[0],
                replace(self.day.segments[1],label="AM_LAST")))

    def test_20_wrong_local_date_denied(self):
        with self.assertRaisesRegex(ValueError,"SESSION_DATE_SCOPE"):
            replace(self.day,trading_day_local=date(2026,11,10))

    def test_21_one_segment_denied(self):
        with self.assertRaisesRegex(ValueError,"BOUNDED_MULTISEGMENT"):
            replace(self.day,segments=(self.day.segments[0],))

    def test_22_unsafe_caller_boolean_cannot_prove_calendar(self):
        self.assertFalse(self.day.calendar_source_issuer_authenticated)

    def test_23_no_external_market_rights(self):
        self.assertFalse(self.report["licensed_market_data_or_cache_rights"])

    def test_24_no_signed_exchange_public_page_admission(self):
        self.assertFalse(self.report["exchange_calendar_issuer_authenticated"])

    def test_25_no_official_auction_aggregation_proof(self):
        self.assertFalse(self.report["official_auction_bar_aggregation_verified"])

    def test_26_no_vendor_signed_first_known(self):
        self.assertFalse(self.report["source_bar_first_known_and_revision_issuer_verified"])

    def test_27_no_real_production_cache(self):
        self.assertFalse(self.report["market_data_or_production_cache_activated"])

    def test_28_no_original_code_touched(self):
        self.assertFalse(self.report["original_v1_or_v2_changed"])

    def test_29_no_owner_release_or_trade(self):
        for f in ("owner_a02_signed","owner_a03_v2_signed","owner_a03_gate_approved",
                  "production_release_authorized","trading_authorized"):
            self.assertFalse(self.report[f])

    def test_30_digest_only_self_report(self):
        self.assertEqual(len(self.report["synthetic_sha256"]),64)

    def test_31_repeatable_synthetic_receipt(self):
        self.assertEqual(m.build()["synthetic_sha256"],self.report["synthetic_sha256"])

    def test_32_candle_ending_exactly_at_lunch_start_is_valid(self):
        # An M5 candle [11:25, 11:30) is valid and must not be
        # confused with a crossing candle [11:27, 11:32).
        v=m.records_at(m.vn_utc(11,25),self.day.scope,event="AM_LAST_FIVE")
        result=self.view((v,),at=v.bar.first_known_utc)
        self.assertEqual(result["candidate_revision_id"],"r1")
        self.assertFalse(result["calendar_issuer_authenticated"])
