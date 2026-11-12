"""A02 fifth DISTINCT set of eight inherited V1 SSI/DNSE/VCBS source boundaries.

Only ACTUAL original Swing V1 functions are evaluated; existing test_* modules
supply fabricated input constructors, NOT mocked V1 implementations.
Provider transport is local injected fixture callbacks only. Never connect a
live MCP/provider, persist licensed quotes or approve market/trading authority.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path

from swing_trading.source_capability_evidence import ProbeEndpoint, ProbeState
from swing_trading.ssi_intraday_label_diagnostics import (
    inspect_ssi_intraday_surface, LabelOrderEvidence,
)
from swing_trading.ssi_multivenue_review import (
    evaluate_ssi_venue_matrix, MatrixState,
)
from swing_trading.ssi_source_qualification import (
    inspect_timestamp, DateOrder,
)
from swing_trading.ssi_volume_parity import (
    audit_ssi_intraday_daily_volume, ParityState as SsiParity,
)
from swing_trading.dnse_d1_reference_fallback import (
    D1ReadState, D1Provider,
)
from swing_trading.vcbs_source_contract import (
    VcbsFeed, vcbs_capability, inspect_vcbs_raw_daily_row,
)
from swing_trading.d1_mcp_transport_bridge import (
    ReceiptState,
)
from swing_trading.c2_fair_source_benchmark import (
    ComparisonAxis, ComparisonStatus, PriceBasis,
    compare_transient_d1_pair, require_benchmark_source_authority,
)
from swing_trading.incremental_cache import Provider

from test_ssi_intraday_label_diagnostics import response, DAY as LABEL_DAY
from test_ssi_multivenue_review import full_matrix
from test_ssi_source_qualification import policy, OCT, DAY as AMBIGUOUS_DAY
from test_ssi_volume_parity import fixture as volumes, AS_OF
from test_dnse_d1_reference_fallback import route as dnse_route, ssi as ssi_quote, request
from test_vcbs_source_contract import row as vcbs_row, STAMP
from test_d1_mcp_transport_bridge import bridge, ssi_payload
from test_c2_fair_source_benchmark import row as fair_row

SCHEMA = "mst.a02.fifth-eight-ssi-dnse-vcbs-source-semantics.synthetic.no-go.v1"
EIGHT = (
    "ssi_intraday_label_diagnostics",
    "ssi_multivenue_review",
    "ssi_source_qualification",
    "ssi_volume_parity",
    "dnse_d1_reference_fallback",
    "vcbs_source_contract",
    "d1_mcp_transport_bridge",
    "c2_fair_source_benchmark",
)


def _verify(condition, reason):
    if not condition:
        raise AssertionError(reason)


def _denied(fn, exc=PermissionError):
    try:
        fn()
    except exc:
        return True
    raise AssertionError("UNTRUSTED_SOURCE_INPUT_PROMOTED_TO_REAL_MARKET_RIGHTS")


def evaluate_fifth_source_matrix():
    checks = {}
    # 1) Clock labels may have apparent gaps; this is NOT proof of M1 bars
    # lost, no-trade minutes, provider UTC timestamp, or first-known cutoff.
    labels = inspect_ssi_intraday_surface(
        ProbeEndpoint.SSI_INTRADAY,
        response("14/10/2026 09:03:00",
                 "14/10/2026 09:01:00",
                 "14/10/2026 09:00:00"),
        symbol="SHS", requested_day=LABEL_DAY, checked_at_utc=AS_OF,
    )
    _verify(labels.state is ProbeState.RETURNED_ROWS
            and labels.date_order_evidence is LabelOrderEvidence.DAY_FIRST_POSSIBLE_ONLY
            and labels.gaps_over_one_minute == 1
            and labels.unobserved_minutes_between_labels == 1
            and not labels.observed_gap_is_missing_candle
            and not labels.eligible_for_m1_m5_m15,
            "SSI_CLOCK_LABEL_GAP_FALSELY_CERTIFIED_AS_MISSING_CANDLE")
    checks["ssi_label_gap_not_missing_bar_or_first_known"] = True

    # 2) Three SSI venue self-reports are still ONE provider, not independent
    # rights and no certified market calendar or source timestamps.
    venue = evaluate_ssi_venue_matrix(full_matrix(), as_of_utc=AS_OF)
    duplicate = evaluate_ssi_venue_matrix(
        full_matrix()+(full_matrix()[0],), as_of_utc=AS_OF,
    )
    _verify(venue.state is MatrixState.ALL_VENUES_OBSERVED_UNCERTIFIED
            and venue.matched_count == 3
            and not venue.provider_independent
            and not venue.source_entitlement_certified
            and duplicate.state is MatrixState.BLOCKED
            and duplicate.blocked_samples[0][-1] == "DUPLICATE_SYMBOL_VENUE_DATE_SAMPLE",
            "SSI_THREE_VENUES_FALSELY_CERTIFY_MULTI_PROVIDER")
    checks["ssi_three_venues_one_provider_not_three_roots"] = True

    # 3) A DD/MM source sample that contradicts the described MM/DD
    # contract cannot become a known UTC market-bar end timestamp.
    time_unknown = inspect_timestamp(
        "13/10/2026 09:00:00", OCT, policy(), intraday=True,
    )
    time_ambiguous = inspect_timestamp(
        "04/11/2026 09:00:00", AMBIGUOUS_DAY, policy(), intraday=True,
    )
    _verify(time_unknown.reason_code == "DATE_ORDER_CONFLICT_OR_UNKNOWN"
            and not time_unknown.usable_for_market_time
            and time_ambiguous.interpreted_time_utc is None
            and len(time_ambiguous.date_candidates) == 2,
            "SSI_CONFLICTING_DATE_FORMAT_FALSE_UTC_CONVERSION")
    checks["ssi_date_order_mismatch_and_ambiguous_clock_blocked"] = True

    # 4) Equal matched volume doesn't prove each minute existed, nor that a
    # source is licensed. Missing intraday is not volume=0 or a holiday.
    minute_sample,daily_sample = volumes()
    parity = audit_ssi_intraday_daily_volume(
        minute_sample,daily_sample,as_of_utc=AS_OF,
    )
    bad_total = audit_ssi_intraday_daily_volume(
        minute_sample,replace(daily_sample,total_match_volume=4101),
        as_of_utc=AS_OF,
    )
    _verify(parity.state is SsiParity.MATCH_UNCERTIFIED
            and parity.summed_intraday_matched_volume == 4100
            and not parity.minute_coverage_certified
            and not parity.market_source_certified
            and bad_total.state is SsiParity.BLOCKED,
            "SSI_MATCHED_VOLUME_FALSE_MINUTE_COVERAGE_OR_BAD_TOTAL_NOT_REJECTED")
    checks["ssi_d1_vs_intraday_volume_equal_only_uncertified"] = True

    # 5) The D1-only fallback never promotes DNSE to a minute-bar provider.
    fallback = dnse_route()
    primary = dnse_route(ssi_callback=lambda r: ssi_quote())
    _verify(fallback.state is D1ReadState.FALLBACK_DNSE_REFERENCE_ONLY
            and fallback.source is D1Provider.DNSE
            and not fallback.eligible_for_indicators
            and not fallback.eligible_for_backtest
            and primary.state is D1ReadState.PRIMARY_SSI_REFERENCE_ONLY
            and not primary.fallback_attempted,
            "DNSE_D1_FALLBACK_OR_SSI_PRIMARY_SOURCE_BOUNDARY_CHANGED")
    checks["dnse_daily_fallback_reference_only_and_primary_not_mixed"] = True

    # 6) VCBS daily OHLC can be parsed as a REFERENCE, not the VCBS
    # intraday price-only chart being replaced with native minute bars.
    vcbs = inspect_vcbs_raw_daily_row(
        vcbs_row(),symbol="SYNX",retrieved_at_utc=STAMP,
    )
    series = vcbs_capability(VcbsFeed.SESSION_PRICE_SERIES)
    _verify(vcbs.provider == "VCBS"
            and not vcbs.rights_verified and not vcbs.indicators_allowed
            and not vcbs.actionable
            and not series.full_minute_ohlcv
            and not series.raw_ohlcv_candidate,
            "VCBS_RAW_REFERENCE_FALSE_LICENSE_OR_MINUTE_OHLC")
    checks["vcbs_raw_daily_not_minute_candle_or_trade"] = True

    # 7) Injected fixture callbacks are NOT live MCP. SSI explicit error
    # switches to DNSE with two segregated receipts; normal SSI avoids DNSE.
    local_bridge, local_calls = bridge()
    bridge_ssi = local_bridge.run(request())
    error = {"status":"error","data":None,
             "error":{"code":"DOWNSTREAM_UNAVAILABLE"}}
    fallback_bridge, fallback_calls = bridge(ssi_response=error)
    bridge_dnse = fallback_bridge.run(request())
    _verify([x[0] for x in local_calls] == ["SSI"]
            and bridge_ssi.audit.state is D1ReadState.PRIMARY_SSI_REFERENCE_ONLY
            and [x[0] for x in fallback_calls] == ["SSI","DNSE"]
            and bridge_dnse.audit.state is D1ReadState.FALLBACK_DNSE_REFERENCE_ONLY
            and tuple(x.provider for x in bridge_dnse.receipts) ==
                (D1Provider.SSI,D1Provider.DNSE)
            and bridge_dnse.receipts[0].state is ReceiptState.UNAVAILABLE
            and not bridge_dnse.actionable
            and not bridge_dnse.historical_backtest_qualified,
            "INJECTED_D1_BRIDGE_FALSE_AUTHORIZATION_OR_SOURCE_MIX")
    checks["bridge_injected_fallback_keeps_separate_receipts_not_real_api"] = True

    # 8) Even two different *caller-reported* price sources aren't
    # authenticated, and price/volume bases must match before comparison.
    fair = compare_transient_d1_pair(
        (fair_row(),),(fair_row(Provider.VCBS),),axis=ComparisonAxis.PRICE,
    )
    basis = compare_transient_d1_pair(
        (fair_row(),),(fair_row(Provider.DNSE,basis=PriceBasis.UNVERIFIED),),
        axis=ComparisonAxis.PRICE,
    )
    _verify(fair.status is ComparisonStatus.COMPARABLE_REPORTED
            and fair.equal_sessions == 1
            and not fair.source_integrity_verified
            and not fair.actionable
            and basis.status is ComparisonStatus.BLOCKED_BASIS
            and basis.unknown_basis_excluded == 1
            and _denied(lambda:require_benchmark_source_authority(fair)),
            "TWO_CALLER_REPORTED_VENDOR_NAMES_PROMOTED_TO_RIGHTS_OR_PARITY")
    checks["fair_d1_vendor_name_parity_not_independent_authenticated_source"] = True

    _verify(all(checks.values()) and len(checks)==8,
            "EIGHT_ACTUAL_ORIGINAL_V1_SOURCE_SEMANTIC_GUARDS_NOT_PASSED")
    return {
        "schema": SCHEMA,
        "status": "EIGHT_REAL_ORIGINAL_SSI_DNSE_VCBS_V1_RUNTIME_BOUNDARIES_PASS_NO_GO",
        "original_upstream_sha": "cd90c1babae8912db31490ad614fc2ad2f868042",
        "protected_main_sha": "4048f91beaaa3410116d97e35896c8b688384e19",
        "executed_original_modules": list(EIGHT),
        "distinct_original_this_batch": 8,
        "previous_distinct_originals": 32,
        "cumulative_scoped_runtime_originals": 40,
        "remaining_originals_without_tranche_style_runtime_qa": 23,
        "linked_safety_checks": checks,
        "linked_safety_count": len(checks),
        "ssi_m1_label_gaps_are_missing_bars_proven": False,
        "ssi_date_policy_certified_by_vendor": False,
        "three_venues_prove_provider_independence": False,
        "three_vendor_names_prove_independent_authentication": False,
        "real_provider_api_or_mcp_called": False,
        "full_native_m1_m5_m15_source_verified": False,
        "real_vendor_data_rights_verified": False,
        "source_quote_retention_approved": False,
        "physical_drive_market_cache_read_write": False,
        "human_owner_a02_module_dispositions": 0,
        "a03_v2_full_abi_behavior_owner_approved": False,
        "g01_g08_external_owner_security_gates_passed": False,
        "production_release_authorized": False,
        "trading_authorized": False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args(argv)
    out=evaluate_fifth_source_matrix()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,sort_keys=True))


if __name__=="__main__":
    main()
