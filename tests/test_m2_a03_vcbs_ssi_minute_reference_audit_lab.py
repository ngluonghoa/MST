"""40 wholly fictional VCBS/SSI clock-price reference non-promotion tests."""
import copy
import unittest

from scripts.m2_a03_vcbs_ssi_minute_reference_audit_lab import (
    SCHEMA,STATUS,MAX_POINTS,fake_source_fixture,synthetic_receipt,
    compare_untrusted_price_references,
)


class VcbsSsiMinuteReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=synthetic_receipt()

    def sample(self):
        return copy.deepcopy(fake_source_fixture())

    def compare(self,vcbs=None,ssi=None,**kwargs):
        a,b=self.sample()
        return compare_untrusted_price_references(
            a if vcbs is None else vcbs,b if ssi is None else ssi,
            symbol=kwargs.get("symbol","XYZ"),
            local_date=kwargs.get("local_date","14/10/2025"))

    def bad(self,changer,exc,needle):
        a,b=self.sample()
        changer(a,b)
        with self.assertRaisesRegex(exc,needle):
            self.compare(a,b)

    def test_01_schema(self):
        self.assertEqual(self.receipt["schema"],SCHEMA)
    def test_02_no_go_status(self):
        self.assertEqual(self.receipt["status"],STATUS)
    def test_03_three_matching_clock_labels(self):
        self.assertEqual(self.receipt["clock_labels_aligned"],3)
    def test_04_two_matching_reference_prices(self):
        self.assertEqual(self.receipt["identical_reference_prices"],2)
    def test_05_one_disagreeing_reference_price(self):
        self.assertEqual(self.receipt["unequal_reference_prices"],1)
    def test_06_actual_market_data_not_present_in_receipt(self):
        self.assertNotIn("prices",self.receipt)
        self.assertNotIn("trading_date",self.receipt)
        self.assertNotIn("source_hashes",self.receipt)
    def test_07_untrusted_disagreement_quarantined(self):
        self.assertEqual(self.receipt["reference_comparison"],
                         "UNTRUSTED_PRICE_MISMATCH_QUARANTINE")
    def test_08_one_synthetic_price_fixed_yields_only_reference(self):
        a,b=self.sample()
        a["series"][1]["price"]=101
        r=self.compare(a,b)
        self.assertEqual(r["identical_reference_prices"],3)
        self.assertEqual(r["reference_comparison"],"UNTRUSTED_PRICE_COINCIDENCE_ONLY")
        self.assertFalse(r["vcbs_native_m5_m15_m30_h1_h4_ohlcv_verified"])
    def test_09_price_mismatch_count_additive(self):
        a,b=self.sample()
        a["series"][2]["price"]=105
        self.assertEqual(self.compare(a,b)["unequal_reference_prices"],2)
    def test_10_vcbs_partial_clock_coverage_is_not_filled(self):
        a,b=self.sample()
        a["series"].pop()
        r=self.compare(a,b)
        self.assertEqual(r["ssi_unmatched_clock_count"],1)
        self.assertEqual(r["vcbs_unmatched_clock_count"],0)
        self.assertFalse(r["vcbs_m1_to_m5_aggregation_authorized"])
    def test_11_ssi_partial_clock_coverage_is_not_filled(self):
        a,b=self.sample()
        b.pop()
        r=self.compare(a,b)
        self.assertEqual(r["vcbs_unmatched_clock_count"],1)
        self.assertEqual(r["ssi_unmatched_clock_count"],0)
    def test_12_session_volume_not_minute_volume(self):
        self.assertTrue(self.receipt["vcbs_top_level_volume_is_session_cumulative_only"])
        self.assertFalse(self.receipt["vcbs_per_minute_open_high_low_close_volume_available"])
    def test_13_session_board_not_m5_bar(self):
        self.assertFalse(self.receipt["vcbs_native_m5_m15_m30_h1_h4_ohlcv_verified"])
    def test_14_session_board_closed_flag_not_m5_closure(self):
        self.assertFalse(self.receipt["vcbs_session_board_ohlc_provisional_flag"])
        self.assertFalse(self.receipt["vcbs_native_m5_m15_m30_h1_h4_ohlcv_verified"])
    def test_15_even_true_ohlc_provisional_no_promotion(self):
        a,b=self.sample()
        a["ohlcProvisional"]=True
        self.assertFalse(self.compare(a,b)["cloud_cache_or_trading_authorized"])
    def test_16_no_market_calendar_authority(self):
        self.assertFalse(self.receipt["calendar_auctions_halts_trading_sessions_verified"])
    def test_17_no_publisher_time_label_authority(self):
        self.assertFalse(self.receipt["ssi_provider_m1_timestamp_start_end_authenticated"])
    def test_18_no_first_known_revision_authority(self):
        self.assertFalse(self.receipt["correction_first_known_source_clock_authenticated"])
    def test_19_no_vendor_rights(self):
        self.assertFalse(self.receipt["vendor_google_drive_retention_license_proven"])
    def test_20_no_github_runner_source_entitlement(self):
        self.assertFalse(self.receipt["github_runner_authenticated_source_access_proven"])
    def test_21_no_trading_or_cache(self):
        self.assertFalse(self.receipt["cloud_cache_or_trading_authorized"])
    def test_22_vcbs_wrong_symbol_denied(self):
        self.bad(lambda a,b:a.update(secCode="OTHER"),PermissionError,"VCBS_SOURCE_SYMBOL")
    def test_23_ssi_wrong_symbol_denied(self):
        self.bad(lambda a,b:b[0].update(symbol="OTHER"),PermissionError,"SSI_PROVIDER_SYMBOL")
    def test_24_no_data_vcbs_denied(self):
        self.bad(lambda a,b:a.update(data_status="no_data"),PermissionError,"VCBS_REFERENCE_NOT_AVAILABLE")
    def test_25_wrong_session_ohlc_source_denied(self):
        self.bad(lambda a,b:a.update(ohlcSource="fake_m5"),PermissionError,"VCBS_EXPECTED_SESSION")
    def test_26_unverified_session_volume_scope_denied(self):
        self.bad(lambda a,b:a.update(recent_volume_scope="unknown"),PermissionError,"VCBS_SESSION_VOLUME_SCOPE")
    def test_27_wrong_price_unit_denied(self):
        self.bad(lambda a,b:a.update(price_unit="thousands"),PermissionError,"VCBS_REFERENCE_UNIT")
    def test_28_wrong_volume_unit_denied(self):
        self.bad(lambda a,b:a.update(volume_unit="lot"),PermissionError,"VCBS_REFERENCE_UNIT")
    def test_29_source_injected_minute_ohlc_denied(self):
        self.bad(lambda a,b:a["series"][0].update(open=100),PermissionError,"VCBS_POINT_ONLY")
    def test_30_source_injected_minute_volume_denied(self):
        self.bad(lambda a,b:a["series"][0].update(volume=17),PermissionError,"VCBS_POINT_ONLY")
    def test_31_source_injected_minute_close_denied(self):
        self.bad(lambda a,b:a["series"][0].update(close=100),PermissionError,"VCBS_POINT_ONLY")
    def test_32_duplicate_vcbs_clock_denied(self):
        self.bad(lambda a,b:a["series"].append(copy.deepcopy(a["series"][0])),ValueError,"VCBS_DUPLICATE")
    def test_33_duplicate_ssi_clock_denied(self):
        self.bad(lambda a,b:b.append(copy.deepcopy(b[0])),ValueError,"SSI_DUPLICATE")
    def test_34_missing_ssi_ohlcv_denied(self):
        self.bad(lambda a,b:b[0].pop("high"),ValueError,"SSI_OHLCV_SHAPE")
    def test_35_invalid_ssi_high_low_denied(self):
        self.bad(lambda a,b:b[0].update(high=99),ValueError,"SSI_REFERENCE_OHLC")
    def test_36_negative_vcbs_price_denied(self):
        self.bad(lambda a,b:a["series"][0].update(price=-1),ValueError,"NONPOSITIVE")
    def test_37_vcbs_nan_denied(self):
        self.bad(lambda a,b:a["series"][0].update(price=float("nan")),ValueError,"NONPOSITIVE")
    def test_38_invalid_clock_denied_without_rounding(self):
        self.bad(lambda a,b:a["series"][0].update(time="24:00:00"),ValueError,"INVALID_HHMMSS")
    def test_39_false_day_scope_denied(self):
        self.bad(lambda a,b:b[0].update(trading_date="13/10/2025 09:15:00"),PermissionError,"SSI_UNVERIFIED_DAY_SCOPE")
    def test_40_invalid_symbol_denied(self):
        with self.assertRaisesRegex(ValueError,"ONE_UPPERCASE_SYMBOL"):
            self.compare(symbol="xyz")
    def test_41_invalid_session_date_denied(self):
        with self.assertRaisesRegex(ValueError,"RAW_VENDOR_SESSION_DATE"):
            self.compare(local_date="2025-10-14")
    def test_42_negative_vcbs_session_volume_denied(self):
        self.bad(lambda a,b:a.update(totalVolume=-100),ValueError,"NONPOSITIVE")
    def test_43_negative_ssi_volume_denied(self):
        self.bad(lambda a,b:b[0].update(volume=-1),ValueError,"NONPOSITIVE")
    def test_44_ambiguous_vcbs_provisional_missing_denied(self):
        self.bad(lambda a,b:a.pop("ohlcProvisional"),ValueError,"EXPLICIT_SESSION_BOARD_PROVISIONAL")
    def test_45_bool_quote_price_denied(self):
        self.bad(lambda a,b:a["series"][0].update(price=True),ValueError,"FINITE_SOURCE_NUMBER")
    def test_46_bounded_price_point_limit_denied(self):
        self.bad(lambda a,b:a.update(series=a["series"]*int(MAX_POINTS/2)),ValueError,"BOUNDED_PRICE_POINT")
    def test_47_bounded_ssi_tick_limit_denied(self):
        self.bad(lambda a,b:b.extend(b*int(MAX_POINTS/2)),ValueError,"BOUNDED_TICK_ROWS")
    def test_48_no_actual_quote_values_output(self):
        r=self.compare()
        self.assertNotIn("source_ohlcv_values",r)
        self.assertNotIn("timeline",r)
        self.assertNotIn("actual_close_prices",r)
    def test_49_string_ssi_numeric_normalization_is_structural_only(self):
        a,b=self.sample()
        b[0]["close"]="101"
        self.assertEqual(self.compare(a,b)["identical_reference_prices"],2)
        self.assertFalse(self.compare(a,b)["ssi_provider_m1_timestamp_start_end_authenticated"])
    def test_50_empty_vcbs_series_denied(self):
        self.bad(lambda a,b:a.update(series=[]),ValueError,"NONEMPTY_BOUNDED_PRICE_POINT")


if __name__=="__main__":
    unittest.main()
