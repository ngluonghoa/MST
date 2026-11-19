"""MST §231 source-native TF registry tests; synthetic, zero provider calls."""
from __future__ import annotations

import unittest

from scripts.mst_mfx_native_timeframes import (
    MAX_SINGLE_PROBE_CALENDAR_DAYS, SOURCE_CLOCK_TZ, SOURCE_NATIVE_TFS,
    NativeTfDenied, provider_resolution, source_tf_metadata,
)


class NativeSourceTimeframe231Tests(unittest.TestCase):
    def test_ssi_exact_supported_native_resolutions(self):
        expected = {
            "M5": "5m", "M15": "15m", "M30": "30m",
            "H1": "1h", "D1": "1d",
        }
        self.assertEqual(set(SOURCE_NATIVE_TFS), set(expected))
        for tf, resolution in expected.items():
            with self.subTest(tf=tf):
                self.assertEqual(provider_resolution("SSI", tf), resolution)

    def test_dnse_exact_supported_native_resolutions(self):
        expected = {
            "M5": "5", "M15": "15", "M30": "30",
            "H1": "1H", "D1": "1D",
        }
        for tf, resolution in expected.items():
            with self.subTest(tf=tf):
                self.assertEqual(provider_resolution("DNSE", tf), resolution)

    def test_provider_native_interval_duration_seconds(self):
        expected = {
            "M5": 300, "M15": 900, "M30": 1800,
            "H1": 3600, "D1": 86400,
        }
        for tf, duration in expected.items():
            with self.subTest(tf=tf):
                self.assertEqual(SOURCE_NATIVE_TFS[tf][2], duration)
                for provider in ("SSI", "DNSE"):
                    self.assertEqual(
                        source_tf_metadata(provider, tf)[
                            "provider_native_bar_interval_seconds"
                        ],
                        duration,
                    )

    def test_h4_must_not_be_claimed_natively(self):
        for provider in ("SSI", "DNSE"):
            with self.subTest(provider=provider), self.assertRaisesRegex(
                NativeTfDenied, "H4_NOT_AVAILABLE"
            ):
                provider_resolution(provider, "H4")

    def test_w1_must_not_be_silently_promoted_as_native(self):
        for provider in ("SSI", "DNSE"):
            with self.subTest(provider=provider), self.assertRaisesRegex(
                NativeTfDenied, "UNKNOWN_OR_UNSUPPORTED"
            ):
                provider_resolution(provider, "W1")

    def test_unknown_providers_fail_closed(self):
        for provider in ("VCBS", "", "ssi", "BROKER_TRADE"):
            with self.subTest(provider=provider), self.assertRaisesRegex(
                NativeTfDenied, "UNVERIFIED_PROVIDER"
            ):
                provider_resolution(provider, "D1")

    def test_unexpected_tf_literals_fail_closed(self):
        for tf in ("m5", "M1", "H2", "D", "1d", "", "M5 ", "M60"):
            with self.subTest(tf=tf), self.assertRaisesRegex(
                NativeTfDenied, "UNKNOWN_OR_UNSUPPORTED"
            ):
                provider_resolution("SSI", tf)

    def test_metadata_never_grants_source_rights_closure_or_trade(self):
        for provider in ("SSI", "DNSE"):
            for tf in SOURCE_NATIVE_TFS:
                with self.subTest(provider=provider, tf=tf):
                    obj = source_tf_metadata(provider, tf)
                    self.assertEqual(obj["source_native_tf"], tf)
                    self.assertEqual(
                        obj["provider_resolution"],
                        provider_resolution(provider, tf),
                    )
                    for gate in (
                        "H4_venue_session_aggregation_proven",
                        "source_closed_bar_attestation_proven",
                        "provider_marketdata_rights_verified",
                        "trade_signal_eligible",
                    ):
                        self.assertIs(obj[gate], False)

    def test_distinct_metadata_calls_do_not_share_mutable_receipts(self):
        a = source_tf_metadata("SSI", "M15")
        b = source_tf_metadata("SSI", "M15")
        self.assertEqual(a, b)
        a["trade_signal_eligible"] = True
        self.assertIs(b["trade_signal_eligible"], False)

    def test_request_window_bounds_are_conservative_not_coverage(self):
        self.assertEqual(
            MAX_SINGLE_PROBE_CALENDAR_DAYS,
            {"M5": 5, "M15": 10, "M30": 20, "H1": 35, "D1": 95},
        )
        self.assertEqual(set(MAX_SINGLE_PROBE_CALENDAR_DAYS), set(SOURCE_NATIVE_TFS))
        self.assertTrue(all(type(v) is int and v > 0
                            for v in MAX_SINGLE_PROBE_CALENDAR_DAYS.values()))

    def test_source_clock_is_vietnam_session_clock(self):
        self.assertEqual(SOURCE_CLOCK_TZ, "Asia/Ho_Chi_Minh")
        # D1 label in a provider response cannot substitute for a validated
        # venue close/finality or a first-known timestamp.
        self.assertFalse(source_tf_metadata("DNSE", "D1")[
            "source_closed_bar_attestation_proven"
        ])


if __name__ == "__main__":
    unittest.main()
