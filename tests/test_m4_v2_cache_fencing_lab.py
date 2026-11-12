"""M4 in-memory fence/CAS simulation: NEVER a Google Drive integration test."""
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta, timezone
import unittest

from swing_trading.v2_cache_partition_plan import FixturePartitionV2
from swing_trading.v2_cache_fencing_lab import (
    FixtureFenceTicketV2, FixtureManifestV2, FixtureManifestWitnessV2,
)

NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)
A = "a" * 64
B = "b" * 64
C = "c" * 64


def partition(provider="SSI", symbol="FAKE001", timeframe="M5", basis="RAW"):
    return FixturePartitionV2(
        provider, f"fixture.{provider.lower()}.d1", symbol, timeframe,
        date(2026, 11, 9), basis, "SRCREV_A",
    )


def manifest(p, ticket, generation=1, previous=None, content=A,
             at=NOW, recovery=None):
    return FixtureManifestV2(
        p.digest, generation, previous, content, ticket.writer_id,
        ticket.epoch, at, recovery,
    )


def genesis(w, p=None, writer="runner.one"):
    p = partition() if p is None else p
    ticket = w.open_fence(p, writer)
    m = manifest(p, ticket)
    digest = w.submit(p, ticket, m, expected_head_digest=None)
    return p, ticket, m, digest


class ImmutableManifestChecks(unittest.TestCase):
    def test_fingerprint_is_deterministic_and_scoped(self):
        w = FixtureManifestWitnessV2()
        p = partition()
        t = w.open_fence(p, "runner.one")
        value = manifest(p, t)
        self.assertEqual(value.digest, manifest(p, t).digest)
        self.assertEqual(len(value.digest), 64)
        self.assertNotEqual(value.digest, manifest(p, t, content=B).digest)
        self.assertNotEqual(value.digest, manifest(p, t, at=NOW + timedelta(seconds=1)).digest)
        self.assertNotEqual(value.digest, manifest(partition("DNSE"), t).digest)

    def test_cannot_claim_any_production_permission(self):
        w = FixtureManifestWitnessV2()
        p, t, m, _ = genesis(w)
        for claim in (m.live_data_authorized, m.drive_write_authorized,
                      m.trading_authorized, w.cloud_cas_proven,
                      w.independently_authenticated_witness, w.drive_write_authorized):
            self.assertIs(claim, False)

    def test_manifest_and_ticket_fields_are_immutable(self):
        w = FixtureManifestWitnessV2()
        p, t, m, _ = genesis(w)
        with self.assertRaises(FrozenInstanceError):
            m.generation = 99
        with self.assertRaises(FrozenInstanceError):
            t.epoch = 99

    def test_generation_positive_exact_int(self):
        w = FixtureManifestWitnessV2()
        p = partition()
        t = w.open_fence(p, "runner.one")
        for bad in (-1, 0, True, 1.5, "2", 2**63):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                manifest(p, t, generation=bad)

    def test_no_parent_on_genesis_and_no_orphan_after(self):
        w = FixtureManifestWitnessV2()
        p, t, _, d1 = genesis(w)
        with self.assertRaises(ValueError):
            manifest(p, t, generation=1, previous=d1)
        with self.assertRaises(ValueError):
            manifest(p, t, generation=2, previous=None)

    def test_bad_sha_writer_and_ticket_are_rejected(self):
        p = partition()
        for bad in ("X" * 64, "", None, "a" * 63):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                FixtureFenceTicketV2(bad, "runner.one", 1)
        for bad in ("Runner Two", "../secret", "", "runner/one"):
            with self.subTest(writer=bad), self.assertRaises(ValueError):
                FixtureFenceTicketV2(p.digest, bad, 1)
        for bad in (0, True, -1, "2"):
            with self.subTest(epoch=bad), self.assertRaises(ValueError):
                FixtureFenceTicketV2(p.digest, "runner.one", bad)

    def test_nonutc_manifest_time_is_rejected(self):
        w = FixtureManifestWitnessV2()
        p = partition()
        t = w.open_fence(p, "runner.one")
        for bad in (NOW.replace(tzinfo=None),
                    NOW.astimezone(timezone(timedelta(hours=7))),
                    "2026-11-09T00:00Z"):
            with self.subTest(time=bad), self.assertRaises((TypeError, ValueError)):
                manifest(p, t, at=bad)

    def test_untrusted_content_sha_is_not_source_authentication(self):
        w = FixtureManifestWitnessV2()
        p, t, _, d1 = genesis(w)
        self.assertEqual(w.head(p).content_digest, A)
        self.assertFalse(w.independently_authenticated_witness)
        self.assertFalse(w.cloud_cas_proven)
        self.assertEqual(len(d1), 64)


