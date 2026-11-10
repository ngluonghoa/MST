"""64 SSI/DNSE/VCBS six-timeframe classification and VCBS no-bar checks."""
from unittest import TestCase
from swing_trading.incremental_cache import Provider as P
from swing_trading.c2_source_capability_audit import (
    ConnectedEndpoint as E,DataNeed as N,RefreshVerdict as V,
    endpoint_contract,advise_connected_refresh)
from scripts import m2_a03_three_source_vcbs_capability_lab as m

class ThreeSourceVCBS(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.all=m.matrix()
        cls.by={(x.provider,x.timeframe):x for x in cls.all}
        cls.result=m.evaluate()
    def test_01_three_sources(self):self.assertEqual(len(m.PROVIDERS),3)
    def test_02_six_timeframes(self):self.assertEqual(len(m.TF),6)
    def test_03_eighteen_rows(self):self.assertEqual(len(self.all),18)
    def test_04_no_duplicates(self):self.assertEqual(len(self.by),18)
    def test_05_all_no_licensed_entitlement(self):self.assertTrue(all(not x.entitlement for x in self.all))
    def test_06_all_no_qualified_native_bars(self):self.assertTrue(all(not x.qualified_native_ohlcv for x in self.all))
    def test_07_all_no_signal_permission(self):self.assertTrue(all(not x.signal_eligible for x in self.all))
    def test_08_ssi_m5_public_unconnected(self):self.assertTrue(self.by[P.SSI,"M5"].public_native_api_documented_unconnected)
    def test_09_ssi_m15_public_unconnected(self):self.assertTrue(self.by[P.SSI,"M15"].public_native_api_documented_unconnected)
    def test_10_ssi_m30_not_verified(self):self.assertFalse(self.by[P.SSI,"M30"].public_native_api_documented_unconnected)
    def test_11_ssi_h1_public_unconnected(self):self.assertTrue(self.by[P.SSI,"H1"].public_native_api_documented_unconnected)
    def test_12_ssi_h4_derived(self):self.assertIn("DERIVED_H4",self.by[P.SSI,"H4"].status)
    def test_13_ssi_d1_connected(self):self.assertIs(self.by[P.SSI,"D1"].connected_endpoint,E.SSI_D1_DETAILED)
    def test_14_dnse_m5_documented(self):self.assertTrue(self.by[P.DNSE,"M5"].public_native_api_documented_unconnected)
    def test_15_dnse_m15_documented(self):self.assertTrue(self.by[P.DNSE,"M15"].public_native_api_documented_unconnected)
    def test_16_dnse_m30_documented(self):self.assertTrue(self.by[P.DNSE,"M30"].public_native_api_documented_unconnected)
    def test_17_dnse_h1_documented(self):self.assertTrue(self.by[P.DNSE,"H1"].public_native_api_documented_unconnected)
    def test_18_dnse_h4_derived(self):self.assertIn("DERIVED_H4",self.by[P.DNSE,"H4"].status)
    def test_19_dnse_d1_connected(self):self.assertIs(self.by[P.DNSE,"D1"].connected_endpoint,E.DNSE_D1_HISTORY)
    def test_20_vcbs_m5_price_only(self):self.assertIn("PRICE_POINTS_NOT",self.by[P.VCBS,"M5"].status)
    def test_21_vcbs_m15_price_only(self):self.assertIs(self.by[P.VCBS,"M15"].connected_endpoint,E.VCBS_INTRADAY_PRICE_POINTS)
    def test_22_vcbs_m30_price_only(self):self.assertIs(self.by[P.VCBS,"M30"].connected_endpoint,E.VCBS_INTRADAY_PRICE_POINTS)
    def test_23_vcbs_h1_price_only(self):self.assertIs(self.by[P.VCBS,"H1"].connected_endpoint,E.VCBS_INTRADAY_PRICE_POINTS)
    def test_24_vcbs_h4_price_only(self):self.assertIs(self.by[P.VCBS,"H4"].connected_endpoint,E.VCBS_INTRADAY_PRICE_POINTS)
    def test_25_vcbs_d1_history(self):self.assertIs(self.by[P.VCBS,"D1"].connected_endpoint,E.VCBS_D1_WINDOW)
    def test_26_vcbs_minute_reference_contract(self):self.assertIs(endpoint_contract(E.VCBS_INTRADAY_PRICE_POINTS).need,N.MINUTE_PRICE_REFERENCE)
    def test_27_vcbs_ohlcv_denied(self):self.assertIs(advise_connected_refresh(E.VCBS_INTRADAY_PRICE_POINTS,N.MINUTE_OHLCV).verdict,V.BLOCKED)
    def test_28_vcbs_price_allowed_reference_only(self):self.assertIs(advise_connected_refresh(E.VCBS_INTRADAY_PRICE_POINTS,N.MINUTE_PRICE_REFERENCE).verdict,V.REFERENCE_SNAPSHOT)
    def test_29_valid_fabricated_shape(self):self.assertEqual(self.result["vcbs_fabricated_probe"]["probe_state"],"SHAPE_RETURNED")
    def test_30_exact_three_fake_prices(self):self.assertEqual(self.result["vcbs_fabricated_probe"]["synthetic_points"],3)
    def test_31_open_high_low_session_only(self):self.assertTrue(self.result["vcbs_fabricated_probe"]["board_session_open_high_low_not_each_m5_bar"])
    def test_32_vcbs_no_per_candle_ohlcv(self):self.assertFalse(self.result["vcbs_fabricated_probe"]["source_has_per_candle_ohlcv"])
    def test_33_no_vcbs_per_candle_volume(self):self.assertFalse(self.result["vcbs_fabricated_probe"]["source_volume_per_m5_verified"])
    def test_34_no_high_low_from_minute_sampling(self):self.assertFalse(self.result["vcbs_fabricated_probe"]["minute_high_low_from_sampling_verified"])
    def test_35_one_point_never_valid_m5(self):
        p=m.fabricated_vcbs();p["series"]=p["series"][:1];p["dataPoints"]=1
        self.assertFalse(m.vcbs_probe(p,"M5")["valid_for_signal_indicators"])
    def test_36_repeated_minute_sample_not_m5(self):
        p=m.fabricated_vcbs();p["series"][1]["time"]="09:15:00"
        self.assertFalse(m.vcbs_probe(p,"M5")["valid_for_signal_indicators"])
    def test_37_spoofed_row_ohlcv_does_not_upgrade_contract(self):
        p=m.fabricated_vcbs()
        for x in p["series"]:x.update({"open":100,"high":105,"low":95,"close":101,"volume":100})
        self.assertFalse(m.vcbs_probe(p,"M5")["valid_for_signal_indicators"])
    def test_38_no_data_denied_as_bar(self):
        p=m.fabricated_vcbs();p.update(data_status="no_data",series=[],dataPoints=0)
        with self.assertRaises(ValueError):m.vcbs_probe(p,"M5")
    def test_39_incorrect_point_count_denied(self):
        p=m.fabricated_vcbs();p["dataPoints"]=99
        with self.assertRaises(ValueError):m.vcbs_probe(p,"M5")
    def test_40_malformed_price_denied(self):
        p=m.fabricated_vcbs();p["series"][0]["price"]="not-a-price"
        with self.assertRaises(ValueError):m.vcbs_probe(p,"M5")
    def test_41_non_dict_denied(self):
        with self.assertRaises(TypeError):m.vcbs_probe([],"M5")
    def test_42_unknown_timeframe_denied(self):
        with self.assertRaises(TypeError):m.vcbs_probe(m.fabricated_vcbs(),"M1")
    def test_43_no_d1_to_h4_false_inheritance(self):self.assertFalse(self.by[P.VCBS,"H4"].public_native_api_documented_unconnected)
    def test_44_require_approved_source_denies_all_18(self):
        for x in self.all:
            with self.subTest(provider=x.provider.value,timeframe=x.timeframe):
                with self.assertRaises(PermissionError):m.require_approved_signal_source(x)
    def test_45_wrong_provider_type_denied(self):
        with self.assertRaises(TypeError):m.one("VCBS","M5")
    def test_46_wrong_timeframe_denied(self):
        with self.assertRaises(TypeError):m.one(P.VCBS,"M1")
    def test_47_no_owner_approval_or_live_cache(self):
        self.assertTrue(all(self.result[key] is False for key in m.GATES))
    def test_48_deterministic_receipt_only(self):
        self.assertEqual(self.result["synthetic_receipt_sha256"],m.evaluate()["synthetic_receipt_sha256"])
        self.assertFalse(self.result["vcbs_fabricated_probe"]["retains_real_source_rows"])

    def test_49_unambiguous_history_day13(self):
        x=m.ssi_date_candidates("13/10/2026 09:15:00")
        self.assertEqual(len(x),1)
        self.assertEqual(x[0][0],"DD_MM_YYYY")
    def test_50_latest_like_11_10_ambiguous(self):
        self.assertEqual(len(m.ssi_date_candidates("11/10/2026 14:45:00")),2)
    def test_51_equal_day_month_still_two_formats(self):
        self.assertEqual(len(m.ssi_date_candidates("11/11/2026 14:45:00")),2)
    def test_52_expected_day_cannot_resolve_ambiguous(self):
        from datetime import date
        with self.assertRaisesRegex(PermissionError,"AMBIGUOUS"):
            m.strict_ssi_day_candidate_only("11/10/2026 14:45:00",date(2026,11,10))
    def test_53_other_expected_day_cannot_resolve_either(self):
        from datetime import date
        with self.assertRaises(PermissionError):
            m.strict_ssi_day_candidate_only("11/10/2026 14:45:00",date(2026,10,11))
    def test_54_unambiguous_history_still_no_source_proof(self):
        from datetime import date
        r=m.strict_ssi_day_candidate_only("13/10/2026 09:15:00",date(2026,10,13))
        self.assertTrue(r["parser_shape_only"])
        self.assertFalse(r["vendor_date_convention_verified"])
    def test_55_unambiguous_day_mismatch_rejected(self):
        from datetime import date
        with self.assertRaises(ValueError):
            m.strict_ssi_day_candidate_only("13/10/2026 09:15:00",date(2026,11,13))
    def test_56_impossible_calendar_day_rejected(self):
        with self.assertRaises(ValueError):m.ssi_date_candidates("31/02/2026 09:15:00")
    def test_57_invalid_hms_rejected(self):
        with self.assertRaises(ValueError):m.ssi_date_candidates("13/10/2026 25:15:00")
    def test_58_wrong_date_shape_rejected(self):
        with self.assertRaises(ValueError):m.ssi_date_candidates("13/10/2026")
    def test_59_ssi_original_c2_synthetic_shape(self):
        r=m.ssi_dnse_synthetic_source_modes()
        self.assertEqual(r["ssi_original_c2_shape"],"SHAPE_RETURNED")
        self.assertEqual(r["ssi_synthetic_rows"],3)
    def test_60_ssi_minute_shape_not_source_semantic(self):
        r=m.ssi_dnse_synthetic_source_modes()
        self.assertFalse(r["ssi_raw_date_semantic_authenticated"])
        self.assertFalse(r["ssi_m5_close_and_interval_authenticated"])
    def test_61_dnse_connected_d1_original_c2_shape(self):
        r=m.ssi_dnse_synthetic_source_modes()
        self.assertEqual(r["dnse_original_c2_shape"],"SHAPE_RETURNED")
        self.assertEqual(r["dnse_synthetic_d1_rows"],3)
    def test_62_dnse_connected_minute_ohlcv_denied(self):
        self.assertTrue(m.ssi_dnse_synthetic_source_modes()["dnse_connected_minute_ohlcv_blocked"])
    def test_63_no_real_source_payload_retained(self):
        self.assertFalse(m.ssi_dnse_synthetic_source_modes()["real_source_payload_persisted"])
        self.assertFalse(self.result["native_minute_ohlcv_connected_and_qualified"])
    def test_64_source_mode_receipt_repeatable(self):
        self.assertEqual(self.result["ssi_dnse_synthetic_mode_probe"],
                         m.ssi_dnse_synthetic_source_modes())
