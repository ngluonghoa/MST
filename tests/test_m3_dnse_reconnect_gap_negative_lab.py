"""Offline negative tests for DNSE documented reconnect/closed-bar continuity.

No live DNS/WS/MCP calls, prices, credentials, symbols, cached market rows,
or vendor-signed first-known evidence.
"""
from datetime import datetime, timezone
import unittest

from scripts.m3_dnse_documented_closed_channel import UntrustedDnseWsMetadata
from scripts.m3_dnse_reconnect_gap_negative_lab import Phase, SyntheticDnseContinuity

T = 1781139600


def message(start=T, *, channel="ohlc_closed.5.json",
            resolution="5", clock_lag=420, last_update_lag=240):
    return UntrustedDnseWsMetadata(
        channel, resolution, "STOCK", start, start + last_update_lag,
        datetime.fromtimestamp(start + clock_lag, tz=timezone.utc)
    )


def ready(channel="ohlc_closed.5.json"):
    gate = SyntheticDnseContinuity(channel=channel)
    e = gate.connect()
    gate.welcome(epoch=e, synthetic_session_id="SYN-SESSION-ONE")
    gate.auth_ack(epoch=e, synthetic_nonce_marker="SYN-NONCE-ONE")
    gate.subscribed_ack(epoch=e, channel=channel)
    return gate, e


def ingest(g, epoch, start=T, *, tag="SYN-DIGEST-A", **kw):
    return g.ingest(epoch=epoch, message=message(start, **kw),
                    synthetic_digest_tag=tag)