class WitnessCompareAndFence(unittest.TestCase):
    def test_empty_head_and_initial_genesis(self):
        w = FixtureManifestWitnessV2()
        p = partition()
        self.assertIsNone(w.head(p))
        p, t, first, digest = genesis(w, p)
        self.assertEqual(w.head(p), first)
        self.assertEqual(w.head(p).digest, digest)
        self.assertEqual(first.generation, 1)

    def test_sequential_generation_and_parent_chain(self):
        w = FixtureManifestWitnessV2()
        p, t, one, d1 = genesis(w)
        two = manifest(p, t, 2, d1, B, NOW + timedelta(seconds=1))
        d2 = w.submit(p, t, two, expected_head_digest=d1)
        self.assertEqual(d2, two.digest)
        self.assertEqual(w.head(p).generation, 2)

    def test_compare_and_swap_rejects_stale_expected_pointer(self):
        w = FixtureManifestWitnessV2()
        p, t, _, d1 = genesis(w)
        second = manifest(p, t, 2, d1, B, NOW + timedelta(seconds=1))
        with self.assertRaisesRegex(ValueError, "CAS_EXPECTED_HEAD_CHANGED"):
            w.submit(p, t, second, expected_head_digest=None)
        self.assertEqual(w.head(p).digest, d1)

    def test_parent_mismatch_and_skipped_generation_leave_head_unchanged(self):
        w = FixtureManifestWitnessV2()
        p, t, one, d1 = genesis(w)
        for bad in (manifest(p, t, 2, B, B),
                    manifest(p, t, 3, d1, B)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                w.submit(p, t, bad, expected_head_digest=d1)
            self.assertIs(w.head(p), one)

    def test_duplicate_publish_and_old_generation_replay_denied(self):
        w = FixtureManifestWitnessV2()
        p, t, first, d1 = genesis(w)
        with self.assertRaises(ValueError):
            w.submit(p, t, first, expected_head_digest=None)
        with self.assertRaises(ValueError):
            w.submit(p, t, first, expected_head_digest=d1)
        self.assertEqual(w.head(p).digest, d1)

    def test_reissued_fence_blocks_old_writer(self):
        w = FixtureManifestWitnessV2()
        p, t1, original, d1 = genesis(w, writer="runner.old")
        t2 = w.open_fence(p, "runner.new")
        self.assertEqual(t2.epoch, t1.epoch + 1)
        old_second = manifest(p, t1, 2, d1, B, NOW + timedelta(minutes=1))
        with self.assertRaisesRegex(PermissionError, "STALE_OR_UNREGISTERED"):
            w.submit(p, t1, old_second, expected_head_digest=d1)
        new_second = manifest(p, t2, 2, d1, B, NOW + timedelta(minutes=1))
        w.submit(p, t2, new_second, expected_head_digest=d1)
        self.assertEqual(w.head(p), new_second)

    def test_cross_provider_and_ticker_writes_denied(self):
        w = FixtureManifestWitnessV2()
        p, t, first, d1 = genesis(w)
        for other in (partition("DNSE"), partition(symbol="FAKE002"),
                      partition(basis="ADJUSTED"), partition(timeframe="H1")):
            with self.subTest(other=other), self.assertRaises((PermissionError, ValueError)):
                w.submit(other, t, first, expected_head_digest=None)
            self.assertIsNone(w.head(other))
        self.assertEqual(w.head(p).digest, d1)

    def test_timestamp_regression_fails_without_mutating_head(self):
        w = FixtureManifestWitnessV2()
        p, t, original, d1 = genesis(w)
        older = manifest(p, t, 2, d1, B, NOW - timedelta(seconds=1))
        with self.assertRaisesRegex(ValueError, "WITNESS_TIME"):
            w.submit(p, t, older, expected_head_digest=d1)
        self.assertIs(w.head(p), original)

    def test_wrong_writer_or_epoch_on_manifest_fails(self):
        w = FixtureManifestWitnessV2()
        p, t, first, d1 = genesis(w)
        for candidate in (
            replace(manifest(p, t, 2, d1), writer_id="runner.other"),
            replace(manifest(p, t, 2, d1), fence_epoch=2),
        ):
            with self.subTest(candidate=candidate), self.assertRaises(PermissionError):
                w.submit(p, t, candidate, expected_head_digest=d1)
            self.assertIs(w.head(p), first)

    def test_missing_fence_and_wrong_types_are_rejected(self):
        w = FixtureManifestWitnessV2()
        p = partition()
        bad_ticket = FixtureFenceTicketV2(p.digest, "runner.one", 1)
        with self.assertRaises(PermissionError):
            w.submit(p, bad_ticket, manifest(p, bad_ticket), expected_head_digest=None)
        with self.assertRaises(TypeError):
            w.submit(p, "ticket", "manifest", expected_head_digest=None)
        with self.assertRaises(TypeError):
            w.open_fence("SSI", "runner.one")

    def test_revoke_seals_future_fences_and_updates(self):
        w = FixtureManifestWitnessV2()
        p, t, original, d1 = genesis(w)
        w.seal(p)
        with self.assertRaisesRegex(PermissionError, "PARTITION_SEALED"):
            w.open_fence(p, "runner.new")
        with self.assertRaisesRegex(PermissionError, "PARTITION_SEALED"):
            w.submit(p, t, manifest(p, t, 2, d1), expected_head_digest=d1)
        self.assertIs(w.head(p), original)


class RecoveryAndDistributedLimit(unittest.TestCase):
    def test_recovery_creates_new_generation_linked_to_current_head(self):
        w = FixtureManifestWitnessV2()
        p, t, original, d1 = genesis(w)
        second = manifest(p, t, 2, d1, B, NOW + timedelta(minutes=1))
        d2 = w.submit(p, t, second, expected_head_digest=d1)
        recovered = manifest(p, t, 3, d2, A, NOW + timedelta(minutes=2), recovery=d1)
        d3 = w.submit(p, t, recovered, expected_head_digest=d2)
        self.assertEqual(w.head(p), recovered)
        self.assertEqual(w.head(p).generation, 3)
        self.assertEqual(w.head(p).recovery_of_manifest_digest, d1)
        self.assertNotEqual(d3, d1)

    def test_recovery_rejects_unknown_target(self):
        w = FixtureManifestWitnessV2()
        p, t, original, d1 = genesis(w)
        bad = manifest(p, t, 2, d1, B, NOW + timedelta(minutes=1), recovery=C)
        with self.assertRaisesRegex(ValueError, "RECOVERY_TARGET"):
            w.submit(p, t, bad, expected_head_digest=d1)
        self.assertIs(w.head(p), original)

    def test_recovery_rejects_wrong_content_for_prior_target(self):
        w = FixtureManifestWitnessV2()
        p, t, _, d1 = genesis(w)
        second = manifest(p, t, 2, d1, B, NOW + timedelta(minutes=1))
        d2 = w.submit(p, t, second, expected_head_digest=d1)
        invalid = manifest(p, t, 3, d2, C, NOW + timedelta(minutes=2), recovery=d1)
        with self.assertRaisesRegex(ValueError, "RECOVERY_CONTENT"):
            w.submit(p, t, invalid, expected_head_digest=d2)
        self.assertEqual(w.head(p).digest, d2)

    def test_cross_partition_target_not_in_same_history(self):
        w = FixtureManifestWitnessV2()
        p, t, _, d1 = genesis(w)
        q, tq, _, dq = genesis(w, partition("DNSE"), writer="runner.dnse")
        invalid = manifest(p, t, 2, d1, A, NOW + timedelta(seconds=1), recovery=dq)
        with self.assertRaisesRegex(ValueError, "RECOVERY_TARGET"):
            w.submit(p, t, invalid, expected_head_digest=d1)
        self.assertIsNotNone(w.head(q))

    def test_two_independent_witnesses_can_disagree_which_proves_not_distributed_cas(self):
        p = partition()
        a = FixtureManifestWitnessV2()
        b = FixtureManifestWitnessV2()
        ta, tb = a.open_fence(p, "runner.a"), b.open_fence(p, "runner.b")
        da = a.submit(p, ta, manifest(p, ta, content=A), expected_head_digest=None)
        db = b.submit(p, tb, manifest(p, tb, content=B), expected_head_digest=None)
        self.assertNotEqual(da, db)
        self.assertFalse(a.cloud_cas_proven)
        self.assertFalse(b.independently_authenticated_witness)

    def test_forged_equal_ticket_is_not_an_authenticated_writer_identity(self):
        w = FixtureManifestWitnessV2()
        p, genuine, _, d1 = genesis(w)
        clone = FixtureFenceTicketV2(p.digest, genuine.writer_id, genuine.epoch)
        self.assertEqual(clone, genuine)
        self.assertFalse(w.independently_authenticated_witness)
        self.assertFalse(w.drive_write_authorized)


if __name__ == "__main__":
    unittest.main()
