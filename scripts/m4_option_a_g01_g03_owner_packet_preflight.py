"""MST Option A G01/G02/G03 owner decision bridge — READ-ONLY, fail-closed.

This validator cross-checks the EXISTING eight-role/25-pair proposal and
historical Drive ACL against real but token-limited GitHub Actions readbacks.
No amount of local/CI evidence produces owner signoff, CAS or a durable floor.
Never accepts a "ready" value; if live state changes, review a new owner
protocol instead of auto-authorizing that state.

Runs ONLY on GitHub-hosted PR #8 with contents:read, never local/project Mac.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.m4_option_a_live_custody_audit import inspect_drive_snapshot
from scripts.m4_option_a_role_separation_preflight import check_role_topology
from scripts.m4_option_a_selection_preflight import validate_option_a_choice
from scripts.m4_reader_readiness_preflight import (
    _BASE, _DENIED, _GATES, _REF,
)

SCHEMA = "mst.m4.option-a.g01-g03.owner-decision-bridge.unapproved.v1"
PACKET_PATH = Path("docs/MST_M4_OPTION_A_G01_G03_OWNER_DECISION_BRIDGE_20261110.json")
ROLE_PATH = Path("docs/MST_M4_OPTION_A_ROLE_SEPARATION_PROPOSAL_20261109.json")
DRIVE_PATH = Path("docs/MST_M4_OPTION_A_DRIVE_ACL_OBSERVATION_20261109.json")
OPTION_PATH = Path("docs/MST_M4_OPTION_A_SCOPE_SELECTION_20261109.json")
EXPECTED_GATES = ("G01", "G02", "G03")
EXPECTED_DECISIONS = ("OA01", "OA02", "OA03", "OA04", "OA05", "OA06")
EXPECTED_STATUS = "OWNER_DECISION_BRIDGE_READONLY_G01_G02_G03_OPEN"
EXPECTED_FIELDS = (
    "production_cache_read_authorized", "production_cache_write_authorized",
    "production_release_authorized", "trading_authorized",
    "privileged_actions_performed", "new_cloud_service_approved",
    "owner_approval_received",
)
EXPECTED_GATE_FALSE = {
    "G01": ("owner_approved", "independent_root_identity_verified",
            "signer_key_custody_proven", "actual_admin_bypass_graph_verified"),
    "G02": ("owner_approved", "protected_witness_ref_provisioned",
            "immutable_remote_floor_verified", "admin_rollback_proof_verified"),
    "G03": ("owner_approved", "two_distinct_writer_accounts_verified",
            "real_server_one_winner_loser_proven",
            "drive_github_atomic_transaction_proven"),
}
EXPECTED_EVIDENCE = {
    "github_live_ci": "READ_ONLY_TOKEN_LIMITED_REST_METADATA_NOT_ADMIN_ATTESTATION",
    "google_drive_live_connector": "FIVE_FOLDER_METADATA_CURRENT_CONNECTOR_VIEW_NOT_DURABLE_ATTESTATION",
    "github_role_proposal": "SIGNED_OWNER_IDENTITY_BINDINGS_ABSENT",
    "a03_test_result": "SIMULATED_DUAL_READER_WRITER_FALSIFICATION_NO_REMOTE_CAS",
}
REQUIRED_FORBIDDEN = (
    "GREEN_SYNTHETIC_QA_PROVES_G01_OR_G02_OR_G03",
    "GH_FAST_FORWARD_EQUALS_TWO_AUTH_SERVER_CAS",
    "DRIVE_FOLDER_OWNER_COUNT_EQUALS_INDEPENDENT_CUSTODY",
    "INPROCESS_WRITER_LABEL_EQUALS_AUTHENTICATED_GITHUB_PRINCIPAL",
    "CALLER_RESETTABLE_SESSION_FLOOR_EQUALS_NONRESETTABLE_EXTERNAL_FLOOR",
    "BYPASS_METADATA_OMITTED_EQUALS_EMPTY_BYPASS_GRAPH",
    "SIGNED_MANIFEST_EQUALS_LICENSED_VENDOR_SOURCE_TRUTH",
)
MANDATORY_OPEN = (
    "A02_final_owner_module_signoff",
    "A03_full_v2_abi_owner_signoff",
    "G04_licensed_market_source",
    "G05_real_physical_drive_market_cache_and_recovery",
    "G06_global_revocation", "G07_independent_provenance",
    "G08_owner_release", "M3_M4_M5_M8_production",
)


def _same(value, expected, reason):
    # Distinguish bool from int, including when strict 0 is required.
    if type(value) is not type(expected) or value != expected:
        raise ValueError(reason)


def _false(raw, fields, reason):
    if type(raw) is not dict:
        raise TypeError(reason + "_DICT_REQUIRED")
    for key in fields:
        if raw.get(key) is not False:
            raise PermissionError(reason + "_" + key)


def assess_packet(
    packet: dict, role_proposal: dict, drive_snapshot: dict,
    option_a: dict, live_custody: dict, live_readiness: dict,
) -> dict:
    """Accept ONLY blocked owner packets, never authorize live production."""
    validate_option_a_choice(option_a)
    roles = check_role_topology(role_proposal)
    drive = inspect_drive_snapshot(drive_snapshot)
    if type(packet) is not dict:
        raise TypeError("OWNER_BRIDGE_PACKET_REQUIRED")
    for k, expected in (
        ("schema", SCHEMA), ("status", EXPECTED_STATUS),
        ("scope", "GITHUB_GOOGLE_DRIVE_ONLY_OPTION_A"),
        ("repository", "ngluonghoa/MST"),
        ("protected_main_source_sha", _BASE),
        ("original_source_tree_sha", "d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e"),
        ("source_upstream_sha", "cd90c1babae8912db31490ad614fc2ad2f868042"),
        ("work_pr", 8),
        ("work_branch_must_remain_draft", True),
        ("implementation_style", "ADDITIVE_NO_V1_OR_EXISTING_V2_MUTATIONS"),
    ):
        _same(packet.get(k), expected, "OWNER_BRIDGE_IDENTITY_DRIFT_" + k)
    if packet.get("evidence_tiers") != EXPECTED_EVIDENCE:
        raise PermissionError("UNTRUSTED_EVIDENCE_PROMOTED_TO_AUTHORITY")
    _false(packet, EXPECTED_FIELDS, "PREMATURE_OWNER_AUTHORIZATION")
    gate_data = packet.get("gates")
    if type(gate_data) is not dict or set(gate_data) != set(EXPECTED_GATES):
        raise ValueError("EXACT_THREE_OWNER_SECURITY_GATES_REQUIRED")
    for gate, flag_names in EXPECTED_GATE_FALSE.items():
        item = gate_data[gate]
        if type(item) is not dict or item.get("state") != "OPEN":
            raise PermissionError("SECURITY_GATE_PREMATURELY_CLOSED_" + gate)
        _false(item, flag_names, "SECURITY_GATE_PREMATURE_CERTIFICATION_" + gate)
        if type(item.get("evidence_to_accept")) is not list or len(item["evidence_to_accept"]) < 3:
            raise ValueError("OWNER_GAP_ACCEPTANCE_CRITERIA_MISSING_" + gate)
        if type(item.get("counterexample")) is not str or not item["counterexample"]:
            raise ValueError("SYNTHETIC_FALSIFICATION_NOT_RECORDED_" + gate)
    decisions = packet.get("owner_decisions")
    if type(decisions) is not list or [
        item.get("id") if type(item) is dict else None for item in decisions
    ] != list(EXPECTED_DECISIONS):
        raise ValueError("OWNER_DECISION_IDS_MISSING_OR_REORDERED")
    for item in decisions:
        if item.get("state") != "OPEN" or (
            item.get("choice") is not None or
            item.get("owner_attestation_uri") is not None
        ):
            raise PermissionError("UNSIGNED_OWNER_DECISION_PREMATURELY_APPROVED")
        if not item.get("topic") or type(item.get("related")) is not list:
            raise ValueError("OWNER_DECISION_TRACEABILITY_MISSING")
    linked = packet.get("linked_gates")
    if type(linked) is not dict or set(linked) != set(MANDATORY_OPEN):
        raise ValueError("UNSCOPED_DEPENDENCY_OR_MISSING_OWNER_GATE")
    for key in MANDATORY_OPEN:
        expected = (
            "BLOCKED" if key == "M3_M4_M5_M8_production" else
            "OPEN_0_OF_63" if key == "A02_final_owner_module_signoff"
            else "OPEN"
        )
        if linked.get(key) != expected:
            raise PermissionError("DEPENDENT_PRODUCTION_GATE_CLAIMED_CLOSED_" + key)
    if packet.get("forbidden_claims") != list(REQUIRED_FORBIDDEN):
        raise PermissionError("NO_GO_INTERPRETATION_CONSTRAINT_REMOVED")

    obs = packet.get("exact_observations")
    if type(obs) is not dict:
        raise ValueError("EXACT_OBSERVATION_PROVENANCE_REQUIRED")
    for key, expected in (
        ("github_main_ruleset_id", 26801439),
        ("github_main_required_approvals", 0),
        ("github_main_has_required_foundation_checks", True),
        ("github_main_no_signatures_required_in_inspected_rule", True),
        ("github_actions_bypass_actor_list_visible", False),
        ("github_witness_ref", _REF),
        ("github_witness_exists_in_latest_read", False),
        ("proposed_role_count", roles["roles_proposed"]),
        ("approved_actual_principal_bindings", roles["roles_with_actual_principals"]),
        ("required_distinct_principal_pairs", roles["required_distinct_principal_pairs"]),
        ("open_owner_role_decisions", roles["role_owner_decisions_open"]),
        ("connected_drive_folder_metadata_count", drive["drive_scope_folder_metadata_observed"]),
        ("connected_drive_visible_owner_role_count_each", drive["drive_visible_owner_role_per_folder"]),
        ("connected_drive_independent_custodian_verified", False),
        ("drive_observation_not_github_actions_live", True),
        ("a03_new_synthetic_tests_pass", 48),
        ("foundation_python311_pass", 2277),
        ("foundation_python312_pass", 2277),
        ("foundation_engineering_source_modules_pass", 63),
    ):
        _same(obs.get(key), expected, "OWNER_OBSERVATION_DRIFT_" + key)
    if type(obs.get("github_code_head_workflows_success")) is not int or (
        obs["github_code_head_workflows_success"] != 18
    ):
        raise ValueError("OWNER_REFERENCE_CI_BASELINE_CHANGED")
    if any(type(obs.get(k)) is not int or obs[k] < 1 for k in (
        "github_m4_live_custody_run_id", "github_m4_readiness_run_id",
        "github_m4_role_matrix_run_id", "github_a03_dual_reader_writer_run_id",
        "github_foundation_run_id",
    )):
        raise ValueError("GITHUB_EVIDENCE_RUN_ID_MISSING")

    if type(live_custody) is not dict or (
        live_custody.get("schema") != "mst.m4.option-a.custody-gap-bundle.unattested.v1"
        or live_custody.get("status") != "OPTION_A_READONLY_METADATA_OBSERVED_REAL_CUSTODY_BLOCKED"
    ):
        raise ValueError("LIVE_CUSTODY_READONLY_RECEIPT_REQUIRED")
    _false(live_custody, (
        "independent_g01_root_attested", "external_g02_floor_attested",
        "two_writer_real_cas_attested", "source_vendor_rights_verified",
        "production_cache_authorized", "trading_authorized",
    ), "LIVE_CUSTODY_UNAUTHORIZED_PROMOTION")
    github = live_custody.get("github_live_for_this_token")
    if type(github) is not dict:
        raise ValueError("LIVE_GITHUB_RECEIPT_REQUIRED")
    for key, expected in (
        ("schema", "mst.m4.option-a.github-custody-readonly.v1"),
        ("evidence_class", "GITHUB_REST_METADATA_FOR_THIS_CI_TOKEN_ONLY"),
        ("main_sha", _BASE),
        ("main_ruleset_active", True),
        ("main_pin_verified", True),
        ("main_ruleset_id", obs["github_main_ruleset_id"]),
        ("main_required_approval_count", obs["github_main_required_approvals"]),
        ("all_three_foundation_checks_required", True),
        ("main_bypass_actor_list_visible", False),
        ("witness_ref_exists_in_readback", False),
    ):
        _same(github.get(key), expected, "LIVE_GITHUB_CUSTODY_DRIFT_" + key)
    _false(github, (
        "witness_owner_control_independently_attested",
        "protected_external_monotonic_floor_verified",
        "two_independent_principals_verified", "physical_drive_market_cache_verified",
        "cache_read_authorized", "cache_write_authorized", "trading_authorized",
    ), "LIVE_GITHUB_RIGHTS_OVERCLAIM")
    if live_custody.get("github_witness_http_status") != "NOT_FOUND_404":
        raise PermissionError("WITNESS_CHANGED_REQUIRES_NEW_OWNER_REVIEW")
    if live_custody.get("drive_historical_connector_snapshot") != drive:
        raise ValueError("HISTORICAL_DRIVE_SNAPSHOT_FALSIFIED_OR_CHANGED")

    if type(live_readiness) is not dict or (
        live_readiness.get("schema") != "mst.m4.reader-readiness.blocking-audit.v1"
        or live_readiness.get("status")
        != "M4_READER_AND_PUBLISHER_BLOCKED_PENDING_EXTERNAL_OWNER_GATES"
    ):
        raise ValueError("READINESS_BLOCKING_RECEIPT_REQUIRED")
    for k, expected in (
        ("main_baseline_verified_for_this_read", True),
        ("main_head_sha", _BASE),
        ("witness_ref_name", _REF),
        ("witness_ref_exists_for_this_read", False),
        ("witness_ref_head_sha_for_this_read", None),
    ):
        _same(live_readiness.get(k), expected, "LIVE_READINESS_DRIFT_" + k)
    if live_readiness.get("owner_gates_still_open") != list(_GATES):
        raise PermissionError("OWNER_GATES_UNJUSTIFIABLY_CLOSED")
    _false(live_readiness, (
        *_DENIED.keys(),
        "witness_actual_owner_authorization",
        "witness_active_protection_effective_end_to_end_verified",
        "witness_ruleset_visible_for_this_token",
        "witness_ruleset_scope_visible_for_this_token",
        "witness_ruleset_metadata_matches_for_this_token",
        "witness_bypass_list_visible_for_this_token",
    ), "LIVE_READINESS_CANNOT_AUTHORIZE")

    return {
        "schema": SCHEMA,
        "status": "G01_G02_G03_OWNER_DECISION_PACKET_BLOCKED_BUT_INTERNALLY_RECONCILED",
        "evidence_kind": "SELF_ATTESTED_REVIEW_AND_TOKEN_LIMITED_METADATA_ONLY",
        "roles_proposed": roles["roles_proposed"],
        "independently_bound_roles": roles["roles_with_actual_principals"],
        "required_distinct_principal_pairs": roles["required_distinct_principal_pairs"],
        "drive_folder_metadata_in_historical_snapshot": drive["drive_scope_folder_metadata_observed"],
        "main_positive_human_approvals_required": obs["github_main_required_approvals"],
        "witness_ref_exists": False,
        "owner_gates_open": list(EXPECTED_GATES),
        "owner_decisions_open": len(EXPECTED_DECISIONS),
        "a03_split_brain_and_reset_falsification_requires_external_authority": True,
        "independent_signer_proven": False,
        "durable_monotonic_floor_proven": False,
        "authenticated_two_writer_cas_proven": False,
        "production_cache_read_authorized": False,
        "production_cache_write_authorized": False,
        "production_release_authorized": False,
        "trading_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, default=PACKET_PATH)
    parser.add_argument("--roles", type=Path, default=ROLE_PATH)
    parser.add_argument("--drive", type=Path, default=DRIVE_PATH)
    parser.add_argument("--option-a", type=Path, default=OPTION_PATH)
    parser.add_argument("--live-custody", type=Path, required=True)
    parser.add_argument("--live-readiness", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    data = lambda p: json.loads(p.read_text(encoding="utf-8"))
    proof = assess_packet(
        data(args.packet), data(args.roles), data(args.drive),
        data(args.option_a), data(args.live_custody), data(args.live_readiness),
    )
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(proof, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8")
    print(json.dumps(proof, sort_keys=True))


if __name__ == "__main__":
    main()
