"""M4 cross-service publish read-barrier lab: ALL metadata invented."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import unittest

from swing_trading.v2_cloud_ref_witness_plan import (
    FixtureGitRefProposalV2, FixtureGitRefReadbackV2,
)
from swing_trading.v2_cloud_publish_verify_lab import (
    FixtureGitCommitObservationV2, FixtureDriveObjectObservationV2,
    FixtureReaderFloorV2, FixtureReadBarrierV2, FixtureBarrierStateV2,
    audit_fixture_cloud_publish,
)

T0 = datetime(2026, 11, 9, 4, tzinfo=timezone.utc)
P = "a" * 64
M = "b" * 64
CONTENT = "c" * 64
HEAD = "1" * 40
CANDIDATE = "2" * 40
TREE = "3" * 40
FOREIGN = "4" * 40


def proposal():
    return FixtureGitRefProposalV2(
        P, HEAD, CANDIDATE, HEAD, M, "fixture.writer", 2, T0,
    )


def readback(p=None, sha=CANDIDATE):
    p = proposal() if p is None else p
    return FixtureGitRefReadbackV2(
        p.branch_name, sha, T0 + timedelta(seconds=1),
    )


def final_readback(p=None, sha=CANDIDATE, at=None):
    p = proposal() if p is None else p
    return FixtureGitRefReadbackV2(
        p.branch_name, sha, T0 + timedelta(seconds=4) if at is None else at,
    )


def commit():
    return FixtureGitCommitObservationV2(
        CANDIDATE, (HEAD,), TREE, P, M, 2, T0 + timedelta(seconds=2),
    )


def drive():
    return FixtureDriveObjectObservationV2(
        P, M, CONTENT, True, T0 + timedelta(seconds=3),
    )


def floor(generation=1, manifest=M, at=None):
    return FixtureReaderFloorV2(
        generation, manifest, T0 if at is None else at,
    )


def inspect(**changes):
    parts = {
        "proposal": proposal(),
        "readback": readback(),
        "commit": commit(),
        "drive": drive(),
        "final_readback": final_readback(),
        "expected_tree_sha": TREE,
        "expected_content_sha256": CONTENT,
    }
    parts.update(changes)
    return audit_fixture_cloud_publish(**parts)


class CloudPublishNegativeTests(unittest.TestCase):
    def assertBlocked(self, result, state):
        self.assertIs(result.state, state)
        self.assertFalse(result.independent_source_verified)
        self.assertFalse(result.distributed_atomicity_verified)
        self.assertFalse(result.licensed_drive_read_authorized)
        self.assertFalse(result.drive_write_authorized)
        self.assertFalse(result.trading_authorized)

    def test_all_consistent_metadata_is_still_unattested(self):
        value = inspect()
        self.assertBlocked(value, FixtureBarrierStateV2.CONSISTENT_CLAIMS_UNATTESTED)
        self.assertEqual(value.candidate_sha, CANDIDATE)
        self.assertEqual(value.manifest_digest, M)

    def test_missing_final_ref_readback_keeps_claims_unproven(self):
        self.assertBlocked(
            inspect(final_readback=None),
            FixtureBarrierStateV2.FINAL_REF_READBACK_MISSING,
        )

    def test_final_ref_readback_before_drive_verification_is_stale(self):
        self.assertBlocked(
            inspect(final_readback=final_readback(at=T0 + timedelta(seconds=2))),
            FixtureBarrierStateV2.FINAL_REF_READBACK_STALE,
        )

    def test_final_ref_moved_to_competing_writer(self):
        self.assertBlocked(
            inspect(final_readback=final_readback(sha=FOREIGN)),
            FixtureBarrierStateV2.FINAL_REF_CHANGED_OR_UNKNOWN,
        )

    def test_final_ref_reverted_to_old_head(self):
        self.assertBlocked(
            inspect(final_readback=final_readback(sha=HEAD)),
            FixtureBarrierStateV2.FINAL_REF_CHANGED_OR_UNKNOWN,
        )

    def test_final_ref_different_partition_cannot_prove_stability(self):
        p = proposal()
        bad = FixtureGitRefReadbackV2(
            p.branch_name[:-64] + "d" * 64,
            CANDIDATE,
            T0 + timedelta(seconds=4),
        )
        with self.assertRaisesRegex(ValueError, "CROSS_PARTITION_FINAL_REF"):
            inspect(final_readback=bad)

    def test_final_ref_must_be_typed_and_bounded(self):
        for invalid in ({"observed_head_sha": CANDIDATE}, 0, False):
            with self.subTest(invalid=invalid), self.assertRaises(TypeError):
                inspect(final_readback=invalid)

    def test_old_ref_still_present_blocks_publish(self):
        self.assertBlocked(
            inspect(readback=readback(sha=HEAD)),
            FixtureBarrierStateV2.REF_NOT_PROMOTED,
        )

    def test_competing_ref_head_blocks_publish(self):
        self.assertBlocked(
            inspect(readback=readback(sha=FOREIGN)),
            FixtureBarrierStateV2.REF_COMPETING_OR_UNKNOWN,
        )

    def test_commit_sha_mismatch_denied(self):
        self.assertBlocked(
            inspect(commit=replace(commit(), commit_sha=FOREIGN)),
            FixtureBarrierStateV2.COMMIT_LINEAGE_MISMATCH,
        )

    def test_commit_parent_mismatch_denied(self):
        self.assertBlocked(
            inspect(commit=replace(commit(), parents=(FOREIGN,))),
            FixtureBarrierStateV2.COMMIT_LINEAGE_MISMATCH,
        )

    def test_octopus_merge_two_parents_not_a_witness_transition(self):
        with self.assertRaisesRegex(ValueError, "Exactly one"):
            replace(commit(), parents=(HEAD, FOREIGN))

    def test_zero_parent_commit_not_valid_transition(self):
        with self.assertRaises(ValueError):
            replace(commit(), parents=())

    def test_unknown_git_tree_does_not_authenticate_manifest(self):
        self.assertBlocked(
            inspect(commit=replace(commit(), tree_sha=FOREIGN)),
            FixtureBarrierStateV2.COMMIT_TREE_OR_PARTITION_MISMATCH,
        )

    def test_expected_git_tree_mismatch_denied(self):
        self.assertBlocked(
            inspect(expected_tree_sha=FOREIGN),
            FixtureBarrierStateV2.COMMIT_TREE_OR_PARTITION_MISMATCH,
        )

    def test_wrong_commit_partition_denied(self):
        self.assertBlocked(
            inspect(commit=replace(commit(), partition_digest="d" * 64)),
            FixtureBarrierStateV2.COMMIT_TREE_OR_PARTITION_MISMATCH,
        )

    def test_commit_manifest_digest_mismatch_denied(self):
        self.assertBlocked(
            inspect(commit=replace(commit(), manifest_digest="d" * 64)),
            FixtureBarrierStateV2.MANIFEST_OR_GENERATION_MISMATCH,
        )

    def test_wrong_generation_denied(self):
        self.assertBlocked(
            inspect(commit=replace(commit(), generation=3)),
            FixtureBarrierStateV2.MANIFEST_OR_GENERATION_MISMATCH,
        )

    def test_missing_drive_chunk_denied(self):
        self.assertBlocked(
            inspect(drive=replace(drive(), present=False)),
            FixtureBarrierStateV2.DRIVE_OBJECT_NOT_READY,
        )

    def test_wrong_drive_content_digest_denied(self):
        self.assertBlocked(
            inspect(drive=replace(drive(), content_digest="d" * 64)),
            FixtureBarrierStateV2.DRIVE_OBJECT_DIGEST_MISMATCH,
        )

    def test_wrong_drive_partition_denied(self):
        self.assertBlocked(
            inspect(drive=replace(drive(), partition_digest="d" * 64)),
            FixtureBarrierStateV2.DRIVE_OBJECT_DIGEST_MISMATCH,
        )

    def test_wrong_drive_manifest_denied(self):
        self.assertBlocked(
            inspect(drive=replace(drive(), manifest_digest="d" * 64)),
            FixtureBarrierStateV2.DRIVE_OBJECT_DIGEST_MISMATCH,
        )

    def test_reader_floor_below_generation_does_not_prove_authority(self):
        value = inspect(reader_floor=floor(1))
        self.assertBlocked(value, FixtureBarrierStateV2.CONSISTENT_CLAIMS_UNATTESTED)

    def test_generation_below_floor_is_denied(self):
        self.assertBlocked(
            inspect(reader_floor=floor(3)),
            FixtureBarrierStateV2.REPLAY_FLOOR_REJECTED,
        )

    def test_same_generation_different_manifest_is_replay_or_fork(self):
        self.assertBlocked(
            inspect(reader_floor=floor(2, "d" * 64)),
            FixtureBarrierStateV2.REPLAY_FLOOR_REJECTED,
        )

    def test_replay_floor_from_future_time_denied(self):
        self.assertBlocked(
            inspect(reader_floor=floor(2, M, T0 + timedelta(seconds=10))),
            FixtureBarrierStateV2.REPLAY_FLOOR_REJECTED,
        )

    def test_cross_partition_readback_raises_not_relabels(self):
        p = proposal()
        wrong = FixtureGitRefReadbackV2(
            p.branch_name[:-64] + "d" * 64,
            CANDIDATE, T0 + timedelta(seconds=1),
        )
        with self.assertRaisesRegex(ValueError, "CROSS_PARTITION"):
            inspect(readback=wrong)

    def test_stale_timestamps_cannot_be_laundered_as_fresh(self):
        with self.assertRaisesRegex(ValueError, "STALE_OBSERVATION"):
            inspect(drive=replace(drive(), observed_at_utc=T0 - timedelta(seconds=1)))
        with self.assertRaisesRegex(ValueError, "STALE_OBSERVATION"):
            inspect(commit=replace(commit(), observed_at_utc=T0 - timedelta(seconds=1)))

    def test_untyped_response_rejected_before_any_decision(self):
        for changes in (
            {"proposal": {"expected_sha": HEAD}},
            {"commit": {"commit_sha": CANDIDATE}},
            {"drive": None},
            {"reader_floor": {"min_generation": 2}},
        ):
            with self.subTest(changes=changes), self.assertRaises(TypeError):
                inspect(**changes)

    def test_metadata_strict_sha_and_bool_types(self):
        with self.assertRaises(ValueError):
            replace(commit(), tree_sha="Z" * 40)
        with self.assertRaises(ValueError):
            replace(drive(), content_digest="x" * 64)
        with self.assertRaises(TypeError):
            replace(drive(), present=1)
        with self.assertRaises(ValueError):
            replace(commit(), generation=True)
        with self.assertRaises(ValueError):
            FixtureReaderFloorV2(0, M, T0)

    def test_utc_only_for_commit_drive_floor(self):
        for bad in (T0.replace(tzinfo=None),
                    T0.astimezone(timezone(timedelta(hours=7)))):
            with self.subTest(timestamp=bad), self.assertRaises(ValueError):
                replace(commit(), observed_at_utc=bad)
            with self.subTest(timestamp=bad), self.assertRaises(ValueError):
                replace(drive(), observed_at_utc=bad)
            with self.subTest(timestamp=bad), self.assertRaises(ValueError):
                replace(floor(), observed_at_utc=bad)

    def test_output_is_frozen_and_cannot_self_promote(self):
        value = inspect()
        with self.assertRaises(FrozenInstanceError):
            value.state = FixtureBarrierStateV2.REF_NOT_PROMOTED
        with self.assertRaises(FrozenInstanceError):
            value.candidate_sha = HEAD
        for status in FixtureBarrierStateV2:
            with self.subTest(status=status):
                forged = FixtureReadBarrierV2(status, CANDIDATE, M)
                self.assertFalse(forged.licensed_drive_read_authorized)
                self.assertFalse(forged.drive_write_authorized)

    def test_valid_complete_claims_still_have_no_data_or_secrets(self):
        for x in (proposal(), readback(), commit(), drive(), inspect()):
            self.assertFalse(hasattr(x, "access_token"))
            self.assertFalse(hasattr(x, "ohlcv"))
            self.assertFalse(hasattr(x, "raw_payload"))


if __name__ == "__main__":
    unittest.main()
