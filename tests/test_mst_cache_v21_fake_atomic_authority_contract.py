"""Fake-only authority contract tests. NOT a production lock, Drive CAS, or signer.

This model demonstrates required fencing behavior independently of Google Drive.
No network, credentials, secrets, production state or real persistence.
"""
import threading
import unittest
from dataclasses import dataclass, field


class ClaimDenied(RuntimeError):
    pass


@dataclass(frozen=True)
class Ticket:
    key: str
    epoch: int
    owner: str
    # Opaque in-process marker ONLY; never a signed or network-valid token.
    marker: object = field(default_factory=object, repr=False)
    expected_version: int | None = None


class ClaimOutcomeUnknown(RuntimeError):
    """The fake commit may have succeeded although its acknowledgement was lost."""


class FakeAtomicAuthority:
    """In-memory linearized contract with a FAKE clock and FAKE availability.

    The lock, state and token secret have NO durability or cross-process safety.
    This class is kept under tests/ and must never be used to authorize Drive.
    """

    def __init__(self):
        self._mutex = threading.Lock()
        self._epochs = {}
        self._active = {}
        self._deadline = {}
        self._highwater = {}
        self._tick = 0
        self._available = True

    def _require_available(self):
        if not self._available:
            raise ClaimDenied("authority unavailable")

    def set_available(self, available):
        if type(available) is not bool:
            raise ValueError("invalid availability flag")
        with self._mutex:
            self._available = available

    def advance(self, ticks):
        """Deterministically simulate clock progression; no wall-clock claim."""
        if type(ticks) is not int or ticks <= 0:
            raise ValueError("invalid clock advance")
        with self._mutex:
            self._tick += ticks

    def claim(self, key, owner, ttl=5, expected_version=None):
        with self._mutex:
            self._require_available()
            if (type(key) is not str or not key or
                    type(owner) is not str or not owner or
                    type(ttl) is not int or ttl <= 0 or
                    (expected_version is not None and
                     (type(expected_version) is not int or expected_version <= 0))):
                raise ClaimDenied("invalid claim arguments")
            current = self._active.get(key)
            if current is not None and self._deadline[key] > self._tick:
                raise ClaimDenied("busy")
            # Even after lease expiry, never reset or reuse an epoch.
            epoch = self._epochs.get(key, 0) + 1
            self._epochs[key] = epoch
            ticket = Ticket(key, epoch, owner, expected_version=expected_version)
            self._active[key] = ticket
            self._deadline[key] = self._tick + ttl
            return ticket

    def expire(self, ticket):
        with self._mutex:
            self._require_available()
            if self._active.get(ticket.key) == ticket:
                del self._active[ticket.key]
                del self._deadline[ticket.key]

    def commit(self, ticket, source_version, lose_ack=False):
        with self._mutex:
            self._require_available()
            if (type(ticket) is not Ticket or
                    self._active.get(ticket.key) != ticket):
                raise ClaimDenied("stale fencing token")
            if self._tick >= self._deadline[ticket.key]:
                raise ClaimDenied("lease expired")
            if type(source_version) is not int or source_version <= 0:
                raise ClaimDenied("invalid source version")
            if (ticket.expected_version is not None and
                    source_version != ticket.expected_version):
                raise ClaimDenied("source version not bound to claim")
            previous = self._highwater.get(ticket.key)
            if previous is not None and source_version <= previous:
                raise ClaimDenied("replay or rollback")
            # Atomic ONLY inside this toy model. In a real system, the
            # authoritative compare-and-commit and external highwater must
            # share a durable, server-enforced transaction/fencing boundary.
            self._highwater[ticket.key] = source_version
            del self._active[ticket.key]
            del self._deadline[ticket.key]
            if lose_ack:
                raise ClaimOutcomeUnknown("commit acknowledgement lost")

    def highwater(self, key):
        with self._mutex:
            self._require_available()
            return self._highwater.get(key)


