"""Test-only SSI/DNSE M5 timestamp START/END ambiguity: no live provider."""
from __future__ import annotations
import argparse, json, re
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from swing_trading.session_calendar import TimestampSemantic
from swing_trading.native_minute_bar_source_plan import BarProduct, describe_bar_product
from swing_trading.incremental_cache import Provider
from scripts.m2_a02_incremental_cache_oracle_lab import identity
from scripts.m2_a03_v2_cache_consumer_contract import fixture_scope
from scripts.m2_a03_multi_segment_session_gap_lab import (
    UntrustedMultiSegmentDay, candidate_screen, fixtures_day, records_at,
    vn_utc, FIVE, VN)
from scripts.m2_a03_v2_session_pit_screen_lab import utc

STATUS="UNVERIFIED_SSI_DNSE_M5_TIME_LABEL_CONVENTION_NO_GO"
DENIED=("ssi_m5_resolution_proven","ssi_start_end_semantic_proven",
        "dnse_start_end_semantic_proven","licensed_vendor_source_proven",
        "official_calendar_and_auction_proven","first_known_origin_proven",
        "drive_market_cache_authorized","v1_v2_original_modified",
        "owner_a02_63_approved","owner_a03_v2_8_approved",
        "owner_a03_14_approved","production_authorized","trading_authorized")

@dataclass(frozen=True)
class Label:
    product: BarProduct
    raw_time: str|int
    local_day: date
    semantic: TimestampSemantic
    verified: bool=False
    def __post_init__(self):
        if type(self.product) is not BarProduct or self.product not in (
            BarProduct.SSI_FASTCONNECT_INTRADAY_OHLC, BarProduct.DNSE_OPENAPI_OHLC):
            raise TypeError("EXPLICIT_NATIVE_BAR_PRODUCT_REQUIRED")
        if type(self.local_day) is not date or type(self.semantic) is not TimestampSemantic:
            raise TypeError("EXPLICIT_LOCAL_DAY_AND_TIMESTAMP_SEMANTIC_REQUIRED")
        if self.verified is not False:
            raise PermissionError("CALLER_SELF_VERIFIED_PROVIDER_NOT_ACCEPTED")

def raw_time(label:Label)->datetime:
    if type(label) is not Label:
        raise TypeError("EXACT_LABEL_REQUIRED")
    if label.product is BarProduct.SSI_FASTCONNECT_INTRADAY_OHLC:
        raw=label.raw_time
        if type(raw) is not str or not re.fullmatch(r"\d{2}:\d{2}:\d{2}",raw):
            raise ValueError("SSI_EXACT_LOCAL_HHMMSS_REQUIRED")
        h,m,s=map(int,raw.split(":"))
        if h>23 or m>59 or s>59:
            raise ValueError("SSI_LOCAL_HHMMSS_OUT_OF_RANGE")
        point=datetime(label.local_day.year,label.local_day.month,
                       label.local_day.day,h,m,s,tzinfo=VN).astimezone(timezone.utc)
    else:
        raw=label.raw_time
        if type(raw) is not int or not (1_000_000_000 <= raw <= 4_000_000_000):
            raise ValueError("DNSE_UNIX_SECONDS_REQUIRED_NOT_MILLISECONDS")
        point=datetime.fromtimestamp(raw,tz=timezone.utc)
    if point.astimezone(VN).date()!=label.local_day:
        raise ValueError("RAW_LABEL_LOCAL_DAY_MISMATCH")
    if point.second or point.microsecond or point.minute%5:
        raise ValueError("M5_FIXTURE_GRID_UNALIGNED_NO_AUTOROUND")
    return point

def interval(label:Label):
    point=utc(raw_time(label))
    if label.semantic is TimestampSemantic.UNKNOWN:
        raise PermissionError("UNKNOWN_PROVIDER_TIME_LABEL_START_END")
    if label.semantic is TimestampSemantic.START:
        return point,point+FIVE
    if label.semantic is TimestampSemantic.END:
        return point-FIVE,point
    raise TypeError("UNKNOWN_TYPED_SEMANTIC")

