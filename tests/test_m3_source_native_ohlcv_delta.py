"""Negative and numeric/metadata separation tests for endpoint-native D1 deltas.

All rows are fabricated TEST FIXTURES. Never feed real vendor price values into
this public GitHub repo or infer source publication/rights from these tests.
"""
from datetime import datetime, timedelta, timezone
import unittest

from scripts.m3_source_native_ohlcv_delta import (
    DailyEndpoint, NativeD1Snapshot, diff_native_d1_versions,
)

T0=datetime(2026,11,12,10,tzinfo=timezone.utc)
T1=datetime(2026,11,12,11,tzinfo=timezone.utc)


def ssi(day="12/11/2026", **override):
    d={"symbol":"ABC","trading_date":day,"open":"100","high":"104",
       "low":"99","close":"102","volume":"200"}
    d.update(override)
    return d


def dnse(day="2026-11-12", **override):
    d={"date_utc":day,"source_unix_seconds":1794448800,
       "open":1,"high":1.04,"low":0.99,"close":1.02,"volume":200}
    d.update(override)
    return d


def vcbs(day="2026-11-12", **override):
    d={"tradingDate":day,"openPrice":100,"highPrice":104,"lowPrice":99,
       "closePrice":102,"volume":200,"adjClosePrice":102,
       "adjFactor":1,"price":102,"priceBasis":"adjusted",
       "trading_value_scope":None}
    d.update(override)
    return d


def snap(rows, *, endpoint=DailyEndpoint.SSI_COMPACT, t=T0,
         symbol="ABC", basis="adjusted", unit="VND_per_share", **extra):
    return NativeD1Snapshot(
        endpoint=endpoint,symbol=symbol,price_basis=basis,unit=unit,
        observed_at_utc=t,rows=tuple(rows),**extra
    )


def compare(rows0, rows1, **kwargs):
    return diff_native_d1_versions(
        snap(rows0,**kwargs),snap(rows1,t=T1,**kwargs)
    )


