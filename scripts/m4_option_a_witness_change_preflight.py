"""MST M4 Option A witness-owner CHANGE PACKET review, never an apply endpoint.

Validates canonical GitHub+Drive-only proposed witness ref/ruleset, role
separation, owner approvals and order of privileged changes. It makes NO
GitHub/Drive network requests and issues NO access credential or grant.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.m4_option_a_selection_preflight import validate_option_a_choice
from scripts.m4_option_a_role_separation_preflight import check_role_topology
from scripts.m4_witness_ruleset_preflight import validate_proposal

_SCHEMA = "mst.m4.option-a.witness-change-packet.unapproved.v1"
_STATUS = "OWNER_CHANGE_REVIEW_PACKET_NO_ACTION_AUTHORIZED"
_REF = "refs/heads/mst/m4-witness/v1"
_MAIN = "4048f91beaaa3410116d97e35896c8b688384e19"
_ROLES = (
    "POLICY_CONTROLLER", "SIGNER_ROOT_CUSTODIAN",
    "REVOCATION_CONTROLLER", "WITNESS_WRITER_A", "WITNESS_WRITER_B",
    "DRIVE_CHUNK_WRITER", "READ_ONLY_VERIFIER",
)
_DECISIONS = (
    "APPROVE_CUSTODIAN_IDENTITIES_ROOT_ADMIN_AND_BYPASS_INVENTORY",
    "APPROVE_WITNESS_REF_NAMESPACE_AND_OWNER_AUTHORITY",
    "APPROVE_GENESIS_BOOTSTRAP_BEFORE_RULESET_ENFORCEMENT",
    "APPROVE_WITNESS_RULESET_APPLY_AND_READBACK",
    "APPROVE_TWO_WRITER_AND_INDEPENDENT_READER_ENROLLMENT",
    "APPROVE_SERVER_CAS_AND_ADVERSARIAL_ROLLBACK_EXPERIMENT",
    "APPROVE_LICENSED_DRIVE_CUSTODY_AND_REVOKE_RECOVERY",
    "APPROVE_FINAL_PARITY_ABI_M3_M4_RELEASE",
)
_STEPS = (
    "CURRENT_STATE_READ_ONLY_PREFLIGHT",
    "OWNER_REVIEW_IDENTITIES_AND_ADMIN_RECOVERY",
    "OWNER_APPROVE_REF_AND_GENESIS",
    "OWNER_GATED_GENESIS_BRANCH_CREATION",
    "OWNER_GATED_RULESET_INSTALLATION",
    "INDEPENDENT_READBACK_AND_EFFECTIVE_PROTECTION",
    "OWNER_GATED_WRITER_SIGNER_ENROLLMENT",
    "MULTIWRITER_CAS_ROLLBACK_AND_GLOBAL_REVOKE_ACCEPTANCE",
    "PHYSICAL_LICENSED_DRIVE_CHUNK_AND_CROSS_SERVICE_BARRIER",
    "FINAL_OWNER_DISPOSITION",
)
_FALSE = (
    "current_witness_ref_exists",
    "current_main_required_signed_commits_in_inspected_ruleset",
    "current_ci_token_bypass_list_visible",
    "current_classic_branch_protection_endpoint_readable",
    "independent_admin_and_root_graph_verified",
    "effective_witness_bypass_absence_verified",
    "approved_production_root_registry",
    "current_owner_authorization_for_privileged_changes",
    "real_witness_ruleset_installed",
    "real_witness_branch_bootstrapped",
    "real_owner_signer_enrolled",
    "real_two_auth_writer_cas_verified",
    "real_license_and_first_known_attested",
    "real_drive_bytes_verified",
    "global_revocation_verified",
    "protected_nonresettable_monotonic_floor_verified",
    "release_approved",
    "production_cache_read_authorized",
    "production_cache_write_authorized",
    "trading_authorized",
)
_IDENTITY = {
    "schema": _SCHEMA,
    "status": _STATUS,
    "repository": "ngluonghoa/MST",
    "branch_scope": "DRAFT_PR8_ONLY",
    "source_baseline": _MAIN,
    "user_selected_platform_scope": "GITHUB_AND_GOOGLE_DRIVE_ONLY",
    "witness_ref": _REF,
    "proposed_witness_ruleset_path":
        "docs/MST_M4_WITNESS_RULESET_PROPOSAL_20261109.json",
    "proposed_identity_policy_path":
        "docs/MST_M4_OPTION_A_ROLE_SEPARATION_PROPOSAL_20261109.json",
    "residual_risk":
        "GITHUB_REPO_ROOT_ADMIN_CAN_CHANGE_OR_REPLACE_REPO_RULES_OR_HISTORY_UNLESS_INDEPENDENTLY_DETECTED; SAME_CONTROLLER_ACROSS_GITHUB_AND_DRIVE_NOT_PROVEN_SAFE",
    "recovery_rule":
        "ON_POLICY_BYPASS_RESET_REF_DRIFT_UNVERIFIED_OWNER_OR_403_QUARANTINE_AND_REQUIRE_OWNER_INDEPENDENT_FLOOR_READBACK; NEVER_AUTOMATICALLY_REBASE_OR_REBOOTSTRAP_G1",
    "decision": "NO_GO_UNTIL_SEPARATE_OWNER_APPROVAL_AND_ADVERSARIAL_EVIDENCE",
}
_EXPECTED_KEYS = (
    set(_IDENTITY) | set(_FALSE) | {
        "current_main_ruleset_id",
        "current_main_required_approving_reviews",
        "suggested_rule_types", "forbidden_rule_types_for_unenrolled_writers",
        "expected_ruleset_condition", "proposed_bypass_actors",
        "privileged_roles_to_verify", "owner_approvals", "change_sequence",
    }
)


def validate_change_packet(raw, witness_proposal, role_proposal, option_a):
    """Ensure this review packet cannot self-execute any privileged action."""
    validate_option_a_choice(option_a)
    validate_proposal(witness_proposal)
    check_role_topology(role_proposal)
    if type(raw) is not dict or set(raw) != _EXPECTED_KEYS:
        raise ValueError("NONCANONICAL_WITNESS_OWNER_CHANGE_PACKET")
    for key, expected in _IDENTITY.items():
        if type(raw.get(key)) is not str or raw[key] != expected:
            raise ValueError("WITNESS_OWNER_CHANGE_IDENTITY_OR_SCOPE_DRIFT_" + key)
    for key in _FALSE:
        if raw.get(key) is not False:
            raise PermissionError("OWNER_CHANGE_PACKET_SELF_AUTHORIZATION_" + key)
    if (type(raw.get("current_main_ruleset_id")) is not int
            or raw["current_main_ruleset_id"] != 26801439
            or type(raw.get("current_main_required_approving_reviews")) is not int
            or raw["current_main_required_approving_reviews"] != 0):
        raise ValueError("LIVE_MAIN_RULESET_BASELINE_DRIFT")
    expected_types = ["deletion", "non_fast_forward", "required_signatures"]
    if raw.get("suggested_rule_types") != expected_types:
        raise ValueError("WITNESS_PROTECTIONS_DRIFT")
    if raw.get("forbidden_rule_types_for_unenrolled_writers") != ["creation", "update"]:
        raise ValueError("WITNESS_WRITER_LOCKOUT_RISK_NOT_ACCOUNTED_FOR")
    if raw.get("expected_ruleset_condition") != {
        "include": [_REF], "exclude": [],
    }:
        raise ValueError("WITNESS_RULESET_EXACT_SCOPE_DRIFT")
    if raw.get("proposed_bypass_actors") != []:
        raise PermissionError("UNAPPROVED_WITNESS_BYPASS_ACTORS")
    if raw.get("privileged_roles_to_verify") != list(_ROLES):
        raise ValueError("WITNESS_REQUIRED_OWNER_ROLES_DRIFT")
    config = validate_proposal(witness_proposal)
    if (raw["suggested_rule_types"] != [v["type"] for v in config["rules"]]
            or raw["expected_ruleset_condition"] != config["conditions"]["ref_name"]
            or raw["proposed_bypass_actors"] != config["bypass_actors"]):
        raise ValueError("WITNESS_PACKET_CONFLICTS_WITH_PRIOR_RULESET_PROPOSAL")
    if not set(_ROLES).issubset({r["role"] for r in role_proposal["roles"]}):
        raise ValueError("WITNESS_ROLE_PROPOSAL_CANNOT_SATISFY_PACKET")
    decisions = raw.get("owner_approvals")
    if type(decisions) is not list or len(decisions) != len(_DECISIONS):
        raise ValueError("EIGHT_OPEN_WITNESS_OWNER_APPROVALS_REQUIRED")
    for i, entry in enumerate(decisions):
        if type(entry) is not dict or set(entry) != {
            "id", "decision", "required_evidence", "status", "owner_principal",
            "approval_receipt_uri", "independently_attested",
        }:
            raise ValueError("NONCANONICAL_WITNESS_OWNER_APPROVAL_ENTRY")
        if (entry["id"] != f"C{i+1:02d}"
                or entry["decision"] != _DECISIONS[i]
                or entry["status"] != "OPEN_OWNER_REVIEW_REQUIRED"
                or entry["owner_principal"] is not None
                or entry["approval_receipt_uri"] is not None
                or entry["independently_attested"] is not False):
            raise PermissionError("WITNESS_OWNER_APPROVAL_SELF_CERTIFIED")
        if type(entry["required_evidence"]) is not str or not entry["required_evidence"].strip():
            raise ValueError("WITNESS_OWNER_EVIDENCE_DESCRIPTION_MISSING")
    steps = raw.get("change_sequence")
    if type(steps) is not list or len(steps) != len(_STEPS):
        raise ValueError("TEN_ORDERED_WITNESS_CHANGE_STEPS_REQUIRED")
    for i, entry in enumerate(steps):
        if type(entry) is not dict or set(entry) != {
            "id", "operation", "intent", "status", "requires_independent_owner_authorization",
            "execution_evidence_uri", "actual_resource_mutation",
        }:
            raise ValueError("NONCANONICAL_WITNESS_CHANGE_STEP_FIELDS")
        if (entry["id"] != f"S{i:02d}"
                or entry["operation"] != _STEPS[i]
                or entry["status"] != "NOT_EXECUTED"
                or entry["requires_independent_owner_authorization"] is not (i >= 2)
                or entry["execution_evidence_uri"] is not None
                or entry["actual_resource_mutation"] is not False):
            raise PermissionError("PREMATURE_EXECUTION_OR_REORDERED_CHANGE_SEQUENCE")
        if type(entry["intent"]) is not str or not entry["intent"].strip():
            raise ValueError("WITNESS_CHANGE_STEP_INTENT_REQUIRED")
    return {
        "schema": "mst.m4.option-a.witness-owner-change-review.blocked.v1",
        "status": "WITNESS_OWNER_CHANGE_PACKET_COMPLETE_NOT_APPROVED_NOT_EXECUTED",
        "owner_approval_gates_open": len(decisions),
        "change_steps_not_executed": len(steps),
        "privileged_change_steps_require_owner": len(steps) - 2,
        "witness_ref_provisioned": False,
        "real_signer_enrolled": False,
        "real_writer_credentials_provisioned": False,
        "independent_admin_control_verified": False,
        "external_nonresettable_floor_verified": False,
        "cache_read_authorized": False,
        "cache_write_authorized": False,
        "trading_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, default=Path(
        "docs/MST_M4_OPTION_A_WITNESS_OWNER_CHANGE_PACKET_20261109.json"
    ))
    parser.add_argument("--witness-proposal", type=Path, default=Path(
        "docs/MST_M4_WITNESS_RULESET_PROPOSAL_20261109.json"
    ))
    parser.add_argument("--role-proposal", type=Path, default=Path(
        "docs/MST_M4_OPTION_A_ROLE_SEPARATION_PROPOSAL_20261109.json"
    ))
    parser.add_argument("--choice", type=Path, default=Path(
        "docs/MST_M4_OPTION_A_SCOPE_SELECTION_20261109.json"
    ))
    parser.add_argument("--out", type=Path)
    a = parser.parse_args(argv)
    def read(path):
        return json.loads(path.read_text(encoding="utf-8"))
    receipt = validate_change_packet(
        read(a.packet), read(a.witness_proposal),
        read(a.role_proposal), read(a.choice),
    )
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