def screen_label(day:UntrustedMultiSegmentDay,rows:tuple,label:Label,
                 phase:str,as_of:datetime):
    if type(day) is not UntrustedMultiSegmentDay or type(label) is not Label:
        raise TypeError("TYPED_DAY_AND_LABEL_REQUIRED")
    if type(rows) is not tuple or not rows:
        raise TypeError("RETAINED_TUPLE_BAR_REQUIRED")
    if describe_bar_product(label.product).provider.value != day.scope.candidate.provider_id:
        raise ValueError("SOURCE_PROVIDER_SCOPE_MISMATCH")
    if label.local_day != day.trading_day_local:
        raise ValueError("SOURCE_LABEL_DAY_SCOPE_MISMATCH")
    start,end=interval(label)
    if any(r.bar.start_utc!=start or r.bar.end_utc!=end for r in rows):
        raise ValueError("RAW_TIME_LABEL_NOT_BOUND_TO_BAR_START_END")
    v=candidate_screen(day,rows,claimed_segment=phase,as_of_utc=utc(as_of))
    return {"revision":v["candidate_revision_id"],"start":start.isoformat(),
            "end":end.isoformat(),"source_convention_qualified":False,
            "source_or_trading_authority":False}

def dnse_day(base:UntrustedMultiSegmentDay):
    scope=fixture_scope(identity(provider=Provider.DNSE))
    return replace(base,scope=scope,segments=tuple(
        replace(seg,slot=replace(seg.slot,partition=scope.candidate))
        for seg in base.segments))

