"""MST Option A actual GitHub read-only ACL/ruleset custody inventory.

A successful execution is evidence about this GitHub token's REST metadata,
NOT independent admin custody, nonresettable floor, vendor rights or approval.
Drive snapshots are separately observed through the user's Google Drive
connector and must NOT be represented as live GitHub-hosted Drive inspection.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError

from scripts.m4_witness_ruleset_preflight import _get_json
from scripts.m4_option_a_selection_preflight import validate_option_a_choice

REPO = "ngluonghoa/MST"
MAIN_PIN = "4048f91beaaa3410116d97e35896c8b688384e19"
WITNESS = "refs/heads/mst/m4-witness/v1"
RULESET_NAME = "MST - Protect Main"
REQUIRED_CONTEXTS = {
    "unittest (3.11)",
    "unittest (3.12)",
    "Contract, source-boundary and wheel checks",
}


def _classify_rest_error(getter, path, token, *, allow_missing=False):
    try:
        return getter(path, token), "VISIBLE"
    except HTTPError as exc:
        if allow_missing and exc.code == 404:
            return None, "NOT_FOUND_404"
        if exc.code in (401, 403):
            return None, "INACCESSIBLE_TO_TOKEN_" + str(exc.code)
        raise


def inspect_github_custody(main, summaries, details, witness, classic_protection):
    """Return only facts witnessed by this token and OPEN security gaps."""
    if type(main) is not dict or main.get("name") != "main":
        raise ValueError("INVALID_LIVE_MAIN_BRANCH")
    if main.get("protected") is not True or (
        type(main.get("commit")) is not dict
        or main["commit"].get("sha") != MAIN_PIN
    ):
        raise ValueError("LIVE_MAIN_PROTECTION_OR_SOURCE_PIN_DRIFT")
    if type(summaries) is not list or type(details) is not dict:
        raise TypeError("GITHUB_RULESET_METADATA_REQUIRED")
    expected = [v for v in summaries if type(v) is dict
                and v.get("name") == RULESET_NAME]
    if len(expected) != 1:
        raise ValueError("MAIN_RULESET_MISSING_OR_AMBIGUOUS")
    item = expected[0]
    rid = item.get("id")
    if type(rid) is not int or rid <= 0 or rid not in details:
        raise ValueError("RULESET_DETAIL_REQUIRED")
    rule = details[rid]
    if type(rule) is not dict or rule.get("id") != rid:
        raise ValueError("RULESET_DETAIL_ID_MISMATCH")
    if rule.get("name") != RULESET_NAME or (
        rule.get("source_type") != "Repository"
        or rule.get("source") != REPO
        or rule.get("target") != "branch"
        or rule.get("enforcement") != "active"
    ):
        raise ValueError("WRONG_RULESET_OWNER_OR_INACTIVE")
    condition = rule.get("conditions")
    target = condition.get("ref_name") if type(condition) is dict else None
    if type(target) is not dict or type(target.get("include")) is not list:
        raise ValueError("RULESET_SCOPE_NOT_VERIFIABLE")
    if "~DEFAULT_BRANCH" not in target["include"]:
        raise ValueError("DEFAULT_BRANCH_NOT_COVERED")
    rows = rule.get("rules")
    if type(rows) is not list or any(type(x) is not dict for x in rows):
        raise ValueError("RULESET_RULE_DETAILS_NOT_VISIBLE")
    kinds = [x.get("type") for x in rows]
    if any(type(t) is not str for t in kinds) or len(set(kinds)) != len(kinds):
        raise ValueError("RULESET_RULES_INVALID_DUPLICATE")
    by_kind = {x["type"]: x for x in rows}
    mandatory = {"deletion", "non_fast_forward", "pull_request", "required_status_checks"}
    if not mandatory.issubset(by_kind):
        raise ValueError("MAIN_BASELINE_RULESET_EXPECTED_PROTECTIONS_MISSING")
    review = by_kind["pull_request"].get("parameters")
    checks = by_kind["required_status_checks"].get("parameters")
    if type(review) is not dict or type(checks) is not dict:
        raise ValueError("PR_APPROVAL_OR_CHECKS_NOT_VISIBLE")
    count = review.get("required_approving_review_count")
    if type(count) is not int or count < 0:
        raise ValueError("REVIEW_COUNT_NOT_VISIBLE")
    contexts_raw = checks.get("required_status_checks")
    if type(contexts_raw) is not list or any(
        type(x) is not dict or type(x.get("context")) is not str
        for x in contexts_raw
    ):
        raise ValueError("REQUIRED_CHECK_CONTEXTS_NOT_VISIBLE")
    contexts = [x["context"] for x in contexts_raw]
    if len(set(contexts)) != len(contexts):
        raise ValueError("DUPLICATE_REQUIRED_CHECKS")
    bypass = rule.get("bypass_actors")
    bypass_visible = type(bypass) is list
    bypass_empty = bypass_visible and not bypass
    if witness is not None:
        if type(witness) is not dict or witness.get("ref") != WITNESS:
            raise ValueError("WITNESS_REF_METADATA_MALFORMED")
    if classic_protection not in (
        "VISIBLE", "NOT_FOUND_404", "INACCESSIBLE_TO_TOKEN_401",
        "INACCESSIBLE_TO_TOKEN_403",
    ):
        raise ValueError("INVALID_CLASSIC_BRANCH_PROTECTION_OBSERVATION")

    return {
        "schema": "mst.m4.option-a.github-custody-readonly.v1",
        "status": "GITHUB_MAIN_BASELINE_VISIBLE_M4_INDEPENDENT_CUSTODY_BLOCKED",
        "evidence_class": "GITHUB_REST_METADATA_FOR_THIS_CI_TOKEN_ONLY",
        "main_pin_verified": True,
        "main_sha": MAIN_PIN,
        "main_ruleset_id": rid,
        "main_ruleset_active": True,
        "main_ruleset_covers_default_branch": True,
        "main_prevents_non_fast_forward_in_visible_rule": True,
        "main_prevents_deletion_in_visible_rule": True,
        "main_requires_pr_in_visible_rule": True,
        "main_required_approval_count": count,
        "main_has_positive_approval_requirement": count > 0,
        "main_required_checks_visible": sorted(contexts),
        "all_three_foundation_checks_required": REQUIRED_CONTEXTS.issubset(contexts),
        "main_requires_signed_commits_in_visible_rule": "required_signatures" in by_kind,
        "main_bypass_actor_list_visible": bypass_visible,
        "main_bypass_actor_list_empty_for_this_read": bool(bypass_empty),
        "current_token_can_bypass": rule.get("current_user_can_bypass"),
        "classic_branch_protection_endpoint_status": classic_protection,
        "witness_ref_exists_in_readback": witness is not None,
        "witness_owner_control_independently_attested": False,
        "github_admin_reset_impossible_proven": False,
        "two_independent_principals_verified": False,
        "global_signer_revocation_verified": False,
        "protected_external_monotonic_floor_verified": False,
        "physical_drive_market_cache_verified": False,
        "cache_read_authorized": False,
        "cache_write_authorized": False,
        "trading_authorized": False,
    }


def inspect_drive_snapshot(raw):
    """Validate historical connector observation WITHOUT implying live ACLs."""
    if type(raw) is not dict or raw.get("schema") != (
        "mst.m4.option-a.drive-acl-observation.unattested.v1"
    ):
        raise ValueError("INVALID_DRIVE_OBSERVATION_SCHEMA")
    if raw.get("source") != "CONNECTED_GOOGLE_DRIVE_FILE_METADATA_READ_ONLY":
        raise ValueError("DRIVE_PROVENANCE_NOT_ACCEPTED")
    if raw.get("visibility") != "CONNECTOR_VIEW_AT_READ_TIME_NOT_PERMANENT_ATTESTATION":
        raise ValueError("DRIVE_ACL_OVERCLAIM")
    required = (
        "MST_ROOT", "SOURCE_BASELINE_SNAPSHOT", "CANONICAL_DOCS",
        "QA_EVIDENCE", "CACHE_STAGING_SYNTHETIC_ONLY",
    )
    rows = raw.get("folders")
    if type(rows) is not list or len(rows) != len(required):
        raise ValueError("MISSING_DRIVE_FOLDER_OBSERVATIONS")
    if [x.get("scope") if type(x) is dict else None for x in rows] != list(required):
        raise ValueError("INVALID_DRIVE_FOLDER_SCOPES")
    for x in rows:
        if x.get("permission_metadata_available") is not True or (
            type(x.get("visible_permissions_count")) is not int
            or x["visible_permissions_count"] != 1
            or x.get("visible_roles") != ["owner"]
            or x.get("shared") is not False
            or x.get("independent_owner_principal_proven") is not False
            or x.get("actual_market_cache_verified") is not False
        ):
            raise ValueError("DRIVE_SNAPSHOT_PERMISSIONS_OR_AUTHORITY_DRIFT")
    for field in (
        "owner_identifiers_in_public_repo",
        "distinct_owner_custody_verified",
        "drive_object_immutability_verified",
        "real_drive_market_cache_verified",
        "approved_writer_identities_verified",
        "drive_permission_change_alerting_verified",
        "independent_trust_root_verified",
        "production_cache_read_authorized",
        "production_cache_write_authorized",
        "trading_authorized",
    ):
        if raw.get(field) is not False:
            raise PermissionError("DRIVE_SNAPSHOT_SELF_AUTHORIZATION_" + field)
    if raw.get("decision") != "OWNER_CUSTODY_AND_DURABLE_FLOOR_GAP_OPEN":
        raise PermissionError("DRIVE_ACL_STATUS_CANNOT_BE_CLOSED")
    return {
        "drive_scope_folder_metadata_observed": 5,
        "drive_metadata_shared_false_count": 5,
        "drive_visible_owner_role_per_folder": 1,
        "drive_observation_is_historical_not_live_ci": True,
        "drive_two_independent_owner_principals_attested": False,
        "drive_real_licensed_immutable_cache_proven": False,
        "drive_cache_read_authorized": False,
        "drive_cache_write_authorized": False,
    }


def main():
    if os.getenv("GITHUB_ACTIONS") != "true" or os.getenv("GITHUB_REPOSITORY") != REPO:
        raise PermissionError("EXACT_GITHUB_HOSTED_REPOSITORY_REQUIRED")
    if os.getenv("GITHUB_EVENT_NAME") != "pull_request":
        raise PermissionError("READONLY_PULL_REQUEST_EVENT_ONLY")
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise PermissionError("GITHUB_CONTENTS_READ_TOKEN_REQUIRED")
    choice = json.loads(Path("docs/MST_M4_OPTION_A_SCOPE_SELECTION_20261109.json").read_text())
    validate_option_a_choice(choice)
    main_meta = _get_json("/branches/main", token)
    rulesets = _get_json("/rulesets", token)
    if type(rulesets) is not list:
        raise TypeError("LIVE_RULESET_LIST_NOT_AVAILABLE")
    main_rule_items = [x for x in rulesets
                       if type(x) is dict and x.get("name") == RULESET_NAME]
    if len(main_rule_items) != 1 or type(main_rule_items[0].get("id")) is not int:
        raise ValueError("EXPECTED_MAIN_RULESET_NOT_VISIBLE")
    rule_id = main_rule_items[0]["id"]
    detail = _get_json("/rulesets/" + str(rule_id), token)
    witness, ws = _classify_rest_error(
        _get_json, "/git/ref/heads/mst/m4-witness/v1", token, allow_missing=True
    )
    if ws not in ("VISIBLE", "NOT_FOUND_404"):
        raise PermissionError("WITNESS_VISIBILITY_NOT_DETERMINABLE")
    _classic, classic_status = _classify_rest_error(
        _get_json, "/branches/main/protection", token, allow_missing=True
    )
    github_receipt = inspect_github_custody(
        main_meta, rulesets, {rule_id: detail}, witness, classic_status
    )
    drive_capture = json.loads(
        Path("docs/MST_M4_OPTION_A_DRIVE_ACL_OBSERVATION_20261109.json").read_text()
    )
    result = {
        "schema": "mst.m4.option-a.custody-gap-bundle.unattested.v1",
        "status": "OPTION_A_READONLY_METADATA_OBSERVED_REAL_CUSTODY_BLOCKED",
        "github_live_for_this_token": github_receipt,
        "drive_historical_connector_snapshot": inspect_drive_snapshot(drive_capture),
        "github_witness_http_status": ws,
        "independent_g01_root_attested": False,
        "external_g02_floor_attested": False,
        "two_writer_real_cas_attested": False,
        "source_vendor_rights_verified": False,
        "production_cache_authorized": False,
        "trading_authorized": False,
    }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
