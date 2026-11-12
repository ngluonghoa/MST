"""MST A02 — actual eight high-impact inherited V1 behavior gates, synthetic only.

Invokes the real locked V1 modules and *existing* independent cache oracle
and market/quality/transaction boundary labs. This joins execution decisions
across modules, not merely AST signatures. Safety-relevant inherited permissive
behaviors are documented as gaps, not patched or called production-ready.

No vendor feed, real signed market authority, broker execution, real Drive
cache, local user runtime, M4 signing/root/bypass or release.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from hashlib import sha256
import json
from pathlib import Path

from scripts.m2_a02_incremental_cache_oracle_lab import run_cache_oracle_lab
from scripts.m2_a02_market_cache_execution_boundary_lab import (
    build_candles, minute, run_boundary_matrix,
)
from swing_trading.contracts import (
    DecisionStatus, Evidence, SignalDecision, Strategy, ZONE_IDS,
)
from swing_trading.engine import evaluate_unimplemented_zones
from swing_trading.replay import ReplayClock
from swing_trading.market_data import BarClosure, Quality
from swing_trading.source_quality import QualityState, SourceEvidence
from swing_trading.cache_fetch_planner import (
    RefreshAction, SourceCapability, SourceCursor, plan_refresh,
)
from swing_trading.vn_backtest_execution_fixture import (
    VNBarVerdict, inspect_fixture_vn_long_exit_bar, require_vn_backtest_release,
)

SCHEMA = "mst.a02.legacy-eight-inherited-behavior-boundary.synthetic.v1"
EIGHT = (
    "contracts", "engine", "replay", "market_data", "source_quality",
    "incremental_cache", "cache_fetch_planner", "vn_backtest_execution_fixture",
)
MOMENTS = (14, 15, 20, 24, 25, 30)
MAIN_SHA = "4048f91beaaa3410116d97e35896c8b688384e19"
SOURCE_SHA = "cd90c1babae8912db31490ad614fc2ad2f868042"


def _canon(item):
    return json.dumps(item, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def _sha(item):
    return sha256(_canon(item).encode("ascii")).hexdigest()


def expected_unverified_zone_decisions(*, when_utc: datetime, strategy: Strategy):
    """Actual V1 engine decisions, never pretend detectors are implemented."""
    decisions = evaluate_unimplemented_zones(strategy, when_utc)
    if len(decisions) != len(ZONE_IDS) or tuple(x.zone_id for x in decisions) != ZONE_IDS:
        raise AssertionError("V1_ZONE_ORDER_OR_COUNT_DRIFT")
    if any(x.strategy != strategy or x.status is not DecisionStatus.UNVERIFIED
           or x.evidence != () for x in decisions):
        raise AssertionError("UNIMPLEMENTED_ZONE_FALSE_POSITIVE")
    return decisions


def evaluate_behavior_matrix():
    legacy, rich = build_candles()
    candles = run_boundary_matrix()
    cache = run_cache_oracle_lab()
    snapshots = []

    for at in MOMENTS:
        as_of = minute(at)
        clock = ReplayClock(as_of)
        legacy_known = clock.known(legacy.revision.first_known_time_utc)
        rich_known = clock.known(rich.observation_revision.first_known_time_utc)
        known_verified = clock.known(rich.verified_at_utc)
        legacy_eligible = legacy.eligible_for_confirmed_signals(clock.as_of_utc)
        richer_prerequisites = rich.confirmation_prerequisites(clock.as_of_utc)
        by_strat = []
        for strategy in (Strategy.SHORT, Strategy.SWING):
            decisions = expected_unverified_zone_decisions(
                when_utc=clock.as_of_utc, strategy=strategy,
            )
            by_strat.append({
                "strategy": strategy.value,
                "count": len(decisions),
                "all_unverified": all(x.status is DecisionStatus.UNVERIFIED for x in decisions),
                "all_evidence_empty": all(x.evidence == () for x in decisions),
                "zones": [x.zone_id for x in decisions],
            })
        observed = candles["candle_snapshots"][MOMENTS.index(at)]
        if (legacy_eligible != observed["legacy_simple_quality_necessary"]
                or richer_prerequisites != observed["v12_source_prerequisites"]
                or legacy_known != rich_known):
            raise AssertionError("CROSS_MODULE_CANDLE_ASOF_BEHAVIOR_DRIFT")
        snapshots.append({
            "minute": at,
            "first_known_revision_visible": legacy_known,
            "verification_timestamp_reached": known_verified,
            "v1_simple_eligible": legacy_eligible,
            "v12_source_prerequisites": richer_prerequisites,
            "not_full_trade_authorization": True,
            "strategies": by_strat,
        })

    if [s["v1_simple_eligible"] for s in snapshots] != [
        False, True, True, True, True, True,
    ] or [s["v12_source_prerequisites"] for s in snapshots] != [
        False, False, False, False, True, True,
    ]:
        raise AssertionError("INHERITED_V1_V12_PRECONDITIONS_CONFLATED")

    # Cross-boundary negative edges run on actual inherited V1 classes.
    v1_missing_volume = replace(legacy, volume=None)
    v1_open = replace(legacy, closure=BarClosure.OPEN)
    v1_unverified = replace(legacy, quality=Quality.UNVERIFIED)
    v12_missing_entitlement = replace(
        rich, provenance=replace(rich.provenance, entitlement_verified=False),
    )
    v12_quality_flag = replace(rich, quality_flags=frozenset({"FIXTURE_WARNING"}))
    v12_unverified = replace(rich, quality_state=QualityState.UNVERIFIED)
    at = minute(30)
    guard_rejections = {
        "v1_missing_volume_rejected": not v1_missing_volume.eligible_for_confirmed_signals(at),
        "v1_open_bar_rejected": not v1_open.eligible_for_confirmed_signals(at),
        "v1_unverified_quality_rejected": not v1_unverified.eligible_for_confirmed_signals(at),
        "v12_missing_entitlement_claim_rejected": not v12_missing_entitlement.confirmation_prerequisites(at),
        "v12_source_quality_flag_rejected": not v12_quality_flag.confirmation_prerequisites(at),
        "v12_unverified_quality_rejected": not v12_unverified.confirmation_prerequisites(at),
        "v1_zero_volume_is_known_not_missing": legacy.volume == 0
        and legacy.eligible_for_confirmed_signals(at),
    }
    if not all(guard_rejections.values()):
        raise AssertionError("V1_V12_QUALITY_NEGATIVE_GUARDS_NOT_ENFORCED")

    # V1 has known permissive mutability/type behavior; report as gaps.
    mutable_clock = ReplayClock(minute(30))
    mutable_clock.advance_to(minute(30))
    try:
        mutable_clock.advance_to(minute(15))
    except ValueError:
        reverse_time_guard = True
    else:
        raise AssertionError("REPLAY_CLOCK_API_ACCEPTED_REVERSE_TIME")
    mutable_clock.as_of_utc = minute(15)  # documented legacy field assignment gap
    direct_assignment_rewind_gap = mutable_clock.as_of_utc == minute(15)
    permissive = Evidence(
        "SYNTHETIC_UNTRUSTED_TYPE", minute(15), "TRUTHY_STRING_NOT_BOOLEAN",
    )
    # Legacy Evidence.verified lacks strict bool type check. DO NOT use it as truth.
    untyped_verified_gap = type(permissive.verified) is not bool and bool(permissive.verified)
    if not (reverse_time_guard and direct_assignment_rewind_gap and untyped_verified_gap):
        raise AssertionError("DOCUMENTED_LEGACY_PERMISSIVE_ABI_GAP_CHANGED")
    try:
        SignalDecision("NONEXISTENT", Strategy.SHORT, DecisionStatus.UNVERIFIED)
    except ValueError:
        zone_identity_guard = True
    else:
        raise AssertionError("INHERITED_ZONE_IDENTITY_GUARD_CHANGED")

    # The 5-min cache planner remains read-only and never certifies a source.
    cursor = SourceCursor(
        last_closed_start_utc=minute(0),
        last_checked_utc=minute(25),
        last_full_reconciled_utc=minute(22),
    )
    def plan(at: int, cap: SourceCapability):
        return plan_refresh(
            now_utc=minute(at), session_start_utc=minute(0),
            latest_expected_closed_start_utc=minute(0),
            bar_duration=timedelta(minutes=15), capability=cap,
            cursor=cursor,
        )
    refresh = {
        "before_cadence": plan(28, SourceCapability.WINDOWED),
        "at_cadence": plan(30, SourceCapability.WINDOWED),
        "correction_reconcile": plan(55, SourceCapability.WINDOWED),
        "unknown_capability": plan(30, SourceCapability.UNKNOWN),
    }
    expect_actions = {
        "before_cadence": RefreshAction.REUSE_CLOSED,
        "at_cadence": RefreshAction.REQUEST_WINDOW,
        "correction_reconcile": RefreshAction.REQUEST_FULL_SESSION,
        "unknown_capability": RefreshAction.BLOCKED,
    }
    if any(refresh[k].action is not expect_actions[k]
           or refresh[k].data_authorized or refresh[k].certified_source_freshness
           for k in refresh):
        raise AssertionError("V1_LOCAL_CACHE_PLAN_FALSELY_CERTIFIED_SOURCE")
    # Caller-claimed immutability only changes a request hint, not root trust.
    finality_claim = plan_refresh(
        now_utc=minute(40), session_start_utc=minute(0),
        latest_expected_closed_start_utc=minute(0),
        bar_duration=timedelta(minutes=15),
        capability=SourceCapability.WINDOWED,
        cursor=cursor, session_ended_verified=True,
        immutable_source_head_verified=True,
    )
    if (finality_claim.action is not RefreshAction.REUSE_CLOSED
            or finality_claim.data_authorized or finality_claim.certified_source_freshness):
        raise AssertionError("SYNTHETIC_FINALITY_HINT_PROMOTED_TO_AUTHORITY")

    if cache["scenario_step_count"] != 10 or cache["final_closed_bars"] != 37:
        raise AssertionError("V1_SQLITE_ORACLE_REPLAY_DRIFT")
    cache_steps = {s["name"]: s for s in cache["scenario_steps"]}
    if (cache_steps["REOPEN_WARM_REUSE"]["indicator_bars_recomputed"] != 0
            or cache_steps["OLD_CORRECTION_R5_REPLAY_TAIL"]["indicator_bars_recomputed"] != 32
            or cache_steps["INCOMPLETE_PAGE_NO_DELETE"]["deleted"] != 0
            or cache_steps["REJECT_AND_ROLLBACK_ALL_TABLES"]["indicator_bars_recomputed"] != 0):
        raise AssertionError("V1_INCREMENTAL_COLD_WARM_CORRECTION_OR_ROLLBACK_DRIFT")

    verdict = inspect_fixture_vn_long_exit_bar(
        entry=D("10"), stop=D("9"), target=D("11"),
        low=D("8.5"), high=D("11.5"),
        bar_closed_utc=minute(15), bar_known_utc=minute(25),
        decision_utc=minute(30),
    )
    if verdict is not VNBarVerdict.AMBIGUOUS_BOTH:
        raise AssertionError("BOTH_STOP_TARGET_TOUCHED_MUST_BE_AMBIGUOUS")
    try:
        require_vn_backtest_release()
    except PermissionError:
        vn_release_blocked = True
    else:
        raise AssertionError("FIXTURE_IMPLIED_VN_LIVE_TRADE_RELEASE")

    receipt = {
        "schema": SCHEMA,
        "status": "EIGHT_V1_RUNTIME_BOUNDARIES_EXECUTED_SYNTHETIC_GAPS_EXPLICIT_NO_GO",
        "original_source_main": MAIN_SHA,
        "original_upstream": SOURCE_SHA,
        "actual_modules_exercised": list(EIGHT),
        "actual_module_count": len(EIGHT),
        "six_asof_minutes": list(MOMENTS),
        "six_snapshots_two_strategies_sixteen_zones": 6 * 2 * 16,
        "original_zone_ids": list(ZONE_IDS),
        "snapshots": snapshots,
        "quality_guard_rejections": guard_rejections,
        "legacy_replay_clock_method_prevents_backstep": reverse_time_guard,
        "legacy_replay_clock_public_field_assignment_can_rewind": direct_assignment_rewind_gap,
        "legacy_evidence_verified_accepts_truthy_string": untyped_verified_gap,
        "legacy_zone_identity_guard_denies_unknown_zone": zone_identity_guard,
        "refresh_actions": {name: row.action.value for name,row in refresh.items()},
        "refresh_outputs_all_uncertified": True,
        "synthetic_finality_flag_did_not_certify_source": True,
        "existing_cache_oracle_scenario_steps": cache["scenario_step_count"],
        "existing_cache_oracle_final_bars": cache["final_closed_bars"],
        "existing_cache_independent_ema_atr": True,
        "cache_old_revision_recompute_count": 32,
        "cache_rejected_transaction_atomic": True,
        "ambiguous_both_stop_and_target_exit": verdict.value,
        "vn_synthetic_pnl": candles["vn_synthetic_net_pnl"],
        "vn_release_blocked": vn_release_blocked,
        "external_market_entitlements_verified": False,
        "v1_v2_full_parity_claimed": False,
        "owner_a02_module_dispositions_approved": 0,
        "owner_a03_full_abi_approved": False,
        "external_g01_g08_gates_closed": False,
        "physical_drive_cache_read_or_written": False,
        "production_cache_read_authorized": False,
        "production_cache_write_authorized": False,
        "production_release_authorized": False,
        "trading_authorized": False,
    }
    receipt["deterministic_synthetic_digest"] = _sha(receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    receipt = evaluate_behavior_matrix()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in receipt.items() if k not in ("snapshots","quality_guard_rejections")},
                     sort_keys=True))


if __name__ == "__main__":
    main()