class FakeAuthorityContractTests(unittest.TestCase):
    def test_two_simultaneous_claimants_exactly_one_wins(self):
        authority = FakeAtomicAuthority()
        barrier = threading.Barrier(2)
        winners, denied = [], []
        def contender(owner):
            barrier.wait()
            try:
                winners.append(authority.claim("SSI:AAA:M5", owner))
            except ClaimDenied:
                denied.append(owner)
        threads = [threading.Thread(target=contender, args=(str(i),)) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(len(winners), 1)
        self.assertEqual(len(denied), 1)

    def test_expired_writer_cannot_commit_after_new_epoch(self):
        authority = FakeAtomicAuthority()
        old = authority.claim("SSI:AAA:M5", "old")
        authority.expire(old)
        new = authority.claim("SSI:AAA:M5", "new")
        self.assertGreater(new.epoch, old.epoch)
        with self.assertRaises(ClaimDenied):
            authority.commit(old, 11)
        authority.commit(new, 11)
        self.assertEqual(authority.highwater(new.key), 11)

    def test_replay_rejected_even_after_fresh_claim(self):
        authority = FakeAtomicAuthority()
        first = authority.claim("SSI:AAA:M5", "run1")
        authority.commit(first, 20)
        second = authority.claim("SSI:AAA:M5", "run2")
        with self.assertRaises(ClaimDenied):
            authority.commit(second, 19)
        with self.assertRaises(ClaimDenied):
            authority.commit(second, 20)
        authority.commit(second, 21)
        self.assertEqual(authority.highwater(second.key), 21)

    def test_distinct_keys_can_be_claimed_independently(self):
        authority = FakeAtomicAuthority()
        a = authority.claim("SSI:AAA:M5", "a")
        b = authority.claim("SSI:AAA:M15", "b")
        self.assertEqual(a.epoch, 1)
        self.assertEqual(b.epoch, 1)

    def test_owner_and_epoch_must_match(self):
        authority = FakeAtomicAuthority()
        real = authority.claim("SSI:AAA:M5", "run1")
        with self.assertRaises(ClaimDenied):
            authority.commit(Ticket(real.key, real.epoch, "impostor"), 1)
        with self.assertRaises(ClaimDenied):
            authority.commit(Ticket(real.key, real.epoch + 1, real.owner), 1)
        authority.commit(real, 1)


    def test_deadline_expires_without_manual_release_and_fences_old_epoch(self):
        authority = FakeAtomicAuthority()
        old = authority.claim("SSI:AAA:M5", "runA", ttl=3)
        authority.advance(3)  # exact expiry boundary must deny old commit
        with self.assertRaisesRegex(ClaimDenied, "lease expired"):
            authority.commit(old, 30)
        new = authority.claim("SSI:AAA:M5", "runB", ttl=3)
        self.assertEqual(new.epoch, old.epoch + 1)
        with self.assertRaisesRegex(ClaimDenied, "stale fencing"):
            authority.commit(old, 30)
        authority.commit(new, 30)
        self.assertEqual(authority.highwater(old.key), 30)

    def test_lost_commit_ack_must_be_reconciled_before_any_retry(self):
        authority = FakeAtomicAuthority()
        first = authority.claim("SSI:AAA:D1", "runA", expected_version=40)
        with self.assertRaises(ClaimOutcomeUnknown):
            authority.commit(first, 40, lose_ack=True)
        # In the fake model the commit took effect although caller saw error.
        self.assertEqual(authority.highwater(first.key), 40)
        with self.assertRaisesRegex(ClaimDenied, "stale fencing"):
            authority.commit(first, 40)
        newer = authority.claim(first.key, "runB", expected_version=41)
        # Version binding denies the attempted old payload before the model
        # gets to its monotonic highwater comparison. Either must fail closed.
        with self.assertRaisesRegex(ClaimDenied, "not bound"):
            authority.commit(newer, 40)
        authority.commit(newer, 41)

    def test_outage_before_commit_denies_mutation_then_recovers(self):
        authority = FakeAtomicAuthority()
        first = authority.claim("DNSE:AAA:H1", "runA", expected_version=7)
        authority.set_available(False)
        with self.assertRaisesRegex(ClaimDenied, "unavailable"):
            authority.commit(first, 7)
        with self.assertRaisesRegex(ClaimDenied, "unavailable"):
            authority.highwater(first.key)
        authority.set_available(True)
        self.assertIsNone(authority.highwater(first.key))
        authority.commit(first, 7)
        self.assertEqual(authority.highwater(first.key), 7)

    def test_same_fields_with_new_opaque_marker_cannot_forge_ticket(self):
        authority = FakeAtomicAuthority()
        real = authority.claim("VCBS:AAA:M15", "runA")
        impostor = Ticket(real.key, real.epoch, real.owner)
        with self.assertRaisesRegex(ClaimDenied, "stale fencing"):
            authority.commit(impostor, 10)
        authority.commit(real, 10)

    def test_claim_binds_source_version_and_rejects_swapped_payload(self):
        authority = FakeAtomicAuthority()
        ticket = authority.claim("SSI:AAA:M5", "runA", expected_version=19)
        with self.assertRaisesRegex(ClaimDenied, "not bound"):
            authority.commit(ticket, 20)
        authority.commit(ticket, 19)

    def test_invalid_noncanonical_version_cannot_consume_highwater(self):
        authority = FakeAtomicAuthority()
        ticket = authority.claim("SSI:AAA:M5", "runA")
        for bad in (True, False, -1, 0, 1.0, "1", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ClaimDenied):
                    authority.commit(ticket, bad)
        self.assertIsNone(authority.highwater(ticket.key))
        authority.commit(ticket, 1)

    def test_active_claim_is_busy_even_for_same_owner(self):
        authority = FakeAtomicAuthority()
        first = authority.claim("SSI:AAA:M5", "runA")
        with self.assertRaisesRegex(ClaimDenied, "busy"):
            authority.claim(first.key, "runA")
        authority.commit(first, 5)
        second = authority.claim(first.key, "runA")
        self.assertGreater(second.epoch, first.epoch)

    def test_invalid_clock_ttl_and_claim_fields_fail_closed(self):
        authority = FakeAtomicAuthority()
        for bad in (0, -1, True, 1.2):
            with self.subTest(ttl=bad):
                with self.assertRaises(ClaimDenied):
                    authority.claim("SSI:AAA:M5", "runA", ttl=bad)
        for bad in (0, True, 1.0, "2"):
            with self.subTest(source=bad):
                with self.assertRaises(ClaimDenied):
                    authority.claim("SSI:AAA:M5", "runA", expected_version=bad)
        for bad in (0, -1, True, 1.0):
            with self.assertRaises(ValueError):
                authority.advance(bad)

    def test_failure_is_isolated_by_key_and_highwater_never_decreases(self):
        authority = FakeAtomicAuthority()
        slow = authority.claim("SSI:AAA:M5", "old", ttl=2)
        independent = authority.claim("SSI:BBB:D1", "runB", ttl=10)
        authority.advance(2)
        with self.assertRaises(ClaimDenied):
            authority.commit(slow, 50)
        authority.commit(independent, 100)
        new = authority.claim("SSI:AAA:M5", "new")
        authority.commit(new, 50)
        self.assertEqual(authority.highwater("SSI:AAA:M5"), 50)
        self.assertEqual(authority.highwater("SSI:BBB:D1"), 100)


if __name__ == "__main__":
    unittest.main()
