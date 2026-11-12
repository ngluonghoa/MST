"""MST M2/A02: multiwriter, restart, source partition and false witness proofs.

All fake digests and metadata. GitHub Actions ephemeral fixtures only.
This is not an authenticated GitHub ref CAS, physical Drive test, vendor right
grant, historical as-of market feed, or a production writer implementation.
The 63 inherited Swing Trading v1 source modules must remain unchanged.
"""
from dataclasses import replace
from datetime import timedelta
import unittest

from swing_trading.v2_cache_fencing_lab import FixtureManifestWitnessV2
from swing_trading.v2_cloud_publish_verify_lab import (
    FixtureBarrierStateV2,
    FixtureDriveObjectObservationV2,
    FixtureGitCommitObservationV2,
    audit_fixture_cloud_publish,
)
from swing_trading.v2_cloud_ref_witness_plan import (
    FixtureGitRefProposalV2, FixtureGitRefReadbackV2,
)
from test_m4_v2_cache_fencing_lab import (
    NOW, A, B, C, genesis, manifest, partition,
)


def matching_genesis_pair():
    """Both witnesses independently 'agree' to the same invented G1 digest."""
    p = partition()
    a = FixtureManifestWitnessV2()
    b = FixtureManifestWitnessV2()
    pa, ta, first_a, da = genesis(a, p, "runner.shared")
    pb, tb, first_b, db = genesis(b, p, "runner.shared")
    assert pa == pb and first_a == first_b and da == db
    return p, a, b, da