def evaluate():
    day,morning,pm,late,_,_,known=fixtures_day()
    dday=dnse_day(day)
    amlast=records_at(vn_utc(11,25),day.scope,event="LAST_AM")
    pmfirst=records_at(vn_utc(13,0),day.scope,event="FIRST_PM")
    dam=records_at(vn_utc(11,25),dday.scope,event="DNSE_AM")
    checks=[]
    def ssi(t,sem):
        return Label(BarProduct.SSI_FASTCONNECT_INTRADAY_OHLC,
                     t,day.trading_day_local,sem)
    def dn(t,sem):
        return Label(BarProduct.DNSE_OPENAPI_OHLC,
                     t,dday.trading_day_local,sem)
    def ok(name,day0,rows,label,phase,clock,expect="r1"):
        result=screen_label(day0,rows,label,phase,clock)
        if result["revision"]!=expect or result["source_convention_qualified"]:
            raise AssertionError("SYNTHETIC_M5_TIMESTAMP_DRIFT_"+name)
        checks.append(name)
    def no(name,fn,exc):
        try:fn()
        except exc:checks.append(name)
        else:raise AssertionError("SYNTHETIC_M5_TIMESTAMP_FAIL_OPEN_"+name)
    ok("SSI_START_1125_TO_1130",day,(amlast,),ssi("11:25:00",TimestampSemantic.START),
       "AM_LAST",amlast.bar.first_known_utc)
    ok("SSI_END_1130_TO_1125",day,(amlast,),ssi("11:30:00",TimestampSemantic.END),
       "AM_LAST",amlast.bar.first_known_utc)
    ok("SSI_START_1300_PM",day,(pmfirst,),ssi("13:00:00",TimestampSemantic.START),
       "PM_FIRST",pmfirst.bar.first_known_utc)
    ok("SSI_END_1305_PM",day,(pmfirst,),ssi("13:05:00",TimestampSemantic.END),
       "PM_FIRST",pmfirst.bar.first_known_utc)
    no("SSI_START_1130_LUNCH_DENIED",
       lambda:screen_label(day,(records_at(vn_utc(11,30),day.scope,event="BREAK"),),
           ssi("11:30:00",TimestampSemantic.START),"AM_LAST",vn_utc(11,35)),ValueError)
    no("SSI_END_1300_LUNCH_DENIED",
       lambda:screen_label(day,(records_at(vn_utc(12,55),day.scope,event="GAP"),),
           ssi("13:00:00",TimestampSemantic.END),"PM_FIRST",vn_utc(13,0)),ValueError)
    no("SSI_UNKNOWN_1130_DENIED",
       lambda:interval(ssi("11:30:00",TimestampSemantic.UNKNOWN)),PermissionError)
    no("SSI_UNALIGNED_TIME_NOT_ROUNDED",
       lambda:raw_time(ssi("14:29:59",TimestampSemantic.END)),ValueError)
    ok("SSI_R1_BEFORE_CORRECTION",day,(morning,late),
       ssi("11:20:00",TimestampSemantic.START),"AM_LAST",
       known-timedelta(microseconds=1),"r1")
    ok("SSI_R2_AT_FIRST_KNOWN",day,(morning,late),
       ssi("11:20:00",TimestampSemantic.START),"AM_LAST",known,"r2")
    ok("DNSE_T_START_1125",dday,(dam,),
       dn(int(vn_utc(11,25).timestamp()),TimestampSemantic.START),
       "AM_LAST",dam.bar.first_known_utc)
    ok("DNSE_T_END_1130",dday,(dam,),
       dn(int(vn_utc(11,30).timestamp()),TimestampSemantic.END),
       "AM_LAST",dam.bar.first_known_utc)
    no("DNSE_T_END_1300_GAP_DENIED",
       lambda:screen_label(dday,(records_at(vn_utc(12,55),dday.scope,event="DNSE_GAP"),),
           dn(int(vn_utc(13,0).timestamp()),TimestampSemantic.END),"PM_FIRST",
           vn_utc(13,0)),ValueError)
    no("DNSE_T_UNKNOWN_DENIED",
       lambda:interval(dn(int(vn_utc(13,0).timestamp()),TimestampSemantic.UNKNOWN)),
       PermissionError)
    no("SOURCE_SCOPE_CROSS_PROVIDER_DENIED",
       lambda:screen_label(dday,(dam,),ssi("11:30:00",TimestampSemantic.END),
           "AM_LAST",dam.bar.first_known_utc),ValueError)
    no("DNSE_UNIX_MILLISECONDS_DENIED",
       lambda:raw_time(dn(int(vn_utc(11,30).timestamp())*1000,
                          TimestampSemantic.END)),ValueError)
    no("DNSE_BOOLEAN_EPOCH_DENIED",
       lambda:raw_time(dn(True,TimestampSemantic.END)),ValueError)
    no("SELF_ASSERTED_VERIFICATION_DENIED",
       lambda:replace(ssi("11:30:00",TimestampSemantic.END),verified=True),
       PermissionError)
    if len(checks)!=18:
        raise AssertionError("EXACT_18_TYPED_SOURCE_TIMESTAMP_SCENARIOS")
    report={"schema":"mst.a03.ssi-dnse-m5-raw-time-ambiguity.synthetic.v1",
            "status":STATUS,"scenarios":checks,"count":len(checks),
            "ssi_field":"Time HH:MM:SS public-document example only",
            "dnse_field":"t integer UNIX seconds public-document example only",
            "source_label_semantic_status":"UNKNOWN_NOT_VERIFIED_FOR_EITHER_ENDPOINT",
            "real_issuer_or_entitlement":"NOT_RECEIVED",
            **{key:False for key in DENIED}}
    payload=json.dumps(report,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    report["synthetic_sha256"]=sha256(payload.encode()).hexdigest()
    return report

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path)
    args=p.parse_args(argv)
    r=evaluate()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in r.items() if k!="scenarios"},sort_keys=True))

if __name__=="__main__":
    main()
