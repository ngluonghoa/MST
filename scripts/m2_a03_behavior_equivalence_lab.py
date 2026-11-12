"""MST A02/A03 synthetic V1↔opt-in V2 behavioral differential.

Run the real inherited V1 contracts side-by-side with current V2 sidecars on
identical typed causal events. This proves only the safe UNVERIFIED subset,
not full strategies/indicator formulas, vendor rights, source provenance,
V2 ABI interchangeability, release approval or trade eligibility.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path

from swing_trading.backtest import BacktestHarness
from swing_trading.causal import CausalMarketEvent
from swing_trading.contracts import DecisionStatus, SignalDecision, Strategy, ZONE_IDS
from swing_trading.engine import evaluate_unimplemented_zones
from swing_trading.engineering_contracts import PortDescriptor
from swing_trading.replay import ReplayClock
from swing_trading.strict_contract_v2 import (
    StrictReplayClockV2, StrictSignalDecisionV2,
    decode_untrusted_v2_json, encode_unverified_v2_json,
    legacy_to_v2_unverified, v2_to_legacy_unverified,
)
from swing_trading.v2_replay_port import (
    StrictReplayHarnessV2, V2_MARKET_PORT, V2_RULES_PORT,
)

T0 = datetime(2026, 11, 9, 0, 0, tzinfo=timezone.utc)
CLOCK_TIMES = tuple(T0 + timedelta(minutes=5 * i) for i in range(4))
V1_MARKET_PORT = PortDescriptor(
    "replay.causal_events", "1.0.0", "SYNTHETIC_TEST_ONLY",
    ("available_events",),
)
V1_RULES_PORT = PortDescriptor(
    "rules.zone_registry", "1.0.0", "SYNTHETIC_TEST_ONLY",
    ("evaluate",),
)


def fixture_events() -> tuple[CausalMarketEvent, ...]:
    """Out-of-order source listing, later revisions and first-known cutoffs."""
    items = (
        ("correction", "r2", 0, 3),
        ("early", "r1", 0, 0),
        ("late", "r1", 1, 2),
        ("revised", "r2", 0, 2),
        ("mid", "r1", 1, 1),
        ("future", "r1", 3, 3),
    )
    return tuple(
        CausalMarketEvent(
            event_id=name,
            revision_id=revision,
            event_time_utc=CLOCK_TIMES[event_idx],
            first_known_time_utc=CLOCK_TIMES[known_idx],
            payload={"SYNTHETIC_TEST_ONLY": True},
        )
        for name, revision, event_idx, known_idx in items
    )


class _FixtureEvents:
    def __init__(self, events: tuple[CausalMarketEvent, ...]):
        self.events = events
        self.calls = 0

    def available_events(self, as_of_utc: datetime):
        self.calls += 1
        return self.events


class _V1Rules:
    def __init__(self):
        self.calls = 0

    def evaluate(self, zone_id, strategy, as_of_utc):
        self.calls += 1
        return SignalDecision(zone_id, strategy, DecisionStatus.UNVERIFIED)


class _V2Rules:
    def __init__(self):
        self.calls = 0

    def evaluate(self, zone_id, strategy, as_of_utc):
        self.calls += 1
        return StrictSignalDecisionV2(zone_id, strategy, DecisionStatus.UNVERIFIED)


def _canonical(records) -> str:
    return json.dumps(
        records, ensure_ascii=True, allow_nan=False, sort_keys=True,
        separators=(",", ":"),
    )


def run_behavior_matrix(*, v1_source=None, v2_source=None, v2_rules=None):
    """Check 128 V1/V2 decisions and 4 time/revision visibility snapshots."""
    clock_v1, clock_v2 = ReplayClock(CLOCK_TIMES[0]), StrictReplayClockV2(CLOCK_TIMES[0])
    events = fixture_events()
    v1_source = _FixtureEvents(events) if v1_source is None else v1_source
    v2_source = _FixtureEvents(events) if v2_source is None else v2_source
    v1_rules = _V1Rules()
    v2_rules = _V2Rules() if v2_rules is None else v2_rules

    legacy = BacktestHarness.from_contracts(
        clock=clock_v1, market_data=v1_source, market_port=V1_MARKET_PORT,
        rules=v1_rules, rules_port=V1_RULES_PORT,
    )
    nextgen = StrictReplayHarnessV2.from_contracts(
        clock=clock_v2, market_data=v2_source, market_port=V2_MARKET_PORT,
        rules=v2_rules, rules_port=V2_RULES_PORT,
    )
    observations = []
    signal_records = []
    for at in CLOCK_TIMES:
        clock_v1.advance_to(at)
        clock_v2.advance_to(at)
        old_events, new_events = legacy.visible_events(), nextgen.visible_events()
        old_ids = [(e.event_id, e.revision_id) for e in old_events]
        new_ids = [(e.event_id, e.revision_id) for e in new_events]
        if old_ids != new_ids or old_events != new_events:
            raise AssertionError("CAUSAL_V1_V2_EVENT_VISIBILITY_PARITY_DRIFT")
        if any(e.first_known_time_utc > at or e.event_time_utc > at for e in new_events):
            raise AssertionError("FUTURE_OBSERVATION_LEAKED")
        observations.append({
            "at": at.isoformat(),
            "visible_revisions": [[a, b] for a, b in old_ids],
        })
        for strategy in Strategy:
            v1_decisions = evaluate_unimplemented_zones(strategy, at)
            if len(v1_decisions) != 16 or tuple(x.zone_id for x in v1_decisions) != ZONE_IDS:
                raise AssertionError("LEGACY_ZONE_SET_OR_ORDER_DRIFT")
            for original in v1_decisions:
                observed = nextgen.evaluate_unverified(original.zone_id, strategy)
                strict = legacy_to_v2_unverified(original)
                reversed_original = v2_to_legacy_unverified(observed)
                wire = encode_unverified_v2_json(observed)
                decoded = decode_untrusted_v2_json(wire)
                if (observed != strict or decoded != strict
                        or reversed_original != original
                        or original.status is not DecisionStatus.UNVERIFIED
                        or original.evidence != ()
                        or observed.evidence != ()):
                    raise AssertionError("UNVERIFIED_V1_V2_DECISION_PARITY_DRIFT")
                signal_records.append({
                    "zone_id": original.zone_id,
                    "strategy": strategy.value,
                    "status": observed.status.value,
                    "evidence_count": len(observed.evidence),
                    "at": at.isoformat(),
                })

    expected_total = len(CLOCK_TIMES) * len(ZONE_IDS) * len(tuple(Strategy))
    if len(signal_records) != expected_total or len(observations) != 4:
        raise AssertionError("BEHAVIOR_MATRIX_COVERAGE_DRIFT")
    if any(x["status"] != "UNVERIFIED" for x in signal_records):
        raise AssertionError("SYNTHETIC_REPLAY_CANNOT_PROMOTE_SIGNAL")

    receipt = {
        "schema": "mst.m2.a03.v1-v2-unverified-behavior-differential.v1",
        "status": "V1_V2_SAFE_UNVERIFIED_FIXTURE_SUBSET_MATCHES",
        "as_of_snapshots_checked": len(observations),
        "zones_checked": len(ZONE_IDS),
        "strategies_checked": len(tuple(Strategy)),
        "decision_comparisons": len(signal_records),
        "causal_event_revisions": len(events),
        "observations": observations,
        "v1_engine_and_v2_unverified_decision_wire_roundtrip_equal": True,
        "v1_v2_known_event_visibility_equal": True,
        "signal_decisions_all_unverified": True,
        "legacy_v1_class_and_constructor_abi_replaced": False,
        "v2_guard_behavior_intentionally_stricter_than_v1": True,
        "full_v2_detector_formula_parity_verified": False,
        "full_v2_abi_interchangeability_approved": False,
        "source_vendor_entitlement_verified": False,
        "real_provider_ohlcv_or_drive_cache_used": False,
        "a02_63_owner_dispositions_approved": False,
        "production_cache_authorized": False,
        "trading_authorized": False,
    }
    # Digest covers the actual pairwise observations, not only a pass/fail flag;
    # it is a test fingerprint, never an independent signed provenance receipt.
    receipt["fixture_matrix_sha256"] = sha256(
        _canonical({"events": observations, "decisions": signal_records}).encode("utf-8")
    ).hexdigest()
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    result = run_behavior_matrix()
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8")
    print(_canonical(result))


if __name__ == "__main__":
    main()
