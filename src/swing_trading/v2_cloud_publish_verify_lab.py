"""M4 offline cross-service publication read barrier — synthetic metadata only.

GitHub ref and Google Drive are separate services: this module audits the
shape of caller-supplied observations, not independently authenticated data.
Every output denies live cache reads/writes, publisher rights and trading.
No GitHub/Drive API calls or real vendor payloads appear here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re

from .replay import require_utc
from .v2_cloud_ref_witness_plan import (
    FixtureGitRefProposalV2, FixtureGitRefReadbackV2,
)

_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _hex(value: str, pattern: re.Pattern[str]) -> None:
    if type(value) is not str or not pattern.fullmatch(value):
        raise ValueError("Exact canonical lowercase digest required")


def _utc(value: datetime) -> datetime:
    if type(value) is not datetime:
        raise TypeError("Exact UTC datetime required")
    return require_utc(value)


@dataclass(frozen=True)
class FixtureGitCommitObservationV2:
    """Untrusted REST-shaped commit/tree observation, not a verified signature."""

    commit_sha: str
    parents: tuple[str, ...]
    tree_sha: str
    partition_digest: str
    manifest_digest: str
    generation: int
    observed_at_utc: datetime

    def __post_init__(self) -> None:
        _hex(self.commit_sha, _SHA1)
        if type(self.parents) is not tuple or len(self.parents) != 1:
            raise ValueError("Exactly one Git commit parent is required")
        _hex(self.parents[0], _SHA1)
        _hex(self.tree_sha, _SHA1)
        _hex(self.partition_digest, _SHA256)
        _hex(self.manifest_digest, _SHA256)
        if type(self.generation) is not int or not 1 <= self.generation <= 2**63 - 1:
            raise ValueError("Positive bounded generation required")
        _utc(self.observed_at_utc)


@dataclass(frozen=True)
class FixtureDriveObjectObservationV2:
    """Caller-claimed Drive object metadata, NOT a real Drive API receipt."""

    partition_digest: str
    manifest_digest: str
    content_digest: str
    present: bool
    observed_at_utc: datetime

    def __post_init__(self) -> None:
        _hex(self.partition_digest, _SHA256)
        _hex(self.manifest_digest, _SHA256)
        _hex(self.content_digest, _SHA256)
        if type(self.present) is not bool:
            raise TypeError("Presence must be exactly boolean")
        _utc(self.observed_at_utc)


@dataclass(frozen=True)
class FixtureReaderFloorV2:
    """Caller-claimed replay floor, NOT independently protected or durable."""

    min_generation: int
    manifest_digest: str
    observed_at_utc: datetime

    def __post_init__(self) -> None:
        if type(self.min_generation) is not int or self.min_generation < 1:
            raise ValueError("Positive replay floor required")
        _hex(self.manifest_digest, _SHA256)
        _utc(self.observed_at_utc)


class FixtureBarrierStateV2(str, Enum):
    REF_NOT_PROMOTED = "REF_NOT_PROMOTED"
    REF_COMPETING_OR_UNKNOWN = "REF_COMPETING_OR_UNKNOWN"
    COMMIT_LINEAGE_MISMATCH = "COMMIT_LINEAGE_MISMATCH"
    COMMIT_TREE_OR_PARTITION_MISMATCH = "COMMIT_TREE_OR_PARTITION_MISMATCH"
    MANIFEST_OR_GENERATION_MISMATCH = "MANIFEST_OR_GENERATION_MISMATCH"
    DRIVE_OBJECT_NOT_READY = "DRIVE_OBJECT_NOT_READY"
    DRIVE_OBJECT_DIGEST_MISMATCH = "DRIVE_OBJECT_DIGEST_MISMATCH"
    REPLAY_FLOOR_REJECTED = "REPLAY_FLOOR_REJECTED"
    FINAL_REF_READBACK_MISSING = "FINAL_REF_READBACK_MISSING"
    FINAL_REF_READBACK_STALE = "FINAL_REF_READBACK_STALE"
    FINAL_REF_CHANGED_OR_UNKNOWN = "FINAL_REF_CHANGED_OR_UNKNOWN"
    CONSISTENT_CLAIMS_UNATTESTED = "CONSISTENT_CLAIMS_UNATTESTED"


@dataclass(frozen=True)
class FixtureReadBarrierV2:
    state: FixtureBarrierStateV2
    candidate_sha: str
    manifest_digest: str

    def __post_init__(self) -> None:
        if type(self.state) is not FixtureBarrierStateV2:
            raise TypeError("Exact enum required")
        _hex(self.candidate_sha, _SHA1)
        _hex(self.manifest_digest, _SHA256)

    @property
    def independent_source_verified(self) -> bool:
        return False

    @property
    def distributed_atomicity_verified(self) -> bool:
        return False

    @property
    def licensed_drive_read_authorized(self) -> bool:
        return False

    @property
    def drive_write_authorized(self) -> bool:
        return False

    @property
    def trading_authorized(self) -> bool:
        return False


def audit_fixture_cloud_publish(
    proposal: FixtureGitRefProposalV2,
    readback: FixtureGitRefReadbackV2,
    commit: FixtureGitCommitObservationV2,
    drive: FixtureDriveObjectObservationV2,
    *,
    expected_tree_sha: str,
    expected_content_sha256: str,
    reader_floor: FixtureReaderFloorV2 | None = None,
    final_readback: FixtureGitRefReadbackV2 | None = None,
) -> FixtureReadBarrierV2:
    """Audit one synthetic publish snapshot; all results deny production use.

    Prioritized negative paths distinguish ref/fork/commit/Drive/rollback.
    Claims matching cannot prove independent GitHub, Drive or vendor custody.
    """
    if any((type(proposal) is not FixtureGitRefProposalV2,
            type(readback) is not FixtureGitRefReadbackV2,
            type(commit) is not FixtureGitCommitObservationV2,
            type(drive) is not FixtureDriveObjectObservationV2)):
        raise TypeError("Exact typed snapshot parts required")
    _hex(expected_tree_sha, _SHA1)
    _hex(expected_content_sha256, _SHA256)
    if reader_floor is not None and type(reader_floor) is not FixtureReaderFloorV2:
        raise TypeError("Typed reader floor required")
    if final_readback is not None and type(final_readback) is not FixtureGitRefReadbackV2:
        raise TypeError("Typed final Git ref readback required")
    if final_readback is not None and proposal.branch_name != final_readback.branch_name:
        raise ValueError("CROSS_PARTITION_FINAL_REF_READBACK")
    if proposal.branch_name != readback.branch_name:
        raise ValueError("CROSS_PARTITION_REF_READBACK")
    if (readback.checked_at_utc < proposal.proposed_at_utc
            or commit.observed_at_utc < proposal.proposed_at_utc
            or drive.observed_at_utc < proposal.proposed_at_utc):
        raise ValueError("STALE_OBSERVATION_CLOCK")
    if readback.observed_head_sha == proposal.expected_head_sha:
        state = FixtureBarrierStateV2.REF_NOT_PROMOTED
    elif readback.observed_head_sha != proposal.candidate_commit_sha:
        state = FixtureBarrierStateV2.REF_COMPETING_OR_UNKNOWN
    elif (commit.commit_sha != proposal.candidate_commit_sha
            or commit.parents != (proposal.expected_head_sha,)):
        state = FixtureBarrierStateV2.COMMIT_LINEAGE_MISMATCH
    elif (commit.tree_sha != expected_tree_sha
            or commit.partition_digest != proposal.partition_digest):
        state = FixtureBarrierStateV2.COMMIT_TREE_OR_PARTITION_MISMATCH
    elif (commit.manifest_digest != proposal.manifest_digest
            or commit.generation != proposal.generation):
        state = FixtureBarrierStateV2.MANIFEST_OR_GENERATION_MISMATCH
    elif not drive.present:
        state = FixtureBarrierStateV2.DRIVE_OBJECT_NOT_READY
    elif (drive.partition_digest != proposal.partition_digest
            or drive.manifest_digest != proposal.manifest_digest
            or drive.content_digest != expected_content_sha256):
        state = FixtureBarrierStateV2.DRIVE_OBJECT_DIGEST_MISMATCH
    elif reader_floor is not None and (
        commit.generation < reader_floor.min_generation
        or (commit.generation == reader_floor.min_generation
            and commit.manifest_digest != reader_floor.manifest_digest)
        or reader_floor.observed_at_utc > readback.checked_at_utc
    ):
        state = FixtureBarrierStateV2.REPLAY_FLOOR_REJECTED
    elif final_readback is None:
        state = FixtureBarrierStateV2.FINAL_REF_READBACK_MISSING
    elif final_readback.checked_at_utc < max(
        readback.checked_at_utc, commit.observed_at_utc, drive.observed_at_utc,
    ):
        state = FixtureBarrierStateV2.FINAL_REF_READBACK_STALE
    elif final_readback.observed_head_sha != proposal.candidate_commit_sha:
        state = FixtureBarrierStateV2.FINAL_REF_CHANGED_OR_UNKNOWN
    else:
        # A stable-looking second caller claim is still NOT an attestation.
        state = FixtureBarrierStateV2.CONSISTENT_CLAIMS_UNATTESTED
    return FixtureReadBarrierV2(state, proposal.candidate_commit_sha, proposal.manifest_digest)
