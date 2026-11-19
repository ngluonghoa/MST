"""MST §230 isolated provider fingerprint regression: fictional data ONLY.

The native fingerprint is a diagnostic after producer-specific shape/rights
validation. It must never be interpreted as vendor signed proof or a market
Cache promotion. No network, credentials, Google Drive, real price rows.
"""
from __future__ import annotations

import copy
import hashlib
import json
import unittest

from scripts.mst_native_source_fingerprint import (
    NativeFingerprintDenied, MAX_CANONICAL_BYTES, SOURCE_PROVIDERS, TF,
    native_canonical_sha256,
)


def dnse():
    return {
        "t": [1794000000, 1794086400],
        "o": [10.5, 10.9],
        "h": [11.1, 11.5],
        "l": [10.1, 10.2],
        "c": [10.9, 11.2],
        "v": [100000, 120000],
        "nextTime": 0,
    }


def ssi():
    return [
        {
            "symbol": "AAA", "tradingDate": "2026-11-10",
            "open": "10500", "high": "11100", "low": "10100",
            "close": "10900", "volume": "100000",
        },
        {
            "symbol": "AAA", "tradingDate": "2026-11-11",
            "open": "10900", "high": "11500", "low": "10200",
            "close": "11200", "volume": "120000",
        },
    ]


