"""MST Option A GitHub + Drive owner-role separation, REVIEW ONLY.

Checks the proposed (unassigned) role matrix against self-attested privilege
escalation. A hypothetical alias exercise models collisions without proving
that distinct GitHub/Drive logins belong to different controllers.

NEVER use this function as an access-control authorization endpoint.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.m4_option_a_selection_preflight import validate_option_a_choice

_SCHEMA = "mst.m4.option-a.roles.separation-proposal.v1"
_STATUS = "PROPOSED_ROLE_TOPOLOGY_ALL_IDENTITIES_UNASSIGNED"
_ROLES = (
    "POLICY_CONTROLLER",
    "SIGNER_ROOT_CUSTODIAN",
    "REVOCATION_CONTROLLER",
    "WITNESS_WRITER_A",
    "WITNESS_WRITER_B",
    "DRIVE_CHUNK_WRITER",
    "READ_ONLY_VERIFIER",
    "PULL_REQUEST_CI",
)
_BOUNDARIES = (
    "GITHUB_WITNESS_POLICY_ADMIN",
    "GITHUB_SIGNER_REGISTRY_CUSTODY",
    "GITHUB_OWNER_RECOVERY_CUSTODY",
    "GITHUB_NARROW_WITNESS_WRITE",
    "GITHUB_NARROW_WITNESS_WRITE",
    "GOOGLE_DRIVE_LICENSED_CHUNK_WRITE",
    "GITHUB_AND_DRIVE_READONLY_VERIFICATION",
    "GITHUB_PR_CONTENTS_READ_ONLY",
)
_CAPABILITIES = (
    ("propose_witness_ruleset", "review_bypass_inventory"),
    ("propose_root_registry", "approve_signer_key_enrollment"),
    ("propose_global_revocation", "review_owner_recovery"),
    ("propose_append_candidate",),
    ("propose_append_candidate",),
    ("stage_immutable_chunk",),
    ("read_witness_floor", "read_registry", "read_drive_bytes"),
    ("read_repo_source", "run_synthetic_tests"),
)
_FORBIDDEN = (
    ("pr_workflow_secret", "publish_cache", "enroll_signer", "verify_own_policy"),
    ("publish_cache", "update_witness_head", "modify_ruleset", "approve_own_registry"),
    ("publish_cache", "modify_ruleset", "self_approve_revoke"),
    ("modify_ruleset", "force_push", "delete_ref", "enroll_signer", "change_floor_genesis", "create_admin_token"),
    ("modify_ruleset", "force_push", "delete_ref", "enroll_signer", "change_floor_genesis", "create_admin_token"),
    ("modify_witness_ruleset", "approve_signer", "create_owner_key", "delete_accepted_cache"),
    ("write_witness", "stage_immutable_chunk", "modify_ruleset", "enroll_signer", "approve_own_receipt"),
    ("write_witness", "stage_immutable_chunk", "access_signer_private_key", "access_real_vendor_token", "modify_ruleset", "approve_owner_gate"),
)
_PAIRS = (
    ("POLICY_CONTROLLER", "SIGNER_ROOT_CUSTODIAN"),
    ("POLICY_CONTROLLER", "WITNESS_WRITER_A"),
    ("POLICY_CONTROLLER", "WITNESS_WRITER_B"),
    ("POLICY_CONTROLLER", "READ_ONLY_VERIFIER"),
    ("SIGNER_ROOT_CUSTODIAN", "REVOCATION_CONTROLLER"),
    ("SIGNER_ROOT_CUSTODIAN", "WITNESS_WRITER_A"),
    ("SIGNER_ROOT_CUSTODIAN", "WITNESS_WRITER_B"),
    ("SIGNER_ROOT_CUSTODIAN", "READ_ONLY_VERIFIER"),
    ("WITNESS_WRITER_A", "WITNESS_WRITER_B"),
    ("WITNESS_WRITER_A", "READ_ONLY_VERIFIER"),
    ("WITNESS_WRITER_B", "READ_ONLY_VERIFIER"),
    ("PULL_REQUEST_CI", "POLICY_CONTROLLER"),
    ("PULL_REQUEST_CI", "SIGNER_ROOT_CUSTODIAN"),
    ("PULL_REQUEST_CI", "REVOCATION_CONTROLLER"),
    ("PULL_REQUEST_CI", "WITNESS_WRITER_A"),
    ("PULL_REQUEST_CI", "WITNESS_WRITER_B"),
    ("PULL_REQUEST_CI", "DRIVE_CHUNK_WRITER"),
    ("PULL_REQUEST_CI", "READ_ONLY_VERIFIER"),
    ("DRIVE_CHUNK_WRITER", "READ_ONLY_VERIFIER"),
    ("DRIVE_CHUNK_WRITER", "SIGNER_ROOT_CUSTODIAN"),
    ("POLICY_CONTROLLER", "REVOCATION_CONTROLLER"),
    ("REVOCATION_CONTROLLER", "WITNESS_WRITER_A"),
    ("REVOCATION_CONTROLLER", "WITNESS_WRITER_B"),
    ("REVOCATION_CONTROLLER", "READ_ONLY_VERIFIER"),
    ("REVOCATION_CONTROLLER", "DRIVE_CHUNK_WRITER"),
)
_OPEN = (
    "OWNER_POLICY_CONTROLLER_AND_BYPASS_GRAPH",
    "INDEPENDENT_SIGNER_REGISTRY_AND_REVOCATION_AUTHORITY",
    "TWO_SEPARATE_GITHUB_WITNESS_WRITERS_AND_ATOMIC_CAS",
    "INDEPENDENT_GITHUB_DRIVE_READER_AND_CHUNK_WRITER_ACLS",
    "OWNER_APPROVED_WITNESS_REF_RULESET_CREATION",
    "OWNER_DECISION_ON_MAIN_REQUIRED_REVIEW_AND_CI_FRESHNESS",
    "LICENSED_VENDOR_DATA_RIGHTS_RETENTION_FIRST_KNOWN",
    "NONRESETTABLE_FLOOR_ADMIN_BYPASS_TAMPER_RECOVERY_PROOF",
)
_FALSE = (
    "witness_ref_provisioned", "signer_keys_enrolled",
    "independent_owners_attested", "actual_identity_bindings_approved",
    "required_real_main_approval_count_already_configured",
    "required_real_witness_signed_commit_policy_configured",
    "external_monotonic_floor_verified",
    "two_independent_authenticated_writer_cas_verified",
    "global_revoke_verified", "licensed_vendor_rights_verified",
    "physical_drive_chunk_readback_verified",
    "production_cache_read_authorized",
    "production_cache_write_authorized", "trading_authorized",
)
_REQUIRED_FAILURES = (
    "on_missing_principal", "on_duplicate_principal",
    "on_pr_ci_privileged_grant", "on_policy_admin_writer_overlap",
    "on_signer_writer_overlap", "on_revoker_self_approval",
    "on_missing_bypass_inventory", "on_owner_admin_policy_reset",
    "on_drive_chunk_not_readback", "on_unlicensed_vendor_data",
    "on_missing_external_floor", "on_missing_evidence",
)
_PRIVILEGED = (
    "CREATE_PROTECTED_WITNESS_REF", "APPLY_WITNESS_RULESET",
    "MODIFY_MAIN_RULESET", "ENROLL_SIGNER_KEYS",
    "ISSUE_WITNESS_WRITER_CREDENTIALS",
    "SHARE_DRIVE_TO_NEW_WRITER_OR_READER",
    "WRITE_LICENSED_MARKET_DATA", "MERGE_PR8",
    "ENABLE_RELEASE_OR_TRADING",
)


def check_role_topology(raw):
    """Validate exact zero-enrollment proposal and return a blocked review."""
    if type(raw) is not dict or raw.get("schema") != _SCHEMA:
        raise ValueError("INVALID_ROLE_TOPOLOGY_SCHEMA")
    if (raw.get("repository") != "ngluonghoa/MST"
            or raw.get("scope_choice") != "A_GITHUB_DRIVE_ONLY"
            or raw.get("status") != _STATUS
            or raw.get("owner_instruction_source")
            != "EXPLICIT_MST_USER_ARCHITECTURE_CHOICE_NOT_SIGNER_APPROVAL"
            or raw.get("baseline_main_commit")
            != "4048f91beaaa3410116d97e35896c8b688384e19"
            or raw.get("witness_ref") != "refs/heads/mst/m4-witness/v1"):
        raise ValueError("ROLE_POLICY_SOURCE_OR_SCOPE_DRIFT")
    for key in _FALSE:
        if raw.get(key) is not False:
            raise PermissionError("ROLE_PROPOSAL_CANNOT_SELF_AUTHORIZE_" + key)
    observed = (
        ("historical_observed_main_pr_review_approval_count", 0),
        ("historical_main_rule_includes_signed_commit", False),
        ("historical_witness_ref_absent", True),
        ("historical_google_drive_visible_owner_count_per_project_folder", 1),
    )
    for name, expected in observed:
        if type(raw.get(name)) is not type(expected) or raw[name] != expected:
            raise ValueError("ROLE_BASELINE_OBSERVATION_NOT_PRESERVED_" + name)
    roles = raw.get("roles")
    if type(roles) is not list or len(roles) != len(_ROLES):
        raise ValueError("EIGHT_UNASSIGNED_ROLES_REQUIRED")
    if [v.get("role") if type(v) is dict else None for v in roles] != list(_ROLES):
        raise ValueError("ROLE_ORDER_OR_IDENTITY_CHANGED")
    for i, role in enumerate(roles):
        if set(role) != {
            "role", "trust_boundary", "principal_binding", "independent_identity_verified",
            "proposed_capabilities", "forbidden_capabilities", "objective",
        }:
            raise ValueError("NONCANONICAL_ROLE_FIELDS")
        if role["trust_boundary"] != _BOUNDARIES[i]:
            raise ValueError("ROLE_TRUST_BOUNDARY_CHANGED")
        if role["principal_binding"] is not None or (
            role["independent_identity_verified"] is not False
        ):
            raise PermissionError("ROLE_IDENTITY_PREMATURELY_ENROLLED")
        if role["proposed_capabilities"] != list(_CAPABILITIES[i]):
            raise ValueError("ROLE_CAPABILITIES_ELEVATED_OR_REMOVED")
        if role["forbidden_capabilities"] != list(_FORBIDDEN[i]):
            raise ValueError("ROLE_FORBIDDEN_PERMISSION_REMOVED")
        if type(role["objective"]) is not str or not role["objective"].strip():
            raise ValueError("ROLE_OBJECTIVE_REQUIRED")
    if raw.get("required_distinct_principal_pairs") != [list(x) for x in _PAIRS]:
        raise ValueError("ROLE_SEPARATION_REQUIREMENTS_DRIFT")
    decisions = raw.get("owner_signoff_decisions")
    if type(decisions) is not list or len(decisions) != len(_OPEN):
        raise ValueError("EIGHT_OPEN_ROLE_DECISIONS_REQUIRED")
    for i, d in enumerate(decisions):
        if type(d) is not dict or set(d) != (
            {"code", "topic", "state", "approver_identity", "proof_uri"}
        ) or (
            d["code"] != f"R{i + 1:02d}"
            or d["topic"] != _OPEN[i] or d["state"] != "OPEN"
            or d["approver_identity"] is not None
            or d["proof_uri"] is not None
        ):
            raise PermissionError("UNREVIEWED_ROLE_DECISION_CLOSED_OR_FORGED")
    failures = raw.get("failure_policy")
    if type(failures) is not dict or set(failures) != set(_REQUIRED_FAILURES):
        raise ValueError("ROLE_DENY_POLICY_INCOMPLETE")
    for key in _REQUIRED_FAILURES:
        if failures[key] not in ("BLOCK", "UNVERIFIED_BLOCK", "QUARANTINE_BLOCK"):
            raise ValueError("UNSAFE_ROLE_FAILURE_POLICY_" + key)
    if raw.get("pending_privileged_actions") != list(_PRIVILEGED):
        raise PermissionError("PRIVILEGED_ACTIONS_MUST_REMAIN_OWNER_GATED")
    return {
        "schema": "mst.m4.option-a.role-topology.blocked-review.v1",
        "status": "OPTION_A_DUTY_SEPARATION_DESIGNED_ALL_REAL_ROLES_UNASSIGNED",
        "roles_proposed": len(_ROLES),
        "roles_with_actual_principals": 0,
        "required_distinct_principal_pairs": len(_PAIRS),
        "role_owner_decisions_open": len(_OPEN),
        "privileged_actions_blocked": len(_PRIVILEGED),
        "observed_main_positive_approval_requirement": False,
        "observed_witness_exists": False,
        "independent_admin_custody_verified": False,
        "external_monotonic_floor_verified": False,
        "production_cache_read_authorized": False,
        "production_cache_write_authorized": False,
        "trading_authorized": False,
    }


def analyze_hypothetical_aliases(bindings):
    """Show alias conflicts only; never infer independence from account names."""
    if type(bindings) is not dict or any(k not in _ROLES for k in bindings):
        raise ValueError("UNRECOGNIZED_ROLE_BINDING_INPUT")
    for k, v in bindings.items():
        if type(v) is not str or not v or len(v) > 128:
            raise ValueError("NONOPAQUE_HYPOTHETICAL_ALIAS")
    conflicts = [
        [a, b] for (a, b) in _PAIRS
        if a in bindings and b in bindings and bindings[a] == bindings[b]
    ]
    return {
        "status": "HYPOTHETICAL_ALIASES_NOT_IDENTITY_ATTESTATION",
        "roles_declared_for_simulation": len(bindings),
        "pairwise_conflicts": conflicts,
        "pairwise_constraints_satisfied_in_simulation": not conflicts and len(bindings) == len(_ROLES),
        "actual_independent_owner_identity_verified": False,
        "production_cache_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", type=Path, default=Path(
        "docs/MST_M4_OPTION_A_ROLE_SEPARATION_PROPOSAL_20261109.json"
    ))
    parser.add_argument("--option-a", type=Path, default=Path(
        "docs/MST_M4_OPTION_A_SCOPE_SELECTION_20261109.json"
    ))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    validate_option_a_choice(json.loads(args.option_a.read_text(encoding="utf-8")))
    receipt = check_role_topology(json.loads(args.proposal.read_text(encoding="utf-8")))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n",
                               encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
