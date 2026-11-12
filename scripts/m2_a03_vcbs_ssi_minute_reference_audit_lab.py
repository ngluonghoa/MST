"""MST A03: VCBS minute PRICE points vs SSI timestamped OHLCV-shaped rows.

Only structurally compares two caller-supplied UNTRUSTED source fixtures.
VCBS's session-level price_board_live OHLC and cumulative_session_matched
totalVolume are NEVER per-minute candle OHLCV, even after the trading session
and even when every price point equals an SSI close at matching clock text.
No source calls, cache publisher, credentials, market observations or orders.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
from pathlib import Path
import json
import re

SCHEMA="mst.a03.vcbs-ssi-minute-price-reference-boundary.synthetic.v1"
STATUS="UNTRUSTED_MINUTE_PRICE_REFERENCE_ONLY_NATIVE_VCBS_M5_TO_H4_NO_GO"
MAX_POINTS=1000
TIME_PATTERN=re.compile(r"^([0-2]\d):([0-5]\d):([0-5]\d)$")
DATE_PATTERN=re.compile(r"^\d\d/\d\d/\d{4}$")
SYM_PATTERN=re.compile(r"^[A-Z0-9-]{1,16}$")
VCBS_MINUTE_DENY_FIELDS=frozenset(("open","high","low","close","volume","highPrice","lowPrice","openPrice","closePrice","tradingVolume","ohlc","ohlcv"))


def _clock(value: object) -> str:
    if type(value) is not str:
        raise TypeError("EXPLICIT_HHMMSS_CLOCK_REQUIRED")
    m=TIME_PATTERN.fullmatch(value)
    if not m or int(m[1])>23:
        raise ValueError("INVALID_HHMMSS_DO_NOT_ROUND_OR_INFER_SESSION")
    return value


def _positive_number(value: object, *, allow_zero: bool=False) -> Decimal:
    if type(value) not in (str,int,float):
        raise ValueError("FINITE_SOURCE_NUMBER_REQUIRED")
    if type(value) is str and not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?",value):
        raise ValueError("SOURCE_NUMBER_CANONICAL_DECIMAL_REQUIRED")
    try:
        n=Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("FINITE_SOURCE_NUMBER_REQUIRED") from exc
    if not n.is_finite() or (n<0 if allow_zero else n<=0):
        raise ValueError("NONPOSITIVE_OR_NONFINITE_SOURCE_PRICE_VOLUME_DENIED")
    return n


def _ssi_ticks(rows: object, symbol: str, local_date: str) -> dict:
    if type(rows) is not list or not rows or len(rows)>MAX_POINTS:
        raise ValueError("SSI_NONEMPTY_BOUNDED_TICK_ROWS_REQUIRED")
    result={}
    prefix=local_date+" "
    for row in rows:
        if type(row) is not dict or row.get("symbol")!=symbol:
            raise PermissionError("SSI_PROVIDER_SYMBOL_SCOPE_MISMATCH")
        raw_stamp=row.get("trading_date")
        if type(raw_stamp) is not str or not raw_stamp.startswith(prefix):
            raise PermissionError("SSI_UNVERIFIED_DAY_SCOPE_MISMATCH")
        clock=_clock(raw_stamp[len(prefix):])
        if clock in result:
            raise ValueError("SSI_DUPLICATE_CLOCK_LABEL_DENIED")
        keys=("open","high","low","close","volume")
        if not all(k in row for k in keys):
            raise ValueError("SSI_OHLCV_SHAPE_REQUIRED_FOR_REFERENCE")
        o,h,l,c,v=(_positive_number(row[k],allow_zero=k=="volume") for k in keys)
        if h<max(o,c) or l>min(o,c) or l>h:
            raise ValueError("SSI_REFERENCE_OHLC_ENVELOPE_INVALID")
        result[clock]=c
    return result


def _vcbs_reference(payload: object, symbol: str) -> dict:
    if type(payload) is not dict or payload.get("secCode")!=symbol:
        raise PermissionError("VCBS_SOURCE_SYMBOL_SCOPE_MISMATCH")
    if payload.get("data_status")!="available":
        raise PermissionError("VCBS_REFERENCE_NOT_AVAILABLE")
    if payload.get("ohlcSource")!="price_board_live":
        raise PermissionError("VCBS_EXPECTED_SESSION_BOARD_SOURCE_REQUIRED")
    if payload.get("recent_volume_scope")!="cumulative_session_matched":
        raise PermissionError("VCBS_SESSION_VOLUME_SCOPE_REQUIRED")
    if payload.get("volume_unit")!="shares" or payload.get("price_unit")!="VND":
        raise PermissionError("VCBS_REFERENCE_UNIT_UNVERIFIED")
    if type(payload.get("ohlcProvisional")) is not bool:
        raise ValueError("EXPLICIT_SESSION_BOARD_PROVISIONAL_FLAG_REQUIRED")
    _positive_number(payload.get("totalVolume"),allow_zero=True)
    rows=payload.get("series")
    if type(rows) is not list or not rows or len(rows)>MAX_POINTS:
        raise ValueError("VCBS_NONEMPTY_BOUNDED_PRICE_POINT_ROWS_REQUIRED")
    result={}
    for row in rows:
        if type(row) is not dict or set(row)!={"time","price"}:
            raise PermissionError("VCBS_POINT_ONLY_DO_NOT_INFER_ROW_LEVEL_CANDLES")
        clock=_clock(row["time"])
        if clock in result:
            raise ValueError("VCBS_DUPLICATE_MINUTE_CLOCK_LABEL_DENIED")
        result[clock]=_positive_number(row["price"])
    return result


def compare_untrusted_price_references(vcbs: object, ssi_rows: object, *,
                                       symbol: str,local_date: str) -> dict:
    """Read-only in-memory alignment; never proves source bar-time semantics."""
    if type(symbol) is not str or not SYM_PATTERN.fullmatch(symbol):
        raise ValueError("EXPLICIT_ONE_UPPERCASE_SYMBOL_REQUIRED")
    if type(local_date) is not str or not DATE_PATTERN.fullmatch(local_date):
        raise ValueError("EXPLICIT_RAW_VENDOR_SESSION_DATE_TOKEN_REQUIRED")
    ssi=_ssi_ticks(ssi_rows,symbol,local_date)
    v=_vcbs_reference(vcbs,symbol)
    common=set(ssi)&set(v)
    matching=sum(ssi[k]==v[k] for k in common)
    mismatching=len(common)-matching
    # Do not emit actual quote values, timestamps, histories or hashes.
    return {
        "schema":SCHEMA,
        "status":STATUS,
        "symbol":symbol,
        "vcbs_price_point_count":len(v),
        "ssi_ohlcv_shaped_tick_count":len(ssi),
        "clock_labels_aligned":len(common),
        "identical_reference_prices":matching,
        "unequal_reference_prices":mismatching,
        "vcbs_unmatched_clock_count":len(v)-len(common),
        "ssi_unmatched_clock_count":len(ssi)-len(common),
        "reference_comparison":("UNTRUSTED_PRICE_MISMATCH_QUARANTINE" if mismatching
                                else "UNTRUSTED_PRICE_COINCIDENCE_ONLY"),
        "vcbs_session_board_ohlc_provisional_flag":vcbs["ohlcProvisional"],
        "vcbs_top_level_volume_is_session_cumulative_only":True,
        "vcbs_per_minute_open_high_low_close_volume_available":False,
        "ssi_provider_m1_timestamp_start_end_authenticated":False,
        "vcbs_native_m5_m15_m30_h1_h4_ohlcv_verified":False,
        "vcbs_m1_to_m5_aggregation_authorized":False,
        "calendar_auctions_halts_trading_sessions_verified":False,
        "correction_first_known_source_clock_authenticated":False,
        "vendor_google_drive_retention_license_proven":False,
        "github_runner_authenticated_source_access_proven":False,
        "cloud_cache_or_trading_authorized":False,
        "reference_only":True,
    }


def fake_source_fixture():
    """Deliberately artificial 3-point session; NOT actual stock prices."""
    sample_vcbs={
        "secCode":"XYZ",
        "data_status":"available",
        "ohlcSource":"price_board_live",
        "ohlcProvisional":False,
        "recent_volume_scope":"cumulative_session_matched",
        "volume_unit":"shares",
        "price_unit":"VND",
        "totalVolume":600,
        "series":[{"time":"09:15:00","price":101},
                  {"time":"09:16:00","price":102},
                  {"time":"09:17:00","price":103}],
    }
    sample_ssi=[
        {"symbol":"XYZ","trading_date":"14/10/2025 09:15:00",
         "open":100,"high":103,"low":99,"close":101,"volume":100},
        {"symbol":"XYZ","trading_date":"14/10/2025 09:16:00",
         "open":101,"high":102,"low":100,"close":101,"volume":200},
        {"symbol":"XYZ","trading_date":"14/10/2025 09:17:00",
         "open":102,"high":104,"low":101,"close":103,"volume":300},
    ]
    return sample_vcbs,sample_ssi


def synthetic_receipt():
    vcbs,ssi=fake_source_fixture()
    r=compare_untrusted_price_references(vcbs,ssi,symbol="XYZ",local_date="14/10/2025")
    if (r["clock_labels_aligned"],r["identical_reference_prices"],
        r["unequal_reference_prices"])!=(3,2,1):
        raise AssertionError("FAKE_REFERENCE_PARITY_DRIFT")
    if r["cloud_cache_or_trading_authorized"] or r["vcbs_per_minute_open_high_low_close_volume_available"]:
        raise PermissionError("FAKE_REFERENCE_CANNOT_AUTHORIZE_CANDLES")
    return r


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args(argv)
    r=synthetic_receipt()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":STATUS,"synthetic_only":True,"fake_clock_matches":3,
                      "fake_price_mismatches":1,"production":False},sort_keys=True))


if __name__=="__main__":
    main()
