"""Test-only SSI latest/full-session, DNSE D1 and VCBS price freshness boundary.

No provider I/O, cache, credentials, market prices or production status.
"""
from __future__ import annotations
import argparse, json
from dataclasses import dataclass
from datetime import datetime, date, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo
from swing_trading.c2_source_capability_audit import (
    ConnectedEndpoint, DataNeed, endpoint_contract)
from scripts.m2_a03_three_source_vcbs_capability_lab import ssi_date_candidates

VN=ZoneInfo("Asia/Ho_Chi_Minh")
DENIED=("source_issuer_clock_authenticated","source_first_known_authenticated",
        "official_calendar_and_session_open_verified","native_m5_closed_bar_verified",
        "cross_provider_same_native_timeframe_verified","source_rights_verified",
        "physical_google_drive_cache_authorized","owner_a02_63_approved",
        "owner_a03_v2_8_approved","owner_a03_14_approved",
        "production_release_authorized","trading_authorized")

def parse_reported_asof(raw):
    if type(raw) is not str or not raw or len(raw)>50:
        raise ValueError("EXACT_CONNECTOR_ASOF_ISO_REQUIRED")
    try:
        value=datetime.fromisoformat(raw.replace("Z","+00:00"))
    except ValueError as exc:
        raise ValueError("UNPARSABLE_CONNECTOR_ASOF") from exc
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("EXPLICIT_SOURCE_CLOCK_OFFSET_REQUIRED")
    return value.astimezone(timezone.utc)

def utc(t):
    if type(t) is not datetime or t.tzinfo is None or t.utcoffset()!=timedelta(0):
        raise ValueError("EXPLICIT_AWARE_UTC_CLOCK_REQUIRED")
    return t

@dataclass(frozen=True)
class UntrustedSSISnapshot:
    endpoint: ConnectedEndpoint
    source_trade_date: str
    connector_asof_utc: datetime
    observed_at_utc: datetime
    requested_day: date|None=None
    issuer_verified: bool=False
    def __post_init__(self):
        if type(self.endpoint) is not ConnectedEndpoint or self.endpoint not in (
            ConnectedEndpoint.SSI_INTRADAY_LATEST,
            ConnectedEndpoint.SSI_INTRADAY_SESSION):
            raise TypeError("ONLY_TYPED_SSI_LATEST_OR_DAY_MODE")
        if type(self.source_trade_date) is not str:
            raise TypeError("EXPLICIT_SOURCE_DATE_TEXT")
        utc(self.connector_asof_utc)
        utc(self.observed_at_utc)
        if self.connector_asof_utc>self.observed_at_utc:
            raise ValueError("CONNECTOR_ASOF_FUTURE_TO_OBSERVER")
        if self.requested_day is not None and type(self.requested_day) is not date:
            raise TypeError("EXPLICIT_REQUESTED_DAY")
        if self.issuer_verified is not False:
            raise PermissionError("CALLER_CANNOT_GRANT_VENDOR_CLOCK_AUTHORITY")

def classify_ssi(w:UntrustedSSISnapshot):
    if type(w) is not UntrustedSSISnapshot:
        raise TypeError("TYPED_SSI_SNAPSHOT_REQUIRED")
    c=ssi_date_candidates(w.source_trade_date)
    if len(c)!=1:
        raise PermissionError("AMBIGUOUS_SSI_DDMM_MMDD_NO_FRESHNESS")
    day=c[0][1]
    if w.requested_day is not None and day!=w.requested_day:
        raise ValueError("SOURCE_DAY_REQUEST_MISMATCH")
    hh,mm,ss=map(int,w.source_trade_date[-8:].split(":"))
    event=datetime(day.year,day.month,day.day,hh,mm,ss,
                   tzinfo=VN).astimezone(timezone.utc)
    if event>w.connector_asof_utc:
        raise ValueError("SOURCE_EVENT_FUTURE_RELATIVE_TO_ASOF")
    product=endpoint_contract(w.endpoint).need
    return {"mode":w.endpoint.value,
            "syntactic_lag_seconds":int((w.connector_asof_utc-event).total_seconds()),
            "single_reference_not_full_session":product is DataNeed.QUOTE_REFERENCE,
            "whole_session_shape_not_native_m5":product is DataNeed.MINUTE_OHLCV,
            "date_parse_shape_only":True,
            "issuer_date_format_proven":False,
            "connector_asof_is_publisher_first_known":False,
            "bar_closed_asof_proven":False,
            "official_latest_freshness_proven":False,
            "signal_eligible":False}

def compare_source_modes(a,b):
    if type(a) is not ConnectedEndpoint or type(b) is not ConnectedEndpoint:
        raise TypeError("TYPED_CONNECTED_SOURCE_ENDPOINT_REQUIRED")
    left,right=endpoint_contract(a),endpoint_contract(b)
    return {"same_provider":left.provider is right.provider,
            "same_product":left.need is right.need,
            "same_price_unit":left.price_units==right.price_units,
            "source_issuer_verified":False,
            "native_same_m5_verified":False,
            "permitted_to_confirm_latest_m5":False}

def evaluate():
    asof=datetime(2026,10,13,2,30,tzinfo=timezone.utc)
    snap=UntrustedSSISnapshot(
        ConnectedEndpoint.SSI_INTRADAY_SESSION,
        "13/10/2026 09:15:00",asof,asof+timedelta(seconds=10),
        date(2026,10,13))
    candidate=classify_ssi(snap)
    assert candidate["syntactic_lag_seconds"]==900
    pair_names=((ConnectedEndpoint.SSI_INTRADAY_LATEST,
                 ConnectedEndpoint.SSI_INTRADAY_SESSION),
                (ConnectedEndpoint.SSI_INTRADAY_SESSION,
                 ConnectedEndpoint.DNSE_D1_HISTORY),
                (ConnectedEndpoint.SSI_INTRADAY_SESSION,
                 ConnectedEndpoint.VCBS_INTRADAY_PRICE_POINTS))
    pairs=[compare_source_modes(a,b) for a,b in pair_names]
    assert not any(x["permitted_to_confirm_latest_m5"] for x in pairs)
    report={"schema":"mst.a03.ssi-dnse-vcbs-source-freshness.synthetic.v1",
            "status":"CONNECTOR_ASOF_IS_NOT_VENDOR_FIRST_KNOWN_NO_GO",
            "synthetic_ssi":candidate,
            "cross_mode_pairs":pairs,
            "same_provider_latest_vs_whole_session_not_equivalent":True,
            "dnse_connected_day_history_not_ssi_m5_confirmation":True,
            "vcbs_price_points_not_ssi_m5_confirmation":True,
            "exchange_calendar_freshness_age_limit":None,
            "source_bar_rows_persisted":False,
            **{k:False for k in DENIED}}
    raw=json.dumps(report,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    report["synthetic_receipt_sha256"]=sha256(raw.encode("ascii")).hexdigest()
    return report

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path)
    args=p.parse_args(argv)
    report=evaluate()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="cross_mode_pairs"},sort_keys=True))

if __name__=="__main__":
    main()
