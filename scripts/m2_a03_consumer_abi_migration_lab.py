"""MST A03 consumer-driven V1/V2 compatibility, downgrade and no-authority lab.

Exercises real unchanged legacy V1 and existing opt-in V2 source on fabricated
fixtures. No source writes, provider calls, licensed market bars, Drive I/O,
owner approval, release or broker/trading operations are authorized.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path

from scripts.m2_a03_behavior_equivalence_lab import (
    V1_MARKET_PORT, V1_RULES_PORT, run_behavior_matrix,
)
from swing_trading.backtest import BacktestHarness
from swing_trading.cache_fetch_planner import (
    RefreshAction, SourceCapability, plan_refresh,
)
from swing_trading.contracts import (
    DecisionStatus, Evidence, SignalDecision, Strategy,
)
from swing_trading.engineering_contracts import PortDescriptor, check_port
from swing_trading.replay import ReplayClock
from swing_trading.strict_contract_v2 import (
    StrictEvidenceV2, StrictReplayClockV2, StrictSignalDecisionV2,
    decode_untrusted_v2_json, encode_unverified_v2_json,
    legacy_to_v2_unverified, v2_to_legacy_unverified,
)
from swing_trading.v2_cache_partition_plan import (
    FixtureHeadV2, FixturePartitionV2, plan_fixture_refresh,
)
from swing_trading.v2_replay_port import (
    StrictReplayHarnessV2, V2_MARKET_PORT, V2_RULES_PORT,
)
from swing_trading.v2_source_adapter import (
    FixtureProbeRequestV2, synthetic_source_registry,
)

SCHEMA = "mst.a03.consumer-driven-v1-v2-unapproved.v1"
AT = datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc)


def rejects(exception_type, callback) -> bool:
    """Check a negative control without hiding other unexpected exceptions."""
    try:
        callback()
    except exception_type:
        return True
    return False


class FixtureMarket:
    def available_events(self, as_of_utc):
        return ()


class FixtureRules:
    def evaluate(self, zone_id, strategy, as_of_utc):
        return SignalDecision(zone_id, strategy, DecisionStatus.UNVERIFIED)


class StrictFixtureRules:
    def evaluate(self, zone_id, strategy, as_of_utc):
        return StrictSignalDecisionV2(zone_id, strategy, DecisionStatus.UNVERIFIED)


def build() -> dict:
    checks = []

    def record(name: str, condition: bool, area: str) -> None:
        if not condition:
            raise AssertionError("A03_CONSUMER_NEGATIVE_GUARD:" + name)
        checks.append({"case": name, "area": area, "result": "PASS_SYNTHETIC_ONLY"})

    old_clock, new_clock = ReplayClock(AT), StrictReplayClockV2(AT)
    old_clock.as_of_utc = AT - timedelta(minutes=1)
    record("LEGACY_PUBLIC_CLOCK_REWIND_PRESERVED",
           old_clock.as_of_utc < AT, "clock")
    record("STRICT_PUBLIC_CLOCK_REWIND_DENIED",
           rejects(ValueError, lambda: setattr(new_clock, "as_of_utc",
                                                AT - timedelta(minutes=1)))
           and new_clock.as_of_utc == AT, "clock")
    record("BOTH_ADVANCE_METHODS_FAIL_REWIND",
           rejects(ValueError, lambda: old_clock.advance_to(AT - timedelta(minutes=2)))
           and rejects(ValueError, lambda: new_clock.advance_to(AT - timedelta(minutes=1))),
           "clock")
    record("FUTURE_KNOWLEDGE_NOT_VISIBLE",
           not new_clock.known(AT + timedelta(seconds=1)), "clock")

    old_evidence = Evidence("synthetic", AT, 1)
    record("LEGACY_TRUTHY_INTEGER_IS_NOT_BOOLEAN",
           type(old_evidence.verified) is int, "evidence")
    record("STRICT_NONBOOLEAN_EVIDENCE_REJECTED",
           rejects(TypeError, lambda: StrictEvidenceV2("synthetic", AT, 1)),
           "evidence")

    safe_v1 = SignalDecision("B1", Strategy.SWING, DecisionStatus.UNVERIFIED)
    safe_v2 = legacy_to_v2_unverified(safe_v1)
    record("EXPLICIT_EMPTY_UNVERIFIED_UPGRADE_DOWNGRADE",
           v2_to_legacy_unverified(safe_v2) == safe_v1, "migration")
    real_looking_v1 = SignalDecision(
        "B1", Strategy.SWING, DecisionStatus.DETECTED,
        (Evidence("synthetic_only", AT, True),),
    )
    record("LEGACY_DETECTED_NOT_AUTOMIGRATED",
           rejects(PermissionError, lambda: legacy_to_v2_unverified(real_looking_v1)),
           "migration")
    synthetic_classified_v2 = StrictSignalDecisionV2(
        "B1", Strategy.SWING, DecisionStatus.DETECTED,
        (StrictEvidenceV2("synthetic_only", AT, True),),
    )
    record("V2_CLASSIFIED_RECORD_NOT_DOWNGRADED",
           rejects(PermissionError, lambda: v2_to_legacy_unverified(synthetic_classified_v2)),
           "migration")
    record("UNTRUSTED_DETECTED_WIRE_DENIED",
           rejects(PermissionError, lambda: decode_untrusted_v2_json(
               '{"schema":"mst.signal_decision.v2","zone_id":"B1","strategy":"SWING",'
               '"status":"DETECTED","evidence":[]}'
           )), "wire")
    record("UNTRUSTED_DUPLICATE_JSON_KEY_DENIED",
           rejects(ValueError, lambda: decode_untrusted_v2_json(
               '{"schema":"mst.signal_decision.v2","schema":"mst.signal_decision.v2",'
               '"zone_id":"B1","strategy":"SWING","status":"UNVERIFIED","evidence":[]}'
           )), "wire")
    record("UNVERIFIED_WIRE_ROUNDTRIP_ONLY",
           decode_untrusted_v2_json(encode_unverified_v2_json(safe_v2)) == safe_v2,
           "wire")

    market, v1_rules, v2_rules = FixtureMarket(), FixtureRules(), StrictFixtureRules()
    record("V1_MARKET_PORT_REJECTS_V2_MAJOR",
           not check_port(V1_MARKET_PORT, V2_MARKET_PORT, market).compatible,
           "consumer_ports")
    record("V2_RULE_PORT_REJECTS_V1_MAJOR",
           not check_port(V2_RULES_PORT, V1_RULES_PORT, v2_rules).compatible,
           "consumer_ports")
    record("V1_BACKTEST_CONSUMER_REJECTS_V2_CLOCK",
           rejects(TypeError, lambda: BacktestHarness.from_contracts(
               clock=StrictReplayClockV2(AT),
               market_data=market, market_port=V1_MARKET_PORT,
               rules=v1_rules, rules_port=V1_RULES_PORT,
           )), "consumer_ports")
    record("V2_REPLAY_CONSUMER_REJECTS_V1_CLOCK",
           rejects(TypeError, lambda: StrictReplayHarnessV2.from_contracts(
               clock=ReplayClock(AT),
               market_data=market, market_port=V2_MARKET_PORT,
               rules=v2_rules, rules_port=V2_RULES_PORT,
           )), "consumer_ports")
    v1_harness = BacktestHarness.from_contracts(
        clock=ReplayClock(AT), market_data=market,
        market_port=V1_MARKET_PORT, rules=v1_rules, rules_port=V1_RULES_PORT,
    )
    v2_harness = StrictReplayHarnessV2.from_contracts(
        clock=StrictReplayClockV2(AT), market_data=market,
        market_port=V2_MARKET_PORT, rules=v2_rules, rules_port=V2_RULES_PORT,
    )
    record("EXPLICIT_SEPARATE_CONSUMERS_RUN_SAFE_EMPTY_FIXTURE",
           v1_harness.visible_events() == v2_harness.visible_events() == ()
           and v2_harness.evaluate_unverified("B1", Strategy.SWING).status
           is DecisionStatus.UNVERIFIED, "consumer_ports")

    registry = synthetic_source_registry()
    probe = registry.probe(
        FixtureProbeRequestV2("SSI", "fixture.ssi.d1", "TEST", "D1", AT),
        PortDescriptor("source.fixture_probe", "2.0.0", "SSI", ("probe",)),
    )
    record("SOURCE_PROBE_SELF_CLAIM_CANNOT_GRANT_RIGHTS",
           probe.state == "UNVERIFIED"
           and probe.source_authorized is False
           and probe.retention_authorized is False
           and probe.trading_authorized is False,
           "source")
    record("CROSS_PROVIDER_CONSUMER_SCOPE_DENIED",
           rejects(ValueError, lambda: registry.probe(
               FixtureProbeRequestV2("SSI", "fixture.ssi.d1", "TEST", "D1", AT),
               PortDescriptor("source.fixture_probe", "2.0.0", "DNSE", ("probe",)),
           )), "source")

    partition = FixturePartitionV2(
        "SSI", "fixture.ssi.d1", "TEST", "M5",
        date(2026, 11, 10), "RAW", "TEST_REVISION",
    )
    other = FixturePartitionV2(
        "DNSE", "fixture.dnse.d1", "TEST", "M5",
        date(2026, 11, 10), "RAW", "TEST_REVISION",
    )
    record("PROVIDER_PARTITION_ISOLATION",
           partition.digest != other.digest, "cache")
    wrong_head = FixtureHeadV2("0" * 64, 1, "1" * 64, AT)
    record("FOREIGN_PARTITION_HEAD_DENIED",
           rejects(ValueError, lambda: plan_fixture_refresh(
               partition, wrong_head, checked_at_utc=AT,
           )), "cache")
    plan = plan_fixture_refresh(partition, None, checked_at_utc=AT)
    record("V2_CACHE_PLAN_NEVER_AUTHORIZES_IO",
           not plan.can_fetch_market_data
           and not plan.can_read_licensed_cache
           and not plan.can_write_drive
           and not plan.source_freshness_verified
           and not plan.permission_to_trade, "cache")
    legacy_plan = plan_refresh(
        now_utc=AT,
        session_start_utc=AT - timedelta(hours=1),
        latest_expected_closed_start_utc=AT - timedelta(minutes=5),
        bar_duration=timedelta(minutes=5),
        capability=SourceCapability.UNKNOWN, cursor=None,
    )
    record("LEGACY_UNVERIFIED_SOURCE_BLOCKS_FETCH",
           legacy_plan.action is RefreshAction.BLOCKED
           and not legacy_plan.data_authorized
           and not legacy_plan.certified_source_freshness, "cache")
    record("CROSS_VERSION_CACHE_OBJECT_NOT_DROPIN",
           rejects(TypeError, lambda: plan_fixture_refresh(
               legacy_plan, None, checked_at_utc=AT,
           )), "cache")

    baseline = run_behavior_matrix()
    record("PRIOR_128_UNVERIFIED_DIFFERENTIAL_RETAINED",
           baseline["decision_comparisons"] == 128
           and baseline["as_of_snapshots_checked"] == 4
           and baseline["v1_v2_known_event_visibility_equal"]
           and baseline["signal_decisions_all_unverified"], "replay")

    if len(checks) != 26 or len({row["case"] for row in checks}) != 26:
        raise AssertionError("A03_CASE_COUNT_OR_UNIQUENESS_DRIFT")
    canonical = json.dumps(checks, sort_keys=True, separators=(",", ":"))
    return {
        "schema": SCHEMA,
        "status": "CONSUMER_DRIVEN_NEGATIVE_AND_SAFE_SUBSET_ONLY_OWNER_NO_GO",
        "cases": checks,
        "case_count": len(checks),
        "case_sha256": sha256(canonical.encode("utf-8")).hexdigest(),
        "original_v1_modified": False,
        "preexisting_eight_v2_modules_modified": False,
        "intentional_noninterchangeable_legacy_contracts": (
            "ReplayClock.as_of_utc_direct_rewind",
            "Evidence.verified_truthy_nonboolean",
        ),
        "approved_adapters": "EMPTY_EVIDENCE_UNVERIFIED_ONLY",
        "owner_a02_signed": 0,
        "owner_a03_signed": 0,
        "full_v1_v2_abi_parity_proven": False,
        "real_vendor_rights_or_live_cache_proven": False,
        "independent_G01_G08_and_OA01_OA06_closed": False,
        "production_or_trading_authorized": False,
        "prior_safe_fixture_sha256": baseline["fixture_matrix_sha256"],
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    report = build()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "cases"},
                     sort_keys=True))


if __name__ == "__main__":
    main()
