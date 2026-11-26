"""Private connected Algolab stock intraday envelope, never canonical bars."""
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
import re

from swing_trading.hose_session_geometry210 import REGULAR_WINDOWS

SCHEMA = "mst.private.algolab_intraday_scope.v0.1"
SOURCE = "stock_intraday_1m (có nến ATC 14:45)"
COLUMNS = ["t", "o", "h", "l", "c", "v", "value"]
UNITS = {"price": "VND (giá thô)", "volume": "cp",
         "t": "giờ Việt Nam, đầu nến"}
STEPS = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60}
VN = timezone(timedelta(hours=7))
ATC = 14 * 60 + 45


class AlgolabIngressDenied(ValueError):
    """Fixed messages; never include source records."""


def _minute(label, day):
    if type(label) is not str or re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\+07:00", label
    ) is None:
        raise AlgolabIngressDenied("MST_339_LABEL_SHAPE")
    try:
        stamp = datetime.fromisoformat(label)
    except ValueError:
        raise AlgolabIngressDenied("MST_339_LABEL_SHAPE") from None
    if stamp.date() != day or stamp.utcoffset() != VN.utcoffset(None):
        raise AlgolabIngressDenied("MST_339_LABEL_DAY")
    return stamp.hour * 60 + stamp.minute, stamp


def _utc(value):
    if type(value) is not datetime or value.utcoffset() != timedelta(0):
        raise AlgolabIngressDenied("MST_339_CAPTURE_CLOCK")
    return value


def inspect_algolab_stock_intraday(*, response, symbol, day, interval,
                                   started, finished):
    """One explicitly requested HOSE regular-day hypothesis, private only.

    The caller supplies an observation captured for this symbol/day/interval.
    Source-reported START/RAW is not an independently certified clock/basis.
    No provenance is inferred for SSI, no missing positions are synthesized.
    """
    if (type(symbol) is not str or re.fullmatch(r"[A-Z]{3}", symbol) is None
            or type(day) is not date or type(interval) is not str
            or interval not in STEPS):
        raise AlgolabIngressDenied("MST_339_SCOPE")
    if _utc(finished) < _utc(started):
        raise AlgolabIngressDenied("MST_339_CAPTURE_CLOCK")
    if type(response) is not dict or response.get("status") != "ok":
        raise AlgolabIngressDenied("MST_339_SOURCE_STATUS")
    data, meta = response.get("data"), response.get("meta")
    if (type(data) is not dict or type(meta) is not dict
            or data.get("symbol") != symbol or data.get("kind") != "stock"
            or data.get("interval") != interval
            or meta.get("function") != "get_price_history"
            or meta.get("source") != SOURCE or meta.get("units") != UNITS
            or meta.get("truncated") is not False
            or "next_cursor" not in meta or meta["next_cursor"] is not None):
        raise AlgolabIngressDenied("MST_339_ENDPOINT_SCOPE_OR_BASIS")
    as_of_minute, as_of = _minute(meta.get("as_of"), day)
    if as_of > finished:
        raise AlgolabIngressDenied("MST_339_FUTURE_OBSERVATION")
    bars = data.get("bars")
    if type(bars) is not dict or bars.get("columns") != COLUMNS:
        raise AlgolabIngressDenied("MST_339_COLUMNS")
    rows = bars.get("rows")
    if (type(rows) is not list or not 1 <= len(rows) <= 226
            or type(meta.get("count")) is not int
            or meta["count"] != len(rows)):
        raise AlgolabIngressDenied("MST_339_COUNT")
    n = STEPS[interval]
    continuous = set(m for lo, hi, _ in REGULAR_WINDOWS for m in range(lo, hi))
    # Provider wall-clock grouping can label 09:00 before continuous trading.
    expected = {m // n * n for m in continuous}
    auction_bucket = ATC // n * n
    expected.add(auction_bucket)
    observed = set()
    last = -1
    reported_zero = 0
    for row in rows:
        if type(row) is not list or len(row) != len(COLUMNS):
            raise AlgolabIngressDenied("MST_339_ROW_SHAPE")
        minute, _ = _minute(row[0], day)
        if minute <= last or minute not in expected or minute > as_of_minute:
            raise AlgolabIngressDenied("MST_339_LABEL_ORDER_OR_SCOPE")
        o, h, low, c, v, value = row[1:]
        if (any(type(x) is not int for x in row[1:])
                or min(o, h, low, c) <= 0 or h < max(o, low, c)
                or low > min(o, c) or min(v, value) < 0):
            raise AlgolabIngressDenied("MST_339_OHLCV")
        last = minute
        observed.add(minute)
        reported_zero += int(v == 0)
    try:
        digest = sha256(json.dumps(
            {"schema": SCHEMA, "symbol": symbol, "day": day.isoformat(),
             "interval": interval, "started": started.isoformat(),
             "finished": finished.isoformat(), "response": response},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode()).hexdigest()
    except (ValueError, TypeError, OverflowError):
        raise AlgolabIngressDenied("MST_339_NONCANONICAL") from None
    return {
        "schema": SCHEMA, "capture_sha256": digest, "interval": interval,
        "source_declared_label": "START", "source_declared_basis": "RAW_VND",
        "source_product": "ALGOLAB_CONNECTED_STOCK_INTRADAY_1M",
        "higher_tf_derived_product": n != 1,
        "observed_bucket_count": len(observed),
        "missing_expected_wall_clock_buckets": len(expected - observed),
        "source_reported_zero_volume_rows": reported_zero,
        "missing_is_zero": False,
        "bucket_presence_proves_minute_coverage": False,
        "auction_bucket_observed": auction_bucket in observed,
        "auction_bucket_may_mix_continuous": auction_bucket in {
            m // n * n for m in continuous
        },
        "session_anchor_incompatible": n in (30, 60),
        "source_clock_independently_attested": False,
        "price_basis_independently_attested": False,
        "first_known_attested": False, "calendar_attested": False,
        "source_rights_attested": False, "native_tf_qualified": False,
        "production_cache_eligible": False, "signal_eligible": False,
    }
