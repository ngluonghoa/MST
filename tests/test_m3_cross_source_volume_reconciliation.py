"""Offline negative and observational tests for source-native share-count QA.

No real quote records, live connector calls, client secrets, network, or source
publisher can be created by this module.
"""
from datetime import date, datetime, timedelta, timezone
import unittest

from scripts.m3_cross_source_volume_reconciliation import (
    Surface, UntrustedVolumeObservation, reconcile_observed_volumes, compare_volume_refreshes,
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



def receipt_clock(h: int = 10):
    return datetime(2026, 11, 12, h, 0, tzinfo=timezone.utc)


class SourceVolumeRefreshReceiptTests(unittest.TestCase):
    def test_repeated_disagreement_never_promoted_to_cache(self):
        prev = (obs(Surface.SSI_MINUTE_SUM, 200, atc=40),
                obs(Surface.DNSE_D1, 200),
                obs(Surface.VCBS_D1, 199),
                obs(Surface.VCBS_BOARD, 199, atc=39))
        result = compare_volume_refreshes(
            prev, prev, previous_received_utc=receipt_clock(),
            current_received_utc=receipt_clock(11))
        self.assertTrue(result["observed_disagreement_persists"])
        self.assertEqual(result["changed_source_surfaces"], [])
        self.assertEqual(result["source_qa_action"], "QUARANTINE_PROVIDER_VOLUME_CONFLICT")
        self.assertEqual(result["incremental_candidate_action"],
                         "RECORD_RECHECK_RECEIPT_WITHOUT_VOLUME_REVISION")
        self.assertFalse(result["approved_market_cache_write"])

    def test_new_vendor_volume_delta_triggers_dependency_invalidating_candidate(self):
        prev = (obs(Surface.SSI_MINUTE_SUM, 200), obs(Surface.DNSE_D1, 200))
        new = (obs(Surface.SSI_MINUTE_SUM, 200), obs(Surface.DNSE_D1, 201))
        out = compare_volume_refreshes(
            prev, new, previous_received_utc=receipt_clock(),
            current_received_utc=receipt_clock(11))
        self.assertEqual(out["changed_source_surfaces"], [Surface.DNSE_D1.value])
        self.assertEqual(out["incremental_candidate_action"],
                         "RECORD_VOLUME_REVISION_AND_INVALIDATE_RESEARCH_DEPENDENCIES")
        self.assertTrue(out["observed_new_disagreement"])
        self.assertFalse(out["signal_eligible"])

    def test_atc_only_revision_is_a_real_source_count_revision(self):
        prev = (obs(Surface.SSI_MINUTE_SUM, 200, atc=40),
                obs(Surface.VCBS_BOARD, 200, atc=40))
        new = (obs(Surface.SSI_MINUTE_SUM, 200, atc=41),
               obs(Surface.VCBS_BOARD, 200, atc=40))
        result = compare_volume_refreshes(
            prev, new, previous_received_utc=receipt_clock(),
            current_received_utc=receipt_clock(11))
        item = result["sources"][0]
        self.assertEqual(item["observed_volume_delta_shares"], 0)
        self.assertEqual(item["atc_delta_shares_if_both_present"], 1)
        self.assertTrue(item["source_counts_changed"])
        self.assertIn(Surface.SSI_MINUTE_SUM.value, result["changed_source_surfaces"])

    def test_new_atc_field_with_unchanged_total_still_triggers_qa(self):
        prev = (obs(Surface.SSI_MINUTE_SUM, 200),
                obs(Surface.VCBS_BOARD, 200, atc=39))
        new = (obs(Surface.SSI_MINUTE_SUM, 200, atc=40),
               obs(Surface.VCBS_BOARD, 200, atc=39))
        result = compare_volume_refreshes(
            prev, new, previous_received_utc=receipt_clock(),
            current_received_utc=receipt_clock(11))
        self.assertTrue(result["sources"][0]["atc_presence_or_value_changed"])
        self.assertIsNone(result["sources"][0]["atc_delta_shares_if_both_present"])

    def test_disagreement_clearing_is_not_finality(self):
        prior = (obs(Surface.SSI_MINUTE_SUM, 200),
                 obs(Surface.VCBS_D1, 199))
        now = (obs(Surface.SSI_MINUTE_SUM, 200),
               obs(Surface.VCBS_D1, 200))
        out = compare_volume_refreshes(
            prior, now, previous_received_utc=receipt_clock(),
            current_received_utc=receipt_clock(11))
        self.assertTrue(out["observed_disagreement_numerically_cleared"])
        self.assertEqual(out["source_qa_action"], "OBSERVED_NUMERIC_AGREEMENT_ONLY")
        self.assertFalse(out["signed_issuer_revision_verified"])
        self.assertFalse(out["production_authorized"])

    def test_identical_counts_never_prove_same_ohlcv(self):
        rec = (obs(Surface.SSI_MINUTE_SUM, 200),
               obs(Surface.DNSE_D1, 200))
        out = compare_volume_refreshes(
            rec, rec, previous_received_utc=receipt_clock(),
            current_received_utc=receipt_clock(11))
        self.assertFalse(out["matching_volume_proves_identical_ohlcv"])
        self.assertFalse(out["source_clock_is_publisher_first_known"])
        self.assertTrue(all(not item["entire_ohlcv_history_identical_proven"]
                            for item in out["sources"]))

    def test_reversed_input_provider_order_produces_same_source_order(self):
        a, b = obs(Surface.SSI_MINUTE_SUM, 200), obs(Surface.DNSE_D1, 200)
        out = compare_volume_refreshes(
            (a,b), (b,a), previous_received_utc=receipt_clock(),
            current_received_utc=receipt_clock(11))
        self.assertEqual([p["source"] for p in out["sources"]],
                         [Surface.SSI_MINUTE_SUM.value, Surface.DNSE_D1.value])
        self.assertEqual(out["changed_source_surfaces"], [])

    def test_mismatched_provider_sets_refused(self):
        with self.assertRaises(ValueError):
            compare_volume_refreshes(
                (obs(Surface.SSI_MINUTE_SUM), obs(Surface.DNSE_D1)),
                (obs(Surface.SSI_MINUTE_SUM), obs(Surface.VCBS_D1)),
                previous_received_utc=receipt_clock(),
                current_received_utc=receipt_clock(11))

    def test_mismatched_symbol_refused(self):
        with self.assertRaises(ValueError):
            compare_volume_refreshes(
                (obs(symbol="ABC"), obs(Surface.DNSE_D1, symbol="ABC")),
                (obs(symbol="XYZ"), obs(Surface.DNSE_D1, symbol="XYZ")),
                previous_received_utc=receipt_clock(),
                current_received_utc=receipt_clock(11))

    def test_mismatched_trading_date_refused(self):
        tomorrow=date(2026, 11, 13)
        with self.assertRaises(ValueError):
            compare_volume_refreshes(
                (obs(), obs(Surface.DNSE_D1)),
                (obs(day=tomorrow), obs(Surface.DNSE_D1, day=tomorrow)),
                previous_received_utc=receipt_clock(),
                current_received_utc=receipt_clock(11))

    def test_wrong_input_shapes_refused(self):
        a=obs()
        b=obs(Surface.DNSE_D1)
        for previous,current in (([a,b],(a,b)),((a,b),[a,b]),((a,b),{})):
            with self.subTest(previous=type(previous).__name__,
                              current=type(current).__name__), self.assertRaises(TypeError):
                compare_volume_refreshes(
                    previous,current,previous_received_utc=receipt_clock(),
                    current_received_utc=receipt_clock(11))

    def test_missing_utc_clock_rejected(self):
        values=(obs(),obs(Surface.DNSE_D1))
        for stamp in (None, "2026-11-12", datetime(2026,11,12,10),
                      datetime(2026,11,12,10,tzinfo=timezone(timedelta(hours=7)))):
            with self.subTest(stamp=repr(stamp)), self.assertRaises(ValueError):
                compare_volume_refreshes(
                    values,values,previous_received_utc=stamp,
                    current_received_utc=receipt_clock(11))

    def test_nonmonotone_receipt_refused(self):
        values=(obs(),obs(Surface.DNSE_D1))
        for new_time in (receipt_clock(), receipt_clock(9)):
            with self.subTest(clock=new_time), self.assertRaises(ValueError):
                compare_volume_refreshes(
                    values,values,previous_received_utc=receipt_clock(),
                    current_received_utc=new_time)

    def test_duplicate_surface_in_single_receipt_refused(self):
        values=(obs(),obs())
        with self.assertRaises(ValueError):
            compare_volume_refreshes(
                values,values,previous_received_utc=receipt_clock(),
                current_received_utc=receipt_clock(11))

    def test_all_four_surfaces_unchanged_deterministic(self):
        prev=(obs(Surface.VCBS_BOARD, 199, atc=39),
              obs(Surface.VCBS_D1,199),
              obs(Surface.DNSE_D1,200),
              obs(Surface.SSI_MINUTE_SUM,200,atc=40))
        out = compare_volume_refreshes(
            prev, tuple(reversed(prev)),
            previous_received_utc=receipt_clock(),
            current_received_utc=receipt_clock(11))
        self.assertEqual(len(out["sources"]),4)
        self.assertEqual(len(out["changed_source_surfaces"]),0)
        self.assertEqual(out["current_disagreement_pair_count"],4)
        self.assertEqual(out["incremental_candidate_action"],
                         "RECORD_RECHECK_RECEIPT_WITHOUT_VOLUME_REVISION")

    def test_trusted_publisher_flag_cannot_be_set_through_refresh(self):
        a,b=obs(),obs(Surface.DNSE_D1)
        with self.assertRaises(PermissionError):
            bad=obs(Surface.VCBS_D1, independent_issuer_authenticated=True)
            compare_volume_refreshes(
                (a,b),(a,b,bad),previous_received_utc=receipt_clock(),
                current_received_utc=receipt_clock(11))


if __name__ == "__main__":
    unittest.main()
