"""M4 cross-GitHub-run registry artifact negative controls (no authority)."""
from copy import deepcopy
import json
import unittest

from scripts.m4_registry_cross_run_fixture import (
    DENIED, _hash, emit_fixture, recover_fixture,
)


def serialize(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class CrossRunRegistryTests(unittest.TestCase):
    def setUp(self):
        self.packet = emit_fixture(101, 8)

    def recover(self, packet=None, *, run=102, pr=8, minimum=None):
        return recover_fixture(
            serialize(self.packet if packet is None else packet),
            current_run_id=run, pr=pr, require_prior=True,
            caller_minimum_run_id=minimum,
        )

    def test_bootstrap_must_never_claim_registry_authority(self):
        result = recover_fixture(None, current_run_id=102, pr=8)
        self.assertIn("UNATTESTED", result["status"])
        for key in DENIED:
            self.assertIs(result[key], False)

    def test_missing_prior_strictly_denied(self):
        with self.assertRaisesRegex(ValueError, "CACHE_NOT_FOUND"):
            recover_fixture(None, current_run_id=102, pr=8, require_prior=True)

    def test_successful_cross_run_bytes_are_unattested(self):
        r = self.recover()
        self.assertEqual(r["prior_run_id"], 101)
        self.assertEqual(r["current_run_id"], 102)
        self.assertIn("UNATTESTED", r["status"])
        for key in DENIED:
            self.assertIs(r[key], False)

    def test_changed_bytes_without_hash_change_are_rejected(self):
        p = deepcopy(self.packet)
        p["claim"]["producer_run_id"] = 100
        with self.assertRaisesRegex(ValueError, "TAMPERED"):
            self.recover(p)

    def test_attacker_self_rehashed_authority_flag_is_denied(self):
        for flag in ("owner_authorized", "vendor_authorized", "cache_write_authorized"):
            p = deepcopy(self.packet)
            p["claim"][flag] = True
            p["claim_digest"] = _hash(p["claim"])
            with self.subTest(flag=flag), self.assertRaisesRegex(
                ValueError, "UNAUTHORIZED"
            ):
                self.recover(p)

    def test_self_rehashed_partition_and_policy_change_denied(self):
        for k in ("partition_digest", "rights_policy_digest"):
            p = deepcopy(self.packet)
            p["claim"][k] = "e" * 64
            p["claim_digest"] = _hash(p["claim"])
            with self.subTest(key=k), self.assertRaisesRegex(ValueError, "UNAUTHORIZED"):
                self.recover(p)

    def test_same_or_future_run_not_accepted(self):
        for run in (100, 101):
            with self.subTest(run=run), self.assertRaisesRegex(
                ValueError, "SAME_RUN_OR_FUTURE"
            ):
                self.recover(run=run)

    def test_cross_pr_replay_rejected(self):
        with self.assertRaisesRegex(ValueError, "CROSS_PR"):
            self.recover(pr=9)

    def test_self_rehashed_revision_epoch_or_floor_lie_denied(self):
        for k, v in (
            ("registry_revision", 2), ("registry_revision", True),
            ("registry_parent_digest", "d" * 64),
            ("key_epoch", 2), ("key_epoch", True),
            ("floor_generation", 4), ("floor_generation", True),
            ("floor_digest", "d" * 64),
        ):
            p = deepcopy(self.packet)
            p["claim"][k] = v
            p["claim_digest"] = _hash(p["claim"])
            with self.subTest(key=k, value=v), self.assertRaisesRegex(
                ValueError, "UNAUTHORIZED"
            ):
                self.recover(p)

    def test_same_valid_cached_artifact_can_be_replayed_to_new_run(self):
        first = self.recover(run=102)
        second = self.recover(run=104)
        self.assertEqual(first["registry_digest"], second["registry_digest"])
        self.assertFalse(first["protected_registry_floor_verified"])
        self.assertFalse(second["protected_registry_floor_verified"])

    def test_caller_minimum_rejects_but_can_be_reset(self):
        with self.assertRaisesRegex(ValueError, "CALLER_ONLY_FLOOR"):
            self.recover(run=104, minimum=102)
        reset = self.recover(run=104)
        self.assertEqual(reset["prior_run_id"], 101)
        self.assertFalse(reset["protected_receipt_floor_verified"])

    def test_untrusted_cache_artifact_can_be_regenerated_with_new_run(self):
        p = emit_fixture(103, 8)
        r = self.recover(p, run=104)
        self.assertEqual(r["prior_run_id"], 103)
        self.assertFalse(r["independent_owner_root_verified"])
        self.assertNotEqual(p["claim_digest"], self.packet["claim_digest"])

    def test_malformed_envelope_and_extra_fields_denied(self):
        for raw in ("{", "[]", "null", "not-json"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                recover_fixture(raw, current_run_id=102, pr=8)
        for bad in ({"claim": self.packet["claim"]}, {"claim": {}, "claim_digest": "a" * 64}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                recover_fixture(serialize(bad), current_run_id=102, pr=8)

    def test_unexpected_claim_extra_field_denied(self):
        p = deepcopy(self.packet)
        p["claim"]["trust_tier"] = "PRODUCTION"
        p["claim_digest"] = _hash(p["claim"])
        with self.assertRaisesRegex(ValueError, "NON_CANONICAL_REGISTRY_CLAIM"):
            self.recover(p)

    def test_untyped_identity_and_ids_fail_closed(self):
        for bad in (True, 0, -1, "101", None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                emit_fixture(bad, 8)
            with self.subTest(pr=bad), self.assertRaises(ValueError):
                emit_fixture(101, bad)
        with self.assertRaises(ValueError):
            recover_fixture(None, current_run_id=101, pr=8,
                            caller_minimum_run_id=0)


if __name__ == "__main__":
    unittest.main()
