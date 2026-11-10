"""A03 explicit fixture adapter candidates + original V1/V2 correction replay.

Synthetic engineering research ONLY. Existing 63 V1 source paths, eight V2
sidecars, provider rights, physical Drive cache and runtime production flags
remain untouched. Adapter proposals are NOT owner-approved releases.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from itertools import islice
import json
from pathlib import Path

from swing_trading.backtest import BacktestHarness
from swing_trading.causal import CausalMarketEvent
from swing_trading.contracts import DecisionStatus, SignalDecision, Strategy
from swing_trading.engine import evaluate_unimplemented_zones
from swing_trading.replay import ReplayClock
from swing_trading.strict_contract_v2 import StrictReplayClockV2, StrictSignalDecisionV2
from swing_trading.v2_replay_port import (
    StrictReplayHarnessV2, V2_MARKET_PORT, V2_RULES_PORT,
)
from scripts.m2_a03_behavior_equivalence_lab import V1_MARKET_PORT, V1_RULES_PORT

SCHEMA = "mst.a03.adapter-correction-replay-owner-unapproved.v1"
T0 = datetime(2026, 11, 9, 8, 0, tzinfo=timezone.utc)
TIMES = tuple(T0 + timedelta(minutes=5 * i) for i in range(4))


def denied(exc, operation) -> bool:
    try:
        operation()
    except exc:
        return True
    return False


class _SubclassEvent(CausalMarketEvent):
    """Demonstrates observable legacy subclass acceptance only."""


class GeneratorFixtureSource:
    """Returns a NEW one-pass iterator for each fixture-only invocation."""

    def __init__(self, events: tuple[CausalMarketEvent, ...]):
        self.events = events
        self.calls = 0

    def available_events(self, as_of_utc):
        self.calls += 1
        return iter(self.events)


class BoundedTupleFixtureAdapter:
    """Proposed explicit consumer-port adapter; never auto-activated.

    Materialize an iterable once, cap its size and optionally deny subclasses.
    No payload normalization, provenance assertion, network or persistence.
    """

    def __init__(self, source, *, max_events: int = 12,
                 exact_base_type: bool = False):
        if type(max_events) is not int or not 1 <= max_events <= 100:
            raise ValueError("Synthetic fixture limit must be int 1..100")
        if type(exact_base_type) is not bool:
            raise TypeError("Explicit boolean event type policy required")
        if not callable(getattr(source, "available_events", None)):
            raise TypeError("Explicit source.available_events required")
        self.source = source
        self.max_events = max_events
        self.exact_base_type = exact_base_type
        self.calls = 0

    def available_events(self, as_of_utc):
        self.calls += 1
        sequence = tuple(islice(
            iter(self.source.available_events(as_of_utc)), self.max_events + 1,
        ))
        if len(sequence) > self.max_events:
            raise ValueError("FIXTURE_CAPACITY_EXCEEDED_FAIL_CLOSED")
        if any(type(x) is not CausalMarketEvent if self.exact_base_type
               else not isinstance(x, CausalMarketEvent) for x in sequence):
            raise TypeError("FIXTURE_EVENT_TYPE_POLICY_DENIED")
        return sequence


class _RulesV1:
    def evaluate(self, zone_id, strategy, as_of_utc):
        return SignalDecision(zone_id, strategy, DecisionStatus.UNVERIFIED)


class _RulesV2:
    def evaluate(self, zone_id, strategy, as_of_utc):
        return StrictSignalDecisionV2(zone_id, strategy, DecisionStatus.UNVERIFIED)


def v1_harness(at, source):
    return BacktestHarness.from_contracts(
        clock=ReplayClock(at), market_data=source, market_port=V1_MARKET_PORT,
        rules=_RulesV1(), rules_port=V1_RULES_PORT,
    )


def v2_harness(at, source):
    return StrictReplayHarnessV2.from_contracts(
        clock=StrictReplayClockV2(at), market_data=source,
        market_port=V2_MARKET_PORT, rules=_RulesV2(),
        rules_port=V2_RULES_PORT,
    )


def correction_events() -> tuple[CausalMarketEvent, ...]:
    """Three revisions of the SAME synthetic event, arriving as-of 0/10/15m.

    Returned out of order intentionally; no provider authority or resolution.
    """
    return (
        CausalMarketEvent("BAR-1", "r3", T0, TIMES[3], {"value": 120}),
        CausalMarketEvent("BAR-1", "r1", T0, TIMES[0], {"value": 100}),
        CausalMarketEvent("BAR-1", "r2", T0, TIMES[2], {"value": 110}),
        CausalMarketEvent("FUTURE", "r1", T0+timedelta(minutes=20),
                          T0+timedelta(minutes=20), {"value": 1}),
    )


def _ids(events) -> tuple[tuple[str, str], ...]:
    return tuple((e.event_id, e.revision_id) for e in events)


DECISIONS = (
    {
        "id": "A03-OWNER-ITERATOR-01",
        "choice": "BOUNDED_TUPLE_SNAPSHOT_AT_EXPLICIT_PORT",
        "alternative": "REJECT_ONE_PASS_ITERATOR",
        "legacy_behavior_change": "V1 iterator becomes re-readable as a tuple",
        "owner_signed": False,
    },
    {
        "id": "A03-OWNER-SUBCLASS-02",
        "choice": "STRICT_REJECT_NON_EXACT_EVENT_AT_OPT_IN_BOUNDARY",
        "alternative": "REVIEW_VERSIONED_SUBCLASS_MIGRATION_SEPARATELY",
        "legacy_behavior_change": "V1 subclass rejected when explicit strict policy selected",
        "owner_signed": False,
    },
    {
        "id": "A03-OWNER-REVISIONS-03",
        "choice": "RETAIN_RAW_AS_OF_REVISIONS_NO_UNAPPROVED_RESOLUTION",
        "alternative": "SOURCE_ATTESTED_VERSIONED_SUPERSESSION_POLICY",
        "legacy_behavior_change": "None; observed raw revisions remain visible",
        "owner_signed": False,
    },
    {
        "id": "A03-OWNER-ROLLBACK-04",
        "choice": "REPLAY_FROM_FRESH_HISTORICAL_AS_OF_CUTOFF",
        "alternative": "SIGNED_N_NMINUS1_RECOVERY_NOT_IMPLEMENTED",
        "legacy_behavior_change": "None in this fixture",
        "owner_signed": False,
    },
    {
        "id": "A03-OWNER-CLOCK-05",
        "choice": "KEEP_V1_DIRECT_REWIND_COMPAT_UNTIL_OPT_IN_ACCEPTANCE",
        "alternative": "V2_STRICT_MONOTONIC_CLOCK",
        "legacy_behavior_change": "Unapproved",
        "owner_signed": False,
    },
    {
        "id": "A03-OWNER-EVIDENCE-06",
        "choice": "DENY_LEGACY_TRUTHY_NONBOOLEAN_PROOF_PROMOTION",
        "alternative": "OWNER_REVIEW_LEGAL_SOURCE_EVIDENCE_MIGRATION",
        "legacy_behavior_change": "Unapproved",
        "owner_signed": False,
    },
)


def build() -> dict:
    cases = []

    def check(name: str, condition: bool, area: str):
        if not condition:
            raise AssertionError("A03_REPLAY_ADAPTER_GUARD_FAILED:" + name)
        cases.append({"case": name, "area": area, "status": "PASS_FIXTURE_ONLY"})

    one = CausalMarketEvent("TEST", "r1", T0, T0, {"fixture": True})
    raw_old = GeneratorFixtureSource((one,))
    raw_new = GeneratorFixtureSource((one,))
    check("RAW_GENERATOR_V1_EXHAUSTION_REPRODUCED",
          v1_harness(T0,raw_old).visible_events() == (), "iterator")
    check("RAW_GENERATOR_V2_MATERIALIZATION_REPRODUCED",
          v2_harness(T0,raw_new).visible_events() == (one,), "iterator")
    old_src, new_src = GeneratorFixtureSource((one,)), GeneratorFixtureSource((one,))
    old_adapter = BoundedTupleFixtureAdapter(old_src)
    new_adapter = BoundedTupleFixtureAdapter(new_src)
    check("EXPLICIT_BOUNDED_TUPLE_RESTORES_V1_VISIBILITY",
          v1_harness(T0,old_adapter).visible_events() == (one,), "iterator")
    check("EXPLICIT_BOUNDED_TUPLE_PRESERVES_V2_VISIBILITY",
          v2_harness(T0,new_adapter).visible_events() == (one,), "iterator")
    check("SOURCE_CALLED_ONCE_BY_EACH_EXPLICIT_ADAPTER",
          old_adapter.calls == new_adapter.calls == 1
          and old_src.calls == new_src.calls == 1, "iterator")
    check("ADAPTER_PRESERVES_EXACT_OBJECT_AND_PAYLOAD",
          old_adapter.available_events(T0)[0] is one, "iterator")
    check("OVERSIZED_GENERATOR_FAILS_CLOSED",
          denied(ValueError, lambda: BoundedTupleFixtureAdapter(
              GeneratorFixtureSource((one,one)), max_events=1
          ).available_events(T0)), "iterator")
    check("INVALID_MAX_BOOL_NOT_ALLOWED",
          denied(ValueError,lambda:BoundedTupleFixtureAdapter(
              GeneratorFixtureSource((one,)),max_events=True)), "iterator")
    check("INVALID_MAX_ZERO_NOT_ALLOWED",
          denied(ValueError,lambda:BoundedTupleFixtureAdapter(
              GeneratorFixtureSource((one,)),max_events=0)), "iterator")
    check("UNSUPPORTED_ITEM_TYPE_DENIED",
          denied(TypeError,lambda:BoundedTupleFixtureAdapter(
              GeneratorFixtureSource((object(),))
          ).available_events(T0)), "iterator")
    check("MISSING_SOURCE_PORT_DENIED",
          denied(TypeError,lambda:BoundedTupleFixtureAdapter(object())), "iterator")

    derived = _SubclassEvent("TEST", "r1", T0, T0, {"tag":"subclass"})
    check("V1_SUBCLASS_RAW_GENERATOR_EXHAUSTION",
          v1_harness(T0,GeneratorFixtureSource((derived,))).visible_events()
          == (), "subclass")
    # Use a materialized tuple to observe original subclass behavior without
    # conflating it with the independent generator-consumption divergence.
    check("V1_SUBCLASS_WITH_TUPLE_ACCEPTED",
          v1_harness(T0,BoundedTupleFixtureAdapter(
              GeneratorFixtureSource((derived,)))
          ).visible_events() == (derived,), "subclass")
    check("V2_SUBCLASS_WITH_TUPLE_DENIED",
          denied(TypeError, lambda:v2_harness(
              T0,BoundedTupleFixtureAdapter(
                  GeneratorFixtureSource((derived,))
              )).visible_events()), "subclass")
    check("EXPLICIT_STRICT_TYPE_PORT_DENIES_SUBCLASS_V1",
          denied(TypeError,lambda:v1_harness(
              T0,BoundedTupleFixtureAdapter(
                  GeneratorFixtureSource((derived,)),exact_base_type=True,
              )).visible_events()), "subclass")
    check("EXPLICIT_STRICT_TYPE_PORT_DENIES_SUBCLASS_V2",
          denied(TypeError,lambda:v2_harness(
              T0,BoundedTupleFixtureAdapter(
                  GeneratorFixtureSource((derived,)),exact_base_type=True,
              )).visible_events()), "subclass")
    check("EXACT_TYPE_POLICY_ACCEPTS_BASE_EVENT",
          v1_harness(T0,BoundedTupleFixtureAdapter(
              GeneratorFixtureSource((one,)),exact_base_type=True,
          )).visible_events() == (one,), "subclass")
    check("NONBOOLEAN_STRICT_FLAG_DENIED",
          denied(TypeError,lambda:BoundedTupleFixtureAdapter(
              GeneratorFixtureSource((one,)),exact_base_type=1)), "subclass")

    events = correction_events()
    expected = (
        (("BAR-1","r1"),),
        (("BAR-1","r1"),),
        (("BAR-1","r1"),("BAR-1","r2")),
        (("BAR-1","r1"),("BAR-1","r2"),("BAR-1","r3")),
    )
    snapshots = []
    for i, at in enumerate(TIMES):
        old = v1_harness(at,BoundedTupleFixtureAdapter(
            GeneratorFixtureSource(events),exact_base_type=True)).visible_events()
        new = v2_harness(at,BoundedTupleFixtureAdapter(
            GeneratorFixtureSource(events),exact_base_type=True)).visible_events()
        record = _ids(old)
        check("CORRECTION_AS_OF_"+str(i)+"_V1_EQUALS_V2",
              old==new and record==expected[i], "correction")
        check("CORRECTION_AS_OF_"+str(i)+"_NO_FUTURE_KNOWLEDGE",
              all(x.event_time_utc<=at and x.first_known_time_utc<=at
                  for x in old), "correction")
        check("CORRECTION_AS_OF_"+str(i)+"_NO_AUTOMATIC_REPLACEMENT",
              len(old)==len(expected[i]), "correction")
        snapshots.append({"as_of":at.isoformat(),"visible_revisions":record})

    check("LATE_REVISION_DOES_NOT_REPAINT_EARLY_SNAPSHOT",
          _ids(v1_harness(TIMES[0],BoundedTupleFixtureAdapter(
              GeneratorFixtureSource(events))).visible_events())
          == expected[0], "correction")
    check("REVISIONS_RAW_HISTORY_NOT_AUTO_SUPERSEDED",
          [x.revision_id for x in v2_harness(
              TIMES[-1],BoundedTupleFixtureAdapter(
                  GeneratorFixtureSource(events))).visible_events()]
          == ["r1","r2","r3"], "correction")
    check("SORTING_IS_BY_FIRST_KNOWN_NOT_SOURCE_LIST_ORDER",
          [e.revision_id for e in events[:3]] == ["r3","r1","r2"]
          and tuple(x[1] for x in snapshots[-1]["visible_revisions"])
          == ("r1","r2","r3"), "correction")
    check("CAUSAL_KNOWN_BEFORE_EVENT_TIME_REJECTED",
          denied(ValueError,lambda:CausalMarketEvent(
              "bad","r1",T0,T0-timedelta(seconds=1),{})), "correction")
    check("NAIVE_FIRST_KNOWN_TIME_REJECTED",
          denied(ValueError,lambda:CausalMarketEvent(
              "bad","r1",T0,datetime(2026,11,9,8,0),{})), "correction")
    statuses = [
        decision.status
        for at in TIMES for strategy in Strategy
        for decision in evaluate_unimplemented_zones(strategy,at)
    ]
    check("ALL_SYNTHETIC_ZONES_REMAIN_UNVERIFIED",
          len(statuses)==4*2*16
          and all(x is DecisionStatus.UNVERIFIED for x in statuses), "signal")
    check("SOURCE_REVISIONS_CANNOT_ASSERT_VERIFIED_TRADE",
          all(not row["owner_signed"] for row in DECISIONS), "signal")
    check("ALL_OWNER_OPTIONS_ARE_PROPOSALS_ONLY",
          len(DECISIONS)==6
          and len({d["id"] for d in DECISIONS})==6
          and all(d["owner_signed"] is False for d in DECISIONS), "governance")

    if len(cases) != 38 or len({x["case"] for x in cases}) != 38:
        raise AssertionError("A03_CASE_COUNT_OR_UNIQUE_NAME_DRIFT")
    digest = sha256(json.dumps(
        {"cases":cases, "snapshots":snapshots, "decisions":DECISIONS},
        sort_keys=True,separators=(",",":"),allow_nan=False,
    ).encode()).hexdigest()
    return {
        "schema": SCHEMA,
        "status": "ADAPTER_PROPOSAL_AND_CAUSAL_REVISION_SYNTHETIC_NO_GO",
        "case_count": len(cases),
        "cases": cases,
        "case_and_snapshot_sha256": digest,
        "as_of_snapshots": snapshots,
        "owner_decision_matrix": list(DECISIONS),
        "real_source_revision_supersession_proven": False,
        "historical_vendor_as_of_authenticity_proven": False,
        "data_rights_or_physical_drive_cache_proven": False,
        "adapter_owner_approved": False,
        "legacy_source_or_preexisting_v2_changed": False,
        "a02_owner_approvals": 0,
        "a03_owner_approvals": 0,
        "all_g01_g08_oa01_oa06_closed": False,
        "production_release_or_trading_authorized": False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path)
    args=p.parse_args(argv)
    report=build()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",
                            encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="cases"},sort_keys=True))


if __name__=="__main__":
    main()
