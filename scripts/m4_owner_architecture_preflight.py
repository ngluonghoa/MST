"""M4 G01/G02 owner architecture ADR gate: validate unresolved proposals ONLY.

Intentional design: this validator cannot accept a production-ready decision.
Any future owner approval requires an independently governed process with a
NEW schema and direct owner evidence, never editing a PR draft flag to true.
No network, signer keys, vendor data, Drive cache writes or policy changes.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

_SCHEMA = "mst.m4.g01-g02.owner-decision.proposal.v1"
_STATUS = "DRAFT_UNSELECTED_OWNER_APPROVAL_REQUIRED"
_LOCK = {
    "swing_commit": "cd90c1babae8912db31490ad614fc2ad2f868042",
    "mst_main_commit": "4048f91beaaa3410116d97e35896c8b688384e19",
    "mst_main_tree": "d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e",
    "inherited_v1_modules": 63,
}
_DECISIONS = {
    "D01": ("SIGNED-G01", "CUSTODY_ARCHITECTURE_AND_SCOPE"),
    "D02": ("SIGNED-G01", "SIGNER_ENROLLMENT_AUTHORITY_AND_ADMIN_BYPASS"),
    "D03": ("SIGNED-G02", "DURABLE_FLOOR_AND_CAS_ROOT"),
    "D04": ("SIGNED-G03", "TWO_INDEPENDENT_PUBLISHERS_AND_READER_IDENTITY"),
    "D05": ("SIGNED-G04", "LICENSED_VENDOR_ASOF_CORRECTION_AND_RETENTION"),
    "D06": ("SIGNED-G06", "GLOBAL_REVOCATION_AND_RECOVERY"),
    "D07": ("SIGNED-G05", "ADDITIONAL_CLOUD_COST_RISK_DATA_RESIDENCY"),
    "D08": ("SIGNED-G08", "FINAL_OWNER_APPROVAL_A02_A03_M3_M4_M8"),
}
_OPTIONS = {
    "A_GITHUB_DRIVE_ONLY": ("CONDITIONAL_UNPROVEN", "EXISTING_GITHUB_DRIVE_ONLY", True),
    "B_CLOUD_KMS_FIRESTORE": (
        "REQUIRES_EXPLICIT_SCOPE_EXTENSION", "NEW_SERVICES_OWNER_PERMISSION_REQUIRED", True,
    ),
    "C_ACTIONS_CACHE_AS_ROOT": (
        "REJECTED_UNSAFE", "EXISTING_COMPONENTS_INSUFFICIENT", False,
    ),
}
_TESTS = (
    "G01-T01", "G01-T02", "G01-T03", "G02-T01", "G02-T02",
    "G02-T03", "G02-T04", "G02-T05", "G02-T06", "G02-T07",
    "M4-T08", "M4-T09", "M4-T10",
)
_FALSE = (
    "owner_approval_received", "production_cache_read_authorized",
    "production_cache_write_authorized", "trading_authorized",
    "external_trust_root_verified", "external_monotonic_floor_verified",
    "real_two_principal_server_cas_verified", "licensed_market_data_verified",
    "actual_google_drive_chunk_sha_verified",
)
_TRUE_INVARIANTS = (
    "external_owner_authority_required",
    "provider_rights_separate_from_publisher_signature",
    "signatures_do_not_prove_market_truth",
    "writer_cannot_reset_floor", "reader_must_refetch_external_floor",
    "recovery_never_lowers_floor", "key_rotation_must_preserve_generation",
    "github_drive_not_single_transaction",
    "any_missing_independent_evidence_blocks",
    "vendor_late_corrections_not_naively_rejected_by_clock",
    "root_admin_reset_risk_must_be_reviewed",
    "github_pr_workflows_read_only",
)


def validate_owner_architecture_draft(raw):
    if type(raw) is not dict:
        raise TypeError("OWNER_ARCHITECTURE_DRAFT_DICT_REQUIRED")
    expected_keys = {
        "schema", "project", "repository", "source_lock", "status", "adr",
        "owner_approval_received", "production_cache_read_authorized",
        "production_cache_write_authorized", "trading_authorized",
        "external_trust_root_verified", "external_monotonic_floor_verified",
        "real_two_principal_server_cas_verified", "licensed_market_data_verified",
        "actual_google_drive_chunk_sha_verified", "options", "owner_decisions",
        "required_witness_tests", "security_invariants", "operational_status",
    }
    if set(raw) != expected_keys:
        raise ValueError("NONCANONICAL_ARCHITECTURE_DRAFT_FIELDS")
    if raw.get("schema") != _SCHEMA or raw.get("status") != _STATUS:
        raise ValueError("UNAPPROVED_OR_MODIFIED_DECISION_SCHEMA")
    if raw.get("project") != "MST" or raw.get("repository") != "ngluonghoa/MST":
        raise ValueError("WRONG_ARCHITECTURE_REPOSITORY")
    if raw.get("source_lock") != _LOCK:
        raise ValueError("PINNED_V1_SOURCE_LOCK_CHANGED")
    if raw.get("adr") != "docs/MST_M4_ADR_G01_G02_TRUST_ROOT_MONOTONIC_FLOOR_20261109.md":
        raise ValueError("INVALID_OWNER_ADR_REFERENCE")
    if raw.get("operational_status") != "ARCHITECTURE_REVIEW_ONLY_PRODUCTION_BLOCKED":
        raise PermissionError("UNAUTHORIZED_ARCHITECTURE_PROMOTION")
    for field in _FALSE:
        if raw.get(field) is not False:
            raise PermissionError("UNAUTHORIZED_OWNER_GATE_SELF_APPROVAL_" + field)
    options = raw.get("options")
    if type(options) is not list or len(options) != 3:
        raise ValueError("THREE_OWNER_ARCHITECTURE_OPTIONS_REQUIRED")
    if [o.get("id") if type(o) is dict else None for o in options] != list(_OPTIONS):
        raise ValueError("ARCHITECTURE_OPTIONS_CHANGED")
    for option in options:
        if set(option) != {
            "id", "status", "scope", "is_selected", "owner_approval_required",
            "description", "blocks",
        }:
            raise ValueError("NONCANONICAL_ARCHITECTURE_OPTION_FIELDS")
        expected_status, expected_scope, needs_approval = _OPTIONS[option["id"]]
        if (option.get("status") != expected_status
                or option.get("scope") != expected_scope
                or option.get("owner_approval_required") is not needs_approval):
            raise ValueError("ARCHITECTURE_OPTION_STATUS_OR_SCOPE_DRIFT")
        if option.get("is_selected") is not False:
            raise PermissionError("ARCHITECTURE_CHOSEN_WITHOUT_OWNER")
        if type(option.get("description")) is not str or not option["description"].strip():
            raise ValueError("MISSING_ARCHITECTURE_TRADEOFF_DESCRIPTION")
        blocks = option.get("blocks")
        if type(blocks) is not list or not blocks or any(
            type(v) is not str or not v for v in blocks
        ):
            raise ValueError("MISSING_UNRESOLVED_ARCHITECTURE_BLOCKERS")
    decisions = raw.get("owner_decisions")
    if type(decisions) is not list or len(decisions) != len(_DECISIONS):
        raise ValueError("EIGHT_OWNER_DECISIONS_REQUIRED")
    if [x.get("id") if type(x) is dict else None for x in decisions] != list(_DECISIONS):
        raise ValueError("OWNER_DECISION_IDS_CHANGED")
    for decision in decisions:
        if set(decision) != {
            "id", "gate", "decision", "state", "chosen", "owner_evidence_uri",
        }:
            raise ValueError("NONCANONICAL_OWNER_DECISION_FIELDS")
        gate, name = _DECISIONS[decision["id"]]
        if decision.get("gate") != gate or decision.get("decision") != name:
            raise ValueError("OWNER_DECISION_TAXONOMY_DRIFT")
        if decision.get("state") != "OPEN":
            raise PermissionError("OWNER_DECISION_CLOSED_WITHOUT_PROOF")
        if decision.get("chosen") is not None or decision.get("owner_evidence_uri") is not None:
            raise PermissionError("OWNER_DECISION_SELF_ATTESTATION")
    if raw.get("required_witness_tests") != list(_TESTS):
        raise ValueError("INDEPENDENT_WITNESS_ACCEPTANCE_TESTS_REMOVED")
    invariants = raw.get("security_invariants")
    if type(invariants) is not dict or set(invariants) != set(_TRUE_INVARIANTS):
        raise ValueError("SECURITY_INVARIANT_LIST_CHANGED")
    for field in _TRUE_INVARIANTS:
        if invariants[field] is not True:
            raise ValueError("MANDATORY_SECURITY_INVARIANT_FALSE_" + field)
    return {
        "schema": "mst.m4.owner-architecture-preflight.blocked.v1",
        "status": "G01_G02_ARCHITECTURE_REVIEW_ONLY_BLOCKED",
        "owner_options_unselected": len(options),
        "owner_decisions_open": len(decisions),
        "independent_witness_tests_required": len(_TESTS),
        "source_main_pinned": True,
        "g01_verified": False,
        "g02_verified": False,
        "new_cloud_services_authorized": False,
        "production_cache_read_authorized": False,
        "production_cache_write_authorized": False,
        "trading_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(
        "docs/MST_M4_G01_G02_OWNER_DECISIONS_20261109.json"
    ))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    rawbytes = args.input.read_bytes()
    review = validate_owner_architecture_draft(json.loads(rawbytes))
    review["untrusted_draft_sha256"] = sha256(rawbytes).hexdigest()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(review, sort_keys=True, indent=2) + "\n",
                               encoding="utf-8")
    print(json.dumps(review, sort_keys=True))


if __name__ == "__main__":
    main()
