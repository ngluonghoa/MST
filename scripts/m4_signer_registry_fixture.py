"""MST M4 synthetic signer registry lifecycle — never production authority.

All registry snapshots, signer pins, clocks and floors are CALLER-SUPPLIED.
This lab checks local shape/lineage only, and deliberately proves that
key rotation, revocation and registry digests cannot attest global ownership,
durable antirollback, distributed CAS, market-data rights or Drive custody.
It performs no network access, key generation, signing or privileged writes.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from scripts.m4_signed_floor_fixture import (
    DENIED_RIGHTS, FixtureAnchor, FixtureFloor, _clock, _digest,
    canonical, verify_signed_fixture,
)

SCHEMA = "mst.m4.signer-registry.fixture.v1"
GENESIS = "0" * 64


@dataclass(frozen=True)
class FixtureSignerRegistry:
    provider: str
    partition_digest: str
    rights_policy_digest: str
    revision: int
    parent_registry_digest: str
    signer_id: str
    key_epoch: int
    public_key_hex: str
    revoked: bool
    observed_at_utc: str

    def __post_init__(self) -> None:
        # The existing fixture validates exact provider/key identity and types.
        FixtureAnchor(
            self.provider, self.partition_digest, self.rights_policy_digest,
            self.signer_id, self.key_epoch, self.public_key_hex,
        )
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("INVALID_REGISTRY_REVISION")
        _digest(self.parent_registry_digest)
        if type(self.revoked) is not bool:
            raise ValueError("STRICT_REGISTRY_REVOKED_BOOL_REQUIRED")
        _clock(self.observed_at_utc)

    @property
    def anchor(self) -> FixtureAnchor:
        return FixtureAnchor(
            self.provider, self.partition_digest, self.rights_policy_digest,
            self.signer_id, self.key_epoch, self.public_key_hex,
        )

    @property
    def digest(self) -> str:
        # Self-hash: it has NO external authenticated owner or durability.
        fields = {
            "schema": SCHEMA,
            "provider": self.provider,
            "partition_digest": self.partition_digest,
            "rights_policy_digest": self.rights_policy_digest,
            "revision": self.revision,
            "parent_registry_digest": self.parent_registry_digest,
            "signer_id": self.signer_id,
            "key_epoch": self.key_epoch,
            "public_key_hex": self.public_key_hex,
            "revoked": self.revoked,
            "observed_at_utc": self.observed_at_utc,
        }
        return sha256(canonical(fields)).hexdigest()


def local_registry_transition(
    previous: FixtureSignerRegistry, proposed: FixtureSignerRegistry,
) -> dict[str, Any]:
    """Check sequential snapshots *given* a caller-chosen predecessor.

    A valid response is NOT approved key enrollment/rotation or revocation.
    Separate callers can choose conflicting histories with no global arbiter.
    """
    if not isinstance(previous, FixtureSignerRegistry) or not isinstance(
        proposed, FixtureSignerRegistry
    ):
        raise TypeError("TWO_TYPED_FIXTURE_REGISTRIES_REQUIRED")
    if (
        previous.provider != proposed.provider or
        previous.partition_digest != proposed.partition_digest or
        previous.rights_policy_digest != proposed.rights_policy_digest or
        previous.signer_id != proposed.signer_id
    ):
        raise ValueError("REGISTRY_NAMESPACE_OR_SIGNER_CHANGE_REQUIRES_OWNER")
    if proposed.revision != previous.revision + 1:
        raise ValueError("REGISTRY_REVISION_NOT_CONSECUTIVE")
    if proposed.parent_registry_digest != previous.digest:
        raise ValueError("REGISTRY_PARENT_DIGEST_MISMATCH")
    if _clock(proposed.observed_at_utc) <= _clock(previous.observed_at_utc):
        raise ValueError("REGISTRY_OBSERVATION_CLOCK_REGRESSION")
    if previous.revoked:
        # Deliberately conservative: local records cannot re-enroll a signer.
        if not proposed.revoked:
            raise PermissionError("REVOKED_SIGNER_REENROLLMENT_REQUIRES_OWNER")
        if (
            proposed.key_epoch != previous.key_epoch or
            proposed.public_key_hex != previous.public_key_hex
        ):
            raise PermissionError("REVOKED_SIGNER_MUTATION_REQUIRES_OWNER")
    elif proposed.revoked:
        if (
            proposed.key_epoch != previous.key_epoch or
            proposed.public_key_hex != previous.public_key_hex
        ):
            raise PermissionError("ROTATION_AND_REVOCATION_REQUIRE_OWNER")
    elif proposed.key_epoch == previous.key_epoch:
        if proposed.public_key_hex != previous.public_key_hex:
            raise ValueError("PUBLIC_KEY_CHANGED_WITHOUT_EPOCH")
    elif proposed.key_epoch == previous.key_epoch + 1:
        if proposed.public_key_hex == previous.public_key_hex:
            raise ValueError("EPOCH_ADVANCED_WITHOUT_NEW_KEY")
    else:
        raise ValueError("REGISTRY_KEY_EPOCH_REWIND_OR_SKIP")
    return {
        "status": "FIXTURE_CALLER_REGISTRY_LINEAGE_CONSISTENT_UNATTESTED",
        "candidate_registry_digest": proposed.digest,
        "external_registry_owner_verified": False,
        "global_key_revocation_verified": False,
        "durable_registry_floor_verified": False,
        **DENIED_RIGHTS,
    }


def verify_with_caller_registry(
    receipt: dict[str, Any], signature_hex: str,
    registry: FixtureSignerRegistry, floor: FixtureFloor,
    caller_pinned_registry_digest: str,
) -> dict[str, Any]:
    """Deny revoked fixture keys, verify a signed receipt only locally.

    The caller can replace BOTH registry and its matching pinned SHA; this
    cannot serve as a production trust root or an authenticated cache read.
    """
    if not isinstance(registry, FixtureSignerRegistry) or not isinstance(
        floor, FixtureFloor
    ):
        raise TypeError("REGISTRY_AND_FLOOR_MUST_BE_TYPED_FIXTURES")
    if _digest(caller_pinned_registry_digest) != registry.digest:
        raise ValueError("REGISTRY_PIN_MISMATCH")
    if registry.revoked:
        raise PermissionError("REGISTRY_KEY_REVOKED_LOCAL_DENY")
    result = verify_signed_fixture(receipt, signature_hex, registry.anchor, floor)
    return {
        **result,
        "status": "FIXTURE_CALLER_REGISTRY_AND_SIGNATURE_CONSISTENT_UNATTESTED",
        "registry_revision": registry.revision,
        "registry_digest": registry.digest,
        "external_registry_owner_verified": False,
        "global_key_revocation_verified": False,
        "durable_registry_floor_verified": False,
    }
