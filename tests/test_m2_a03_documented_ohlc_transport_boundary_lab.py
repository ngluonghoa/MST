"""26 source transport document reconciliation and closed-vs-forming negatives."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest import TestCase

from swing_trading.incremental_cache import Provider
from scripts.m2_a03_three_source_vcbs_capability_lab import one
from scripts import m2_a03_documented_ohlc_transport_boundary_lab as m

class DocumentedSourceTransportTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closed=m.fabricated()
        cls.forming=m.fabricated(m.DocumentedTransport.DNSE_WS_FORMING,
                                 update_after_start_seconds=350)
        cls.observer=datetime.fromtimestamp(max(cls.closed.lastUpdated,cls.forming.lastUpdated)+20,tz=timezone.utc)
        cls.result=m.build()
    def read(self,w):
        return m.documented_channel_observation(w,observed_at_utc=self.observer)

    def test_01_three_documented_transport_products(self):self.assertEqual(len(m.DocumentedTransport),3)
    def test_02_ssi_rest_30m_documented(self):self.assertTrue(one(Provider.SSI,"M30").public_native_api_documented_unconnected)
    def test_03_ssi_rest_30m_mcp_unconnected(self):self.assertFalse(m.documented_m30_ssi_status()["current_connected_mcp_supports_rest_v3_30m"])
    def test_04_ssi_sdk_tutorial_not_30m(self):self.assertFalse(m.documented_m30_ssi_status()["sdk_tutorial_30m_independently_proven"])
    def test_05_dnse_public_ws_start_label(self):self.assertTrue(self.result["dnse_public_ws_start_label_documented"])
    def test_06_dnse_forming_channel_documented(self):self.assertTrue(self.result["dnse_public_ws_ohlc_forming_channel_documented"])
    def test_07_dnse_closed_channel_documented(self):self.assertTrue(self.result["dnse_public_ws_ohlc_closed_channel_documented"])
    def test_08_dnse_connected_mcp_not_ws(self):self.assertTrue(self.result["dnse_connected_mcp_is_d1_history_not_live_ws"])
    def test_09_closed_claim_after_end_is_shape_only(self):
        r=self.read(self.closed)
        self.assertTrue(r["claimed_closed_channel_shape_after_end"])
        self.assertFalse(r["source_channel_authenticated"])
    def test_10_in_progress_even_if_after_end(self):
        r=self.read(self.forming)
        self.assertTrue(r["source_payload_self_declares_forming_channel"])
        self.assertFalse(r["claimed_closed_channel_shape_after_end"])
    def test_11_forming_channel_cannot_signal(self):self.assertFalse(self.read(self.forming)["can_emit_signal"])
    def test_12_closed_channel_still_cannot_signal(self):self.assertFalse(self.read(self.closed)["can_emit_signal"])
    def test_13_start_label_nominal_end_plus_five(self):
        self.assertEqual(self.read(self.closed)["nominal_end_seconds"],self.closed.time+300)
    def test_14_closed_before_nominal_end_denied(self):
        with self.assertRaisesRegex(ValueError,"BEFORE_NOMINAL"):
            self.read(replace(self.closed,lastUpdated=self.closed.time+299))
    def test_15_exact_nominal_end_shape_allowed_only_unverified(self):
        r=self.read(replace(self.closed,lastUpdated=self.closed.time+300))
        self.assertTrue(r["claimed_closed_channel_shape_after_end"])
        self.assertFalse(r["real_closed_native_m5_qualified"])
    def test_16_source_false_attestation_denied(self):
        with self.assertRaises(PermissionError):
            replace(self.closed,source_verified=True)
    def test_17_wrong_resolution_denied(self):
        with self.assertRaisesRegex(ValueError,"FIVE_MINUTE"):
            replace(self.closed,resolution="15")
    def test_18_wrong_product_transport_denied(self):
        with self.assertRaises(TypeError):
            replace(self.closed,transport=m.DocumentedTransport.SSI_REST_V3)
    def test_19_milliseconds_epoch_denied(self):
        with self.assertRaisesRegex(ValueError,"UNIX_SECONDS"):
            replace(self.closed,time=self.closed.time*1000)
    def test_20_boolean_epoch_denied(self):
        with self.assertRaisesRegex(ValueError,"UNIX_SECONDS"):
            replace(self.closed,lastUpdated=True)
    def test_21_unaligned_m5_timestamp_denied(self):
        with self.assertRaisesRegex(ValueError,"UNALIGNED"):
            replace(self.closed,time=self.closed.time+1)
    def test_22_source_event_after_observer_denied(self):
        with self.assertRaisesRegex(ValueError,"AFTER_OBSERVER"):
            m.documented_channel_observation(
                self.closed,observed_at_utc=datetime.fromtimestamp(
                    self.closed.lastUpdated-1,tz=timezone.utc))
    def test_23_negative_volume_denied(self):
        with self.assertRaisesRegex(ValueError,"NONNEGATIVE"):
            replace(self.closed,volume=-1)
    def test_24_wrong_ohlc_geometry_denied(self):
        with self.assertRaisesRegex(ValueError,"INCONSISTENT"):
            replace(self.closed,low=Decimal("105"))
    def test_25_all_license_owner_and_cache_gates_closed(self):
        self.assertTrue(all(self.result[k] is False for k in m.DENIED))
        self.assertFalse(self.result["dnse_qualified_closed_M5_signal"])
    def test_26_repeatable_synthetic_receipt_not_issuer(self):
        self.assertEqual(len(self.result["synthetic_receipt_sha256"]),64)
        self.assertEqual(self.result["synthetic_receipt_sha256"],m.build()["synthetic_receipt_sha256"])
