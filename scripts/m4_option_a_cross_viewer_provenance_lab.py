"""MST Option A two-viewer provenance/collision lab, strictly review-only.

Two READ EVENTS, tokens, or display labels do NOT prove two independent
human/organizational controllers. Both GH REST snapshots in this PR run use
one GITHUB_TOKEN; Drive ACL is historical connected-connector metadata.

This module deliberately cannot accept any real signer/owner authorization.
It can detect reported collisions, stale/conflicting observations and absent
bypass fields in SYNTHETIC examples. Real principals are never inputs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.m4_option_a_private_owner_evidence_intake_preflight import (
    INTAKE_PATH, verify_intake,
)
from scripts.m4_option_a_effective_authority_threat_preflight import THREAT_PATH
from scripts.m4_option_a_g01_g03_owner_packet_preflight import (
    PACKET_PATH, ROLE_PATH, DRIVE_PATH, OPTION_PATH,
)

LEDGER_PATH = Path("docs/MST_M4_OPTION_A_CROSS_VIEWER_PROVENANCE_NEGATIVE_20261110.json")
SCHEMA = "mst.m4.option-a.cross-viewer-provenance.synthetic-negative.v1"
_VIEW_KEYS = ("GH_CONNECTED_VIEW", "GH_ACTIONS_TOKEN_VIEW", "DRIVE_CONNECTED_VIEW")
_SOURCES = ("CONNECTED_GITHUB_REPO_METADATA", "GITHUB_ACTIONS_READONLY_REST",
            "CONNECTED_GOOGLE_DRIVE_PERMISSION_METADATA")
_SURFACES = ("repository_permissions", "main_ruleset_and_witness",
             "five_mst_folders")
_TRUTH_CONTROL = (
    "simulation_only", "compare_same_domain_only",
    "independent_evidence_requires_external_attestation",
    "same_viewer_alias_is_not_two_credential_proof",
    "different_aliases_do_not_prove_independent_control",
    "unknown_bypass_is_not_empty", "concurrent_snapshot_drift_blocks",
    "explicitly_empty_bypass_list_is_not_future_policy_integrity",
    "github_drive_views_are_not_transactional", "no_github_api_mutations",
    "no_drive_api_mutations", "no_vendor_data_ingestion",
    "no_secrets_in_pr_logs",
)
_CUSTODY_FALSE = (
    "owner_approved_second_verifier",
    "second_authenticated_person_or_controller_exists_in_evidence",
    "verified_identity_control_disjointness", "verified_distinct_credentials",
    "verified_cross_account_signer_root",
    "verified_cross_account_nonresettable_floor",
    "publicly_disclosed_account_ids", "publicly_disclosed_secrets",
    "private_owner_evidence_channel_approved",
)
_POLICIES = (
    ("V01", "TWO_VERIFIED_ACCOUNT_CONTROLLERS", "OA01", "G01"),
    ("V02", "ADMIN_BYPASS_SCOPE_AND_RECOVERY", "OA05", "G01"),
    ("V03", "FRESH_READER_PROTECTED_WITNESS_AND_FLOOR", "OA02", "G02"),
    ("V04", "REAL_TWO_WRITER_CAS_IDENTITY", "OA03", "G03"),
    ("V05", "GOOGLE_DRIVE_OWNER_INHERITANCE_AND_RIGHTS", "OA04", "G05"),
    ("V06", "INDEPENDENT_EVIDENCE_PROVENANCE_NO_SELF_APPROVAL", "OA05", "G07"),
)
_VIEW_FIELDS = {
    "source", "view_tag", "controller_tag", "credential_tag",
    "captured_epoch", "main_head", "main_ruleset", "review_min",
    "witness_exists", "bypass_visible", "bypass_count",
}
_ACCEPTED_SOURCES = {"OWNER_ADMIN_REST_SIMULATED", "ACTIONS_READONLY_REST_SIMULATED"}


def _exact(value, expected, msg):
    if type(value) is not type(expected) or value != expected:
        raise ValueError(msg)


def _false(obj, names, msg):
    if type(obj) is not dict:
        raise TypeError(msg + "_DICT_REQUIRED")
    for name in names:
        if obj.get(name) is not False:
            raise PermissionError(msg + "_" + name)


def compare_synthetic_views(left: dict, right: dict) -> dict:
    """Classify two SYNTHETIC readbacks, never prove actual controllers.

    Only normalized no-PII values enter and no raw viewer labels or actor
    IDs are returned. Do not pass live GitHub account identifiers to this API.
    """
    for viewer in (left, right):
        if type(viewer) is not dict or set(viewer) != _VIEW_FIELDS:
            raise ValueError("SYNTHETIC_VIEW_FIELDS_REQUIRED")
        if viewer["source"] not in _ACCEPTED_SOURCES:
            raise ValueError("REAL_IDENTITY_OR_EXTERNAL_PROVENANCE_NOT_ADMITTED")
        for k in ("view_tag", "controller_tag", "credential_tag"):
            if type(viewer[k]) is not str or not viewer[k].startswith("FIXTURE_") or (
                len(viewer[k]) > 40 or not viewer[k][8:].replace("_", "").isalnum()
            ):
                raise PermissionError("ONLY_SYNTHETIC_OPAQUE_VIEW_TAGS_ALLOWED")
        if type(viewer["captured_epoch"]) is not int or viewer["captured_epoch"] < 1:
            raise ValueError("INVALID_SYNTHETIC_CAPTURE_EPOCH")
        if viewer["main_head"] != "4048f91beaaa3410116d97e35896c8b688384e19":
            raise PermissionError("SOURCE_PIN_DRIFT_QUARANTINE")
        _exact(viewer["main_ruleset"], 26801439, "MAIN_RULESET_ID_DRIFT")
        _exact(viewer["review_min"], 0, "MAIN_REVIEW_METADATA_DRIFT")
        _exact(viewer["witness_exists"], False, "WITNESS_STATE_CHANGED_NO_AUTO_ACCEPT")
        if type(viewer["bypass_visible"]) is not bool:
            raise ValueError("BYPASS_FIELD_VISIBILITY_REQUIRED")
        if viewer["bypass_visible"]:
            if type(viewer["bypass_count"]) is not int or viewer["bypass_count"] < 0:
                raise ValueError("VISIBLE_BYPASS_COUNT_REQUIRED")
        elif viewer["bypass_count"] is not None:
            raise PermissionError("OMITTED_BYPASS_CANNOT_HAVE_AN_ASSUMED_COUNT")
    if left["view_tag"] == right["view_tag"]:
        view_relation = "REPEATED_VIEW_TAG"
    else:
        view_relation = "DIFFERENT_REPORTED_VIEW_TAGS_NOT_ATTESTED"
    if left["controller_tag"] == right["controller_tag"]:
        control_relation = "REPORTED_SHARED_CONTROLLER"
    else:
        control_relation = "REPORTED_DIFFERENT_CONTROLLERS_NOT_VERIFIED"
    if left["credential_tag"] == right["credential_tag"]:
        credential_relation = "REPORTED_SAME_CREDENTIAL"
    else:
        credential_relation = "REPORTED_DIFFERENT_CREDENTIAL_TAGS_NOT_VERIFIED"
    skew = abs(left["captured_epoch"] - right["captured_epoch"])
    if skew > 300:
        freshness = "STALE_SNAPSHOTS_REVIEW_REQUIRED"
    else:
        freshness = "CLOSE_IN_TIME_NOT_ATOMIC"
    if not left["bypass_visible"] and not right["bypass_visible"]:
        bypass = "BOTH_UNAVAILABLE_UNKNOWN"
    elif not left["bypass_visible"] or not right["bypass_visible"]:
        bypass = "PARTIAL_VISIBILITY_UNKNOWN_GLOBAL_BYPASS"
    elif left["bypass_count"] != right["bypass_count"]:
        bypass = "CONFLICTING_VISIBLE_COUNTS_BLOCK"
    else:
        bypass = "MATCHING_COUNTS_NOT_GLOBAL_BYPASS_PROOF"
    return {
        "schema": "mst.m4.cross-viewer.synthetic-comparison.no-auth.v1",
        "evidence_type": "SYNTHETIC_INPUT_ONLY",
        "view_relation": view_relation,
        "controller_relation": control_relation,
        "credential_relation": credential_relation,
        "freshness": freshness,
        "bypass_classification": bypass,
        "individual_authenticated_controllers_proven": 0,
        "global_admin_bypass_graph_proven": False,
        "independent_signer_root_proven": False,
        "protected_external_monotonic_floor_proven": False,
        "two_real_authenticated_writers_proven": False,
        "owner_production_authorization_proven": False,
        "status": "NO_GO_REVIEW_ONLY_ALL_REAL_OWNER_GATES_OPEN",
    }


def validate_cross_view_ledger(
    ledger: dict, intake: dict, root_register: dict, owner_packet: dict,
    role_matrix: dict, historical_drive: dict, selected_option: dict,
    current_github_custody: dict, current_github_readiness: dict,
) -> dict:
    previous = verify_intake(
        intake, root_register, owner_packet, role_matrix, historical_drive,
        selected_option, current_github_custody, current_github_readiness,
    )
    if type(ledger) is not dict:
        raise TypeError("VIEW_PROVENANCE_LEDGER_REQUIRED")
    expected_header = {
        "schema": SCHEMA,
        "status": "TWO_VIEWER_CONSISTENCY_REVIEW_ONLY_ZERO_INDEPENDENT_CUSTODIANS",
        "source_main": "4048f91beaaa3410116d97e35896c8b688384e19",
        "source_tree": "d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e",
        "upstream": "cd90c1babae8912db31490ad614fc2ad2f868042",
        "repository": "ngluonghoa/MST",
        "scope": "OPTION_A_GITHUB_AND_GOOGLE_DRIVE_ONLY",
        "prior_private_intake": str(INTAKE_PATH),
        "prior_owner_security_bridge": str(PACKET_PATH),
        "relevant_evidence": ["E01", "E05", "E07", "E10", "E14"],
    }
    for name, expected in expected_header.items():
        _exact(ledger.get(name), expected, "TWO_VIEWER_LEDGER_DRIFT_" + name)
    channels = ledger.get("evidence_channels")
    if type(channels) is not list or len(channels) != 3:
        raise ValueError("EXACT_GH_CONNECTOR_ACTIONS_DRIVE_SCOPES_REQUIRED")
    for index, channel in enumerate(channels):
        if type(channel) is not dict or set(channel) != {
            "id", "source", "surface", "visible_admin",
            "source_is_actual_current_connected_viewer",
            "viewer_controller_independence_verified",
            "owner_bypass_graph_complete", "signed_root_proven",
            "may_disclose_subject_identity",
        }:
            raise PermissionError("UNREVIEWED_VIEWER_OR_PRIVATE_DATA_FIELD")
        for name, expected in (
            ("id", _VIEW_KEYS[index]), ("source", _SOURCES[index]),
            ("surface", _SURFACES[index]),
            ("visible_admin", index == 0),
            ("source_is_actual_current_connected_viewer", index != 1),
        ):
            _exact(channel.get(name), expected, "VIEWER_SCOPE_DRIFT_" + name)
        _false(channel, (
            "viewer_controller_independence_verified",
            "owner_bypass_graph_complete", "signed_root_proven",
            "may_disclose_subject_identity",
        ), "UNVERIFIED_READER_MUST_STAY_UNTRUSTED")
    _false(ledger.get("consent_and_custody"), _CUSTODY_FALSE,
           "UNAPPROVED_IDENTITY_OR_PRIVATE_EVIDENCE")
    protocol = ledger.get("protocol")
    if type(protocol) is not dict or set(protocol) != set(_TRUTH_CONTROL):
        raise ValueError("READONLY_PROVENANCE_PROTOCOL_INCOMPLETE")
    for k in _TRUTH_CONTROL:
        _exact(protocol[k], True, "READONLY_PRIVACY_OR_SCOPE_WEAKENED_" + k)
    experiments = ledger.get("owner_required_experiments")
    if type(experiments) is not list or len(experiments) != len(_POLICIES):
        raise ValueError("SIX_PRIVATE_OWNER_TESTS_MUST_REMAIN_UNAUTHORIZED")
    for entry, (code, topic, decision, gate) in zip(experiments, _POLICIES):
        if type(entry) is not dict or set(entry) != {
            "id", "topic", "state", "owner_decision", "gate",
        }:
            raise PermissionError("PRIVATE_EXPERIMENT_FIELDS_UNREVIEWED")
        for k, value in (
            ("id", code), ("topic", topic), ("state", "NOT_AUTHORIZED"),
            ("owner_decision", decision), ("gate", gate),
        ):
            _exact(entry.get(k), value, "UNAPPROVED_OWNER_EXPERIMENT_" + code)
    _exact(ledger.get("security_gates_open"),
           [f"G{i:02d}" for i in range(1, 9)], "G01_G08_NOT_ALL_OPEN")
    _exact(ledger.get("independently_verified_controller_count"),
           0, "INDEPENDENT_CONTROL_NOT_PROVEN")
    _false(ledger, (
        "actual_credential_pair_verified", "owner_approval_received",
        "witness_provisioned", "production_cache_read_authorized",
        "production_cache_write_authorized", "production_trading_authorized",
    ), "PRODUCTION_AUTHORIZATION_PREMATURE")
    _exact(ledger.get("next_owner_action"),
           "APPROVE_PRIVATE_TWO_CONTROLLER_READ_ONLY_EVIDENCE_PROCEDURE_BEFORE_ANY_REAL_PROOF",
           "UNAPPROVED_PRIVILEGED_APPLY_SCOPE")
    if previous["external_evidence_items_received"] != 0:
        raise PermissionError("PRIVATE_PROOFS_CHANGED_MUST_BE_REVIEWED_SEPARATELY")
    # The two live readbacks are actually made with the SAME github.token in
    # PR Actions. The connected GitHub view is separate but is NOT independently
    # proven to have a separate human controller. No count escalation.
    return {
        "schema": SCHEMA,
        "status": "THREE_VIEW_SCOPES_RECONCILED_ZERO_INDEPENDENT_CONTROLLERS_NO_GO",
        "reported_view_scopes": len(channels),
        "authenticated_independent_controllers": 0,
        "owner_evidence_classes_received": 0,
        "private_owner_experiments_approved": 0,
        "root_threats_open": 12,
        "owner_decisions_open": 6,
        "security_gates_open": [f"G{i:02d}" for i in range(1, 9)],
        "git_connector_and_actions_are_not_proven_independent_owners": True,
        "two_actions_readbacks_are_same_token_not_independent_principals": True,
        "drive_connected_view_is_not_live_actions_acl": True,
        "actual_g01_signer_root": False,
        "actual_g02_floor": False,
        "actual_g03_two_writer_remote_cas": False,
        "private_evidence_ingested": False,
        "no_acl_ref_signer_or_production_change": True,
        "production_cache_read_authorized": False,
        "production_cache_write_authorized": False,
        "production_trading_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=LEDGER_PATH)
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
    def data(path):
        return json.loads(path.read_text(encoding="utf-8"))
    receipt = validate_cross_view_ledger(
        data(args.ledger), data(args.intake), data(args.threats),
        data(args.owner), data(args.roles), data(args.drive),
        data(args.option), data(args.live_custody), data(args.live_readiness),
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
