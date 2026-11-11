"""40 strictly fictional SSI intraday/D1 arithmetic and date-contract safeguards."""
import copy
import unittest

from scripts.m2_a03_ssi_intraday_d1_observational_lab import (
    SCHEMA,STATUS,MAX_TICKS,audit_ssi_session,fake_fixture,synthetic_receipt,
)


class SsiIntradayD1ObservationalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=synthetic_receipt()

    def fixture(self):
        return copy.deepcopy(fake_fixture())

    def compute(self,rows=None,daily=None,symbol="ZZZ",day_token="14/10/2025"):
        a,b=self.fixture()
        return audit_ssi_session(a if rows is None else rows,
                                 b if daily is None else daily,
                                 symbol=symbol,day_token=day_token)

    def bad(self,mutator,exception,needle):
        a,b=self.fixture()
        mutator(a,b)
        with self.assertRaisesRegex(exception,needle):
            self.compute(a,b)

    def test_01_schema(self):
        self.assertEqual(self.r["schema"],SCHEMA)

    def test_02_no_go_status(self):
        self.assertEqual(self.r["status"],STATUS)

    def test_03_three_fake_intraday_rows(self):
        self.assertEqual(self.r["tick_row_count"],3)

    def test_04_all_five_fields_match(self):
        self.assertEqual(self.r["intraday_to_d1_price_volume_fields_matched"],5)

    def test_05_one_literal_d1_match(self):
        self.assertEqual(self.r["matching_d1_source_rows"],1)

    def test_06_other_daily_row_ignored_but_not_silently_mixed(self):
        self.assertEqual(self.r["other_d1_window_rows_ignored"],1)

    def test_07_one_clock_gap_not_missing_bars_grant(self):
        self.assertEqual(self.r["non_60_second_adjacent_clock_differences"],1)
        self.assertFalse(self.r["source_calendar_gaps_backfillable"])

    def test_08_date_conflicts_with_mmdy_descriptor(self):
        self.assertEqual(self.r["day_token_format_evidence"],
                         "OBSERVED_LITERAL_CONFLICTS_WITH_MMDY_CONNECTOR_DESCRIPTION")

    def test_09_contract_descriptor_is_not_authenticated(self):
        self.assertFalse(self.r["date_contract_verified_by_issuer"])

    def test_10_no_native_minute_candle_closure(self):
        self.assertFalse(self.r["native_m1_m5_bar_closure_or_start_end_verified"])

    def test_11_no_source_first_known(self):
        self.assertFalse(self.r["source_event_time_and_first_known_authenticated"])

    def test_12_no_vendor_retention_license(self):
        self.assertFalse(self.r["provider_cloud_retention_license_verified"])

    def test_13_no_github_runner_source_access(self):
        self.assertFalse(self.r["github_runner_market_source_connected"])

    def test_14_no_market_calendar(self):
        self.assertFalse(self.r["official_market_calendar_and_corporate_actions_verified"])

    def test_15_no_cache_or_trading(self):
        self.assertFalse(self.r["production_cache_or_trading_authorized"])

    def test_16_full_raw_price_sys_token_not_attested(self):
        self.assertFalse(self.r["original_raw_price_sys_token_endpoint_authenticated"])

    def test_17_wrong_tick_open_denied(self):
        self.bad(lambda a,b:a[0].update(open=101),PermissionError,"ARITHMETIC_DRIFT")

    def test_18_wrong_tick_high_denied(self):
        self.bad(lambda a,b:a[2].update(high=105),PermissionError,"ARITHMETIC_DRIFT")

    def test_19_wrong_tick_low_denied(self):
        self.bad(lambda a,b:a[0].update(low=100),PermissionError,"ARITHMETIC_DRIFT")

    def test_20_wrong_tick_close_denied(self):
        self.bad(lambda a,b:a[-1].update(close=104),PermissionError,"ARITHMETIC_DRIFT")

    def test_21_wrong_volume_denied(self):
        self.bad(lambda a,b:a[0].update(volume=149),PermissionError,"ARITHMETIC_DRIFT")

    def test_22_wrong_daily_close_denied(self):
        self.bad(lambda a,b:b[0].update(close=104),PermissionError,"ARITHMETIC_DRIFT")

    def test_23_wrong_daily_volume_denied(self):
        self.bad(lambda a,b:b[0].update(volume=800),PermissionError,"ARITHMETIC_DRIFT")

    def test_24_intra_session_high_low_envelope_denied(self):
        self.bad(lambda a,b:a[1].update(high=100),ValueError,"OHLC_ENVELOPE")

    def test_25_daily_high_low_envelope_denied(self):
        self.bad(lambda a,b:b[0].update(low=110),ValueError,"D1_OHLC_ENVELOPE")

    def test_26_duplicate_tick_clock_denied(self):
        self.bad(lambda a,b:a.append(copy.deepcopy(a[0])),ValueError,"DUPLICATE_SSI")

    def test_27_wrong_provider_symbol_denied(self):
        self.bad(lambda a,b:a[0].update(symbol="OTHER"),PermissionError,"SYMBOL_MIXED")

    def test_28_wrong_provider_date_denied(self):
        self.bad(lambda a,b:a[0].update(trading_date="13/10/2025 09:15:00"),
                 PermissionError,"LITERAL_DATE_SCOPE")

    def test_29_missing_price_changed_bool_denied(self):
        self.bad(lambda a,b:a[0].pop("price_changed"),ValueError,"PRICE_CHANGED_BOOL")

    def test_30_price_changed_true_recorded_but_unqualified(self):
        a,b=self.fixture()
        a[0]["price_changed"]=True
        r=self.compute(a,b)
        self.assertEqual(r["price_changed_rows"],1)
        self.assertFalse(r["source_event_time_and_first_known_authenticated"])

    def test_31_negative_volume_denied(self):
        self.bad(lambda a,b:a[0].update(volume=-1),ValueError,"NONPOSITIVE")

    def test_32_nonfinite_high_denied(self):
        self.bad(lambda a,b:a[0].update(high=float("nan")),ValueError,"NONPOSITIVE")

    def test_33_bool_price_denied(self):
        self.bad(lambda a,b:a[0].update(close=True),ValueError,"FINITE_UNAMBIGUOUS")

    def test_34_missing_daily_field_denied(self):
        self.bad(lambda a,b:b[0].pop("volume"),ValueError,"MISSING_SSI_D1_FIELD")

    def test_35_missing_tick_field_denied(self):
        self.bad(lambda a,b:a[0].pop("volume"),ValueError,"MISSING_SSI_INTRADAY_FIELD")

    def test_36_duplicate_d1_date_denied(self):
        self.bad(lambda a,b:b.append(copy.deepcopy(b[0])),ValueError,"EXACT_ONE_D1_ROW")

    def test_37_no_d1_date_match_denied(self):
        self.bad(lambda a,b:b.pop(0),ValueError,"EXACT_ONE_D1_ROW")

    def test_38_unavailable_both_date_parsers_denied(self):
        with self.assertRaisesRegex(ValueError,"DATE_TOKEN_IMPOSSIBLE"):
            self.compute(day_token="14/13/2025")

    def test_39_wrong_declared_mmdd_calendar_day_denied(self):
        with self.assertRaisesRegex(ValueError,"SOURCE_CALENDAR_DATE_IMPOSSIBLE"):
            self.compute(day_token="31/02/2025")

    def test_40_ambiguous_day_stays_unqualified(self):
        a,b=self.fixture()
        for row in a:row["trading_date"]=row["trading_date"].replace("14/10/2025","10/11/2025")
        b[0]["trading_date"]="10/11/2025"
        r=self.compute(a,b,day_token="10/11/2025")
        self.assertEqual(r["day_token_format_evidence"],
                         "OBSERVED_LITERAL_AMBIGUOUS_DDMM_VS_MMDD")
        self.assertFalse(r["date_contract_verified_by_issuer"])

    def test_41_unambiguous_mmdd_shape_not_signature(self):
        a,b=self.fixture()
        for row in a:row["trading_date"]=row["trading_date"].replace("14/10/2025","10/14/2025")
        b[0]["trading_date"]="10/14/2025"
        r=self.compute(a,b,day_token="10/14/2025")
        self.assertEqual(r["day_token_format_evidence"],
                         "OBSERVED_LITERAL_MMDY_SHAPE_ONLY_NO_SOURCE_ISSUER")
        self.assertFalse(r["date_contract_verified_by_issuer"])

    def test_42_reversed_tick_input_is_sorted_not_issuance_order(self):
        a,b=self.fixture()
        r=self.compute(list(reversed(a)),b)
        self.assertEqual(r["intraday_to_d1_price_volume_fields_matched"],5)
        self.assertFalse(r["source_event_time_and_first_known_authenticated"])

    def test_43_tick_order_clock_cannot_make_source_native_m5(self):
        a,b=self.fixture()
        a[1]["trading_date"]="14/10/2025 09:17:00"
        a[2]["trading_date"]="14/10/2025 09:18:00"
        r=self.compute(a,b)
        self.assertEqual(r["intraday_to_d1_price_volume_fields_matched"],5)
        self.assertFalse(r["native_m1_m5_bar_closure_or_start_end_verified"])

    def test_44_negative_d1_volume_denied(self):
        self.bad(lambda a,b:b[0].update(volume=-10),ValueError,"NONPOSITIVE")

    def test_45_empty_daily_denied(self):
        with self.assertRaisesRegex(ValueError,"NONEMPTY_SSI_DAILY"):
            self.compute(daily=[])

    def test_46_empty_intraday_denied(self):
        with self.assertRaisesRegex(ValueError,"NONEMPTY_BOUNDED_SSI_TICKS"):
            self.compute(rows=[])

    def test_47_invalid_local_clock_denied(self):
        self.bad(lambda a,b:a[0].update(trading_date="14/10/2025 24:15:00"),
                 ValueError,"INVALID_LOCAL_CLOCK")

    def test_48_non_numeric_price_string_denied(self):
        self.bad(lambda a,b:a[0].update(open="101,5"),ValueError,"CANONICAL_NONNEGATIVE")

    def test_49_up_to_max_rows_not_self_source_approved(self):
        a,b=self.fixture()
        a[0]["volume"]="150"
        r=self.compute(a,b)
        self.assertFalse(r["production_cache_or_trading_authorized"])

    def test_50_no_raw_source_rows_emitted(self):
        self.assertNotIn("OHLCV",str(self.r).upper())
        self.assertNotIn("raw_source_price_series",self.r)
        self.assertNotIn("all_ticks",self.r)


if __name__=="__main__":
    unittest.main()
