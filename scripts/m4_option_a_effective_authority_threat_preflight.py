"""MST Option A effective GitHub+Drive authority threat review — STRICT NO GO.

This module intentionally cannot promote an untrusted private-identity,
bypass, signer, witness or license claim into production authorization.
It reuses the existing G01-G03 owner bridge and reads actual GitHub token-
limited REST receipts in CI; Drive observations remain historical connector
metadata. There are NO privileged API calls, keys or remote writes here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.m4_option_a_g01_g03_owner_packet_preflight import (
    PACKET_PATH, ROLE_PATH, DRIVE_PATH, OPTION_PATH, assess_packet,
)

SCHEMA = "mst.m4.option-a.effective-authority-threat-register.unattested.v1"
THREAT_PATH = Path("docs/MST_M4_OPTION_A_EFFECTIVE_AUTHORITY_THREAT_REGISTER_20261110.json")

THREATS = (
    ("T01", "ADMIN_MUTATES_WITNESS_RULESET", "G01", "OA01",
     "UNVERIFIED_BLOCK", "INDEPENDENT_EFFECTIVE_ADMIN_AND_BYPASS_READBACK"),
    ("T02", "PROTECTED_WITNESS_REF_DELETED_OR_RECREATED", "G02", "OA02",
     "UNVERIFIED_BLOCK", "OWNER_APPROVED_NONDELETE_NONFORCE_AND_MONOTONIC_REMOTE_FLOOR"),
    ("T03", "SIGNER_ROOT_AND_WRITER_SHARE_CONTROLLER", "G01", "OA01",
     "UNVERIFIED_BLOCK", "PRIVATE_DISTINCT_CONTROLLER_AND_KEY_ENROLLMENT_PROOF"),
    ("T04", "ROOT_ADMIN_REWINDS_SIGNER_EPOCH_OR_GENESIS", "G02", "OA05",
     "UNVERIFIED_BLOCK", "INDEPENDENT_REGISTRY_AND_ANTIROLLBACK_RECOVERY_WITNESS"),
    ("T05", "DRIVE_OWNER_CHANGES_OR_DELETES_CACHED_OBJECT", "G05", "OA04",
     "UNVERIFIED_BLOCK", "OWNER_CUSTODY_AND_PHYSICAL_BYTE_READBACK_WITH_RETENTION"),
    ("T06", "TWO_WRITER_LABELS_SHARE_ONE_CREDENTIAL", "G03", "OA03",
     "UNVERIFIED_BLOCK", "TWO_REAL_DISTINCT_NONADMIN_AUTHENTICATED_PRINCIPALS"),
    ("T07", "PULL_REQUEST_ACTION_OBTAINS_PRIVILEGED_WRITER_KEY", "G01", "OA01",
     "UNVERIFIED_BLOCK", "SEPARATE_PR_TOKEN_AND_SIGNER_WRITER_SECRET_DOMAIN"),
    ("T08", "OMITTED_BYPASS_ACTORS_TREATED_AS_EMPTY", "G01", "OA05",
     "UNVERIFIED_BLOCK", "INDEPENDENT_OWNER_ADMIN_BYPASS_INVENTORY"),
    ("T09", "APPROVER_SELF_SIGNS_POLICY_AND_REGISTRY", "G01", "OA01",
     "UNVERIFIED_BLOCK", "DISTINCT_OWNER_APPROVAL_AND_REVOCATION_CONTROLLER"),
    ("T10", "FRESH_READER_ACCEPTS_OLDER_VALID_SIGNED_HISTORY", "G02", "OA02",
     "COUNTEREXAMPLE_BLOCK", "REMOTE_HIGHEST_ACCEPTED_FLOOR_FROM_INDEPENDENT_AUTHORITY"),
    ("T11", "GITHUB_REF_AND_DRIVE_OBJECT_DISAGREE_ON_CRASH", "G03", "OA04",
     "UNVERIFIED_BLOCK", "TWO_SERVICE_READER_READBACK_AND_QUARANTINE_PROTOCOL"),
    ("T12", "ACTIONS_TOKEN_METADATA_MISTAKEN_FOR_GLOBAL_ROOT_FACT", "G07", "OA05",
     "UNVERIFIED_BLOCK", "SEPARATELY_AUTHENTICATED_PERMISSION_SCOPE_PROVENANCE"),
)
_FALSE = (
    "external_authority_signer_verified",
    "external_monotonic_floor_verified",
    "authenticated_two_principal_cas_verified",
    "cross_service_atomic_commit_verified",
    "independent_admin_bypass_inventory_verified",
    "independent_owner_signoff_received",
    "release_read_authorized",
    "cache_write_authorized",
    "trading_authorized",
)
TRUST_TIERS = {
    "original_source_parity": "GITHUB_SOURCE_SHA_CHECKS_ONLY",
    "github_ci_ruleset": "TOKEN_LIMITED_ACTIVE_MAIN_RULESET",
    "connected_github_repository": (
        "SEPARATE_CONNECTED_ACCOUNT_ADMIN_PERMISSION_OBSERVED_NOT_EFFECTIVE_BYPASS_PROOF"
    ),
    "connected_drive_folder_acl": (
        "FIVE_CURRENT_FOLDER_METADATA_VIEWS_NO_IMMUTABLE_EXTERNAL_CUSTODY"
    ),
    "proposed_rolematrix": "EIGHT_UNASSIGNED_ROLES_TWENTY_FIVE_PAIR_CONSTRAINTS",
    "synthetic_a03": "LOCAL_CONCURRENCY_SPLIT_BRAIN_AND_RESET_COUNTEREXAMPLE",
    "owner_independent_proof": "ABSENT_NOT_A_VALIDATED_ATTESTATION",
}


def _assert_equal(actual, expected, reason):
    if type(actual) is not type(expected) or actual != expected:
        raise ValueError(reason)


def _assert_false(data, fields, prefix):
    if type(data) is not dict:
        raise TypeError(prefix + "_DICT_REQUIRED")
    for name in fields:
        if data.get(name) is not False:
            raise PermissionError(prefix + "_" + name)


def evaluate_threats(
    register: dict,
    owner_packet: dict, roles: dict, drive: dict, option: dict,
    live_custody: dict, live_readiness: dict,
) -> dict:
    """Falsification/no-go receipt only. No owner identity is accepted."""
    owner = assess_packet(
        owner_packet, roles, drive, option, live_custody, live_readiness,
    )
    if type(register) is not dict:
        raise TypeError("ROOT_THREAT_REGISTER_DICT_REQUIRED")
    for k, expected in (
        ("schema", SCHEMA),
        ("repository", "ngluonghoa/MST"),
        ("option", "GITHUB_GOOGLE_DRIVE_ONLY"),
        ("current_state", "READ_ONLY_OWNER_ROOT_BYPASS_THREAT_MODEL_ALL_EXTERNAL_GATES_OPEN"),
        ("owner_decision_source", str(PACKET_PATH)),
        ("existing_role_source", str(ROLE_PATH)),
        ("existing_drive_snapshot_source", str(DRIVE_PATH)),
        ("published_principal_identifiers", False),
        ("attached_private_keys", False),
    ):
        _assert_equal(register.get(k), expected, "ROOT_THREAT_REGISTER_DRIFT_" + k)
    if register.get("trust_layers") != TRUST_TIERS:
        raise PermissionError("UNSIGNED_TRUST_LAYER_PROMOTED_TO_INDEPENDENT_AUTHORITY")
    if register.get("source_lock") != {
        "main": "4048f91beaaa3410116d97e35896c8b688384e19",
        "tree": "d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e",
        "upstream": "cd90c1babae8912db31490ad614fc2ad2f868042",
    }:
        raise PermissionError("ORIGINAL_SOURCE_PARITY_ROOT_DRIFT")
    if register.get("required_owner_decisions") != [
        "OA01", "OA02", "OA03", "OA04", "OA05", "OA06",
    ]:
        raise PermissionError("OWNER_DECISION_QUEUE_CHANGED_WITHOUT_APPROVAL")
    if register.get("required_open_external_gates") != [
        "G01", "G02", "G03", "G04", "G05", "G06", "G07", "G08",
    ]:
        raise PermissionError("EXTERNAL_SECURITY_GATES_SILENTLY_CLOSED")
    scenarios = register.get("threats")
    if type(scenarios) is not list or len(scenarios) != len(THREATS):
        raise ValueError("EXACT_TWELVE_ROOT_RISK_SCENARIOS_REQUIRED")
    for scenario, expected in zip(scenarios, THREATS):
        if type(scenario) is not dict:
            raise TypeError("THREAT_SCENARIO_DICT_REQUIRED")
        if set(scenario) != {
            "id", "scenario", "gate", "decision", "state", "control",
        }:
            raise ValueError("THREAT_SCENARIO_CANNOT_HIDE_UNKNOWN_FIELDS")
        if tuple(scenario[k] for k in (
            "id", "scenario", "gate", "decision", "state", "control",
        )) != expected:
            raise PermissionError("ROOT_THREAT_NOT_PROVEN_CLOSED_" + expected[0])
    _assert_false(register, _FALSE, "UNAUTHORIZED_ROOT_AUTHORITY_CLAIM")
    observations = register.get("observed_static")
    if type(observations) is not dict:
        raise ValueError("OBSERVED_STATIC_METADATA_REQUIRED")
    for key, expected in (
        ("repo_main_rule_id", 26801439),
        ("repo_main_positive_review_required", 0),
        ("repo_main_protected", True),
        ("witness_ref_provisioned", False),
        ("github_ci_bypass_list_visible", False),
        ("drive_metadata_folders_count", 5),
        ("drive_visible_owner_roles_each", 1),
        ("bound_roles_count", 0),
        ("distinct_principal_constraints", 25),
        ("github_connector_account_admin_permission_observed", True),
        ("admin_permission_does_not_prove_effective_bypass", True),
    ):
        _assert_equal(observations.get(key), expected,
                      "ROOT_THREAT_OBSERVATION_CHANGED_" + key)
    if owner["owner_gates_open"] != ["G01", "G02", "G03"] or (
        owner["independently_bound_roles"] != 0
        or owner["main_positive_human_approvals_required"] != 0
        or owner["witness_ref_exists"] is not False
    ):
        raise PermissionError("OWNER_G01_G03_EXISTING_BLOCKING_CONTRACT_BROKEN")
    if not register.get("safe_next") == (
        "PRIVATE_OWNER_EFFECTIVE_IDENTITY_ACL_AND_PLATFORM_ROOT_RISK_REVIEW_NO_APPLY"
    ):
        raise PermissionError("SCOPE_ESCALATION_TO_PRIVILEGED_APPLY")

    return {
        "schema": SCHEMA,
        "status": "TWELVE_ROOT_AND_IDENTITY_THREATS_REVIEWED_ALL_OPEN_PRODUCTION_NO_GO",
        "evidence_kind": "TOKEN_LIMITED_LIVE_GITHUB_PLUS_HISTORICAL_DRIVE_METADATA_UNATTESTED",
        "scenario_count": len(THREATS),
        "owner_decisions_open": len(register["required_owner_decisions"]),
        "external_gates_open": register["required_open_external_gates"],
        "one_inprocess_source_of_truth_does_not_prove_remote_cas": True,
        "connected_admin_permission_does_not_prove_effective_bypass": True,
        "single_visible_drive_owner_does_not_prove_independent_custody": True,
        "token_omitted_bypass_is_not_empty_bypass_proof": True,
        "bound_independent_role_principals": 0,
        "source_v1_modules_modified": False,
        "independent_signer_or_root_authority": False,
        "externally_nonresettable_monotonic_floor": False,
        "two_authenticated_writer_remote_cas": False,
        "privileged_changes_performed": False,
        "production_cache_read_authorized": False,
        "production_cache_write_authorized": False,
        "production_release_authorized": False,
        "trading_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", type=Path, default=THREAT_PATH)
    parser.add_argument("--packet", type=Path, default=PACKET_PATH)
    parser.add_argument("--roles", type=Path, default=ROLE_PATH)
    parser.add_argument("--drive", type=Path, default=DRIVE_PATH)
    parser.add_argument("--option", type=Path, default=OPTION_PATH)
    parser.add_argument("--live-custody", type=Path, required=True)
    parser.add_argument("--live-readiness", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    def data(path):
        return json.loads(path.read_text(encoding="utf-8"))
    result = evaluate_threats(
        data(args.register), data(args.packet), data(args.roles),
        data(args.drive), data(args.option),
        data(args.live_custody), data(args.live_readiness),
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
