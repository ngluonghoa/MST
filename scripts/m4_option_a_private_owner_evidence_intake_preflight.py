"""MST M4 Option A owner-private evidence intake: PUBLIC requirements, NO evidence.

The publicly versioned JSON is intentionally a zero-intake checklist. It is
NOT a storage location for real subject identifiers, signatures, private links,
API tokens, key fingerprints, owner attestations, or approval records.

Reuses the existing root-threat and G01-G03 no-go validators and the two
separate GitHub Actions read-only REST receipts. Passing always BLOCKS.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from scripts.m4_option_a_effective_authority_threat_preflight import (
    THREAT_PATH, evaluate_threats,
)
from scripts.m4_option_a_g01_g03_owner_packet_preflight import (
    PACKET_PATH, ROLE_PATH, DRIVE_PATH, OPTION_PATH,
)

SCHEMA = "mst.m4.option-a.private-owner-evidence-intake.plan.unapproved.v1"
INTAKE_PATH = Path("docs/MST_M4_OPTION_A_PRIVATE_OWNER_EVIDENCE_INTAKE_20261110.json")
_GATES = tuple(f"G{i:02d}" for i in range(1, 9))
_OA = tuple(f"OA{i:02d}" for i in range(1, 7))
_IDS = tuple(f"E{i:02d}" for i in range(1, 15))
_THREATS = tuple(f"T{i:02d}" for i in range(1, 13))

# Exact REQUIREMENT classes, never actual authenticated account or key data.
_REQUIREMENTS = (
    ("E01", "GITHUB_EFFECTIVE_ADMIN_BYPASS_INVENTORY",
     ("G01",), ("OA01", "OA05"), ("T01", "T08", "T12")),
    ("E02", "PROTECTED_WITNESS_REF_RULESET_OWNER_READBACK",
     ("G02",), ("OA02",), ("T02",)),
    ("E03", "SIGNER_ROOT_INDEPENDENT_ENROLLMENT",
     ("G01",), ("OA01", "OA02"), ("T03", "T09")),
    ("E04", "EPOCH_REVOCATION_ADMIN_RECOVERY",
     ("G02", "G06"), ("OA02", "OA05"), ("T04",)),
    ("E05", "TWO_INDEPENDENT_AUTHENTICATED_WRITERS",
     ("G03",), ("OA03",), ("T06",)),
    ("E06", "PR_ACTIONS_SECRET_AND_ROLE_ISOLATION",
     ("G01", "G07"), ("OA01", "OA03"), ("T07",)),
    ("E07", "GOOGLE_DRIVE_EFFECTIVE_OWNER_ACL_AND_RETENTION",
     ("G05",), ("OA04",), ("T05",)),
    ("E08", "RESTART_PROOF_EXTERNAL_MONOTONIC_FLOOR",
     ("G02",), ("OA02",), ("T10",)),
    ("E09", "TWO_SERVICE_COMMIT_RECOVERY_READ_BARRIER",
     ("G03", "G05"), ("OA04",), ("T11",)),
    ("E10", "OWNER_SIGNED_SHARED_ROOT_RISK_DECISION",
     ("G01", "G02", "G08"), ("OA05",), ("T01", "T04")),
    ("E11", "LICENSED_VENDOR_FIRST_KNOWN_RIGHTS_RETENTION",
     ("G04",), ("OA04",), ("T05",)),
    ("E12", "OWNER_SIGNED_A02_A03_RELEASE_APPROVALS",
     ("G08",), ("OA06",), ()),
    ("E13", "INDEPENDENT_TWO_PRINCIPAL_SERVER_CAS_PROOF",
     ("G03",), ("OA03",), ("T02", "T06")),
    ("E14", "EVIDENCE_PROVENANCE_TWO_VIEWER_RECONCILIATION",
     ("G07",), ("OA01", "OA05"), ("T08", "T12")),
)
_TOP_FIELDS = {
    "schema", "repository", "dated_local", "architecture", "source_pin_main",
    "upstream_pin", "source_tree", "existing_root_threat_register",
    "existing_owner_bridge", "existing_role_matrix",
    "existing_drive_acl_snapshot", "status",
    "public_repository_has_private_owner_identifiers",
    "actual_private_evidence_intake_channel_approved",
    "independent_owner_or_signer_verified", "source_of_truth_source",
    "existing_options_owner_decisions", "existing_security_gates",
    "evidence_requirements", "ingestion_safety", "admissions",
    "next_owner_action",
}
_UNSAFE_PUBLIC_ACCEPTANCE = (
    re.compile(r"[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}"),
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"-----BEGIN[ -](?:RSA|OPENSSH|EC|PRIVATE)", re.IGNORECASE),
    re.compile(r"(?:github_pat_|ghp_|gho_|ghs_|AIza)[A-Za-z0-9_-]{3,}"),
    re.compile(r"(?:password|secret|private[_ -]?key|token)\s*[:=]\s*\S+", re.IGNORECASE),
)
_META_FIELDS = {
    "id", "kind", "gates", "decisions", "threats", "acceptance", "state",
    "private_evidence_uri", "principal_binding", "signer_fingerprint",
    "verifier_attestation_uri", "independently_verified", "owner_reviewed",
}
_NULL = (
    "private_evidence_uri", "principal_binding", "signer_fingerprint",
    "verifier_attestation_uri",
)
_POLICY_TRUE = (
    "public_git_contains_requirements_only",
    "public_git_cannot_hold_private_evidence_uri_or_identity",
    "no_private_signer_keys_or_provider_tokens",
    "never_export_raw_credential_or_personal_identity",
    "evidence_from_single_connected_account_not_independent",
    "two_viewer_attestation_not_currently_available",
)
_POLICY_FALSE = (
    "access_controlled_external_evidence_store_proven",
    "private_owner_channel_provisioned",
)
_ADMISSIONS_FALSE = (
    "live_github_bypass_inventory_independent",
    "protected_witness_ref_exists",
    "drive_independent_readonly_custody",
    "externally_authenticated_signer",
    "cross_run_nonresettable_floor",
    "independent_multiwriter_server_cas",
    "owner_signed_decision_available",
    "effective_control_plane_separation_proven",
    "physical_licensed_drive_market_cache_verified",
    "production_cache_read_authorized", "production_cache_write_authorized",
    "production_release_authorized", "trading_authorized",
)


def _equals(actual, expected, reason):
    if type(actual) is not type(expected) or actual != expected:
        raise ValueError(reason)


def _false(obj, keys, reason):
    if type(obj) is not dict:
        raise TypeError(reason + "_DICT_REQUIRED")
    for key in keys:
        if obj.get(key) is not False:
            raise PermissionError(reason + "_" + key)


def verify_intake(
    intake: dict, root_register: dict, owner_packet: dict, role_matrix: dict,
    historical_drive: dict, selected_option: dict,
    current_github_custody: dict, current_github_readiness: dict,
) -> dict:
    """Validate a totally empty, unapproved PRIVATE owner intake plan.

    Real evidence must be handled separately with owner-controlled private
    access, identity/custody proofs and a DIFFERENT approved workflow. Even a
    full checklist can NEVER be a signer or release credential.
    """
    threat_receipt = evaluate_threats(
        root_register, owner_packet, role_matrix, historical_drive,
        selected_option, current_github_custody, current_github_readiness,
    )
    if type(intake) is not dict:
        raise TypeError("PRIVATE_INTAKE_PLAN_DICT_REQUIRED")
    if set(intake) != _TOP_FIELDS:
        raise PermissionError("PUBLIC_PRIVATE_INTAKE_ADDED_UNREVIEWED_TOP_LEVEL_FIELDS")
    for key, expected in (
        ("schema", SCHEMA),
        ("repository", "ngluonghoa/MST"),
        ("architecture", "OPTION_A_GITHUB_GOOGLE_DRIVE_ONLY"),
        ("source_pin_main", "4048f91beaaa3410116d97e35896c8b688384e19"),
        ("upstream_pin", "cd90c1babae8912db31490ad614fc2ad2f868042"),
        ("source_tree", "d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e"),
        ("existing_root_threat_register", str(THREAT_PATH)),
        ("existing_owner_bridge", str(PACKET_PATH)),
        ("existing_role_matrix", str(ROLE_PATH)),
        ("existing_drive_acl_snapshot", str(DRIVE_PATH)),
        ("status", "PRIVATE_OWNER_EVIDENCE_REQUIREMENTS_NOT_COLLECTED_PRODUCTION_BLOCKED"),
        ("public_repository_has_private_owner_identifiers", False),
        ("actual_private_evidence_intake_channel_approved", False),
        ("independent_owner_or_signer_verified", False),
        ("source_of_truth_source",
         "EXISTING_OWNER_BRIDGE_AND_ROLE_MATRIX_NOT_AN_INDEPENDENT_AUTHORITY"),
    ):
        _equals(intake.get(key), expected, "PRIVATE_INTAKE_SCOPE_OR_AUTHORITY_DRIFT_" + key)
    if intake.get("existing_options_owner_decisions") != list(_OA):
        raise PermissionError("OWNER_DECISIONS_NOT_ALL_OPEN_AND_LISTED")
    if intake.get("existing_security_gates") != list(_GATES):
        raise PermissionError("SECURITY_GATES_NOT_ALL_OPEN_AND_LISTED")
    if threat_receipt["scenario_count"] != len(_THREATS):
        raise PermissionError("ROOT_THREAT_REGISTRY_NOT_COMPLETE")
    proofs = intake.get("evidence_requirements")
    if type(proofs) is not list or len(proofs) != len(_REQUIREMENTS):
        raise ValueError("EXACT_FOURTEEN_PRIVATE_EVIDENCE_REQUIREMENTS_REQUIRED")
    covered_gates, covered_decisions, covered_threats = set(), set(), set()
    for actual, requirement in zip(proofs, _REQUIREMENTS):
        if type(actual) is not dict or set(actual) != _META_FIELDS:
            raise PermissionError("PUBLIC_INTAKE_ADDED_PRIVATE_OR_UNREVIEWED_FIELDS")
        id_, kind, gates, decisions, threats = requirement
        for name, expected in (
            ("id", id_), ("kind", kind), ("gates", list(gates)),
            ("decisions", list(decisions)), ("threats", list(threats)),
            ("state", "NOT_RECEIVED"),
        ):
            _equals(actual.get(name), expected, "INTAKE_REQUIRED_EVIDENCE_DRIFT_" + id_)
        if type(actual.get("acceptance")) is not str or len(actual["acceptance"]) < 60:
            raise ValueError("INDEPENDENT_ACCEPTANCE_EVIDENCE_DESCRIPTION_MISSING_" + id_)
        if any(pattern.search(actual["acceptance"]) for pattern in _UNSAFE_PUBLIC_ACCEPTANCE):
            raise PermissionError("PRIVATE_IDENTIFIER_OR_SECRET_IN_PUBLIC_ACCEPTANCE_" + id_)
        for sensitive in _NULL:
            if actual[sensitive] is not None:
                raise PermissionError("PRIVATE_EVIDENCE_OR_IDENTITY_IN_PUBLIC_REPO_" + id_)
        _false(actual, ("independently_verified", "owner_reviewed"),
               "UNSIGNED_OWNER_EVIDENCE_SELF_ATTESTED_" + id_)
        covered_gates.update(gates)
        covered_decisions.update(decisions)
        covered_threats.update(threats)
    if covered_gates != set(_GATES) or covered_decisions != set(_OA) or (
        covered_threats != set(_THREATS)
    ):
        raise ValueError("INDEPENDENT_OWNER_EVIDENCE_COVERAGE_INCOMPLETE")
    safety = intake.get("ingestion_safety")
    if type(safety) is not dict or set(safety) != (
        set(_POLICY_TRUE) | set(_POLICY_FALSE)
    ):
        raise ValueError("PRIVATE_INTAKE_POLICY_INCOMPLETE")
    for key in _POLICY_TRUE:
        _equals(safety.get(key), True, "PRIVATE_INTAKE_DATA_SAFETY_WEAKENED_" + key)
    _false(safety, _POLICY_FALSE, "NONEXISTENT_PRIVATE_EVIDENCE_CUSTODY_CLAIMED")
    admission = intake.get("admissions")
    if type(admission) is not dict or set(admission) != set(_ADMISSIONS_FALSE):
        raise ValueError("PRODUCTION_ADMISSION_GATES_INCOMPLETE")
    _false(admission, _ADMISSIONS_FALSE, "PREMATURE_G01_G08_RELEASE_APPROVAL")
    if intake.get("next_owner_action") != (
        "PRIVATE_ROLE_AND_BYPASS_EVIDENCE_INTAKE_APPROVAL_THEN_INDEPENDENT_READ_ONLY_VERIFICATION_NO_APPLY"
    ):
        raise PermissionError("OWNER_EVIDENCE_INTAKE_SCOPE_ESCALATION")
    return {
        "schema": SCHEMA,
        "status": "FOURTEEN_PRIVATE_OWNER_REQUIREMENTS_RECONCILED_ALL_UNRECEIVED_NO_GO",
        "external_evidence_items_required": len(proofs),
        "external_evidence_items_received": 0,
        "owner_decisions_open": len(_OA),
        "security_gates_open": list(_GATES),
        "root_threats_covered": len(_THREATS),
        "owner_role_principals_verified": 0,
        "private_credential_or_principal_written_to_public_git": False,
        "actual_independently_controlled_private_intake_store_proven": False,
        "connected_github_admin_is_not_independent_bypass_attestation": True,
        "github_actions_bypass_visibility_is_not_global_proof": True,
        "google_drive_single_owner_role_is_not_independent_custody": True,
        "external_signer": False,
        "nonresettable_external_floor": False,
        "real_two_writer_server_cas": False,
        "privileged_changes_performed": False,
        "production_cache_read_authorized": False,
        "production_cache_write_authorized": False,
        "production_release_authorized": False,
        "trading_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", type=Path, default=INTAKE_PATH)
    parser.add_argument("--threats", type=Path, default=THREAT_PATH)
    parser.add_argument("--owner", type=Path, default=PACKET_PATH)
    parser.add_argument("--roles", type=Path, default=ROLE_PATH)
    parser.add_argument("--drive", type=Path, default=DRIVE_PATH)
    parser.add_argument("--option", type=Path, default=OPTION_PATH)
    parser.add_argument("--live-custody", type=Path, required=True)
    parser.add_argument("--live-readiness", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    def read(path):
        return json.loads(path.read_text(encoding="utf-8"))
    receipt = verify_intake(
        read(args.intake), read(args.threats), read(args.owner),
        read(args.roles), read(args.drive), read(args.option),
        read(args.live_custody), read(args.live_readiness),
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
