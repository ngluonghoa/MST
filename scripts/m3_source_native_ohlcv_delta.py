"""MST M3 - endpoint-specific source-native D1 OHLCV revision observer.

Pure typed offline comparator. It does not query vendors, access Google Drive,
write Cache V2, sign publisher first-known or authorize trading. Source rows and
their original values stay in PRIVATE storage; output lists only day labels,
changed field names, counts and recommended (not executed) dependency actions.

Same-provider/different-endpoint data are never treated as the same revision
stream. Provider-native price units/bases are compared only within identity.
An absent optional metadata key versus an explicit null is informational,
NOT a price or adjustment revision.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
import re
from typing import Any

_DAY_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DAY_DMY = re.compile(r"^\d{2}/\d{2}/\d{4}$")
_SYM = re.compile(r"^[A-Z0-9]{1,10}$")
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")


class DailyEndpoint(str, Enum):
    SSI_COMPACT = "SSI.marketdata_list_stock_daily_data"
    SSI_DETAILED = "SSI.marketdata_list_daily_stock_infor"
    DNSE_CONNECTED_DAY = "DNSE.price_get_history.DAY"
    VCBS_DAILY = "VCBS.vcbs_get_history.D"


_FIELDS = {
    DailyEndpoint.SSI_COMPACT: ("open", "high", "low", "close", "volume"),
    DailyEndpoint.SSI_DETAILED: ("open", "high", "low", "close", "volume"),
    DailyEndpoint.DNSE_CONNECTED_DAY: ("open", "high", "low", "close", "volume"),
    DailyEndpoint.VCBS_DAILY: ("openPrice", "highPrice", "lowPrice", "closePrice", "volume"),
}
_AUX = {
    DailyEndpoint.SSI_COMPACT: (),
    DailyEndpoint.SSI_DETAILED: (
        "close_price_adjusted", "open_raw", "high_raw", "low_raw", "close_raw",
    ),
    DailyEndpoint.DNSE_CONNECTED_DAY: (),
    DailyEndpoint.VCBS_DAILY: ("adjClosePrice", "adjFactor", "price", "priceBasis"),
}
_AUX_NUMERIC = frozenset((
    "close_price_adjusted", "open_raw", "high_raw", "low_raw", "close_raw",
    "adjClosePrice", "adjFactor", "price",
))


@dataclass(frozen=True)
class NativeD1Snapshot:
    endpoint: DailyEndpoint
    symbol: str
    price_basis: str
    unit: str
    observed_at_utc: datetime
    rows: tuple[dict[str, Any], ...]
    timeframe: str = "D1"
    issuer_first_known_verified: bool = False
    licensed_publisher_verified: bool = False

    def __post_init__(self) -> None:
        if type(self.endpoint) is not DailyEndpoint:
            raise TypeError("EXACT_ENDPOINT_PRODUCT_REQUIRED")
        if type(self.symbol) is not str or not _SYM.fullmatch(self.symbol):
            raise ValueError("CANONICAL_STOCK_SYMBOL_REQUIRED")
        for key in (self.price_basis, self.unit):
            if type(key) is not str or not _TOKEN.fullmatch(key):
                raise ValueError("SOURCE_NATIVE_PRICE_BASIS_UNIT_REQUIRED")
        if self.timeframe != "D1":
            raise ValueError("D1_ONLY_WITHOUT_UNVERIFIED_INTRADAY_PROMOTION")
        stamp = self.observed_at_utc
        if (type(stamp) is not datetime or stamp.tzinfo is None
                or stamp.utcoffset() != timedelta(0)):
            raise ValueError("UTC_LOCAL_RECEIPT_TIMESTAMP_REQUIRED")
        if (self.issuer_first_known_verified is not False
                or self.licensed_publisher_verified is not False):
            raise PermissionError("SELF_ATTESTED_VENDOR_RIGHTS_OR_FIRST_KNOWN_DENIED")
        if type(self.rows) is not tuple or not self.rows:
            raise ValueError("NONEMPTY_IMMUTABLE_SOURCE_ROWS_REQUIRED")
        seen: set[str] = set()
        for row in self.rows:
            if type(row) is not dict:
                raise TypeError("JSON_SOURCE_ROW_DICT_REQUIRED")
            day = _day(self.endpoint, row)
            if day in seen:
                raise ValueError("DUPLICATE_SOURCE_DAY_DENIED")
            seen.add(day)
            _values(self.endpoint, row)


def _number(value: Any, *, nonnegative: bool = True) -> Decimal:
    if type(value) not in (str, int, float, Decimal):
        raise ValueError("NUMERIC_SOURCE_FIELD_REQUIRED")
    if type(value) is str and not value.strip():
        raise ValueError("EMPTY_NUMERIC_SOURCE_FIELD")
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("INVALID_NUMERIC_SOURCE_FIELD") from None
    if not n.is_finite() or (nonnegative and n < 0):
        raise ValueError("FINITE_NONNEGATIVE_SOURCE_FIELD_REQUIRED")
    return n


def _day(endpoint: DailyEndpoint, row: dict[str, Any]) -> str:
    if endpoint in (DailyEndpoint.SSI_COMPACT, DailyEndpoint.SSI_DETAILED):
        raw = row.get("trading_date")
        if type(raw) is not str or not _DAY_DMY.fullmatch(raw):
            raise ValueError("SSI_LOCAL_DMY_SESSION_REQUIRED")
        d, m, y = map(int, raw.split("/"))
        parsed = date(y, m, d)
    else:
        key = "date_utc" if endpoint is DailyEndpoint.DNSE_CONNECTED_DAY else "tradingDate"
        raw = row.get(key)
        if type(raw) is not str or not _DAY_ISO.fullmatch(raw):
            raise ValueError("NATIVE_ISO_DAILY_LABEL_REQUIRED")
        parsed = date.fromisoformat(raw)
        if endpoint is DailyEndpoint.DNSE_CONNECTED_DAY:
            t = row.get("source_unix_seconds")
            if type(t) is not int or t < 0:
                raise ValueError("NATIVE_DNSE_UNIX_START_REQUIRED")
            try:
                observed_day = datetime.fromtimestamp(t, tz=timezone.utc).date()
            except (OverflowError, OSError, ValueError):
                raise ValueError("DNSE_UNIX_DATE_OUT_OF_RANGE") from None
            if observed_day != parsed:
                raise ValueError("DNSE_UNIX_AND_UTC_DATE_LABEL_DISAGREE")
    return parsed.isoformat()


def _values(endpoint: DailyEndpoint, row: dict[str, Any]) -> tuple[Decimal, ...]:
    o, h, l, c, v = (_number(row[k]) for k in _FIELDS[endpoint])
    if h < max(o, c, l) or l > min(o, c) or v != v.to_integral_value():
        raise ValueError("INVALID_SOURCE_NATIVE_OHLCV")
    return o, h, l, c, v


def _aux(endpoint: DailyEndpoint, row: dict[str, Any]) -> tuple[Any, ...]:
    out: list[Any] = []
    for key in _AUX[endpoint]:
        raw = row.get(key)
        if raw is None:
            out.append(None)
        elif key in _AUX_NUMERIC:
            out.append(_number(raw))
        elif type(raw) is str:
            out.append(raw)
        else:
            raise ValueError("INVALID_ADJUSTMENT_BASIS_FIELD")
    return tuple(out)


def _core_and_metadata(endpoint: DailyEndpoint, row: dict[str, Any]) -> tuple[
    tuple[Decimal, ...], tuple[Any, ...], dict[str, Any]
]:
    identity = {"trading_date"} if endpoint in (
        DailyEndpoint.SSI_COMPACT, DailyEndpoint.SSI_DETAILED,
    ) else {"source_unix_seconds", "date_utc"} if endpoint is DailyEndpoint.DNSE_CONNECTED_DAY else {"tradingDate"}
    structural = identity | set(_FIELDS[endpoint]) | set(_AUX[endpoint])
    return _values(endpoint, row), _aux(endpoint, row), {
        k: v for k, v in row.items() if k not in structural
    }


def diff_native_d1_versions(
    earlier: NativeD1Snapshot,
    later: NativeD1Snapshot,
) -> dict[str, object]:
    """Classify observed changes WITHOUT deleting or publishing any source row."""
    if type(earlier) is not NativeD1Snapshot or type(later) is not NativeD1Snapshot:
        raise TypeError("TWO_TYPED_SOURCE_SNAPSHOTS_REQUIRED")
    identity = lambda p: (
        p.endpoint, p.symbol, p.timeframe, p.price_basis, p.unit,
    )
    if identity(earlier) != identity(later):
        raise ValueError("EXACT_ENDPOINT_SYMBOL_TF_BASIS_AND_UNIT_REQUIRED")
    if later.observed_at_utc <= earlier.observed_at_utc:
        raise ValueError("STRICTLY_INCREASING_LOCAL_RECEIPT_REQUIRED")

    a = {_day(earlier.endpoint, r): r for r in earlier.rows}
    b = {_day(later.endpoint, r): r for r in later.rows}
    matched = sorted(set(a) & set(b))
    additions = sorted(set(b) - set(a))
    missing = sorted(set(a) - set(b))
    numerical: list[dict[str, object]] = []
    adjustment: list[dict[str, object]] = []
    timestamp_label: list[dict[str, object]] = []
    metadata: list[dict[str, object]] = []
    equal = 0
    for day in matched:
        core0, aux0, meta0 = _core_and_metadata(earlier.endpoint, a[day])
        core1, aux1, meta1 = _core_and_metadata(later.endpoint, b[day])
        if core0 != core1:
            changed = [f for i, f in enumerate(("open", "high", "low", "close", "volume"))
                       if core0[i] != core1[i]]
            numerical.append({"day": day, "changed_fields": changed})
        if aux0 != aux1:
            changed = [name for i, name in enumerate(_AUX[earlier.endpoint])
                       if aux0[i] != aux1[i]]
            adjustment.append({"day": day, "changed_fields": changed})
        if (earlier.endpoint is DailyEndpoint.DNSE_CONNECTED_DAY
                and a[day]["source_unix_seconds"] != b[day]["source_unix_seconds"]):
            timestamp_label.append({
                "day": day,
                "changed_fields": ["source_unix_seconds"],
            })
        keys = sorted(set(meta0) | set(meta1))
        meta_changes = [k for k in keys if
                        (k not in meta0) != (k not in meta1) or
                        meta0.get(k) != meta1.get(k)]
        if meta_changes:
            null_shape_only = all(
                (k not in meta0 and meta1.get(k) is None)
                or (k not in meta1 and meta0.get(k) is None)
                for k in meta_changes
            )
            metadata.append({
                "day": day,
                "changed_fields": meta_changes,
                "absent_vs_null_only": null_shape_only,
            })
        if (core0 == core1 and aux0 == aux1 and not meta_changes
                and not any(x["day"] == day for x in timestamp_label)):
            equal += 1
    changed_days = sorted(
        set(additions) | {x["day"] for x in numerical + adjustment + timestamp_label}
    )
    return {
        "schema": "mst.m3.endpoint-native.d1-ohlcv-revision-observer.v1",
        "endpoint": earlier.endpoint.value,
        "symbol": earlier.symbol,
        "timeframe": "D1",
        "price_basis": earlier.price_basis,
        "source_unit": earlier.unit,
        "previous_local_received_utc": earlier.observed_at_utc.isoformat(),
        "current_local_received_utc": later.observed_at_utc.isoformat(),
        "old_rows": len(a),
        "new_rows": len(b),
        "overlapping_rows": len(matched),
        "unchanged_rows": equal,
        "added_day_labels": additions,
        "missing_prior_day_labels_UNVERIFIED": missing,
        "numeric_ohlcv_revisions": numerical,
        "adjustment_or_price_basis_revisions": adjustment,
        "source_candle_start_timestamp_revisions": timestamp_label,
        "metadata_changes_only_or_in_addition": metadata,
        "affected_research_day_labels": changed_days,
        "recommendation": (
            "REBUILD_DEPENDENT_RESEARCH_CANDIDATES_AFTER_NEW_VERSION"
            if changed_days else
            "SOURCE_RECEIPT_ONLY_NO_NUMERIC_OR_ADJUSTMENT_REVISION_OBSERVED"
        ),
        "missing_prior_rows_may_be_window_or_source_scope": bool(missing),
        "metadata_absent_null_must_not_be_price_revision": True,
        "cross_provider_comparison_not_performed": True,
        "session_closed_issuer_verified": False,
        "source_first_known_authenticated": False,
        "independent_retention_entitlement_verified": False,
        "source_revisions_were_vendor_signed": False,
        "deletion_authorized": False,
        "automatic_cache_v2_write_authorized": False,
        "signal_eligible": False,
        "production_authorized": False,
    }
