"""A03 candidate v2 wire contract: untrusted inbound, synthetic-only fixture.

This test-only decoder deliberately handles UNVERIFIED decisions with no evidence.
It is NOT a published API, data licence, provider attestation, or real trade signal.
The project must approve the v2 schema before a runtime wire adapter is added.
"""
import json
import unittest

from swing_trading.contracts import DecisionStatus, SignalDecision, Strategy, ZONE_IDS

SCHEMA = "mst.signal_decision.v2"
_FIELDS = frozenset(("schema", "zone_id", "strategy", "status", "evidence"))


def decode_untrusted_fixture(payload: dict) -> SignalDecision:
    """Reject all untrusted actionable or unversioned decisions, even when typed."""
    if type(payload) is not dict:
        raise TypeError("wire document must be an exact JSON object")
    if payload.keys() != _FIELDS:
        raise ValueError("schema required and unknown or missing fields forbidden")
    if payload["schema"] != SCHEMA:
        raise ValueError("unsupported schema version")
    if type(payload["zone_id"]) is not str or payload["zone_id"] not in ZONE_IDS:
        raise ValueError("invalid canonical zone ID")
    if type(payload["strategy"]) is not str:
        raise TypeError("strategy must be JSON string")
    strategy = Strategy(payload["strategy"])
    if type(payload["status"]) is not str:
        raise TypeError("status must be JSON string")
    if payload["status"] != DecisionStatus.UNVERIFIED.value:
        raise PermissionError("untrusted wire cannot claim an actionable status")
    if type(payload["evidence"]) is not list or payload["evidence"]:
        raise PermissionError("untrusted wire cannot attest market evidence")
    return SignalDecision(payload["zone_id"], strategy, DecisionStatus.UNVERIFIED)


def encode_unverified_fixture(decision: SignalDecision) -> str:
    """Deterministic synthetic wire fixture, no provider or production authority."""
    if type(decision) is not SignalDecision:
        raise TypeError("typed SignalDecision required")
    if decision.status is not DecisionStatus.UNVERIFIED or decision.evidence:
        raise PermissionError("only unverified and evidence-free fixture output")
    return json.dumps({
        "schema": SCHEMA, "zone_id": decision.zone_id,
        "strategy": decision.strategy.value, "status": decision.status.value,
        "evidence": [],
    }, sort_keys=True, separators=(",", ":"))


def sample(zone_id="B1", strategy="SHORT"):
    return {"schema": SCHEMA, "zone_id": zone_id, "strategy": strategy,
            "status": "UNVERIFIED", "evidence": []}


class WireV2BoundaryCandidateTests(unittest.TestCase):
    def test_all_sixteen_zone_roundtrips_stay_unverified(self):
        for zone in ZONE_IDS:
            for strategy in Strategy:
                with self.subTest(zone=zone, strategy=strategy):
                    typed = decode_untrusted_fixture(sample(zone, strategy.value))
                    encoded = encode_unverified_fixture(typed)
                    self.assertEqual(decode_untrusted_fixture(json.loads(encoded)), typed)
                    self.assertIs(typed.status, DecisionStatus.UNVERIFIED)
                    self.assertFalse(typed.evidence)

    def test_legacy_unversioned_record_is_not_silently_coerced(self):
        payload = sample()
        payload.pop("schema")
        with self.assertRaises(ValueError):
            decode_untrusted_fixture(payload)

    def test_unknown_version_is_rejected_not_auto_migrated(self):
        for version in ("mst.signal_decision.v1", "mst.signal_decision.v3", ""):
            with self.subTest(version=version), self.assertRaises(ValueError):
                decode_untrusted_fixture({**sample(), "schema": version})

    def test_unknown_or_missing_fields_cannot_be_ignored(self):
        with self.assertRaises(ValueError):
            decode_untrusted_fixture({**sample(), "rights": "granted"})
        for key in tuple(sample()):
            with self.subTest(key=key):
                payload = sample()
                del payload[key]
                with self.assertRaises(ValueError):
                    decode_untrusted_fixture(payload)

    def test_non_object_wire_is_rejected(self):
        for payload in ([], (), None, "UNVERIFIED", 2, True):
            with self.subTest(payload=payload), self.assertRaises(TypeError):
                decode_untrusted_fixture(payload)

    def test_bogus_zone_does_not_map_to_a_valid_signal(self):
        for bad in ("B0", "B9", "S9", "BUY", "", None, 1):
            with self.subTest(zone=bad), self.assertRaises(ValueError):
                decode_untrusted_fixture({**sample(), "zone_id": bad})

    def test_unknown_enum_or_type_is_rejected(self):
        for value in ("M5", "", None, 0, True):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                decode_untrusted_fixture({**sample(), "strategy": value})

    def test_actionable_status_is_denied_even_with_fake_evidence(self):
        for status in ("DETECTED", "NOT_DETECTED", "MUA_XAC_NHAN"):
            with self.subTest(status=status), self.assertRaises(PermissionError):
                decode_untrusted_fixture({**sample(), "status": status})

    def test_claimed_verified_evidence_does_not_create_permission(self):
        with self.assertRaises(PermissionError):
            decode_untrusted_fixture({
                **sample(),
                "evidence": [{"origin": "FAKE", "as_of_utc": "2026-11-08T00:00:00+00:00", "verified": True}],
            })

    def test_nonlist_or_nonempty_evidence_is_denied(self):
        for item in (None, {}, (), "true", [True], [1]):
            with self.subTest(item=item), self.assertRaises(PermissionError):
                decode_untrusted_fixture({**sample(), "evidence": item})

    def test_nonstring_status_does_not_get_coerced(self):
        for value in (True, 1, None, ["UNVERIFIED"]):
            with self.subTest(value=value), self.assertRaises(TypeError):
                decode_untrusted_fixture({**sample(), "status": value})

    def test_encoder_denies_nonunverified_and_fabricated_receipts(self):
        for status, evidence in (
            (DecisionStatus.NOT_DETECTED, ()), (DecisionStatus.DETECTED, ()),
        ):
            # construct a valid domain object with a typed fixture evidence
            from datetime import datetime, timezone
            from swing_trading.contracts import Evidence
            item = Evidence("SYNTHETIC_TEST_ONLY", datetime(2026, 11, 8, tzinfo=timezone.utc), True)
            typed = SignalDecision("B1", Strategy.SHORT, status, (item,))
            with self.subTest(status=status), self.assertRaises(PermissionError):
                encode_unverified_fixture(typed)
        with self.assertRaises(PermissionError):
            from datetime import datetime, timezone
            from swing_trading.contracts import Evidence
            item = Evidence("SYNTHETIC_TEST_ONLY", datetime(2026, 11, 8, tzinfo=timezone.utc), True)
            encode_unverified_fixture(
                SignalDecision("B1", Strategy.SHORT, DecisionStatus.UNVERIFIED, (item,))
            )

    def test_encoder_deterministic_and_does_not_claim_rights(self):
        value = encode_unverified_fixture(
            SignalDecision("S8", Strategy.SWING, DecisionStatus.UNVERIFIED)
        )
        self.assertEqual(value, encode_unverified_fixture(
            SignalDecision("S8", Strategy.SWING, DecisionStatus.UNVERIFIED)
        ))
        self.assertEqual(set(json.loads(value)), _FIELDS)
        self.assertNotIn("rights", value.lower())
        self.assertNotIn("provider", value.lower())


if __name__ == "__main__":
    unittest.main()
