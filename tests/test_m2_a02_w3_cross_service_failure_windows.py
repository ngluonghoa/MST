"""MST A02/W3 cross-service publication failure windows, source-locked.

These exercises consume existing opt-in V2 *caller-claimed metadata* barriers.
No network, physical Drive, actual GitHub ref updates, licensed market bars,
signer keys, distributed CAS, cloud write authorization or trading. Unchanged
legacy v1 modules remain the sole 1:1 baseline.
"""
from dataclasses import fields, replace
from datetime import timedelta
import unittest

from swing_trading.v2_cloud_publish_verify_lab import (
    FixtureBarrierStateV2, FixtureReaderFloorV2,
)
from test_m4_v2_cloud_publish_verify_lab import (
    T0, P, M, CONTENT, HEAD, CANDIDATE, TREE, FOREIGN,
    proposal, readback, final_readback, commit, drive, floor, inspect,
)


class CrossServiceFailureWindowsTests(unittest.TestCase):
    def assertUnattested(self, result, expected):
        self.assertIs(result.state, expected)
        self.assertFalse(result.independent_source_verified)
        self.assertFalse(result.distributed_atomicity_verified)
        self.assertFalse(result.licensed_drive_read_authorized)
        self.assertFalse(result.drive_write_authorized)
        self.assertFalse(result.trading_authorized)

    def test_drive_chunk_staged_before_git_ref_is_not_published(self):
        # Synthetic staging at T0+3 is not a committed cache head when ref
        # readback remains at the old SHA.
        staged = inspect(readback=readback(sha=HEAD))
        self.assertUnattested(staged, FixtureBarrierStateV2.REF_NOT_PROMOTED)
        promoted = inspect()
        self.assertUnattested(
            promoted, FixtureBarrierStateV2.CONSISTENT_CLAIMS_UNATTESTED,
        )
        self.assertEqual(staged.manifest_digest, promoted.manifest_digest)

    def test_git_ref_visible_before_drive_object_cannot_release_data(self):
        not_yet = inspect(drive=replace(drive(), present=False))
        self.assertUnattested(
            not_yet, FixtureBarrierStateV2.DRIVE_OBJECT_NOT_READY,
        )
        later = inspect()
        self.assertUnattested(
            later, FixtureBarrierStateV2.CONSISTENT_CLAIMS_UNATTESTED,
        )

    def test_unknown_result_requires_final_ref_readback_and_competitor_detection(self):
        missing = inspect(final_readback=None)
        old = inspect(final_readback=final_readback(sha=HEAD))
        competitor = inspect(final_readback=final_readback(sha=FOREIGN))
        claimed = inspect()
        self.assertUnattested(
            missing, FixtureBarrierStateV2.FINAL_REF_READBACK_MISSING,
        )
        self.assertUnattested(
            old, FixtureBarrierStateV2.FINAL_REF_CHANGED_OR_UNKNOWN,
        )
        self.assertUnattested(
            competitor, FixtureBarrierStateV2.FINAL_REF_CHANGED_OR_UNKNOWN,
        )
        self.assertUnattested(
            claimed, FixtureBarrierStateV2.CONSISTENT_CLAIMS_UNATTESTED,
        )
        # Even a good-looking second ref claim is not remote transaction proof.

    def test_claimed_ref_stable_then_later_competing_ref_is_toc_tou_gap(self):
        before = inspect()
        after = inspect(
            final_readback=final_readback(
                sha=FOREIGN, at=T0 + timedelta(seconds=5),
            ),
        )
        self.assertUnattested(
            before, FixtureBarrierStateV2.CONSISTENT_CLAIMS_UNATTESTED,
        )
        self.assertUnattested(
            after, FixtureBarrierStateV2.FINAL_REF_CHANGED_OR_UNKNOWN,
        )
        # The earlier immutable report has no expiry or lease / latest-head
        # evidence; its authorizations must remain False forever.
        self.assertFalse(before.licensed_drive_read_authorized)
        self.assertEqual(before.candidate_sha, CANDIDATE)

    def test_drive_object_claim_changes_after_cached_observation(self):
        original = inspect()
        changed = inspect(
            drive=replace(
                drive(), content_digest="d" * 64,
                observed_at_utc=T0 + timedelta(seconds=4),
            ),
            final_readback=final_readback(at=T0 + timedelta(seconds=5)),
        )
        self.assertUnattested(
            original, FixtureBarrierStateV2.CONSISTENT_CLAIMS_UNATTESTED,
        )
        self.assertUnattested(
            changed, FixtureBarrierStateV2.DRIVE_OBJECT_DIGEST_MISMATCH,
        )
        # A read of claimed object metadata at T0+3 cannot guarantee that
        # the remote object remains immutable/reachable after T0+4.

    def test_reader_floor_has_no_partition_id_and_can_be_reused_across_claims(self):
        # The existing *fixture floor* does not carry partition or owner
        # identity. A low floor for A can be handed to unrelated B and the
        # shape verifier cannot detect the misbinding. No production rights
        # are granted by either path.
        self.assertNotIn(
            "partition_digest", {f.name for f in fields(FixtureReaderFloorV2)},
        )
        old_floor = floor(generation=1, manifest=M)
        new_partition = "e" * 64
        p = replace(proposal(), partition_digest=new_partition)
        c = replace(commit(), partition_digest=new_partition)
        d = replace(drive(), partition_digest=new_partition)
        first = inspect(reader_floor=old_floor)
        second = inspect(
            proposal=p,
            readback=replace(readback(), branch_name=p.branch_name),
            commit=c, drive=d,
            final_readback=replace(
                final_readback(), branch_name=p.branch_name,
            ),
            reader_floor=old_floor,
        )
        self.assertUnattested(
            first, FixtureBarrierStateV2.CONSISTENT_CLAIMS_UNATTESTED,
        )
        self.assertUnattested(
            second, FixtureBarrierStateV2.CONSISTENT_CLAIMS_UNATTESTED,
        )
        self.assertNotEqual(P, new_partition)

    def test_stale_final_observation_must_not_count_as_post_drive_verification(self):
        stale = inspect(
            final_readback=final_readback(
                at=T0 + timedelta(seconds=2),
            ),
        )
        self.assertUnattested(
            stale, FixtureBarrierStateV2.FINAL_REF_READBACK_STALE,
        )
        current_claim = inspect()
        self.assertUnattested(
            current_claim, FixtureBarrierStateV2.CONSISTENT_CLAIMS_UNATTESTED,
        )
        self.assertFalse(current_claim.distributed_atomicity_verified)

    def test_downgraded_caller_floor_and_no_floor_leave_claims_unattested(self):
        weak = inspect(reader_floor=floor(generation=1))
        none = inspect(reader_floor=None)
        strict = inspect(reader_floor=floor(generation=3))
        self.assertUnattested(
            weak, FixtureBarrierStateV2.CONSISTENT_CLAIMS_UNATTESTED,
        )
        self.assertUnattested(
            none, FixtureBarrierStateV2.CONSISTENT_CLAIMS_UNATTESTED,
        )
        self.assertUnattested(
            strict, FixtureBarrierStateV2.REPLAY_FLOOR_REJECTED,
        )
        # Caller can select whether to supply the floor. This is not an
        # independently protected monotonic accepted-head store.

    def test_same_metadata_retry_is_pure_snapshot_not_idempotent_cloud_commit(self):
        first = inspect()
        second = inspect()
        self.assertEqual(first, second)
        self.assertUnattested(
            second, FixtureBarrierStateV2.CONSISTENT_CLAIMS_UNATTESTED,
        )
        self.assertFalse(hasattr(second, "transaction_id"))
        self.assertFalse(hasattr(second, "idempotency_key"))
        # Re-evaluating claims does not write, commit, retry or recover Drive.
