"""Consumer-driven v2 port substitution tests; synthesized events and rules only.

Tests cover explicit v1/v2 isolation, semantic known-time parity, and
EngineeringPortRegistry's in-memory swap/rollback contract. They do not
exercise network I/O, vendor entitlements, broker execution or Cloud runtime.
"""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import unittest

from swing_trading.backtest import BacktestHarness
from swing_trading.causal import CausalMarketEvent
from swing_trading.contracts import DecisionStatus, Evidence, SignalDecision, Strategy, ZONE_IDS
from swing_trading.engineering_contracts import (
    EngineeringPortRegistry, PortDescriptor, check_port, require_compatible_port,
)
from swing_trading.replay import ReplayClock
from swing_trading.strict_contract_v2 import (
    StrictEvidenceV2, StrictReplayClockV2, StrictSignalDecisionV2,
)
from swing_trading.v2_replay_port import (
    StrictReplayHarnessV2, V2_MARKET_PORT, V2_RULES_PORT,
)

T0 = datetime(2026, 11, 9, 0, tzinfo=timezone.utc)
T1 = T0 + timedelta(minutes=5)
T2 = T1 + timedelta(minutes=5)


class FakeSource:
    def __init__(self, events=()):
        self.events = tuple(events)
        self.calls = 0

    def available_events(self, as_of_utc):
        self.calls += 1
        return self.events


class FakeRules:
    def __init__(self, override=None):
        self.calls = 0
        self.override = override

    def evaluate(self, zone_id, strategy, as_of_utc):
        self.calls += 1
        if self.override is not None:
            return self.override
        return StrictSignalDecisionV2(zone_id, strategy, DecisionStatus.UNVERIFIED)


class MissingMethods:
    pass


def event(event_id, event_time, first_known, revision="r1"):
    return CausalMarketEvent(
        event_id, revision, event_time, first_known, {"synthetic": True}
    )


def harness(clock=None, source=None, rules=None, market_port=None, rules_port=None):
    return StrictReplayHarnessV2.from_contracts(
        clock=StrictReplayClockV2(T0) if clock is None else clock,
        market_data=FakeSource() if source is None else source,
        market_port=V2_MARKET_PORT if market_port is None else market_port,
        rules=FakeRules() if rules is None else rules,
        rules_port=V2_RULES_PORT if rules_port is None else rules_port,
    )


