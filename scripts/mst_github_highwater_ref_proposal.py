"""§199 no-write GitHub fast-forward highwater ref proposal diagnostic.

This module NEVER makes a GitHub API call or writes a Git ref. It checks
caller-supplied observations of a *separate private owner-controlled* repository
and the exact parent edge of a proposed single-parent commit against §197's
signed-source CAS intent. force=False is a fast-forward precondition, not an
independent proof of atomicity, private visibility, owner IAM, append-only
history, readback, durable monotonicity, or a trusted signer. No publishing.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any

from scripts.mst_highwater_cas_intent import (
    CasIntentDenied, verify_pre_submit_snapshot,
)

REF_SCHEMA = "mst.cloud.github_highwater_ref_observation.v0.1"
COMMIT_SCHEMA = "mst.cloud.github_highwater_commit_observation.v0.1"
PROPOSAL_SCHEMA = "mst.cloud.github_highwater_ff_proposal.v0.1"
REF_FIELDS = frozenset(("schema", "repository", "visibility", "ref", "sha"))
COMMIT_FIELDS = frozenset(("schema", "sha", "parents", "tree_sha"))
PROPOSAL_FIELDS = frozenset((
    "schema", "repository", "ref", "expected_parent_sha",
    "proposed_commit_sha", "proposed_tree_sha", "series_id",
    "request_id", "intent_sha256", "observed_generation",
    "proposed_generation", "expected_revision", "proposed_revision",
    "expected_tip_checkpoint_sha256", "proposed_tip_checkpoint_sha256",
    "force", "external_owner_controls_required", "remote_write_executed",
    "atomic_cas_independently_proven", "cache_published",
    "signals_eligible", "proposal_sha256",
))
GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
REPOSITORY = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}\Z"
)
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class GithubRefProposalDenied(ValueError):
    """Fixed diagnostic errors only, never print credentials or source bytes."""


def _hash(value: dict[str, Any]) -> str:
    try:
        raw = json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True, allow_nan=False,
        ).encode("utf-8")
    except (ValueError, TypeError, OverflowError):
        raise GithubRefProposalDenied("MST_FF_PROPOSAL_JSON_INVALID") from None
    if not 0 < len(raw) <= 4096:
        raise GithubRefProposalDenied("MST_FF_PROPOSAL_SIZE_INVALID")
    return sha256(raw).hexdigest()


def _ref(observed: Any, series_id: str) -> dict[str, Any]:
    if type(observed) is not dict or set(observed) != REF_FIELDS:
        raise GithubRefProposalDenied("MST_FF_REF_SCHEMA_INVALID")
    repository = observed["repository"]
    if (observed["schema"] != REF_SCHEMA
            or type(repository) is not str
            or REPOSITORY.fullmatch(repository) is None
            or repository.lower() == "ngluonghoa/mst"
            or observed["visibility"] != "private"
            or type(observed["ref"]) is not str
            or observed["ref"] != "refs/heads/highwater/" + series_id
            or type(observed["sha"]) is not str
            or GIT_SHA.fullmatch(observed["sha"]) is None
            or observed["sha"] == "0" * 40):
        raise GithubRefProposalDenied("MST_FF_REF_SCOPE_INVALID")
    return observed


def _commit(candidate: Any, old_sha: str) -> dict[str, Any]:
    if type(candidate) is not dict or set(candidate) != COMMIT_FIELDS:
        raise GithubRefProposalDenied("MST_FF_COMMIT_SCHEMA_INVALID")
    if (candidate["schema"] != COMMIT_SCHEMA
            or type(candidate["sha"]) is not str
            or GIT_SHA.fullmatch(candidate["sha"]) is None
            or candidate["sha"] in (old_sha, "0" * 40)
            or type(candidate["tree_sha"]) is not str
            or GIT_SHA.fullmatch(candidate["tree_sha"]) is None
            or candidate["tree_sha"] == "0" * 40
            or type(candidate["parents"]) is not list
            or len(candidate["parents"]) != 1
            or type(candidate["parents"][0]) is not str
            or candidate["parents"][0] != old_sha):
        raise GithubRefProposalDenied("MST_FF_NOT_SINGLE_PARENT_SUCCESSOR")
    return candidate


def prepare_github_highwater_ff_proposal(
    *, prepared_intent: Any, original_intent_sha256: str,
    original_anchor: Any, observed_ref: Any,
    expected_observed_ref_sha: str, candidate_commit: Any,
) -> dict[str, Any]:
    """Return a bounded proposal ONLY; no HTTP, Git ref update or side effects.

    Inputs are caller-provided and cannot authenticate GitHub permissions.
    Even an exactly linked proposed commit must later be fetched by immutable
    SHA, have its signed payload independently verified, and use a separately
    authorized private owner repository with protected ref and trusted tip.
    """
    try:
        verify_pre_submit_snapshot(
            prepared_intent, observed_external_anchor=original_anchor,
            expected_prepared_intent_sha256=original_intent_sha256,
        )
    except CasIntentDenied:
        raise GithubRefProposalDenied("MST_FF_CAS_INTENT_UNVERIFIED") from None
    ref = _ref(observed_ref, prepared_intent["series_id"])
    if (type(expected_observed_ref_sha) is not str
            or GIT_SHA.fullmatch(expected_observed_ref_sha) is None
            or expected_observed_ref_sha != ref["sha"]):
        raise GithubRefProposalDenied("MST_FF_OBSERVED_REF_HEAD_MISMATCH")
    commit = _commit(candidate_commit, ref["sha"])
    proposal = {
        "schema": PROPOSAL_SCHEMA,
        "repository": ref["repository"],
        "ref": ref["ref"],
        "expected_parent_sha": ref["sha"],
        "proposed_commit_sha": commit["sha"],
        "proposed_tree_sha": commit["tree_sha"],
        "series_id": prepared_intent["series_id"],
        "request_id": prepared_intent["request_id"],
        "intent_sha256": prepared_intent["intent_sha256"],
        "observed_generation": prepared_intent["observed_generation"],
        "proposed_generation": prepared_intent["proposed_generation"],
        "expected_revision": prepared_intent["expected_revision"],
        "proposed_revision": prepared_intent["proposed_revision"],
        "expected_tip_checkpoint_sha256": (
            prepared_intent["expected_tip_checkpoint_sha256"]
        ),
        "proposed_tip_checkpoint_sha256": (
            prepared_intent["proposed_tip_checkpoint_sha256"]
        ),
        "force": False,
        "external_owner_controls_required": True,
        "remote_write_executed": False,
        "atomic_cas_independently_proven": False,
        "cache_published": False,
        "signals_eligible": False,
    }
    return {**proposal, "proposal_sha256": _hash(proposal)}


def verify_github_highwater_ff_reread(
    proposal: Any, *, originally_prepared_proposal_sha256: str,
    current_ref_observation: Any,
) -> dict[str, Any]:
    """Detect stale source head; NEVER interpret reread as atomic CAS.

    A second writer can advance the same ref after this comparison; only an
    actual provider-enforced non-forced ref update can reject a sibling. Even
    that is not an immutable, independently anchored highwater guarantee.
    """
    if type(proposal) is not dict or set(proposal) != PROPOSAL_FIELDS:
        raise GithubRefProposalDenied("MST_FF_PREPARED_PROPOSAL_SCHEMA_INVALID")
    fingerprint = proposal["proposal_sha256"]
    if (type(originally_prepared_proposal_sha256) is not str
            or DIGEST.fullmatch(originally_prepared_proposal_sha256) is None
            or fingerprint != originally_prepared_proposal_sha256):
        raise GithubRefProposalDenied("MST_FF_PREPARED_PROPOSAL_REPLACED")
    unsigned = {k: v for k, v in proposal.items() if k != "proposal_sha256"}
    if (type(fingerprint) is not str or DIGEST.fullmatch(fingerprint) is None
            or fingerprint != _hash(unsigned)
            or proposal["schema"] != PROPOSAL_SCHEMA
            or proposal["force"] is not False
            or proposal["external_owner_controls_required"] is not True
            or proposal["remote_write_executed"] is not False
            or proposal["atomic_cas_independently_proven"] is not False
            or proposal["cache_published"] is not False
            or proposal["signals_eligible"] is not False
            or type(proposal["expected_parent_sha"]) is not str
            or GIT_SHA.fullmatch(proposal["expected_parent_sha"]) is None
            or type(proposal["proposed_commit_sha"]) is not str
            or GIT_SHA.fullmatch(proposal["proposed_commit_sha"]) is None
            or proposal["expected_parent_sha"] == proposal["proposed_commit_sha"]
            or type(proposal["proposed_tree_sha"]) is not str
            or GIT_SHA.fullmatch(proposal["proposed_tree_sha"]) is None
            or type(proposal["request_id"]) is not str
            or type(proposal["intent_sha256"]) is not str
            or DIGEST.fullmatch(proposal["intent_sha256"]) is None):
        raise GithubRefProposalDenied("MST_FF_PROPOSAL_INTEGRITY_INVALID")
    ref = _ref(current_ref_observation, proposal["series_id"])
    if (proposal["repository"] != ref["repository"]
            or proposal["ref"] != ref["ref"]
            or proposal["expected_parent_sha"] != ref["sha"]):
        raise GithubRefProposalDenied("MST_FF_REF_MOVED_REPREPARE_REQUIRED")
    return {
        "schema": "mst.cloud.github_highwater_ff_diagnostic.v0.1",
        "proposal_sha256": fingerprint,
        "observed_ref_sha": ref["sha"],
        "proposed_commit_sha": proposal["proposed_commit_sha"],
        "github_update_force": False,
        "owner_principal_and_permissions_verified": False,
        "candidate_commit_body_independently_verified": False,
        "remote_fast_forward_update_executed": False,
        "monotone_highwater_independently_verified": False,
        "atomic_cas_independently_proven": False,
        "cache_published": False,
        "signals_eligible": False,
    }