class MultiwriterAndRecoveryBoundaryTests(unittest.TestCase):
    def test_shared_genesis_two_separate_witnesses_accept_competing_g2_forks(self):
        p, a, b, ancestor = matching_genesis_pair()
        ta = a.open_fence(p, "writer.alpha")
        tb = b.open_fence(p, "writer.beta")
        left = manifest(p, ta, 2, ancestor, B, NOW + timedelta(minutes=1))
        right = manifest(p, tb, 2, ancestor, C, NOW + timedelta(minutes=1))
        left_digest = a.submit(p, ta, left, expected_head_digest=ancestor)
        right_digest = b.submit(p, tb, right, expected_head_digest=ancestor)
        self.assertNotEqual(left_digest, right_digest)
        self.assertEqual((left.generation, right.generation), (2, 2))
        self.assertEqual(left.previous_manifest_digest, ancestor)
        self.assertEqual(right.previous_manifest_digest, ancestor)
        self.assertFalse(a.cloud_cas_proven)
        self.assertFalse(b.independently_authenticated_witness)
        # A serializing *single* witness would reject the losing stale writer,
        # but two process-local witnesses do not share a linearization point.

    def test_seal_in_one_witness_does_not_revoke_an_independent_writer(self):
        p, a, b, ancestor = matching_genesis_pair()
        a.seal(p)
        with self.assertRaisesRegex(PermissionError, "PARTITION_SEALED"):
            a.open_fence(p, "writer.blocked")
        tb = b.open_fence(p, "writer.unaware")
        next_b = manifest(p, tb, 2, ancestor, B, NOW + timedelta(minutes=1))
        b.submit(p, tb, next_b, expected_head_digest=ancestor)
        self.assertEqual(b.head(p).generation, 2)
        self.assertFalse(b.drive_write_authorized)
        # An in-memory revocation cannot prove provider or custody revocation.

    def test_fresh_witness_process_can_resurrect_genesis_after_g2(self):
        p = partition()
        working = FixtureManifestWitnessV2()
        _, ticket, _, first_digest = genesis(working, p, "writer.original")
        second = manifest(
            p, ticket, 2, first_digest, B, NOW + timedelta(minutes=1),
        )
        working.submit(p, ticket, second, expected_head_digest=first_digest)
        self.assertEqual(working.head(p).generation, 2)
        restarted = FixtureManifestWitnessV2()
        _, _, old, old_digest = genesis(restarted, p, "writer.original")
        self.assertEqual(old_digest, first_digest)
        self.assertEqual(restarted.head(p), old)
        self.assertEqual(restarted.head(p).generation, 1)
        self.assertEqual(working.head(p).generation, 2)
        # No durable monotonic floor survives creating a new witness instance.

    def test_single_witness_accepts_old_content_digest_as_new_generation_without_recovery_receipt(self):
        w = FixtureManifestWitnessV2()
        p, ticket, _, first_digest = genesis(w)
        second = manifest(
            p, ticket, 2, first_digest, B, NOW + timedelta(seconds=1),
        )
        second_digest = w.submit(
            p, ticket, second, expected_head_digest=first_digest,
        )
        third = manifest(
            p, ticket, 3, second_digest, A, NOW + timedelta(seconds=2),
            recovery=None,
        )
        w.submit(p, ticket, third, expected_head_digest=second_digest)
        self.assertEqual(w.head(p).content_digest, A)
        self.assertIsNone(w.head(p).recovery_of_manifest_digest)
        self.assertEqual(w.head(p).generation, 3)
        # Even a rising timestamp/epoch does not establish source-data freshness.

    def test_three_provider_partitions_are_isolated_within_one_fixture_witness(self):
        w = FixtureManifestWitnessV2()
        ps = (partition("SSI"), partition("DNSE"), partition("VCBS"))
        results = [
            genesis(w, p, "writer." + p.provider_id.lower())
            for p in ps
        ]
        digests = tuple(p.digest for p in ps)
        self.assertEqual(len(set(digests)), 3)
        self.assertTrue(all(w.head(p).generation == 1 for p in ps))
        w.seal(ps[0])
        for p, ticket, first, prev in results[1:]:
            second = manifest(p, ticket, 2, prev, B, NOW + timedelta(seconds=1))
            w.submit(p, ticket, second, expected_head_digest=prev)
        self.assertEqual(w.head(ps[0]).generation, 1)
        self.assertEqual(w.head(ps[1]).generation, 2)
        self.assertEqual(w.head(ps[2]).generation, 2)
        with self.assertRaises((ValueError, PermissionError)):
            p, ticket, original, first = results[1]
            w.submit(ps[2], ticket, original, expected_head_digest=None)
        self.assertFalse(w.cloud_cas_proven)
        # Typed partition isolation is useful; SSI/DNSE/VCBS strings are not
        # licensed provider entitlements or independently enrolled identities.

    def test_same_provider_different_revision_namespace_has_distinct_witness_heads(self):
        w = FixtureManifestWitnessV2()
        p1 = partition("SSI", symbol="SYN002")
        p2 = replace(p1, source_revision_namespace="SRCREV_B")
        self.assertNotEqual(p1.digest, p2.digest)
        genesis(w, p1, "writer.old")
        genesis(w, p2, "writer.new")
        self.assertIsNotNone(w.head(p1))
        self.assertIsNotNone(w.head(p2))
        self.assertNotEqual(w.head(p1).partition_digest, w.head(p2).partition_digest)
        self.assertFalse(w.independently_authenticated_witness)
        # No automatic migration, ownership/entitlement transfer, or shared
        # source-clock witness follows from a new namespace.

    def test_two_competing_git_drive_metadata_claims_both_look_consistent_but_remain_unattested(self):
        p = partition("SSI", symbol="SYN003")
        prior = "1" * 40
        tree = "4" * 40
        published_at = NOW + timedelta(minutes=1)
        states = []
        for candidate, md, chunk in (
            ("2" * 40, A, B),
            ("3" * 40, C, A),
        ):
            proposal = FixtureGitRefProposalV2(
                p.digest, prior, candidate, prior, md,
                "writer.test", 2, published_at,
            )
            readback = FixtureGitRefReadbackV2(
                proposal.branch_name, candidate,
                published_at + timedelta(seconds=1),
            )
            commit = FixtureGitCommitObservationV2(
                candidate, (prior,), tree, p.digest, md, 2,
                published_at + timedelta(seconds=2),
            )
            drive = FixtureDriveObjectObservationV2(
                p.digest, md, chunk, True,
                published_at + timedelta(seconds=3),
            )
            final_readback = FixtureGitRefReadbackV2(
                proposal.branch_name, candidate,
                published_at + timedelta(seconds=4),
            )
            result = audit_fixture_cloud_publish(
                proposal, readback, commit, drive,
                expected_tree_sha=tree, expected_content_sha256=chunk,
                final_readback=final_readback,
            )
            self.assertIs(
                result.state, FixtureBarrierStateV2.CONSISTENT_CLAIMS_UNATTESTED,
            )
            self.assertFalse(result.distributed_atomicity_verified)
            self.assertFalse(result.independent_source_verified)
            self.assertFalse(result.drive_write_authorized)
            states.append(result.candidate_sha)
        self.assertNotEqual(states[0], states[1])
        # Separate, self-consistent caller-supplied observations are not
        # an independent linearizable GitHub+Drive witness.
