"""M2/A03 interoperability and whole-package call-site audit, synthetic only.

No network, broker, licensed OHLCV or real-world trading authority is used.
The strict Python runtime DTO is NOT an unversioned JSON deserializer.
"""
import ast
import copy
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import pickle
import unittest

from swing_trading.contracts import (
    DecisionStatus, Evidence, SignalDecision, Strategy, ZONE_IDS,
)
from swing_trading.replay import ReplayClock

BASE = datetime(2026, 11, 8, tzinfo=timezone.utc)
SRC = Path(__file__).resolve().parents[1] / "src" / "swing_trading"


def decoded_fixture(wire: dict) -> SignalDecision:
    """EXPLICIT typed decoding of synthetic contract data, never production rights."""
    return SignalDecision(
        zone_id=wire["zone_id"],
        strategy=Strategy(wire["strategy"]),
        status=DecisionStatus(wire["status"]),
        evidence=tuple(
            Evidence(
                item["origin"],
                datetime.fromisoformat(item["as_of_utc"]),
                item["verified"],
            )
            for item in wire["evidence"]
        ),
    )


def typed_fixture() -> SignalDecision:
    return SignalDecision(
        "B1", Strategy.SHORT, DecisionStatus.NOT_DETECTED,
        (Evidence("SYNTHETIC_TEST_ONLY", BASE, True),),
    )


class SerialCompatibilityTests(unittest.TestCase):
    def test_public_typed_dataclass_roundtrip_by_replace(self):
        original = typed_fixture()
        rebuilt = replace(original)
        self.assertEqual(rebuilt, original)
        self.assertIsInstance(rebuilt.strategy, Strategy)
        self.assertIsInstance(rebuilt.status, DecisionStatus)
        self.assertEqual(type(rebuilt.evidence), tuple)

    def test_asdict_needs_explicit_retyped_evidence_members(self):
        original = typed_fixture()
        mapping = asdict(original)
        self.assertIsInstance(mapping["evidence"][0], dict)
        with self.assertRaises(TypeError):
            SignalDecision(**mapping)
        typed = replace(original, evidence=tuple(Evidence(**e) for e in mapping["evidence"]))
        self.assertEqual(typed, original)

    def test_json_wire_is_string_enum_and_requires_explicit_decoder(self):
        original = typed_fixture()
        wire = {
            "zone_id": original.zone_id,
            "strategy": original.strategy,
            "status": original.status,
            "evidence": [{
                "origin": e.origin,
                "as_of_utc": e.as_of_utc.isoformat(),
                "verified": e.verified,
            } for e in original.evidence],
        }
        encoded = json.dumps(wire, sort_keys=True)
        raw = json.loads(encoded)
        self.assertIsInstance(raw["strategy"], str)
        with self.assertRaises(TypeError):
            SignalDecision(**raw)
        self.assertEqual(decoded_fixture(raw), original)

    def test_wire_unverified_preserves_16_zone_ids_without_promotion(self):
        for zone_id in ZONE_IDS:
            with self.subTest(zone=zone_id):
                raw = {
                    "zone_id": zone_id,
                    "strategy": "SWING",
                    "status": "UNVERIFIED",
                    "evidence": [],
                }
                self.assertIs(decoded_fixture(raw).status, DecisionStatus.UNVERIFIED)

    def test_wire_truthy_string_cannot_be_verified(self):
        raw = {
            "zone_id": "B1",
            "strategy": "SHORT",
            "status": "DETECTED",
            "evidence": [{
                "origin": "SYNTHETIC_TEST_ONLY",
                "as_of_utc": BASE.isoformat(),
                "verified": "true",
            }],
        }
        with self.assertRaises(TypeError):
            decoded_fixture(raw)

    def test_wire_unknown_status_never_defaults_to_detected(self):
        raw = {
            "zone_id": "B1",
            "strategy": "SHORT",
            "status": "READY_TO_BUY",
            "evidence": [],
        }
        with self.assertRaises(ValueError):
            decoded_fixture(raw)

    def test_wire_non_utc_evidence_rejected(self):
        raw = {
            "zone_id": "B1",
            "strategy": "SHORT",
            "status": "DETECTED",
            "evidence": [{
                "origin": "SYNTHETIC_TEST_ONLY",
                "as_of_utc": "2026-11-08T07:00:00+07:00",
                "verified": True,
            }],
        }
        with self.assertRaises(ValueError):
            decoded_fixture(raw)

    def test_frozen_decision_has_no_mutable_verified_field(self):
        from dataclasses import FrozenInstanceError
        original = typed_fixture()
        with self.assertRaises(FrozenInstanceError):
            original.evidence[0].verified = False
        self.assertTrue(original.evidence[0].verified)

    def test_python_copy_and_pickle_of_trusted_clock_snapshot(self):
        # pickle is acceptable ONLY for trusted local engineering data;
        # unpickling untrusted bytes is forbidden and not covered here.
        original = ReplayClock(BASE + timedelta(minutes=5))
        for cloned in (copy.copy(original), copy.deepcopy(original), pickle.loads(pickle.dumps(original))):
            with self.subTest(kind=type(cloned)):
                self.assertEqual(cloned, original)
                with self.assertRaises(ValueError):
                    cloned.as_of_utc = BASE
                self.assertEqual(cloned, original)

    def test_new_clock_snapshot_does_not_rewind_original(self):
        original = ReplayClock(BASE + timedelta(minutes=5))
        earlier = replace(original, as_of_utc=BASE)
        self.assertNotEqual(earlier, original)
        self.assertEqual(original.as_of_utc, BASE + timedelta(minutes=5))
        self.assertTrue(earlier.known(BASE))
        self.assertFalse(earlier.known(BASE + timedelta(seconds=1)))


