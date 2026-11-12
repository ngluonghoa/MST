"""Exact-close zero-overlap source V1 bug and unaffected branch regressions."""
from unittest import TestCase
from scripts import m2_a02_refresh_zero_overlap_boundary_lab as m


class OriginalPlannerZeroOverlapTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=m.evaluate()

    def test_01_twenty_two_distinct_scenarios(self):
        self.assertEqual(len(m.CASES),22)
        self.assertEqual(len({x[0] for x in m.CASES}),22)

    def test_02_exact_four_original_exception_paths(self):
        self.assertEqual(self.r["reproduced_original_value_error_cases"],4)

    def test_03_current_close_exact_start_end_exception(self):
        self.assertEqual(m.call_original({"overlap":0})["kind"],"ERROR_EMPTY_REQUEST")

    def test_04_exception_matches_original_source_text(self):
        self.assertEqual(m.call_original({"overlap":0})["detail"],"ValueError: Empty request")

    def test_05_session_finality_alone_still_raises(self):
        self.assertEqual(m.call_original({"overlap":0,"session_final":True})["kind"],"ERROR_EMPTY_REQUEST")

    def test_06_head_finality_alone_still_raises(self):
        self.assertEqual(m.call_original({"overlap":0,"head_final":True})["kind"],"ERROR_EMPTY_REQUEST")

    def test_07_preview_can_trigger_same_boundary(self):
        self.assertEqual(m.call_original({"overlap":0,"checked":50,"preview":True})["kind"],"ERROR_EMPTY_REQUEST")

    def test_08_one_overlap_prevents_zero_length_window(self):
        self.assertEqual(m.call_original({"overlap":1})["kind"],"WINDOW_45_50")

    def test_09_session_floor_clamps_large_overlap(self):
        self.assertEqual(m.call_original({"overlap":24})["kind"],"WINDOW_0_50")

    def test_10_minute_after_close_avoids_empty(self):
        self.assertEqual(m.call_original({"overlap":0,"now":51})["kind"],"WINDOW_50_51")

    def test_11_minute_before_close_avoids_empty(self):
        self.assertEqual(m.call_original({"overlap":0,"now":49,"latest":40,
            "closed":40,"checked":40,"full":40})["kind"],"WINDOW_45_49")

    def test_12_new_candle_no_overlap_requests_once(self):
        self.assertEqual(m.call_original({"overlap":0,"closed":40,"checked":45})["kind"],"WINDOW_45_50")

    def test_13_new_candle_one_overlap_requests_previous(self):
        self.assertEqual(m.call_original({"overlap":1,"closed":40,"checked":45})["kind"],"WINDOW_40_50")

    def test_14_when_recently_checked_reuses(self):
        self.assertEqual(m.call_original({"overlap":0,"checked":50})["kind"],"REUSE")

    def test_15_larger_refresh_interval_reuses(self):
        self.assertEqual(m.call_original({"overlap":0,"refresh":6})["kind"],"REUSE")

    def test_16_correction_due_forces_full_scope(self):
        self.assertEqual(m.call_original({"overlap":0,"full":10})["kind"],"FULL_0_50")

    def test_17_full_reconcile_missing_forces_full(self):
        self.assertEqual(m.call_original({"overlap":0,"full":None})["kind"],"FULL_0_50")

    def test_18_full_provider_forces_full(self):
        self.assertEqual(m.call_original({"overlap":0,"cap":"FULL_SESSION"})["kind"],"FULL_0_50")

    def test_19_unknown_capability_is_blocked(self):
        self.assertEqual(m.call_original({"overlap":0,"cap":"UNKNOWN"})["kind"],"BLOCKED")

    def test_20_cold_cache_fetches_full(self):
        self.assertEqual(m.call_original({"overlap":0,"cold":True})["kind"],"FULL_0_50")

    def test_21_both_finality_flags_reuse_but_not_authority(self):
        self.assertEqual(m.call_original({"overlap":0,"session_final":True,
             "head_final":True})["kind"],"REUSE_FINALITY_CLAIM")
        self.assertFalse(self.r["vendor_entitlement_and_source_verified"])

    def test_22_unknown_capability_blocks_even_with_finality(self):
        self.assertEqual(m.call_original({"overlap":0,"cap":"UNKNOWN",
             "session_final":True,"head_final":True})["kind"],"BLOCKED")

    def test_23_rewound_session_source_blocks(self):
        self.assertEqual(m.call_original({"overlap":0,"closed":46,
             "checked":46,"full":46})["kind"],"BLOCKED")

    def test_24_preview_with_overlap_requests_valid_window(self):
        self.assertEqual(m.call_original({"overlap":1,"checked":50,
             "preview":True})["kind"],"WINDOW_45_50")

    def test_25_full_provider_new_closed_bar_no_empty(self):
        self.assertEqual(m.call_original({"cap":"FULL_SESSION","closed":40,
             "checked":45})["kind"],"FULL_0_50")

    def test_26_actual_cases_match_independent_expected_matrix(self):
        self.assertTrue(all(x["actual"]==x["expected"] for x in self.r["cases"]))

    def test_27_no_runtime_v1_source_patch_claimed(self):
        self.assertFalse(self.r["original_v1_source_modified"])

    def test_28_no_signed_a02_or_a03_approval(self):
        self.assertFalse(self.r["a02_owner_approved"])
        self.assertFalse(self.r["a03_v2_full_parity_approved"])

    def test_29_external_floor_and_real_drive_not_proven(self):
        self.assertFalse(self.r["external_floor_cas_proven"])
        self.assertFalse(self.r["real_drive_market_cache_authorized"])

    def test_30_no_trading(self):
        self.assertFalse(self.r["trading_authorized"])
        self.assertFalse(self.r["production_release_authorized"])

    def test_31_exact_no_go_verdict(self):
        self.assertEqual(self.r["status"],m.STATUS)

    def test_32_digest_only_consistency(self):
        self.assertEqual(len(self.r["synthetic_case_index_sha256"]),64)
