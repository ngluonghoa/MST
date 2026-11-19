"""§234 isolated fictional tests: no live provider calls, no source-series logs."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import base64
import json
import unittest

from scripts.mst_dnse_native_cloud_readonly234 import (
    CONTEXT, DnseProbeDenied, URL, _validate_native,
    make_signed_headers, require_owner_and_window, run_probe,
)

NOW = datetime(2026, 11, 20, 1, 0, 0, tzinfo=timezone.utc)
NONCE = "f" * 32


def valid_env():
    return {
        **CONTEXT,
        "MST_DNSE_API_KEY": "test_api_key_123",
        "MST_DNSE_API_SECRET": "test_secret_12345",
        "MST_DNSE_SYMBOL": "FPT",
        "MST_SOURCE_TF": "D1",
        "MST_DNSE_FROM_DATE": "2026-11-17",
        "MST_DNSE_TO_DATE": "2026-11-18",
    }


def fake_payload(env=None):
    _, start, _, _ = require_owner_and_window(env or valid_env())
    return {
        "t": [start + 9*3600, start + 86400 + 9*3600],
        "o": [20, 19], "h": [21, 20], "l": [19, 18],
        "c": [19.5, 19.0], "v": [100, 200], "nextTime": 0,
    }


class Response:
    def __init__(self, data=None, status=200):
        self.status_code = status
        self.content = json.dumps(data if data is not None else fake_payload()).encode()


class Session:
    def __init__(self, data=None, status=200):
        self.data, self.status = data, status
        self.calls = []

    def get(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return Response(self.data, self.status)


class DnseCloud234Tests(unittest.TestCase):
    def test_valid_fake_native_receipt_remains_unverified_and_no_trade(self):
        e, s = valid_env(), Session()
        r = run_probe(s, e, issued_at=NOW, nonce=NONCE)
        self.assertEqual(r["native_source_rows_observed"], 2)
        self.assertEqual(r["timeframe"], "D1")
        self.assertTrue(r["ohlcv_local_invariants_verified"])
        for k in (
            "source_window_complete_attested",
            "historical_first_known_and_closed_attested",
            "price_unit_and_adjustment_basis_attested",
            "provider_source_rights_independently_attested",
            "data_written_to_drive",
            "market_cache_promoted",
            "signals_and_trading_eligible",
        ):
            self.assertIs(r[k], False)
        self.assertEqual(len(s.calls), 1)
        args, kwargs = s.calls[0]
        self.assertEqual(args, (URL,))
        self.assertEqual(kwargs["params"]["resolution"], "1D")
        self.assertEqual(kwargs["params"]["type"], "STOCK")
        self.assertEqual(kwargs["timeout"], 20)
        self.assertFalse(kwargs["allow_redirects"])
        self.assertNotIn(e["MST_DNSE_API_SECRET"], json.dumps(r))
        self.assertNotIn('"o"', json.dumps(r))

    def test_all_five_native_tf_map_not_h4_or_w1(self):
        for tf, resolution in (
            ("M5", "5"), ("M15", "15"), ("M30", "30"),
            ("H1", "1H"), ("D1", "1D"),
        ):
            e = valid_env()
            e["MST_SOURCE_TF"] = tf
            with self.subTest(tf=tf):
                self.assertEqual(require_owner_and_window(e)[0], resolution)
        for tf in ("H4", "W1", "M1"):
            e = valid_env()
            e["MST_SOURCE_TF"] = tf
            with self.subTest(tf=tf), self.assertRaises(DnseProbeDenied):
                require_owner_and_window(e)

    def test_signature_fixed_vector_and_nonce(self):
        e = valid_env()
        hdr = make_signed_headers(e["MST_DNSE_API_KEY"], e["MST_DNSE_API_SECRET"], NOW, NONCE)
        signing = "(request-target): get /price/ohlc\ndate: " + hdr["Date"] + "\nnonce: " + NONCE
        expected = base64.b64encode(
            hmac.new(e["MST_DNSE_API_SECRET"].encode(), signing.encode(), hashlib.sha256).digest()
        ).decode().replace("+", "%2B").replace("/", "%2F").replace("=", "%3D")
        self.assertIn('signature="' + expected + '"', hdr["X-Signature"])
        self.assertIn('nonce="' + NONCE + '"', hdr["X-Signature"])
        self.assertEqual(hdr["version"], "2026-07-23")
        self.assertEqual(hdr["Date"], "Fri, 20 Nov 2026 01:00:00 +0000")

    def test_wrong_context_ref_attempt_rights_credentials_no_http(self):
        for key, value in (
            ("GITHUB_REF", "refs/heads/feature"),
            ("GITHUB_RUN_ATTEMPT", "2"),
            ("GITHUB_REPOSITORY", "attacker/MST"),
            ("GITHUB_WORKFLOW_REF", "other"),
            ("MST_DNSE_PROBE_CONFIRM", "NO"),
            ("MST_DNSE_READONLY_OWNER_ACCEPTED", "false"),
            ("MST_DNSE_SOURCE_RIGHTS_CONFIRMED", "false"),
            ("MST_DNSE_API_KEY", ""),
            ("MST_DNSE_API_SECRET", ""),
        ):
            with self.subTest(key=key):
                e, s = valid_env(), Session()
                e[key] = value
                with self.assertRaises(DnseProbeDenied):
                    run_probe(s, e, issued_at=NOW, nonce=NONCE)
                self.assertEqual(s.calls, [])

    def test_invalid_windows_prevent_any_request(self):
        for a, b in (
            ("2026-11-20", "2026-11-19"), ("2026-01-01", "2026-11-18"),
            ("2026-02-30", "2026-03-01"), ("2026/11/19", "2026-11-20"),
        ):
            e, s = valid_env(), Session()
            e["MST_DNSE_FROM_DATE"], e["MST_DNSE_TO_DATE"] = a, b
            with self.subTest(a=a, b=b), self.assertRaises(DnseProbeDenied):
                run_probe(s, e, issued_at=NOW, nonce=NONCE)
            self.assertFalse(s.calls)

    def test_no_empty_unordered_or_duplicate_timestamps(self):
        for data in (
            {**fake_payload(), "t": []},
            {**fake_payload(), "t": fake_payload()["t"][::-1]},
            {**fake_payload(), "t": [fake_payload()["t"][0]]*2},
            {**fake_payload(), "t": [0, 1]},
        ):
            with self.subTest(data=data), self.assertRaises(DnseProbeDenied):
                run_probe(Session(data), valid_env(), issued_at=NOW, nonce=NONCE)

    def test_ohlc_and_volume_constraints(self):
        for part, values in (
            ("h", [18, 20]),
            ("l", [22, 18]),
            ("c", [0, 19]),
            ("o", [float("nan"), 19]),
            ("v", [-1, 200]),
            ("v", [1.3, 200]),
        ):
            bad = fake_payload()
            bad[part] = values
            with self.subTest(part=part, values=values), self.assertRaises(DnseProbeDenied):
                _validate_native(bad, *require_owner_and_window(valid_env())[1:3])

    def test_malformed_response_and_excess_rows_rejected(self):
        orig = fake_payload()
        for bad in (
            {}, {"t": []}, {**orig, "v": [1]},
            {**orig, "nextTime": -1}, {**orig, "nextTime": "0"},
            {**orig, "t": orig["t"] * 251},
        ):
            with self.subTest(bad=type(bad).__name__), self.assertRaises(DnseProbeDenied):
                run_probe(Session(bad), valid_env(), issued_at=NOW, nonce=NONCE)

    def test_nexttime_hint_is_not_completeness_attestation(self):
        p = fake_payload()
        p["nextTime"] = p["t"][-1] + 3600
        out = run_probe(Session(p), valid_env(), issued_at=NOW, nonce=NONCE)
        self.assertTrue(out["provider_pagination_hint_present"])
        self.assertFalse(out["source_window_complete_attested"])

    def test_provider_error_or_exception_never_prints_payload(self):
        e = valid_env()
        s = Session({"SECRET_TOKEN": "do-not-print"}, 403)
        with self.assertRaisesRegex(DnseProbeDenied, "^MST_234_DNSE_HTTP_DENIED$"):
            run_probe(s, e, issued_at=NOW, nonce=NONCE)
        class Broken:
            def get(self, *args, **kwargs):
                raise RuntimeError("SECRET_HTTP_HEADER_IN_EXCEPTION")
        with self.assertRaisesRegex(DnseProbeDenied, "^MST_234_DNSE_TRANSPORT_OR_PARSE_FAILED$"):
            run_probe(Broken(), e, issued_at=NOW, nonce=NONCE)

    def test_invalid_signing_context_denied(self):
        for nonce in ("x", "X"*32, "0"*33):
            with self.subTest(nonce=nonce), self.assertRaises(DnseProbeDenied):
                make_signed_headers("key", "secret", NOW, nonce)
        with self.assertRaises(DnseProbeDenied):
            make_signed_headers("key", "secret", NOW.replace(tzinfo=None), NONCE)

    def test_market_prices_and_secrets_never_in_receipt(self):
        e = valid_env()
        r = run_probe(Session(), e, issued_at=NOW, nonce=NONCE)
        blob = json.dumps(r)
        self.assertNotIn("test_secret_12345", blob)
        for k in ("o", "h", "l", "c", "v", "API_KEY", "API_SECRET"):
            self.assertNotIn('"' + k + '"', blob)


if __name__ == "__main__":
    unittest.main()
