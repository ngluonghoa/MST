"""M4 cloud Git-reference witness *proposal*, not a GitHub API client.

Protocol sketch for a non-force-fast-forward ref update where each candidate
commit has EXACTLY the observed prior head as its Git parent. This source
performs NO network, Drive CRUD, credentials, licensed data or ref update.
GitHub's connector expected_sha may be a client-side precheck; the server's
force=False/fast-forward rule is the actual ref ancestry guard. Whether a
specific remote update succeeded must be read back and verified separately.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re

from .replay import require_utc

_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_WRITER = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_PREFIX = "mst/m4-witness-test-only/"


def _sha(value: str, pattern: re.Pattern, label: str) -> None:
    if type(value) is not str or not pattern.fullmatch(value):
        raise ValueError(label + " must have a canonical lowercase digest")


def _utc(value: datetime) -> datetime:
    if type(value) is not datetime:
        raise TypeError("Explicit UTC datetime required")
    return require_utc(value)


@dataclass(frozen=True)
class FixtureGitRefProposalV2:
    """Preflight metadata for a hypothetical isolated Git ref update only."""

    partition_digest: str
    expected_head_sha: str
    candidate_commit_sha: str
    candidate_parent_sha: str
    manifest_digest: str
    writer_id: str
    generation: int
    proposed_at_utc: datetime

    def __post_init__(self) -> None:
        _sha(self.partition_digest, _SHA256, "Partition identity")
        for label, value in (
            ("Expected head", self.expected_head_sha),
            ("New commit", self.candidate_commit_sha),
            ("Commit parent", self.candidate_parent_sha),
        ):
            _sha(value, _SHA1, label)
        _sha(self.manifest_digest, _SHA256, "Manifest identity")
        if self.candidate_commit_sha == self.expected_head_sha:
            raise ValueError("No-op promotion cannot act as new generation")
        if self.candidate_parent_sha != self.expected_head_sha:
            raise ValueError("Candidate commit must descend directly from expected head")
        if type(self.writer_id) is not str or not _WRITER.fullmatch(self.writer_id):
            raise ValueError("Explicit opaque writer identity required")
        if type(self.generation) is not int or self.generation < 1:
            raise ValueError("Positive generation required")
        _utc(self.proposed_at_utc)

    @property
    def branch_name(self) -> str:
        """Dedicated LAB ref, not a provisioned branch or secret-free policy."""
        return _PREFIX + self.partition_digest

    @property
    def update_intent(self) -> dict[str, str | bool]:
        """Only the *shape* of a future GitHub write; never execute here."""
        return {
            "branch_name": self.branch_name,
            "sha": self.candidate_commit_sha,
            "expected_sha": self.expected_head_sha,
            "force": False,
        }

    @property
    def source_licence_authorized(self) -> bool:
        return False

    @property
    def write_enabled(self) -> bool:
        return False


@dataclass(frozen=True)
class FixtureGitRefReadbackV2:
    """Caller-supplied observation; NOT server-attested or a trusted signature."""

    branch_name: str
    observed_head_sha: str
    checked_at_utc: datetime

    def __post_init__(self) -> None:
        if type(self.branch_name) is not str or not self.branch_name.startswith(_PREFIX):
            raise ValueError("Only MST test-only ref namespace accepted")
        suffix = self.branch_name[len(_PREFIX):]
        _sha(suffix, _SHA256, "Partition ref suffix")
        _sha(self.observed_head_sha, _SHA1, "Observed head")
        _utc(self.checked_at_utc)


class FixtureRefResultV2(str, Enum):
    CANDIDATE_SHA_OBSERVED_UNATTESTED = "CANDIDATE_SHA_OBSERVED_UNATTESTED"
    OLD_SHA_STILL_OBSERVED = "OLD_SHA_STILL_OBSERVED"
    COMPETING_OR_UNKNOWN_SHA = "COMPETING_OR_UNKNOWN_SHA"


@dataclass(frozen=True)
class FixtureRefReconcileV2:
    """Readback categorization only; NEVER a real drive-publish authorization."""

    result: FixtureRefResultV2
    proposed_manifest_digest: str

    @property
    def independent_commit_lineage_verified(self) -> bool:
        return False

    @property
    def global_cas_proven(self) -> bool:
        return False

    @property
    def cloud_cache_write_authorized(self) -> bool:
        return False

    @property
    def trading_authorized(self) -> bool:
        return False


def reconcile_fixture_ref(
    proposal: FixtureGitRefProposalV2,
    readback: FixtureGitRefReadbackV2,
) -> FixtureRefReconcileV2:
    """Classify a possibly ambiguous GitHub error; NEVER infer acceptance.

    Seeing the proposed SHA after a write is insufficient: a separate,
    independently authenticated read of commit tree/parent, manifest digest,
    vendor rights, protection against external writers and Drive chunk hashes
    would still be needed for any real system.
    """
    if type(proposal) is not FixtureGitRefProposalV2:
        raise TypeError("Typed witness proposal required")
    if type(readback) is not FixtureGitRefReadbackV2:
        raise TypeError("Typed ref readback required")
    if proposal.branch_name != readback.branch_name:
        raise ValueError("CROSS_PARTITION_REF_READBACK")
    if readback.checked_at_utc < proposal.proposed_at_utc:
        raise ValueError("STANDING_OR_REWOUND_READBACK_DENIED")
    if readback.observed_head_sha == proposal.candidate_commit_sha:
        result = FixtureRefResultV2.CANDIDATE_SHA_OBSERVED_UNATTESTED
    elif readback.observed_head_sha == proposal.expected_head_sha:
        result = FixtureRefResultV2.OLD_SHA_STILL_OBSERVED
    else:
        result = FixtureRefResultV2.COMPETING_OR_UNKNOWN_SHA
    return FixtureRefReconcileV2(result, proposal.manifest_digest)
