"""MST A03: six timeframes x three providers and VCBS price-only negative QA.

This scripts/ module has NO I/O, credentials, provider reads or trading.
MCP endpoint shape, public separately connected API and licensed/approved
historical candle source are distinct classes of evidence.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import argparse
import json
from swing_trading.incremental_cache import Provider
from swing_trading.c2_source_capability_audit import (
    ConnectedEndpoint as E, DataNeed, ProbeState, RefreshVerdict,
    advise_connected_refresh, audit_transient_response, endpoint_contract,
)

SCHEMA="mst.a03.three-provider-six-timeframe-capability.untrusted.v1"
TF=("M5","M15","M30","H1","H4","D1")
PROVIDERS=(Provider.SSI,Provider.DNSE,Provider.VCBS)
PUBLIC_API={
    Provider.SSI: frozenset(("M5","M15","H1","D1")),
    Provider.DNSE: frozenset(("M5","M15","M30","H1","D1")),
    Provider.VCBS: frozenset(),
}
SURFACES={
    Provider.SSI:(E.SSI_INTRADAY_SESSION,E.SSI_D1_DETAILED),
    Provider.DNSE:(E.DNSE_D1_HISTORY,E.DNSE_D1_HISTORY),
    Provider.VCBS:(E.VCBS_INTRADAY_PRICE_POINTS,E.VCBS_D1_WINDOW),
}
GATES=("native_minute_ohlcv_connected_and_qualified",
       "independent_vendor_issuer_verified","publisher_first_known_verified",
       "official_calendar_and_timestamp_semantics_verified",
       "source_rights_and_retention_approved","real_drive_market_cache_authorized",
       "upstream_v1_or_v2_modified","a02_63_approved","a03_v2_8_approved",
       "a03_14_approved","production_release_authorized","trading_authorized")

@dataclass(frozen=True)
class Capability:
    provider: Provider
    timeframe: str
    connected_endpoint: E
    public_native_api_documented_unconnected: bool
    connected_data_need: DataNeed
    entitlement: bool=False
    qualified_native_ohlcv: bool=False
    signal_eligible: bool=False

    def __post_init__(self):
        if type(self.provider) is not Provider or type(self.timeframe) is not str or self.timeframe not in TF:
            raise TypeError("TYPED_3_BY_6_SOURCE_TIMEFRAME_REQUIRED")
        if type(self.connected_endpoint) is not E or type(self.connected_data_need) is not DataNeed:
            raise TypeError("TYPED_CONNECTED_SURFACE_REQUIRED")
        meta=endpoint_contract(self.connected_endpoint)
        if meta.provider is not self.provider or meta.need is not self.connected_data_need:
            raise ValueError("CONNECTED_ENDPOINT_PROVIDER_OR_NEED_MISMATCH")
        if type(self.public_native_api_documented_unconnected) is not bool:
            raise TypeError("PUBLIC_DOCUMENT_EVIDENCE_EXPLICIT_BOOLEAN")
        if self.entitlement or self.qualified_native_ohlcv or self.signal_eligible:
            raise PermissionError("PUBLIC_API_OR_MCP_SCHEMA_NEVER_GRANTS_MARKET_SOURCE")

    @property
    def status(self):
        if self.timeframe=="D1":
            return "D1_CONNECTED_SHAPE_ONLY_SOURCE_RIGHTS_UNVERIFIED"
        if self.provider is Provider.VCBS:
            return "VCBS_INTRADAY_PRICE_POINTS_NOT_MINUTE_OHLCV"
        if self.timeframe=="H4":
            return "DERIVED_H4_UNVERIFIED_SESSION_CORRECTION_ASOF"
        if self.public_native_api_documented_unconnected:
            return "PUBLIC_NATIVE_OHLCV_API_NOT_CONNECTED_THROUGH_CURRENT_MCP"
        return "NATIVE_TIMEFRAME_NOT_VERIFIED_NEEDS_APPROVED_POLICY"

def matrix():
    out=[]
    for provider in PROVIDERS:
        for tf in TF:
            e=SURFACES[provider][1 if tf=="D1" else 0]
            out.append(Capability(provider,tf,e,tf in PUBLIC_API[provider],
                                  endpoint_contract(e).need))
    if len(out)!=18 or len({(x.provider,x.timeframe) for x in out})!=18:
        raise AssertionError("EXACT_18_SOURCE_TIMEFRAME_ROWS")
    return tuple(out)

def one(provider,timeframe):
    if type(provider) is not Provider or type(timeframe) is not str or timeframe not in TF:
        raise TypeError("EXPLICIT_SOURCE_TIMEFRAME_ID_REQUIRED")
    return next(x for x in matrix() if x.provider is provider and x.timeframe==timeframe)

def vcbs_probe(payload,timeframe):
    """Original C2 in-memory check returns sanitized counts, NOT price rows."""
    if type(payload) is not dict or type(timeframe) is not str or timeframe not in TF:
        raise TypeError("EXACT_TYPED_VCBS_FIXTURE_AND_TIMEFRAME_REQUIRED")
    ep=E.VCBS_INTRADAY_PRICE_POINTS
    assert endpoint_contract(ep).need is DataNeed.MINUTE_PRICE_REFERENCE
    probe=audit_transient_response(
        ep,payload,checked_at_utc=datetime(2026,11,10,2,0,tzinfo=timezone.utc))
    if probe.state is not ProbeState.SHAPE_RETURNED:
        raise ValueError("VCBS_PRICE_POINT_PAYLOAD_NOT_VALID")
    if advise_connected_refresh(ep,DataNeed.MINUTE_OHLCV).verdict is not RefreshVerdict.BLOCKED:
        raise AssertionError("SOURCE_C2_MINUTE_OHLCV_GATE_CHANGED")
    if advise_connected_refresh(ep,DataNeed.MINUTE_PRICE_REFERENCE).verdict is not RefreshVerdict.REFERENCE_SNAPSHOT:
        raise AssertionError("SOURCE_C2_PRICE_REFERENCE_GATE_CHANGED")
    return {
        "source":"VCBS","timeframe":timeframe,
        "synthetic_points":probe.observed_rows,
        "probe_state":probe.state.value,
        "point_data_is_minute_reference_only":True,
        "board_session_open_high_low_not_each_m5_bar":True,
        "source_has_per_candle_ohlcv":False,
        "source_volume_per_m5_verified":False,
        "minute_high_low_from_sampling_verified":False,
        "valid_for_signal_indicators":False,
        "retains_real_source_rows":False,
    }

def fabricated_vcbs():
    return {"data_status":"available","dataPoints":3,
        "series":[{"time":"09:15:00","price":100},
                  {"time":"09:16:00","price":101},
                  {"time":"09:17:00","price":99}],
        "ohlcSource":"price_board_live","open":98,"high":102,
        "low":97,"totalVolume":999,"ohlcProvisional":True}

def require_approved_signal_source(row):
    if type(row) is not Capability:
        raise TypeError("TYPED_SOURCE_STATUS_REQUIRED")
    raise PermissionError("NO_SIGNED_SOURCE_RIGHTS_NATIVE_BARS_AND_OWNER_APPROVAL")


# Additional connector-mode shape probe. Synthetic only, no SSI/DNSE I/O.
from datetime import date as CalendarDate
import re as _date_regex

def ssi_date_candidates(raw):
    if type(raw) is not str:
        raise TypeError("STRICT_SSI_DATE_STRING_REQUIRED")
    match=_date_regex.fullmatch(
        r"(\d{2})/(\d{2})/(\d{4}) (\d{2}):(\d{2}):(\d{2})",raw)
    if match is None:
        raise ValueError("EXACT_DATE_HMS_REQUIRED")
    a,b,year,hh,minute,seconds=map(int,match.groups())
    if hh>23 or minute>59 or seconds>59:
        raise ValueError("IMPOSSIBLE_SOURCE_CLOCK")
    choices=[]
    for fmt,month,day in (("DD_MM_YYYY",b,a),("MM_DD_YYYY",a,b)):
        try:
            value=CalendarDate(year,month,day)
        except ValueError:
            continue
        choices.append((fmt,value))
    if not choices:
        raise ValueError("INVALID_CALENDAR_DATE")
    return tuple(choices)

def strict_ssi_day_candidate_only(raw,expected_day):
    if type(expected_day) is not CalendarDate:
        raise TypeError("EXPLICIT_EXPECTED_DAY_REQUIRED")
    options=ssi_date_candidates(raw)
    if len(options)!=1:
        raise PermissionError("AMBIGUOUS_DD_MM_VS_MM_DD_SOURCE_FIELD")
    if options[0][1]!=expected_day:
        raise ValueError("SOURCE_DATE_EXPECTATION_MISMATCH")
    return {"day_shape":expected_day.isoformat(),
            "parser_shape_only":True,"vendor_date_convention_verified":False}

def ssi_dnse_synthetic_source_modes():
    """Exercise original C2 on invented source rows, never a live snapshot."""
    fake_ssi={"status":"ok","data":{"ticks":[
        {"symbol":"SYN","trading_date":"13/10/2026 "+time,
         "open":100,"high":102,"low":99,"close":101,"volume":10}
        for time in ("09:15:00","09:16:00","09:17:00")
    ]}}
    fake_dnse={"data":{
        "t":[int(datetime(2026,11,day,tzinfo=timezone.utc).timestamp())
             for day in (6,9,10)],
        "o":[100,101,102],"h":[103,104,105],"l":[98,99,100],
        "c":[101,102,103],"v":[10,11,12],
    }}
    now=datetime(2026,11,10,17,0,tzinfo=timezone.utc)
    ss=audit_transient_response(E.SSI_INTRADAY_SESSION,fake_ssi,
                                checked_at_utc=now)
    dn=audit_transient_response(E.DNSE_D1_HISTORY,fake_dnse,
                                checked_at_utc=now)
    if ss.state is not ProbeState.SHAPE_RETURNED or dn.state is not ProbeState.SHAPE_RETURNED:
        raise AssertionError("C2_SOURCE_MODE_SHAPE_CHANGED")
    if ss.observed_rows!=3 or dn.observed_rows!=3:
        raise AssertionError("MANUFACTURED_ROW_COUNT_CHANGED")
    if advise_connected_refresh(E.DNSE_D1_HISTORY,DataNeed.MINUTE_OHLCV).verdict is not RefreshVerdict.BLOCKED:
        raise AssertionError("DNSE_D1_FALSELY_QUALIFIED_M5")
    if advise_connected_refresh(E.SSI_INTRADAY_SESSION,DataNeed.MINUTE_OHLCV).verdict is not RefreshVerdict.REFETCH_WHOLE_SESSION:
        raise AssertionError("SSI_CONNECTED_SESSION_REFRESH_DRIFT")
    if len(ssi_date_candidates("13/10/2026 09:15:00"))!=1 or len(ssi_date_candidates("11/10/2026 09:15:00"))!=2:
        raise AssertionError("SSI_SOURCE_MODE_DATE_DISAMBIGUATION_DRIFT")
    return {
        "ssi_original_c2_shape":ss.state.value,
        "ssi_synthetic_rows":ss.observed_rows,
        "ssi_raw_date_semantic_authenticated":False,
        "ssi_m5_close_and_interval_authenticated":False,
        "ssi_ambiguous_latest_token_inferred":False,
        "dnse_original_c2_shape":dn.state.value,
        "dnse_synthetic_d1_rows":dn.observed_rows,
        "dnse_mcp_m5_parameter_present":False,
        "dnse_connected_minute_ohlcv_blocked":True,
        "real_source_payload_persisted":False,
    }

def evaluate():
    rows=matrix()
    vcbs=vcbs_probe(fabricated_vcbs(),"M5")
    if vcbs["source_has_per_candle_ohlcv"] or vcbs["valid_for_signal_indicators"]:
        raise AssertionError("VCBS_FALSE_OHLCV_PROMOTION")
    if any(x.qualified_native_ohlcv or x.signal_eligible for x in rows):
        raise AssertionError("PUBLIC_API_MCP_SHAPE_PROMOTED_TO_TRADING")
    if any(x.connected_endpoint is not E.VCBS_INTRADAY_PRICE_POINTS
           for x in rows if x.provider is Provider.VCBS and x.timeframe!="D1"):
        raise AssertionError("CONNECTED_VCBS_INTRADAY_CONTRACT_DRIFT")
    out={
        "schema":SCHEMA,
        "status":"UNVERIFIED_THREE_SOURCE_MATRIX_VCBS_REFERENCE_ONLY_NO_GO",
        "provider_count":3,"timeframe_count":6,"rows_count":18,
        "rows":[{
            "provider":x.provider.value,"timeframe":x.timeframe,
            "connected_endpoint":x.connected_endpoint.value,
            "connected_data_need":x.connected_data_need.value,
            "public_native_api_documented_unconnected":
                x.public_native_api_documented_unconnected,
            "status":x.status,"qualified_native_ohlcv":False,
            "signal_eligible":False,
        } for x in rows],
        "vcbs_fabricated_probe":vcbs,
        "ssi_dnse_synthetic_mode_probe":ssi_dnse_synthetic_source_modes(),
        "source_legal_first_known_and_auction_not_proven":True,
        **{k:False for k in GATES},
    }
    canonical=json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    out["synthetic_receipt_sha256"]=sha256(canonical.encode("ascii")).hexdigest()
    return out

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out",type=Path)
    a=ap.parse_args(argv)
    r=evaluate()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in r.items() if k!="rows"},sort_keys=True))

if __name__=="__main__":
    main()
