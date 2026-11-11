"""Fake-only authority contract tests. NOT a production lock, Drive CAS, or signer.

This model demonstrates required fencing behavior independently of Google Drive.
No network, credentials, secrets, production state or real persistence.
"""
import threading
import unittest
from dataclasses import dataclass


class ClaimDenied(RuntimeError):
    pass


@dataclass(frozen=True)
class Ticket:
    key: str
    epoch: int
    owner: str


class FakeAtomicAuthority:
    """Single-process reference model; NOT safe across processes or machines."""

    def __init__(self):
        self._mutex = threading.Lock()
        self._epochs = {}
        self._active = {}
        self._highwater = {}

    def claim(self, key, owner):
        with self._mutex:
            if key in self._active:
                raise ClaimDenied("busy")
            epoch = self._epochs.get(key, 0) + 1
            self._epochs[key] = epoch
            ticket = Ticket(key, epoch, owner)
            self._active[key] = ticket
            return ticket

    def expire(self, ticket):
        with self._mutex:
            if self._active.get(ticket.key) == ticket:
                del self._active[ticket.key]

    def commit(self, ticket, source_version):
        with self._mutex:
            if self._active.get(ticket.key) != ticket:
                raise ClaimDenied("stale fencing token")
            previous = self._highwater.get(ticket.key)
            if previous is not None and source_version <= previous:
                raise ClaimDenied("replay or rollback")
            self._highwater[ticket.key] = source_version
            del self._active[ticket.key]

    def highwater(self, key):
        with self._mutex:
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


if __name__ == "__main__":
    unittest.main()
