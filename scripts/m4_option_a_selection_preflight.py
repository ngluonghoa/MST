"""MST M4 owner architecture choice A — scope selection only, NEVER custody.

A user explicitly selected GitHub + Google Drive as the permitted MST
architecture. This read-only guard records that *choice*, not authenticated
signer enrollment, owner key attestation, permission to create witness refs,
real OHLCV entitlements, or any authority to trade.

The historical unselected ADR proposal is left immutable. A versioned
selection overlay takes precedence for architecture choice ONLY.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

SCHEMA = "mst.m4.option-a.scope-decision.v1"
CHOICE_STATUS = "OPTION_A_CHOSEN_SCOPE_ONLY_G01_G08_STILL_OPEN"
SOURCE = {
    "swing_commit": "cd90c1babae8912db31490ad614fc2ad2f868042",
    "mst_main_commit": "4048f91beaaa3410116d97e35896c8b688384e19",
    "mst_main_tree": "d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e",
    "inherited_v1_modules": 63,
}
FALSE_FLAGS = (
    "selection_is_production_approval",
    "additional_cloud_services_approved",
    "kms_firestore_approved",
    "app_main_merge_approved",
    "privileged_witness_repo_or_ruleset_provisioning_approved",
    "signer_enrollment_approved",
    "production_credentials_approved",
    "licensed_vendor_data_ingestion_approved",
    "real_google_drive_market_cache_promotion_approved",
    "production_cache_read_authorized",
    "production_cache_write_authorized",
    "trading_authorized",
    "independent_owner_identity_attested",
    "independent_signer_root_verified",
    "protected_monotonic_registry_receipt_floor_verified",
    "global_revocation_verified",
    "two_independent_writer_cas_verified",
    "physical_licensed_drive_chunk_verified",
    "eight_signed_gates_closed",
)
TRUE_FLAGS = (
    "architecture_choice_recorded",
    "architecture_choice_scope_approved",
    "prior_proposal_is_historical_unselected_snapshot",
)
OPEN_GATES = [f"SIGNED-G{n:02d}" for n in range(1, 9)]
CONTROLS = [
    "SEPARATE_OWNER_CONTROLLED_GITHUB_WITNESS_CUSTODY",
    "NO_PR_TOKEN_OR_ACTIONS_CACHE_AS_TRUST_ROOT",
    "SIGNED_OWNER_APPROVED_REGISTRY_WITH_REVOCATION",
    "PROTECTED_APPEND_ONLY_WITNESS_FIRST_PARENT_AND_EXTERNAL_READBACK",
    "FLOOR_REGISTRY_PARTITION_RIGHTS_EPOCH_LINEAGE",
    "TWO_AUTHENTICATED_PUBLISHERS_SINGLE_WINNER_SERVER_CAS",
    "ACTUAL_LICENSED_GOOGLE_DRIVE_IMMUTABLE_CHUNK_BYTES",
    "FAIL_CLOSED_CROSS_SERVICE_READ_BARRIER_AND_CRASH_RECOVERY",
    "ADMIN_BYPASS_TAMPER_RESPONSE_AND_ROOT_RESET_TEST",
]
BLOCKED_ACTIONS = [
    "CREATE_OR_MODIFY_PROTECTED_WITNESS_REF",
    "CHANGE_GITHUB_RULESETS",
    "ISSUE_SIGNING_KEYS",
    "ENROLL_REAL_VENDOR_SOURCE",
    "PUBLISH_REAL_MARKET_CACHE",
    "MERGE_PR8",
    "ISSUE_REAL_TRADES",
]
REQUIRED_STRINGS = {
    "schema": SCHEMA,
    "project": "MST",
    "repository": "ngluonghoa/MST",
    "recorded_date": "2026-11-09",
    "decision_source": "EXPLICIT_USER_MESSAGE_IN_MST_CHAT",
    "decision_source_quote": "Đồng ý phương án A",
    "decision_origin_integrity": "CHAT_INSTRUCTION_RECORDED_NOT_INDEPENDENTLY_SIGNED",
    "selected_architecture": "A_GITHUB_DRIVE_ONLY",
    "architecture_scope": "GITHUB_AND_GOOGLE_DRIVE_ONLY",
    "implementation_status": "SELECTED_FOR_DESIGN_ONLY_NO_PRIVILEGED_IMPLEMENTATION",
    "prior_proposal_snapshot": "docs/MST_M4_G01_G02_OWNER_DECISIONS_20261109.json",
    "decision_status": CHOICE_STATUS,
    "next_stage": "OPTION_A_READ_ONLY_FEASIBILITY_AND_OWNER_CONTROL_DESIGN",
}


def validate_option_a_choice(record):
    """Enforce fixed user choice and that no operational permission follows."""
    if type(record) is not dict:
        raise TypeError("OPTION_A_CHOICE_OBJECT_REQUIRED")
    expected_keys = (
        set(REQUIRED_STRINGS) | set(TRUE_FLAGS) | set(FALSE_FLAGS)
        | {"source_lock", "allowed_platforms", "signed_gates_open",
           "option_a_controls_to_design", "blocked_principal_actions"}
    )
    if set(record) != expected_keys:
        raise ValueError("NONCANONICAL_OPTION_A_CHOICE_FIELDS")
    for k, expected in REQUIRED_STRINGS.items():
        if record[k] != expected or type(record[k]) is not str:
            raise ValueError("OPTION_A_CHOICE_IDENTITY_OR_SCOPE_DRIFT_" + k)
    lock = record["source_lock"]
    if type(lock) is not dict or set(lock) != set(SOURCE):
        raise ValueError("PINNED_SOURCE_LOCK_CHANGED")
    for name, expected in SOURCE.items():
        if type(lock[name]) is not type(expected) or lock[name] != expected:
            raise ValueError("PINNED_SOURCE_LOCK_CHANGED")
    for k in TRUE_FLAGS:
        if record[k] is not True:
            raise ValueError("EXPLICIT_ARCHITECTURE_CHOICE_NOT_RECORDED_" + k)
    for k in FALSE_FLAGS:
        if record[k] is not False:
            raise PermissionError("OPTION_A_SCOPE_CANNOT_GRANT_PRODUCTION_RIGHT_" + k)
    if record["allowed_platforms"] != ["GitHub", "Google Drive"]:
        raise PermissionError("OUT_OF_SCOPE_PLATFORM_REJECTED")
    if record["signed_gates_open"] != OPEN_GATES:
        raise PermissionError("SIGNED_G01_G08_CANNOT_BE_CLOSED_BY_SCOPE_SELECTION")
    if record["option_a_controls_to_design"] != CONTROLS:
        raise ValueError("REQUIRED_OPTION_A_INDEPENDENCE_CONTROLS_CHANGED")
    if record["blocked_principal_actions"] != BLOCKED_ACTIONS:
        raise PermissionError("OWNER_GATED_ACTIONS_CANNOT_BE_UNBLOCKED")
    return {
        "schema": "mst.m4.option-a.scope-preflight.blocked.v1",
        "status": "OPTION_A_SCOPE_SELECTED_M4_CUSTODY_AND_PRODUCTION_BLOCKED",
        "architecture_option_selected": "A_GITHUB_DRIVE_ONLY",
        "allowed_platforms": ["GitHub", "Google Drive"],
        "owner_architecture_scope_choice_recorded": True,
        "independent_owner_authentication_attested": False,
        "signed_gates_open_count": 8,
        "real_witness_or_signer_provisioning_authorized": False,
        "new_cloud_services_authorized": False,
        "cache_read_authorized": False,
        "cache_write_authorized": False,
        "trading_authorized": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=Path(
        "docs/MST_M4_OPTION_A_SCOPE_SELECTION_20261109.json"
    ))
    p.add_argument("--output", type=Path)
    a = p.parse_args(argv)
    raw = a.input.read_bytes()
    result = validate_option_a_choice(json.loads(raw))
    # SHA only checks JSON bytes; NO independent user signature is implied.
    result["decision_record_sha256_untrusted"] = sha256(raw).hexdigest()
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
