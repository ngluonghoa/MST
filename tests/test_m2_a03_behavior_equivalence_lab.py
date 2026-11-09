"""A03 behavior and ABI acceptance: shared safe V1/V2 subset only.

No vendor OHLCV, actual source receipts, Drive cache, broker, or calibrated
16-zone detectors. A green test MUST NOT close A02 or full A03 owner approval.
"""
from datetime import datetime, timedelta, timezone
import re
import unittest

from scripts.m2_a03_behavior_equivalence_lab import (
    CLOCK_TIMES, T0, V1_MARKET_PORT, V1_RULES_PORT,
    _FixtureEvents, _V1Rules, _V2Rules, fixture_events, run_behavior_matrix,
)
from swing_trading.backtest import BacktestHarness
from swing_trading.causal import CausalMarketEvent
from swing_trading.contracts import (
    DecisionStatus, Evidence, SignalDecision, Strategy, ZONE_IDS,
)
from swing_trading.engineering_contracts import PortDescriptor
from swing_trading.engine import evaluate_unimplemented_zones
from swing_trading.replay import ReplayClock
from swing_trading.strict_contract_v2 import (
    StrictEvidenceV2, StrictReplayClockV2, StrictSignalDecisionV2,
    decode_untrusted_v2_json,
)
from swing_trading.v2_replay_port import (
    StrictReplayHarnessV2, V2_MARKET_PORT, V2_RULES_PORT,
)


class SafeFixtureSubsetGoldenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = run_behavior_matrix()

    def test_all_16_zone_ids_original_order(self):
        self.assertEqual(
            ZONE_IDS,
            tuple([f"B{i}" for i in range(1, 9)]
                  + [f"S{i}" for i in range(1, 9)]),
        )
        self.assertEqual(self.receipt["zones_checked"], 16)

    def test_both_original_strategies_are_compared(self):
        self.assertEqual(tuple(x.value for x in Strategy), ("SHORT", "SWING"))
        self.assertEqual(self.receipt["strategies_checked"], 2)

    def test_4_timepoints_128_runtime_decision_comparisons(self):
        self.assertEqual(self.receipt["decision_comparisons"], 128)
        self.assertEqual(self.receipt["as_of_snapshots_checked"], 4)
        self.assertEqual(self.receipt["status"],
                         "V1_V2_SAFE_UNVERIFIED_FIXTURE_SUBSET_MATCHES")

    def test_all_six_causal_event_revisions_and_known_cutoffs(self):
        self.assertEqual(self.receipt["causal_event_revisions"], 6)
        observations = self.receipt["observations"]
        self.assertEqual([len(v["visible_revisions"]) for v in observations],
                         [1, 2, 4, 6])
        self.assertEqual(observations[0]["visible_revisions"], [["early", "r1"]])
        self.assertIn(["correction", "r2"], observations[-1]["visible_revisions"])
        self.assertNotIn(["correction", "r2"], observations[2]["visible_revisions"])
        self.assertNotIn(["future", "r1"], observations[2]["visible_revisions"])

    def test_observations_sorted_by_first_known_not_ingestion_order(self):
        last = self.receipt["observations"][-1]["visible_revisions"]
        self.assertEqual(last, [
            ["early", "r1"], ["mid", "r1"], ["revised", "r2"],
            ["late", "r1"], ["correction", "r2"], ["future", "r1"],
        ])

    def test_stable_synthetic_digest_reproducible(self):
        receipt2 = run_behavior_matrix()
        digest = self.receipt["fixture_matrix_sha256"]
        self.assertRegex(digest, r"^[a-f0-9]{64}$")
        self.assertEqual(receipt2["fixture_matrix_sha256"], digest)
        self.assertEqual(receipt2["observations"], self.receipt["observations"])

    def test_all_unverified_no_authority_or_qualified_market_data(self):
        for field in (
            "full_v2_detector_formula_parity_verified",
            "full_v2_abi_interchangeability_approved",
            "source_vendor_entitlement_verified",
            "real_provider_ohlcv_or_drive_cache_used",
            "a02_63_owner_dispositions_approved",
            "production_cache_authorized",
            "trading_authorized",
        ):
            with self.subTest(field=field):
                self.assertIs(self.receipt[field], False)
        self.assertTrue(self.receipt["signal_decisions_all_unverified"])
        self.assertTrue(self.receipt["v1_v2_known_event_visibility_equal"])

    def test_no_decision_marked_detected_or_not_detected(self):
        for at in CLOCK_TIMES:
            for strategy in Strategy:
                decisions = evaluate_unimplemented_zones(strategy, at)
                self.assertEqual(len(decisions), 16)
                self.assertTrue(all(
                    decision.status is DecisionStatus.UNVERIFIED
                    and not decision.evidence for decision in decisions
                ))


