"""Read-only GitHub M4 witness ruleset owner preflight (NOT a provisioner).

No settings changes, ref writes, Drive access, vendor input or production
authorization. Ruleset visibility and bypass metadata can vary by token.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

_REPO = "ngluonghoa/MST"
_PROPOSAL_PATH = Path("docs/MST_M4_WITNESS_RULESET_PROPOSAL_20261109.json")
_UNATTESTED = {
    "witness_authoritative": False,
    "protected_independent_floor": False,
    "distributed_two_account_cas": False,
    "vendor_entitlement_verified": False,
    "source_clock_verified": False,
    "physical_drive_cache_verified": False,
    "market_data_use_authorized": False,
    "trading_authorized": False,
}


def _types(rules):
    if not isinstance(rules, list):
        raise ValueError("RULES_NOT_ARRAY")
    kinds = [r["type"] for r in rules if type(r) is dict and type(r.get("type")) is str]
    if len(kinds) != len(rules) or len(kinds) != len(set(kinds)):
        raise ValueError("INVALID_OR_DUPLICATED_RULE_TYPES")
    return set(kinds)


def validate_proposal(proposal):
    if type(proposal) is not dict or proposal.get("schema") != "mst.m4.witness.ruleset.proposal.v1":
        raise ValueError("INVALID_PROPOSAL_SCHEMA")
    if proposal.get("repository") != _REPO or proposal.get("project") != "MST":
        raise ValueError("WRONG_REPOSITORY")
    ref = "refs/heads/mst/m4-witness/v1"
    if proposal.get("witness_ref") != ref:
        raise ValueError("WRONG_WITNESS_REF")
    if proposal.get("status") != "DRAFT_OWNER_APPROVAL_REQUIRED_NOT_APPLIED":
        raise ValueError("INVALID_PROPOSAL_STATUS")
    config = proposal.get("proposed_ruleset")
    if type(config) is not dict:
        raise ValueError("MISSING_PROPOSED_RULESET")
    if (config.get("name") != "MST - M4 Protected Witness (proposed)"
            or config.get("target") != "branch" or config.get("enforcement") != "active"):
        raise ValueError("PROPOSED_RULESET_IDENTITY_OR_ENFORCEMENT_DRIFT")
    target = config.get("conditions")
    target = target.get("ref_name") if type(target) is dict else None
    if (type(target) is not dict or target.get("include") != [ref]
            or target.get("exclude") != []):
        raise ValueError("WITNESS_EXACT_REF_SCOPE_REQUIRED")
    if config.get("bypass_actors") != []:
        raise ValueError("PROPOSAL_BYPASS_MUST_BE_EMPTY")
    if _types(config.get("rules")) != {"deletion", "non_fast_forward", "required_signatures"}:
        raise ValueError("PROPOSED_WITNESS_RULES_DRIFT")
    flags = proposal.get("guardrails")
    if type(flags) is not dict or flags.get("proposal_only") is not True:
        raise ValueError("PROPOSAL_MUST_STAY_DRY_RUN")
    for key in (
        "owner_approval_received", "branch_bootstrapped",
        "authenticated_writers_enrolled", "source_clock_attested",
        "protected_monotonic_floor_operational", "physical_drive_cache_verified",
        "published_cache_authorized", "trading_authorized",
    ):
        if flags.get(key) is not False:
            raise ValueError("PREMATURE_APPROVAL_OR_AUTHORIZATION_" + key)
    return config


def inspect_rulesets(proposal, summaries, detailed_by_id):
    """Classify live remote metadata without mistaking it for owner approval."""
    expected = validate_proposal(proposal)
    if not isinstance(summaries, list) or type(detailed_by_id) is not dict:
        raise TypeError("GITHUB_RULESET_LIST_OR_DETAILS_INVALID")
    same_name = [r for r in summaries if type(r) is dict and r.get("name") == expected["name"]]
    if len(same_name) > 1:
        raise ValueError("AMBIGUOUS_DUPLICATE_WITNESS_RULESETS")
    if not same_name:
        return {
            "status": "WITNESS_RULESET_NOT_PROVISIONED",
            "witness_ref": proposal["witness_ref"],
            "ruleset_visible": False,
            "ruleset_scope_verified": False,
            "bypass_list_verified": False,
            "owner_approval_verified": False,
            **_UNATTESTED,
        }
    summary = same_name[0]
    ident = summary.get("id")
    if type(ident) is not int or ident <= 0 or ident not in detailed_by_id:
        raise ValueError("MATCHED_RULESET_DETAIL_REQUIRED")
    actual = detailed_by_id[ident]
    if type(actual) is not dict or actual.get("id") != ident:
        raise ValueError("RULESET_DETAIL_ID_MISMATCH")
    if actual.get("source_type") != "Repository" or actual.get("source") != _REPO:
        raise ValueError("WITNESS_RULESET_WRONG_OWNER")
    if actual.get("target") != "branch" or actual.get("enforcement") != "active":
        raise ValueError("WITNESS_RULESET_NOT_ACTIVE")
    cond = actual.get("conditions")
    cond = cond.get("ref_name") if type(cond) is dict else None
    if type(cond) is not dict or cond.get("include") != [proposal["witness_ref"]] or cond.get("exclude") != []:
        raise ValueError("WITNESS_RULESET_WRONG_OR_OVERBROAD_SCOPE")
    rules = _types(actual.get("rules"))
    if not {"deletion", "non_fast_forward", "required_signatures"}.issubset(rules):
        raise ValueError("WITNESS_RULESET_PROTECTIONS_MISSING")
    if "creation" in rules or "update" in rules:
        raise ValueError("WITNESS_RULESET_FREEZES_UNENROLLED_WRITER")
    bypass = actual.get("bypass_actors")
    if bypass is not None and bypass != []:
        raise ValueError("WITNESS_RULESET_UNREVIEWED_BYPASS_ACTORS")
    if actual.get("current_user_can_bypass") not in ("never", None):
        raise ValueError("CURRENT_ACTOR_CAN_BYPASS")
    # A ruleset's existence is not evidence a branch exists, a publisher is
    # enrolled, external floor is trusted, or rights have been approved.
    return {
        "status": "WITNESS_RULESET_METADATA_MATCHED_UNATTESTED",
        "witness_ref": proposal["witness_ref"],
        "ruleset_id": ident,
        "ruleset_visible": True,
        "ruleset_scope_verified": True,
        "bypass_list_verified": bypass == [],
        "owner_approval_verified": False,
        **_UNATTESTED,
    }


def _get_json(path, token):
    req = Request(
        "https://api.github.com/repos/" + _REPO + path,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "MST-M4-Witness-ReadOnly-Preflight",
        },
    )
    with urlopen(req, timeout=15) as response:
        return json.load(response)


def main():
    if os.getenv("GITHUB_ACTIONS") != "true" or os.getenv("GITHUB_REPOSITORY") != _REPO:
        raise PermissionError("EXACT_REPO_GITHUB_ACTIONS_ONLY")
    if os.getenv("GITHUB_EVENT_NAME") != "pull_request":
        raise PermissionError("ONLY_PR_EVENT_ALLOWED")
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise PermissionError("READ_ONLY_TOKEN_REQUIRED")
    proposal = json.loads(_PROPOSAL_PATH.read_text())
    validate_proposal(proposal)
    summaries = _get_json("/rulesets", token)
    if type(summaries) is not list:
        raise ValueError("GITHUB_RULESET_LIST_NOT_AVAILABLE")
    detailed = {}
    for item in summaries:
        if type(item) is dict and item.get("name") == proposal["proposed_ruleset"]["name"]:
            ident = item.get("id")
            if type(ident) is not int:
                raise ValueError("INVALID_RULESET_ID")
            detailed[ident] = _get_json("/rulesets/" + str(ident), token)
    print(json.dumps(inspect_rulesets(proposal, summaries, detailed), sort_keys=True))


if __name__ == "__main__":
    main()
