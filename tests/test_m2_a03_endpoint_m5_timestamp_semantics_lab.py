"""35 fixture-only SSI/DNSE M5 raw label semantic contract tests."""
from dataclasses import replace
from datetime import date,timedelta
from unittest import TestCase
from swing_trading.session_calendar import TimestampSemantic as S
from swing_trading.native_minute_bar_source_plan import BarProduct as P
from scripts import m2_a03_endpoint_m5_timestamp_semantics_lab as m

class EndpointM5Tests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.day,cls.am,cls.pm,cls.late,_,_,cls.known=m.fixtures_day()
        cls.dn=m.dnse_day(cls.day)
        cls.bar=m.records_at(m.vn_utc(11,25),cls.day.scope,event="AM_LAST")
        cls.r=m.evaluate()
    def si(self,time,sem):
        return m.Label(P.SSI_FASTCONNECT_INTRADAY_OHLC,time,
                       self.day.trading_day_local,sem)
    def de(self,time,sem):
        return m.Label(P.DNSE_OPENAPI_OHLC,time,self.dn.trading_day_local,sem)
    def test_01_exact_eighteen_cases(self):self.assertEqual(self.r["count"],18)
    def test_02_source_enums_are_original(self):self.assertEqual(S.START.value,"START")
    def test_03_start_1125(self):self.assertEqual(m.interval(self.si("11:25:00",S.START)),(m.vn_utc(11,25),m.vn_utc(11,30)))
    def test_04_end_1130(self):self.assertEqual(m.interval(self.si("11:30:00",S.END)),(m.vn_utc(11,25),m.vn_utc(11,30)))
    def test_05_start_1130_is_lunch(self):self.assertEqual(m.interval(self.si("11:30:00",S.START)),(m.vn_utc(11,30),m.vn_utc(11,35)))
    def test_06_start_1300_is_pm(self):self.assertEqual(m.interval(self.si("13:00:00",S.START)),(m.vn_utc(13,0),m.vn_utc(13,5)))
    def test_07_end_1300_is_gap(self):self.assertEqual(m.interval(self.si("13:00:00",S.END)),(m.vn_utc(12,55),m.vn_utc(13,0)))
    def test_08_end_1305_is_pm(self):self.assertEqual(m.interval(self.si("13:05:00",S.END)),(m.vn_utc(13,0),m.vn_utc(13,5)))
    def test_09_undecided_semantic_denied(self):
        with self.assertRaises(PermissionError):m.interval(self.si("11:30:00",S.UNKNOWN))
    def test_10_cannot_self_assert_verified(self):
        with self.assertRaises(PermissionError):replace(self.si("11:30:00",S.END),verified=True)
    def test_11_hms_required(self):
        with self.assertRaises(ValueError):m.raw_time(self.si("11:30",S.END))
    def test_12_no_rounding_59_seconds(self):
        with self.assertRaises(ValueError):m.raw_time(self.si("14:29:59",S.END))
    def test_13_hour_24_denied(self):
        with self.assertRaises(ValueError):m.raw_time(self.si("24:00:00",S.END))
    def test_14_dnse_start_unix(self):
        self.assertEqual(m.interval(self.de(int(m.vn_utc(11,25).timestamp()),S.START)),(m.vn_utc(11,25),m.vn_utc(11,30)))
    def test_15_dnse_end_unix(self):
        self.assertEqual(m.interval(self.de(int(m.vn_utc(11,30).timestamp()),S.END)),(m.vn_utc(11,25),m.vn_utc(11,30)))
    def test_16_millis_denied(self):
        with self.assertRaises(ValueError):m.raw_time(self.de(int(m.vn_utc(11,30).timestamp())*1000,S.END))
    def test_17_bool_epoch_denied(self):
        with self.assertRaises(ValueError):m.raw_time(self.de(True,S.END))
    def test_18_dnse_unknown_denied(self):
        with self.assertRaises(PermissionError):m.interval(self.de(int(m.vn_utc(13,0).timestamp()),S.UNKNOWN))
    def test_19_non_native_day_only_product_denied(self):
        with self.assertRaises(TypeError):m.Label(P.DNSE_CONNECTED_DAY_ONLY,1900000000,self.day.trading_day_local,S.START)
    def test_20_string_semantic_not_typed(self):
        with self.assertRaises(TypeError):m.Label(P.DNSE_OPENAPI_OHLC,1900000000,self.day.trading_day_local,"START")
    def test_21_wrong_provider_bound_denied(self):
        b=m.records_at(m.vn_utc(11,25),self.dn.scope,event="DNSE")
        with self.assertRaises(ValueError):m.screen_label(self.dn,(b,),self.si("11:30:00",S.END),"AM_LAST",b.bar.first_known_utc)
    def test_22_wrong_bar_start_for_label_denied(self):
        with self.assertRaises(ValueError):m.screen_label(self.day,(self.bar,),self.si("11:30:00",S.START),"AM_LAST",self.bar.bar.first_known_utc)
    def test_23_wrong_day_denied(self):
        label=replace(self.si("11:30:00",S.END),local_day=date(2026,11,10))
        with self.assertRaises(ValueError):m.screen_label(self.day,(self.bar,),label,"AM_LAST",self.bar.bar.first_known_utc)
    def test_24_unknown_not_auto_calendar_fit(self):
        with self.assertRaises(PermissionError):m.screen_label(self.day,(self.bar,),self.si("11:30:00",S.UNKNOWN),"AM_LAST",self.bar.bar.first_known_utc)
    def test_25_before_first_known_r1(self):
        r=m.screen_label(self.day,(self.am,self.late),self.si("11:20:00",S.START),"AM_LAST",self.known-timedelta(microseconds=1))
        self.assertEqual(r["revision"],"r1")
    def test_26_at_first_known_r2(self):
        r=m.screen_label(self.day,(self.am,self.late),self.si("11:20:00",S.START),"AM_LAST",self.known)
        self.assertEqual(r["revision"],"r2")
    def test_27_before_candle_close_not_usable(self):
        self.assertIsNone(m.screen_label(self.day,(self.bar,),self.si("11:25:00",S.START),"AM_LAST",m.vn_utc(11,29))["revision"])
    def test_28_ssi_semantic_not_authenticated(self):self.assertFalse(self.r["ssi_start_end_semantic_proven"])
    def test_29_dnse_semantic_not_authenticated(self):self.assertFalse(self.r["dnse_start_end_semantic_proven"])
    def test_30_no_native_ssi_m5_proof(self):self.assertFalse(self.r["ssi_m5_resolution_proven"])
    def test_31_no_real_source_or_rights(self):self.assertFalse(self.r["licensed_vendor_source_proven"])
    def test_32_no_drive_market_cache(self):self.assertFalse(self.r["drive_market_cache_authorized"])
    def test_33_original_source_unchanged(self):self.assertFalse(self.r["v1_v2_original_modified"])
    def test_34_no_approval_trade(self):
        for k in ("owner_a02_63_approved","owner_a03_v2_8_approved","owner_a03_14_approved","production_authorized","trading_authorized"):
            self.assertFalse(self.r[k])
    def test_35_deterministic_checksum(self):
        self.assertEqual(len(self.r["synthetic_sha256"]),64)
        self.assertEqual(m.evaluate()["synthetic_sha256"],self.r["synthetic_sha256"])
