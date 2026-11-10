"""24 negative source clock/connected endpoint comparison tests."""
from dataclasses import replace
from datetime import datetime,date,timedelta,timezone
from unittest import TestCase
from swing_trading.c2_source_capability_audit import ConnectedEndpoint as E
from scripts import m2_a03_connected_source_freshness_lab as m

class ConnectedSourceFreshnessQA(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a=datetime(2026,10,13,2,30,tzinfo=timezone.utc)
        cls.w=m.UntrustedSSISnapshot(E.SSI_INTRADAY_SESSION,
            "13/10/2026 09:15:00",cls.a,cls.a+timedelta(seconds=10),date(2026,10,13))
        cls.r=m.evaluate()
    def test_01_asof_z(self):self.assertEqual(m.parse_reported_asof("2026-10-13T02:30:00Z"),self.a)
    def test_02_asof_offset(self):self.assertEqual(m.parse_reported_asof("2026-10-13T09:30:00+07:00"),self.a)
    def test_03_asof_naive_denied(self):
        with self.assertRaises(ValueError):m.parse_reported_asof("2026-10-13T02:30:00")
    def test_04_asof_bad_text_denied(self):
        with self.assertRaises(ValueError):m.parse_reported_asof("bad")
    def test_05_empty_asof_denied(self):
        with self.assertRaises(ValueError):m.parse_reported_asof("")
    def test_06_naive_observer_denied(self):
        with self.assertRaises(ValueError):replace(self.w,observed_at_utc=datetime(2026,10,13,2,30))
    def test_07_asof_future_to_observer_denied(self):
        with self.assertRaises(ValueError):replace(self.w,observed_at_utc=self.a-timedelta(seconds=1))
    def test_08_cannot_self_certify_issuer(self):
        with self.assertRaises(PermissionError):replace(self.w,issuer_verified=True)
    def test_09_ambiguous_latest_denied(self):
        w=replace(self.w,endpoint=E.SSI_INTRADAY_LATEST,
                  source_trade_date="11/10/2026 14:45:00",requested_day=None)
        with self.assertRaisesRegex(PermissionError,"AMBIGUOUS"):m.classify_ssi(w)
    def test_10_request_day_cannot_resolve_ambiguity(self):
        w=replace(self.w,source_trade_date="11/10/2026 14:45:00",
                  requested_day=date(2026,11,10))
        with self.assertRaises(PermissionError):m.classify_ssi(w)
    def test_11_unambiguous_wrong_requested_day_denied(self):
        with self.assertRaisesRegex(ValueError,"SOURCE_DAY_REQUEST"):
            m.classify_ssi(replace(self.w,requested_day=date(2026,10,14)))
    def test_12_future_event_to_connector_asof_denied(self):
        with self.assertRaisesRegex(ValueError,"SOURCE_EVENT_FUTURE"):
            m.classify_ssi(replace(self.w,connector_asof_utc=self.a-timedelta(hours=1)))
    def test_13_c2_unambiguous_is_only_shape(self):
        self.assertFalse(m.classify_ssi(self.w)["issuer_date_format_proven"])
    def test_14_synthetic_lag_900_seconds(self):
        self.assertEqual(m.classify_ssi(self.w)["syntactic_lag_seconds"],900)
    def test_15_lag_is_not_official_session_freshness(self):
        self.assertIsNone(self.r["exchange_calendar_freshness_age_limit"])
        self.assertFalse(m.classify_ssi(self.w)["official_latest_freshness_proven"])
    def test_16_connector_asof_not_vendor_first_known(self):
        self.assertFalse(m.classify_ssi(self.w)["connector_asof_is_publisher_first_known"])
    def test_17_ssi_latest_single_not_full_session(self):
        x=m.compare_source_modes(E.SSI_INTRADAY_LATEST,E.SSI_INTRADAY_SESSION)
        self.assertTrue(x["same_provider"])
        self.assertFalse(x["same_product"])
    def test_18_ssi_intraday_not_dnse_d1(self):
        x=m.compare_source_modes(E.SSI_INTRADAY_SESSION,E.DNSE_D1_HISTORY)
        self.assertFalse(x["same_product"])
        self.assertFalse(x["same_price_unit"])
    def test_19_ssi_intraday_not_vcbs_price_points(self):
        x=m.compare_source_modes(E.SSI_INTRADAY_SESSION,E.VCBS_INTRADAY_PRICE_POINTS)
        self.assertFalse(x["same_product"])
        self.assertFalse(x["permitted_to_confirm_latest_m5"])
    def test_20_even_same_endpoint_not_issuer_verified(self):
        x=m.compare_source_modes(E.SSI_INTRADAY_SESSION,E.SSI_INTRADAY_SESSION)
        self.assertTrue(x["same_product"])
        self.assertFalse(x["source_issuer_verified"])
    def test_21_wrong_endpoint_type_denied(self):
        with self.assertRaises(TypeError):
            m.compare_source_modes("SSI",E.DNSE_D1_HISTORY)
    def test_22_no_cross_mode_m5_eligibility(self):
        self.assertEqual(len(self.r["cross_mode_pairs"]),3)
        self.assertTrue(all(not x["permitted_to_confirm_latest_m5"] for x in self.r["cross_mode_pairs"]))
    def test_23_owner_gates_are_all_closed(self):
        self.assertTrue(all(self.r[k] is False for k in m.DENIED))
        self.assertFalse(self.r["source_bar_rows_persisted"])
    def test_24_report_deterministic_no_source_data(self):
        self.assertEqual(len(self.r["synthetic_receipt_sha256"]),64)
        self.assertEqual(self.r["synthetic_receipt_sha256"],m.evaluate()["synthetic_receipt_sha256"])