class NativeOHLCVRevisionTests(unittest.TestCase):
    def test_same_numeric_strings_and_integer_values_are_equal(self):
        d=compare([ssi()],[ssi(open=100,high=104.0,low=99,close=102,volume=200)])
        self.assertEqual(d["unchanged_rows"],1)
        self.assertEqual(d["numeric_ohlcv_revisions"],[])
        self.assertFalse(d["signal_eligible"])

    def test_changed_close_without_volume_change_invalidate(self):
        d=compare([ssi()],[ssi(close="103")])
        self.assertEqual(d["numeric_ohlcv_revisions"],
                         [{"day":"2026-11-12","changed_fields":["close"]}])
        self.assertEqual(d["affected_research_day_labels"],["2026-11-12"])
        self.assertEqual(d["recommendation"],
                         "REBUILD_DEPENDENT_RESEARCH_CANDIDATES_AFTER_NEW_VERSION")

    def test_changed_volume_without_price_change_detected(self):
        d=compare([ssi()],[ssi(volume="201")])
        self.assertEqual(d["numeric_ohlcv_revisions"][0]["changed_fields"],["volume"])

    def test_open_high_low_close_all_changed(self):
        d=compare([ssi()],[ssi(open="101",high="105",low="98",close="103")])
        self.assertEqual(d["numeric_ohlcv_revisions"][0]["changed_fields"],
                         ["open","high","low","close"])

    def test_absent_vs_null_metadata_only_not_price_revision(self):
        old=vcbs()
        new=vcbs()
        del new["trading_value_scope"]
        d=compare([old],[new],endpoint=DailyEndpoint.VCBS_DAILY)
        self.assertEqual(d["numeric_ohlcv_revisions"],[])
        self.assertEqual(d["adjustment_or_price_basis_revisions"],[])
        self.assertEqual(d["metadata_changes_only_or_in_addition"],
                         [{"day":"2026-11-12","changed_fields":["trading_value_scope"],
                           "absent_vs_null_only":True}])
        self.assertEqual(d["affected_research_day_labels"],[])
        self.assertEqual(d["recommendation"],
                         "SOURCE_RECEIPT_ONLY_NO_NUMERIC_OR_ADJUSTMENT_REVISION_OBSERVED")

    def test_changed_nonnull_metadata_does_not_invalidate_price(self):
        d=compare([vcbs(source="board_supplement")],
                  [vcbs(source="historical")],endpoint=DailyEndpoint.VCBS_DAILY)
        self.assertFalse(d["metadata_changes_only_or_in_addition"][0]["absent_vs_null_only"])
        self.assertEqual(d["affected_research_day_labels"],[])

    def test_adj_close_revision_invalidates_without_core_change(self):
        d=compare([vcbs()],[vcbs(adjClosePrice=101)],
                  endpoint=DailyEndpoint.VCBS_DAILY)
        self.assertEqual(d["numeric_ohlcv_revisions"],[])
        self.assertEqual(d["adjustment_or_price_basis_revisions"][0]["changed_fields"],
                         ["adjClosePrice"])
        self.assertEqual(d["affected_research_day_labels"],["2026-11-12"])

    def test_adjustment_factor_revision_is_separate(self):
        d=compare([vcbs()],[vcbs(adjFactor=0.95)],
                  endpoint=DailyEndpoint.VCBS_DAILY)
        self.assertEqual(d["adjustment_or_price_basis_revisions"][0]["changed_fields"],
                         ["adjFactor"])

    def test_price_basis_revision_is_distinct_from_metadata(self):
        d=compare([vcbs()],[vcbs(priceBasis="raw")],
                  endpoint=DailyEndpoint.VCBS_DAILY)
        self.assertEqual(d["adjustment_or_price_basis_revisions"][0]["changed_fields"],
                         ["priceBasis"])

    def test_optional_aux_missing_and_null_equivalent(self):
        before=ssi()
        after=ssi(close_price_adjusted=None)
        d=compare([before],[after],endpoint=DailyEndpoint.SSI_DETAILED)
        self.assertEqual(d["adjustment_or_price_basis_revisions"],[])
        self.assertEqual(d["metadata_changes_only_or_in_addition"],[])

    def test_detailed_ssi_raw_change_only_is_revision(self):
        d=compare([ssi(close_raw="102")],[ssi(close_raw="101")],
                  endpoint=DailyEndpoint.SSI_DETAILED)
        self.assertEqual(d["numeric_ohlcv_revisions"],[])
        self.assertEqual(d["adjustment_or_price_basis_revisions"][0]["changed_fields"],
                         ["close_raw"])

    def test_dnse_native_numeric_untouched_without_cross_source_scale(self):
        d=compare([dnse()],[dnse(open="1.00",high="1.04",low="0.990",close="1.020")],
                  endpoint=DailyEndpoint.DNSE_CONNECTED_DAY,basis="source_native",unit="native_unverified")
        self.assertEqual(d["numeric_ohlcv_revisions"],[])
        self.assertTrue(d["cross_provider_comparison_not_performed"])

    def test_dnse_different_timestamp_date_rejected(self):
        with self.assertRaises(ValueError):
            snap([dnse(day="2026-11-11")],endpoint=DailyEndpoint.DNSE_CONNECTED_DAY)

    def test_dnse_missing_timestamp_rejected(self):
        d=dnse()
        del d["source_unix_seconds"]
        with self.assertRaises(ValueError):
            snap([d],endpoint=DailyEndpoint.DNSE_CONNECTED_DAY)

    def test_dnse_bad_timestamp_type_rejected(self):
        with self.assertRaises(ValueError):
            snap([dnse(source_unix_seconds="1794448800")],
                 endpoint=DailyEndpoint.DNSE_CONNECTED_DAY)

    def test_add_new_session_does_not_claim_closed(self):
        d=compare([ssi(day="11/11/2026")],
                  [ssi(day="11/11/2026"),ssi(day="12/11/2026")])
        self.assertEqual(d["added_day_labels"],["2026-11-12"])
        self.assertFalse(d["session_closed_issuer_verified"])
        self.assertFalse(d["automatic_cache_v2_write_authorized"])

    def test_missing_prior_day_is_unverified_not_authorized_delete(self):
        d=compare([ssi(day="11/11/2026"),ssi(day="12/11/2026")],
                  [ssi(day="12/11/2026")])
        self.assertEqual(d["missing_prior_day_labels_UNVERIFIED"],["2026-11-11"])
        self.assertTrue(d["missing_prior_rows_may_be_window_or_source_scope"])
        self.assertFalse(d["deletion_authorized"])

    def test_same_day_reordered_rows_not_revision(self):
        old=[ssi("11/11/2026"),ssi("12/11/2026")]
        d=compare(old,old[::-1])
        self.assertEqual(d["unchanged_rows"],2)
        self.assertEqual(d["affected_research_day_labels"],[])

    def test_duplicate_day_rejected(self):
        with self.assertRaises(ValueError):
            snap([ssi(),ssi()])

    def test_different_endpoints_never_compared(self):
        with self.assertRaises(ValueError):
            diff_native_d1_versions(
                snap([ssi()],endpoint=DailyEndpoint.SSI_COMPACT),
                snap([ssi()],endpoint=DailyEndpoint.SSI_DETAILED,t=T1))

    def test_source_unit_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            diff_native_d1_versions(snap([ssi()]),
                                    snap([ssi()],t=T1,unit="thousand_VND"))

    def test_price_basis_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            diff_native_d1_versions(snap([ssi()]),
                                    snap([ssi()],t=T1,basis="raw"))

    def test_symbol_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            diff_native_d1_versions(snap([ssi()]),
                                    snap([ssi()],t=T1,symbol="XYZ"))

    def test_utc_nonmonotone_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            diff_native_d1_versions(snap([ssi()]),
                                    snap([ssi()],t=T0))

    def test_non_utc_local_receipt_rejected(self):
        with self.assertRaises(ValueError):
            snap([ssi()],t=datetime(2026,11,12,11,tzinfo=timezone(timedelta(hours=7))))

    def test_missing_tz_refused(self):
        with self.assertRaises(ValueError):
            snap([ssi()],t=datetime(2026,11,12,11))

    def test_self_attested_rights_denied(self):
        with self.assertRaises(PermissionError):
            snap([ssi()],licensed_publisher_verified=True)

    def test_self_attested_first_known_denied(self):
        with self.assertRaises(PermissionError):
            snap([ssi()],issuer_first_known_verified=True)

    def test_invalid_symbol_denied(self):
        for symbol in ("abc","ABC-DEF","",123,"X"*11):
            with self.subTest(symbol=symbol),self.assertRaises(ValueError):
                snap([ssi()],symbol=symbol)

    def test_invalid_provider_type_denied(self):
        with self.assertRaises(TypeError):
            snap([ssi()],endpoint="SSI.marketdata_list_stock_daily_data")

    def test_intraday_timeframe_promotion_denied(self):
        with self.assertRaises(ValueError):
            snap([ssi()],timeframe="M5")

    def test_negative_volume_rejected(self):
        with self.assertRaises(ValueError):
            snap([ssi(volume="-1")])

    def test_fractional_volume_rejected(self):
        with self.assertRaises(ValueError):
            snap([ssi(volume="201.5")])

    def test_boolean_volume_rejected(self):
        with self.assertRaises(ValueError):
            snap([ssi(volume=True)])

    def test_nonfinite_price_rejected(self):
        for close in ("NaN","Infinity","-Infinity"):
            with self.subTest(close=close),self.assertRaises(ValueError):
                snap([ssi(close=close)])

    def test_invalid_ohlc_low_high_rejected(self):
        with self.assertRaises(ValueError):
            snap([ssi(high="98")])

    def test_invalid_date_rejected(self):
        with self.assertRaises(ValueError):
            snap([ssi(day="31/02/2026")])

    def test_different_session_day_labels_are_independent(self):
        d=compare([ssi(day="11/11/2026")],[ssi(day="12/11/2026")])
        self.assertEqual(d["added_day_labels"],["2026-11-12"])
        self.assertEqual(d["missing_prior_day_labels_UNVERIFIED"],["2026-11-11"])

    def test_metadata_and_numeric_changes_kept_separate(self):
        old=vcbs(trading_value_scope=None)
        new=vcbs(closePrice=103)
        del new["trading_value_scope"]
        d=compare([old],[new],endpoint=DailyEndpoint.VCBS_DAILY)
        self.assertEqual(d["numeric_ohlcv_revisions"][0]["changed_fields"],["close"])
        self.assertTrue(d["metadata_changes_only_or_in_addition"][0]["absent_vs_null_only"])

    def test_no_real_prices_in_report(self):
        d=compare([ssi()],[ssi(close="103")])
        for forbidden in ("source_rows","old_ohlcv","new_ohlcv","password","api_key"):
            self.assertNotIn(forbidden,d)
        self.assertFalse(d["production_authorized"])



    def test_dnse_same_day_source_start_revision_invalidates(self):
        before=dnse()
        after=dnse(source_unix_seconds=1794448860)
        d=compare([before],[after],endpoint=DailyEndpoint.DNSE_CONNECTED_DAY,
                  basis="source_native",unit="native_unverified")
        self.assertEqual(d["numeric_ohlcv_revisions"],[])
        self.assertEqual(d["source_candle_start_timestamp_revisions"],
                         [{"day":"2026-11-12",
                           "changed_fields":["source_unix_seconds"]}])
        self.assertEqual(d["affected_research_day_labels"],["2026-11-12"])
        self.assertEqual(d["unchanged_rows"],0)

    def test_dnse_same_timestamp_no_revision(self):
        d=compare([dnse()],[dnse()],endpoint=DailyEndpoint.DNSE_CONNECTED_DAY,
                  basis="source_native",unit="native_unverified")
        self.assertEqual(d["source_candle_start_timestamp_revisions"],[])
        self.assertEqual(d["unchanged_rows"],1)

    def test_dnse_source_start_does_not_become_issuer_first_known(self):
        d=compare([dnse()],[dnse(source_unix_seconds=1794448860)],
                  endpoint=DailyEndpoint.DNSE_CONNECTED_DAY,
                  basis="source_native",unit="native_unverified")
        self.assertFalse(d["source_first_known_authenticated"])
        self.assertFalse(d["automatic_cache_v2_write_authorized"])

if __name__ == "__main__":
    unittest.main()
