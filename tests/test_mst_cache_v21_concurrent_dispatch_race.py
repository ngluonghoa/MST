"""Deterministic two-writer race demonstration; NO Google Drive or OAuth calls.

This test documents the unclosed concurrent writer gap in the PR23 staging
algorithm. It deliberately does not assert exactly-once or production safety.
"""
import unittest
from scripts import mst_cache_v21_staging_fictional_manual as staging


class SimulatedStage:
    """A Drive-like list/create pair with no transaction or CAS."""
    def __init__(self):
        self.objects = []

    def list_all(self):
        return tuple(self.objects)

    def create(self, run_id):
        self.objects.append(run_id)


class ConcurrentDispatchRaceTests(unittest.TestCase):
    def test_two_distinct_dispatches_can_both_pass_empty_preflight(self):
        stage = SimulatedStage()
        # Explicit schedule: both preflight reads finish before either create.
        a_snapshot = stage.list_all()
        b_snapshot = stage.list_all()
        self.assertEqual(a_snapshot, ())
        self.assertEqual(b_snapshot, ())
        if not a_snapshot:
            stage.create("dispatch-A")
        if not b_snapshot:
            stage.create("dispatch-B")
        self.assertEqual(stage.list_all(), ("dispatch-A", "dispatch-B"))
        # Both uploads can happen; post-read census can detect the conflict
        # but cannot undo a completed write. This is NOT a live Drive test.
        self.assertEqual(len(stage.list_all()), 2)

    def test_sequential_dispatch_is_rejected_by_full_folder_census(self):
        stage = SimulatedStage()
        if not stage.list_all():
            stage.create("dispatch-A")
        second_snapshot = stage.list_all()
        self.assertNotEqual(second_snapshot, ())
        self.assertEqual(stage.list_all(), ("dispatch-A",))

    def test_atomic_external_claim_would_serialize_but_is_not_implemented(self):
        claims = set()
        def claim_once(key):
            if key in claims:
                return False
            claims.add(key)
            return True
        self.assertTrue(claim_once("fixture-slot"))
        self.assertFalse(claim_once("fixture-slot"))
        self.assertEqual(len(claims), 1)
        # Local set is an explanatory model, NOT Google Drive CAS.


    def test_expired_fencing_epoch_cannot_block_direct_unmediated_drive_create(self):
        stage = SimulatedStage()
        authoritative_epoch = 2
        stale_epoch = 1
        # A stale writer can call Drive files.create without passing its
        # epoch: Drive's basic upload API does not enforce this toy authority.
        stage.create("stale-writer-epoch-1")
        stale_commit_accepted = (stale_epoch == authoritative_epoch)
        self.assertFalse(stale_commit_accepted)
        self.assertEqual(stage.list_all(), ("stale-writer-epoch-1",))
        # Post-hoc authority rejection cannot undo the earlier file create.
        # This is a NEGATIVE acceptance case, not proof of protection.

    def test_after_upload_permission_failure_cannot_retract_artifact(self):
        stage = SimulatedStage()
        was_private_on_preflight = True
        self.assertTrue(was_private_on_preflight)
        stage.create("fictional-json")
        became_shared_before_postcondition = True
        pass_receipt_allowed = not became_shared_before_postcondition
        self.assertFalse(pass_receipt_allowed)
        # Fail-closed receipt cannot make a successful earlier write disappear.
        self.assertEqual(stage.list_all(), ("fictional-json",))

    def test_lost_drive_upload_ack_requires_inspection_not_fresh_dispatch(self):
        stage = SimulatedStage()
        stage.create("first-dispatch")
        acknowledgment_lost = True
        self.assertTrue(acknowledgment_lost)
        second_dispatch_snapshot = stage.list_all()
        self.assertNotEqual(second_dispatch_snapshot, ())
        if not second_dispatch_snapshot:
            stage.create("second-dispatch")
        self.assertEqual(stage.list_all(), ("first-dispatch",))
        # A rerun with new RUN_ID must not reinterpret the unknown first
        # outcome as permission to create another file.

    def test_self_consistent_drive_snapshot_can_still_be_rolled_back(self):
        # A self-consistent metadata digest plus file bytes alone can be
        # replayed together. Only trusted independent monotonic highwater
        # outside this namespace can detect an old complete snapshot.
        latest = {"version": 21, "media": b"latest", "digest": b"latest"}
        old = {"version": 20, "media": b"old", "digest": b"old"}
        self.assertEqual(latest["media"], latest["digest"])
        observed = dict(old)  # adversary replays BOTH content and metadata
        self.assertEqual(observed["media"], observed["digest"])
        independent_trusted_highwater = 21
        self.assertLess(observed["version"], independent_trusted_highwater)


if __name__ == "__main__":
    unittest.main()
