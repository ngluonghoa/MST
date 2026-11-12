"""48 synthetic DNSE WS lifecycle regression checks, no real network usage."""
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
    def test_17_proactive_pong_without_ping_permitted_by_dnse(self):
        r = self.run_trace(*self.e[:7], m.ToyEvent(7, "pong"))
        self.assertEqual(r["fake_proactive_pongs"], 1)
        self.assertEqual(r["fake_heartbeat_roundtrips"], 0)
    def test_18_wrong_optional_echo_is_diagnostic_not_issuer(self):
        r = self.run_trace(*self.swapped(8, detail="toy-ping-wrong"))
        self.assertEqual(r["fake_pong_echo_mismatches"], 1)
        self.assertFalse(r["source_issuer_authenticated"])
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
            self.run_trace(*self.e[:7], m.ToyEvent(7, "connection_expired"),
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

    def test_29_pong_without_echo_timestamp_is_valid(self):
        r = self.run_trace(*self.swapped(8, detail=""))
        self.assertEqual(r["fake_pongs_without_echo"], 1)
        self.assertEqual(r["fake_heartbeat_roundtrips"], 1)
    def test_30_pong_matching_echo_still_valid(self):
        r = self.run_trace(*self.e[:9])
        self.assertEqual(r["fake_heartbeat_roundtrips"], 1)
        self.assertEqual(r["fake_pong_echo_mismatches"], 0)
    def test_31_proactive_pong_cannot_claim_rtt(self):
        r = self.run_trace(*self.e[:7], m.ToyEvent(7, "pong"))
        self.assertEqual(r["fake_heartbeat_roundtrips"], 0)
    def test_32_auth_success_must_finish_within_thirty_seconds(self):
        with self.assertRaisesRegex(ValueError, "AUTH_SUCCESS_30_SECOND"):
            self.run_trace(self.e[0], self.e[1], m.ToyEvent(31, "auth_success"))
    def test_33_auth_success_at_thirty_seconds_allowed(self):
        r = self.run_trace(self.e[0], self.e[1], m.ToyEvent(30, "auth_success"))
        self.assertEqual(r["ending_state"], "AUTHENTICATED_CLAIM")
    def test_34_exact_connection_expired_action(self):
        r = self.run_trace(*self.e[:7], m.ToyEvent(7, "connection_expired"))
        self.assertEqual(r["ending_state"], "EXPIRED_CLAIM")
    def test_35_fake_expired_alias_no_longer_accepted(self):
        with self.assertRaisesRegex(ValueError, "KNOWN_CONTROL"):
            self.run_trace(*self.e[:7], m.ToyEvent(7, "expired"))
    def test_36_expired_requires_reconnect_before_data(self):
        with self.assertRaisesRegex(ValueError, "NO_STREAM_DATA"):
            self.run_trace(*self.e[:7], m.ToyEvent(7, "connection_expired"),
                           m.ToyEvent(8, "closed_data"))
    def test_37_documented_auth_failed_error_fail_closed(self):
        r = self.run_trace(self.e[0], self.e[1], m.ToyEvent(2, "error", "AUTH_FAILED"))
        self.assertEqual(r["ending_state"], "ERROR_CLAIM")
        self.assertEqual(r["fake_error_controls"], 1)
    def test_38_after_error_data_denied(self):
        with self.assertRaisesRegex(ValueError, "NO_STREAM_DATA"):
            self.run_trace(self.e[0], self.e[1], m.ToyEvent(2, "error", "AUTH_FAILED"),
                           m.ToyEvent(3, "closed_data"))
    def test_39_fake_invalid_error_code_rejected(self):
        with self.assertRaisesRegex(ValueError, "ERROR_CONTROL"):
            self.run_trace(self.e[0], self.e[1], m.ToyEvent(2, "error", "UNKNOWN"))
    def test_40_backoff_documented_bounded_sequence(self):
        self.assertEqual([m.synthetic_backoff_seconds(i) for i in range(8)],
                         [1, 2, 4, 8, 16, 32, 60, 60])
    def test_41_backoff_boolean_and_negative_invalid(self):
        with self.assertRaises(ValueError):
            m.synthetic_backoff_seconds(True)
        with self.assertRaises(ValueError):
            m.synthetic_backoff_seconds(-1)
    def test_42_sixty_second_boundary_for_pong(self):
        r = self.run_trace(*self.e[:8], m.ToyEvent(240, "pong"))
        self.assertEqual(r["fake_heartbeat_roundtrips"], 1)
    def test_43_sixty_one_second_pong_deadline(self):
        with self.assertRaisesRegex(ValueError, "PONG_HEARTBEAT"):
            self.run_trace(*self.e[:8], m.ToyEvent(241, "pong"))
    def test_44_proactive_pong_with_fake_echo_denied_by_local_guard(self):
        with self.assertRaisesRegex(ValueError, "PROACTIVE_PONG"):
            self.run_trace(*self.e[:7], m.ToyEvent(7, "pong", "toy-ping-1"))
    def test_45_control_with_t_field_known_action_is_control(self):
        self.assertEqual(m.classify_untrusted_inbound({"action": "ping", "T": "odd"}),
                         "CONTROL_SHAPE_UNTRUSTED")
    def test_46_data_with_unknown_action_and_t_field_is_data(self):
        self.assertEqual(m.classify_untrusted_inbound({"action": "estimated_index",
                                                       "T": "market_index"}),
                         "DATA_SHAPE_UNTRUSTED")
    def test_47_unknown_action_without_t_is_untrusted(self):
        self.assertEqual(m.classify_untrusted_inbound({"action": "weird"}),
                         "UNKNOWN_SHAPE_UNTRUSTED")
    def test_48_not_a_dict_no_trust(self):
        with self.assertRaises(TypeError):
            m.classify_untrusted_inbound([])
