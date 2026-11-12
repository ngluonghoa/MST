"""MST A03 VCBS D1 -> W1/MN1 adjusted-price arithmetic crosscheck (QA ONLY).

The connected VCBS history interface can return source-provided weekly/monthly
aggregates. We must not compare W/M adjusted open/high/low directly to raw
daily openPrice/highPrice/lowPrice: the correct reconstruction applies the
original day's adjFactor to EACH daily OHLC observation before aggregating.

This checker NEVER proves a historical venue calendar, full provider issuance,
first-known, vendor use rights, tradable signal or production Cache. It never
fetches market data. GitHub CI runs ONLY fictional synthetic examples.
"""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re

SCHEMA="mst.a03.vcbs.d1-w1-mn1-adjusted-observational-crosscheck.v1"
STATUS="SOURCE_OBSERVED_ADJUSTMENT_ARITHMETIC_ONLY_CALENDAR_LICENSE_CACHE_NO_GO"
PRICE_TOLERANCE=Decimal("0.10")
OTHER_TOLERANCE=Decimal("0.02")
PERIODS=("W","M")
FIELDS=("sessions","open","high","low","close","volume","tradingValue","ptValue","foreignNetValue")


def _date(value):
    if type(value) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",value):
        raise ValueError("EXACT_ISO_LOCAL_TRADING_DATE_REQUIRED")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("INVALID_SOURCE_DATE") from exc


def _num(value):
    if type(value) not in (int,float):
        raise ValueError("FINITE_NUMERIC_SOURCE_FIELD_REQUIRED")
    try:
        number=Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("FINITE_NUMERIC_SOURCE_FIELD_REQUIRED") from exc
    if not number.is_finite():
        raise ValueError("FINITE_NUMERIC_SOURCE_FIELD_REQUIRED")
    return number


def _daily(rows):
    if type(rows) is not list or not rows:
        raise ValueError("EXACT_NONEMPTY_DAILY_ARRAY_REQUIRED")
    index={}
    for row in rows:
        if type(row) is not dict or row.get("priceBasis")!="adjusted":
            raise PermissionError("VCBS_D1_ADJUSTED_BASIS_REQUIRED")
        if row.get("price_unit")!="VND" or row.get("volumeScope")!="matched":
            raise PermissionError("VCBS_D1_VND_MATCHED_VOLUME_SCOPE_REQUIRED")
        if row.get("provisional") is True:
            raise PermissionError("DAILY_OPEN_OR_PROVISIONAL_NOT_ELIGIBLE")
        key=_date(row.get("tradingDate"))
        if key in index:
            raise ValueError("DUPLICATE_D1_SESSION_DENIED")
        for name in ("openPrice","highPrice","lowPrice","closePrice","adjClosePrice",
                     "adjFactor","volume","tradingValue","ptValue","foreignNetValue"):
            if name not in row:
                raise ValueError("MISSING_D1_FIELD_"+name)
        o,h,l,c,f=(_num(row[k]) for k in
                    ("openPrice","highPrice","lowPrice","closePrice","adjFactor"))
        if min(o,h,l,c,f)<=0 or h<max(o,c) or l>min(o,c) or l>h:
            raise ValueError("INVALID_RAW_DAILY_OHLC_OR_ADJ_FACTOR")
        if _num(row["adjClosePrice"])<=0 or _num(row["volume"])<0:
            raise ValueError("INVALID_ADJUSTED_CLOSE_OR_VOLUME")
        # Trading values / foreign net may be negative (net), not absent.
        for name in ("tradingValue","ptValue","foreignNetValue"):
            _num(row[name])
        index[key]=row
    return index


def _period(row):
    if type(row) is not dict or row.get("interval") not in PERIODS:
        raise ValueError("VCBS_ONLY_W1_OR_MN1_PERIOD_REQUIRED")
    if row.get("priceBasis")!="adjusted" or row.get("price_unit")!="VND":
        raise PermissionError("NO_MIXED_PRICE_BASIS_IN_VCBS_AGGREGATION")
    if type(row.get("partial")) is not bool:
        raise PermissionError("EXPLICIT_PROVIDER_PARTIAL_FLAG_REQUIRED")
    if row.get("provisional") is True:
        raise PermissionError("PROVISIONAL_VCBS_PERIOD_NOT_ACCEPTABLE")
    lo,hi=_date(row.get("periodStart")),_date(row.get("periodEnd"))
    if lo>hi or row.get("tradingDate")!=hi.isoformat():
        raise ValueError("PERIOD_DATE_SCOPE_OR_LABEL_MISMATCH")
    if row["interval"]=="W" and (lo.isocalendar()[:2]!=hi.isocalendar()[:2]):
        raise ValueError("WEEKLY_PERIOD_CROSSES_ISO_WEEK")
    if row["interval"]=="M" and (lo.year,lo.month)!=(hi.year,hi.month):
        raise ValueError("MONTHLY_PERIOD_CROSSES_CALENDAR_MONTH")
    return lo,hi


