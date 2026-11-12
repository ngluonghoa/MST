"""50 wholly invented VCBS adjusted W/M crosscheck and NO-GO test cases."""
import copy
import math
import unittest

from scripts.m2_a03_vcbs_adjusted_wm_crosscheck_lab import (
    SCHEMA,STATUS,PRICE_TOLERANCE,OTHER_TOLERANCE,FIELDS,
    fake_fixture,run_synthetic,compare_source_periods,
)


class VcbsAdjustedHigherTimeframeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=run_synthetic()

    def fresh(self):
        return copy.deepcopy(fake_fixture())

    def check_bad(self,change,match):
        d,p=self.fresh()
        change(d,p)
        with self.assertRaisesRegex((ValueError,PermissionError),match):
            compare_source_periods(d,p)

    def test_01_schema(self):
        self.assertEqual(self.result["schema"],SCHEMA)

    def test_02_status_no_source_approval(self):
        self.assertEqual(self.result["status"],STATUS)

    def test_03_two_fake_periods(self):
        self.assertEqual(self.result["period_count"],2)

    def test_04_one_partial(self):
        self.assertEqual(self.result["partial_count"],1)

    def test_05_week_is_not_calendar_certified(self):
        self.assertEqual(self.result["period_comparisons"][0]["classification"],
                         "OBSERVATIONAL_ARITHMETIC_MATCH_NOT_CALENDAR_CERTIFIED")

    def test_06_month_is_quarantined(self):
        self.assertEqual(self.result["period_comparisons"][1]["classification"],
                         "QUARANTINED_PARTIAL_PERIOD")

    def test_07_week_factor_is_used(self):
        self.assertTrue(self.result["period_comparisons"][0]["adjustment_present"])

    def test_08_month_factor_is_used(self):
        self.assertTrue(self.result["period_comparisons"][1]["adjustment_present"])

    def test_09_raw_daily_open_distinct_from_adjusted_period_open(self):
        d,p=self.fresh()
        self.assertNotEqual(d[0]["openPrice"],p[0]["open"])

    def test_10_no_issuer_first_known(self):
        self.assertFalse(self.result["issuer_first_known_authenticated"])

    def test_11_no_market_calendar(self):
        self.assertFalse(self.result["official_holiday_and_halt_calendar_verified"])

    def test_12_no_real_provider_calls(self):
        self.assertFalse(self.result["actual_provider_data_queried"])

    def test_13_no_production_cache_or_trading(self):
        self.assertFalse(self.result["cloud_cache_storage_or_trading_authorized"])

    def test_14_no_verified_closed_candles_claim(self):
        self.assertFalse(self.result["fully_closed_source_candles_attested"])

    def test_15_zero_synthetic_mismatches(self):
        self.assertTrue(all(z["numeric_mismatch_count"]==0 for z in self.result["period_comparisons"]))

    def test_16_output_excludes_real_price_rows(self):
        self.assertNotIn("daily_rows",self.result)
        self.assertNotIn("source_values",str(self.result))

    def test_17_raw_open_without_factor_denied(self):
        self.check_bad(lambda d,p:p[0].update(open=100),"ARITHMETIC_DRIFT")

    def test_18_raw_low_without_factor_denied(self):
        self.check_bad(lambda d,p:p[0].update(low=95),"ARITHMETIC_DRIFT")

    def test_19_wrong_high_denied(self):
        self.check_bad(lambda d,p:p[0].update(high=119),"ARITHMETIC_DRIFT")

    def test_20_wrong_close_denied(self):
        self.check_bad(lambda d,p:p[0].update(close=109),"ARITHMETIC_DRIFT")

    def test_21_wrong_session_count_denied(self):
        self.check_bad(lambda d,p:p[0].update(sessions=2),"ARITHMETIC_DRIFT")

    def test_22_wrong_volume_denied(self):
        self.check_bad(lambda d,p:p[0].update(volume=381),"ARITHMETIC_DRIFT")

    def test_23_wrong_trading_value_denied(self):
        self.check_bad(lambda d,p:p[0].update(tradingValue=37001),"ARITHMETIC_DRIFT")

    def test_24_wrong_putthrough_value_denied(self):
        self.check_bad(lambda d,p:p[0].update(ptValue=951),"ARITHMETIC_DRIFT")

    def test_25_wrong_foreign_net_value_denied(self):
        self.check_bad(lambda d,p:p[0].update(foreignNetValue=1),"ARITHMETIC_DRIFT")

    def test_26_raw_daily_basis_denied(self):
        self.check_bad(lambda d,p:d[0].update(priceBasis="raw"),"ADJUSTED_BASIS")

    def test_27_raw_week_basis_denied(self):
        self.check_bad(lambda d,p:p[0].update(priceBasis="raw"),"NO_MIXED_PRICE_BASIS")

    def test_28_wrong_week_currency_denied(self):
        self.check_bad(lambda d,p:p[0].update(price_unit="UNCONFIRMED"),"NO_MIXED_PRICE_BASIS")

    def test_29_wrong_daily_currency_denied(self):
        self.check_bad(lambda d,p:d[0].update(price_unit="thousands"),"VND_MATCHED_VOLUME_SCOPE")

    def test_30_unverified_daily_volume_scope_denied(self):
        self.check_bad(lambda d,p:d[0].update(volumeScope="mixed"),"VND_MATCHED_VOLUME_SCOPE")

    def test_31_daily_provisional_denied(self):
        self.check_bad(lambda d,p:d[0].update(provisional=True),"DAILY_OPEN_OR_PROVISIONAL")

    def test_32_period_provisional_denied(self):
        self.check_bad(lambda d,p:p[0].update(provisional=True),"PROVISIONAL_VCBS_PERIOD")

    def test_33_missing_partial_denied(self):
        self.check_bad(lambda d,p:p[0].pop("partial"),"PARTIAL_FLAG")

    def test_34_untyped_partial_denied(self):
        self.check_bad(lambda d,p:p[0].update(partial="false"),"PARTIAL_FLAG")

    def test_35_week_cannot_cross_iso_week(self):
        self.check_bad(lambda d,p:p[0].update(periodStart="2025-02-28"),"ISO_WEEK")

    def test_36_month_cannot_cross_calendar_month(self):
        self.check_bad(lambda d,p:p[1].update(periodStart="2025-02-28"),"CALENDAR_MONTH")

    def test_37_reversed_period_denied(self):
        self.check_bad(lambda d,p:p[0].update(periodStart="2025-03-06"),"PERIOD_DATE_SCOPE")

    def test_38_period_label_mismatch_denied(self):
        self.check_bad(lambda d,p:p[0].update(tradingDate="2025-03-04"),"PERIOD_DATE_SCOPE")

    def test_39_duplicate_daily_session_denied(self):
        self.check_bad(lambda d,p:d.append(copy.deepcopy(d[0])),"DUPLICATE_D1_SESSION")

    def test_40_duplicate_week_period_denied(self):
        self.check_bad(lambda d,p:p.append(copy.deepcopy(p[0])),"DUPLICATE_W_M_PERIOD")

    def test_41_empty_daily_denied(self):
        with self.assertRaisesRegex(ValueError,"NONEMPTY_DAILY_ARRAY"):
            compare_source_periods([],self.fresh()[1])

    def test_42_empty_period_denied(self):
        with self.assertRaisesRegex(ValueError,"NONEMPTY_W_M_ARRAY"):
            compare_source_periods(self.fresh()[0],[])

    def test_43_missing_matching_daily_dates_denied(self):
        self.check_bad(lambda d,p:p[0].update(periodStart="2025-03-06",periodEnd="2025-03-07",tradingDate="2025-03-07"),"MISSING_W_M_DAILY")

    def test_44_invalid_raw_ohlc_denied(self):
        self.check_bad(lambda d,p:d[0].update(highPrice=99),"INVALID_RAW_DAILY")

    def test_45_negative_adjustment_factor_denied(self):
        self.check_bad(lambda d,p:d[0].update(adjFactor=-1),"INVALID_RAW_DAILY")

    def test_46_negative_volume_denied(self):
        self.check_bad(lambda d,p:d[0].update(volume=-1),"ADJUSTED_CLOSE_OR_VOLUME")

    def test_47_bool_price_field_denied(self):
        self.check_bad(lambda d,p:d[0].update(openPrice=True),"FINITE_NUMERIC")

    def test_48_nan_denied(self):
        self.check_bad(lambda d,p:d[0].update(openPrice=float("nan")),"FINITE_NUMERIC")

    def test_49_invalid_iso_source_date_denied(self):
        self.check_bad(lambda d,p:d[0].update(tradingDate="03/03/2025"),"EXACT_ISO")

    def test_50_missing_adjustment_field_denied(self):
        self.check_bad(lambda d,p:d[0].pop("adjFactor"),"MISSING_D1_FIELD")


if __name__=="__main__":
    unittest.main()
