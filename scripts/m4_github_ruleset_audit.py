"""Read-only MST GitHub ruleset/ref protection audit from hosted Actions.

This checks *observed* GitHub repository metadata; it never creates refs,
tests force pushes, grants a GitHub token write scope, or publishes market
data. main protection cannot substitute for a protected M4 cache witness.
"""
from __future__ import annotations

import json
import os

from scripts.m4_github_ref_readback import _get

_REPO = "ngluonghoa/MST"
_RULESET_ID = 26801439
_BASE = "4048f91beaaa3410116d97e35896c8b688384e19"
_TEST_REFS = (
    "mst/m4-witness-test-only/race-20261109-r1",
    "mst/m4-witness-test-only/race-20261109-r2",
)
_TEST_HEADS = (
    "eb74a8c9cbfaa1fc6376b9b02ff837bfb7e7b19f",
    "3487a1c08faa404aab311ff6fff719f8ba9b8b6a",
)
_REQUIRED_CI = (
    "unittest (3.11)",
    "unittest (3.12)",
    "Contract, source-boundary and wheel checks",
)
_UNPROVEN = {
    "protected_m4_witness_ref_present": False,
    "independently_protected_rollback_floor": False,
    "force_delete_admin_bypass_tested": False,
    "two_credential_writer_cas_proven": False,
    "signed_vendor_data_source_verified": False,
    "real_drive_chunk_custody_verified": False,
    "trading_authorized": False,
}


def _has_rule(rules: list, kind: str) -> bool:
    return any(type(r) is dict and r.get("type") == kind for r in rules)


def audit_ruleset(ruleset: dict, main: dict, trial_refs: list[dict]) -> dict:
    """Fail closed on policy drift, without treating public API claims as signer proof."""
    if type(ruleset) is not dict or type(main) is not dict:
        raise TypeError("RULESET_AND_MAIN_OBJECTS_REQUIRED")
    if type(trial_refs) is not list or len(trial_refs) != len(_TEST_REFS):
        raise ValueError("EXPECTED_TWO_TEST_REFS")
    if ruleset.get("id") != _RULESET_ID or ruleset.get("name") != "MST - Protect Main":
        raise ValueError("WRONG_OR_REPLACED_RULESET")
    if (ruleset.get("target") != "branch" or ruleset.get("source_type") != "Repository" or
        ruleset.get("source") != _REPO or ruleset.get("enforcement") != "active"):
        raise ValueError("INACTIVE_OR_WRONG_RULESET_SCOPE")
    conditions = ruleset.get("conditions")
    refs = conditions.get("ref_name") if type(conditions) is dict else None
    if type(refs) is not dict or refs.get("include") != ["~DEFAULT_BRANCH"] or refs.get("exclude") != []:
        raise ValueError("RULESET_NOT_DEFAULT_BRANCH_ONLY")
    bypass = ruleset.get("bypass_actors")
    if bypass != [] or ruleset.get("current_user_can_bypass") != "never":
        raise ValueError("RULESET_BYPASS_NOT_EXCLUDED_FOR_CURRENT_ACTOR")
    rules = ruleset.get("rules")
    if type(rules) is not list:
        raise ValueError("INVALID_RULES")
    for kind in ("deletion", "non_fast_forward", "pull_request", "required_status_checks"):
        if not _has_rule(rules, kind):
            raise ValueError("MISSING_MAIN_RULE_" + kind.upper())
    req = next(x for x in rules if x.get("type") == "required_status_checks")
    parameters = req.get("parameters")
    checks = parameters.get("required_status_checks") if type(parameters) is dict else None
    if type(checks) is not list or set(
        item.get("context") for item in checks if type(item) is dict
    ) != set(_REQUIRED_CI) or len(checks) != len(_REQUIRED_CI):
        raise ValueError("REQUIRED_CI_SET_DRIFT")
    if main.get("name") != "main" or main.get("protected") is not True:
        raise ValueError("MAIN_NOT_PROTECTED")
    mcommit = main.get("commit")
    if type(mcommit) is not dict or mcommit.get("sha") != _BASE:
        raise ValueError("MAIN_BASELINE_MOVED")
    # Legacy branch-protection endpoint may say enabled=false: GitHub ruleset
    # is separately active. Do not equate branch.protection.enabled with the
    # total effective ruleset state or claim the branch has no protection.
    for i, item in enumerate(trial_refs):
        if type(item) is not dict or item.get("name") != _TEST_REFS[i]:
            raise ValueError("TEST_BRANCH_IDENTITY_MISMATCH")
        if item.get("protected") is not False:
            raise ValueError("TEST_REF_POLICY_CHANGED_REEVALUATE")
        commit = item.get("commit")
        if type(commit) is not dict or commit.get("sha") != _TEST_HEADS[i]:
            raise ValueError("TEST_BRANCH_HEAD_CHANGED")
    return {
        "status": "MAIN_RULESET_ACTIVE_M4_TEST_REFS_UNPROTECTED",
        "main_protected": True,
        "main_baseline_head": _BASE,
        "main_ruleset_id": _RULESET_ID,
        "main_required_status_checks": list(_REQUIRED_CI),
        "main_no_configured_bypass_for_this_actor": True,
        "test_ref_protected": [False, False],
        "source": "GitHub ruleset and branch REST metadata (not effective policy enforcement test)",
        **_UNPROVEN,
    }


def main() -> None:
    if os.getenv("GITHUB_ACTIONS") != "true" or os.getenv("GITHUB_REPOSITORY") != _REPO:
        raise PermissionError("GITHUB_ACTIONS_EXACT_REPO_REQUIRED")
    if os.getenv("GITHUB_EVENT_NAME") != "pull_request":
        raise PermissionError("PR_TRIGGER_REQUIRED")
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise PermissionError("READ_ONLY_TOKEN_REQUIRED")
    ruleset = _get("/rulesets/" + str(_RULESET_ID), token)
    main_branch = _get("/branches/main", token)
    test_branches = [_get("/branches/" + name, token) for name in _TEST_REFS]
    print(json.dumps({"debug_ruleset_actor_bypass": ruleset.get("current_user_can_bypass", "<absent>"), "debug_configured_bypass_actor_count": len(ruleset.get("bypass_actors", [])) if isinstance(ruleset.get("bypass_actors"), list) else "<unavailable>", "debug_meta_not_authority": True}, sort_keys=True))
    print(json.dumps(audit_ruleset(ruleset, main_branch, test_branches), sort_keys=True))


if __name__ == "__main__":
    main()
