"""M4 Ed25519 fixture-only signed receipt, partition floor, anti-replay QA.

Private keys are generated in memory per test, NOT stored in GitHub, copied
to Drive, used as production signing authority, or made into credentials.
"""
from dataclasses import replace
from hashlib import sha256
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.m4_signed_floor_fixture import (
    SCHEMA, FixtureAnchor, canonical, seed_floor, verify_signed_fixture,
)


def keypair():
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()
    return priv, pub


class SignedFloorFixtureContracts(unittest.TestCase):
    def setUp(self):
        self.private, public = keypair()
        self.anchor = FixtureAnchor(
            provider="SSI", partition_digest="a" * 64,
            rights_policy_digest="b" * 64, signer_id="fixture.writer",
            key_epoch=1, public_key_hex=public,
        )
        self.base = seed_floor(self.anchor)
        self.g1 = self.make_receipt()

    def make_receipt(self, *, floor=None, content_digest=None, **fields):
        floor = self.base if floor is None else floor
        generation = floor.generation + 1
        day = generation + 1
        raw = dict(
            schema=SCHEMA, provider=self.anchor.provider,
            partition_digest=self.anchor.partition_digest,
            rights_policy_digest=self.anchor.rights_policy_digest,
            signer_id=self.anchor.signer_id, key_epoch=self.anchor.key_epoch,
            generation=generation,
            parent_receipt_digest=floor.head_receipt_digest,
            content_digest=content_digest or sha256(f"fixture-body-{generation}".encode()).hexdigest(),
            source_first_known_utc=f"2026-01-{day:02d}T01:00:00Z",
            observed_at_utc=f"2026-01-{day:02d}T02:00:00Z",
            published_at_utc=f"2026-01-{day:02d}T03:00:00Z",
            recovery_of_receipt_digest=None,
        )
        raw.update(fields)
        return raw

    def sign(self, receipt, private=None):
        return (private or self.private).sign(canonical(receipt)).hex()

    def check(self, receipt, *, floor=None, anchor=None, private=None):
        return verify_signed_fixture(
            receipt, self.sign(receipt, private),
            anchor or self.anchor, self.base if floor is None else floor,
        )

    def test_two_generation_valid_signature_chain_remains_unattested(self):
        first = self.check(self.g1)
        g2 = self.make_receipt(floor=first["next_floor"])
        second = self.check(g2, floor=first["next_floor"])
        self.assertEqual((first["next_floor"].generation, second["next_floor"].generation), (1, 2))
        self.assertEqual(g2["parent_receipt_digest"], first["receipt_digest"])
        self.assertEqual(second["next_floor"].head_receipt_digest, second["receipt_digest"])
        self.assertTrue(second["fixture_signature_verified_for_caller_pinned_key"])
        self.assertIn("UNATTESTED", second["status"])
        for field in (
            "independent_signer_custody_verified", "authenticated_vendor_source_clock_verified",
            "globally_durable_monotonic_floor_verified", "distributed_two_writer_cas_verified",
            "google_drive_byte_custody_verified", "licensed_market_data_authorized",
            "cache_write_authorized", "trading_authorized",
        ):
            self.assertIs(second[field], False)

    def test_receipt_tampered_after_signature_is_rejected(self):
        valid_sig = self.sign(self.g1)
        tampered = dict(self.g1, content_digest="c" * 64)
        with self.assertRaisesRegex(ValueError, "INVALID_SIGNATURE"):
            verify_signed_fixture(tampered, valid_sig, self.anchor, self.base)

    def test_wrong_signer_private_key_with_pinned_anchor_rejected(self):
        foreign, _ = keypair()
        with self.assertRaisesRegex(ValueError, "INVALID_SIGNATURE"):
            self.check(self.g1, private=foreign)

    def test_replacing_caller_anchor_and_floor_can_self_authorize_signature_only(self):
        foreign, foreign_pub = keypair()
        fake_anchor = replace(self.anchor, public_key_hex=foreign_pub)
        fake_floor = seed_floor(fake_anchor)
        fake = verify_signed_fixture(self.g1, self.sign(self.g1, foreign), fake_anchor, fake_floor)
        self.assertTrue(fake["fixture_signature_verified_for_caller_pinned_key"])
        self.assertFalse(fake["independent_signer_custody_verified"])
        self.assertFalse(fake["trading_authorized"])

    def test_different_partition_floor_cannot_be_reused(self):
        stale = replace(self.base, partition_digest="d" * 64)
        with self.assertRaisesRegex(ValueError, "CROSS_PARTITION_OR_EPOCH"):
            self.check(self.g1, floor=stale)

    def test_different_rights_policy_floor_cannot_be_reused(self):
        stale = replace(self.base, rights_policy_digest="d" * 64)
        with self.assertRaisesRegex(ValueError, "CROSS_PARTITION_OR_EPOCH"):
            self.check(self.g1, floor=stale)

    def test_wrong_provider_partition_and_signer_epoch_rejected(self):
        for changes in (
            dict(provider="DNSE"), dict(partition_digest="c" * 64),
            dict(rights_policy_digest="d" * 64), dict(signer_id="different"),
            dict(key_epoch=2),
        ):
            with self.subTest(changes=changes):
                candidate = dict(self.g1, **changes)
                with self.assertRaises(ValueError):
                    self.check(candidate)

    def test_wrong_key_epoch_in_floor_rejected(self):
        stale = replace(self.base, key_epoch=2)
        with self.assertRaisesRegex(ValueError, "CROSS_PARTITION_OR_EPOCH"):
            self.check(self.g1, floor=stale)

    def test_parent_head_substitution_and_generation_jump_rejected(self):
        for changes, expected in (
            (dict(parent_receipt_digest="f" * 64), "PARENT_HEAD_MISMATCH"),
            (dict(generation=3), "NON_MONOTONIC_OR_SKIPPED_GENERATION"),
            (dict(generation=True), "NON_MONOTONIC_OR_SKIPPED_GENERATION"),
        ):
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(ValueError, expected):
                    self.check(dict(self.g1, **changes))

    def test_previous_content_replay_at_higher_generation_is_denied(self):
        floor1 = self.check(self.g1)["next_floor"]
        g2 = self.make_receipt(floor=floor1, content_digest=self.g1["content_digest"])
        with self.assertRaisesRegex(ValueError, "REPLAYED_PREVIOUS_CONTENT"):
            self.check(g2, floor=floor1)

    def test_authorized_recovery_cannot_be_invented_by_signed_receipt(self):
        floor1 = self.check(self.g1)["next_floor"]
        g2 = self.make_receipt(floor=floor1, recovery_of_receipt_digest=self.g1["content_digest"])
        with self.assertRaisesRegex(ValueError, "UNAUTHORIZED_RECOVERY_REQUEST"):
            self.check(g2, floor=floor1)

    def test_source_clock_backdating_denied_even_if_resigned(self):
        floor1 = self.check(self.g1)["next_floor"]
        g2 = self.make_receipt(floor=floor1, source_first_known_utc="2026-01-01T04:00:00Z")
        with self.assertRaisesRegex(ValueError, "CLOCK_NON_MONOTONIC"):
            self.check(g2, floor=floor1)

    def test_inconsistent_observation_or_publish_clock_denied(self):
        for fields in (
            dict(source_first_known_utc="2026-01-02T05:00:00Z"),
            dict(published_at_utc="2026-01-02T01:00:00Z"),
        ):
            with self.subTest(fields=fields):
                with self.assertRaisesRegex(ValueError, "INCONSISTENT_CLOCK_ORDER"):
                    self.check(dict(self.g1, **fields))

    def test_invalid_clock_and_extra_json_field_denied(self):
        for bad in ("2026-01-02T01:00:00+00:00", "bad", "2026-99-02T01:00:00Z"):
            with self.subTest(clock=bad), self.assertRaises(ValueError):
                self.check(dict(self.g1, observed_at_utc=bad))
        with self.assertRaisesRegex(ValueError, "NON_CANONICAL_SIGNED_RECEIPT"):
            self.check(dict(self.g1, owner_approved=True))

    def test_signature_malformed_or_missing_rejected(self):
        for sig in ("", "a" * 128, "00", None):
            with self.subTest(sig=sig), self.assertRaises(ValueError):
                verify_signed_fixture(self.g1, sig, self.anchor, self.base)

    def test_two_distinct_signed_children_of_same_floor_are_locally_accepted(self):
        # Even with one pinned signer, two separately evaluated candidates
        # can fork at G1: signing alone does NOT provide global CAS.
        a = self.check(self.g1)
        b_content = sha256(b"different-blob").hexdigest()
        g1b = self.make_receipt(content_digest=b_content)
        b = self.check(g1b)
        self.assertEqual(a["next_floor"].generation, b["next_floor"].generation)
        self.assertNotEqual(a["receipt_digest"], b["receipt_digest"])
        self.assertFalse(a["distributed_two_writer_cas_verified"])
        self.assertFalse(b["distributed_two_writer_cas_verified"])
        g2_stale_parent = self.make_receipt(
            floor=a["next_floor"], parent_receipt_digest="0" * 64
        )
        with self.assertRaisesRegex(ValueError, "PARENT_HEAD_MISMATCH"):
            self.check(g2_stale_parent, floor=a["next_floor"])

    def test_replacing_ephemeral_floor_reaccepts_old_signed_receipt(self):
        floor1 = self.check(self.g1)["next_floor"]
        second = self.check(self.make_receipt(floor=floor1), floor=floor1)
        reset = seed_floor(self.anchor)
        reaccepted = self.check(self.g1, floor=reset)
        self.assertEqual(reaccepted["next_floor"].generation, 1)
        self.assertEqual(second["next_floor"].generation, 2)
        self.assertFalse(reaccepted["globally_durable_monotonic_floor_verified"])

    def test_different_content_digest_for_same_underlying_data_unprovable(self):
        # Retimestamping metadata could change a digest while underlying
        # OHLCV is stale: no vendor-signed source facts are examined here.
        floor1 = self.check(self.g1)["next_floor"]
        retimestamped = self.make_receipt(floor=floor1, content_digest="e" * 64)
        state = self.check(retimestamped, floor=floor1)
        self.assertFalse(state["authenticated_vendor_source_clock_verified"])
        self.assertFalse(state["licensed_market_data_authorized"])