class DeliberateAbiDifferenceTests(unittest.TestCase):
    def test_original_constructor_and_class_identity_not_replaced(self):
        legacy = BacktestHarness(
            ReplayClock(T0), _FixtureEvents(fixture_events()), _V1Rules()
        )
        self.assertIs(type(legacy.clock), ReplayClock)
        self.assertIsNot(StrictReplayClockV2, ReplayClock)
        self.assertIsNot(StrictSignalDecisionV2, SignalDecision)

    def test_legacy_explicit_untyped_behavior_still_exists(self):
        old = SignalDecision("B1", "SHORT", DecisionStatus.UNVERIFIED)
        self.assertEqual(old.strategy, "SHORT")
        self.assertEqual(Evidence("legacy", T0, "yes").verified, "yes")
        with self.assertRaises(TypeError):
            StrictSignalDecisionV2("B1", "SHORT", DecisionStatus.UNVERIFIED)
        with self.assertRaises(TypeError):
            StrictEvidenceV2("legacy", T0, "yes")

    def test_v1_direct_rewind_known_gap_is_not_silently_mutated(self):
        v1 = ReplayClock(T0 + timedelta(minutes=5))
        v1.as_of_utc = T0
        self.assertEqual(v1.as_of_utc, T0)
        v2 = StrictReplayClockV2(T0 + timedelta(minutes=5))
        with self.assertRaises(ValueError):
            v2.as_of_utc = T0
        self.assertEqual(v2.as_of_utc, T0 + timedelta(minutes=5))

    def test_v1_accepts_legacy_port_version_but_not_v2_port(self):
        self.assertEqual(V1_MARKET_PORT.version, "1.0.0")
        self.assertEqual(V2_MARKET_PORT.version, "2.0.0")
        old = BacktestHarness.from_contracts(
            clock=ReplayClock(T0), market_data=_FixtureEvents(()),
            market_port=V1_MARKET_PORT, rules=_V1Rules(),
            rules_port=V1_RULES_PORT,
        )
        self.assertIs(type(old), BacktestHarness)
        with self.assertRaisesRegex(ValueError, "INCOMPATIBLE_CONTRACT_VERSION"):
            BacktestHarness.from_contracts(
                clock=ReplayClock(T0), market_data=_FixtureEvents(()),
                market_port=V2_MARKET_PORT, rules=_V1Rules(),
                rules_port=V1_RULES_PORT,
            )

    def test_v2_cannot_accept_legacy_market_and_rules_ports(self):
        with self.assertRaisesRegex(ValueError, "INCOMPATIBLE_CONTRACT_VERSION"):
            StrictReplayHarnessV2.from_contracts(
                clock=StrictReplayClockV2(T0), market_data=_FixtureEvents(()),
                market_port=V1_MARKET_PORT, rules=_V2Rules(),
                rules_port=V2_RULES_PORT,
            )
        with self.assertRaisesRegex(ValueError, "INCOMPATIBLE_CONTRACT_VERSION"):
            StrictReplayHarnessV2.from_contracts(
                clock=StrictReplayClockV2(T0), market_data=_FixtureEvents(()),
                market_port=V2_MARKET_PORT, rules=_V2Rules(),
                rules_port=V1_RULES_PORT,
            )

    def test_v2_clock_direct_assignment_non_utc_denied(self):
        v2 = StrictReplayClockV2(T0)
        with self.assertRaises(ValueError):
            v2.as_of_utc = T0.replace(tzinfo=None)
        with self.assertRaises(ValueError):
            v2.as_of_utc = T0.astimezone(timezone(timedelta(hours=7)))
        self.assertEqual(v2.as_of_utc, T0)

    def test_explicit_versioned_v2_untrusted_wire_never_promotes(self):
        for status in ("DETECTED", "NOT_DETECTED"):
            with self.subTest(status=status), self.assertRaises(PermissionError):
                decode_untrusted_v2_json(
                    '{"schema":"mst.signal_decision.v2","zone_id":"B1",'
                    '"strategy":"SHORT","status":"' + status + '","evidence":[]}'
                )


