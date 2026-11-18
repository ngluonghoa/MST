"""Provider-partitioned canonical native-source fingerprint, diagnostics only.

A SHA-256 over sanitized source-native data + explicit symbol/TF/provider
context is useful for private quarantine/overlap audit. It is NOT:
- a hash of the original HTTP wire bytes, an issuer digital signature,
- proof of a vendor contract, source first-known/venue finality,
- a distributed CAS or a promotion into signals/backtests.
Only called after provider-specific shape/OHLCV validation.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

TF = frozenset(("D1", "H1", "M30", "M15", "M5"))
DNSE_KEYS = frozenset(("t", "o", "h", "l", "c", "v", "nextTime"))
SSI_KEYS = frozenset((
    "symbol", "tradingDate", "open", "high", "low", "close", "volume"
))
MAX_CANONICAL_BYTES = 1_500_000
SOURCE_PROVIDERS = ("DNSE", "SSI")


class NativeFingerprintDenied(ValueError):
    """Never expose native prices, tokens or row contents in errors."""


def native_canonical_sha256(
    provider: str, symbol: str, timeframe: str, native: Any,
) -> str:
    """Hash exact sanitized provider-native values with contextual identity.

    Key order does not change the digest; row order and all stored values do.
    Numeric string formatting is NOT normalized here: this fingerprints the
    sanitized native payload, not economically equivalent price values.
    """
    if (type(provider) is not str or provider not in SOURCE_PROVIDERS
            or type(symbol) is not str
            or re.fullmatch(r"[A-Z]{3}", symbol) is None
            or type(timeframe) is not str or timeframe not in TF):
        raise NativeFingerprintDenied("MST_NATIVE_DIGEST_IDENTITY_INVALID")
    if provider == "DNSE":
        if (type(native) is not dict or set(native) != DNSE_KEYS
                or type(native["nextTime"]) is not int
                or native["nextTime"] != 0
                or any(type(native[k]) is not list for k in DNSE_KEYS
                       if k != "nextTime")
                or not 1 <= len(native["t"]) <= 2048
                or any(len(native[k]) != len(native["t"])
                       for k in ("o", "h", "l", "c", "v"))):
            raise NativeFingerprintDenied("MST_NATIVE_DIGEST_DNSE_FIELDS_INVALID")
    else:
        if (type(native) is not list or not 1 <= len(native) <= 500
                or any(type(row) is not dict or set(row) != SSI_KEYS
                       or row["symbol"] != symbol
                       or type(row["tradingDate"]) is not str
                       for row in native)):
            raise NativeFingerprintDenied("MST_NATIVE_DIGEST_SSI_FIELDS_INVALID")
    envelope = {
        "schema": "mst.private.native_payload_fingerprint.v0.1",
        "provider": provider,
        "symbol": symbol,
        "native_timeframe": timeframe,
        "native": native,
    }
    try:
        data = json.dumps(
            envelope, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError):
        raise NativeFingerprintDenied("MST_NATIVE_DIGEST_NONCANONICAL") from None
    if not 0 < len(data) <= MAX_CANONICAL_BYTES:
        raise NativeFingerprintDenied("MST_NATIVE_DIGEST_SIZE_INVALID")
    return hashlib.sha256(data).hexdigest()
