#!/usr/bin/env python3
"""§234 DNSE signed, manual GitHub main-only OHLC observation. NO_TRADE.

No broker/order endpoints, Drive writes, source-series output, or claimed rights.
The DNSE official historical OHLC endpoint and HMAC auth are read-only.
"""
from __future__ import annotations

import base64
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from email.utils import format_datetime
import hashlib
import hmac
import json
import os
import re
import uuid
from typing import Any, Mapping

from scripts.mst_mfx_native_timeframes import (
    MAX_SINGLE_PROBE_CALENDAR_DAYS, provider_resolution,
)

URL = "https://openapi.dnse.com.vn/price/ohlc"
PATH = "/price/ohlc"
API_VERSION = "2026-07-23"
SYMBOLS = ("FPT", "HPG", "DCM")
MAX_ROWS = 500
MAX_BYTES = 250_000
CONTEXT = {
    "GITHUB_REPOSITORY": "ngluonghoa/MST",
    "GITHUB_REPOSITORY_ID": "1450356304",
    "GITHUB_REPOSITORY_OWNER_ID": "353049266",
    "GITHUB_REF": "refs/heads/main",
    "GITHUB_EVENT_NAME": "workflow_dispatch",
    "GITHUB_WORKFLOW_REF": (
        "ngluonghoa/MST/.github/workflows/"
        "mst-dnse-native-readonly-manual.yml@refs/heads/main"
    ),
    "GITHUB_RUN_ATTEMPT": "1",
    "MST_DNSE_PROBE_CONFIRM": "READ_DNSE_ONLY",
    "MST_DNSE_READONLY_OWNER_ACCEPTED": "true",
    "MST_DNSE_SOURCE_RIGHTS_CONFIRMED": "true",
}


class DnseProbeDenied(ValueError):
    """Only use authored safe error identifiers; never provider error text."""


