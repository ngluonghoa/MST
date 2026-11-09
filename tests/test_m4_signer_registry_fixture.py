"""M4 signer enrollment/rotation/revocation synthetic-only negative controls.

Every key is created in test memory. No owner keys, source permissions, actual
vendor data, GitHub protected witnesses or Google Drive objects are touched.
"""
from dataclasses import replace
from hashlib import sha256
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.m4_signed_floor_fixture import (
    SCHEMA as RECEIPT_SCHEMA, canonical, seed_floor,
)
from scripts.m4_signer_registry_fixture import (
    GENESIS, FixtureSignerRegistry, local_registry_transition,
    verify_with_caller_registry,
)


def keypair():
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()
    return private, public


class LocalSignerRegistryFixtureTests(unittest.TestCase):
    def setUp(self):
        self.private, public = keypair()
        self.registry = FixtureSignerRegistry(
            provider="SSI",
            partition_digest="a" * 64,
            rights_policy_digest="b" * 64,
            revision=1,
            parent_registry_digest=GENESIS,
            signer_id="fixture.writer",
            key_epoch=1,
            public_key_hex=public,
            revoked=False,
            observed_at_utc="2026-01-01T01:00:00Z",
        )
        self.floor = seed_floor(self.registry.anchor)
        self.receipt = self.receipt_for(self.registry, self.floor)

    def receipt_for(self, registry, floor, **changes):
        generation = floor.generation + 1
        day = generation + 1
        value = dict(
            schema=RECEIPT_SCHEMA,
            provider=registry.provider,
            partition_digest=registry.partition_digest,
            rights_policy_digest=registry.rights_policy_digest,
            signer_id=registry.signer_id,
            key_epoch=registry.key_epoch,
            generation=generation,
            parent_receipt_digest=floor.head_receipt_digest,
            content_digest=sha256(f"synthetic-body-{generation}".encode()).hexdigest(),
            source_first_known_utc=f"2026-01-{day:02d}T01:00:00Z",
            observed_at_utc=f"2026-01-{day:02d}T02:00:00Z",
            published_at_utc=f"2026-01-{day:02d}T03:00:00Z",
            recovery_of_receipt_digest=None,
        )
        value.update(changes)
        return value

    def signed(self, receipt=None, private=None):
        receipt = self.receipt if receipt is None else receipt
        return (private or self.private).sign(canonical(receipt)).hex()

    def verify(self, registry=None, floor=None, receipt=None, private=None, pin=None):
        registry = self.registry if registry is None else registry
        floor = self.floor if floor is None else floor
        receipt = self.receipt if receipt is None else receipt
        return verify_with_caller_registry(
            receipt, self.signed(receipt, private), registry, floor,
            registry.digest if pin is None else pin,
        )

    def next_registry(self, **changes):
        proposed = replace(
            self.registry,
            revision=self.registry.revision + 1,
            parent_registry_digest=self.registry.digest,
            observed_at_utc="2026-01-03T00:00:00Z",
        )
        return replace(proposed, **changes)

    def test_signature_with_caller_registry_remains_unattested(self):
        result = self.verify()
        self.assertIn("UNATTESTED", result["status"])
        self.assertEqual(result["registry_digest"], self.registry.digest)
        self.assertEqual(result["registry_revision"], 1)
        for key in (
            "external_registry_owner_verified", "global_key_revocation_verified",
            "durable_registry_floor_verified",
            "independent_signer_custody_verified",
            "authenticated_vendor_source_clock_verified",
            "globally_durable_monotonic_floor_verified",
            "distributed_two_writer_cas_verified",
            "google_drive_byte_custody_verified",
            "licensed_market_data_authorized",
            "cache_write_authorized", "trading_authorized",
        ):
            self.assertIs(result[key], False, key)

    def test_wrong_registry_pin_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "REGISTRY_PIN_MISMATCH"):
            self.verify(pin="f" * 64)

    def test_untyped_or_malformed_registry_pin_fails(self):
        for pin in ("not-sha", "", "A" * 64, None, 42):
            with self.subTest(pin=pin), self.assertRaises(ValueError):
                self.verify(pin=pin)

    def test_valid_signature_not_accepted_after_local_revocation(self):
        revoked = self.next_registry(revoked=True)
        evidence = local_registry_transition(self.registry, revoked)
        self.assertFalse(evidence["global_key_revocation_verified"])
        with self.assertRaisesRegex(PermissionError, "REGISTRY_KEY_REVOKED"):
            self.verify(registry=revoked)

    def test_valid_consecutive_snapshot_remains_unattested(self):
        proposed = self.next_registry()
        evidence = local_registry_transition(self.registry, proposed)
        self.assertIn("UNATTESTED", evidence["status"])
        self.assertEqual(evidence["candidate_registry_digest"], proposed.digest)
        self.assertFalse(evidence["external_registry_owner_verified"])

    def test_snapshot_revision_skip_or_rewind_is_denied(self):
        for revision in (1, 3, 0, True):
            if revision in (0,):
                with self.assertRaises(ValueError):
                    self.next_registry(revision=revision)
                continue
            with self.subTest(revision=revision), self.assertRaises(ValueError):
                local_registry_transition(self.registry, self.next_registry(revision=revision))

    def test_parent_digest_mismatch_is_denied(self):
        with self.assertRaisesRegex(ValueError, "REGISTRY_PARENT_DIGEST"):
            local_registry_transition(
                self.registry, self.next_registry(parent_registry_digest="e" * 64),
            )

    def test_older_registry_timestamp_is_denied(self):
        with self.assertRaisesRegex(ValueError, "REGISTRY_OBSERVATION_CLOCK"):
            local_registry_transition(
                self.registry, self.next_registry(observed_at_utc="2025-12-31T00:00:00Z"),
            )

    def test_cross_provider_and_partition_transplant_is_denied(self):
        for change in (
            {"provider": "VCBS"},
            {"partition_digest": "c" * 64},
            {"rights_policy_digest": "d" * 64},
        ):
            with self.subTest(change=change), self.assertRaisesRegex(
                ValueError, "REGISTRY_NAMESPACE"
            ):
                local_registry_transition(self.registry, self.next_registry(**change))

    def test_signer_id_swap_requires_owner(self):
        with self.assertRaisesRegex(ValueError, "SIGNER_CHANGE_REQUIRES_OWNER"):
            local_registry_transition(
                self.registry, self.next_registry(signer_id="unknown.writer"),
            )

    def test_public_key_swap_without_new_epoch_is_denied(self):
        _, other_public = keypair()
        with self.assertRaisesRegex(ValueError, "PUBLIC_KEY_CHANGED_WITHOUT_EPOCH"):
            local_registry_transition(
                self.registry, self.next_registry(public_key_hex=other_public),
            )

    def test_epoch_increment_without_distinct_key_is_denied(self):
        with self.assertRaisesRegex(ValueError, "EPOCH_ADVANCED_WITHOUT_NEW_KEY"):
            local_registry_transition(
                self.registry, self.next_registry(key_epoch=2),
            )

    def test_epoch_skip_or_regression_is_denied(self):
        for epoch in (0, 3, True):
            if epoch == 0:
                with self.assertRaises(ValueError):
                    self.next_registry(key_epoch=epoch)
                continue
            _, pub = keypair()
            with self.subTest(epoch=epoch), self.assertRaises(ValueError):
                local_registry_transition(
                    self.registry, self.next_registry(key_epoch=epoch, public_key_hex=pub),
                )

    def test_rotation_and_revocation_together_cannot_claim_owner(self):
        _, pub = keypair()
        with self.assertRaisesRegex(PermissionError, "ROTATION_AND_REVOCATION"):
            local_registry_transition(
                self.registry,
                self.next_registry(key_epoch=2, public_key_hex=pub, revoked=True),
            )

    def test_revoked_signer_cannot_be_locally_reenabled(self):
        revoked = self.next_registry(revoked=True)
        candidate = replace(
            revoked, revision=3, parent_registry_digest=revoked.digest,
            observed_at_utc="2026-01-04T00:00:00Z", revoked=False,
        )
        with self.assertRaisesRegex(PermissionError, "REENROLLMENT"):
            local_registry_transition(revoked, candidate)

    def test_revoked_signer_cannot_be_mutated_into_new_key(self):
        revoked = self.next_registry(revoked=True)
        _, pub = keypair()
        candidate = replace(
            revoked, revision=3, parent_registry_digest=revoked.digest,
            observed_at_utc="2026-01-04T00:00:00Z",
            key_epoch=2, public_key_hex=pub,
        )
        with self.assertRaisesRegex(PermissionError, "REVOKED_SIGNER_MUTATION"):
            local_registry_transition(revoked, candidate)

    def test_two_valid_rotated_siblings_prove_no_global_registry_cas(self):
        _, pub_a = keypair()
        _, pub_b = keypair()
        a = self.next_registry(key_epoch=2, public_key_hex=pub_a)
        b = self.next_registry(key_epoch=2, public_key_hex=pub_b)
        yes_a = local_registry_transition(self.registry, a)
        yes_b = local_registry_transition(self.registry, b)
        self.assertNotEqual(a.digest, b.digest)
        self.assertEqual(a.parent_registry_digest, b.parent_registry_digest)
        self.assertFalse(yes_a["globally_durable_monotonic_floor_verified"])
        self.assertFalse(yes_b["distributed_two_writer_cas_verified"])

    def test_revocation_is_not_global_for_stale_runner_snapshot(self):
        revoked = self.next_registry(revoked=True)
        local_registry_transition(self.registry, revoked)
        stale_runner = self.verify()
        self.assertTrue(stale_runner["fixture_signature_verified_for_caller_pinned_key"])
        with self.assertRaisesRegex(PermissionError, "REGISTRY_KEY_REVOKED"):
            self.verify(registry=revoked)
        self.assertFalse(stale_runner["global_key_revocation_verified"])

    def test_registry_and_floor_reset_replays_old_signature_after_revocation(self):
        next_floor = self.verify()["next_floor"]
        second_receipt = self.receipt_for(self.registry, next_floor)
        second = self.verify(floor=next_floor, receipt=second_receipt)
        self.assertEqual(second["next_floor"].generation, 2)
        revoked = self.next_registry(revoked=True)
        local_registry_transition(self.registry, revoked)
        replayed = self.verify(floor=seed_floor(self.registry.anchor))
        self.assertEqual(replayed["next_floor"].generation, 1)
        self.assertFalse(replayed["durable_registry_floor_verified"])

    def test_rotated_key_rejects_old_signed_epoch_locally(self):
        _, new_public = keypair()
        rotated = self.next_registry(key_epoch=2, public_key_hex=new_public)
        local_registry_transition(self.registry, rotated)
        with self.assertRaisesRegex(ValueError, "SIGNER_PARTITION_POLICY_OR_EPOCH"):
            self.verify(registry=rotated, floor=seed_floor(rotated.anchor))

    def test_rotated_key_new_genesis_is_not_historical_continuity(self):
        new_private, new_public = keypair()
        rotated = self.next_registry(key_epoch=2, public_key_hex=new_public)
        local_registry_transition(self.registry, rotated)
        fresh = seed_floor(rotated.anchor)
        receipt = self.receipt_for(rotated, fresh)
        state = self.verify(
            registry=rotated, floor=fresh, receipt=receipt, private=new_private,
        )
        self.assertEqual(state["next_floor"].generation, 1)
        self.assertFalse(state["durable_registry_floor_verified"])
        self.assertFalse(state["globally_durable_monotonic_floor_verified"])

    def test_attacker_can_replace_registry_and_pin_and_self_sign(self):
        attacker, public = keypair()
        spoofed = replace(self.registry, public_key_hex=public)
        result = self.verify(
            registry=spoofed, floor=seed_floor(spoofed.anchor), private=attacker,
        )
        self.assertTrue(result["fixture_signature_verified_for_caller_pinned_key"])
        self.assertFalse(result["external_registry_owner_verified"])
        self.assertFalse(result["trading_authorized"])

    def test_signed_body_change_is_still_rejected(self):
        changed = dict(self.receipt, content_digest="e" * 64)
        sig_original = self.signed()
        with self.assertRaisesRegex(ValueError, "INVALID_SIGNATURE"):
            verify_with_caller_registry(
                changed, sig_original, self.registry, self.floor, self.registry.digest,
            )

    def test_untyped_fixture_inputs_deny(self):
        with self.assertRaises(TypeError):
            local_registry_transition(self.registry, {"revision": 2})
        with self.assertRaises(TypeError):
            verify_with_caller_registry(
                self.receipt, self.signed(), self.registry, {}, self.registry.digest,
            )

    def test_malformed_registry_constructor_fails(self):
        for change in (
            {"revoked": "no"},
            {"revision": True},
            {"observed_at_utc": "2026-01-01T01:00:00+00:00"},
            {"public_key_hex": "not-key"},
            {"provider": "FAKE"},
        ):
            with self.subTest(change=change), self.assertRaises((ValueError, TypeError)):
                replace(self.registry, **change)


if __name__ == "__main__":
    unittest.main()
