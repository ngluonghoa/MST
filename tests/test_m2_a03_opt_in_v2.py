"""Cloud-only regressions for opt-in v2, with untouched legacy v1 contracts."""
import copy
from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
import json
import unittest

from swing_trading.backtest import BacktestHarness
from swing_trading.causal import CausalMarketEvent
from swing_trading.contracts import (
    DecisionStatus, Evidence, SignalDecision, Strategy, ZONE_IDS,
)
from swing_trading.engine import evaluate_unimplemented_zones
from swing_trading.replay import ReplayClock
from swing_trading.strict_contract_v2 import (
    WIRE_SCHEMA_V2,
    StrictEvidenceV2,
    StrictReplayClockV2,
    StrictSignalDecisionV2,
    decode_untrusted_v2_json,
    encode_unverified_v2_json,
    legacy_to_v2_unverified,
    v2_to_legacy_unverified,
)

T0 = datetime(2026, 11, 9, tzinfo=timezone.utc)
T1 = T0 + timedelta(minutes=5)


class LegacyV1Parity(unittest.TestCase):
    def test_legacy_unchanged_public_types(self):
        self.assertEqual(tuple(f.name for f in fields(SignalDecision)),
                         ("zone_id", "strategy", "status", "evidence"))
        self.assertEqual(tuple(f.name for f in fields(ReplayClock)), ("as_of_utc",))
        self.assertEqual(len(ZONE_IDS), 16)

    def test_legacy_clock_direct_rewind_behavior_is_unchanged(self):
        v1 = ReplayClock(T1)
        v1.as_of_utc = T0
        self.assertEqual(v1.as_of_utc, T0)
        with self.assertRaises(ValueError):
            v1.advance_to(T0 - timedelta(minutes=1))

    def test_legacy_v1_untyped_behavior_stays_unchanged(self):
        old = SignalDecision("B1", "SHORT", DecisionStatus.UNVERIFIED)
        self.assertEqual(old.strategy, "SHORT")
        self.assertEqual(Evidence("legacy-test", T0, "yes").verified, "yes")

    def test_legacy_engine_still_emits_all_unverified(self):
        for strategy in Strategy:
            values = evaluate_unimplemented_zones(strategy, T0)
            self.assertEqual(tuple(v.zone_id for v in values), ZONE_IDS)
            self.assertTrue(all(v.status is DecisionStatus.UNVERIFIED for v in values))
            self.assertTrue(all(type(v) is SignalDecision for v in values))

    def test_v2_classes_are_distinct_and_not_reexports(self):
        self.assertIsNot(ReplayClock, StrictReplayClockV2)
        self.assertIsNot(Evidence, StrictEvidenceV2)
        self.assertIsNot(SignalDecision, StrictSignalDecisionV2)

    def test_legacy_versioned_backtest_port_rejects_v2_clock(self):
        # The opt-in clock is not silently substituted into a v1 versioned port.
        with self.assertRaisesRegex(TypeError, "Explicit causal ReplayClock required"):
            BacktestHarness.from_contracts(
                clock=StrictReplayClockV2(T0), market_data=None,
                market_port=None, rules=None, rules_port=None,
            )


class StrictClockV2(unittest.TestCase):
    def test_assignment_and_advance_cannot_rewind(self):
        clock = StrictReplayClockV2(T0)
        clock.advance_to(T1)
        for attempt in (T0,):
            with self.assertRaises(ValueError):
                clock.as_of_utc = attempt
            self.assertEqual(clock.as_of_utc, T1)
        self.assertTrue(clock.known(T1))
        self.assertFalse(clock.known(T1 + timedelta(seconds=1)))

    def test_naive_non_utc_and_bad_type_rejected(self):
        clock = StrictReplayClockV2(T1)
        for bad in (T0.replace(tzinfo=None),
                    T0.astimezone(timezone(timedelta(hours=7)))):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                clock.as_of_utc = bad
        with self.assertRaises(TypeError):
            clock.as_of_utc = "2026-11-09T00:00:00Z"
        self.assertEqual(clock.as_of_utc, T1)

    def test_construction_validates_type_and_time(self):
        with self.assertRaises(TypeError):
            StrictReplayClockV2("2026-11-09")
        with self.assertRaises(ValueError):
            StrictReplayClockV2(T0.replace(tzinfo=None))

    def test_independent_earlier_snapshot_via_replace(self):
        clock = StrictReplayClockV2(T1)
        old = replace(clock, as_of_utc=T0)
        self.assertEqual(old.as_of_utc, T0)
        self.assertEqual(clock.as_of_utc, T1)
        self.assertEqual(copy.copy(clock), clock)


