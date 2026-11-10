"""A03 supplier-proof owner intake contract, public UNAPPROVED requirements only.

This is deliberately NOT a cryptographic provider verifier or license checker.
No real evidence is read here; a caller cannot grant its own independent trust.
Reuses existing M4 E03/E08/E11/E12/E13/E14; no duplicate owner authority.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

SCHEMA = "mst.a03.supplier-owner-proof-acceptance.public-unapproved.v1"
PACKET_PATH = Path("docs/MST_A03_SUPPLIER_OWNER_PROOF_PACKET_UNAPPROVED_20261110.json")
M4_PATH = Path("docs/MST_M4_OPTION_A_PRIVATE_OWNER_EVIDENCE_INTAKE_20261110.json")
SOURCE = "cd90c1babae8912db31490ad614fc2ad2f868042"
MAIN = "4048f91beaaa3410116d97e35896c8b688384e19"
TREE = "d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e"
CROSSWALK = {
    "A03-OWNER-SOURCE-HEAD-CLOSURE-11": ("E11", "E14"),
    "A03-OWNER-INDEPENDENT-CUSTODY-12": ("E03", "E14"),
    "A03-OWNER-DURABLE-FLOOR-13": ("E08", "E13"),
    "A03-OWNER-LICENSED-REPLAY-14": ("E11", "E12"),
}
SCENARIOS = (
    "CALLER_REPLACES_PUBLIC_KEY",
    "SIGNED_HISTORY_REHASHED",
    "SELF_CLAIMED_TWO_VIEWERS",
    "SAME_ACCOUNT_DIFFERENT_ROLE_LABELS",
    "MISSING_MIDDLE_CORRECTION",
    "TOMBSTONE_RESURRECTION",
    "FUTURE_CORRECTION_LEAKS_ASOF",
    "UNOFFICIAL_SESSION_CALENDAR",
    "UNATTESTED_KEY_REVOCATION",
    "FRESH_RUN_RESET_FLOOR",
    "TWO_SIGNED_FORKS_PASS_SEPARATELY",
    "ADMIN_BYPASS_OF_PROTECTED_REF",
    "VENDOR_RIGHTS_ONLY_SELF_DECLARED",
    "DRIVE_LINK_WITHOUT_PHYSICAL_BYTES",
    "SINGLE_CONNECTED_ACCOUNT_APPROVAL",
    "UNSIGNED_RELEASE_OWNER_DECISION",
)
ADMISSIONS = (
    "provider_issued_root_authenticated",
    "provider_revision_head_complete",
    "independent_source_viewer_custody_verified",
    "nonresettable_cross_run_floor_verified",
    "two_writer_server_cas_verified",
    "licensed_market_data_and_drive_retention_authorized",
    "physical_drive_market_cache_verified",
    "qualified_market_signal_authorized",
    "production_release_authorized",
    "trading_authorized",
)
HANDLING = (
    "public_requirements_only",
    "no_private_principal_or_key_or_evidence_url",
    "no_real_provider_api_calls",
    "no_vendor_market_cache_writes",
    "no_privileged_github_mutation",
    "no_merge_or_release",
)
EXPECTED_KEYS = {
    "schema", "repository", "architecture", "source_pin",
    "protected_main_pin", "source_tree_pin", "prior_m4_private_intake",
    "status", "owner_choices_approved", "owner_choices_total",
    "a02_original_module_owner_approved", "a03_opt_in_v2_owner_approved",
    "requirements", "untrusted_claim_scenarios", "admissions", "handling",
}
REQUIREMENT_KEYS = {
    "gate", "existing_m4_requirement_ids", "acceptance_checks", "proof_state",
    "owner_approved", "independent_verifier_attested",
}
SCENARIO_KEYS = {"id", "gate", "missing_independent_proof", "expected"}
FORBIDDEN_TOKENS = ("http://", "https://", "@", "BEGIN PRIVATE KEY", "ghp_", "github_pat_", "AIza")


def _equals(actual, expected, error):
    if type(actual) is not type(expected) or actual != expected:
        raise ValueError(error)


def validate_packet(packet: dict, m4_intake: dict) -> dict:
    """Strict frozen public preflight. Pass means REQUIREMENTS COMPLETE, not approved."""
    if type(packet) is not dict or set(packet) != EXPECTED_KEYS:
        raise ValueError("A03_PUBLIC_PACKET_TOP_LEVEL_DRIFT")
    for key, expected in (
        ("schema", SCHEMA), ("repository", "ngluonghoa/MST"),
        ("architecture", "OPTION_A_GITHUB_GOOGLE_DRIVE_ONLY"),
        ("source_pin", SOURCE), ("protected_main_pin", MAIN),
        ("source_tree_pin", TREE),
        ("prior_m4_private_intake", str(M4_PATH)),
        ("status", "REQUIREMENTS_ONLY_ALL_OWNER_PROOFS_NOT_RECEIVED_NO_GO"),
        ("owner_choices_approved", 0), ("owner_choices_total", 14),
        ("a02_original_module_owner_approved", 0),
        ("a03_opt_in_v2_owner_approved", 0),
    ):
        _equals(packet[key], expected, "A03_AUTHORITY_OR_SOURCE_PIN_DRIFT_" + key)
    if type(m4_intake) is not dict or type(m4_intake.get("evidence_requirements")) is not list:
        raise ValueError("M4_PRIVATE_INTAKE_NOT_READABLE")
    m4 = {r.get("id"): r for r in m4_intake["evidence_requirements"]
          if type(r) is dict}
    if set(m4) != {f"E{i:02d}" for i in range(1, 15)}:
        raise ValueError("M4_14_EVIDENCE_REQUIREMENTS_MISSING")
    for id_ in {e for refs in CROSSWALK.values() for e in refs}:
        r = m4[id_]
        if r.get("state") != "NOT_RECEIVED" or r.get("independently_verified") is not False or r.get("owner_reviewed") is not False:
            raise PermissionError("M4_PRIVATE_REQUIREMENT_FALSELY_CLOSED_" + id_)
        for secret in ("private_evidence_uri", "principal_binding", "signer_fingerprint", "verifier_attestation_uri"):
            if r.get(secret) is not None:
                raise PermissionError("M4_PRIVATE_IDENTIFIER_PUBLISHED_" + id_)
    requirements = packet["requirements"]
    if type(requirements) is not list or len(requirements) != 4:
        raise ValueError("A03_FOUR_OWNER_PROOFS_REQUIRED")
    for row, (gate, requirements_ids) in zip(requirements, CROSSWALK.items()):
        if type(row) is not dict or set(row) != REQUIREMENT_KEYS:
            raise ValueError("A03_PUBLIC_REQUIREMENT_FIELDS_DRIFT")
        _equals(row["gate"], gate, "A03_GATE_ORDER_OR_NAME_DRIFT")
        _equals(row["existing_m4_requirement_ids"], list(requirements_ids),
                "A03_DUPLICATE_OR_MISSING_M4_CROSSWALK")
        _equals(row["proof_state"], "NOT_RECEIVED", "A03_OWNER_PROOF_NOT_RECEIVED")
        for boolean in ("owner_approved", "independent_verifier_attested"):
            if row[boolean] is not False:
                raise PermissionError("A03_SELF_APPROVAL_PROHIBITED_" + boolean)
        checks = row["acceptance_checks"]
        if type(checks) is not list or len(checks) != 3 or any(
                type(c) is not str or len(c) < 65 or any(bad in c for bad in FORBIDDEN_TOKENS)
                for c in checks):
            raise ValueError("A03_INDEPENDENT_ACCEPTANCE_CHECKLIST_INCOMPLETE_OR_SENSITIVE")
        if len(set(checks)) != 3:
            raise ValueError("A03_DUPLICATE_ACCEPTANCE_CHECK")
    scenarios = packet["untrusted_claim_scenarios"]
    if type(scenarios) is not list or len(scenarios) != len(SCENARIOS):
        raise ValueError("A03_UNTRUSTED_PROOF_NEGATIVE_COVERAGE_MISSING")
    for scenario, scenario_id in zip(scenarios, SCENARIOS):
        if type(scenario) is not dict or set(scenario) != SCENARIO_KEYS:
            raise ValueError("A03_UNTRUSTED_PROOF_CASE_STRUCTURE_DRIFT")
        _equals(scenario["id"], scenario_id, "A03_NEGATIVE_CASE_ID_DRIFT")
        if scenario["gate"] not in CROSSWALK:
            raise ValueError("A03_NEGATIVE_CASE_UNKNOWN_GATE")
        _equals(scenario["expected"], "NO_GO_UNTRUSTED_PROOF_CLAIM",
                "A03_NEGATIVE_CASE_PREMATURE_PROMOTION")
        if type(scenario["missing_independent_proof"]) is not str or len(scenario["missing_independent_proof"]) < 20:
            raise ValueError("A03_NEGATIVE_CASE_NO_INDEPENDENT_PROOF_CONDITION")
    if type(packet["admissions"]) is not dict or set(packet["admissions"]) != set(ADMISSIONS):
        raise ValueError("A03_ADMISSION_FIELDS_DRIFT")
    for key in ADMISSIONS:
        if packet["admissions"][key] is not False:
            raise PermissionError("A03_NONOWNER_CANNOT_GRANT_" + key)
    if type(packet["handling"]) is not dict or set(packet["handling"]) != set(HANDLING):
        raise ValueError("A03_PUBLIC_DATA_HANDLING_FIELDS_DRIFT")
    for key in HANDLING:
        if packet["handling"][key] is not True:
            raise PermissionError("A03_PUBLIC_PRIVACY_OR_NO_APPLY_RULE_WEAKENED_" + key)
    # Only public requirements and not identifiers or live proof content.
    case_ids = [x["id"] for x in scenarios]
    receipt = {
        "schema": SCHEMA,
        "status": "PUBLIC_REQUIREMENTS_PREFLIGHT_PASS_ALL_REAL_EVIDENCE_ABSENT_OWNER_NO_GO",
        "owner_gate_count": len(requirements),
        "acceptance_check_count": sum(len(x["acceptance_checks"]) for x in requirements),
        "untrusted_negative_case_count": len(scenarios),
        "negative_case_ids": case_ids,
        "m4_existing_requirement_ids": sorted({e for refs in CROSSWALK.values() for e in refs}),
        "a03_owner_choices_approved": 0,
        "a02_original_module_owner_approved": 0,
        "a03_v2_owner_approved": 0,
        "externally_authenticated_supplier": False,
        "independently_proven_custody": False,
        "nonresettable_floor_and_real_cas": False,
        "licensed_google_drive_cache": False,
        "real_source_qualified_signal": False,
        "production_release": False,
        "trading": False,
    }
    canonical = json.dumps({"gates": list(CROSSWALK), "cases": case_ids}, sort_keys=True,
                           separators=(",", ":"), ensure_ascii=True)
    receipt["public_requirement_index_sha256"] = sha256(canonical.encode()).hexdigest()
    return receipt


def evaluate_untrusted_claim(claim: dict) -> dict:
    """An apparently complete self-claim can NEVER be promoted to evidence.

    Independently obtained provider/owner proof would require a separately
    approved, private, access-controlled process not implemented in this tool.
    """
    if type(claim) is not dict or set(claim) != {
        "claims_vendor_issuer_authentic", "claims_separate_custody",
        "claims_durable_floor", "claims_licensed_drive_cache",
        "claims_owner_approved",
    }:
        raise ValueError("UNTRUSTED_CLAIM_SHAPE_INVALID")
    if any(type(v) is not bool for v in claim.values()):
        raise TypeError("UNTRUSTED_CLAIM_EXACT_BOOLEAN_REQUIRED")
    return {
        "classification": "UNTRUSTED_SELF_CLAIM_REQUIRES_INDEPENDENT_PRIVATE_PROOF_NO_GO",
        "provider_verified": False,
        "owner_approved": False,
        "production_release": False,
        "trading": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--packet", type=Path, default=PACKET_PATH)
    p.add_argument("--existing-m4", type=Path, default=M4_PATH)
    p.add_argument("--out", type=Path)
    a = p.parse_args(argv)
    result = validate_packet(json.loads(a.packet.read_text(encoding="utf-8")),
                             json.loads(a.existing_m4.read_text(encoding="utf-8")))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
