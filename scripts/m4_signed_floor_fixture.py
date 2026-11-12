"""M4 test-only Ed25519 receipt chain with externally PINNED-FOR-TEST signer.

This deliberately models a single caller-supplied trust anchor and an ephemeral
in-process floor. It is NOT source provenance, a verified external signer,
cross-account authorization, rollback-safe custody, GitHub CAS, Google Drive
transport, or permission to ingest market data or trade. No private keys
are stored, generated, exported or loaded by this production-facing script.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

HEX64 = re.compile(r"^[a-f0-9]{64}$")
UTC_CLOCK = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SCHEMA = "mst.m4.signed-floor.fixture.v1"
RECEIPT_KEYS = frozenset({
    "schema", "provider", "partition_digest", "rights_policy_digest",
    "signer_id", "key_epoch", "generation", "parent_receipt_digest",
    "content_digest", "source_first_known_utc", "observed_at_utc",
    "published_at_utc", "recovery_of_receipt_digest",
})
DENIED_RIGHTS = {
    "independent_signer_custody_verified": False,
    "authenticated_vendor_source_clock_verified": False,
    "globally_durable_monotonic_floor_verified": False,
    "distributed_two_writer_cas_verified": False,
    "google_drive_byte_custody_verified": False,
    "licensed_market_data_authorized": False,
    "cache_write_authorized": False,
    "trading_authorized": False,
}


def _digest(value):
    if type(value) is not str or not HEX64.fullmatch(value):
        raise ValueError("INVALID_SHA256_DIGEST")
    return value


def _clock(value):
    if type(value) is not str or not UTC_CLOCK.fullmatch(value):
        raise ValueError("STRICT_UTC_SECOND_CLOCK_REQUIRED")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as e:
        raise ValueError("INVALID_UTC_CLOCK") from e
    return parsed.replace(tzinfo=timezone.utc)


def canonical(data):
    if type(data) is not dict:
        raise TypeError("CANONICAL_DICT_REQUIRED")
    return json.dumps(data, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


@dataclass(frozen=True)
class FixtureAnchor:
    provider: str
    partition_digest: str
    rights_policy_digest: str
    signer_id: str
    key_epoch: int
    public_key_hex: str

    def __post_init__(self):
        if self.provider not in {"SSI", "DNSE", "VCBS"}:
            raise ValueError("UNAPPROVED_PROVIDER_LABEL")
        _digest(self.partition_digest)
        _digest(self.rights_policy_digest)
        if type(self.signer_id) is not str or not re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", self.signer_id):
            raise ValueError("INVALID_SIGNER_ID")
        if type(self.key_epoch) is not int or self.key_epoch < 1:
            raise ValueError("INVALID_SIGNER_EPOCH")
        if type(self.public_key_hex) is not str or not HEX64.fullmatch(self.public_key_hex):
            raise ValueError("INVALID_PUBLIC_KEY")
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(self.public_key_hex))


@dataclass(frozen=True)
class FixtureFloor:
    partition_digest: str
    rights_policy_digest: str
    signer_id: str
    key_epoch: int
    generation: int
    head_receipt_digest: str
    source_first_known_utc: str
    observed_at_utc: str
    published_at_utc: str
    seen_content_digests: tuple[str, ...]

    def __post_init__(self):
        for item in (self.partition_digest, self.rights_policy_digest,
                     self.head_receipt_digest):
            _digest(item)
        if type(self.key_epoch) is not int or self.key_epoch < 1:
            raise ValueError("INVALID_FLOOR_EPOCH")
        if type(self.generation) is not int or self.generation < 0:
            raise ValueError("INVALID_FLOOR_GENERATION")
        for item in (self.source_first_known_utc, self.observed_at_utc,
                     self.published_at_utc):
            _clock(item)
        if type(self.seen_content_digests) is not tuple:
            raise ValueError("INVALID_SEEN_CONTENT_HISTORY")
        if len(set(self.seen_content_digests)) != len(self.seen_content_digests):
            raise ValueError("DUPLICATED_CONTENT_HISTORY")
        for item in self.seen_content_digests:
            _digest(item)


def seed_floor(anchor, *, at="2026-01-01T00:00:00Z"):
    """Caller-created test floor — intentionally NOT trusted external state."""
    _clock(at)
    return FixtureFloor(anchor.partition_digest, anchor.rights_policy_digest,
                        anchor.signer_id, anchor.key_epoch, 0, "0" * 64,
                        at, at, at, ())


def verify_signed_fixture(receipt, signature_hex, anchor, floor):
    """Verify a fixture signature and its locally supplied floor, deny all rights.

    Cryptographically verifies a candidate with the TEST-CALLER'S pinned key.
    The caller can replace the key/floor: independent trust is NOT established.
    """
    if not isinstance(anchor, FixtureAnchor) or not isinstance(floor, FixtureFloor):
        raise TypeError("EXPLICIT_FIXTURE_ANCHOR_AND_FLOOR_REQUIRED")
    if type(receipt) is not dict or frozenset(receipt) != RECEIPT_KEYS:
        raise ValueError("NON_CANONICAL_SIGNED_RECEIPT")
    if receipt.get("schema") != SCHEMA or receipt.get("provider") != anchor.provider:
        raise ValueError("SOURCE_IDENTITY_MISMATCH")
    if (receipt.get("partition_digest") != anchor.partition_digest or
        receipt.get("rights_policy_digest") != anchor.rights_policy_digest or
        receipt.get("signer_id") != anchor.signer_id or
        type(receipt.get("key_epoch")) is not int or
        receipt["key_epoch"] != anchor.key_epoch):
        raise ValueError("SIGNER_PARTITION_POLICY_OR_EPOCH_MISMATCH")
    if (floor.partition_digest != anchor.partition_digest or
        floor.rights_policy_digest != anchor.rights_policy_digest or
        floor.signer_id != anchor.signer_id or floor.key_epoch != anchor.key_epoch):
        raise ValueError("CROSS_PARTITION_OR_EPOCH_FLOOR_TRANSPLANT")
    if type(signature_hex) is not str or not re.fullmatch(r"[a-f0-9]{128}", signature_hex):
        raise ValueError("INVALID_SIGNATURE_ENCODING")
    encoded = canonical(receipt)
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(anchor.public_key_hex)).verify(
            bytes.fromhex(signature_hex), encoded
        )
    except InvalidSignature as e:
        raise ValueError("INVALID_SIGNATURE_FOR_PINNED_FIXTURE_KEY") from e

    if type(receipt["generation"]) is not int or receipt["generation"] != floor.generation + 1:
        raise ValueError("NON_MONOTONIC_OR_SKIPPED_GENERATION")
    if receipt["parent_receipt_digest"] != floor.head_receipt_digest:
        raise ValueError("PARENT_HEAD_MISMATCH")
    content = _digest(receipt["content_digest"])
    _digest(receipt["parent_receipt_digest"])
    if receipt["recovery_of_receipt_digest"] is not None:
        # Any recovery requires owner authorization and independent custody;
        # it is intentionally not implemented in this test-only verifier.
        raise ValueError("UNAUTHORIZED_RECOVERY_REQUEST")
    if content in floor.seen_content_digests:
        raise ValueError("REPLAYED_PREVIOUS_CONTENT")
    first_known = _clock(receipt["source_first_known_utc"])
    observed = _clock(receipt["observed_at_utc"])
    published = _clock(receipt["published_at_utc"])
    if first_known > observed or observed > published:
        raise ValueError("INCONSISTENT_CLOCK_ORDER")
    if (first_known <= _clock(floor.source_first_known_utc) or
        observed <= _clock(floor.observed_at_utc) or
        published <= _clock(floor.published_at_utc)):
        raise ValueError("CLOCK_NON_MONOTONIC")
    digest = sha256(encoded).hexdigest()
    next_floor = FixtureFloor(
        anchor.partition_digest, anchor.rights_policy_digest, anchor.signer_id,
        anchor.key_epoch, receipt["generation"], digest,
        receipt["source_first_known_utc"], receipt["observed_at_utc"],
        receipt["published_at_utc"], floor.seen_content_digests + (content,),
    )
    return {
        "status": "FIXTURE_SIGNATURE_AND_CALLER_FLOOR_CONSISTENT_UNATTESTED",
        "fixture_signature_verified_for_caller_pinned_key": True,
        "receipt_digest": digest,
        "next_floor": next_floor,
        **DENIED_RIGHTS,
    }
