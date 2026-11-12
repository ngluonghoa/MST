"""32 checks for explicitly hypothetical DNSE WS replay/close coverage."""
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from unittest import TestCase
from scripts import m2_a03_dnse_ws_reconnect_coverage_lab as m
from scripts.m2_a03_documented_ohlc_transport_boundary_lab import DocumentedTransport as T

class DNSEWSReconnectCoverageTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grid=m.toy_grid()
        cls.b=[m.close_at(i) for i in range(3)]
        cls.cases=m.make_scenario_rows()
        cls.result=m.build()
    def r(self,*items):
        return m.reconcile(m.samples_for(tuple(items)),self.grid)
    def test_01_exact_ten_scenarios(self):self.assertEqual(self.result["scenario_count"],10)
    def test_02_clean_toy_grid_structural_only(self):
        x=self.r(*self.cases["COMPLETE_UNTRUSTED"])
        self.assertEqual(x["status"],"STRUCTURALLY_COVERED_BUT_UNTRUSTED")
    def test_03_clean_grid_not_market_authority(self):
        self.assertFalse(self.r(*self.cases["COMPLETE_UNTRUSTED"])["source_eligible_for_signal"])
    def test_04_one_missing_closed_rejected(self):
        self.assertEqual(self.r(*self.cases["NO_CLOSED_MIDDLE"])["closed_grid_missing_count"],1)
    def test_05_forming_is_not_closed_middle(self):
        x=self.r(*self.cases["FORMING_NOT_CLOSED"])
        self.assertEqual(x["closed_grid_missing_count"],1)
    def test_06_late_middle_after_newer_closed_detected(self):
        self.assertEqual(self.r(*self.cases["CLOSED_OUT_OF_ORDER"])["closed_out_of_order_count"],1)
    def test_07_same_closed_payload_duplicate_tracked(self):
        x=self.r(*self.cases["EXACT_DUPLICATE_NOT_PROOF"])
        self.assertEqual(x["closed_exact_duplicate_count"],1)
    def test_08_same_closed_duplicate_does_not_grant_rights(self):
        self.assertFalse(self.r(*self.cases["EXACT_DUPLICATE_NOT_PROOF"])["source_eligible_for_signal"])
    def test_09_conflicting_closed_same_start_quarantined(self):
        self.assertEqual(self.r(*self.cases["CONFLICTING_DUPLICATE"])["closed_conflict_count"],1)
    def test_10_conflicting_closed_does_not_invent_revision(self):
        x=self.r(*self.cases["CONFLICTING_DUPLICATE"])
        self.assertTrue(x["must_not_auto_forge_revision_or_gap_fill"])
    def test_11_reconnect_requires_backfill_even_with_full_toy_grid(self):
        x=self.r(*self.cases["RECONNECT_COMPLETE_STILL_UNTRUSTED"])
        self.assertIn("CONNECTION_GENERATION_CHANGED_REQUIRES_BACKFILL",x["reasons"])
    def test_12_local_reconnect_detected(self):
        self.assertEqual(self.r(*self.cases["RECONNECT_COMPLETE_STILL_UNTRUSTED"])["local_reconnect_count"],1)
    def test_13_reconnect_and_gap_both_flags(self):
        x=self.r(*self.cases["RECONNECT_AND_GAP"])
        self.assertEqual((x["local_reconnect_count"],x["closed_grid_missing_count"]),(1,1))
    def test_14_forming_after_closed_not_source_revision(self):
        self.assertEqual(self.r(*self.cases["FORMING_AFTER_CLOSED"])["forming_after_closed_count"],1)
    def test_15_bar_outside_declared_grid_is_untrusted(self):
        self.assertEqual(self.r(*self.cases["UNEXPECTED_BAR"])["unexpected_time_count"],1)
    def test_16_hypothetical_grid_not_official(self):
        self.assertTrue(self.r(*self.cases["COMPLETE_UNTRUSTED"])["hypothetical_grid_not_official_market_calendar"])
    def test_17_no_issuer_sequence_in_local_generation(self):
        self.assertTrue(self.result["fake_local_connection_generation_not_issuer_sequence"])
    def test_18_no_actual_websocket(self):self.assertFalse(self.result["actual_ws_access_ever_used"])
    def test_19_no_source_backfill_rights(self):self.assertFalse(self.result["provider_history_backfill_authenticated"])
    def test_20_no_first_known_proof(self):self.assertFalse(self.result["source_revision_first_known_verified"])
    def test_21_no_owner_consent(self):
        self.assertFalse(self.result["a02_63_owner_approved"])
        self.assertFalse(self.result["a03_v2_8_owner_approved"])
        self.assertFalse(self.result["a03_14_owner_approved"])
    def test_22_no_market_drive_cache(self):self.assertFalse(self.result["real_drive_market_cache_active"])
    def test_23_no_orders(self):self.assertFalse(self.result["trading_authorized"])
    def test_24_empty_expected_grid_denied(self):
        with self.assertRaises(TypeError):m.reconcile(tuple(),tuple())
    def test_25_duplicate_grid_denied(self):
        with self.assertRaises(ValueError):m.reconcile(tuple(),(self.grid[0],self.grid[0]))
    def test_26_reversed_grid_denied(self):
        with self.assertRaises(ValueError):m.reconcile(tuple(),tuple(reversed(self.grid)))
    def test_27_unaligned_grid_denied(self):
        with self.assertRaises(ValueError):m.reconcile(tuple(),(self.grid[0]+1,))
    def test_28_boolean_grid_timestamp_denied(self):
        with self.assertRaises(ValueError):m.reconcile(tuple(),(True,))
    def test_29_generation_boolean_denied(self):
        t=datetime.fromtimestamp(self.grid[0]+1000,timezone.utc)
        with self.assertRaises(ValueError):m.LocalObservation(self.b[0],t,True)
    def test_30_generation_rollback_denied(self):
        events=m.samples_for(((self.b[0],2),(self.b[1],1)))
        with self.assertRaisesRegex(ValueError,"ROLLBACK"):m.reconcile(events,self.grid)
    def test_31_observer_clock_rollback_denied(self):
        t=datetime.fromtimestamp(self.grid[0]+1000,timezone.utc)
        events=(m.LocalObservation(self.b[0],t,1),
                m.LocalObservation(self.b[1],t-timedelta(seconds=1),1))
        with self.assertRaisesRegex(ValueError,"NOT_MONOTONE"):m.reconcile(events,self.grid)
    def test_32_repeatable_receipt_without_real_data(self):
        self.assertEqual(len(self.result["synthetic_receipt_sha256"]),64)
        self.assertEqual(self.result["synthetic_receipt_sha256"],m.build()["synthetic_receipt_sha256"])
        self.assertTrue(self.result["no_real_ws_rows_or_source_timestamps_saved"])
