"""Fixture-only original V1 late revision and cross-session membership QA."""
from unittest import TestCase
from scripts import m2_a02_v1_cross_session_first_known_lab as m


class CrossSessionFirstKnownTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=m.evaluate()
        cls.assertions=set(cls.r["assertions"])

    def test_01_exact_assertion_count(self):
        self.assertEqual(self.r["assertion_count"],21)

    def test_02_assertion_labels_unique(self):
        self.assertEqual(len(self.assertions),21)

    def test_03_four_initial_a(self):
        self.assertEqual(self.r["counts"]["a_initial"],4)

    def test_04_three_initial_b(self):
        self.assertEqual(self.r["counts"]["b_initial"],3)

    def test_05_late_revision_keeps_a_bar_count(self):
        self.assertEqual(self.r["counts"]["a_after_late_revision"],4)

    def test_06_late_revision_rebuilds_three(self):
        self.assertEqual(self.r["counts"]["a_revised_checkpoint_tail"],3)

    def test_07_late_revision_uses_original_checkpoint_math(self):
        self.assertIn("A_CORRECTED_COLD_ORACLE",self.assertions)

    def test_08_correct_session_b_remains_isolated(self):
        self.assertTrue(self.r["distinct_proper_session_keys_remain_isolated"])

    def test_09_before_first_known_not_visible_to_clock(self):
        self.assertIn("BEFORE_FIRST_KNOWN_REPLAY_CLOCK_EXCLUDES",self.assertions)

    def test_10_at_first_known_visible_to_clock(self):
        self.assertIn("EXACT_FIRST_KNOWN_REPLAY_CLOCK_INCLUDES",self.assertions)

    def test_11_raw_reader_no_asof_parameter(self):
        self.assertIn("READ_BARS_HAS_NO_ASOF_PARAMETER",self.assertions)

    def test_12_latest_only_reader_can_be_misused_at_old_asof(self):
        self.assertTrue(self.r["latest_only_reader_does_not_preserve_historical_asof_payload"])

    def test_13_wrong_session_b_bar_accepted_in_a(self):
        self.assertTrue(self.r["wrong_session_candle_can_be_written_into_caller_labeled_partition"])

    def test_14_wrong_b_in_a_grows_a_to_five(self):
        self.assertEqual(self.r["counts"]["a_after_mislabeled_b"],5)

    def test_15_cross_session_insert_recomputes_one(self):
        self.assertEqual(self.r["counts"]["a_mislabeled_checkpoint_tail"],1)

    def test_16_internal_parity_does_not_certify_membership(self):
        self.assertIn("INTERNAL_COLD_PARITY_CANNOT_AUTHENTICATE_SESSION",self.assertions)

    def test_17_real_b_cache_unmodified(self):
        self.assertIn("ACTUAL_B_PARTITION_REMAINS_UNCHANGED",self.assertions)

    def test_18_bar_no_calendar_membership_attestation(self):
        self.assertIn("BAR_HAS_NO_OFFICIAL_SESSION_MEMBER_PROOF",self.assertions)

    def test_19_no_real_vendor_revision(self):
        self.assertFalse(self.r["real_vendor_revision_attested"])

    def test_20_no_official_calendar(self):
        self.assertFalse(self.r["official_session_calendar_verified"])

    def test_21_no_authenticated_first_known(self):
        self.assertFalse(self.r["signed_source_first_known_verified"])

    def test_22_no_native_asof_certificate(self):
        self.assertFalse(self.r["historical_asof_reader_qualified"])

    def test_23_no_owner_signoffs(self):
        for key in ("a02_63_owner_signed","a03_v2_8_owner_signed","a03_14_owner_signed"):
            self.assertFalse(self.r[key])

    def test_24_no_real_drive_cache(self):
        self.assertFalse(self.r["real_google_drive_cache_authorized"])

    def test_25_no_live_prod_or_trade(self):
        self.assertFalse(self.r["production_authorized"])
        self.assertFalse(self.r["trading_authorized"])

    def test_26_original_v1_unchanged(self):
        self.assertFalse(self.r["original_v1_modified"])

    def test_27_receipt_digest_format(self):
        self.assertEqual(len(self.r["synthetic_digest_sha256"]),64)

    def test_28_deterministic_receipt(self):
        self.assertEqual(m.evaluate()["synthetic_digest_sha256"],
                         self.r["synthetic_digest_sha256"])
