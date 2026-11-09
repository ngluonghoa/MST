"""MST A02 W3: synthetic crash/restart journal oracle and V2 read barrier.

The journal is a TEST-ONLY, UNSIGNED JSON file on an ephemeral GitHub Actions
runner. It is deliberately neither a GitHub/Drive API, protected durable
witness, transaction, cryptographic signer nor licensed market-data store.
The inherited 63 v1 source modules and all existing V2 modules stay unchanged.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from swing_trading.v2_cloud_publish_verify_lab import FixtureBarrierStateV2
from test_m4_v2_cloud_publish_verify_lab import (
    P, M, HEAD, CONTENT, FOREIGN, T0,
    drive, readback, final_readback, floor, inspect,
)


PHASES = (
    "INTENT",
    "DRIVE_STAGED",
    "GIT_REQUESTED_UNKNOWN",
    "REF_OBSERVED",
    "DRIVE_VISIBLE",
    "FINAL_REF_OBSERVED",
)


class EphemeralJournalOracle:
    """File-backed **test oracle**, NOT cross-account CAS or protected custody.

    Re-instantiating this helper from the same runner's ephemeral file
    simulates a writer-process restart, not a new GitHub Actions run.
    Its vulnerable replaceable file is a deliberate negative-path fixture.
    """

    def __init__(self, path):
        self.path = Path(path)

    def _read(self):
        return json.loads(self.path.read_text()) if self.path.exists() else {}

    def _write(self, state):
        temp = self.path.with_suffix(".next")
        temp.write_text(json.dumps(state, sort_keys=True, separators=(",", ":")))
        temp.replace(self.path)

    def begin(self, operation, partition, expected_head, content):
        if not isinstance(operation, str) or not operation:
            raise ValueError("EXPLICIT_OPERATION_ID_REQUIRED")
        claim = {
            "partition": partition, "expected_head": expected_head,
            "content": content,
        }
        state = self._read()
        if operation in state:
            old = state[operation]
            if any(old[key] != value for key, value in claim.items()):
                raise ValueError("OP_ID_COLLISION_OR_PAYLOAD_DRIFT")
            return old.copy()
        state[operation] = dict(claim, phase=PHASES[0])
        self._write(state)
        return state[operation].copy()

    def mark(self, operation, phase):
        if phase not in PHASES:
            raise ValueError("UNKNOWN_PHASE")
        state = self._read()
        if operation not in state:
            raise KeyError("NO_DURABLE_INTENT")
        if PHASES.index(phase) < PHASES.index(state[operation]["phase"]):
            raise ValueError("LOCAL_PHASE_ROLLBACK")
        state[operation]["phase"] = phase
        self._write(state)
        return state[operation].copy()

    def read(self, operation):
        return self._read()[operation].copy()

    def operations(self):
        return self._read()


class CrashRestartContractTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory(prefix="mst-ci-crash-fixture-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.path = self.root / "untrusted-ops.json"
        self.journal = EphemeralJournalOracle(self.path)
        self.operation = "fixture-op-a"
        self.journal.begin(self.operation, P, HEAD, CONTENT)

    def assertDenied(self, result, state):
        self.assertIs(result.state, state)
        self.assertFalse(result.independent_source_verified)
        self.assertFalse(result.distributed_atomicity_verified)
        self.assertFalse(result.licensed_drive_read_authorized)
        self.assertFalse(result.drive_write_authorized)
        self.assertFalse(result.trading_authorized)

    def test_six_crash_cutpoints_are_classified_by_existing_v2_barrier(self):
        # Each cutpoint runs through the ORIGINAL opt-in V2 read barrier.
        cases = (
            ("INTENT", dict(
                readback=readback(sha=HEAD), drive=drive().__class__(
                    P, M, CONTENT, False, T0,
                ), final_readback=None,
            ), FixtureBarrierStateV2.REF_NOT_PROMOTED),
            ("DRIVE_STAGED", dict(
                readback=readback(sha=HEAD),
            ), FixtureBarrierStateV2.REF_NOT_PROMOTED),
            ("GIT_REQUESTED_UNKNOWN", dict(
                final_readback=None,
            ), FixtureBarrierStateV2.FINAL_REF_READBACK_MISSING),
            ("REF_OBSERVED", dict(
                drive=drive().__class__(P, M, CONTENT, False, T0),
            ), FixtureBarrierStateV2.DRIVE_OBJECT_NOT_READY),
            ("DRIVE_VISIBLE", dict(
                final_readback=None,
            ), FixtureBarrierStateV2.FINAL_REF_READBACK_MISSING),
            ("FINAL_REF_OBSERVED", dict(),
             FixtureBarrierStateV2.CONSISTENT_CLAIMS_UNATTESTED),
        )
        for phase, changes, expected in cases:
            with self.subTest(cutpoint=phase):
                self.journal.mark(self.operation, phase)
                reloaded = EphemeralJournalOracle(self.path)
                self.assertEqual(reloaded.read(self.operation)["phase"], phase)
                self.assertDenied(inspect(**changes), expected)

    def test_restart_after_drive_stage_is_only_a_staged_orphan(self):
        self.journal.mark(self.operation, "DRIVE_STAGED")
        new_process = EphemeralJournalOracle(self.path)
        saved = new_process.begin(self.operation, P, HEAD, CONTENT)
        self.assertEqual(saved["phase"], "DRIVE_STAGED")
        self.assertDenied(
            inspect(readback=readback(sha=HEAD)),
            FixtureBarrierStateV2.REF_NOT_PROMOTED,
        )

    def test_restart_after_opaque_git_response_cannot_infer_publish(self):
        self.journal.mark(self.operation, "GIT_REQUESTED_UNKNOWN")
        loaded = EphemeralJournalOracle(self.path).read(self.operation)
        self.assertEqual(loaded["expected_head"], HEAD)
        self.assertDenied(
            inspect(final_readback=None),
            FixtureBarrierStateV2.FINAL_REF_READBACK_MISSING,
        )
        self.assertDenied(
            inspect(final_readback=final_readback(sha=FOREIGN)),
            FixtureBarrierStateV2.FINAL_REF_CHANGED_OR_UNKNOWN,
        )

    def test_restart_after_git_ref_but_before_drive_visibility_blocks_read(self):
        self.journal.mark(self.operation, "REF_OBSERVED")
        self.assertEqual(
            EphemeralJournalOracle(self.path).read(self.operation)["phase"],
            "REF_OBSERVED",
        )
        self.assertDenied(
            inspect(drive=drive().__class__(P, M, CONTENT, False, T0)),
            FixtureBarrierStateV2.DRIVE_OBJECT_NOT_READY,
        )

    def test_crash_after_final_claim_still_not_an_authenticated_receipt(self):
        self.journal.mark(self.operation, "FINAL_REF_OBSERVED")
        self.assertEqual(
            EphemeralJournalOracle(self.path).read(self.operation)["phase"],
            "FINAL_REF_OBSERVED",
        )
        self.assertDenied(
            inspect(reader_floor=floor(1)),
            FixtureBarrierStateV2.CONSISTENT_CLAIMS_UNATTESTED,
        )

    def test_same_operation_retry_is_journal_idempotent_but_not_remote_cas(self):
        self.journal.mark(self.operation, "DRIVE_STAGED")
        before = self.path.read_bytes()
        later = EphemeralJournalOracle(self.path)
        a = later.begin(self.operation, P, HEAD, CONTENT)
        b = later.mark(self.operation, "DRIVE_STAGED")
        self.assertEqual(a, b)
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(len(later.operations()), 1)
        self.assertFalse(inspect().distributed_atomicity_verified)

    def test_same_operation_new_payload_or_partition_rejected_after_restart(self):
        for partition, content in ((P, "f" * 64), ("e" * 64, CONTENT)):
            with self.subTest(partition=partition, content=content):
                with self.assertRaisesRegex(ValueError, "OP_ID_COLLISION"):
                    EphemeralJournalOracle(self.path).begin(
                        self.operation, partition, HEAD, content,
                    )
        self.assertEqual(len(self.journal.operations()), 1)

    def test_missing_intent_and_local_phase_rewind_rejected_in_fixture_model(self):
        with self.assertRaises(KeyError):
            self.journal.mark("unknown-operation", "DRIVE_STAGED")
        self.journal.mark(self.operation, "GIT_REQUESTED_UNKNOWN")
        with self.assertRaisesRegex(ValueError, "LOCAL_PHASE_ROLLBACK"):
            self.journal.mark(self.operation, "DRIVE_STAGED")
        with self.assertRaisesRegex(ValueError, "UNKNOWN_PHASE"):
            self.journal.mark(self.operation, "PRODUCTION_SUCCESS")

    def test_two_distinct_operations_same_parent_are_not_serialized(self):
        self.journal.begin("fixture-op-b", P, HEAD, "e" * 64)
        self.assertEqual(len(self.journal.operations()), 2)
        self.assertEqual(
            self.journal.read("fixture-op-a")["expected_head"],
            self.journal.read("fixture-op-b")["expected_head"],
        )
        self.assertFalse(inspect().distributed_atomicity_verified)
        # Local operation-id dedupe is not an inter-writer CAS winner election.

    def test_loss_of_replaceable_ci_journal_defeats_cross_run_durability(self):
        self.journal.mark(self.operation, "FINAL_REF_OBSERVED")
        prior = self.journal.read(self.operation)
        self.path.unlink()  # allowed in THIS UNTRUSTED test-only oracle
        new_process = EphemeralJournalOracle(self.path)
        self.assertEqual(new_process.operations(), {})
        resurrected = new_process.begin(self.operation, P, HEAD, CONTENT)
        self.assertEqual(resurrected["phase"], "INTENT")
        self.assertNotEqual(prior["phase"], resurrected["phase"])
        # A new hosted runner would not even have this temporary local file.

    def test_floor_downgrade_remains_caller_controlled_after_restart(self):
        self.journal.mark(self.operation, "DRIVE_VISIBLE")
        EphemeralJournalOracle(self.path).read(self.operation)
        self.assertDenied(
            inspect(reader_floor=floor(3)),
            FixtureBarrierStateV2.REPLAY_FLOOR_REJECTED,
        )
        self.assertDenied(
            inspect(reader_floor=floor(1)),
            FixtureBarrierStateV2.CONSISTENT_CLAIMS_UNATTESTED,
        )
        self.assertDenied(
            inspect(reader_floor=None),
            FixtureBarrierStateV2.CONSISTENT_CLAIMS_UNATTESTED,
        )
        # A trusted floor must live beyond this replaceable file and cannot
        # become optional on a new process or Actions run.
