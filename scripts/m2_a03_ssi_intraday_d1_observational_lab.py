"""MST A03 SSI intraday-session -> D1 observational source consistency lab.

The connected SSI lightweight intraday endpoint has genuine OHLCV-shaped rows;
its richer raw-price/sysToken endpoint may be unavailable. This lab only checks
source-internal arithmetic on caller-supplied fictional or transient records.
It does NOT certify a native provider-issued closed M1/M5 candle, calendar,
format, first-known revision, licensed retention, Cloud Cache or trading.

Important: the connected endpoint description calls trading_date MM/dd/yyyy,
but an observed source token 14/10/2026 cannot be MM/dd/yyyy. We preserve
literal tokens and never resolve source timestamp labels from caller intent.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
from pathlib import Path
import json
import re

SCHEMA="mst.a03.ssi-intraday-to-d1-observational-arithmetic.v1"
STATUS="SSI_WHOLE_SESSION_D1_PARITY_ONLY_NATIVE_MINUTE_CLOSE_DATE_CONTRACT_NO_GO"
CLOCK_RE=re.compile(r"^([0-2]\d):([0-5]\d):([0-5]\d)$")
DATE_RE=re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
SYMBOL_RE=re.compile(r"^[A-Z0-9-]{1,16}$")
FIELDS=("open","high","low","close","volume")
MAX_TICKS=1000
TOL=Decimal("0.01")


def number(value,*,allow_zero=False):
    if type(value) not in (str,int,float):
        raise ValueError("FINITE_UNAMBIGUOUS_VND_OR_SHARES_REQUIRED")
    if type(value) is str and not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?",value):
        raise ValueError("CANONICAL_NONNEGATIVE_NUMERIC_STRING_REQUIRED")
    try:
        x=Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("FINITE_UNAMBIGUOUS_VND_OR_SHARES_REQUIRED") from exc
    if not x.is_finite() or (x<0 if allow_zero else x<=0):
        raise ValueError("NONPOSITIVE_OR_NONFINITE_OHLCV_VALUE")
    return x


def clock_time(value):
    if type(value) is not str:
        raise ValueError("EXACT_HHMMSS_LOCAL_CLOCK_REQUIRED")
    match=CLOCK_RE.fullmatch(value)
    if match is None or int(match[1])>23:
        raise ValueError("INVALID_LOCAL_CLOCK")
    return value,int(match[1])*3600+int(match[2])*60+int(match[3])


def observed_date_contract(day_token):
    if type(day_token) is not str:
        raise ValueError("EXACT_RAW_VENDOR_DATE_TOKEN_REQUIRED")
    m=DATE_RE.fullmatch(day_token)
    if m is None:
        raise ValueError("RAW_SOURCE_DATE_TOKEN_DDMM_OR_MMDD_REQUIRED")
    a,b,year=map(int,m.groups())
    if not (1<=a<=31 and 1<=b<=31 and 2000<=year<=2100):
        raise ValueError("DATE_TOKEN_OUT_OF_RANGE")
    if a>12 and b<=12:
        return "OBSERVED_LITERAL_CONFLICTS_WITH_MMDY_CONNECTOR_DESCRIPTION"
    if a<=12 and b>12:
        return "OBSERVED_LITERAL_MMDY_SHAPE_ONLY_NO_SOURCE_ISSUER"
    if a<=12 and b<=12:
        return "OBSERVED_LITERAL_AMBIGUOUS_DDMM_VS_MMDD"
    raise ValueError("RAW_SOURCE_DATE_TOKEN_IMPOSSIBLE_BOTH_ORDERS")


def audit_ssi_session(ticks, daily_rows, *, symbol, day_token):
    """Pure read-only shape/parity. No source calls and no source-right claims."""
    if type(symbol) is not str or SYMBOL_RE.fullmatch(symbol) is None:
        raise ValueError("ONE_UPPERCASE_STOCK_SYMBOL_REQUIRED")
    date_status=observed_date_contract(day_token)
    if type(ticks) is not list or not ticks or len(ticks)>MAX_TICKS:
        raise ValueError("EXPLICIT_NONEMPTY_BOUNDED_SSI_TICKS_REQUIRED")
    if type(daily_rows) is not list or not daily_rows:
        raise ValueError("EXPLICIT_NONEMPTY_SSI_DAILY_ROWS_REQUIRED")
    selected=[r for r in daily_rows if type(r) is dict and r.get("symbol")==symbol and
              r.get("trading_date")==day_token]
    if len(selected)!=1:
        raise ValueError("EXACT_ONE_D1_ROW_WITH_SAME_LITERAL_DAY_TOKEN_REQUIRED")
    daily=selected[0]
    d={}
    for key in FIELDS:
        if key not in daily:
            raise ValueError("MISSING_SSI_D1_FIELD_"+key)
        d[key]=number(daily[key],allow_zero=key=="volume")
    if d["high"]<max(d["open"],d["close"]) or d["low"]>min(d["open"],d["close"]):
        raise ValueError("D1_OHLC_ENVELOPE_INVALID")
    tick_times=set()
    rows=[]
    date_prefix=day_token+" "
    adjusted_count=0
    for row in ticks:
        if type(row) is not dict or row.get("symbol")!=symbol:
            raise PermissionError("SSI_INTRADAY_SYMBOL_MIXED_OR_MISSING")
        stamp=row.get("trading_date")
        if type(stamp) is not str or not stamp.startswith(date_prefix):
            raise PermissionError("SSI_INTRADAY_LITERAL_DATE_SCOPE_CONFLICT")
        clock,seconds=clock_time(stamp[len(date_prefix):])
        if clock in tick_times:
            raise ValueError("DUPLICATE_SSI_INTRADAY_CLOCK_LABEL_DENIED")
        tick_times.add(clock)
        if type(row.get("price_changed")) is not bool:
            raise ValueError("EXPLICIT_PRICE_CHANGED_BOOL_REQUIRED")
        adjusted_count+=int(row["price_changed"])
        ohlcv={}
        for key in FIELDS:
            if key not in row:
                raise ValueError("MISSING_SSI_INTRADAY_FIELD_"+key)
            ohlcv[key]=number(row[key],allow_zero=key=="volume")
        if ohlcv["high"]<max(ohlcv["open"],ohlcv["close"]) or ohlcv["low"]>min(ohlcv["open"],ohlcv["close"]):
            raise ValueError("SSI_INTRADAY_OHLC_ENVELOPE_INVALID")
        rows.append((seconds,ohlcv))
    rows.sort(key=lambda pair:pair[0])
    if any(a[0]>=b[0] for a,b in zip(rows,rows[1:])):
        raise ValueError("SSI_INTRADAY_CLOCK_ORDER_NOT_STRICT")
    candidate={
        "open":rows[0][1]["open"],
        "high":max(r["high"] for _,r in rows),
        "low":min(r["low"] for _,r in rows),
        "close":rows[-1][1]["close"],
        "volume":sum((r["volume"] for _,r in rows),Decimal(0)),
    }
    mismatches=tuple(k for k in FIELDS if abs(candidate[k]-d[k])>TOL)
    if mismatches:
        raise PermissionError("SSI_INTRADAY_D1_ARITHMETIC_DRIFT_DENIED:"+",".join(mismatches))
    irregular=sum(b[0]-a[0]!=60 for a,b in zip(rows,rows[1:]))
    return {
        "schema":SCHEMA,
        "status":STATUS,
        "symbol":symbol,
        "day_token_format_evidence":date_status,
        "connector_description_claimed_format":"MM/dd/yyyy HH:mm:ss",
        "date_contract_verified_by_issuer":False,
        "tick_row_count":len(rows),
        "matching_d1_source_rows":1,
        "other_d1_window_rows_ignored":len(daily_rows)-1,
        "intraday_to_d1_price_volume_fields_matched":5,
        "non_60_second_adjacent_clock_differences":irregular,
        "price_changed_rows":adjusted_count,
        "original_raw_price_sys_token_endpoint_authenticated":False,
        "native_m1_m5_bar_closure_or_start_end_verified":False,
        "source_calendar_gaps_backfillable":False,
        "source_event_time_and_first_known_authenticated":False,
        "provider_cloud_retention_license_verified":False,
        "github_runner_market_source_connected":False,
        "official_market_calendar_and_corporate_actions_verified":False,
        "production_cache_or_trading_authorized":False,
    }


def fake_fixture():
    """Fake symbol/date/prices that are NOT any real issuer observation."""
    rows=[
        dict(symbol="ZZZ",trading_date="14/10/2025 09:15:00",
             open=100,high=103,low=99,close=102,volume=150,price_changed=False),
        dict(symbol="ZZZ",trading_date="14/10/2025 09:16:00",
             open=102,high=105,low=101,close=104,volume=250,price_changed=False),
        dict(symbol="ZZZ",trading_date="14/10/2025 09:18:00",
             open=104,high=106,low=100,close=105,volume=350,price_changed=False),
    ]
    daily=[
        dict(symbol="ZZZ",trading_date="14/10/2025",
             open="100",high="106",low="99",close="105",volume="750"),
        dict(symbol="ZZZ",trading_date="13/10/2025",
             open="100",high="110",low="98",close="108",volume="800"),
    ]
    return rows,daily


def synthetic_receipt():
    ticks,daily=fake_fixture()
    r=audit_ssi_session(ticks,daily,symbol="ZZZ",day_token="14/10/2025")
    if r["tick_row_count"]!=3 or r["intraday_to_d1_price_volume_fields_matched"]!=5:
        raise AssertionError("FAKE_SSI_PARITY_DRIFT")
    if r["day_token_format_evidence"]!="OBSERVED_LITERAL_CONFLICTS_WITH_MMDY_CONNECTOR_DESCRIPTION":
        raise AssertionError("FAKE_SSI_DATE_CONFLICT_DRIFT")
    return r


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args(argv)
    r=synthetic_receipt()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"status":STATUS,"synthetic_only":True,"all_live_source_gates_no_go":True},sort_keys=True))


if __name__=="__main__":
    main()