class VersionedPortIsolationTests(unittest.TestCase):
    def test_contract_ids_are_explicit_v2_synthetic(self):
        self.assertEqual(V2_MARKET_PORT.contract_id, "replay.causal_events")
        self.assertEqual(V2_RULES_PORT.contract_id, "rules.zone_registry")
        self.assertEqual(V2_MARKET_PORT.version, "2.0.0")
        self.assertEqual(V2_RULES_PORT.version, "2.0.0")
        self.assertEqual(V2_MARKET_PORT.scope, "SYNTHETIC_TEST_ONLY")

    def test_legacy_clock_rejected_before_callbacks(self):
        source = FakeSource()
        rules = FakeRules()
        with self.assertRaisesRegex(TypeError, "StrictReplayClockV2 required"):
            harness(clock=ReplayClock(T0), source=source, rules=rules)
        self.assertEqual(source.calls, 0)
        self.assertEqual(rules.calls, 0)

    def test_direct_constructor_without_port_pins_cannot_bypass_gate(self):
        with self.assertRaises(TypeError):
            StrictReplayHarnessV2(
                clock=StrictReplayClockV2(T0),
                market_data=FakeSource(), rules=FakeRules(),
            )
        with self.assertRaisesRegex(ValueError, "INCOMPATIBLE_CONTRACT_VERSION"):
            StrictReplayHarnessV2(
                clock=StrictReplayClockV2(T0),
                market_data=FakeSource(), rules=FakeRules(),
                market_port=replace(V2_MARKET_PORT, version="1.0.0"),
                rules_port=V2_RULES_PORT,
            )

    def test_after_wiring_ports_and_provider_cannot_be_reassigned(self):
        fixture = harness()
        with self.assertRaises(FrozenInstanceError):
            fixture.market_port = replace(V2_MARKET_PORT, version="1.0.0")
        with self.assertRaises(FrozenInstanceError):
            fixture.market_data = MissingMethods()
        with self.assertRaises(FrozenInstanceError):
            fixture.clock = ReplayClock(T0)
        self.assertEqual(fixture.market_port.version, "2.0.0")

    def test_legacy_version_1_port_cannot_fake_v2(self):
        source = FakeSource()
        old = replace(V2_MARKET_PORT, version="1.0.0")
        with self.assertRaisesRegex(ValueError, "INCOMPATIBLE_CONTRACT_VERSION"):
            harness(source=source, market_port=old)
        self.assertEqual(source.calls, 0)

    def test_source_scope_fallback_and_downgrade_denied(self):
        source = FakeSource()
        for bad in (
            replace(V2_MARKET_PORT, scope="SSI"),
            replace(V2_MARKET_PORT, scope="LIVE"),
            replace(V2_MARKET_PORT, version="1.9.9"),
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                harness(source=source, market_port=bad)
        self.assertEqual(source.calls, 0)

    def test_wrong_contract_id_and_missing_method_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "CONTRACT_ID_MISMATCH"):
            harness(market_port=replace(V2_MARKET_PORT, contract_id="other.data"))
        with self.assertRaisesRegex(ValueError, "MISSING_CALLABLE"):
            harness(source=MissingMethods())

    def test_rules_mismatch_rejected_without_evaluating(self):
        rules = FakeRules()
        for bad in (
            replace(V2_RULES_PORT, version="1.0.0"),
            replace(V2_RULES_PORT, scope="DNSE"),
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                harness(rules=rules, rules_port=bad)
        self.assertEqual(rules.calls, 0)

    def test_legacy_harness_does_not_implicitly_accept_v2(self):
        with self.assertRaisesRegex(TypeError, "Explicit causal ReplayClock required"):
            BacktestHarness.from_contracts(
                clock=StrictReplayClockV2(T0),
                market_data=FakeSource(),
                market_port=V2_MARKET_PORT,
                rules=FakeRules(),
                rules_port=V2_RULES_PORT,
            )

    def test_new_minor_port_can_satisfy_old_minor_explicitly(self):
        upgraded = replace(V2_MARKET_PORT, version="2.1.0")
        result = check_port(V2_MARKET_PORT, upgraded, FakeSource())
        self.assertTrue(result.compatible)
        self.assertFalse(result.live_data_authorized)
        self.assertFalse(result.deploy_authorized)
        self.assertFalse(result.trading_authorized)


class StrictReplayConsumerTests(unittest.TestCase):
    def test_injected_fixture_ports_not_executed_during_construction(self):
        source, rules = FakeSource(), FakeRules()
        _ = harness(source=source, rules=rules)
        self.assertEqual((source.calls, rules.calls), (0, 0))

    def test_no_future_event_or_future_known_revision(self):
        src = FakeSource((
            event("old", T0, T0),
            event("late_revision", T0, T1, "r2"),
            event("future_event", T2, T2),
        ))
        clock = StrictReplayClockV2(T0)
        h = harness(clock=clock, source=src)
        self.assertEqual(tuple(e.event_id for e in h.visible_events()), ("old",))
        clock.advance_to(T1)
        self.assertEqual(tuple(e.event_id for e in h.visible_events()),
                         ("old", "late_revision"))
        clock.advance_to(T2)
        self.assertEqual(tuple(e.event_id for e in h.visible_events()),
                         ("old", "late_revision", "future_event"))

    def test_sorted_event_replay_is_stable(self):
        src = FakeSource((
            event("z", T0, T0),
            event("a", T0, T0, "r2"),
            event("a", T0, T0, "r1"),
        ))
        out = harness(source=src).visible_events()
        self.assertEqual([(e.event_id, e.revision_id) for e in out],
                         [("a", "r1"), ("a", "r2"), ("z", "r1")])

    def test_wrong_type_from_source_denied_even_if_future(self):
        src = FakeSource((event("old", T0, T0), object()))
        with self.assertRaises(TypeError):
            harness(source=src).visible_events()

    def test_failed_rewind_does_not_change_causal_visibility(self):
        src = FakeSource((event("old", T0, T0), event("late", T0, T1)))
        clock = StrictReplayClockV2(T1)
        h = harness(source=src, clock=clock)
        with self.assertRaises(ValueError):
            clock.as_of_utc = T0
        self.assertEqual([e.event_id for e in h.visible_events()], ["old", "late"])

    def test_all_16_zones_and_2_strategies_remain_unverified(self):
        rules = FakeRules()
        h = harness(rules=rules)
        for zone in ZONE_IDS:
            for strategy in Strategy:
                with self.subTest(zone=zone, strategy=strategy):
                    result = h.evaluate_unverified(zone, strategy)
                    self.assertIs(type(result), StrictSignalDecisionV2)
                    self.assertIs(result.status, DecisionStatus.UNVERIFIED)
                    self.assertFalse(result.evidence)
        self.assertEqual(rules.calls, 32)

    def test_legacy_untyped_rule_result_is_rejected(self):
        old = SignalDecision("B1", Strategy.SHORT, DecisionStatus.UNVERIFIED)
        with self.assertRaises(TypeError):
            harness(rules=FakeRules(old)).evaluate_unverified("B1", Strategy.SHORT)

    def test_typed_fake_detected_and_not_detected_are_denied(self):
        proof = StrictEvidenceV2("FAKE", T0, True)
        for status in (DecisionStatus.DETECTED, DecisionStatus.NOT_DETECTED):
            with self.subTest(status=status), self.assertRaises(PermissionError):
                value = StrictSignalDecisionV2("B1", Strategy.SHORT, status, (proof,))
                harness(rules=FakeRules(value)).evaluate_unverified("B1", Strategy.SHORT)

    def test_wrong_zone_and_strategy_response_denied(self):
        for response in (
            StrictSignalDecisionV2("B2", Strategy.SHORT, DecisionStatus.UNVERIFIED),
            StrictSignalDecisionV2("B1", Strategy.SWING, DecisionStatus.UNVERIFIED),
        ):
            with self.subTest(response=response), self.assertRaises(ValueError):
                harness(rules=FakeRules(response)).evaluate_unverified("B1", Strategy.SHORT)

    def test_unverified_result_with_caller_evidence_denied(self):
        proof = StrictEvidenceV2("FAKE", T0, True)
        value = StrictSignalDecisionV2(
            "B1", Strategy.SHORT, DecisionStatus.UNVERIFIED, (proof,)
        )
        with self.assertRaises(PermissionError):
            harness(rules=FakeRules(value)).evaluate_unverified("B1", Strategy.SHORT)

    def test_invalid_zone_and_strategy_block_before_rule_call(self):
        rules = FakeRules()
        h = harness(rules=rules)
        with self.assertRaises(ValueError):
            h.evaluate_unverified("B9", Strategy.SHORT)
        with self.assertRaises(TypeError):
            h.evaluate_unverified("B1", "SHORT")
        self.assertEqual(rules.calls, 0)


class RegistrySwapAndRollbackTests(unittest.TestCase):
    def test_scoped_add_resolve_replace_restore_without_v1_mutation(self):
        reg = EngineeringPortRegistry()
        original = FakeSource((event("x", T0, T0),))
        alternate = FakeSource((event("x", T0, T0),))
        reg.add(V2_MARKET_PORT, original)
        reg.bind_consumer("mst.v2.preview", V2_MARKET_PORT)
        self.assertIs(reg.resolve(V2_MARKET_PORT), original)
        newer = replace(V2_MARKET_PORT, version="2.1.0")
        reg.replace(V2_MARKET_PORT, newer, alternate)
        self.assertIs(reg.resolve(V2_MARKET_PORT), alternate)
        self.assertEqual(harness(source=reg.resolve(V2_MARKET_PORT)).visible_events(),
                         harness(source=original).visible_events())
        reg.replace(V2_MARKET_PORT, V2_MARKET_PORT, original)
        self.assertIs(reg.resolve(V2_MARKET_PORT), original)
        self.assertEqual(reg.count, 1)

    def test_failed_incompatible_swap_keeps_last_good_port(self):
        reg = EngineeringPortRegistry()
        original = FakeSource()
        reg.add(V2_MARKET_PORT, original)
        reg.bind_consumer("mst.v2.preview", V2_MARKET_PORT)
        for bad in (
            replace(V2_MARKET_PORT, version="1.9.9"),
            replace(V2_MARKET_PORT, scope="SSI"),
            replace(V2_MARKET_PORT, contract_id="other.data"),
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                reg.replace(V2_MARKET_PORT, bad, FakeSource())
            self.assertIs(reg.resolve(V2_MARKET_PORT), original)

    def test_pinned_new_minor_consumer_blocks_rollback_to_old_version(self):
        reg = EngineeringPortRegistry()
        original = FakeSource()
        newer = replace(V2_MARKET_PORT, version="2.1.0")
        reg.add(newer, original)
        reg.bind_consumer("mst.v2.needsminor", newer)
        with self.assertRaisesRegex(ValueError, "INCOMPATIBLE_CONTRACT_VERSION"):
            reg.replace(V2_MARKET_PORT, V2_MARKET_PORT, FakeSource())
        self.assertIs(reg.resolve(newer), original)

    def test_pinned_consumer_prevents_remove_until_detached(self):
        reg = EngineeringPortRegistry()
        reg.add(V2_MARKET_PORT, FakeSource())
        reg.bind_consumer("mst.v2.preview", V2_MARKET_PORT)
        with self.assertRaisesRegex(ValueError, "PORT_HAS_ATTACHED_CONSUMERS"):
            reg.remove(V2_MARKET_PORT)
        self.assertEqual(reg.count, 1)
        reg.detach_consumer("mst.v2.preview")
        reg.remove(V2_MARKET_PORT)
        self.assertEqual(reg.count, 0)


if __name__ == "__main__":
    unittest.main()
