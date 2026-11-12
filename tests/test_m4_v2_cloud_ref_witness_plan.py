"""M4 Git-ref witness protocol shape. All values synthetic and Cloud-I/O free."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import unittest

from swing_trading.v2_cloud_ref_witness_plan import (
    FixtureGitRefProposalV2, FixtureGitRefReadbackV2, FixtureRefResultV2,
    reconcile_fixture_ref,
)

T0 = datetime(2026, 11, 9, 3, tzinfo=timezone.utc)
PART = "a" * 64
OTHER = "b" * 64
HEAD = "1" * 40
ALPHA = "2" * 40
BETA = "3" * 40
MANIFEST = "4" * 64


def proposal(part=PART, head=HEAD, candidate=ALPHA, parent=HEAD, gen=1):
    return FixtureGitRefProposalV2(
        part, head, candidate, parent, MANIFEST, "runner.alpha", gen, T0,
    )


def observe(p=None, sha=ALPHA, at=T0, branch=None):
    p = proposal() if p is None else p
    return FixtureGitRefReadbackV2(
        p.branch_name if branch is None else branch, sha, at,
    )


class GitHubRefIntentTests(unittest.TestCase):
    def test_intent_forces_non_force_update_and_explicit_expected_head(self):
        value = proposal()
        self.assertEqual(value.update_intent["sha"], ALPHA)
        self.assertEqual(value.update_intent["expected_sha"], HEAD)
        self.assertIs(value.update_intent["force"], False)
        self.assertEqual(value.update_intent["branch_name"], value.branch_name)
        self.assertNotIn("credentials", value.update_intent)
        self.assertNotIn("content", value.update_intent)

    def test_namespace_encodes_complete_source_partition_digest(self):
        p1, p2 = proposal(PART), proposal(OTHER)
        self.assertNotEqual(p1.branch_name, p2.branch_name)
        self.assertTrue(p1.branch_name.endswith(PART))
        self.assertTrue(p1.branch_name.startswith("mst/m4-witness-test-only/"))

    def test_same_parent_two_concurrent_writers_propose_distinct_commits(self):
        first = proposal(candidate=ALPHA)
        second = proposal(candidate=BETA)
        self.assertEqual(first.expected_head_sha, second.expected_head_sha)
        self.assertEqual(first.candidate_parent_sha, second.candidate_parent_sha)
        self.assertNotEqual(first.candidate_commit_sha, second.candidate_commit_sha)
        self.assertIs(first.update_intent["force"], False)
        self.assertIs(second.update_intent["force"], False)
        self.assertFalse(first.write_enabled)
        self.assertFalse(second.write_enabled)

    def test_commit_must_be_direct_child_of_claimed_prior_head(self):
        with self.assertRaisesRegex(ValueError, "directly"):
            proposal(candidate=ALPHA, parent=BETA)
        with self.assertRaisesRegex(ValueError, "No-op"):
            proposal(candidate=HEAD)

    def test_digest_and_commit_sha_types_cannot_be_auto_coerced(self):
        with self.assertRaises(ValueError):
            proposal(part="x" * 64)
        with self.assertRaises(ValueError):
            proposal(head="1" * 39, parent="1" * 39)
        with self.assertRaises(ValueError):
            proposal(candidate="2" * 41)
        with self.assertRaises(ValueError):
            replace(proposal(), manifest_digest="not-sha256")
        with self.assertRaises(ValueError):
            replace(proposal(), writer_id="../runner")
        with self.assertRaises(ValueError):
            replace(proposal(), writer_id="Runner.SSO")

    def test_generation_rejects_boolean_and_missing(self):
        for bad in (0, -1, True, "3", None):
            with self.subTest(gen=bad), self.assertRaises(ValueError):
                proposal(gen=bad)

    def test_utc_and_timezone_checks_fail_closed(self):
        for bad in (T0.replace(tzinfo=None),
                    T0.astimezone(timezone(timedelta(hours=7))),
                    "2026-11-09T03:00:00Z"):
            with self.subTest(value=bad), self.assertRaises((TypeError, ValueError)):
                replace(proposal(), proposed_at_utc=bad)

    def test_frozen_proposal_cannot_rewrite_expected_head(self):
        original = proposal()
        with self.assertRaises(FrozenInstanceError):
            original.expected_head_sha = BETA

    def test_intent_never_allows_licensed_source_or_cache_writes(self):
        p = proposal()
        self.assertFalse(p.source_licence_authorized)
        self.assertFalse(p.write_enabled)
        self.assertNotIn("force_with_lease", p.update_intent)


class ReadbackAndAmbiguousWriteTests(unittest.TestCase):
    def test_observed_candidate_sha_is_not_independent_attestation(self):
        value = reconcile_fixture_ref(proposal(), observe())
        self.assertIs(value.result, FixtureRefResultV2.CANDIDATE_SHA_OBSERVED_UNATTESTED)
        self.assertEqual(value.proposed_manifest_digest, MANIFEST)
        self.assertFalse(value.independent_commit_lineage_verified)
        self.assertFalse(value.global_cas_proven)
        self.assertFalse(value.cloud_cache_write_authorized)
        self.assertFalse(value.trading_authorized)

    def test_old_ref_still_present_is_not_a_success(self):
        value = reconcile_fixture_ref(proposal(), observe(sha=HEAD))
        self.assertIs(value.result, FixtureRefResultV2.OLD_SHA_STILL_OBSERVED)
        self.assertFalse(value.global_cas_proven)

    def test_competing_writer_ref_readback_rejects_this_candidate(self):
        p = proposal(candidate=ALPHA)
        result = reconcile_fixture_ref(p, observe(p, sha=BETA))
        self.assertIs(result.result, FixtureRefResultV2.COMPETING_OR_UNKNOWN_SHA)
        self.assertFalse(result.cloud_cache_write_authorized)

    def test_unknown_commit_sha_fails_closed_after_opaque_server_error(self):
        result = reconcile_fixture_ref(proposal(), observe(sha="e" * 40))
        self.assertIs(result.result, FixtureRefResultV2.COMPETING_OR_UNKNOWN_SHA)
        self.assertFalse(result.independent_commit_lineage_verified)

    def test_wrong_partition_readback_rejected(self):
        p = proposal()
        b = observe(p, branch=proposal(OTHER).branch_name)
        with self.assertRaisesRegex(ValueError, "CROSS_PARTITION"):
            reconcile_fixture_ref(p, b)

    def test_readback_before_promotion_not_validated(self):
        p = proposal()
        with self.assertRaisesRegex(ValueError, "REWOUND"):
            reconcile_fixture_ref(p, observe(p, at=T0 - timedelta(seconds=1)))

    def test_reconciliation_only_accepts_exact_types(self):
        with self.assertRaises(TypeError):
            reconcile_fixture_ref({"sha": ALPHA}, observe())
        with self.assertRaises(TypeError):
            reconcile_fixture_ref(proposal(), {"sha": ALPHA})

    def test_invalid_readback_ref_or_sha_rejected(self):
        for branch in ("refs/heads/main", "mst/m4-witness-test-only/../escape",
                       "mst/m4-witness-test-only/" + "X" * 64):
            with self.subTest(branch=branch), self.assertRaises(ValueError):
                FixtureGitRefReadbackV2(branch, ALPHA, T0)
        with self.assertRaises(ValueError):
            FixtureGitRefReadbackV2(proposal().branch_name, "Z" * 40, T0)

    def test_readback_utc_enforced(self):
        with self.assertRaises(ValueError):
            observe(at=T0.replace(tzinfo=None))

    def test_sha_observation_not_cryptographic_signer_or_vendor_rights(self):
        p = proposal()
        result = reconcile_fixture_ref(p, observe(p, ALPHA))
        self.assertFalse(p.source_licence_authorized)
        self.assertFalse(p.write_enabled)
        self.assertFalse(result.global_cas_proven)
        self.assertFalse(result.cloud_cache_write_authorized)

    def test_newer_generation_does_not_infer_prior_commit_lineage(self):
        p = proposal(gen=100)
        output = reconcile_fixture_ref(p, observe(p, ALPHA))
        self.assertIs(output.result, FixtureRefResultV2.CANDIDATE_SHA_OBSERVED_UNATTESTED)
        self.assertFalse(output.independent_commit_lineage_verified)


if __name__ == "__main__":
    unittest.main()
