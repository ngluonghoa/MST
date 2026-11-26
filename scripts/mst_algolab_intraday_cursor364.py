"""§364 private paginated Algolab M1 diagnostic; no source admission."""
from datetime import date, datetime
from hashlib import sha256
import json
import re

from scripts.mst_algolab_intraday_scope339 import (
    SOURCE, COLUMNS, UNITS, _minute, _utc, AlgolabIngressDenied,
)
from swing_trading.hose_session_geometry210 import REGULAR_WINDOWS

SCHEMA = "mst.private.algolab_m1_cursor_chain.v0.1"
WINDOW = frozenset(m for lo, hi, _ in REGULAR_WINDOWS for m in range(lo, hi))
ATC = 14 * 60 + 45


def _deny(code):
    raise AlgolabIngressDenied("MST_364_" + code)


def _clock(value):
    if type(value) is not str:
        _deny("CAPTURE_CLOCK")
    try:
        parsed = datetime.fromisoformat(value)
        return _utc(parsed)
    except (ValueError, TypeError, AttributeError):
        _deny("CAPTURE_CLOCK")


def _scope(symbol, days, limit):
    if type(symbol) is not str or re.fullmatch(r"[A-Z]{3}", symbol) is None:
        _deny("SYMBOL")
    if (type(days) is not tuple or not 1 <= len(days) <= 21
            or any(type(day) is not date for day in days)
            or tuple(sorted(set(days))) != days):
        _deny("OBSERVED_DATE_SCOPE")
    if (days[-1] - days[0]).days > 31 or type(limit) is not int or not 1 <= limit <= 1000:
        _deny("BOUNDED_REQUEST")
    return {"symbol": symbol, "interval": "1m", "from_date": days[0].isoformat(),
            "to_date": days[-1].isoformat(), "limit": limit}


def _request(page, base, cursor):
    if type(page) is not dict or set(page) != {
            "request", "retrievalStartedUtc", "retrievalFinishedUtc", "response"}:
        _deny("PAGE_SHAPE")
    wanted = dict(base)
    if cursor is not None:
        wanted["cursor"] = cursor
    if type(page["request"]) is not dict or page["request"] != wanted:
        _deny("REQUEST_CHAIN")
    if type(page["request"].get("limit")) is not int:
        _deny("REQUEST_CHAIN")


def _envelope(response, symbol, limit):
    if type(response) is not dict or response.get("status") != "ok":
        _deny("SOURCE_STATUS")
    data, meta = response.get("data"), response.get("meta")
    if (type(data) is not dict or type(meta) is not dict
            or data.get("symbol") != symbol or data.get("kind") != "stock"
            or data.get("interval") != "1m"
            or meta.get("function") != "get_price_history"
            or meta.get("source") != SOURCE or meta.get("units") != UNITS
            or meta.get("truncated") is not False or "next_cursor" not in meta):
        _deny("SOURCE_PRODUCT")
    bars = data.get("bars")
    if type(bars) is not dict or bars.get("columns") != COLUMNS:
        _deny("COLUMNS")
    rows = bars.get("rows")
    if (type(rows) is not list or not 1 <= len(rows) <= limit
            or type(meta.get("count")) is not int or meta["count"] != len(rows)):
        _deny("PAGE_COUNT")
    cursor = meta["next_cursor"]
    if cursor is not None and (
            type(cursor) is not str or not cursor or len(cursor) > 1024
            or cursor.strip() != cursor or len(rows) != limit):
        _deny("CURSOR_SHAPE")
    return rows, meta, cursor


def _row(row, days, finish):
    if type(row) is not list or len(row) != len(COLUMNS):
        _deny("ROW_SHAPE")
    label = row[0]
    if type(label) is not str:
        _deny("ROW_LABEL")
    try:
        day = date.fromisoformat(label[:10])
    except ValueError:
        _deny("ROW_LABEL")
    if day not in days:
        _deny("UNEXPECTED_OBSERVED_DATE")
    minute, stamp = _minute(label, day)
    if stamp > finish or (minute not in WINDOW and minute != ATC):
        _deny("ROW_SESSION_OR_FUTURE")
    if any(type(x) is not int for x in row[1:]):
        _deny("ROW_NUMBER")
    o, h, low, c, v, value = row[1:]
    if min(o, h, low, c) <= 0 or h < max(o, low, c) or low > min(o, c) or min(v, value) < 0:
        _deny("ROW_OHLCV")
    return day, minute, stamp