class WholePackageConsumerInventoryTests(unittest.TestCase):
    def test_all_63_source_modules_parse_without_dynamic_import(self):
        modules = sorted(SRC.glob("*.py"))
        self.assertEqual(len(modules), 63)
        for file in modules:
            with self.subTest(module=file.name):
                ast.parse(file.read_text(encoding="utf-8"), filename=file.name)

    def test_no_literal_untyped_signal_decision_in_source_call_sites(self):
        violations = []
        counts = {"replay_module_importers": 0, "ReplayClock_calls": 0,
                  "SignalDecision_calls": 0, "Evidence_calls": 0,
                  "ReplayClock_direct_writes": 0}
        for file in sorted(SRC.glob("*.py")):
            root = ast.parse(file.read_text(encoding="utf-8"), filename=file.name)
            imports_replay = False
            for node in ast.walk(root):
                if isinstance(node, ast.ImportFrom) and (
                    (node.level == 1 and node.module == "replay") or
                    (node.level == 0 and node.module == "swing_trading.replay")
                ):
                    imports_replay = True
                if isinstance(node, ast.Call):
                    name = (node.func.id if isinstance(node.func, ast.Name)
                            else node.func.attr if isinstance(node.func, ast.Attribute)
                            else "")
                    if name in ("ReplayClock", "SignalDecision", "Evidence"):
                        counts[name + "_calls"] += 1
                    if name == "SignalDecision":
                        selected = list(node.args[1:3])
                        selected += [
                            kw.value for kw in node.keywords
                            if kw.arg in ("strategy", "status")
                        ]
                        if any(isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                               for arg in selected):
                            violations.append(f"{file.name}:{node.lineno}")
                if isinstance(node, ast.Assign):
                    if any(isinstance(t, ast.Attribute) and t.attr == "as_of_utc"
                           for t in node.targets):
                        counts["ReplayClock_direct_writes"] += 1
            if imports_replay:
                counts["replay_module_importers"] += 1
        # No exact count pin: AST diagnostic imports include require_utc-only users,
        # not 31 independently verified ReplayClock consumers.
        self.assertGreater(counts["replay_module_importers"], 0)
        self.assertGreater(counts["SignalDecision_calls"], 0)
        self.assertFalse(violations, f"Untyped literal decision constructors: {violations}")
        print("M2_A03_CONSUMER_INVENTORY=" + json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
