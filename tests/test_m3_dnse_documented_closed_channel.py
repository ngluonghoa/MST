"""DNSE source-product/closed-channel provenance negative checks, offline only."""
from datetime import datetime, timezone, timedelta
import unittest

from scripts.m3_dnse_documented_closed_channel import (
    UntrustedDnseWsMetadata, examine, require_authorized_closed_bar
)

T = 1781139600  # fabricated Unix-seconds source label (synthetic only)
UTC_OBS = datetime.fromtimestamp(T + 420, tz=timezone.utc)


def sample(channel="ohlc_closed.5.json", resolution="5", **kw):
    return UntrustedDnseWsMetadata(
        channel, resolution, "STOCK", T, T + 240, UTC_OBS, **kw
    )


class DnseClosedChannelTests(unittest.TestCase):
    def test_closed_channel_documented_candidate_not_qualified(self):
        result = examine(sample())
        self.assertEqual(result["structural_status"], "DOCUMENTED_CLOSED_CHANNEL_ENVELOPE_UNTRUSTED")
        self.assertFalse(result["source_native_closed_event_verified"])

    def test_forming_channel_never_closed(self):
        result = examine(sample(channel="ohlc.5.json"))
        self.assertEqual(result["structural_status"], "FORMING_CHANNEL_NOT_CLOSED")
        self.assertFalse(result["signal_eligible"])

    def test_channel_resolution_drift_denied(self):
        with self.assertRaisesRegex(ValueError, "RESOLUTION_MISMATCH"):
            sample(resolution="15")

    def test_unknown_resolution_denied(self):
        with self.assertRaises(ValueError):
            sample(channel="ohlc_closed.4H.json", resolution="4H")

    def test_h4_not_native(self):
        r = examine(sample())
        self.assertFalse(r["native_h4_documented"])
        self.assertFalse(r["listed_six_timeframes_all_native"])

    def test_documented_mst_timeframes(self):
        for resolution, tf in (("5", "M5"), ("15", "M15"), ("30", "M30"),
                               ("1H", "H1"), ("1D", "D1")):
            with self.subTest(resolution=resolution):
                r = examine(sample(channel=f"ohlc_closed.{resolution}.json", resolution=resolution))
                self.assertEqual(r["candidate_mst_timeframe"], tf)
                self.assertFalse(r["cache_publish_authorized"])

    def test_auxiliary_resolution_not_six_tf_target(self):
        for resolution in ("1", "3", "1W"):
            with self.subTest(resolution=resolution):
                r = examine(sample(channel=f"ohlc_closed.{resolution}.json", resolution=resolution))
                self.assertIsNone(r["candidate_mst_timeframe"])

    def test_msgpack_channel_documented(self):
        self.assertEqual(examine(sample(channel="ohlc_closed.5.msgpack"))["encoding"], "msgpack")

    def test_rest_url_cannot_be_forged_into_ws_channel(self):
        for channel in ("/price/ohlc", "price_get_history", "ohlc_closed.5", "ohlc_closed.5.json.evil"):
            with self.subTest(channel=channel), self.assertRaises(ValueError):
                sample(channel=channel)

    def test_bar_timestamp_is_start_not_publisher_first_known(self):
        r = examine(sample())
        self.assertEqual(r["timestamp_field_semantics"], "CANDLE_START_UNIX_SECONDS")
        self.assertFalse(r["first_known_issuer_authenticated"])

    def test_last_updated_does_not_prove_first_known(self):
        self.assertEqual(examine(sample())["last_updated_field_semantics"],
                         "LAST_SOURCE_UPDATE_NOT_FIRST_KNOWN")

    def test_theoretical_intraday_end_not_official_calendar(self):
        r = examine(sample())
        self.assertEqual(r["fixed_intraday_end_candidate_seconds"], T + 300)
        self.assertFalse(r["official_exchange_calendar_verified"])

    def test_daily_no_naive_24h_market_close(self):
        r = examine(sample(channel="ohlc_closed.1D.json", resolution="1D"))
        self.assertIsNone(r["fixed_intraday_end_candidate_seconds"])

    def test_weekly_no_naive_7d_market_close(self):
        r = examine(sample(channel="ohlc_closed.1W.json", resolution="1W"))
        self.assertIsNone(r["fixed_intraday_end_candidate_seconds"])

    def test_last_updated_before_bar_start_rejected(self):
        with self.assertRaisesRegex(ValueError, "TIME_ORDER"):
            UntrustedDnseWsMetadata("ohlc_closed.5.json", "5", "STOCK", T, T-1, UTC_OBS)

    def test_boolean_or_float_unix_timestamp_rejected(self):
        for bad in (True, 1.5, "1781139600"):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                UntrustedDnseWsMetadata("ohlc_closed.5.json", "5", "STOCK", bad, T+1, UTC_OBS)

    def test_naive_observer_rejected(self):
        with self.assertRaisesRegex(ValueError, "UTC_OBSERVATION"):
            UntrustedDnseWsMetadata("ohlc_closed.5.json", "5", "STOCK", T, T+1,
                                    datetime(2026, 6, 11))

    def test_nonutc_observer_rejected(self):
        with self.assertRaisesRegex(ValueError, "UTC_OBSERVATION"):
            UntrustedDnseWsMetadata("ohlc_closed.5.json", "5", "STOCK", T, T+1,
                                    UTC_OBS.astimezone(timezone(timedelta(hours=7))))

    def test_observation_clock_skew_remains_untrusted(self):
        m = UntrustedDnseWsMetadata("ohlc_closed.5.json", "5", "STOCK", T, T+400,
                                    datetime.fromtimestamp(T+300, tz=timezone.utc))
        self.assertTrue(examine(m)["clock_order_warning"])
        self.assertFalse(examine(m)["cache_publish_authorized"])

    def test_cannot_self_authenticate_vendor(self):
        with self.assertRaises(PermissionError):
            sample(authenticated_vendor_connection=True)

    def test_cannot_self_grant_right_to_retain(self):
        with self.assertRaises(PermissionError):
            sample(authorized_for_retention=True)

    def test_cannot_self_attest_issuer_first_known(self):
        with self.assertRaises(PermissionError):
            sample(independently_verified_first_known=True)

    def test_actual_market_bar_request_remains_denied(self):
        with self.assertRaises(PermissionError):
            require_authorized_closed_bar(sample())

    def test_no_connected_mcp_equivalence(self):
        self.assertFalse(examine(sample())["equivalent_to_connected_dnse_day_mcp"])

    def test_wrong_type_product_rejected(self):
        with self.assertRaises(ValueError):
            UntrustedDnseWsMetadata("ohlc_closed.5.json", "5", "INDEX", T, T+5, UTC_OBS)

    def test_invalid_envelope_type_rejected(self):
        with self.assertRaises(TypeError):
            examine({"channel": "ohlc_closed.5.json"})

    def test_future_epoch_bound_rejected(self):
        with self.assertRaises(ValueError):
            UntrustedDnseWsMetadata("ohlc_closed.5.json", "5", "STOCK", 4102444800, 4102444800, UTC_OBS)


if __name__ == "__main__":
    unittest.main()