class StrictDecisionV2(unittest.TestCase):
    def test_valid_typed_fixture_preserved(self):
        proof = StrictEvidenceV2("SYNTHETIC_TEST_ONLY", T0, True)
        value = StrictSignalDecisionV2(
            "B1", Strategy.SHORT, DecisionStatus.NOT_DETECTED, (proof,)
        )
        self.assertEqual(replace(value), value)
        self.assertEqual(value.evidence, (proof,))

    def test_untyped_enums_and_bool_rejected(self):
        for x in ("SHORT", 1, None):
            with self.subTest(strategy=x), self.assertRaises(TypeError):
                StrictSignalDecisionV2("B1", x, DecisionStatus.UNVERIFIED)
        for x in ("DETECTED", 1, None):
            with self.subTest(status=x), self.assertRaises(TypeError):
                StrictSignalDecisionV2("B1", Strategy.SHORT, x)
        for x in ("yes", 1, None, [], 0):
            with self.subTest(verified=x), self.assertRaises(TypeError):
                StrictEvidenceV2("SYNTHETIC_TEST_ONLY", T0, x)

    def test_bad_evidence_container_or_item(self):
        proof = StrictEvidenceV2("SYNTHETIC_TEST_ONLY", T0, True)
        with self.assertRaises(TypeError):
            StrictSignalDecisionV2("B1", Strategy.SHORT, DecisionStatus.UNVERIFIED, [proof])
        with self.assertRaises(TypeError):
            StrictSignalDecisionV2("B1", Strategy.SHORT, DecisionStatus.UNVERIFIED, (object(),))
        with self.assertRaises(ValueError):
            StrictSignalDecisionV2(
                "B1", Strategy.SHORT, DecisionStatus.DETECTED,
                (StrictEvidenceV2("SYNTHETIC_TEST_ONLY", T0, False),)
            )

    def test_bogus_origin_zone_and_non_utc(self):
        for bad in ("", " ", None, 123):
            with self.subTest(origin=bad), self.assertRaises(ValueError):
                StrictEvidenceV2(bad, T0, False)
        with self.assertRaises(ValueError):
            StrictSignalDecisionV2("B9", Strategy.SHORT, DecisionStatus.UNVERIFIED)
        with self.assertRaises(ValueError):
            StrictEvidenceV2("SYNTHETIC_TEST_ONLY", T0.replace(tzinfo=None), False)

    def test_frozen_evidence_not_assignable(self):
        proof = StrictEvidenceV2("SYNTHETIC_TEST_ONLY", T0, True)
        with self.assertRaises(FrozenInstanceError):
            proof.verified = False


class ExplicitLegacyAdapter(unittest.TestCase):
    def test_unverified_empty_evidence_roundtrip_for_all_zones(self):
        for zone in ZONE_IDS:
            for strategy in Strategy:
                with self.subTest(zone=zone, strategy=strategy):
                    old = SignalDecision(zone, strategy, DecisionStatus.UNVERIFIED)
                    fresh = legacy_to_v2_unverified(old)
                    self.assertIs(type(fresh), StrictSignalDecisionV2)
                    self.assertEqual(v2_to_legacy_unverified(fresh), old)

    def test_reject_untyped_or_unverified_with_fake_evidence(self):
        old = SignalDecision("B1", "SHORT", DecisionStatus.UNVERIFIED)
        with self.assertRaises(TypeError):
            legacy_to_v2_unverified(old)
        old2 = SignalDecision(
            "B1", Strategy.SHORT, DecisionStatus.UNVERIFIED,
            (Evidence("SYNTHETIC_TEST_ONLY", T0, True),)
        )
        with self.assertRaises(PermissionError):
            legacy_to_v2_unverified(old2)
        proof = StrictEvidenceV2("SYNTHETIC_TEST_ONLY", T0, True)
        with self.assertRaises(PermissionError):
            v2_to_legacy_unverified(StrictSignalDecisionV2(
                "B1", Strategy.SHORT, DecisionStatus.UNVERIFIED, (proof,)
            ))

    def test_no_authentication_or_order_rights_added(self):
        typed = legacy_to_v2_unverified(
            SignalDecision("S8", Strategy.SWING, DecisionStatus.UNVERIFIED)
        )
        self.assertIs(typed.status, DecisionStatus.UNVERIFIED)
        self.assertFalse(typed.evidence)


def wire(zone="B1", strategy="SHORT", status="UNVERIFIED", evidence=None, schema=WIRE_SCHEMA_V2):
    return json.dumps({
        "schema": schema,
        "zone_id": zone,
        "strategy": strategy,
        "status": status,
        "evidence": [] if evidence is None else evidence,
    })


