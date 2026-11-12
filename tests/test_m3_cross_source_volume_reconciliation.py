"""Offline negative and observational tests for source-native share-count QA.

No real quote records, live connector calls, client secrets, network, or source
publisher can be created by this module.
"""
from datetime import date
import unittest

from scripts.m3_cross_source_volume_reconciliation import (
    Surface, UntrustedVolumeObservation, reconcile_observed_volumes,
)

D = date(2026, 11, 12)


def obs(source=Surface.SSI_MINUTE_SUM, volume=200, *, atc=None,
        symbol="ABC", day=D, **extra):
    return UntrustedVolumeObservation(source, symbol, day, volume,
                                      atc_volume_shares=atc, **extra)


class SourceVolumeReconciliationTests(unittest.TestCase):
    def test_three_observed_equal_counts_never_grant_source_authority(self):
        r = reconcile_observed_volumes(
            obs(Surface.SSI_MINUTE_SUM, 200, atc=40),
            obs(Surface.DNSE_D1, 200),
            obs(Surface.VCBS_D1, 200),
        )
        self.assertEqual(r["pairwise_disagreement_count"], 0)
        self.assertEqual(r["observed_state"], "OBSERVED_EQUAL_COUNTS_UNTRUSTED")
        self.assertFalse(r["signal_eligible"])
        self.assertFalse(r["production_authorized"])

    def test_four_surface_one_share_difference(self):
        r = reconcile_observed_volumes(
            obs(Surface.SSI_MINUTE_SUM, 200, atc=40),
            obs(Surface.DNSE_D1, 200),
            obs(Surface.VCBS_D1, 199),
            obs(Surface.VCBS_BOARD, 199, atc=39),
        )
        self.assertEqual(r["pairwise_disagreement_count"], 4)
        self.assertEqual(r["observed_state"], "OBSERVED_VOLUME_MISMATCH_QUARANTINE")
        pair = next(p for p in r["pairwise_observations"]
                    if p["left_source"] == Surface.SSI_MINUTE_SUM.value and
                    p["right_source"] == Surface.VCBS_BOARD.value)
        self.assertEqual(pair["left_minus_right_shares"], 1)
        self.assertEqual(pair["left_minus_right_atc_shares"], 1)
        self.assertTrue(pair["session_difference_equals_atc_difference"])
        self.assertFalse(pair["auction_arithmetic_proves_cause"])

    def test_auction_difference_can_disagree_with_session_difference(self):
        r = reconcile_observed_volumes(
            obs(Surface.SSI_MINUTE_SUM, 200, atc=40),
            obs(Surface.VCBS_BOARD, 198, atc=39),
        )
        p = r["pairwise_observations"][0]
        self.assertEqual(p["left_minus_right_shares"], 2)
        self.assertEqual(p["left_minus_right_atc_shares"], 1)
        self.assertFalse(p["session_difference_equals_atc_difference"])

    def test_missing_atc_remains_unknown(self):
        r = reconcile_observed_volumes(
            obs(Surface.SSI_MINUTE_SUM, 200),
            obs(Surface.VCBS_BOARD, 199, atc=39),
        )
        p = r["pairwise_observations"][0]
        self.assertIsNone(p["left_minus_right_atc_shares"])
        self.assertIsNone(p["session_difference_equals_atc_difference"])

    def test_auction_difference_zero_not_publisher_attestation(self):
        r = reconcile_observed_volumes(
            obs(Surface.SSI_MINUTE_SUM, 200, atc=40),
            obs(Surface.VCBS_BOARD, 200, atc=40),
        )
        p = r["pairwise_observations"][0]
        self.assertTrue(p["session_difference_equals_atc_difference"])
        self.assertFalse(p["identical_market_volume_scope_proven"])
        self.assertFalse(r["source_native_closed_bar_verified"])

    def test_four_source_equal_count(self):
        r = reconcile_observed_volumes(
            obs(Surface.SSI_MINUTE_SUM, 0, atc=0),
            obs(Surface.DNSE_D1, 0),
            obs(Surface.VCBS_D1, 0),
            obs(Surface.VCBS_BOARD, 0, atc=0),
        )
        self.assertEqual(len(r["pairwise_observations"]), 6)
        self.assertEqual(r["pairwise_disagreement_count"], 0)
        self.assertFalse(r["complete_market_auction_proof"])

    def test_cannot_call_with_one_source(self):
        with self.assertRaises(ValueError):
            reconcile_observed_volumes(obs())

    def test_cannot_call_with_no_sources(self):
        with self.assertRaises(ValueError):
            reconcile_observed_volumes()

    def test_cannot_call_with_five_sources(self):
        with self.assertRaises(ValueError):
            reconcile_observed_volumes(*(obs() for _ in range(5)))

    def test_duplicate_surface_denied(self):
        with self.assertRaises(ValueError):
            reconcile_observed_volumes(obs(), obs())

    def test_distinct_symbol_denied(self):
        with self.assertRaises(ValueError):
            reconcile_observed_volumes(obs(symbol="ABC"), obs(Surface.DNSE_D1, symbol="XYZ"))

    def test_distinct_day_denied(self):
        with self.assertRaises(ValueError):
            reconcile_observed_volumes(obs(), obs(Surface.DNSE_D1, day=date(2026, 11, 11)))

    def test_record_must_be_typed(self):
        with self.assertRaises(TypeError):
            reconcile_observed_volumes(obs(), {"source": "DNSE", "volume": 200})

    def test_source_enum_cannot_be_str(self):
        with self.assertRaises(TypeError):
            obs("SSI.intraday.minute_volume_sum")

    def test_symbol_must_be_uppercase(self):
        with self.assertRaises(ValueError):
            obs(symbol="abc")

    def test_symbol_disallows_whitespace_and_punctuation(self):
        for value in ("ABC DEF", "ABC-N", "", "A" * 11, "ABC/DEF", 123):
            with self.subTest(value=value), self.assertRaises(ValueError):
                obs(symbol=value)

    def test_day_must_be_exact_date(self):
        for value in ("2026-11-12", None, 20261112, True):
            with self.subTest(value=value), self.assertRaises(TypeError):
                obs(day=value)

    def test_session_volume_must_be_nonnegative_int(self):
        for value in (-1, 200.0, True, None, "200"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                obs(volume=value)

    def test_atc_volume_must_be_nonnegative_integral_subset(self):
        for value in (-1, 201, 2.0, True, "20"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                obs(atc=value)

    def test_no_atc_on_dnse_d1(self):
        with self.assertRaises(ValueError):
            obs(Surface.DNSE_D1, 200, atc=30)

    def test_no_atc_on_vcbs_daily(self):
        with self.assertRaises(ValueError):
            obs(Surface.VCBS_D1, 200, atc=30)

    def test_requires_exact_share_unit(self):
        for unit in ("thousand_shares", "VND", "USD", "share", None, 1000):
            with self.subTest(unit=unit), self.assertRaises(ValueError):
                obs(units=unit)

    def test_spoofed_first_known_claim_denied(self):
        with self.assertRaises(PermissionError):
            obs(first_known_authenticated=True)

    def test_spoofed_publisher_claim_denied(self):
        with self.assertRaises(PermissionError):
            obs(independent_issuer_authenticated=True)

    def test_spoofed_volume_scope_claim_denied(self):
        with self.assertRaises(PermissionError):
            obs(provider_volume_scope_verified=True)

    def test_spoofed_vendor_retention_rights_denied(self):
        with self.assertRaises(PermissionError):
            obs(source_retention_approved_by_vendor=True)

    def test_no_price_arrays_or_credentials_in_report(self):
        r = reconcile_observed_volumes(obs(), obs(Surface.VCBS_D1))
        for forbidden in ("open", "high", "low", "close", "api_key", "token", "secret",
                          "issuer_signature", "quote_rows"):
            self.assertNotIn(forbidden, r)

    def test_sorted_report_identical_for_reversed_input(self):
        a = obs(Surface.SSI_MINUTE_SUM, 200, atc=40)
        b = obs(Surface.DNSE_D1, 200)
        c = obs(Surface.VCBS_D1, 199)
        self.assertEqual(reconcile_observed_volumes(a, b, c),
                         reconcile_observed_volumes(c, a, b))

    def test_negative_pairwise_difference_is_not_clamped(self):
        r = reconcile_observed_volumes(
            obs(Surface.SSI_MINUTE_SUM, 198),
            obs(Surface.VCBS_BOARD, 200, atc=40),
        )
        self.assertEqual(r["pairwise_observations"][0]["left_minus_right_shares"], -2)

    def test_two_source_mismatch_still_not_trading(self):
        r = reconcile_observed_volumes(
            obs(Surface.SSI_MINUTE_SUM, 200),
            obs(Surface.DNSE_D1, 201),
        )
        self.assertFalse(r["cache_v2_authorized"])
        self.assertFalse(r["licensed_persistent_retention_verified"])
        self.assertEqual(r["pairwise_disagreement_count"], 1)

    def test_different_feed_family_is_observation_not_verification(self):
        r = reconcile_observed_volumes(
            obs(Surface.SSI_MINUTE_SUM, 200),
            obs(Surface.DNSE_D1, 200),
        )
        self.assertFalse(r["provider_scope_equivalence_verified"])
        self.assertFalse(r["issuer_source_and_first_known_verified"])


if __name__ == "__main__":
    unittest.main()
