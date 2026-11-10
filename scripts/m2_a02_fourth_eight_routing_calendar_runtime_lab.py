"""MST A02 fourth distinct eight original-V1 routing/calendar/data-quality runtime tranche.

Calls actual unmodified inherited V1 functions, with original pre-existing
test/ fixture constructors only. All payloads are invented, no network calls,
licensed quotes, exchange calendar authority, official session data, broker
orders, real Drive cache, external signer or owner approvals.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date, timedelta
import json
from pathlib import Path

from swing_trading.adaptive_source_router import RouteMode, SourceTask, PriceBasis, PriceUnit
from swing_trading.c2_source_capability_audit import (
    ConnectedEndpoint, DataNeed, ProbeState, RefreshVerdict,
    audit_transient_response, advise_connected_refresh,
    require_authorized_c2_source,
)
from swing_trading.c2_session_probe_readiness import (
    summarize_session_probes, session_coverage,
    require_authorized_session_metrics,
)
from swing_trading.d1_atr_reconciliation import (
    SessionAuditState, audit_d1_session_inventory,
)
from swing_trading.native_minute_bar_source_plan import (
    BarProduct, SourceBarGateClosed, candidate_native_bar_sources,
    sketch_first_page_query,
)
from swing_trading.session_calendar import SessionType
from swing_trading.ssi_historical_availability import HistoricalAvailabilityState
from swing_trading.vn_2026_closure_anchors import (
    ClosureAuditState, audit_2026_notice_closure_collisions,
)
from swing_trading.incremental_cache import Provider
from swing_trading.market_data import Timeframe

# Existing, purely synthetic test-construction helpers. These do NOT replace
# the eight original V1 domain functions under evaluation.
from test_adaptive_source_router import NOW, candidate, probe as route_probe, select
from test_c2_source_capability_audit import (
    run as shape_run, ssi_row, ssi_d1, ssi_minute, dnse, dnse_row,
    vcbs_row,
)
from test_c2_session_probe_readiness import probe as session_probe
from test_d1_atr_reconciliation import AS_OF, d1, sessions
from test_native_minute_bar_source_plan import DAY as PLAN_DAY, START, END
from test_session_calendar import T as CAL_T, bar as calendar_bar, snapshot as calendar_snapshot, session
from test_ssi_historical_availability import probe as ssi_review
from test_ssi_volume_parity import fixture as ssi_receipts
from test_vn_2026_closure_anchors import inventory

SCHEMA = "mst.a02.original-v1-fourth-eight-routing-calendar-no-go.v1"
EIGHT = (
    "adaptive_source_router",
    "c2_source_capability_audit",
    "c2_session_probe_readiness",
    "d1_atr_reconciliation",
    "native_minute_bar_source_plan",
    "session_calendar",
    "ssi_historical_availability",
    "vn_2026_closure_anchors",
)


def _need(cond, name):
    if not cond:
        raise AssertionError(name)


def _deny(fn, exc=PermissionError):
    try:
        fn()
    except exc:
        return True
    raise AssertionError("UNAUTHORIZED_CLAIM_OR_INVALID_SOURCE_WAS_ACCEPTED")


def execute_fourth_eight_runtime():
    # 1. Reference router task, speed and quality: diagnostics do NOT
    # authenticate provider, rights or an actual candle.
    dnse_diag = candidate(Provider.DNSE)
    ssi_diag = candidate(Provider.SSI)
    vcbs_diag = candidate(Provider.VCBS)
    route = select(ssi_diag, dnse_diag, vcbs_diag)
    minute = select(
        candidate(Provider.DNSE, SourceTask.M1_OHLCV),
        candidate(Provider.SSI, SourceTask.M1_OHLCV),
        candidate(Provider.VCBS, SourceTask.M1_OHLCV),
        task=SourceTask.M1_OHLCV,
    )
    blocked_route = select(
        candidate(Provider.DNSE, SourceTask.M1_OHLCV),
        candidate(Provider.VCBS, SourceTask.M1_OHLCV),
        task=SourceTask.M1_OHLCV,
    )
    wrong_basis = select(
        candidate(Provider.DNSE, price_basis=PriceBasis.ADJUSTED),
        task=SourceTask.D1_OHLCV,
    )
    _need(
        route.mode is RouteMode.REFERENCE_CANDIDATE
        and route.selected is Provider.DNSE
        and not route.source_authority_verified
        and not route.persistence_authorized
        and not route.trading_actionable
        and minute.selected is Provider.SSI
        and minute.reference_only
        and blocked_route.mode is RouteMode.BLOCKED
        and wrong_basis.mode is RouteMode.BLOCKED,
        "REFERENCE_ROUTER_QUALITY_BEFORE_LATENCY_OR_FALSE_MINUTE_SOURCE",
    )

    # 2. Actual C2 metadata-only shape schema, distinct provider feeds.
    shapes = {
        "ssi_daily": shape_run(ConnectedEndpoint.SSI_D1_DETAILED,
                               ssi_d1(ssi_row())),
        "ssi_bad_ohlc": shape_run(ConnectedEndpoint.SSI_D1_DETAILED,
                                  ssi_d1(ssi_row(high=9800))),
        "dnse_daily": shape_run(ConnectedEndpoint.DNSE_D1_HISTORY,
                                dnse(dnse_row())),
        "vcbs_daily": shape_run(ConnectedEndpoint.VCBS_D1_WINDOW,
                                [vcbs_row()]),
        "ssi_empty": shape_run(ConnectedEndpoint.SSI_INTRADAY_SESSION,
                               ssi_minute()),
    }
    _need(shapes["ssi_daily"].state is ProbeState.SHAPE_RETURNED
          and shapes["dnse_daily"].state is ProbeState.SHAPE_RETURNED
          and shapes["vcbs_daily"].state is ProbeState.SHAPE_RETURNED
          and shapes["ssi_bad_ohlc"].state is ProbeState.SCHEMA_REJECTED
          and shapes["ssi_empty"].state is ProbeState.EMPTY_UNVERIFIED
          and all(not x.production_adapter_enabled and not x.source_authority_verified
                  and not x.trading_actionable for x in shapes.values())
          and _deny(lambda: require_authorized_c2_source(shapes["ssi_daily"])),
          "MCP_SHAPE_CANNOT_BE_VENDOR_ENTITLEMENT_OR_NATIVE_BAR",
    )
    minute_advice = advise_connected_refresh(
        ConnectedEndpoint.SSI_INTRADAY_SESSION, DataNeed.MINUTE_OHLCV)
    invalid_delta = advise_connected_refresh(
        ConnectedEndpoint.SSI_INTRADAY_SESSION, DataNeed.MINUTE_OHLCV,
        changed_since_required=True)
    _need(minute_advice.verdict is RefreshVerdict.REFETCH_WHOLE_SESSION
          and invalid_delta.verdict is RefreshVerdict.BLOCKED
          and not minute_advice.source_authority_verified,
          "C2_NO_FIVE_MINUTE_MCP_CURSOR_INVENTED")

    # 3. One synthetic set of 5 probe latencies. These are not measured
    # external-wire bytes or provider SLAs.
    metrics = summarize_session_probes(tuple(
        session_probe(client_monotonic_elapsed_ns=n*1_000_000)
        for n in (50,100,120,300,900)))[0]
    short_metrics = summarize_session_probes(
        tuple(session_probe() for _ in range(4)))[0]
    coverage = session_coverage((session_probe(),))[0]
    _need(
        metrics.median_elapsed_ms == 120
        and metrics.p95_elapsed_ms == 900
        and not metrics.provider_sla_verified
        and not metrics.router_eligible
        and metrics.measured_network_wire_samples == 0
        and short_metrics.p95_elapsed_ms is None
        and "MULTIPLE_WEEKDAY_SESSIONS_MISSING" in coverage.missing_review_gates
        and not coverage.validated_market_session
        and _deny(lambda: require_authorized_session_metrics(metrics)),
        "UNMEASURED_PROBE_LATENCY_FALSELY_PROMOTED",
    )

    # 4. Explicit untrusted inventory matching does NOT mean there were no
    # omitted real trading dates.
    history = d1(20)
    invented = sessions(history)
    match = audit_d1_session_inventory(history, invented, as_of_utc=AS_OF)
    missing = audit_d1_session_inventory(history[:-1], invented, as_of_utc=AS_OF)
    _need(
        match.state is SessionAuditState.MATCH_UNCERTIFIED
        and match.expected_count == 20 and match.actual_count == 20
        and not match.calendar_certified and not match.actionable
        and missing.state is SessionAuditState.BLOCKED
        and missing.missing_session_ids
        and not missing.actionable,
        "D1_MISSING_HISTORY_SILENTLY_SMOOTHED_OR_CALENDAR_CERTIFIED",
    )

    # 5. Connected intraday tick tool is not a native M1/M5/M15 closed bar
    # tool. Publicly documented OHLC external product sketches are inert.
    all_minute = candidate_native_bar_sources(Timeframe.M5)
    ssi_sketch = sketch_first_page_query(
        BarProduct.SSI_FASTCONNECT_INTRADAY_OHLC,Timeframe.M1,
        symbol="FPT",session_day=PLAN_DAY,
    )
    dnse_sketch = sketch_first_page_query(
        BarProduct.DNSE_OPENAPI_OHLC,Timeframe.M5,
        symbol="FPT",session_day=PLAN_DAY,
        start_utc=START,end_utc=END,
    )
    _need(
        len(all_minute) == 4
        and all(not x.executable and not x.actionable for x in all_minute)
        and not ssi_sketch.connected and not ssi_sketch.ready_to_send
        and not dnse_sketch.connected and not dnse_sketch.ready_to_send
        and not dnse_sketch.retention_approved
        and _deny(lambda: sketch_first_page_query(
            BarProduct.SSI_CONNECTED_INTRADAY_TICKS,Timeframe.M5,
            symbol="FPT",session_day=PLAN_DAY),SourceBarGateClosed)
        and _deny(lambda: sketch_first_page_query(
            BarProduct.SSI_FASTCONNECT_INTRADAY_OHLC,Timeframe.M15,
            symbol="FPT",session_day=PLAN_DAY),SourceBarGateClosed),
        "PUBLIC_NATIVE_OHLC_DOCS_PROMOTED_TO_CONNECTED_MCP",
    )

    # 6. Only a fabricated VERIFIED continuous same-session period can
    # structurally contain a synthetic M15 bar. Auction and lunch gap don't.
    positive = calendar_snapshot().resolve_intraday(
        calendar_bar(),CAL_T+timedelta(minutes=15))
    unverified = calendar_snapshot(verified=False).resolve_intraday(
        calendar_bar(),CAL_T+timedelta(minutes=15))
    outside = calendar_snapshot().resolve_intraday(
        calendar_bar(CAL_T+timedelta(minutes=45)),
        CAL_T+timedelta(hours=2,minutes=15))
    auction = calendar_snapshot((session("ATC",kind=SessionType.AUCTION),))
    _need(
        positive is not None and positive.session_id == "AM"
        and unverified is None and outside is None
        and auction.resolve_intraday(
            calendar_bar(sid="ATC"),CAL_T+timedelta(minutes=15)) is None,
        "INTRADAY_GAP_AUCTION_OR_UNVERIFIED_SESSION_INCLUDED",
    )

    # 7. A successful empty SSI intraday history alongside DAILY positive
    # matched volume means unresolved availability, not 'no trades'.
    intraday, daily = ssi_receipts()
    matching = ssi_review()
    empty_positive = ssi_review(intraday=replace(intraday,rows=()))
    empty_zero = ssi_review(
        intraday=replace(intraday,rows=()),
        daily=replace(daily,total_match_volume=0),
    )
    _need(
        matching.state is HistoricalAvailabilityState.NONEMPTY_MATCHED_UNCERTIFIED
        and empty_positive.state is HistoricalAvailabilityState.INTRADAY_EMPTY_DAILY_TRADES_UNCERTIFIED
        and empty_zero.state is HistoricalAvailabilityState.BLOCKED
        and not matching.source_entitlement_certified
        and not matching.complete_m1_history_certified
        and not empty_positive.actionable,
        "HISTORICAL_EMPTY_NOT_DAILY_ZERO_OR_LICENSE",
    )

    # 8. Selected published 2026 HOSE/HNX closure anchors block synthetic
    # expected sessions on an announced closure, but no full calendar exists.
    closed_day = date(2026,1,2)
    closed_hose = audit_2026_notice_closure_collisions(
        inventory(closed_day),exchange="HOSE")
    closed_hnx = audit_2026_notice_closure_collisions(
        inventory(closed_day),exchange="HNX")
    ordinary = audit_2026_notice_closure_collisions(
        inventory(date(2026,1,5)),exchange="HOSE")
    _need(
        closed_hose.state is ClosureAuditState.BLOCKED
        and closed_hnx.state is ClosureAuditState.BLOCKED
        and ordinary.state is ClosureAuditState.NO_KNOWN_COLLISION_UNCERTIFIED
        and not closed_hose.full_calendar_certified
        and not ordinary.full_calendar_certified,
        "EXPLICIT_CLOSURE_NOT_BLOCKED_OR_FALSE_FULL_CALENDAR",
    )
    checks = {
        "routing_reference_D1_DNSE_M1_SSI_only_not_authority": True,
        "C2_three_vendor_schema_shape_not_rights": True,
        "C2_no_unverified_incremental_cursor": True,
        "five_synthetic_probe_latency_not_SLA": True,
        "missing_D1_session_inventory_blocks_atr_replay": True,
        "native_M1_M5_endpoint_catalog_not_connected": True,
        "synthetic_session_no_auction_or_gap_leak": True,
        "SSI_empty_intraday_positive_daily_not_zero_trade": True,
        "2026_known_closure_collision_blocks_without_full_calendar": True,
    }
    return {
        "schema": SCHEMA,
        "status": "FOURTH_EIGHT_ORIGINAL_ROUTING_SESSION_DATA_QA_PASS_PRODUCTION_NO_GO",
        "original_upstream_sha": "cd90c1babae8912db31490ad614fc2ad2f868042",
        "protected_main_sha": "4048f91beaaa3410116d97e35896c8b688384e19",
        "executed_original_modules": list(EIGHT),
        "this_tranche_distinct_modules": 8,
        "prior_tranches_distinct_modules": 24,
        "cumulative_distinct_original_v1_module_count": 32,
        "remaining_original_v1_without_tranche_runtime_qa": 31,
        "linked_check_count": len(checks),
        "linked_checks": checks,
        "synthetic_probe_median_ms": metrics.median_elapsed_ms,
        "synthetic_probe_p95_ms": metrics.p95_elapsed_ms,
        "source_license_verified": False,
        "official_full_exchange_calendar_verified": False,
        "real_provider_source_credential_bound": False,
        "real_minute_history_coverage_verified": False,
        "actual_provider_network_call_made": False,
        "actual_drive_market_cache_read_write": False,
        "a02_owner_signed_modules": 0,
        "a03_v2_full_abi_approved": False,
        "g01_g08_actual_security_gates_closed": False,
        "production_release_authorized": False,
        "trading_authorized": False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path)
    args=p.parse_args(argv)
    report=execute_fourth_eight_runtime()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,sort_keys=True))


if __name__=="__main__":
    main()
