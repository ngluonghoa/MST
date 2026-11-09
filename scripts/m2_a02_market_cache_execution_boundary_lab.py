"""MST A02 market/revision/cache/VN execution: real inherited-contract boundary matrix.

Executes inherited V1/V1.2 business predicates and candidate V2 *planning
metadata*, without pretending the V2 sidecar implements market-data/backtest
behavior. All fabricated inputs are labeled SYNTHETIC_TEST_ONLY. A green run
proves expected guard distinctions, not provider rights, fills or live trading.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D
from hashlib import sha256
import json
from pathlib import Path

from swing_trading.cache_fetch_planner import (
    RefreshAction, SourceCapability, SourceCursor, plan_refresh,
)
from swing_trading.market_data import (
    BarClosure, CanonicalCandle, InstrumentClass, MarketBarKey,
    ObservationRevision, PriceBasis, ProviderObservationKey, Quality, Timeframe,
)
from swing_trading.replay_batch import replay_frame
from swing_trading.source_quality import (
    CanonicalCandleV12, CoverageState, LifecycleState, ObservationOrigin,
    ObservationRevisionV12, ProviderObservationKeyV12, QualityState,
    SourceEvidence,
)
from swing_trading.v2_cache_partition_plan import (
    CandidateRefreshHint, FixtureHeadV2, FixturePartitionV2,
    plan_fixture_refresh,
)
from swing_trading.vn_backtest_execution_fixture import (
    VNAction, VNBarVerdict, VNSyntheticFill, VNSyntheticRules,
    calculate_fixture_vn_trade, inspect_fixture_vn_long_exit_bar,
    require_vn_backtest_release,
)

T0 = datetime(2026, 11, 6, 2, tzinfo=timezone.utc)


def minute(offset: int) -> datetime:
    return T0 + timedelta(minutes=offset)


def build_candles() -> tuple[CanonicalCandle, CanonicalCandleV12]:
    """Same fabricated bar and first-known time; intentionally distinct contracts."""
    key = MarketBarKey(
        "STOCK:HOSE:FAKE001", "HOSE", InstrumentClass.STOCK,
        Timeframe.M15, "synthetic-session-1", minute(0), PriceBasis.RAW,
        "synthetic-calendar-v1", "synthetic-aggregation-v1",
    )
    base = CanonicalCandle(
        key, ProviderObservationKey("SYNTHETIC", "fixture.bars", "fake-1"),
        ObservationRevision("r1", "a" * 64, minute(15), minute(20)),
        minute(15), D("10"), D("12"), D("9"), D("11"), 0,
        Quality.VERIFIED, BarClosure.CLOSED, 15, 15,
    )
    obs = ProviderObservationKeyV12(
        "SwingTrading1.8", key, "SYNTHETIC",
        ObservationOrigin.NATIVE, "synthetic-stream",
    )
    rev = ObservationRevisionV12(
        obs, "r1", "adjust-1", "ingest-1", minute(15), minute(20),
    )
    evidence = SourceEvidence(
        "synthetic://nonprovider", "synthetic-snapshot", "fake-1",
        True, True, True, True,
    )
    rich = CanonicalCandleV12(
        market_bar_key=key, observation_key=obs, observation_revision=rev,
        bar_end_utc=minute(15),
        open=D("10"), high=D("12"), low=D("9"), close=D("11"),
        volume=0, matched_value=None, observed_minutes=15,
        expected_minutes=15, source_event_ids=("synthetic-r1",),
        raw_digest_sha256="a" * 64, normalized_digest_sha256="b" * 64,
        retrieved_at_utc=minute(20), verified_at_utc=minute(25),
        lifecycle_state=LifecycleState.CLOSED,
        coverage_state=CoverageState.COMPLETE,
        quality_state=QualityState.VERIFIED,
        calendar_cutoff_verified=True, quality_flags=frozenset(),
        provenance=evidence,
    )
    return base, rich


def run_boundary_matrix():
    """Return deterministic, non-authoritative test observations only."""
    legacy, rich = build_candles()
    snapshots = []
    for at in (14, 15, 20, 24, 25, 30):
        now = minute(at)
        frame = replay_frame((rich.market_bar_key,), (rich,), now)
        replay_bar = frame.bars[0]
        rich_ready = rich.confirmation_prerequisites(now)
        legacy_ready = legacy.eligible_for_confirmed_signals(now)
        if rich_ready != replay_bar.source_prerequisites_at(now):
            raise AssertionError("RICH_CANDLE_REPLAY_PREREQUISITE_DRIFT")
        snapshots.append({
            "minute": at,
            "legacy_simple_quality_necessary": legacy_ready,
            "v12_source_prerequisites": rich_ready,
            "v12_revision_visible": replay_bar.resolution.selected is not None,
            "v12_reason": replay_bar.resolution.reason,
            "source_authority_independently_attested": False,
        })
    if [x["legacy_simple_quality_necessary"] for x in snapshots] != [
        False, True, True, True, True, True,
    ]:
        raise AssertionError("LEGACY_CANDLE_QUALITY_BOUNDARY_DRIFT")
    if [x["v12_source_prerequisites"] for x in snapshots] != [
        False, False, False, False, True, True,
    ]:
        raise AssertionError("V12_VERIFICATION_KNOWN_TIME_BOUNDARY_DRIFT")
    if [x["v12_revision_visible"] for x in snapshots] != [
        False, True, True, True, True, True,
    ]:
        raise AssertionError("REPLAY_SOURCE_VISIBILITY_BOUNDARY_DRIFT")

    dup = replay_frame(
        (rich.market_bar_key,), (rich, rich, rich), minute(30),
    ).bars[0]
    if (dup.exact_retransmissions_removed != 2
            or dup.resolution.selected != rich
            or not dup.source_prerequisites_at(minute(30))):
        raise AssertionError("EXACT_RETRANSMISSION_DEDUP_DRIFT")
    collided = replace(
        rich, close=D("11.5"), raw_digest_sha256="c" * 64,
    )
    conflict = replay_frame(
        (rich.market_bar_key,), (rich, collided), minute(30),
    ).bars[0]
    if (not conflict.revision_identity_collision
            or conflict.resolution.selected is not None
            or conflict.source_prerequisites_at(minute(30))):
        raise AssertionError("SAME_SOURCE_REVISION_CONFLICT_NOT_BLOCKED")
    correction_revision = replace(
        rich.observation_revision,
        source_revision_or_payload_digest="r2",
        first_known_time_utc=minute(40), retrieved_at_utc=minute(41),
    )
    corrected = replace(
        rich, observation_revision=correction_revision,
        close=D("11.5"), retrieved_at_utc=minute(41),
        verified_at_utc=minute(42),
    )
    early = replay_frame(
        (rich.market_bar_key,), (rich, corrected), minute(30),
    ).bars[0]
    late = replay_frame(
        (rich.market_bar_key,), (rich, corrected), minute(50),
    ).bars[0]
    if (early.resolution.selected != rich
            or late.resolution.reason != "SOURCE_OR_REVISION_CONFLICT"
            or late.resolution.selected is not None):
        raise AssertionError("FUTURE_CORRECTION_REPLAY_PARITY_DRIFT")

    cursor = SourceCursor(
        last_closed_start_utc=minute(0),
        last_checked_utc=minute(25),
        last_full_reconciled_utc=minute(22),
    )
    def old_plan(at: int):
        return plan_refresh(
            now_utc=minute(at), session_start_utc=minute(0),
            latest_expected_closed_start_utc=minute(0),
            bar_duration=timedelta(minutes=15),
            capability=SourceCapability.WINDOWED, cursor=cursor,
        )
    legacy_recent = old_plan(28)
    legacy_due = old_plan(30)
    legacy_correction_due = old_plan(55)
    if (legacy_recent.action is not RefreshAction.REUSE_CLOSED
            or legacy_due.action is not RefreshAction.REQUEST_WINDOW
            or legacy_correction_due.action is not RefreshAction.REQUEST_FULL_SESSION):
        raise AssertionError("V1_CACHE_REFRESH_POLICY_DRIFT")
    partition = FixturePartitionV2(
        "SSI", "fixture.ssi.d1", "FAKE001", "M15",
        date(2026, 11, 6), "RAW", "SYNTHETIC.R1",
    )
    untrusted_head = FixtureHeadV2(
        partition.digest, 1, "a" * 64, minute(25),
    )
    v2_recent = plan_fixture_refresh(
        partition, untrusted_head, checked_at_utc=minute(28),
    )
    v2_due = plan_fixture_refresh(
        partition, untrusted_head, checked_at_utc=minute(30),
    )
    if (v2_recent.hint is not CandidateRefreshHint.RECENT_METADATA
            or v2_due.hint is not CandidateRefreshHint.NEEDS_PROVIDER_REVALIDATION
            or legacy_recent.certified_source_freshness
            or legacy_due.data_authorized
            or v2_due.can_fetch_market_data
            or v2_due.source_freshness_verified
            or v2_due.can_write_drive):
        raise AssertionError("CACHE_HINT_MISTAKEN_FOR_SOURCE_AUTHORITY")

    rules = VNSyntheticRules(
        "HOSE", 100, D("0.1"), D("8"), D("20"),
        D("0.001"), D("0.001"), D("0.001"),
    )
    entry = VNSyntheticFill(
        "FAKE001", "HOSE", VNAction.BUY, 100, D("10"),
        minute(0), minute(1), 1,
    )
    exit_fill = VNSyntheticFill(
        "FAKE001", "HOSE", VNAction.EXIT_LONG_SELL, 100, D("12"),
        minute(60), minute(61), 4,
    )
    metric = calculate_fixture_vn_trade(
        entry, exit_fill, rules,
        exit_allowed_from_session=3, as_of_utc=minute(70),
    )
    if (metric.gross_pnl != D("200")
            or metric.net_pnl != D("196.6")
            or metric.live_action_eligible
            or metric.externally_verified_fill):
        raise AssertionError("SYNTHETIC_VN_ECONOMIC_REFERENCE_DRIFT")
    verdict = inspect_fixture_vn_long_exit_bar(
        entry=D("10"), stop=D("9"), target=D("11"),
        low=D("8.5"), high=D("11.5"),
        bar_closed_utc=minute(15), bar_known_utc=minute(25),
        decision_utc=minute(30),
    )
    if verdict is not VNBarVerdict.AMBIGUOUS_BOTH:
        raise AssertionError("AMBIGUOUS_STOP_AND_TP_MUST_NOT_INFER_FILL")
    try:
        require_vn_backtest_release()
    except PermissionError:
        pass
    else:
        raise AssertionError("SYNTHETIC_BACKTEST_RELEASE_SELF_AUTHORIZED")

    result = {
        "schema": "mst.m2.a02.market-cache-vn-fixture-boundary.v1",
        "status": "ACTUAL_INHERITED_MARKET_CACHE_AND_VN_GUARDS_VERIFIED_WITH_EXPLICIT_V2_SCOPE_GAP",
        "candle_snapshots": snapshots,
        "first_known_revision_boundaries_checked": len(snapshots),
        "simple_v1_and_v12_prerequisites_not_interchangeable": True,
        "exact_retransmissions_removed": dup.exact_retransmissions_removed,
        "different_payload_same_revision_identity_conflict_blocked": True,
        "late_correction_did_not_rewrite_prior_as_of_frame": True,
        "v1_refresh_hints": [
            legacy_recent.action.value, legacy_due.action.value,
            legacy_correction_due.action.value,
        ],
        "v2_refresh_hints": [v2_recent.hint.value, v2_due.hint.value],
        "v1_and_v2_cache_contracts_are_not_equivalent": True,
        "vn_synthetic_net_pnl": str(metric.net_pnl),
        "vn_both_stop_and_target_touched": verdict.value,
        "vn_external_session_release_index_required": True,
        "v2_market_data_replay_and_vn_backtest_parity_implemented": False,
        "vendor_source_evidence_independently_authenticated": False,
        "drive_bytes_read_or_written": False,
        "real_broker_fill_verified": False,
        "calendar_and_t_plus_two_certified": False,
        "a02_63_owner_dispositions_approved": False,
        "a03_v2_abi_full_acceptance_approved": False,
        "production_cache_authorized": False,
        "trading_authorized": False,
    }
    payload = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    )
    result["synthetic_observation_sha256"] = sha256(payload.encode("ascii")).hexdigest()
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    receipt = run_boundary_matrix()
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
