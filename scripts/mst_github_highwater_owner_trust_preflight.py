"""§202 owner-custody preflight: structurally check provider-LIKE input only.

NO NETWORK, GitHub ref updates, IAM, app credentials, signer, vendor quote
reads, production Cache, broker or trading. GitHub list/ruleset/root records
here are caller-supplied and UNTRUSTED. A complete, apparently active ruleset
can still be disabled/bypassed by privileged actors or the provider; this
module never treats such data as independent trust or immutable storage.

For real evidence, independently authenticate GitHub read-only API origin,
repository permissions, effective branch rules, private-owner controls and
a separately anchored monotone key/ref/tip. None is implemented here.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any

from scripts.mst_github_highwater_ref_proposal import (
    GithubRefProposalDenied, verify_github_highwater_ff_reread,
)

INVENTORY_SCHEMA = "mst.cloud.owner_repo_inventory_candidate.v0.1"
REPOSITORY_SCHEMA = "mst.cloud.owner_private_repo_observation_candidate.v0.1"
RULESET_SCHEMA = "mst.cloud.highwater_effective_ruleset_candidate.v0.1"
TRUST_SCHEMA = "mst.cloud.owner_external_trust_floor_candidate.v0.1"
ENTRY_FIELDS = frozenset(("id", "full_name", "visibility"))
REPOSITORY_FIELDS = frozenset((
    "schema", "id", "full_name", "visibility", "owner_login", "archived",
))
RULESET_FIELDS = frozenset((
    "schema", "repository_id", "ref", "source_type", "target",
    "enforcement", "include", "exclude", "bypass_actors", "rules",
    "observed_read_only", "provider_origin_authenticated",
))
TRUST_FIELDS = frozenset((
    "schema", "repository_id", "ref", "external_witness_id",
    "owner_key_sha256", "key_epoch", "old_ref_sha",
    "old_checkpoint_tip_sha256", "review_status", "owner_verified",
))
REQUIRED_RULES = frozenset((
    "deletion", "non_fast_forward", "required_linear_history",
))
GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
ACCOUNT = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}\Z")
WITNESS = re.compile(r"[A-Za-z0-9_./:-]{12,120}\Z")
MAX_REPOS = 500


class OwnerTrustPreflightDenied(ValueError):
    """Only fixed sanitized errors; no token, key or source data in errors."""


def _digest(value: Any) -> str:
    try:
        b = json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            allow_nan=False, ensure_ascii=True,
        ).encode("utf-8")
    except (ValueError, TypeError, OverflowError):
        raise OwnerTrustPreflightDenied("MST_TRUST_JSON_INVALID") from None
    if not 0 < len(b) <= 8192:
        raise OwnerTrustPreflightDenied("MST_TRUST_EVIDENCE_SIZE_INVALID")
    return sha256(b).hexdigest()


def _valid_repo_entry(item: Any, owner_login: str) -> None:
    if (type(item) is not dict or set(item) != ENTRY_FIELDS
            or type(item["id"]) is not int or item["id"] <= 0
            or type(item["full_name"]) is not str
            or not item["full_name"].startswith(owner_login + "/")
            or item["full_name"].count("/") != 1
            or item["visibility"] not in ("public", "private", "internal")):
        raise OwnerTrustPreflightDenied("MST_TRUST_REPO_ENTRY_INVALID")


def review_accessible_owner_repo_inventory(
    *, owner_login: str, entries: Any, claimed_complete: Any,
) -> dict[str, Any]:
    """Assess an inventory supplied by caller, without re-querying GitHub.

    A 7/7 public repo list may establish only an observed accessible scope,
    not the global absence of a private highwater repo.
    """
    if (type(owner_login) is not str
            or ACCOUNT.fullmatch(owner_login) is None
            or type(entries) is not list
            or len(entries) > MAX_REPOS
            or claimed_complete is not True):
        raise OwnerTrustPreflightDenied("MST_TRUST_INVENTORY_INPUT_INVALID")
    seen_id: set[int] = set()
    seen_name: set[str] = set()
    private: list[str] = []
    for item in entries:
        _valid_repo_entry(item, owner_login)
        name = item["full_name"].lower()
        if name in seen_name or item["id"] in seen_id:
            raise OwnerTrustPreflightDenied("MST_TRUST_REPO_DUPLICATE")
        seen_id.add(item["id"])
        seen_name.add(name)
        if item["visibility"] == "private" and name != (
            owner_login + "/MST"
        ).lower():
            private.append(item["full_name"])
    return {
        "schema": INVENTORY_SCHEMA,
        "owner_login": owner_login,
        "caller_claimed_complete": True,
        "observed_visible_repo_count": len(entries),
        "observed_private_custody_repo_count": len(private),
        "visible_private_custody_candidates": sorted(private),
        "private_backend_candidate_visible": bool(private),
        "inventory_verified_against_authenticated_provider": False,
        "separate_owner_highwater_backend_provisioned": False,
        "highwater_write_authorized": False,
        "production_cache_published": False,
        "signals_eligible": False,
    }


def review_owner_highwater_trust_boundary(
    *, proposal: Any, pinned_proposal_sha256: str,
    expected_old_ref_observation: Any,
    owner_repo_observation: Any,
    effective_ruleset_observation: Any,
    external_trust_floor_candidate: Any,
    pinned_ruleset_sha256: str, pinned_external_floor_sha256: str,
) -> dict[str, Any]:
    """Evaluate strict candidate ruleset and owner floor, no attestation.

    Caller MUST NOT promote candidate observations to GitHub-authenticated
    proof, and user rights or actual rule effects cannot be inferred here.
    """
    try:
        verify_github_highwater_ff_reread(
            proposal, originally_prepared_proposal_sha256=pinned_proposal_sha256,
            current_ref_observation=expected_old_ref_observation,
        )
    except GithubRefProposalDenied:
        raise OwnerTrustPreflightDenied("MST_TRUST_PRIOR_PROPOSAL_INVALID") from None
    p = proposal
    repo = owner_repo_observation
    if (type(repo) is not dict or set(repo) != REPOSITORY_FIELDS
            or repo["schema"] != REPOSITORY_SCHEMA
            or type(repo["id"]) is not int or repo["id"] <= 0
            or type(repo["full_name"]) is not str
            or repo["full_name"] != p["repository"]
            or repo["visibility"] != "private"
            or repo["archived"] is not False
            or type(repo["owner_login"]) is not str
            or ACCOUNT.fullmatch(repo["owner_login"]) is None
            or repo["full_name"].split("/")[0] != repo["owner_login"]
            or repo["full_name"].lower() == "ngluonghoa/mst"):
        raise OwnerTrustPreflightDenied("MST_TRUST_PRIVATE_OWNER_REPO_INVALID")
    ruleset = effective_ruleset_observation
    if (type(ruleset) is not dict or set(ruleset) != RULESET_FIELDS
            or ruleset["schema"] != RULESET_SCHEMA
            or type(ruleset["repository_id"]) is not int
            or ruleset["repository_id"] != repo["id"]
            or ruleset["ref"] != p["ref"]
            or ruleset["source_type"] not in ("Repository", "Organization")
            or ruleset["target"] != "branch"
            or ruleset["enforcement"] != "active"
            or ruleset["observed_read_only"] is not True
            or ruleset["provider_origin_authenticated"] is not False):
        raise OwnerTrustPreflightDenied("MST_TRUST_RULESET_SCOPE_OR_ENFORCEMENT")
    # Conservative: exact ref only. No wildcards, negations or uncertain
    # matching semantics. Other active rulesets need independent review too.
    if (type(ruleset["include"]) is not list
            or ruleset["include"] != [p["ref"]]
            or type(ruleset["exclude"]) is not list
            or ruleset["exclude"] != []
            or type(ruleset["bypass_actors"]) is not list
            or ruleset["bypass_actors"] != []
            or type(ruleset["rules"]) is not list
            or len(ruleset["rules"]) != len(REQUIRED_RULES)
            or any(type(t) is not str for t in ruleset["rules"])
            or set(ruleset["rules"]) != REQUIRED_RULES):
        raise OwnerTrustPreflightDenied("MST_TRUST_RULESET_NOT_STRICT_ENOUGH")
    floor = external_trust_floor_candidate
    if (type(floor) is not dict or set(floor) != TRUST_FIELDS
            or floor["schema"] != TRUST_SCHEMA
            or type(floor["repository_id"]) is not int
            or floor["repository_id"] != repo["id"]
            or floor["ref"] != p["ref"]
            or type(floor["external_witness_id"]) is not str
            or WITNESS.fullmatch(floor["external_witness_id"]) is None
            or type(floor["owner_key_sha256"]) is not str
            or SHA.fullmatch(floor["owner_key_sha256"]) is None
            or type(floor["key_epoch"]) is not int
            or floor["key_epoch"] < 1
            or floor["old_ref_sha"] != p["expected_parent_sha"]
            or floor["old_checkpoint_tip_sha256"]
               != p["expected_tip_checkpoint_sha256"]
            or floor["review_status"] != "PENDING_EXTERNAL_AUTHENTICATION"
            or floor["owner_verified"] is not False):
        raise OwnerTrustPreflightDenied("MST_TRUST_OWNER_FLOOR_INVALID")
    if (type(pinned_ruleset_sha256) is not str
            or SHA.fullmatch(pinned_ruleset_sha256) is None
            or _digest(ruleset) != pinned_ruleset_sha256
            or type(pinned_external_floor_sha256) is not str
            or SHA.fullmatch(pinned_external_floor_sha256) is None
            or _digest(floor) != pinned_external_floor_sha256):
        raise OwnerTrustPreflightDenied("MST_TRUST_CANDIDATE_PIN_DRIFT")
    return {
        "schema": "mst.cloud.owner_custody_trust_preflight.v0.1",
        "repository_name": repo["full_name"],
        "candidate_repository_id": repo["id"],
        "candidate_old_ref_sha": p["expected_parent_sha"],
        "ruleset_types_observed_in_supplied_claim": sorted(REQUIRED_RULES),
        "no_bypass_actors_in_supplied_claim": True,
        "external_owner_root_candidate_hash": pinned_external_floor_sha256,
        "provider_authenticated_ruleset_readback": False,
        "owner_witness_proven_independent": False,
        "owner_signer_tip_epoch_proven_monotone": False,
        "administrator_override_prevented": False,
        "real_private_repo_access_confirmed": False,
        "real_remote_ref_update_or_cas_proven": False,
        "highwater_write_authorized": False,
        "cache_published": False,
        "signals_eligible": False,
    }
