"""Test-only DNSE WebSocket reconnect, replay, missing-close and conflict guard.

Composes the existing source-document closed/forming typed fixture. Expected
minutes are explicitly supplied HYPOTHETICAL grid cells, NOT an exchange
calendar or proof all bars should exist. Never connects to any live stream.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path

from scripts.m2_a03_documented_ohlc_transport_boundary_lab import (
    DocumentedTransport as Transport, UntrustedDocumentedDNSEBar as Bar,
    documented_channel_observation, fabricated,
)

SCHEMA="mst.a03.dnse-ws-reconnect-closed-bar-coverage-untrusted.v1"
NO_GO="DNSE_WS_REPLAY_AND_GAP_COVERAGE_SYNTHETIC_NO_SOURCE_AUTHORITY"
DENIED=(
 "actual_ws_access_ever_used","actual_exchange_calendar_qualified",
 "publisher_issuer_authenticated","source_sequence_or_resumption_contract_verified",
 "provider_history_backfill_authenticated","closed_feed_history_complete_verified",
 "source_revision_first_known_verified","independent_source_ledger_verified",
 "licensed_market_data_retention_authorized","real_drive_market_cache_active",
 "original_63_v1_or_8_v2_changed","a02_63_owner_approved",
 "a03_v2_8_owner_approved","a03_14_owner_approved",
 "production_release_authorized","trading_authorized",
)

@dataclass(frozen=True)
class LocalObservation:
    """Local *fabricated* collection generation is NOT a vendor sequence."""
    bar: Bar
    observed_at_utc: datetime
    local_connection_generation: int
    def __post_init__(self):
        if type(self.bar) is not Bar:
            raise TypeError("EXACT_SOURCE_DOCUMENT_BAR_FIXTURE_REQUIRED")
        t=self.observed_at_utc
        if (type(t) is not datetime or t.tzinfo is None or
            t.utcoffset()!=timedelta(0)):
            raise ValueError("EXACT_UTC_LOCAL_OBSERVER_REQUIRED")
        if (type(self.local_connection_generation) is not int or
            self.local_connection_generation<1):
            raise ValueError("POSITIVE_LOCAL_GENERATION_NOT_VENDOR_SEQ_REQUIRED")

def payload_tuple(bar:Bar):
    return (bar.open,bar.high,bar.low,bar.close,bar.volume,
            bar.lastUpdated,bar.resolution)

def reconcile(samples:tuple[LocalObservation,...],
              expected_starts:tuple[int,...])->dict:
    """Check observed synthetic events against *declared toy expected grid*.

    A clean result means observed shape coverage only, never broker/source
    qualification, official no-trade/auction bar expectations, or CAS closure.
    """
    if type(samples) is not tuple or any(type(x) is not LocalObservation for x in samples):
        raise TypeError("IMMUTABLE_TYPED_LOCAL_OBSERVATIONS_REQUIRED")
    if type(expected_starts) is not tuple or not expected_starts:
        raise TypeError("EXPLICIT_NONEMPTY_HYPOTHETICAL_GRID_REQUIRED")
    if any(type(x) is not int or x<1_000_000_000 or x>4_000_000_000 or x%300
           for x in expected_starts):
        raise ValueError("TYPED_UNIX_SECONDS_FIVE_MINUTE_GRID_REQUIRED")
    if tuple(sorted(set(expected_starts)))!=expected_starts:
        raise ValueError("STRICT_UNIQUE_ASCENDING_HYPOTHETICAL_GRID_REQUIRED")
    prev_obs=None;prev_gen=0
    by_start={}
    seen_closed=[]
    closed_count=0;forming_count=0
    exact_duplicates=0;conflicts=0
    forming_after_closed=0
    unknown_start=0;out_of_order=0;generation_increments=0
    for event in samples:
        if prev_obs is not None and event.observed_at_utc < prev_obs:
            raise ValueError("LOCAL_CAPTURE_OBSERVATIONS_NOT_MONOTONE")
        if event.local_connection_generation<prev_gen:
            raise ValueError("LOCAL_CONNECTION_GENERATION_ROLLBACK_DENIED")
        if prev_gen and event.local_connection_generation>prev_gen:
            generation_increments+=1
        prev_gen=event.local_connection_generation
        prev_obs=event.observed_at_utc
        bar=event.bar
        documented_channel_observation(bar,observed_at_utc=event.observed_at_utc)
        if bar.time not in expected_starts:
            unknown_start+=1
        if bar.transport is Transport.DNSE_WS_FORMING:
            forming_count+=1
            if bar.time in by_start:
                forming_after_closed+=1
            continue
        closed_count+=1
        if seen_closed and bar.time<seen_closed[-1]:
            out_of_order+=1
        seen_closed.append(bar.time)
        new=payload_tuple(bar)
        prior=by_start.get(bar.time)
        if prior is None:
            by_start[bar.time]=new
        elif prior==new:
            exact_duplicates+=1
        else:
            conflicts+=1
    missing=sum(x not in by_start for x in expected_starts)
    reasons=[]
    for key,count in (
        ("CLOSED_CANDLE_GAP_IN_HYPOTHETICAL_GRID",missing),
        ("CONFLICTING_CLOSED_REDELIVERY_NOT_A_SOURCE_REVISION",conflicts),
        ("CLOSED_BAR_OUT_OF_EVENT_ORDER",out_of_order),
        ("UNEXPECTED_BAR_OUTSIDE_EXPLICIT_GRID",unknown_start),
        ("FORMING_REDELIVERY_AFTER_CLOSED",forming_after_closed),
        ("CONNECTION_GENERATION_CHANGED_REQUIRES_BACKFILL",generation_increments),
    ):
        if count: reasons.append(key)
    # Duplicate identical payload is tracked but not proof of stream continuity.
    status=("INCOMPLETE_OR_UNVERIFIED_STREAM_REQUIRES_EXTERNAL_BACKFILL"
            if reasons else "STRUCTURALLY_COVERED_BUT_UNTRUSTED")
    return {
        "schema":SCHEMA,"status":status,
        "source_status":NO_GO,
        "hypothetical_expected_count":len(expected_starts),
        "observed_count":len(samples),
        "closed_event_count":closed_count,
        "forming_event_count":forming_count,
        "closed_grid_missing_count":missing,
        "closed_conflict_count":conflicts,
        "closed_exact_duplicate_count":exact_duplicates,
        "closed_out_of_order_count":out_of_order,
        "unexpected_time_count":unknown_start,
        "forming_after_closed_count":forming_after_closed,
        "local_reconnect_count":generation_increments,
        "reasons":reasons,
        "hypothetical_grid_not_official_market_calendar":True,
        "source_closed_stream_proven_complete":False,
        "source_first_known_proven":False,
        "must_not_auto_forge_revision_or_gap_fill":True,
        "source_eligible_for_signal":False,
    }

def toy_grid():
    base=fabricated().time
    return (base,base+300,base+600)

def close_at(i:int)->Bar:
    start=toy_grid()[0]+300*i
    original=fabricated()
    return replace(original,time=start,lastUpdated=start+301)

def forming_at(i:int)->Bar:
    original=close_at(i)
    return replace(original,transport=Transport.DNSE_WS_FORMING)

def samples_for(events:tuple[tuple[Bar,int],...]):
    base=toy_grid()[0]
    return tuple(LocalObservation(
        bar,event_time,gen) for bar,event_time,gen in (
            (b,datetime.fromtimestamp(base+4000+idx,timezone.utc),g)
            for idx,(b,g) in enumerate(events))
    )

def make_scenario_rows():
    b0,b1,b2=close_at(0),close_at(1),close_at(2)
    return {
        "COMPLETE_UNTRUSTED":((b0,1),(b1,1),(b2,1)),
        "NO_CLOSED_MIDDLE":((b0,1),(b2,1)),
        "FORMING_NOT_CLOSED":((b0,1),(forming_at(1),1),(b2,1)),
        "CLOSED_OUT_OF_ORDER":((b0,1),(b2,1),(b1,1)),
        "EXACT_DUPLICATE_NOT_PROOF":((b0,1),(b1,1),(b1,1),(b2,1)),
        "CONFLICTING_DUPLICATE":((b0,1),(b1,1),
                                 (replace(b1,volume=b1.volume+1),1),(b2,1)),
        "RECONNECT_COMPLETE_STILL_UNTRUSTED":((b0,1),(b1,2),(b2,2)),
        "RECONNECT_AND_GAP":((b0,1),(b2,2)),
        "FORMING_AFTER_CLOSED":((b0,1),(b1,1),(forming_at(1),1),(b2,1)),
        "UNEXPECTED_BAR":((b0,1),(b1,1),(b2,1),(close_at(3),1)),
    }

def build():
    cases={}
    for name,events in make_scenario_rows().items():
        result=reconcile(samples_for(events),toy_grid())
        cases[name]={
            "status":result["status"],"reasons":result["reasons"],
            "missing":result["closed_grid_missing_count"],
            "duplicate":result["closed_exact_duplicate_count"],
            "conflicts":result["closed_conflict_count"],
            "reordered":result["closed_out_of_order_count"],
            "reconnect":result["local_reconnect_count"],
            "signal_eligible":result["source_eligible_for_signal"],
        }
    if len(cases)!=10:raise AssertionError("TEN_DISTINCT_STREAM_SCENARIOS_REQUIRED")
    if cases["COMPLETE_UNTRUSTED"]["status"]!="STRUCTURALLY_COVERED_BUT_UNTRUSTED":
        raise AssertionError("CLEAN_TOY_COVERAGE_NOT_RECOGNIZED")
    if cases["NO_CLOSED_MIDDLE"]["missing"]!=1:
        raise AssertionError("MISSING_TOY_CLOSED_EVENT_UNRECOGNIZED")
    if cases["RECONNECT_COMPLETE_STILL_UNTRUSTED"]["reconnect"]!=1:
        raise AssertionError("LOCAL_RECONNECT_UNRECOGNIZED")
    if cases["CONFLICTING_DUPLICATE"]["conflicts"]!=1:
        raise AssertionError("CLOSED_CONFLICT_NOT_QUARANTINED")
    if any(x["signal_eligible"] for x in cases.values()):
        raise AssertionError("UNVERIFIED_WEBSOCKET_ENABLED_SIGNALS")
    out={
        "schema":SCHEMA,"status":NO_GO,
        "scenario_count":len(cases),
        "cases":cases,
        "source_channel":"DNSE_PUBLIC_DOCUMENTED_WEBSOCKET_NOT_CONNECTED",
        "fake_local_connection_generation_not_issuer_sequence":True,
        "fake_grid_not_official_session_holiday_auction":True,
        "no_real_ws_rows_or_source_timestamps_saved":True,
        **{key:False for key in DENIED}
    }
    payload=json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    out["synthetic_receipt_sha256"]=sha256(payload.encode("ascii")).hexdigest()
    return out

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path)
    args=p.parse_args(argv)
    r=build()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in r.items() if k!="cases"},sort_keys=True))

if __name__=="__main__":
    main()
