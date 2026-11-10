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
