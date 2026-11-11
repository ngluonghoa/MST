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


if __name__ == "__main__":
    unittest.main()