class DnseReconnectGapNegativeTests(unittest.TestCase):
    def test_constructor_requires_exact_closed_intraday_channel(self):
        for channel in ("ohlc.5.json", "ohlc_closed.1D.json",
                        "ohlc_closed.1W.json", "ohlc_closed.4H.json",
                        "ohlc_closed.5", "ohlc_closed.5.json.evil"):
            with self.subTest(channel=channel), self.assertRaises(ValueError):
                SyntheticDnseContinuity(channel=channel)

    def test_invalid_channel_type(self):
        with self.assertRaises(TypeError):
            SyntheticDnseContinuity(channel=5)

    def test_documented_resolution_candidate(self):
        for resolution in ("5", "15", "30", "1H"):
            with self.subTest(resolution=resolution):
                g = SyntheticDnseContinuity(channel=f"ohlc_closed.{resolution}.json")
                self.assertGreater(g.interval_seconds, 0)
                self.assertFalse(g.report()["cache_publish_authorized"])

    def test_new_connection_needs_fresh_welcome_auth_subscribe(self):
        g = SyntheticDnseContinuity(channel="ohlc_closed.5.json")
        e = g.connect()
        self.assertEqual(e, 1)
        self.assertEqual(g.phase, Phase.NEED_WELCOME)
        with self.assertRaises(PermissionError):
            ingest(g, e)
        g.welcome(epoch=e, synthetic_session_id="SYN-SESSION-ONE")
        self.assertEqual(g.phase, Phase.NEED_AUTH_ACK)
        g.auth_ack(epoch=e, synthetic_nonce_marker="SYN-NONCE-ONE")
        self.assertEqual(g.phase, Phase.NEED_SUBSCRIBED_ACK)
        g.subscribed_ack(epoch=e, channel=g.channel)
        self.assertEqual(g.phase, Phase.RECEIVE_CANDIDATES)

    def test_cannot_connect_twice_without_disconnect(self):
        g, _ = ready()
        with self.assertRaises(PermissionError):
            g.connect()

    def test_cannot_auth_before_welcome(self):
        g = SyntheticDnseContinuity(channel="ohlc_closed.5.json")
        e = g.connect()
        with self.assertRaises(PermissionError):
            g.auth_ack(epoch=e, synthetic_nonce_marker="SYN-NONCE-ONE")

    def test_cannot_subscribe_before_auth(self):
        g = SyntheticDnseContinuity(channel="ohlc_closed.5.json")
        e = g.connect()
        g.welcome(epoch=e, synthetic_session_id="SYN-SESSION-ONE")
        with self.assertRaises(PermissionError):
            g.subscribed_ack(epoch=e, channel=g.channel)

    def test_synthetic_session_not_vendor_session(self):
        g = SyntheticDnseContinuity(channel="ohlc_closed.5.json")
        e = g.connect()
        with self.assertRaises(PermissionError):
            g.welcome(epoch=e, synthetic_session_id="conn_reallooking")
        self.assertEqual(g.phase, Phase.NEED_WELCOME)

    def test_synthetic_nonce_marker_required(self):
        g = SyntheticDnseContinuity(channel="ohlc_closed.5.json")
        e = g.connect()
        g.welcome(epoch=e, synthetic_session_id="SYN-SESSION-ONE")
        with self.assertRaises(PermissionError):
            g.auth_ack(epoch=e, synthetic_nonce_marker="1750000000123456")
        self.assertEqual(g.phase, Phase.NEED_AUTH_ACK)

    def test_wrong_subscribed_channel_rejected(self):
        g = SyntheticDnseContinuity(channel="ohlc_closed.5.json")
        e = g.connect()
        g.welcome(epoch=e, synthetic_session_id="SYN-SESSION-ONE")
        g.auth_ack(epoch=e, synthetic_nonce_marker="SYN-NONCE-ONE")
        with self.assertRaises(PermissionError):
            g.subscribed_ack(epoch=e, channel="ohlc.5.json")
        self.assertEqual(g.phase, Phase.NEED_SUBSCRIBED_ACK)

    def test_candidate_accepted_only_as_untrusted(self):
        g, e = ready()
        self.assertEqual(ingest(g, e), "UNVERIFIED_CLOSED_CHANNEL_SLOT_ONLY")
        r = g.report()
        self.assertEqual(r["synthetic_slots_seen"], 1)
        self.assertFalse(r["signal_eligible"])
        self.assertFalse(r["source_rights_and_retention_verified"])

    def test_forming_message_never_closed(self):
        g, e = ready()
        with self.assertRaises(PermissionError):
            ingest(g, e, channel="ohlc.5.json")

    def test_other_timeframe_never_accepted(self):
        g, e = ready()
        with self.assertRaises(PermissionError):
            ingest(g, e, channel="ohlc_closed.15.json", resolution="15")

    def test_other_encoding_never_accepted(self):
        g, e = ready()
        with self.assertRaises(PermissionError):
            ingest(g, e, channel="ohlc_closed.5.msgpack")

    def test_missing_real_envelope_type_denied(self):
        g, e = ready()
        with self.assertRaises(TypeError):
            g.ingest(epoch=e, message={"time": T},
                     synthetic_digest_tag="SYN-DIGEST-A")

    def test_nonfixture_digest_denied(self):
        g, e = ready()
        for candidate in ("deadbeef", "OHLC_PRICES", "", 123, None):
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                g.ingest(epoch=e, message=message(), synthetic_digest_tag=candidate)

    def test_identical_duplicate_is_observation_not_proof(self):
        g, e = ready()
        ingest(g, e)
        self.assertEqual(ingest(g, e), "IDENTICAL_DUPLICATE_UNTRUSTED")
        self.assertEqual(g.report()["same_slot_duplicate_count"], 1)
        self.assertEqual(g.report()["synthetic_slots_seen"], 1)
        self.assertFalse(g.report()["cache_publish_authorized"])

    def test_conflicting_duplicate_quarantined(self):
        g, e = ready()
        ingest(g, e)
        self.assertEqual(ingest(g, e, tag="SYN-DIGEST-B"),
                         "CONFLICTING_CLOSED_SLOT_QUARANTINE")
        self.assertEqual(g.phase, Phase.QUARANTINED)
        self.assertEqual(g.report()["same_slot_conflict_count"], 1)
        with self.assertRaises(PermissionError):
            ingest(g, e, T + 300)

    def test_out_of_order_unknown_slot_quarantined(self):
        g, e = ready()
        ingest(g, e, T+600)
        self.assertEqual(ingest(g, e, T+300),
                         "OUT_OF_ORDER_CLOSED_SLOT_QUARANTINE")
        self.assertEqual(g.report()["out_of_order_count"], 1)

    def test_candidate_gap_not_proof_real_bar_missing(self):
        g, e = ready()
        ingest(g, e)
        ingest(g, e, T+600)
        r = g.report()
        self.assertEqual(r["potential_calendar_or_delivery_gap_count"], 1)
        self.assertFalse(r["official_calendar_or_no_trade_verified"])

    def test_adjacent_labels_still_do_not_prove_continuity(self):
        g, e = ready()
        ingest(g, e)
        ingest(g, e, T+300)
        self.assertEqual(g.report()["potential_calendar_or_delivery_gap_count"], 0)
        self.assertFalse(g.report()["server_gap_replay_documented"])
        self.assertFalse(g.report()["cache_publish_authorized"])

    def test_lunch_gap_not_assumed_missing_bar(self):
        g, e = ready()
        ingest(g, e)
        ingest(g, e, T+7200)
        self.assertEqual(g.report()["potential_calendar_or_delivery_gap_count"], 1)
        self.assertFalse(g.report()["official_calendar_or_no_trade_verified"])

    def test_future_last_updated_relative_to_local_clock_quarantined(self):
        g, e = ready()
        result = ingest(g, e, clock_lag=100, last_update_lag=200)
        self.assertEqual(result, "CLIENT_CLOCK_SKEW_QUARANTINE")
        self.assertEqual(g.phase, Phase.QUARANTINED)
        self.assertEqual(g.report()["client_clock_warnings"], 1)

    def test_disconnect_forces_unknown_delivery_history(self):
        g, e = ready()
        ingest(g, e)
        g.disconnect(epoch=e, close_code=1008)
        r = g.report()
        self.assertEqual(r["disconnect_count"], 1)
        self.assertTrue(r["reconnect_delivery_history_unverified"])
        self.assertEqual(r["phase"], "DISCONNECTED")

    def test_client_network_loss_code_1006_denies_continuity(self):
        g, e = ready()
        g.disconnect(epoch=e, close_code=1006)
        self.assertTrue(g.report()["reconnect_delivery_history_unverified"])

    def test_connection_expired_code_1008_not_production_freshness(self):
        g, e = ready()
        g.disconnect(epoch=e, close_code=1008)
        e2 = g.connect()
        self.assertEqual(e2, e+1)
        self.assertFalse(g.report()["transport_epoch_is_vendor_authenticated"])

    def test_reconnect_requires_new_session_marker(self):
        g, e = ready()
        g.disconnect(epoch=e, close_code=1008)
        e2 = g.connect()
        with self.assertRaises(PermissionError):
            g.welcome(epoch=e2, synthetic_session_id="SYN-SESSION-ONE")

    def test_reconnect_requires_new_nonce_marker(self):
        g, e = ready()
        g.disconnect(epoch=e, close_code=1008)
        e2 = g.connect()
        g.welcome(epoch=e2, synthetic_session_id="SYN-SESSION-TWO")
        with self.assertRaises(PermissionError):
            g.auth_ack(epoch=e2, synthetic_nonce_marker="SYN-NONCE-ONE")

    def test_reconnect_requires_subscription_again(self):
        g, e = ready()
        g.disconnect(epoch=e, close_code=1008)
        e2 = g.connect()
        g.welcome(epoch=e2, synthetic_session_id="SYN-SESSION-TWO")
        g.auth_ack(epoch=e2, synthetic_nonce_marker="SYN-NONCE-TWO")
        with self.assertRaises(PermissionError):
            ingest(g, e2)
        g.subscribed_ack(epoch=e2, channel=g.channel)
        self.assertEqual(g.phase, Phase.RECEIVE_CANDIDATES)

    def test_old_epoch_data_rejected_after_reconnect(self):
        g, e = ready()
        g.disconnect(epoch=e, close_code=1008)
        e2 = g.connect()
        g.welcome(epoch=e2, synthetic_session_id="SYN-SESSION-TWO")
        g.auth_ack(epoch=e2, synthetic_nonce_marker="SYN-NONCE-TWO")
        g.subscribed_ack(epoch=e2, channel=g.channel)
        with self.assertRaises(PermissionError):
            ingest(g, e)
        self.assertEqual(ingest(g, e2), "UNVERIFIED_CLOSED_CHANNEL_SLOT_ONLY")

    def test_reconnect_adjacent_label_still_unknown(self):
        g, e = ready()
        ingest(g, e)
        g.disconnect(epoch=e, close_code=1008)
        e2 = g.connect()
        g.welcome(epoch=e2, synthetic_session_id="SYN-SESSION-TWO")
        g.auth_ack(epoch=e2, synthetic_nonce_marker="SYN-NONCE-TWO")
        g.subscribed_ack(epoch=e2, channel=g.channel)
        ingest(g, e2, T+300)
        r = g.report()
        self.assertEqual(r["potential_calendar_or_delivery_gap_count"], 0)
        self.assertTrue(r["reconnect_delivery_history_unverified"])
        self.assertFalse(r["reconciled_with_authorized_rest_backfill"])

    def test_invalid_close_code_denied(self):
        g, e = ready()
        for code in (999, 5000, True, "1008"):
            with self.subTest(code=code), self.assertRaises(ValueError):
                g.disconnect(epoch=e, close_code=code)
        self.assertEqual(g.phase, Phase.RECEIVE_CANDIDATES)

    def test_invalid_disconnect_epoch_denied(self):
        g, e = ready()
        with self.assertRaises(PermissionError):
            g.disconnect(epoch=e+1, close_code=1008)

    def test_double_disconnect_denied(self):
        g, e = ready()
        g.disconnect(epoch=e, close_code=1008)
        with self.assertRaises(PermissionError):
            g.disconnect(epoch=e, close_code=1008)

    def test_authorize_replay_impossible(self):
        g, _ = ready()
        with self.assertRaises(PermissionError):
            g.authorize_replay()

    def test_capacity_quarantines_without_market_data_storage(self):
        g, e = ready()
        for n in range(512):
            ingest(g, e, T+n*300)
        self.assertEqual(g.report()["synthetic_slots_seen"], 512)
        self.assertEqual(ingest(g, e, T+512*300),
                         "BOUNDED_METADATA_CAPACITY_QUARANTINE")
        self.assertEqual(g.phase, Phase.QUARANTINED)
        self.assertEqual(g.report()["synthetic_slots_seen"], 512)

    def test_report_contains_no_market_payload_or_credentials(self):
        g, e = ready()
        ingest(g, e)
        report = g.report()
        self.assertTrue(all(name not in report for name in
                            ("symbol", "open", "high", "low", "close", "volume",
                             "api_key", "nonce", "signature", "price")))
        self.assertEqual(report["decision"],
                         "NO_GO_NO_TRUSTED_CONTINUITY_OR_FIRST_KNOWN")
        self.assertFalse(report["production_authorized"])


if __name__ == "__main__":
    unittest.main()