def inspect_algolab_m1_cursor_chain(*, symbol, observed_days, limit, pages):
    """Verify one bounded retrospective cursor chain, not causal availability.

    Dates are caller-declared observed anchors, NOT an official calendar.
    Page as_of is only a reported last-row label on this observed product.
    Preserve retrieval clocks separately; an exhausted cursor proves neither
    omitted no-trade minutes nor an immutable historical provider snapshot.
    """
    base = _scope(symbol, observed_days, limit)
    if type(pages) is not tuple or not 1 <= len(pages) <= 7:
        _deny("IMMUTABLE_BOUNDED_PAGES")
    days = set(observed_days)
    seen_cursors = set()
    observed = {day: set() for day in observed_days}
    count = proxy = zero = 0
    cursor = previous_first = previous_finish = None
    for i, page in enumerate(pages):
        if i and cursor is None:
            _deny("PAGE_AFTER_EXHAUSTION")
        _request(page, base, cursor)
        start = _clock(page["retrievalStartedUtc"])
        finish = _clock(page["retrievalFinishedUtc"])
        if finish < start or (previous_finish is not None and start < previous_finish):
            _deny("CAPTURE_ORDER")
        rows, meta, cursor = _envelope(page["response"], symbol, limit)
        if cursor is not None:
            if cursor in seen_cursors:
                _deny("CURSOR_CYCLE")
            seen_cursors.add(cursor)
        previous_stamp = first = None
        for row in rows:
            day, minute, stamp = _row(row, days, finish)
            if previous_stamp is not None and stamp <= previous_stamp:
                _deny("PAGE_ROW_ORDER")
            if minute in observed[day]:
                _deny("DUPLICATE_LABEL")
            observed[day].add(minute)
            first = stamp if first is None else first
            previous_stamp = stamp
            count += 1
            zero += int(row[5] == 0)
            proxy += int(row[6] == row[4] * row[5])
        if previous_first is not None and previous_stamp >= previous_first:
            _deny("PAGE_RANGE_OVERLAP_OR_ORDER")
        if meta.get("as_of") != rows[-1][0]:
            _deny("PAGE_AS_OF_NOT_LAST_ROW")
        previous_first, previous_finish = first, finish
    if cursor is not None:
        _deny("CURSOR_NOT_EXHAUSTED")
    if any(not minutes for minutes in observed.values()):
        _deny("MISSING_OBSERVED_DATE")
    try:
        digest = sha256(json.dumps(
            {"schema": SCHEMA, "request": base,
             "observed_days": [d.isoformat() for d in observed_days], "pages": pages},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
        ).encode()).hexdigest()
    except (TypeError, ValueError, OverflowError):
        _deny("NONCANONICAL_CAPTURE")
    return {
        "schema": SCHEMA, "capture_sha256": digest, "page_count": len(pages),
        "observed_date_count": len(days), "observed_row_count": count,
        "missing_continuous_label_count": sum(len(WINDOW - m) for m in observed.values()),
        "auction_label_count": sum(ATC in m for m in observed.values()),
        "reported_zero_volume_count": zero, "close_times_volume_equal_count": proxy,
        "cursor_exhausted": True, "page_as_of_equals_last_row": True,
        "page_as_of_is_retrieval_clock": False, "historical_first_known_attested": False,
        "official_calendar_attested": False, "minute_coverage_attested": False,
        "raw_matched_volume_independently_attested": False,
        "exact_turnover_attested": False, "immutable_provider_snapshot_attested": False,
        "source_rights_attested": False, "production_cache_eligible": False,
        "signal_eligible": False,
    }
