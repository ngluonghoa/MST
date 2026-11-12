"""M4 synthetic *single-memory-witness* manifest CAS/fence/rollback lab.

No Google Drive CRUD, network, credentials, data persistence or licensed bars.
Both tickets and content digests are caller-controlled test metadata. This is
NOT distributed CAS: two witness instances cannot arbitrate a shared Drive
manifest or guarantee crash durability, freshness, entitlement or authorship.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import re

from .replay import require_utc
from .v2_cache_partition_plan import FixturePartitionV2

_HEX = re.compile(r"^[0-9a-f]{64}$")
_WRITER = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_DOMAIN = "mst.cache.manifest.v2.lab_only"


def _hash(value: str) -> str:
    if type(value) is not str or not _HEX.fullmatch(value):
        raise ValueError("Canonical SHA256 required")
    return value


def _utc(value: datetime) -> datetime:
    if type(value) is not datetime:
        raise TypeError("Explicit UTC datetime required")
    return require_utc(value)


def _writer(value: str) -> str:
    if type(value) is not str or not _WRITER.fullmatch(value):
        raise ValueError("Opaque fixture writer ID required")
    return value


@dataclass(frozen=True)
class FixtureFenceTicketV2:
    """Caller-held in-memory epoch claim; NOT a signed or durable lease."""

    partition_digest: str
    writer_id: str
    epoch: int

    def __post_init__(self) -> None:
        _hash(self.partition_digest)
        _writer(self.writer_id)
        if type(self.epoch) is not int or self.epoch < 1:
            raise ValueError("Positive integer fence epoch required")


@dataclass(frozen=True)
class FixtureManifestV2:
    """Content-addressed lab metadata, never an authorized Drive manifest."""

    partition_digest: str
    generation: int
    previous_manifest_digest: str | None
    content_digest: str
    writer_id: str
    fence_epoch: int
    written_at_utc: datetime
    recovery_of_manifest_digest: str | None = None

    def __post_init__(self) -> None:
        _hash(self.partition_digest)
        _hash(self.content_digest)
        _writer(self.writer_id)
        _utc(self.written_at_utc)
        if type(self.generation) is not int or not 1 <= self.generation <= 2**63 - 1:
            raise ValueError("Bounded positive generation required")
        if type(self.fence_epoch) is not int or self.fence_epoch < 1:
            raise ValueError("Valid fence epoch required")
        if (self.generation == 1) != (self.previous_manifest_digest is None):
            raise ValueError("Genesis must have no parent; later generations must")
        if self.previous_manifest_digest is not None:
            _hash(self.previous_manifest_digest)
        if self.recovery_of_manifest_digest is not None:
            _hash(self.recovery_of_manifest_digest)

    @property
    def digest(self) -> str:
        payload = {
            "domain": _DOMAIN, "partition": self.partition_digest,
            "generation": self.generation,
            "previous": self.previous_manifest_digest,
            "content_digest": self.content_digest,
            "writer": self.writer_id, "epoch": self.fence_epoch,
            "written_at_utc": self.written_at_utc.isoformat(timespec="microseconds"),
            "recovery_of": self.recovery_of_manifest_digest,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return sha256(raw.encode("ascii")).hexdigest()

    @property
    def live_data_authorized(self) -> bool:
        return False

    @property
    def drive_write_authorized(self) -> bool:
        return False

    @property
    def trading_authorized(self) -> bool:
        return False


class FixtureManifestWitnessV2:
    """One-process linearization test double, NEVER a distributed Drive witness.

    If a second instance is created, neither can detect that the other has
    published the same partition. A future production design MUST provide
    real independent fencing, append-only custody, writer authentication,
    crash durability, authority checks, and a Drive update coordination gate.
    """

    def __init__(self) -> None:
        self._heads: dict[str, FixtureManifestV2] = {}
        self._history: dict[str, dict[str, FixtureManifestV2]] = {}
        self._epochs: dict[str, int] = {}
        self._tickets: dict[str, FixtureFenceTicketV2] = {}
        self._sealed: set[str] = set()

    def open_fence(self, partition: FixturePartitionV2, writer_id: str) -> FixtureFenceTicketV2:
        if type(partition) is not FixturePartitionV2:
            raise TypeError("Fixture partition required")
        key = partition.digest
        _writer(writer_id)
        if key in self._sealed:
            raise PermissionError("PARTITION_SEALED_NO_MORE_FIXTURE_WRITES")
        epoch = self._epochs.get(key, 0) + 1
        ticket = FixtureFenceTicketV2(key, writer_id, epoch)
        self._epochs[key] = epoch
        self._tickets[key] = ticket
        return ticket

    def head(self, partition: FixturePartitionV2) -> FixtureManifestV2 | None:
        if type(partition) is not FixturePartitionV2:
            raise TypeError("Fixture partition required")
        return self._heads.get(partition.digest)

    def submit(
        self, partition: FixturePartitionV2, ticket: FixtureFenceTicketV2,
        manifest: FixtureManifestV2, *, expected_head_digest: str | None,
    ) -> str:
        """Compare/check/promote within ONE Python instance ONLY."""
        if type(partition) is not FixturePartitionV2:
            raise TypeError("FixturePartitionV2 required")
        if type(ticket) is not FixtureFenceTicketV2 or type(manifest) is not FixtureManifestV2:
            raise TypeError("Typed fence and manifest required")
        key = partition.digest
        if key in self._sealed:
            raise PermissionError("PARTITION_SEALED_NO_MORE_FIXTURE_WRITES")
        active = self._tickets.get(key)
        if (active is None or ticket != active or manifest.writer_id != active.writer_id
                or manifest.fence_epoch != active.epoch):
            raise PermissionError("STALE_OR_UNREGISTERED_WRITER_FENCE")
        if ticket.partition_digest != key or manifest.partition_digest != key:
            raise ValueError("CROSS_PARTITION_MANIFEST_OR_TICKET")
        current = self._heads.get(key)
        prior_digest = current.digest if current else None
        if expected_head_digest is not None:
            _hash(expected_head_digest)
        if expected_head_digest != prior_digest:
            raise ValueError("CAS_EXPECTED_HEAD_CHANGED")
        if manifest.previous_manifest_digest != prior_digest:
            raise ValueError("MANIFEST_PARENT_CHAIN_MISMATCH")
        if manifest.generation != (current.generation + 1 if current else 1):
            raise ValueError("GENERATION_MUST_INCREASE_EXACTLY_ONE")
        if current is not None and manifest.written_at_utc < current.written_at_utc:
            raise ValueError("WITNESS_TIME_CANNOT_REWIND")
        if manifest.recovery_of_manifest_digest is not None:
            history = self._history.get(key, {})
            target = history.get(manifest.recovery_of_manifest_digest)
            if target is None or target.generation >= manifest.generation:
                raise ValueError("RECOVERY_TARGET_NOT_IN_SAME_PARTITION_HISTORY")
            if manifest.content_digest != target.content_digest:
                raise ValueError("RECOVERY_CONTENT_DIGEST_MISMATCH")
        new_digest = manifest.digest
        # Single-threaded in-memory simulator: NOT an atomic Drive operation.
        self._heads[key] = manifest
        self._history.setdefault(key, {})[new_digest] = manifest
        return new_digest

    def seal(self, partition: FixturePartitionV2) -> None:
        """Synthetic revocation gate; does NOT delete remote retained data."""
        if type(partition) is not FixturePartitionV2:
            raise TypeError("FixturePartitionV2 required")
        self._sealed.add(partition.digest)
        self._tickets.pop(partition.digest, None)

    @property
    def cloud_cas_proven(self) -> bool:
        return False

    @property
    def independently_authenticated_witness(self) -> bool:
        return False

    @property
    def drive_write_authorized(self) -> bool:
        return False