class InjectedDifferentialFailureTests(unittest.TestCase):
    def test_malicious_v2_rule_promoting_detected_is_denied(self):
        class UnsafeRules(_V2Rules):
            def evaluate(self, zone_id, strategy, as_of_utc):
                return StrictSignalDecisionV2(
                    zone_id, strategy, DecisionStatus.DETECTED,
                    (StrictEvidenceV2("SYNTHETIC", as_of_utc, True),),
                )

        with self.assertRaisesRegex(PermissionError, "cannot promote"):
            run_behavior_matrix(v2_rules=UnsafeRules())

    def test_malformed_v2_rule_returns_legacy_and_is_rejected(self):
        class WrongResult(_V2Rules):
            def evaluate(self, zone_id, strategy, as_of_utc):
                return SignalDecision(zone_id, strategy, DecisionStatus.UNVERIFIED)

        with self.assertRaisesRegex(TypeError, "StrictSignalDecisionV2"):
            run_behavior_matrix(v2_rules=WrongResult())

    def test_v2_rule_wrong_zone_denied_before_cross_comparison(self):
        class WrongZone(_V2Rules):
            def evaluate(self, zone_id, strategy, as_of_utc):
                other_zone = "S8" if zone_id != "S8" else "B1"
                return StrictSignalDecisionV2(other_zone, strategy, DecisionStatus.UNVERIFIED)

        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            run_behavior_matrix(v2_rules=WrongZone())

    def test_v2_rule_wrong_strategy_denied_before_cross_comparison(self):
        class WrongStrategy(_V2Rules):
            def evaluate(self, zone_id, strategy, as_of_utc):
                other = Strategy.SWING if strategy is Strategy.SHORT else Strategy.SHORT
                return StrictSignalDecisionV2(zone_id, other, DecisionStatus.UNVERIFIED)

        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            run_behavior_matrix(v2_rules=WrongStrategy())

    def test_v2_source_future_or_untrusted_source_mismatch_detected(self):
        items = fixture_events()
        with self.assertRaisesRegex(AssertionError, "EVENT_VISIBILITY_PARITY_DRIFT"):
            run_behavior_matrix(v2_source=_FixtureEvents(items[:-1]))

    def test_v2_source_added_future_event_only_still_filtered(self):
        items = fixture_events()
        future = CausalMarketEvent(
            "not-yet-known", "r1",
            CLOCK_TIMES[-1] + timedelta(minutes=5),
            CLOCK_TIMES[-1] + timedelta(minutes=10), {"synthetic": True},
        )
        test = run_behavior_matrix(v2_source=_FixtureEvents(items + (future,)))
        self.assertEqual(test["decision_comparisons"], 128)

    def test_v2_source_wrong_event_type_denied(self):
        class Bogus:
            pass
        with self.assertRaisesRegex(TypeError, "typed causal fixture events"):
            run_behavior_matrix(v2_source=_FixtureEvents(fixture_events() + (Bogus(),)))

    def test_v2_source_earlier_revision_hidden_until_first_known(self):
        matrix = run_behavior_matrix()
        first = matrix["observations"][0]["visible_revisions"]
        second = matrix["observations"][1]["visible_revisions"]
        self.assertNotIn(["revised", "r2"], first)
        self.assertNotIn(["revised", "r2"], second)
        self.assertIn(["revised", "r2"], matrix["observations"][2]["visible_revisions"])


if __name__ == "__main__":
    unittest.main()
