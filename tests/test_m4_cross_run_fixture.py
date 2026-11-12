"""M4 cross-run test-only artifact parser invariants; synthetic only."""
from copy import deepcopy
from hashlib import sha256
import json
import unittest

from scripts.m4_cross_run_fixture import canonical, emit_claim, recover_claim


def text(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class CrossRunArtifactProtocolTests(unittest.TestCase):
    def setUp(self):
        self.artifact = emit_claim(101, 8)

    def check_no_authority(self, result):
        for key in (
            "real_google_drive_readback", "independent_witness",
            "durable_rollback_floor", "distributed_cas",
            "vendor_entitlement", "market_data_authorized",
            "trading_authorized",
        ):
            self.assertIs(result[key], False)

    def test_bootstrap_is_explicit_and_unattested(self):
        result = recover_claim(None, current_run_id=101, pr_number=8)
        self.assertEqual(result["status"], "BOOTSTRAP_NO_PRIOR_CACHE")
        self.check_no_authority(result)
        with self.assertRaisesRegex(ValueError, "NO_CROSS_RUN_CACHE"):
            recover_claim(None, current_run_id=102, pr_number=8, require_prior=True)

    def test_prior_run_candidate_is_verified_only_as_untrusted_bytes(self):
        value = recover_claim(text(self.artifact), current_run_id=102,
                              pr_number=8, require_prior=True)
        self.assertEqual(value["prior_run_id"], 101)
        self.assertEqual(value["current_run_id"], 102)
        self.assertEqual(
            value["status"], "CROSS_RUN_CACHE_BYTES_VERIFIED_UNATTESTED",
        )
        self.check_no_authority(value)

    def test_reject_corrupt_artifact(self):
        value = deepcopy(self.artifact)
        value["claim"]["content_sha256"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "CORRUPTED_CACHED_FIXTURE"):
            recover_claim(text(value), current_run_id=102, pr_number=8)

    def test_reject_same_run_or_future_run_replay(self):
        for run_id in (101, 100):
            with self.subTest(run_id=run_id):
                with self.assertRaisesRegex(ValueError, "NON_MONOTONIC"):
                    recover_claim(text(self.artifact), current_run_id=run_id,
                                  pr_number=8)

    def test_reject_cross_pr_cache(self):
        with self.assertRaisesRegex(ValueError, "CROSS_PR_CACHE"):
            recover_claim(text(self.artifact), current_run_id=102, pr_number=9)

    def test_reject_caller_self_rehashed_false_authority_claim(self):
        value = deepcopy(self.artifact)
        value["claim"]["witness_authorized"] = True
        value["claim_sha256"] = sha256(canonical(value["claim"])).hexdigest()
        with self.assertRaisesRegex(ValueError, "MISMATCHED_OR_UNTRUSTED"):
            recover_claim(text(value), current_run_id=102, pr_number=8)

    def test_reject_self_rehashed_partition_substitution(self):
        value = deepcopy(self.artifact)
        value["claim"]["partition_sha256"] = "e" * 64
        value["claim_sha256"] = sha256(canonical(value["claim"])).hexdigest()
        with self.assertRaisesRegex(ValueError, "MISMATCHED_OR_UNTRUSTED"):
            recover_claim(text(value), current_run_id=102, pr_number=8)

    def test_reject_unexpected_receipt_or_claim_fields(self):
        for altered in (
            {"claim": self.artifact["claim"], "claim_sha256":
             self.artifact["claim_sha256"], "authorized": True},
            {"claim": self.artifact["claim"]},
        ):
            with self.subTest(value=altered):
                with self.assertRaisesRegex(ValueError, "NON_CANONICAL_RECEIPT"):
                    recover_claim(text(altered), current_run_id=102, pr_number=8)
        value = deepcopy(self.artifact)
        value["claim"]["source_license"] = "CLAIMED"
        value["claim_sha256"] = sha256(canonical(value["claim"])).hexdigest()
        with self.assertRaisesRegex(ValueError, "NON_CANONICAL_CLAIM"):
            recover_claim(text(value), current_run_id=102, pr_number=8)

    def test_deterministic_fixture_digest_is_not_signature(self):
        self.assertEqual(emit_claim(101, 8), self.artifact)
        self.assertEqual(
            self.artifact["claim_sha256"],
            sha256(canonical(self.artifact["claim"])).hexdigest(),
        )
        self.assertNotIn("signature", self.artifact)
        self.check_no_authority(
            recover_claim(text(self.artifact), current_run_id=103, pr_number=8),
        )

    def test_invalid_id_and_malformed_json_denied(self):
        for bad in (0, -1, True, "101"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                emit_claim(bad, 8)
        for bad in ("not-json", "[]", "null"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                recover_claim(bad, current_run_id=102, pr_number=8)
