"""MST M4 owner/readiness preflight — read GitHub only, NEVER authorize.

The GitHub branch/ruleset REST API can establish what that particular token
observed. It cannot independently attest owner trust-root custody, protected
monotonic rollback floor, vendor rights, actual Drive bytes, two-account CAS
or emergency revocation. All outputs are BLOCKED even when metadata matches.

Run in read-only pull_request workflow only. No API writes, secrets exports,
signing, market data, protected branch mutations, or local dependencies.
"""
from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError

from scripts.m4_witness_ruleset_preflight import (
    _get_json, inspect_rulesets, validate_proposal,
)

_REPO = "ngluonghoa/MST"
_BASE = "4048f91beaaa3410116d97e35896c8b688384e19"
_REF = "refs/heads/mst/m4-witness/v1"
_SHA1 = re.compile(r"^[a-f0-9]{40}$")
_SOURCE = "GITHUB_REST_READ_ONLY_METADATA_FOR_THIS_TOKEN"
_GATES = (
    "SIGNED_G01_INDEPENDENT_OWNER_SIGNER_ROOT",
    "SIGNED_G02_EXTERNALLY_DURABLE_REGISTRY_RECEIPT_FLOOR",
    "SIGNED_G03_TWO_INDEPENDENT_WRITER_SERVER_ATOMIC_CAS",
    "SIGNED_G04_LICENSED_VENDOR_FIRST_KNOWN_AND_CORRECTION_RIGHTS",
    "SIGNED_G05_REAL_DRIVE_BYTES_GIT_COMMIT_AND_CRASH_RECOVERY",
    "SIGNED_G06_GLOBAL_SIGNER_REVOCATION_AND_EPOCH_FENCING",
    "SIGNED_G07_MACHINE_VERIFIABLE_INDEPENDENT_TRUST_PROVENANCE",
    "SIGNED_G08_A02_A03_M3_M4_M8_OWNER_RELEASE_APPROVALS",
)
_DENIED = {
    "independent_owner_signer_verified": False,
    "owner_approval_verified": False,
    "protected_external_monotonic_floor_verified": False,
    "authenticated_two_principal_cas_verified": False,
    "global_signer_revocation_verified": False,
    "licensed_vendor_first_known_verified": False,
    "real_google_drive_bytes_verified": False,
    "cache_read_authorized": False,
    "cache_write_authorized": False,
    "trading_authorized": False,
}


def read_only_readiness(proposal, main_branch, rulesets, details, witness_ref):
    """Evaluate REST-shaped read-only snapshot without issuing authorization.

    witness_ref is None only when GitHub returned 404. A well-formed ref may
    appear without protection. Other network/permission errors must NOT be
    misreported as absence.
    """
    validate_proposal(proposal)
    if type(main_branch) is not dict:
        raise TypeError("MAIN_BRANCH_METADATA_REQUIRED")
    if main_branch.get("name") != "main" or main_branch.get("protected") is not True:
        raise ValueError("MAIN_NOT_PROTECTED_OR_WRONG_BRANCH")
    commit = main_branch.get("commit")
    if type(commit) is not dict or commit.get("sha") != _BASE:
        raise ValueError("PINNED_SOURCE_MAIN_HEAD_DRIFT")
    policy = inspect_rulesets(proposal, rulesets, details)
    if witness_ref is None:
        witness_exists = False
        witness_sha = None
    elif type(witness_ref) is dict:
        name = witness_ref.get("ref")
        obj = witness_ref.get("object")
        if name != _REF:
            raise ValueError("WRONG_REMOTE_WITNESS_REF")
        if type(obj) is not dict or obj.get("type") != "commit":
            raise ValueError("WITNESS_GIT_OBJECT_NOT_COMMIT")
        witness_sha = obj.get("sha")
        if type(witness_sha) is not str or not _SHA1.fullmatch(witness_sha):
            raise ValueError("MALFORMED_WITNESS_HEAD_SHA")
        witness_exists = True
    else:
        raise TypeError("REMOTE_WITNESS_REF_OBJECT_OR_404_REQUIRED")

    # Stronger than a positive ruleset name: a ref might exist WITHOUT
    # a matching active/pinned policy. The caller's view may omit bypasses.
    witness_ruleset_visible = policy["ruleset_visible"]
    witness_policy_scope_visible = policy["ruleset_scope_verified"]
    witness_policy_metadata_matches = bool(
        witness_ruleset_visible and witness_policy_scope_visible
    )
    witness_policy_bypass_list_visible = policy["bypass_list_verified"]
    return {
        "schema": "mst.m4.reader-readiness.blocking-audit.v1",
        "status": "M4_READER_AND_PUBLISHER_BLOCKED_PENDING_EXTERNAL_OWNER_GATES",
        "evidence_class": _SOURCE,
        "main_baseline_verified_for_this_read": True,
        "main_head_sha": _BASE,
        "witness_ref_name": _REF,
        "witness_ref_exists_for_this_read": witness_exists,
        "witness_ref_head_sha_for_this_read": witness_sha,
        "witness_ruleset_visible_for_this_token": witness_ruleset_visible,
        "witness_ruleset_scope_visible_for_this_token": witness_policy_scope_visible,
        "witness_ruleset_metadata_matches_for_this_token": witness_policy_metadata_matches,
        "witness_bypass_list_visible_for_this_token": witness_policy_bypass_list_visible,
        "witness_actual_owner_authorization": False,
        "witness_active_protection_effective_end_to_end_verified": False,
        "owner_gates_still_open": list(_GATES),
        **_DENIED,
    }


def _get_witness_ref(token):
    try:
        return _get_json("/git/ref/heads/mst/m4-witness/v1", token)
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def main():
    if os.getenv("GITHUB_ACTIONS") != "true" or os.getenv("GITHUB_REPOSITORY") != _REPO:
        raise PermissionError("GITHUB_ACTIONS_EXACT_REPOSITORY_ONLY")
    if os.getenv("GITHUB_EVENT_NAME") != "pull_request":
        raise PermissionError("READ_ONLY_PR_EVENT_ONLY")
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise PermissionError("READ_ONLY_TOKEN_MISSING")

    from pathlib import Path

    path = Path("docs/MST_M4_WITNESS_RULESET_PROPOSAL_20261109.json")
    proposal = json.loads(path.read_text(encoding="utf-8"))
    validate_proposal(proposal)
    main_branch = _get_json("/branches/main", token)
    summaries = _get_json("/rulesets", token)
    if type(summaries) is not list:
        raise ValueError("GITHUB_RULESETS_LIST_NOT_AVAILABLE")
    details = {}
    for item in summaries:
        if type(item) is dict and item.get("name") == proposal["proposed_ruleset"]["name"]:
            ident = item.get("id")
            if type(ident) is not int or ident <= 0:
                raise ValueError("RULESET_IDENTIFIER_NOT_VERIFIABLE")
            details[ident] = _get_json("/rulesets/" + str(ident), token)
    witness = _get_witness_ref(token)
    print(json.dumps(
        read_only_readiness(proposal, main_branch, summaries, details, witness),
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
