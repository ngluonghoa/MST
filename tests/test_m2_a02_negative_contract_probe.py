"""M2/A02 intentionally failing security-contract probes. DO NOT MERGE.

These tests are NEGATIVE EXPECTATIONS of future stricter public boundaries.
At the pinned M1 baseline, 4 are intentionally RED to demonstrate potential
bypass of method-only validation, without altering any production source code.

Do not mark missing type guards as approved behavior. Close this probe PR
after collecting CI evidence; preserve exact 1:1 main tree.
"""
import unittest
from datetime import datetime, timedelta, timezone

from swing_trading.replay import ReplayClock
from swing_trading.contracts import DecisionStatus, Evidence, SignalDecision, Strategy

T0 = datetime(2026, 11, 8, tzinfo=timezone.utc)
T1 = T0 + timedelta(minutes=5)


class M2A02NegativeContractProbe(unittest.TestCase):
    def test_baseline_method_guard_is_intact(self):
        clock = ReplayClock(T0)
        clock.advance_to(T1)
        with self.assertRaises(ValueError):
            clock.advance_to(T0)

    def test_negative_direct_field_rewind_must_fail_closed(self):
        clock = ReplayClock(T1)
        with self.assertRaises(ValueError):
            clock.as_of_utc = T0

    def test_negative_strategy_requires_strict_enum(self):
        with self.assertRaises(TypeError):
            SignalDecision("B1", "SHORT", DecisionStatus.UNVERIFIED)

    def test_negative_status_requires_strict_enum(self):
        positive_fixture = Evidence("synthetic-fixture", T0, True)
        with self.assertRaises(TypeError):
            SignalDecision("B1", Strategy.SHORT, "DETECTED", (positive_fixture,))

    def test_negative_evidence_verified_must_be_boolean(self):
        with self.assertRaises(TypeError):
            Evidence("synthetic-fixture", T0, "yes")


if __name__ == "__main__":
    unittest.main()
