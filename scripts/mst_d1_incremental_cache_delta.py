"""MST deterministic D1 source Cache delta planner; pure Cloud QA-only logic.

Source rolling-window exits MUST NOT delete historical Cache versions.
No I/O, auth, publisher, Signal Engine or trade actions in this module.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from typing import Any, Mapping


class DeltaDenied(ValueError):
    """Static fail-closed codes; never include source data in messages."""


OLD_SCHEMA = "mst.mcp.d1.private_drive_snapshot.v0.2"
NEW_SCHEMA = "mst.private_connector_d1_cache_capture.v1"
PROVIDERS = ("SSI", "DNSE", "VCBS")
MAX_ROWS = 5000
MAX_UNIX = 253402300799


def _digest(value: object) -> str:
    try:
        raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, OverflowError):
        raise DeltaDenied("MST_DELTA_BAD_JSON") from None
    return sha256(raw).hexdigest()


def _num(value: object, *, price: bool) -> Decimal:
    if type(value) not in (int, float, str):
        raise DeltaDenied("MST_DELTA_BAD_NUMBER_TYPE")
    raw = str(value)
    if not raw or len(raw) > 120:
        raise DeltaDenied("MST_DELTA_OVERSIZED_NUMBER")
    try:
        number = Decimal(raw)
    except InvalidOperation:
        raise DeltaDenied("MST_DELTA_BAD_NUMBER") from None
    if not number.is_finite() or (number <= 0 if price else number < 0):
        raise DeltaDenied("MST_DELTA_BAD_NUMBER_RANGE")
    return number


def _date(row: dict[str, Any], provider: str) -> str:
    try:
        if provider == "SSI":
            value = row["trading_date"]
            if type(value) is not str or not re.fullmatch(r"[0-9]{2}/[0-9]{2}/[0-9]{4}", value):
                raise ValueError()
            return datetime.strptime(value, "%d/%m/%Y").date().isoformat()
        if provider == "VCBS":
            value = row["tradingDate"]
            if type(value) is not str or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                raise ValueError()
            return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
        ts = row["source_unix_seconds"]
        if type(ts) is not int or not 0 < ts <= MAX_UNIX:
            raise ValueError()
        date = datetime.fromtimestamp(ts, timezone.utc).date().isoformat()
        if row.get("date_utc", date) != date:
            raise ValueError()
        return date
    except (ValueError, KeyError, OverflowError, OSError, TypeError):
        raise DeltaDenied("MST_DELTA_INVALID_DATE") from None


def _values(row: dict[str, Any], provider: str) -> tuple[Decimal, ...]:
    fields = (("openPrice", "highPrice", "lowPrice", "closePrice", "volume")
              if provider == "VCBS" else ("open", "high", "low", "close", "volume"))
    try:
        values = tuple(_num(row[field], price=index < 4)
                       for index, field in enumerate(fields))
    except KeyError:
        raise DeltaDenied("MST_DELTA_MISSING_OHLCV") from None
    o, h, l, c, volume = values
    if h < max(o, c, l) or l > min(o, c):
        raise DeltaDenied("MST_DELTA_INVALID_OHLC")
    return values


def _dnse_day(timestamp: object) -> str:
    if type(timestamp) is not int or not 0 < timestamp <= MAX_UNIX:
        raise DeltaDenied("MST_DELTA_INVALID_DATE")
    try:
        return datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()
    except (ValueError, OverflowError, OSError):
        raise DeltaDenied("MST_DELTA_INVALID_DATE") from None


def _dnse_rows(value: object) -> list[dict[str, Any]]:
    if type(value) is not dict or type(value.get("nextTime")) is not int or value["nextTime"] != 0:
        raise DeltaDenied("MST_DELTA_DNSE_UNFINISHED_PAGE")
    fields = ("t", "o", "h", "l", "c", "v")
    if any(type(value.get(key)) is not list for key in fields):
        raise DeltaDenied("MST_DELTA_DNSE_BAD_ARRAYS")
    n = len(value["t"])
    if not 1 <= n <= MAX_ROWS or any(len(value[key]) != n for key in fields):
        raise DeltaDenied("MST_DELTA_DNSE_BAD_ARRAYS")
    return [
        {"source_unix_seconds": value["t"][i], "date_utc": _dnse_day(value["t"][i]),
         "open": value["o"][i], "high": value["h"][i],
         "low": value["l"][i], "close": value["c"][i], "volume": value["v"][i]}
        for i in range(n)
    ]


def _snapshot(source: object, provider: str, symbol: str) -> tuple[dict[str, dict[str, Any]], str]:
    if type(source) is not dict or source.get("schema") not in (OLD_SCHEMA, NEW_SCHEMA):
        raise DeltaDenied("MST_DELTA_UNKNOWN_SCHEMA")
    if source.get("provider") != provider or source.get("symbol") != symbol or source.get("timeframe") != "D1":
        raise DeltaDenied("MST_DELTA_PROVIDER_SYMBOL_TF_DRIFT")
    if source["schema"] == OLD_SCHEMA:
        rows = source.get("rows")
        expected = source.get("retained_row_count")
    else:
        native = source.get("native_source_data")
        rows = (_dnse_rows(native) if provider == "DNSE"
                else native.get("data") if provider == "VCBS" and type(native) is dict
                else native)
        expected = source.get("source_rows_observed")
    if (type(rows) is not list or type(expected) is not int
            or not 1 <= len(rows) <= MAX_ROWS or len(rows) != expected):
        raise DeltaDenied("MST_DELTA_COUNT_MISMATCH")
    mapped: dict[str, dict[str, Any]] = {}
    for row in rows:
        if type(row) is not dict:
            raise DeltaDenied("MST_DELTA_BAD_ROW")
        if provider == "SSI" and row.get("symbol") != symbol:
            raise DeltaDenied("MST_DELTA_ROW_SYMBOL_DRIFT")
        date = _date(row, provider)
        _values(row, provider)
        if date in mapped:
            raise DeltaDenied("MST_DELTA_DUPLICATE_SESSION")
        mapped[date] = row
    return mapped, _digest(rows)


def plan_d1_delta(previous: Mapping[str, Any], current: Mapping[str, Any],
                  *, provider: str, symbol: str) -> dict[str, Any]:
    """No-write plan. Preserve source-native rows and both corrected versions."""
    if (provider not in PROVIDERS or type(symbol) is not str
            or not re.fullmatch(r"[A-Z]{3}", symbol)):
        raise DeltaDenied("MST_DELTA_UNSUPPORTED_IDENTITY")
    old, old_sha = _snapshot(previous, provider, symbol)
    new, new_sha = _snapshot(current, provider, symbol)
    overlap = sorted(old.keys() & new.keys())
    fields = (("openPrice", "highPrice", "lowPrice", "closePrice", "volume")
              if provider == "VCBS" else ("open", "high", "low", "close", "volume"))
    revisions = []
    for date in overlap:
        if _values(old[date], provider) != _values(new[date], provider):
            revisions.append({
                "date": date, "before": old[date], "after": new[date],
                "changed_fields": [f for f in fields
                                   if _num(old[date][f], price=f != "volume") !=
                                      _num(new[date][f], price=f != "volume")]
            })
    result = {
        "schema": "mst.private_d1_source_delta_plan.v1",
        "provider": provider, "symbol": symbol, "timeframe": "D1",
        "previous_sha256": old_sha, "current_sha256": new_sha,
        "added": [{"date": date, "source_row": new[date]}
                  for date in sorted(new.keys() - old.keys())],
        "revised": revisions,
        "window_exited_not_deleted": sorted(old.keys() - new.keys()),
        "unchanged_overlap": len(overlap) - len(revisions),
        "preserve_source_versions": True,
        "independent_signed_publish_cas": False,
        "venue_closed_bar_attested": False,
        "signal_eligible": False,
        "trade_orders": 0,
    }
    result["plan_sha256"] = _digest(result)
    return result