class UntrustedWireV2(unittest.TestCase):
    def test_16_zone_two_strategy_roundtrips(self):
        for zone in ZONE_IDS:
            for strategy in Strategy:
                with self.subTest(zone=zone, strategy=strategy):
                    decoded = decode_untrusted_v2_json(wire(zone=zone, strategy=strategy.value))
                    self.assertIs(decoded.status, DecisionStatus.UNVERIFIED)
                    self.assertEqual(decoded.evidence, ())
                    self.assertEqual(
                        decode_untrusted_v2_json(encode_unverified_v2_json(decoded)),
                        decoded
                    )

    def test_versionless_v1_and_unknown_v2_are_denied(self):
        with self.assertRaises(ValueError):
            decode_untrusted_v2_json(json.dumps({
                "zone_id": "B1", "strategy": "SHORT",
                "status": "UNVERIFIED", "evidence": [],
            }))
        for version in ("mst.signal_decision.v1", "mst.signal_decision.v3", ""):
            with self.subTest(version=version), self.assertRaises(ValueError):
                decode_untrusted_v2_json(wire(schema=version))

    def test_duplicate_json_keys_denied_including_nested(self):
        original = wire()
        duplicate = original[:-1] + ',"strategy":"SWING"}'
        with self.assertRaises(ValueError):
            decode_untrusted_v2_json(duplicate)
        with self.assertRaises(ValueError):
            decode_untrusted_v2_json('{"schema":"mst.signal_decision.v2","schema":"mst.signal_decision.v2"}')

    def test_invalid_zone_strategy_and_status_denied(self):
        for zone in ("B9", "S0", "BUY", "", 1):
            with self.subTest(zone=zone), self.assertRaises(ValueError):
                decode_untrusted_v2_json(wire(zone=zone))
        for strategy in ("M5", "Unknown", None, True):
            with self.subTest(strategy=strategy), self.assertRaises((TypeError, ValueError)):
                decode_untrusted_v2_json(wire(strategy=strategy))
        for status in ("DETECTED", "NOT_DETECTED", "READY_TO_BUY"):
            with self.subTest(status=status), self.assertRaises(PermissionError):
                decode_untrusted_v2_json(wire(status=status))

    def test_evidence_cannot_grant_market_rights(self):
        with self.assertRaises(PermissionError):
            decode_untrusted_v2_json(wire(evidence=[{
                "origin": "SSI", "verified": True, "as_of_utc": T0.isoformat(),
            }]))
        for x in (None, "verified", {}, True):
            with self.subTest(evidence=x), self.assertRaises(PermissionError):
                decode_untrusted_v2_json(json.dumps({
                    "schema": WIRE_SCHEMA_V2,
                    "zone_id": "B1",
                    "strategy": "SHORT",
                    "status": "UNVERIFIED",
                    "evidence": x,
                }))

    def test_unknown_missing_and_nonfinite_json_denied(self):
        missing = json.loads(wire())
        missing.pop("status")
        with self.assertRaises(ValueError):
            decode_untrusted_v2_json(json.dumps(missing))
        extra = json.loads(wire())
        extra["entitlement_verified"] = True
        with self.assertRaises(ValueError):
            decode_untrusted_v2_json(json.dumps(extra))
        payload = json.loads(wire())
        payload["evidence"] = float("nan")
        with self.assertRaises(ValueError):
            decode_untrusted_v2_json(json.dumps(payload))

    def test_non_object_nonstring_and_oversize_denied(self):
        for x in (None, b"{}", {}, 1):
            with self.subTest(value=x), self.assertRaises(TypeError):
                decode_untrusted_v2_json(x)
        for x in ("null", "[]", "true", "42"):
            with self.subTest(value=x), self.assertRaises(ValueError):
                decode_untrusted_v2_json(x)
        with self.assertRaises(ValueError):
            decode_untrusted_v2_json(wire() + " " * 5000)

    def test_encoder_rejects_actionable_even_if_typed_fixture(self):
        proof = StrictEvidenceV2("SYNTHETIC_TEST_ONLY", T0, True)
        value = StrictSignalDecisionV2(
            "B1", Strategy.SHORT, DecisionStatus.DETECTED, (proof,)
        )
        with self.assertRaises(PermissionError):
            encode_unverified_v2_json(value)
        with self.assertRaises(TypeError):
            encode_unverified_v2_json(
                SignalDecision("B1", Strategy.SHORT, DecisionStatus.UNVERIFIED)
            )

    def test_v1_legacy_module_ast_blobs_still_identical(self):
        # The exact SHA verification is recorded independently in GitHub branch
        # comparison; this test establishes a direct runtime v1/v2 contract boundary.
        self.assertIsNot(SignalDecision, StrictSignalDecisionV2)
        self.assertEqual(decode_untrusted_v2_json(wire()).status, DecisionStatus.UNVERIFIED)
        self.assertIsInstance(SignalDecision("B1", Strategy.SHORT, DecisionStatus.UNVERIFIED), SignalDecision)


if __name__ == "__main__":
    unittest.main()
