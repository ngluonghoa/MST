"""MST M2/A03: fail-closed public contract guards on synthetic data only.

These are the formerly red A02 tests from PR #5, plus compatibility tests.
No vendor rights, real trading decision, live data, or provider transport is used.
"""
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from swing_trading.backtest import BacktestHarness
from swing_trading.causal import CausalMarketEvent
from swing_trading.contracts import (
    DecisionStatus, Evidence, SignalDecision, Strategy, ZONE_IDS,
)
from swing_trading.engine import evaluate_unimplemented_zones
from swing_trading.replay import ReplayClock

T0 = datetime(2026, 11, 8, tzinfo=timezone.utc)
T1 = T0 + timedelta(minutes=5)


class TestClockBoundary(unittest.TestCase):
    def test_direct_field_rewind_is_rejected_atomically(self):
        clock = ReplayClock(T1)
        with self.assertRaises(ValueError):
            clock.as_of_utc = T0
        self.assertEqual(clock.as_of_utc, T1)

    def test_direct_naive_or_non_utc_assignment_is_rejected(self):
        clock = ReplayClock(T1)
        for bad in (
            T0.replace(tzinfo=None),
            T0.astimezone(timezone(timedelta(hours=7))),
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                clock.as_of_utc = bad
            self.assertEqual(clock.as_of_utc, T1)

    def test_direct_forward_and_equal_assignments_keep_public_api(self):
        clock = ReplayClock(T0)
        clock.as_of_utc = T0
        clock.as_of_utc = T1
        self.assertEqual(clock.as_of_utc, T1)
        self.assertTrue(clock.known(T1))
        self.assertFalse(clock.known(T1 + timedelta(seconds=1)))

    def test_advance_to_backward_still_fails_and_does_not_mutate(self):
        clock = ReplayClock(T0)
        clock.advance_to(T1)
        with self.assertRaises(ValueError):
            clock.advance_to(T0)
        self.assertEqual(clock.as_of_utc, T1)

    def test_new_snapshot_can_be_created_at_independent_earlier_time(self):
        clock = ReplayClock(T1)
        old_snapshot = replace(clock, as_of_utc=T0)
        self.assertEqual(old_snapshot.as_of_utc, T0)
        self.assertEqual(clock.as_of_utc, T1)
        self.assertNotEqual(old_snapshot, clock)


class TestDecisionBoundary(unittest.TestCase):
    def test_string_strategy_rejected_even_when_unverified(self):
        with self.assertRaises(TypeError):
            SignalDecision("B1", "SHORT", DecisionStatus.UNVERIFIED)

    def test_string_status_rejected_even_with_verified_fixture(self):
        item = Evidence("synthetic-fixture", T0, True)
        with self.assertRaises(TypeError):
            SignalDecision("B1", Strategy.SHORT, "DETECTED", (item,))

    def test_string_unverified_status_does_not_coerce_enum(self):
        with self.assertRaises(TypeError):
            SignalDecision("B1", Strategy.SHORT, "UNVERIFIED")

    def test_truthy_nonboolean_evidence_is_rejected(self):
        for bad in ("yes", 1, None, [], {}):
            with self.subTest(value=bad), self.assertRaises(TypeError):
                Evidence("synthetic-fixture", T0, bad)

    def test_explicit_false_evidence_cannot_confirm(self):
        item = Evidence("synthetic-fixture", T0, False)
        with self.assertRaises(ValueError):
            SignalDecision("B1", Strategy.SHORT, DecisionStatus.DETECTED, (item,))

    def test_wrong_evidence_container_and_members_are_rejected(self):
        item = Evidence("synthetic-fixture", T0, True)
        with self.assertRaises(TypeError):
            SignalDecision("B1", Strategy.SHORT, DecisionStatus.UNVERIFIED, [item])
        with self.assertRaises(TypeError):
            SignalDecision("B1", Strategy.SHORT, DecisionStatus.DETECTED, (object(),))

    def test_untyped_evidence_origin_or_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            Evidence(123, T0, True)
        with self.assertRaises(TypeError):
            Evidence("synthetic-fixture", "2026-11-08", True)

    def test_valid_typed_decision_preserves_source_behavior(self):
        evidence = Evidence("synthetic-fixture", T0, True)
        decision = SignalDecision(
            "B1", Strategy.SHORT, DecisionStatus.NOT_DETECTED, (evidence,),
        )
        self.assertIs(decision.status, DecisionStatus.NOT_DETECTED)
        self.assertEqual(decision.evidence, (evidence,))

    def test_all_16_unimplemented_zones_still_unverified(self):
        self.assertEqual(len(ZONE_IDS), 16)
        for strategy in Strategy:
            with self.subTest(strategy=strategy):
                result = evaluate_unimplemented_zones(strategy, T0)
                self.assertEqual(tuple(item.zone_id for item in result), ZONE_IDS)
                self.assertTrue(
                    all(item.status is DecisionStatus.UNVERIFIED for item in result)
                )


class FakeData:
    def available_events(self, as_of_utc):
        return (
            CausalMarketEvent("fixture", "r1", T0, T0, {}),
            CausalMarketEvent("fixture", "r2", T0, T1, {}),
        )


class FakeRules:
    def evaluate(self, zone_id, strategy, as_of_utc):
        return SignalDecision(zone_id, strategy, DecisionStatus.UNVERIFIED)


class TestCausalConsumerCompatibility(unittest.TestCase):
    def test_backtest_visibility_not_affected_by_failed_clock_rewind(self):
        harness = BacktestHarness(ReplayClock(T0), FakeData(), FakeRules())
        self.assertEqual([e.revision_id for e in harness.visible_events()], ["r1"])
        harness.clock.advance_to(T1)
        self.assertEqual(
            [e.revision_id for e in harness.visible_events()], ["r1", "r2"],
        )
        with self.assertRaises(ValueError):
            harness.clock.as_of_utc = T0
        self.assertEqual(
            [e.revision_id for e in harness.visible_events()], ["r1", "r2"],
        )


if __name__ == "__main__":
    unittest.main()
