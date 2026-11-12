"""Negative-only metadata source-finality regression; no provider IO."""
import unittest
from datetime import date, datetime
from scripts.m3_cross_surface_finality_gate import (
    Endpoint, Observation, classify, reconcile, example
)


D = date(2026, 11, 12)


class CrossSurfaceFinalityTests(unittest.TestCase):
    def test_vcbs_d1_true_is_provisional(self):
        o = Observation(Endpoint.VCBS_D1, D, True, True)
        self.assertEqual(classify(o)["observed_state"], "EXPLICIT_VCBS_D1_PROVISIONAL")

    def test_vcbs_board_false_is_not_d1_closure(self):
        o = Observation(Endpoint.VCBS_INTRADAY_BOARD, D, True, False)
        c = classify(o)
        self.assertEqual(c["observed_state"], "VCBS_BOARD_OHLC_HINT_ONLY")
        self.assertFalse(c["closed_bar_verified"])

    def test_vcbs_board_true_still_not_signal(self):
        o = Observation(Endpoint.VCBS_INTRADAY_BOARD, D, True, True)
        self.assertFalse(classify(o)["signal_eligible"])

    def test_d1_false_is_unqualified_hint(self):
        c = classify(Observation(Endpoint.VCBS_D1, D, True, False))
        self.assertEqual(c["observed_state"], "NONPROVISIONAL_HINT_UNQUALIFIED")
        self.assertFalse(c["cache_publish_authorized"])

    def test_d1_missing_marker_is_not_false(self):
        c = classify(Observation(Endpoint.VCBS_D1, D))
        self.assertEqual(c["observed_state"], "NO_EXPLICIT_FINALITY_FIELD")

    def test_dnse_d1_date_or_timestamp_does_not_prove_close(self):
        c = classify(Observation(Endpoint.DNSE_D1, D))
        self.assertFalse(c["closed_bar_verified"])
        self.assertFalse(c["publisher_first_known_verified"])

    def test_ssi_latest_quote_cannot_verify_m5_close(self):
        c = classify(Observation(Endpoint.SSI_INTRADAY_LATEST, D))
        self.assertEqual(c["claim_scope"], "INTRADAY_REFERENCE")
        self.assertFalse(c["signal_eligible"])

    def test_same_provider_cross_surface_disagreement_denied(self):
        a = Observation(Endpoint.VCBS_D1, D, True, True)
        b = Observation(Endpoint.VCBS_INTRADAY_BOARD, D, True, False)
        r = reconcile(a, b)
        self.assertFalse(r["can_borrow_finality_between_endpoints"])
        self.assertEqual(r["decision"], "NO_GO_CROSS_SURFACE_FINALITY_NOT_TRANSFERABLE")

    def test_flip_arguments_cannot_change_authority(self):
        a = Observation(Endpoint.VCBS_D1, D, True, True)
        b = Observation(Endpoint.VCBS_INTRADAY_BOARD, D, True, False)
        for x, y in ((a, b), (b, a)):
            self.assertFalse(reconcile(x, y)["source_closed_bar_verified"])

    def test_cross_provider_d1_not_equal_vendor_proof(self):
        a = Observation(Endpoint.SSI_D1, D)
        b = Observation(Endpoint.DNSE_D1, D)
        self.assertFalse(reconcile(a, b)["source_entitlement_verified"])

    def test_vcbs_d1_and_dnse_d1_cannot_confirm_each_other(self):
        a = Observation(Endpoint.VCBS_D1, D, True, False)
        b = Observation(Endpoint.DNSE_D1, D)
        self.assertFalse(reconcile(a, b)["cache_publish_authorized"])

    def test_different_day_rejected(self):
        with self.assertRaisesRegex(ValueError, "SAME_TRADING_DAY"):
            reconcile(Observation(Endpoint.VCBS_D1, D),
                      Observation(Endpoint.DNSE_D1, date(2026, 11, 11)))

    def test_same_endpoint_rejected(self):
        with self.assertRaisesRegex(ValueError, "DISTINCT_ENDPOINTS"):
            reconcile(Observation(Endpoint.SSI_D1, D), Observation(Endpoint.SSI_D1, D))

    def test_marker_missing_value_cannot_be_true(self):
        with self.assertRaisesRegex(ValueError, "ABSENT_MARKER"):
            Observation(Endpoint.VCBS_D1, D, False, True)

    def test_marker_present_must_be_bool(self):
        for x in (None, 0, 1, "false", "true", {}):
            with self.subTest(x=x), self.assertRaises(TypeError):
                Observation(Endpoint.VCBS_D1, D, True, x)

    def test_unrecognized_marker_for_other_provider_rejected(self):
        with self.assertRaisesRegex(ValueError, "ENDPOINT_DOES_NOT_SUPPLY"):
            Observation(Endpoint.DNSE_D1, D, True, False)

    def test_no_self_attested_issuer_finality(self):
        with self.assertRaises(PermissionError):
            Observation(Endpoint.VCBS_D1, D, True, False, issuer_finality_authenticated=True)

    def test_no_self_attested_retention_rights(self):
        with self.assertRaises(PermissionError):
            Observation(Endpoint.VCBS_D1, D, retention_authorized=True)

    def test_datetime_is_not_a_trading_day(self):
        with self.assertRaises(TypeError):
            Observation(Endpoint.VCBS_D1, datetime(2026, 11, 12))

    def test_bad_endpoint_cannot_be_blessed(self):
        with self.assertRaises(TypeError):
            Observation("VCBS.vcbs_get_history.D", D)

    def test_fake_evidence_mapping_not_accepted(self):
        with self.assertRaises(TypeError):
            classify({"endpoint": Endpoint.VCBS_D1, "marker": False})

    def test_example_always_no_go(self):
        r = example()
        self.assertEqual(r["decision"], "NO_GO_CROSS_SURFACE_FINALITY_NOT_TRANSFERABLE")
        self.assertFalse(r["signal_eligible"])
        self.assertFalse(r["cache_publish_authorized"])


if __name__ == "__main__":
    unittest.main()
