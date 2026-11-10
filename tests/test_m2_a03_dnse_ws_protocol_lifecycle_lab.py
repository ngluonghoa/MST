"""28 synthetic DNSE WS lifecycle regression checks, no real network usage."""
from dataclasses import replace
from unittest import TestCase
from scripts import m2_a03_dnse_ws_protocol_lifecycle_lab as m

class DNSEWSDocumentedLifecycleTests(TestCase):
    def setUp(self):
        self.e = m.toy_trace()
    def run_trace(self, *events):
        return m.inspect_trace(tuple(events))
    def swapped(self, index, **changes):
        x = list(self.e)
        x[index] = replace(x[index], **changes)
        return tuple(x)
    def test_01_toy_two_connection_claim_only(self):
        self.assertEqual(self.run_trace(*self.e)["imaginary_session_count"], 2)
    def test_02_fake_auth_attempts_not_issuer(self):
        x = m.build()
        self.assertEqual(x["fake_auth_attempts"], 2)
        self.assertFalse(x["source_issuer_authenticated"])
    def test_03_reconnect_requires_both_subscriptions_again(self):
        self.assertEqual(m.build()["fake_subscribe_ack_count"], 2)
    def test_04_close_events_not_completeness(self):
        x = m.build()
        self.assertEqual(x["fake_closed_event_count"], 2)
        self.assertFalse(x["closed_delivery_completeness_proven"])
    def test_05_forming_not_native_closed(self):
        self.assertEqual(m.build()["fake_forming_event_count"], 1)
    def test_06_ping_pong_tracked_not_stream_authority(self):
        self.assertEqual(m.build()["fake_heartbeat_roundtrips"], 1)
    def test_07_no_credentials_or_actual_websocket(self):
        self.assertFalse(m.build()["source_credentials_present"])
        self.assertFalse(m.build()["real_websocket_opened"])
    def test_08_no_data_before_subscription_ack(self):
        with self.assertRaisesRegex(ValueError, "NO_STREAM_DATA"):
            self.run_trace(*self.e[:4], m.ToyEvent(4, "closed_data"))
    def test_09_no_subscribe_before_auth_success(self):
        with self.assertRaisesRegex(ValueError, "BOTH_MST"):
            self.run_trace(*self.e[:2], m.ToyEvent(2, "subscribe", m.CHANNELS))
    def test_10_no_auth_before_welcome(self):
        with self.assertRaisesRegex(ValueError, "AUTH_ONLY"):
            self.run_trace(m.ToyEvent(1, "auth", "toy-nonce-1", 1))
    def test_11_no_auth_success_before_request(self):
        with self.assertRaisesRegex(ValueError, "AUTH_SUCCESS"):
            self.run_trace(self.e[0], self.e[2])
    def test_12_reconnect_cannot_reuse_session_id(self):
        with self.assertRaisesRegex(ValueError, "FRESH_FAKE_WELCOME"):
            self.run_trace(*self.swapped(10, detail="toy-session-1"))
    def test_13_reconnect_cannot_reuse_nonce(self):
        with self.assertRaisesRegex(ValueError, "FRESH_SYNTHETIC_NONCE"):
            self.run_trace(*self.swapped(11, detail="toy-nonce-1"))
    def test_14_auth_clock_skew_over_five_minutes(self):
        with self.assertRaisesRegex(ValueError, "SKEW"):
            self.run_trace(*self.swapped(1, client_clock_seconds=302))
    def test_15_auth_deadline_thirty_seconds(self):
        with self.assertRaisesRegex(ValueError, "30_SECOND"):
            self.run_trace(self.e[0], m.ToyEvent(31, "auth", "toy-nonce-1", 31))
    def test_16_missing_pong_timeout(self):
        with self.assertRaisesRegex(ValueError, "PONG_HEARTBEAT"):
            self.run_trace(*self.e[:8], m.ToyEvent(241, "closed_data"))
    def test_17_pong_without_ping(self):
        with self.assertRaisesRegex(ValueError, "PONG_MUST_ECHO"):
            self.run_trace(*self.e[:7], m.ToyEvent(7, "pong", "toy-ping-1"))
    def test_18_wrong_pong_echo(self):
        with self.assertRaisesRegex(ValueError, "PONG_MUST_ECHO"):
            self.run_trace(*self.swapped(8, detail="toy-ping-wrong"))
    def test_19_boolean_seconds_rejected(self):
        with self.assertRaises(TypeError):
            self.run_trace(m.ToyEvent(True, "welcome", "toy-session-x"))
    def test_20_local_clock_rewind_rejected(self):
        with self.assertRaisesRegex(ValueError, "REWIND"):
            self.run_trace(self.e[0], m.ToyEvent(0, "auth", "toy-nonce-1", 0),
                           m.ToyEvent(0, "auth_success"), m.ToyEvent(0, "subscribe", m.CHANNELS),
                           m.ToyEvent(0, "subscribed"), m.ToyEvent(1, "ping", "toy-ping-1"),
                           m.ToyEvent(0, "pong", "toy-ping-1"))
    def test_21_session_eight_hour_limit(self):
        with self.assertRaisesRegex(ValueError, "EIGHT_HOUR"):
            self.run_trace(*self.e[:7], m.ToyEvent(28801, "closed_data"))
    def test_22_expired_session_cannot_emit_data(self):
        with self.assertRaisesRegex(ValueError, "NO_STREAM_DATA"):
            self.run_trace(*self.e[:7], m.ToyEvent(7, "expired"),
                           m.ToyEvent(8, "closed_data"))
    def test_23_missing_mst_dual_channels(self):
        with self.assertRaisesRegex(ValueError, "BOTH_MST"):
            self.run_trace(*self.swapped(3, detail="ohlc_closed.5.json"))
    def test_24_receipt_deterministic_without_secret_material(self):
        self.assertEqual(m.build()["synthetic_receipt_sha256"], m.build()["synthetic_receipt_sha256"])
        self.assertEqual(len(m.build()["synthetic_receipt_sha256"]), 64)
    def test_25_absent_auth_clock_rejected(self):
        with self.assertRaisesRegex(ValueError, "SKEW"):
            self.run_trace(*self.swapped(1, client_clock_seconds=None))
    def test_26_boolean_auth_clock_rejected(self):
        with self.assertRaisesRegex(ValueError, "SKEW"):
            self.run_trace(*self.swapped(1, client_clock_seconds=True))
    def test_27_duplicate_ping_without_pong(self):
        with self.assertRaisesRegex(ValueError, "ONE_PENDING"):
            self.run_trace(*self.e[:8], m.ToyEvent(181, "ping", "toy-ping-2"))
    def test_28_reconnect_without_new_subscribe_ack(self):
        with self.assertRaisesRegex(ValueError, "NO_STREAM_DATA"):
            self.run_trace(*self.e[:12], self.e[12], m.ToyEvent(245, "closed_data"))