def compare_source_periods(daily_rows,period_rows):
    """Report arithmetic only; fail closed on ANY discrepancy.

    All inputs are untrusted externally sourced shapes; this function is
    not a source authenticator, official calendar validator or Cache writer.
    """
    day_index=_daily(daily_rows)
    if type(period_rows) is not list or not period_rows:
        raise ValueError("EXACT_NONEMPTY_W_M_ARRAY_REQUIRED")
    seen=set()
    results=[]
    for row in period_rows:
        lo,hi=_period(row)
        identity=(row["interval"],lo,hi)
        if identity in seen:
            raise ValueError("DUPLICATE_W_M_PERIOD_DENIED")
        seen.add(identity)
        matching=[day_index[k] for k in sorted(day_index) if lo<=k<=hi]
        if not matching:
            raise ValueError("MISSING_W_M_DAILY_SOURCE_DATES")
        # adjFactor is a DAILY corporate-action-aware input. Applying only
        # the first/last day's factor to a whole range is not equivalent.
        scaled=lambda k,r: _num(r[k])*_num(r["adjFactor"])
        expected={
            "sessions":Decimal(len(matching)),
            "open":scaled("openPrice",matching[0]),
            "high":max(scaled("highPrice",r) for r in matching),
            "low":min(scaled("lowPrice",r) for r in matching),
            "close":_num(matching[-1]["adjClosePrice"]),
            "volume":sum((_num(r["volume"]) for r in matching),Decimal(0)),
            "tradingValue":sum((_num(r["tradingValue"]) for r in matching),Decimal(0)),
            "ptValue":sum((_num(r["ptValue"]) for r in matching),Decimal(0)),
            "foreignNetValue":sum((_num(r["foreignNetValue"]) for r in matching),Decimal(0)),
        }
        mismatches=[]
        for key in FIELDS:
            actual=_num(row.get(key))
            tolerance=PRICE_TOLERANCE if key in ("open","high","low","close") else OTHER_TOLERANCE
            if abs(actual-expected[key])>tolerance:
                mismatches.append(key)
        if mismatches:
            raise PermissionError("VCBS_D1_W_M_CROSS_SOURCE_ARITHMETIC_DRIFT_DENIED:"+
                                  ",".join(mismatches))
        results.append({
            "interval":row["interval"],
            "daily_source_count_verified":len(matching),
            "adjustment_present":any(_num(r["adjFactor"])!=1 for r in matching),
            "source_reported_partial":row["partial"],
            "classification":("QUARANTINED_PARTIAL_PERIOD" if row["partial"]
                              else "OBSERVATIONAL_ARITHMETIC_MATCH_NOT_CALENDAR_CERTIFIED"),
            "price_basis":"adjusted",
            "numeric_mismatch_count":0,
            "calendar_source_completeness_attested":False,
            "issuer_first_known_or_correction_authority_attested":False,
            "provider_cloud_retention_license_proven":False,
            "cache_publish_approved":False,
        })
    return {
        "schema":SCHEMA,
        "status":STATUS,
        "period_comparisons":results,
        "period_count":len(results),
        "partial_count":sum(r["source_reported_partial"] for r in results),
        "fully_closed_source_candles_attested":False,
        "actual_provider_data_queried":False,
        "official_holiday_and_halt_calendar_verified":False,
        "issuer_first_known_authenticated":False,
        "cloud_cache_storage_or_trading_authorized":False,
    }


def fake_fixture():
    """Only fictional TEST tokens and made-up OHLC numbers, no vendor rows."""
    rows=[
        dict(tradingDate="2025-03-03",priceBasis="adjusted",price_unit="VND",
             volumeScope="matched",openPrice=100,highPrice=110,lowPrice=95,
             closePrice=100,adjClosePrice=90,adjFactor=0.9,
             volume=100,tradingValue=10000,ptValue=200,foreignNetValue=-50),
        dict(tradingDate="2025-03-04",priceBasis="adjusted",price_unit="VND",
             volumeScope="matched",openPrice=105,highPrice=120,lowPrice=98,
             closePrice=108,adjClosePrice=108,adjFactor=1.0,
             volume=150,tradingValue=13000,ptValue=300,foreignNetValue=40),
        dict(tradingDate="2025-03-05",priceBasis="adjusted",price_unit="VND",
             volumeScope="matched",openPrice=109,highPrice=117,lowPrice=104,
             closePrice=110,adjClosePrice=110,adjFactor=1.0,
             volume=130,tradingValue=14000,ptValue=450,foreignNetValue=10),
    ]
    fields=dict(tradingDate="2025-03-05",periodStart="2025-03-03",
                periodEnd="2025-03-05",sessions=3,open=90,high=120,low=85.5,
                close=110,priceBasis="adjusted",price_unit="VND",
                volume=380,tradingValue=37000,ptValue=950,
                foreignNetValue=0,partial=False,provisional=False)
    week=dict(fields,interval="W")
    month=dict(fields,interval="M",partial=True)
    return rows,[week,month]


def run_synthetic():
    d,p=fake_fixture()
    result=compare_source_periods(d,p)
    if result["period_count"]!=2 or result["partial_count"]!=1:
        raise AssertionError("VCBS_FAKE_W_M_ASSERTION_DRIFT")
    if result["period_comparisons"][0]["numeric_mismatch_count"]!=0:
        raise AssertionError("VCBS_FAKE_ADJUSTED_PRICE_MISMATCH")
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args(argv)
    result=run_synthetic()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print(json.dumps({"status":STATUS,"synthetic_period_count":result["period_count"],
                      "actual_quote_rows_or_authenticated_issuer":False,
                      "cloud_cache_and_trading_allowed":False},sort_keys=True))


if __name__=="__main__":
    main()