def require_owner_and_window(env: Mapping[str, str]) -> tuple[str, int, int, str]:
    if (not isinstance(env, Mapping)
            or any(env.get(k) != v for k, v in CONTEXT.items())):
        raise DnseProbeDenied("MST_234_MAIN_OWNER_RIGHTS_GATE_REQUIRED")
    key, secret = env.get("MST_DNSE_API_KEY"), env.get("MST_DNSE_API_SECRET")
    if (type(key) is not str or not re.fullmatch(r"[A-Za-z0-9_\-]{8,128}", key)
            or type(secret) is not str or not 8 <= len(secret) <= 256
            or any(ord(ch) < 33 or ord(ch) > 126 for ch in secret)):
        raise DnseProbeDenied("MST_234_DNSE_API_CREDENTIALS_REQUIRED")
    symbol, tf = env.get("MST_DNSE_SYMBOL"), env.get("MST_SOURCE_TF")
    if symbol not in SYMBOLS:
        raise DnseProbeDenied("MST_234_SYMBOL_DENIED")
    try:
        resolution = provider_resolution("DNSE", tf)
        start_text, end_text = env["MST_DNSE_FROM_DATE"], env["MST_DNSE_TO_DATE"]
        if (type(start_text) is not str or type(end_text) is not str
                or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", start_text)
                or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", end_text)):
            raise ValueError("date format")
        start_day, end_day = date.fromisoformat(start_text), date.fromisoformat(end_text)
        days = (end_day - start_day).days + 1
        if not 1 <= days <= MAX_SINGLE_PROBE_CALENDAR_DAYS[tf]:
            raise ValueError("window out of bounds")
        start = int(datetime.combine(
            start_day, time.min, tzinfo=timezone(timedelta(hours=7))
        ).timestamp())
        end = int(datetime.combine(
            end_day + timedelta(days=1), time.min,
            tzinfo=timezone(timedelta(hours=7))
        ).timestamp())
    except (KeyError, TypeError, ValueError, OverflowError):
        raise DnseProbeDenied("MST_234_NATIVE_TF_OR_WINDOW_DENIED") from None
    return resolution, start, end, symbol


def make_signed_headers(
    key: str, secret: str, issued_at: datetime, nonce: str
) -> dict[str, str]:
    """DNSE documented HMAC-SHA256 signing string; no body or account action."""
    if (issued_at.tzinfo is None or issued_at.utcoffset() != timedelta(0)
            or type(nonce) is not str or not re.fullmatch(r"[0-9a-f]{32}", nonce)):
        raise DnseProbeDenied("MST_234_SIGNING_CONTEXT_INVALID")
    stamp = format_datetime(issued_at)
    payload = ("(request-target): get " + PATH + "\ndate: " + stamp +
               "\nnonce: " + nonce).encode("utf-8")
    signed = base64.b64encode(
        hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
    ).decode("ascii")
    encoded = signed.replace("+", "%2B").replace("/", "%2F").replace("=", "%3D")
    return {
        "X-API-Key": key,
        "Date": stamp,
        "version": API_VERSION,
        "X-Signature": (
            'Signature keyId="' + key +
            '",algorithm="hmac-sha256",headers="(request-target) date",signature="' +
            encoded + '",nonce="' + nonce + '"'
        ),
    }


def _validate_native(payload: Any, start: int, end: int) -> tuple[int, bool]:
    if type(payload) is not dict:
        raise DnseProbeDenied("MST_234_OHLC_SHAPE_INVALID")
    labels = ("t", "o", "h", "l", "c", "v")
    series = [payload.get(field) for field in labels]
    if (any(type(item) is not list for item in series)
            or not 1 <= len(series[0]) <= MAX_ROWS
            or any(len(item) != len(series[0]) for item in series[1:])):
        raise DnseProbeDenied("MST_234_OHLC_LENGTH_INVALID")
    prev = None
    for index, stamp in enumerate(series[0]):
        if (type(stamp) is not int or not start <= stamp < end
                or (prev is not None and stamp <= prev)):
            raise DnseProbeDenied("MST_234_OHLC_TIMESTAMP_INVALID")
        prev = stamp
        numbers = []
        for values in series[1:5]:
            value = values[index]
            if type(value) not in (int, float, str):
                raise DnseProbeDenied("MST_234_OHLC_PRICE_INVALID")
            try:
                amount = Decimal(str(value))
            except InvalidOperation:
                raise DnseProbeDenied("MST_234_OHLC_PRICE_INVALID") from None
            if not amount.is_finite() or amount <= 0:
                raise DnseProbeDenied("MST_234_OHLC_PRICE_INVALID")
            numbers.append(amount)
        o, h, l, c = numbers
        if not l <= min(o, c) <= max(o, c) <= h:
            raise DnseProbeDenied("MST_234_OHLC_INVARIANT_FAILED")
        volume = series[5][index]
        if type(volume) is not int or volume < 0:
            raise DnseProbeDenied("MST_234_OHLC_VOLUME_INVALID")
    next_time = payload.get("nextTime")
    if type(next_time) is not int or next_time < 0:
        raise DnseProbeDenied("MST_234_NEXTTIME_UNVERIFIED")
    # nextTime=0 is not official completeness/first-known attestation either.
    return len(series[0]), next_time != 0


def run_probe(
    session: Any, env: Mapping[str, str], *,
    issued_at: datetime | None = None, nonce: str | None = None,
) -> dict[str, object]:
    resolution, start, end, symbol = require_owner_and_window(env)
    when = issued_at if issued_at is not None else datetime.now(timezone.utc)
    ident = nonce if nonce is not None else uuid.uuid4().hex
    headers = make_signed_headers(
        env["MST_DNSE_API_KEY"], env["MST_DNSE_API_SECRET"], when, ident
    )
    params = {
        "symbol": symbol, "type": "STOCK", "resolution": resolution,
        "from": start, "to": end,
    }
    try:
        response = session.get(
            URL, params=params, headers=headers, timeout=20,
            allow_redirects=False,
        )
        if response.status_code != 200:
            raise DnseProbeDenied("MST_234_DNSE_HTTP_DENIED")
        raw = response.content
        if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES:
            raise DnseProbeDenied("MST_234_DNSE_RESPONSE_BOUNDS")
        data = json.loads(raw)
    except DnseProbeDenied:
        raise
    except Exception:
        raise DnseProbeDenied("MST_234_DNSE_TRANSPORT_OR_PARSE_FAILED") from None
    count, pagination = _validate_native(data, start, end)
    return {
        "schema": "mst.cloud.dnse_native_readonly_receipt.v0.1",
        "status": "MST_234_DNSE_NATIVE_READONLY_PROBE_PASS",
        "source": "DNSE_OFFICIAL_OPENAPI",
        "timeframe": env["MST_SOURCE_TF"],
        "native_source_rows_observed": count,
        "provider_pagination_hint_present": pagination,
        "ohlcv_local_invariants_verified": True,
        "source_window_complete_attested": False,
        "historical_first_known_and_closed_attested": False,
        "price_unit_and_adjustment_basis_attested": False,
        "provider_source_rights_independently_attested": False,
        "data_written_to_drive": False,
        "market_cache_promoted": False,
        "signals_and_trading_eligible": False,
    }


def main() -> None:
    try:
        import requests
    except Exception:
        raise DnseProbeDenied("MST_234_HTTPS_DEPENDENCY_UNAVAILABLE") from None
    print(json.dumps(run_probe(requests.Session(), os.environ), sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except DnseProbeDenied as exc:
        raise SystemExit(str(exc)) from None
