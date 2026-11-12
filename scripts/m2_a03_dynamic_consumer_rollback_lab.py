"""MST A03 actual-consumer replay/registry/cache and N/N-1 rollback falsification.

No original V1 or eight opt-in V2 sources change. This is a deterministic
non-authorizing test lab: no live feeds, licensed data, Google Drive I/O,
signer/witness provisioning, broker operations or production deployment.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path

from swing_trading.backtest import BacktestHarness
from swing_trading.causal import CausalMarketEvent
from swing_trading.contracts import (
    DecisionStatus, Evidence, SignalDecision, Strategy,
)
from swing_trading.engineering_contracts import EngineeringPortRegistry, PortDescriptor
from swing_trading.replay import ReplayClock
from swing_trading.strict_contract_v2 import (
    StrictEvidenceV2, StrictReplayClockV2, StrictSignalDecisionV2,
)
from swing_trading.v2_replay_port import (
    StrictReplayHarnessV2, V2_MARKET_PORT, V2_RULES_PORT,
)
from swing_trading.v2_source_adapter import (
    FixtureSourceAdapterV2, FixtureSourceIdentityV2, synthetic_source_registry,
)
from swing_trading.v2_cache_partition_plan import (
    CandidateRefreshHint, FixtureHeadV2, FixturePartitionV2, plan_fixture_refresh,
)
from scripts.m2_a03_behavior_equivalence_lab import (
    V1_MARKET_PORT, V1_RULES_PORT, run_behavior_matrix,
)

SCHEMA = "mst.a03.dynamic-consumer-n-nminus1-falsification.no-authority.v1"
AT = datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc)


def denied(error_type, action) -> bool:
    try:
        action()
    except error_type:
        return True
    return False


class _Market:
    def __init__(self, events=(), *, stream=False):
        self.events = events
        self.stream = stream
        self.calls = 0

    def available_events(self, as_of_utc):
        self.calls += 1
        return iter(self.events) if self.stream else self.events


class _Rules:
    def __init__(self, reply=None):
        self.reply = reply
        self.calls = 0

    def evaluate(self, zone_id, strategy, as_of_utc):
        self.calls += 1
        if self.reply is not None:
            return self.reply
        return StrictSignalDecisionV2(zone_id, strategy, DecisionStatus.UNVERIFIED)


class _Adapter:
    def probe(self):
        return "SYNTHETIC_TEST_ONLY"


class _DerivedEvent(CausalMarketEvent):
    """Legacy V1 accepts subclass; V2 requires exact CausalMarketEvent."""


def _events():
    return (
        CausalMarketEvent("now", "r1", AT-timedelta(minutes=5), AT,
                          {"fixture": "only"}),
        CausalMarketEvent("prior", "r2", AT-timedelta(minutes=10),
                          AT-timedelta(minutes=1), {"fixture": "correction"}),
        CausalMarketEvent("future", "r3", AT-timedelta(minutes=5),
                          AT+timedelta(minutes=5), {"fixture": "later-known"}),
    )


def _v1(market):
    return BacktestHarness.from_contracts(
        clock=ReplayClock(AT), market_data=market, market_port=V1_MARKET_PORT,
        rules=_AdapterRulesV1(), rules_port=V1_RULES_PORT,
    )


class _AdapterRulesV1:
    def evaluate(self, zone_id, strategy, as_of_utc):
        return SignalDecision(zone_id, strategy, DecisionStatus.UNVERIFIED)


def _v2(market, rules=None):
    return StrictReplayHarnessV2.from_contracts(
        clock=StrictReplayClockV2(AT), market_data=market,
        market_port=V2_MARKET_PORT,
        rules=_Rules() if rules is None else rules, rules_port=V2_RULES_PORT,
    )


def _desc(version):
    return PortDescriptor("lab.versioned_probe", version, "SYNTHETIC_TEST_ONLY",
                          ("probe",))


def _ssi(version):
    return FixtureSourceAdapterV2(
        FixtureSourceIdentityV2("SSI", "fixture.ssi.d1", version)
    )


def build() -> dict:
    cases = []

    def check(name, assertion, group):
        if not assertion:
            raise AssertionError("A03_DYNAMIC_CONSUMER_FALSIFICATION:" + name)
        cases.append({"case": name, "group": group, "result": "PASS_FIXTURE_ONLY"})

    events = _events()
    v1_list, v2_list = _Market(events), _Market(events)
    old = _v1(v1_list).visible_events()
    new = _v2(v2_list).visible_events()
    check("LIST_MARKET_SAME_VISIBLE_REVISIONS",
          [(x.event_id,x.revision_id) for x in old] ==
          [(x.event_id,x.revision_id) for x in new] ==
          [("prior","r2"),("now","r1")], "replay")
    check("MARKET_CALLED_ONCE_PER_SEPARATE_CONSUMER",
          v1_list.calls == v2_list.calls == 1, "replay")
    check("FUTURE_KNOWN_EVENT_BOTH_HIDDEN",
          all(x.event_id != "future" for x in old+new), "replay")
    check("SORTED_FIRST_KNOWN_REVISION_ORDER",
          [x.event_id for x in new] == ["prior","now"], "replay")

    streamed_v1 = _Market((events[0],), stream=True)
    streamed_v2 = _Market((events[0],), stream=True)
    old_stream = _v1(streamed_v1).visible_events()
    new_stream = _v2(streamed_v2).visible_events()
    # This difference is a compatibility FINDING, not an approved change:
    # V1 validation consumes a one-pass iterator, V2 snapshots it first.
    check("LEGACY_V1_GENERATOR_CONSUMED_BEFORE_FILTER",
          old_stream == () and streamed_v1.calls == 1, "replay_difference")
    check("STRICT_V2_GENERATOR_MATERIALIZED_BEFORE_FILTER",
          len(new_stream) == 1 and new_stream[0].event_id == "now"
          and streamed_v2.calls == 1, "replay_difference")
    derived = _DerivedEvent("sub", "r1", AT, AT, {"fixture": "subclass"})
    check("LEGACY_V1_SUBCLASS_EVENT_ACCEPTED",
          len(_v1(_Market((derived,))).visible_events()) == 1,
          "replay_difference")
    check("STRICT_V2_SUBCLASS_EVENT_DENIED",
          denied(TypeError, lambda: _v2(_Market((derived,))).visible_events()),
          "replay_difference")
    check("V1_REJECTS_UNTYPED_MARKET_EVENT",
          denied(TypeError, lambda: _v1(_Market((object(),))).visible_events()),
          "replay")
    check("V2_REJECTS_UNTYPED_MARKET_EVENT",
          denied(TypeError, lambda: _v2(_Market((object(),))).visible_events()),
          "replay")

    rules = _Rules()
    decision = _v2(_Market(), rules).evaluate_unverified("B1",Strategy.SWING)
    check("EXACT_UNVERIFIED_RULE_SUCCESS",
          decision.status is DecisionStatus.UNVERIFIED and not decision.evidence,
          "rule")
    check("V2_RULE_EXECUTED_EXACTLY_ONCE",
          rules.calls == 1, "rule")
    for label, record in (
        ("DETECTED", StrictSignalDecisionV2(
            "B1",Strategy.SWING,DecisionStatus.DETECTED,
            (StrictEvidenceV2("synthetic",AT,True),))),
        ("NOT_DETECTED",StrictSignalDecisionV2(
            "B1",Strategy.SWING,DecisionStatus.NOT_DETECTED,
            (StrictEvidenceV2("synthetic",AT,True),))),
    ):
        check("V2_"+label+"_SELF_ATTESTED_RULE_DENIED",
              denied(PermissionError,lambda record=record:
                     _v2(_Market(),_Rules(record)).evaluate_unverified(
                         "B1",Strategy.SWING)), "rule")
    check("V2_RULE_WRONG_ZONE_ID_DENIED",
          denied(ValueError, lambda: _v2(
              _Market(),_Rules(StrictSignalDecisionV2(
                  "B2",Strategy.SWING,DecisionStatus.UNVERIFIED
              ))).evaluate_unverified("B1",Strategy.SWING)), "rule")
    check("V2_RULE_WRONG_STRATEGY_DENIED",
          denied(ValueError, lambda: _v2(
              _Market(),_Rules(StrictSignalDecisionV2(
                  "B1",Strategy.SHORT,DecisionStatus.UNVERIFIED
              ))).evaluate_unverified("B1",Strategy.SWING)), "rule")
    check("V2_RULE_LEGACY_RESULT_TYPE_DENIED",
          denied(TypeError, lambda: _v2(
              _Market(),_Rules(SignalDecision(
                  "B1",Strategy.SWING,DecisionStatus.UNVERIFIED
              ))).evaluate_unverified("B1",Strategy.SWING)), "rule")
    uncalled = _Rules()
    bad_harness = _v2(_Market(),uncalled)
    check("V2_BAD_ZONE_PRE_VALIDATION_NO_CALLBACK",
          denied(ValueError, lambda: bad_harness.evaluate_unverified(
              "B99",Strategy.SWING)) and uncalled.calls == 0, "rule")
    check("V2_BAD_STRATEGY_PRE_VALIDATION_NO_CALLBACK",
          denied(TypeError, lambda: bad_harness.evaluate_unverified(
              "B1","SWING")) and uncalled.calls == 0, "rule")
    check("LEGACY_TRUTHY_EVIDENCE_IS_NOT_SOURCE_AUTHORITY",
          type(Evidence("synthetic",AT,1).verified) is int
          and denied(TypeError,lambda:StrictEvidenceV2("synthetic",AT,1)),
          "rule")

    # In-memory EngineeringPortRegistry. N/N-1 refers to fixture semver, not
    # a real release or durable rollback guarantee.
    port = EngineeringPortRegistry()
    p20,p21 = _desc("2.0.0"),_desc("2.1.0")
    a20,a21 = _Adapter(),_Adapter()
    port.add(p20,a20)
    check("PORT_N_BASELINE_RESOLVES",
          port.resolve(p20) is a20, "registry")
    port.bind_consumer("old.consumer",p20)
    port.replace(p20,p21,a21)
    check("PORT_N_TO_NPLUS1_OLD_CONSUMER_COMPATIBLE",
          port.resolve(p20) is a21, "registry")
    port.replace(p20,p20,a20)
    check("PORT_NPLUS1_TO_N_ROLLBACK_WITH_OLD_PIN",
          port.resolve(p20) is a20, "registry")
    port.replace(p20,p21,a21)
    port.bind_consumer("new.consumer",p21)
    check("PORT_NEW_PIN_BLOCKS_N_MINUS_ONE_DOWNGRADE",
          denied(ValueError,lambda:port.replace(p20,p20,a20))
          and port.resolve(p21) is a21, "registry")
    check("PORT_NO_PARTIAL_MUTATION_AFTER_REJECTED_DOWNGRADE",
          port.resolve(p20) is a21, "registry")
    port.detach_consumer("new.consumer")
    port.replace(p20,p20,a20)
    check("PORT_ROLLBACK_AFTER_EXPLICIT_UNPIN",
          port.resolve(p20) is a20, "registry")
    check("PORT_PINNED_REMOVE_DENIED",
          denied(ValueError,lambda:port.remove(p20)), "registry")
    port.detach_consumer("old.consumer")
    port.remove(p20)
    check("PORT_REMOVE_ONLY_AFTER_ALL_DETACHED",
          port.count == 0, "registry")

    source = synthetic_source_registry()
    s20 = PortDescriptor("source.fixture_probe","2.0.0","SSI",("probe",))
    s21 = PortDescriptor("source.fixture_probe","2.1.0","SSI",("probe",))
    source.bind_consumer("old.source.consumer","SSI",s20)
    source.replace("SSI",_ssi("2.1.0"))
    check("SOURCE_N_TO_NPLUS1_WITH_OLD_PIN",
          source.resolve("SSI",s20).identity.version == "2.1.0", "source")
    source.bind_consumer("new.source.consumer","SSI",s21)
    check("SOURCE_PINNED_NPLUS1_BLOCKS_ROLLBACK",
          denied(ValueError,lambda:source.replace("SSI",_ssi("2.0.0")))
          and source.resolve("SSI",s21).identity.version == "2.1.0",
          "source")
    check("SOURCE_REFUSES_CROSS_PROVIDER_HOTSWAP",
          denied(ValueError,lambda:source.replace(
              "SSI",FixtureSourceAdapterV2(
                  FixtureSourceIdentityV2("DNSE","fixture.dnse.d1")
              ))), "source")
    check("SOURCE_PINNED_REMOVE_DENIED",
          denied(ValueError,lambda:source.remove("SSI")), "source")
    source.detach_consumer("new.source.consumer")
    source.replace("SSI",_ssi("2.0.0"))
    check("SOURCE_ROLLBACK_AFTER_NEW_CONSUMER_DETACH",
          source.resolve("SSI",s20).identity.version == "2.0.0",
          "source")
    source.detach_consumer("old.source.consumer")
    source.remove("SSI")
    check("SOURCE_REMOVE_AFTER_ALL_PINS_DETACHED",
          "SSI" not in source.providers, "source")
    check("SOURCE_OTHER_PROVIDERS_UNTOUCHED",
          set(source.providers) == {"DNSE","VCBS"}, "source")

    part = FixturePartitionV2("SSI","fixture.ssi.d1","TEST","M5",
                               date(2026,11,10),"RAW","REV_A")
    basis = FixturePartitionV2("SSI","fixture.ssi.d1","TEST","M5",
                                date(2026,11,10),"ADJUSTED","REV_A")
    revised = FixturePartitionV2("SSI","fixture.ssi.d1","TEST","M5",
                                  date(2026,11,10),"RAW","REV_B")
    check("CACHE_PRICE_BASIS_NOT_INTERCHANGEABLE",
          part.digest != basis.digest, "cache")
    check("CACHE_REVISION_NAMESPACE_NOT_INTERCHANGEABLE",
          part.digest != revised.digest, "cache")
    ahead = FixtureHeadV2(part.digest,1,"f"*64,AT+timedelta(minutes=1))
    check("CACHE_FUTURE_HEAD_REJECTED",
          denied(ValueError,lambda:plan_fixture_refresh(
              part,ahead,checked_at_utc=AT)), "cache")
    head = FixtureHeadV2(part.digest,1,"f"*64,AT)
    recent = plan_fixture_refresh(part,head,checked_at_utc=AT+timedelta(minutes=4))
    stale = plan_fixture_refresh(part,head,checked_at_utc=AT+timedelta(minutes=6))
    check("CACHE_RECENT_METADATA_ONLY_NOT_SOURCE_FRESHNESS",
          recent.hint is CandidateRefreshHint.RECENT_METADATA
          and recent.source_freshness_verified is False, "cache")
    check("CACHE_STALE_METADATA_REQUIRES_REVALIDATION",
          stale.hint is CandidateRefreshHint.NEEDS_PROVIDER_REVALIDATION,
          "cache")
    check("CACHE_V2_PLANNER_NEVER_GRANTS_IO_OR_TRADING",
          all(not getattr(plan,name) for plan in (recent,stale)
              for name in ("can_fetch_market_data","can_read_licensed_cache",
                           "can_write_drive","source_freshness_verified",
                           "permission_to_trade")), "cache")

    baseline = run_behavior_matrix()
    check("PRIOR_128_UNVERIFIED_ONLY_DECISIONS_UNCHANGED",
          baseline["decision_comparisons"] == 128
          and baseline["signal_decisions_all_unverified"]
          and baseline["v1_v2_known_event_visibility_equal"],
          "reference")

    if len(cases) < 35 or len({row["case"] for row in cases}) != len(cases):
        raise AssertionError("A03_INSUFFICIENT_OR_DUPLICATE_DYNAMIC_CASES")
    canon = json.dumps(cases,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    return {
        "schema": SCHEMA,
        "result": "SCOPED_REAL_CODE_DYNAMIC_CONSUMER_NEGATIVE_QA_ONLY",
        "case_count": len(cases),
        "case_sha256": sha256(canon.encode("utf-8")).hexdigest(),
        "cases": cases,
        "new_compatibility_findings": [
            {
                "finding":"V1_ONE_PASS_EVENT_ITERATOR_CONSUMED",
                "v1_scope":"BacktestHarness.visible_events",
                "v2_scope":"StrictReplayHarnessV2.visible_events",
                "substitutability":"NOT_INTERCHANGEABLE_WITH_GENERATOR",
                "owner_disposition":"NOT_SIGNED",
            },
            {
                "finding":"V1_EVENT_SUBCLASS_ACCEPTED_V2_EXACT_TYPE_ONLY",
                "v1_scope":"BacktestHarness.visible_events",
                "v2_scope":"StrictReplayHarnessV2.visible_events",
                "substitutability":"NOT_INTERCHANGEABLE_WITH_SUBCLASS",
                "owner_disposition":"NOT_SIGNED",
            },
        ],
        "rollback_scope":"IN_MEMORY_SYNTHETIC_SEMVER_2_0_TO_2_1_TO_2_0_ONLY",
        "automatic_compatibility_adapter_authorized":False,
        "full_v1_v2_abi_or_behavior_certified":False,
        "a02_owner_signed":0,
        "a03_owner_signed":0,
        "G01_G08_OA01_OA06_closed":False,
        "real_source_rights_or_physical_drive_cache_proven":False,
        "real_N_Nminus1_release_rollback_tested":False,
        "production_or_trading_authorized":False,
        "prior_128_fixture_sha256":baseline["fixture_matrix_sha256"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args(argv)
    report=build()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="cases"},sort_keys=True))


if __name__=="__main__":
    main()