class IsolatedNativeFingerprint230Tests(unittest.TestCase):
    def test_two_providers_and_five_supported_source_timeframes_only(self):
        self.assertEqual(set(SOURCE_PROVIDERS), {"DNSE", "SSI"})
        self.assertEqual(set(TF), {"D1", "H1", "M30", "M15", "M5"})

    def test_dnse_envelope_stable_under_top_level_dict_order(self):
        original = dnse()
        digest = native_canonical_sha256("DNSE", "AAA", "D1", original)
        reordered = {k: original[k] for k in reversed(tuple(original))}
        self.assertEqual(digest, native_canonical_sha256("DNSE", "AAA", "D1", reordered))
        self.assertEqual(len(digest), 64)
        self.assertEqual(digest, digest.lower())
        self.assertEqual(original, dnse())  # input is not mutated

    def test_native_digest_is_not_sha256_of_wire_json(self):
        payload = dnse()
        digest = native_canonical_sha256("DNSE", "AAA", "D1", payload)
        raw_wire_hash = hashlib.sha256(json.dumps(payload).encode()).hexdigest()
        self.assertNotEqual(digest, raw_wire_hash)

    def test_changes_in_data_or_row_order_change_digest(self):
        base = dnse()
        reference = native_canonical_sha256("DNSE", "AAA", "D1", base)
        for key, replacement in (
            ("t", [base["t"][1], base["t"][0]]),
            ("o", [10.6, base["o"][1]]),
            ("h", [11.2, base["h"][1]]),
            ("l", [10.0, base["l"][1]]),
            ("c", [11.0, base["c"][1]]),
            ("v", [base["v"][0] + 1, base["v"][1]]),
        ):
            changed = copy.deepcopy(base)
            changed[key] = replacement
            with self.subTest(field=key):
                self.assertNotEqual(
                    reference, native_canonical_sha256("DNSE", "AAA", "D1", changed)
                )

    def test_identity_partition_covers_provider_symbol_timeframe(self):
        base = dnse()
        reference = native_canonical_sha256("DNSE", "AAA", "D1", base)
        for symbol, tf in (("BBB", "D1"), ("AAA", "M5"), ("AAA", "H1")):
            with self.subTest(symbol=symbol, tf=tf):
                self.assertNotEqual(
                    reference, native_canonical_sha256("DNSE", symbol, tf, base)
                )
        self.assertNotEqual(
            reference,
            native_canonical_sha256("SSI", "AAA", "D1", ssi())
        )

    def test_unknown_provider_symbol_and_timeframe_rejected(self):
        for p, symbol, tf, native in (
            ("VCBS", "AAA", "D1", dnse()),
            ("DNSE", "AAAA", "D1", dnse()),
            ("DNSE", "aaA", "D1", dnse()),
            ("DNSE", "AAA", "H4", dnse()),
            ("DNSE", "AAA", "W1", dnse()),
            ("SSI", "AAA", "1D", ssi()),
            ("", "AAA", "D1", dnse()),
        ):
            with self.subTest(p=p, symbol=symbol, tf=tf), self.assertRaisesRegex(
                NativeFingerprintDenied, "IDENTITY_INVALID"
            ):
                native_canonical_sha256(p, symbol, tf, native)

    def test_dnse_rejects_pagination_or_unknown_fields(self):
        base = dnse()
        for mutation in (
            {"nextTime": 12345678},
            {"nextTime": "0"},
            {"token": "FAKE_SECRET_NOT_A_REAL_TOKEN"},
            {"broker_account": "FAKE_ACCOUNT"},
        ):
            with self.subTest(keys=list(mutation)), self.assertRaisesRegex(
                NativeFingerprintDenied, "DNSE_FIELDS_INVALID"
            ):
                native_canonical_sha256("DNSE", "AAA", "D1", {**base, **mutation})

    def test_dnse_rejects_empty_malformed_or_different_array_lengths(self):
        for payload in (
            {**dnse(), "o": []},
            {**dnse(), "v": [100000]},
            {**dnse(), "t": []},
            {**dnse(), "t": "not a list"},
            {**dnse(), "t": [1] * 2049, "o": [1] * 2049,
             "h": [1] * 2049, "l": [1] * 2049,
             "c": [1] * 2049, "v": [1] * 2049},
        ):
            with self.assertRaisesRegex(
                NativeFingerprintDenied, "DNSE_FIELDS_INVALID"
            ):
                native_canonical_sha256("DNSE", "AAA", "D1", payload)

    def test_ssi_preserves_native_row_order_and_numeric_text(self):
        rows = ssi()
        original = native_canonical_sha256("SSI", "AAA", "D1", rows)
        self.assertNotEqual(
            original,
            native_canonical_sha256("SSI", "AAA", "D1", list(reversed(rows)))
        )
        changed = copy.deepcopy(rows)
        changed[0]["close"] = "10900.0"
        self.assertNotEqual(
            original, native_canonical_sha256("SSI", "AAA", "D1", changed)
        )

    def test_ssi_strict_column_names_and_symbol_scoping(self):
        rows = ssi()
        for change in (
            dict(rows[0], symbol="BBB"),
            dict(rows[0], account="FAKE_ACCOUNT"),
            {k: v for k, v in rows[0].items() if k != "tradingDate"},
            dict(rows[0], tradingDate=12345),
        ):
            with self.subTest(fields=list(change)), self.assertRaisesRegex(
                NativeFingerprintDenied, "SSI_FIELDS_INVALID"
            ):
                native_canonical_sha256("SSI", "AAA", "D1", [change, rows[1]])

    def test_ssi_rows_bounded(self):
        for rows in ([], ssi() * 251, [42]):
            with self.assertRaisesRegex(
                NativeFingerprintDenied, "SSI_FIELDS_INVALID"
            ):
                native_canonical_sha256("SSI", "AAA", "D1", rows)

    def test_noncanonical_nan_infinity_and_unserializable_denied(self):
        for bad in (float("nan"), float("inf"), object()):
            data = dnse()
            data["c"][0] = bad
            with self.subTest(type=str(type(bad))), self.assertRaisesRegex(
                NativeFingerprintDenied, "NONCANONICAL"
            ):
                native_canonical_sha256("DNSE", "AAA", "D1", data)

    def test_canonical_size_limit(self):
        payload = dnse()
        payload["o"][0] = "x" * (MAX_CANONICAL_BYTES + 1)
        with self.assertRaisesRegex(NativeFingerprintDenied, "SIZE_INVALID"):
            native_canonical_sha256("DNSE", "AAA", "D1", payload)

    def test_errors_never_contain_provider_input_or_secret(self):
        secret = "FAKE_NOT_A_REAL_CREDENTIAL"
        bad = {**dnse(), "authToken": secret}
        with self.assertRaises(NativeFingerprintDenied) as ctx:
            native_canonical_sha256("DNSE", "AAA", "D1", bad)
        self.assertNotIn(secret, str(ctx.exception))
        self.assertNotIn(str(bad), str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
