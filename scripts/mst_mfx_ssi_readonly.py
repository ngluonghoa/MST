"""MST official SSI FastConnect V3 — owner-gated market-data-only D1 ingress.

This module is intentionally NOT a market Cache publisher and never stores
prices. The user must separately provision a market-data scoped API key,
confirm source-use rights and dispatch the main-only GitHub workflow.
No OTP, refresh-token persistence, trading client or broker/order endpoint.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Mapping

AUTH_URL = "https://api.ssi.com.vn/api/v3/auth/token"
OHLC_URL = "https://api.ssi.com.vn/api/v3/data/ohlc"
MAX_RESPONSE_BYTES = 1_000_000
MAX_PAGES = 5
PAGE_SIZE = 100
MAX_ROWS = MAX_PAGES * PAGE_SIZE
# Import one shared conservative request span contract for SSI and DNSE.
# This is not source-coverage or closed-session certification.
from scripts.mst_mfx_native_timeframes import (
    MAX_SINGLE_PROBE_CALENDAR_DAYS as MAX_CALENDAR_SPAN_BY_TF,
)
SYMBOL_RE = re.compile(r"[A-Z]{3}\Z")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


class SsiSourceDenied(ValueError):
    """Only fixed error codes, without secrets or provider payloads."""


def guard_ssi(env: Mapping[str, str]) -> tuple[str, date, date]:
    mode = env.get("MST_MFX_SOURCE_MODE")
    if mode not in ("ssi-d1-readonly", "ssi-native-readonly",
                    "ssi-native-quarantine-stage"):
        raise SsiSourceDenied("MST_SSI_EXACT_READONLY_MODE_REQUIRED")
    from scripts.mst_mfx_native_timeframes import provider_resolution, NativeTfDenied
    timeframe = env.get("MST_SOURCE_TF", "D1")
    try:
        provider_resolution("SSI", timeframe)
    except NativeTfDenied:
        raise SsiSourceDenied("MST_SSI_NATIVE_TF_UNSUPPORTED") from None
    if mode == "ssi-d1-readonly" and timeframe != "D1":
        raise SsiSourceDenied("MST_SSI_D1_MODE_CANNOT_PROMOTE_OTHER_TF")
    if (env.get("MST_SSI_READONLY_OWNER_ACCEPTED") != "true"
            or env.get("MST_SSI_SOURCE_RIGHTS_CONFIRMED") != "true"):
        raise SsiSourceDenied("MST_SSI_MARKETDATA_AND_RIGHTS_GATES_REQUIRED")
    if any(type(env.get(k)) is not str or not env[k].strip()
           for k in ("MST_SSI_API_KEY", "MST_SSI_API_SECRET")):
        raise SsiSourceDenied("MST_SSI_MARKETDATA_ONLY_CREDENTIALS_REQUIRED")
    symbol = env.get("MST_SSI_SYMBOL", "")
    if type(symbol) is not str or not SYMBOL_RE.fullmatch(symbol):
        raise SsiSourceDenied("MST_SSI_EXACT_STOCK_SYMBOL_REQUIRED")
    first, last = env.get("MST_SSI_FROM_DATE"), env.get("MST_SSI_TO_DATE")
    if (type(first) is not str or type(last) is not str
            or not ISO_DATE.fullmatch(first) or not ISO_DATE.fullmatch(last)):
        raise SsiSourceDenied("MST_SSI_ISO_DATE_WINDOW_REQUIRED")
    try:
        a, b = date.fromisoformat(first), date.fromisoformat(last)
    except ValueError:
        raise SsiSourceDenied("MST_SSI_INVALID_ISO_DATE") from None
    if b < a or b-a > timedelta(days=MAX_CALENDAR_SPAN_BY_TF[timeframe]):
        raise SsiSourceDenied("MST_SSI_TF_BOUNDED_WINDOW_REQUIRED")
    return symbol, a, b


def _json_bounded(response: Any, *, endpoint: str) -> dict:
    """A bounded, exact 200 JSON result; never dump token or market rows."""
    if response.status_code != 200:
        raise SsiSourceDenied("MST_SSI_"+endpoint+"_HTTP_NOT_200")
    raw = response.content
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_RESPONSE_BYTES:
        raise SsiSourceDenied("MST_SSI_"+endpoint+"_BOUNDED_JSON_REQUIRED")
    payload = response.json()
    if type(payload) is not dict:
        raise SsiSourceDenied("MST_SSI_"+endpoint+"_JSON_OBJECT_REQUIRED")
    return payload


def _positive_decimal(raw: Any) -> Decimal:
    if type(raw) not in (str, int, float) or (
            type(raw) is str and not raw.strip()):
        raise SsiSourceDenied("MST_SSI_SOURCE_NATIVE_NUMBER_REQUIRED")
    try:
        n = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        raise SsiSourceDenied("MST_SSI_SOURCE_NATIVE_NUMBER_INVALID") from None
    if not n.is_finite() or n <= 0:
        raise SsiSourceDenied("MST_SSI_SOURCE_NATIVE_PRICE_INVALID")
    return n


def _volume(raw: Any) -> int:
    if type(raw) not in (str, int):
        raise SsiSourceDenied("MST_SSI_NATIVE_VOLUME_REQUIRED")
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        raise SsiSourceDenied("MST_SSI_NATIVE_VOLUME_INVALID") from None
    if not value.is_finite() or value < 0 or value != value.to_integral_value():
        raise SsiSourceDenied("MST_SSI_NATIVE_VOLUME_NONNEGATIVE_INTEGER_REQUIRED")
    return int(value)


def _native_source_row(
    row: Any, *, symbol: str, first: date, last: date, timeframe: str,
) -> str:
    if type(row) is not dict or row.get("symbol") != symbol:
        raise SsiSourceDenied("MST_SSI_SOURCE_SYMBOL_MISMATCH")
    label = row.get("tradingDate")
    if type(label) is not str:
        raise SsiSourceDenied("MST_SSI_NATIVE_TRADING_LABEL_REQUIRED")
    try:
        if timeframe == "D1":
            if not ISO_DATE.fullmatch(label):
                raise ValueError("not ISO D1")
            d = date.fromisoformat(label)
        else:
            # Keep the native minute/second label; do not collapse to a D1 key.
            if not re.fullmatch(r"\d{4}[-/]\d{2}[-/]\d{2} \d{2}:\d{2}:\d{2}", label):
                raise ValueError("not a native intraday timestamp")
            native_clock = datetime.strptime(label.replace("/", "-"), "%Y-%m-%d %H:%M:%S")
            d = native_clock.date()
            label = native_clock.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise SsiSourceDenied("MST_SSI_NATIVE_TF_TRADING_TIMESTAMP_INVALID") from None
    if not first <= d <= last:
        raise SsiSourceDenied("MST_SSI_OUTSIDE_REQUESTED_WINDOW")
    try:
        o, h, l, c = (
            _positive_decimal(row[key]) for key in ("open", "high", "low", "close")
        )
        _volume(row["volume"])
    except KeyError:
        raise SsiSourceDenied("MST_SSI_SOURCE_NATIVE_ROW_INCOMPLETE") from None
    if h < max(o, l, c) or l > min(o, h, c):
        raise SsiSourceDenied("MST_SSI_SOURCE_OHLC_INVARIANT_FAILED")
    return label


def _fetch_ssi_native_once(session: Any, env: Mapping[str,str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Real REST auth + paged OHLC; only aggregate non-sensitive result returned.

    Does NOT return access/refresh tokens, native rows, dates, or price values.
    No logging of HTTP errors, request headers, response text or credentials.
    """
    symbol, first, last = guard_ssi(env)
    tf = env.get("MST_SOURCE_TF", "D1")
    from scripts.mst_mfx_native_timeframes import source_tf_metadata, provider_resolution
    try:
        reply = session.post(
            AUTH_URL,
            json={"apiKey":env["MST_SSI_API_KEY"],
                  "apiSecret":env["MST_SSI_API_SECRET"]},
            headers={"Accept":"application/json","Content-Type":"application/json"},
            allow_redirects=False, timeout=20,
        )
        auth = _json_bounded(reply, endpoint="TOKEN")
        access = auth.get("accessToken")
        if (auth.get("tokenType") != "Bearer" or type(access) is not str
                or not 24 <= len(access) <= 8192
                or "\n" in access or "\r" in access):
            raise SsiSourceDenied("MST_SSI_READONLY_BEARER_NOT_OBTAINED")
    except SsiSourceDenied:
        raise
    except Exception:
        raise SsiSourceDenied("MST_SSI_TOKEN_TRANSPORT_FAILED_CLOSED") from None

    seen: set[str] = set()
    captured: list[dict[str, Any]] = []
    expected_pages: int | None = None
    expected_items: int | None = None
    expected_items_field: bool | None = None
    expected_page_count_field: bool | None = None
    pages = 0
    for page in range(1, MAX_PAGES+1):
        # SSI FastConnect V3 requires YYYY/MM/DD for 1d, but
        # YYYY/MM/DD HH:mm:ss for intraday OHLCV. The time-of-day
        # bounds include the entire requested last calendar day.
        first_param = first.strftime("%Y/%m/%d")
        last_param = last.strftime("%Y/%m/%d")
        if tf != "D1":
            first_param += " 00:00:00"
            last_param += " 23:59:59"
        params = {
            "symbol":symbol,
            "from":first_param,
            "to":last_param,
            "timeFrame":provider_resolution("SSI", tf),
            "pageIndex":page,
            "pageSize":PAGE_SIZE,
        }
        try:
            reply = session.get(
                OHLC_URL,params=params,
                headers={"Authorization":"Bearer "+access,
                         "Content-Type":"application/json",
                         "Accept":"application/json"},
                allow_redirects=False,timeout=25,
            )
            data = _json_bounded(reply, endpoint="OHLC")
        except SsiSourceDenied:
            raise
        except Exception:
            raise SsiSourceDenied("MST_SSI_OHLC_TRANSPORT_FAILED_CLOSED") from None
        rows = data.get("data")
        if type(rows) is not list or len(rows) > PAGE_SIZE:
            raise SsiSourceDenied("MST_SSI_OHLC_PAGE_INVALID")
        # Official V3 documentation includes pageIndex or pageNumber and pageSize.
        # A server silently ignoring the requested pageSize or returning an
        # inconsistent index is NOT a safe, complete source read.
        if (type(data.get("pageSize")) is not int
                or data["pageSize"] != PAGE_SIZE):
            raise SsiSourceDenied("MST_SSI_SOURCE_PAGE_SIZE_DRIFT")
        indices = [
            data[k] for k in ("pageIndex", "pageNumber") if k in data
        ]
        if (not indices or any(type(i) is not int or i != page for i in indices)):
            raise SsiSourceDenied("MST_SSI_SOURCE_PAGE_NUMBER_DRIFT")
        # A server-declared total/page count must not disappear or appear
        # halfway through a multi-page source read.
        has_items = "itemsCount" in data
        has_page_count = "pageCount" in data
        if expected_items_field is None:
            expected_items_field = has_items
            expected_page_count_field = has_page_count
        elif (has_items != expected_items_field
              or has_page_count != expected_page_count_field):
            raise SsiSourceDenied("MST_SSI_PAGINATION_FIELD_PRESENCE_DRIFT")
        announced_items = data.get("itemsCount")
        if has_items and announced_items is None:
            raise SsiSourceDenied("MST_SSI_SOURCE_ITEMS_COUNT_NULL")
        if announced_items is not None:
            if (type(announced_items) is not int or
                    not 1 <= announced_items <= MAX_ROWS):
                raise SsiSourceDenied("MST_SSI_SOURCE_ITEMS_COUNT_UNBOUNDED")
            if expected_items is None:
                expected_items = announced_items
            elif expected_items != announced_items:
                raise SsiSourceDenied("MST_SSI_SOURCE_ITEMS_COUNT_MUTATED")
        announced = data.get("pageCount")
        if has_page_count and announced is None:
            raise SsiSourceDenied("MST_SSI_SOURCE_PAGE_COUNT_NULL")
        if announced is not None:
            if type(announced) is not int or not 1 <= announced <= MAX_PAGES:
                raise SsiSourceDenied("MST_SSI_TOO_MANY_OR_INVALID_PAGES")
            if expected_pages is None:
                expected_pages = announced
            elif expected_pages != announced:
                raise SsiSourceDenied("MST_SSI_PAGING_METADATA_MUTATED")
        pages += 1
        for row in rows:
            label = _native_source_row(row, symbol=symbol, first=first, last=last, timeframe=tf)
            if label in seen:
                raise SsiSourceDenied("MST_SSI_DUPLICATE_SOURCE_BAR_TIMESTAMP")
            seen.add(label)
            # Capture only the audited market OHLCV fields, not arbitrary
            # additional vendor fields or tokens. Preserve source numeric units.
            captured.append({
                "symbol": symbol, "tradingDate": label,
                **{k: row[k] for k in ("open", "high", "low", "close", "volume")},
            })
        if expected_items is not None and len(seen) > expected_items:
            raise SsiSourceDenied("MST_SSI_SOURCE_ITEMS_COUNT_EXCEEDED")
        if expected_pages is not None:
            if not rows and page < expected_pages:
                raise SsiSourceDenied("MST_SSI_PAGING_EARLY_EMPTY_PAGE")
            if page == expected_pages:
                if expected_items is not None and len(seen) != expected_items:
                    raise SsiSourceDenied("MST_SSI_SOURCE_ITEMS_COUNT_MISMATCH")
                break
            if expected_items is not None and len(seen) == expected_items:
                raise SsiSourceDenied("MST_SSI_PAGECOUNT_EXCEEDS_SOURCE_ITEMS")
        elif expected_items is not None:
            # Even a short page is incomplete until all server-declared
            # items have actually been read, never silently truncate.
            if len(seen) == expected_items:
                break
            if not rows:
                raise SsiSourceDenied("MST_SSI_SOURCE_ITEMS_COUNT_MISMATCH")
        elif len(rows) < PAGE_SIZE:
            break
    else:
        raise SsiSourceDenied("MST_SSI_BOUND_PAGINATION_EXHAUSTED")
    if not seen or len(seen) > MAX_ROWS:
        raise SsiSourceDenied("MST_SSI_EMPTY_OR_EXCESSIVE_SOURCE_SCOPE")
    if expected_items is not None and len(seen) != expected_items:
        raise SsiSourceDenied("MST_SSI_SOURCE_ITEMS_COUNT_MISMATCH")
    report = {
        "provider":"SSI_FASTCONNECT_V3_MARKET_DATA",
        **source_tf_metadata("SSI",tf),
        "native_source_rows_observed":len(seen),
        "source_pages_verified":pages,
        "source_items_count_verified": expected_items is not None,
        "complete_historical_source_coverage_proven":False,
        "market_data_token_used_without_otp":True,
        "source_ohlcv_invariants_verified":True,
        "price_unit_or_adjusted_basis_verified":False,
        "venue_native_close_issuer_attested":False,
        "source_rights_or_retention_independently_audited":False,
        "private_data_stored_to_drive":False,
        "signal_eligible":False,
        "trading_or_broker_calls":0,
    }
    return report, captured


def read_ssi_native_once(session: Any, env: Mapping[str,str]) -> dict[str, Any]:
    """Compatibility read-only entrypoint: no source rows in stdout/receipt."""
    report, _ = _fetch_ssi_native_once(session, env)
    return report


def read_ssi_d1_once(session: Any, env: Mapping[str,str]) -> dict[str, Any]:
    """Legacy D1-only caller. Prevent accidental use as an intraday shortcut."""
    if env.get("MST_SOURCE_TF", "D1") != "D1":
        raise SsiSourceDenied("MST_SSI_D1_ONLY_CALLER")
    return read_ssi_native_once(session, env)
