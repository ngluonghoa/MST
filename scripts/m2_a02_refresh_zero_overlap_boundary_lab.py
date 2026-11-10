"""A02 original V1 cache planner exact-close zero-overlap defect characterization.

Runs unchanged Swing Trading 1.8 code on fabricated UTC minutes.
NO external provider, network/cache write, source rights, or trading permission.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from swing_trading.cache_fetch_planner import (
    SourceCapability, SourceCursor, RefreshAction, plan_refresh,
)
T0 = datetime(2026, 11, 10, 2, 0, tzinfo=timezone.utc)
FIVE = timedelta(minutes=5)
SCHEMA = "mst.a02.legacy-refresh-exact-close-zero-overlap-gap.v1"
STATUS = "ORIGINAL_V1_EMPTY_WINDOW_BUG_REPRODUCED_OWNER_DISPOSITION_OPEN"
CASES = (
    ("EXACT_CLOSE_ZERO_OVERLAP", dict(overlap=0), "ERROR_EMPTY_REQUEST"),
    ("EXACT_CLOSE_ZERO_OVERLAP_SESSION_FLAG", dict(overlap=0,session_final=True), "ERROR_EMPTY_REQUEST"),
    ("EXACT_CLOSE_ZERO_OVERLAP_HEAD_FLAG", dict(overlap=0,head_final=True), "ERROR_EMPTY_REQUEST"),
    ("EXACT_CLOSE_ZERO_OVERLAP_PREVIEW", dict(overlap=0,checked=50,preview=True), "ERROR_EMPTY_REQUEST"),
    ("EXACT_CLOSE_ONE_OVERLAP", dict(overlap=1), "WINDOW_45_50"),
    ("EXACT_CLOSE_TWENTYFOUR_OVERLAP", dict(overlap=24), "WINDOW_0_50"),
    ("ONE_MIN_AFTER_CLOSE_ZERO_OVERLAP", dict(overlap=0,now=51), "WINDOW_50_51"),
    ("ONE_MIN_BEFORE_NEXT_CLOSE_ZERO_OVERLAP", dict(overlap=0,now=49,latest=40,closed=40,checked=40,full=40), "WINDOW_45_49"),
    ("NEW_CLOSED_BAR_ZERO_OVERLAP", dict(overlap=0,closed=40,checked=45), "WINDOW_45_50"),
    ("NEW_CLOSED_BAR_ONE_OVERLAP", dict(overlap=1,closed=40,checked=45), "WINDOW_40_50"),
    ("EXACT_CLOSE_NO_DUE", dict(overlap=0,checked=50), "REUSE"),
    ("EXACT_CLOSE_REFRESH_INTERVAL_NOT_DUE", dict(overlap=0,refresh=6), "REUSE"),
    ("EXACT_CLOSE_RECONCILE_DUE", dict(overlap=0,full=10), "FULL_0_50"),
    ("EXACT_CLOSE_NO_FULL_RECONCILE_YET", dict(overlap=0,full=None), "FULL_0_50"),
    ("EXACT_CLOSE_FULL_PROVIDER", dict(overlap=0,cap="FULL_SESSION"), "FULL_0_50"),
    ("EXACT_CLOSE_UNKNOWN_PROVIDER", dict(overlap=0,cap="UNKNOWN"), "BLOCKED"),
    ("EXACT_CLOSE_COLD", dict(overlap=0,cold=True), "FULL_0_50"),
    ("EXACT_CLOSE_BOTH_FINALITY_FLAGS", dict(overlap=0,session_final=True,head_final=True), "REUSE_FINALITY_CLAIM"),
    ("EXACT_CLOSE_UNKNOWN_WITH_FINALITY", dict(overlap=0,cap="UNKNOWN",session_final=True,head_final=True), "BLOCKED"),
    ("EXACT_CLOSE_SOURCE_REWIND", dict(overlap=0,closed=46,checked=46,full=46), "BLOCKED"),
    ("EXACT_CLOSE_PREVIEW_ONE_OVERLAP", dict(overlap=1,checked=50,preview=True), "WINDOW_45_50"),
    ("EXACT_CLOSE_NEW_BAR_FULL_PROVIDER", dict(cap="FULL_SESSION",closed=40,checked=45), "FULL_0_50"),
)
BUG_CASES = frozenset(x[0] for x in CASES if x[2] == "ERROR_EMPTY_REQUEST")
DENIALS = ("original_v1_source_modified","a02_owner_approved","a03_v2_full_parity_approved",
    "vendor_entitlement_and_source_verified","official_market_calendar_verified",
    "real_drive_market_cache_authorized","external_floor_cas_proven",
    "production_release_authorized","trading_authorized")


def time(minute: int) -> datetime:
    return T0 + timedelta(minutes=minute)


def call_original(settings: dict) -> dict:
    cfg = dict(now=50, latest=45, closed=45, checked=45, full=45, overlap=1,
               cap="WINDOWED", cold=False, preview=False,
               session_final=False, head_final=False, refresh=5)
    cfg.update(settings)
    cursor = None if cfg["cold"] else SourceCursor(
        time(cfg["closed"]),time(cfg["checked"]),
        None if cfg["full"] is None else time(cfg["full"]))
    try:
        r=plan_refresh(now_utc=time(cfg["now"]), session_start_utc=time(0),
            latest_expected_closed_start_utc=time(cfg["latest"]),
            bar_duration=FIVE, capability=SourceCapability[cfg["cap"]],
            cursor=cursor, overlap_bars=cfg["overlap"],
            refresh_interval=timedelta(minutes=cfg["refresh"]),
            correction_reconcile_interval=timedelta(minutes=30),
            provisional_requested=cfg["preview"],
            session_ended_verified=cfg["session_final"],
            immutable_source_head_verified=cfg["head_final"])
    except ValueError as exc:
        if str(exc) != "Empty request":
            raise
        return {"kind":"ERROR_EMPTY_REQUEST","detail":"ValueError: Empty request"}
    if r.certified_source_freshness or r.data_authorized:
        raise AssertionError("PLANNER_FALSE_SOURCE_OR_TRADING_AUTHORIZATION")
    if r.action in (RefreshAction.REQUEST_WINDOW,RefreshAction.REQUEST_FULL_SESSION):
        if r.start_utc is None or r.end_utc is None or r.start_utc >= r.end_utc:
            raise AssertionError("INVALID_RETURNED_REQUEST_WINDOW")
        start=int((r.start_utc-T0)/timedelta(minutes=1))
        end=int((r.end_utc-T0)/timedelta(minutes=1))
        prefix="WINDOW" if r.action is RefreshAction.REQUEST_WINDOW else "FULL"
        return {"kind":f"{prefix}_{start}_{end}","reason":r.reason}
    if r.action is RefreshAction.BLOCKED:
        return {"kind":"BLOCKED","reason":r.reason}
    if r.action is RefreshAction.REUSE_CLOSED:
        return {"kind":"REUSE_FINALITY_CLAIM" if "FINALITY" in r.reason else "REUSE",
                "reason":r.reason}
    raise AssertionError("UNKNOWN_ORIGINAL_REFRESH_ACTION")


def evaluate() -> dict:
    output=[]
    for name,arguments,expected in CASES:
        observed=call_original(arguments)
        if observed["kind"]!=expected:
            raise AssertionError("ORIGINAL_V1_BOUNDARY_OUTCOME_DRIFT_"+name)
        output.append({"name":name,"expected":expected,"actual":observed["kind"]})
    n=sum(x["actual"]=="ERROR_EMPTY_REQUEST" for x in output)
    if n!=4 or len(output)!=22:
        raise AssertionError("ORIGINAL_ZERO_OVERLAP_BUG_FIXTURE_SCOPE_CHANGED")
    result=dict(schema=SCHEMA,status=STATUS,scenario_count=len(output),
       reproduced_original_value_error_cases=n,
       unaffected_neighbor_scenario_count=len(output)-n,
       original_no_overlap_valid_input_exception_reproduced=True,
       original_exception_message="ValueError: Empty request",
       original_unchanged_behavior_requires_owner_disposition=True,
       no_independent_live_provider_called=True,
       cases=output,**{name:False for name in DENIALS})
    payload=json.dumps(result,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    result["synthetic_case_index_sha256"]=sha256(payload.encode("ascii")).hexdigest()
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path)
    a=p.parse_args(argv)
    result=evaluate()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="cases"},sort_keys=True))


if __name__=="__main__":
    main()
