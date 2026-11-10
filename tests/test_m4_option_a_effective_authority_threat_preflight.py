"""Root/admin bypass threat register: 30+ negative controls, NO production apply.

API-shaped fixtures below are deliberately MOCKED for unit testing.
Hosted CI separately runs actual read-only GitHub REST custody/readiness.
"""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.m4_option_a_effective_authority_threat_preflight import (
    SCHEMA, THREAT_PATH, THREATS, evaluate_threats,
)
from scripts.m4_option_a_g01_g03_owner_packet_preflight import (
    PACKET_PATH, ROLE_PATH, DRIVE_PATH, OPTION_PATH,
)
from scripts.m4_option_a_live_custody_audit import inspect_drive_snapshot
from scripts.m4_reader_readiness_preflight import _BASE, _DENIED, _GATES, _REF


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def mocked_ci_metadata(drive):
    """Mocked blocked REST shape only, not independently read evidence."""
    snapshot = inspect_drive_snapshot(drive)
    custody = {
        "schema": "mst.m4.option-a.custody-gap-bundle.unattested.v1",
        "status": "OPTION_A_READONLY_METADATA_OBSERVED_REAL_CUSTODY_BLOCKED",
        "github_live_for_this_token": {
            "schema": "mst.m4.option-a.github-custody-readonly.v1",
            "evidence_class": "GITHUB_REST_METADATA_FOR_THIS_CI_TOKEN_ONLY",
            "main_sha": _BASE,
            "main_ruleset_active": True,
            "main_pin_verified": True,
            "main_ruleset_id": 26801439,
            "main_required_approval_count": 0,
            "all_three_foundation_checks_required": True,
            "main_bypass_actor_list_visible": False,
            "witness_ref_exists_in_readback": False,
            "witness_owner_control_independently_attested": False,
            "protected_external_monotonic_floor_verified": False,
            "two_independent_principals_verified": False,
            "physical_drive_market_cache_verified": False,
            "cache_read_authorized": False,
            "cache_write_authorized": False,
            "trading_authorized": False,
        },
        "drive_historical_connector_snapshot": snapshot,
        "github_witness_http_status": "NOT_FOUND_404",
        "independent_g01_root_attested": False,
        "external_g02_floor_attested": False,
        "two_writer_real_cas_attested": False,
        "source_vendor_rights_verified": False,
        "production_cache_authorized": False,
        "trading_authorized": False,
    }
    readiness = {
        "schema": "mst.m4.reader-readiness.blocking-audit.v1",
        "status": "M4_READER_AND_PUBLISHER_BLOCKED_PENDING_EXTERNAL_OWNER_GATES",
        "main_baseline_verified_for_this_read": True,
        "main_head_sha": _BASE,
        "witness_ref_name": _REF,
        "witness_ref_exists_for_this_read": False,
        "witness_ref_head_sha_for_this_read": None,
        "owner_gates_still_open": list(_GATES),
        "witness_actual_owner_authorization": False,
        "witness_active_protection_effective_end_to_end_verified": False,
        "witness_ruleset_visible_for_this_token": False,
        "witness_ruleset_scope_visible_for_this_token": False,
        "witness_ruleset_metadata_matches_for_this_token": False,
        "witness_bypass_list_visible_for_this_token": False,
        **_DENIED,
    }
    return custody, readiness


class EffectiveAuthorityRootThreatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.register = read(THREAT_PATH)
        cls.packet = read(PACKET_PATH)
        cls.roles = read(ROLE_PATH)
        cls.drive = read(DRIVE_PATH)
        cls.option = read(OPTION_PATH)
        cls.custody, cls.readiness = mocked_ci_metadata(cls.drive)

    def run_assessment(self, register=None, packet=None, roles=None, drive=None,
                       option=None, custody=None, readiness=None):
        return evaluate_threats(
            self.register if register is None else register,
            self.packet if packet is None else packet,
            self.roles if roles is None else roles,
            self.drive if drive is None else drive,
            self.option if option is None else option,
            self.custody if custody is None else custody,
            self.readiness if readiness is None else readiness,
        )

    def refused(self, op, pattern):
        with self.assertRaisesRegex((PermissionError, ValueError, TypeError), pattern):
            op()

    def test_review_accepts_only_blocked_packet(self):
        o = self.run_assessment()
        self.assertEqual(o["schema"], SCHEMA)
        self.assertIn("PRODUCTION_NO_GO", o["status"])

    def test_all_twelve_threats_present(self):
        self.assertEqual(self.run_assessment()["scenario_count"], 12)
        self.assertEqual(len(THREATS), 12)

    def test_register_deterministic(self):
        self.assertEqual(self.run_assessment(), self.run_assessment())

    def test_six_owner_decisions_remain_open(self):
        self.assertEqual(self.run_assessment()["owner_decisions_open"], 6)

    def test_eight_gates_remain_open(self):
        self.assertEqual(len(self.run_assessment()["external_gates_open"]), 8)

    def test_zero_bound_roles(self):
        self.assertEqual(self.run_assessment()["bound_independent_role_principals"], 0)

    def test_main_and_source_unchanged(self):
        self.assertFalse(self.run_assessment()["source_v1_modules_modified"])

    def test_admin_permission_not_a_global_bypass_attestation(self):
        o = self.run_assessment()
        self.assertTrue(o["connected_admin_permission_does_not_prove_effective_bypass"])

    def test_single_drive_owner_not_independent_custody(self):
        self.assertTrue(self.run_assessment()["single_visible_drive_owner_does_not_prove_independent_custody"])

    def test_omitted_bypass_not_empty_list_proof(self):
        self.assertTrue(self.run_assessment()["token_omitted_bypass_is_not_empty_bypass_proof"])

    def test_all_rights_false(self):
        o = self.run_assessment()
        for key in (
            "independent_signer_or_root_authority",
            "externally_nonresettable_monotonic_floor",
            "two_authenticated_writer_remote_cas",
            "privileged_changes_performed",
            "production_cache_read_authorized",
            "production_cache_write_authorized",
            "production_release_authorized",
            "trading_authorized",
        ):
            with self.subTest(key=key):
                self.assertFalse(o[key])

    def test_public_principal_names_forbidden(self):
        bad = deepcopy(self.register)
        bad["published_principal_identifiers"] = True
        self.refused(lambda: self.run_assessment(register=bad), "ROOT_THREAT_REGISTER_DRIFT")

    def test_private_keys_forbidden(self):
        bad = deepcopy(self.register)
        bad["attached_private_keys"] = True
        self.refused(lambda: self.run_assessment(register=bad), "ROOT_THREAT_REGISTER_DRIFT")

    def test_invalid_schema_rejected(self):
        bad = deepcopy(self.register)
        bad["schema"] = "v2-authorized"
        self.refused(lambda: self.run_assessment(register=bad), "ROOT_THREAT_REGISTER_DRIFT")

    def test_extra_cloud_service_rejected(self):
        bad = deepcopy(self.register)
        bad["option"] = "CLOUD_KMS"
        self.refused(lambda: self.run_assessment(register=bad), "ROOT_THREAT_REGISTER_DRIFT")

    def test_main_source_rollback_rejected(self):
        bad = deepcopy(self.register)
        bad["source_lock"]["main"] = "e"*40
        self.refused(lambda: self.run_assessment(register=bad), "ORIGINAL_SOURCE_PARITY_ROOT_DRIFT")

    def test_altered_role_proposal_ref_rejected(self):
        bad = deepcopy(self.register)
        bad["existing_role_source"] = "forged"
        self.refused(lambda: self.run_assessment(register=bad), "ROOT_THREAT_REGISTER_DRIFT")

    def test_cannot_claim_ci_is_root_signature(self):
        bad = deepcopy(self.register)
        bad["trust_layers"]["github_ci_ruleset"] = "INDEPENDENT_SIGNER"
        self.refused(lambda: self.run_assessment(register=bad), "UNSIGNED_TRUST_LAYER_PROMOTED")

    def test_cannot_claim_drive_folder_is_worm_storage(self):
        bad = deepcopy(self.register)
        bad["trust_layers"]["connected_drive_folder_acl"] = "WORM"
        self.refused(lambda: self.run_assessment(register=bad), "UNSIGNED_TRUST_LAYER_PROMOTED")

    def test_cannot_remove_owner_decision(self):
        bad = deepcopy(self.register)
        bad["required_owner_decisions"].remove("OA05")
        self.refused(lambda: self.run_assessment(register=bad), "OWNER_DECISION_QUEUE_CHANGED")

    def test_cannot_remove_g03_gate(self):
        bad = deepcopy(self.register)
        bad["required_open_external_gates"].remove("G03")
        self.refused(lambda: self.run_assessment(register=bad), "EXTERNAL_SECURITY_GATES")

    def test_extra_threat_without_review_denied(self):
        bad = deepcopy(self.register)
        bad["threats"].append(deepcopy(bad["threats"][0]))
        self.refused(lambda: self.run_assessment(register=bad), "EXACT_TWELVE")

    def test_missing_threat_denied(self):
        bad = deepcopy(self.register)
        bad["threats"].pop()
        self.refused(lambda: self.run_assessment(register=bad), "EXACT_TWELVE")

    def test_duplicate_threat_denied(self):
        bad = deepcopy(self.register)
        bad["threats"][1] = deepcopy(bad["threats"][0])
        self.refused(lambda: self.run_assessment(register=bad), "ROOT_THREAT_NOT_PROVEN_CLOSED")

    def test_unknown_threat_field_denied(self):
        bad = deepcopy(self.register)
        bad["threats"][0]["owner_approved"] = True
        self.refused(lambda: self.run_assessment(register=bad), "THREAT_SCENARIO_CANNOT_HIDE")

    def test_root_admin_threat_not_silently_closed(self):
        bad = deepcopy(self.register)
        bad["threats"][0]["state"] = "CLOSED"
        self.refused(lambda: self.run_assessment(register=bad), "ROOT_THREAT_NOT_PROVEN_CLOSED")

    def test_reset_floor_counterexample_not_reclassified_as_pass(self):
        bad = deepcopy(self.register)
        bad["threats"][9]["state"] = "PASS"
        self.refused(lambda: self.run_assessment(register=bad), "ROOT_THREAT_NOT_PROVEN_CLOSED")

    def test_unknown_bypass_not_treated_as_empty(self):
        bad = deepcopy(self.register)
        bad["observed_static"]["github_ci_bypass_list_visible"] = True
        self.refused(lambda: self.run_assessment(register=bad), "ROOT_THREAT_OBSERVATION_CHANGED")

    def test_role_bindings_cannot_be_self_attested(self):
        bad = deepcopy(self.register)
        bad["observed_static"]["bound_roles_count"] = 8
        self.refused(lambda: self.run_assessment(register=bad), "ROOT_THREAT_OBSERVATION_CHANGED")

    def test_admin_permission_does_not_prove_bypass(self):
        bad = deepcopy(self.register)
        bad["observed_static"]["admin_permission_does_not_prove_effective_bypass"] = False
        self.refused(lambda: self.run_assessment(register=bad), "ROOT_THREAT_OBSERVATION_CHANGED")

    def test_staged_witness_cannot_be_claimed_real(self):
        bad = deepcopy(self.register)
        bad["observed_static"]["witness_ref_provisioned"] = True
        self.refused(lambda: self.run_assessment(register=bad), "ROOT_THREAT_OBSERVATION_CHANGED")

    def test_claimed_external_signer_rejected(self):
        bad = deepcopy(self.register)
        bad["external_authority_signer_verified"] = True
        self.refused(lambda: self.run_assessment(register=bad), "UNAUTHORIZED_ROOT_AUTHORITY_CLAIM")

    def test_claimed_nonresettable_floor_rejected(self):
        bad = deepcopy(self.register)
        bad["external_monotonic_floor_verified"] = True
        self.refused(lambda: self.run_assessment(register=bad), "UNAUTHORIZED_ROOT_AUTHORITY_CLAIM")

    def test_claimed_real_two_writer_cas_rejected(self):
        bad = deepcopy(self.register)
        bad["authenticated_two_principal_cas_verified"] = True
        self.refused(lambda: self.run_assessment(register=bad), "UNAUTHORIZED_ROOT_AUTHORITY_CLAIM")

    def test_claimed_signed_owner_release_rejected(self):
        bad = deepcopy(self.register)
        bad["independent_owner_signoff_received"] = True
        self.refused(lambda: self.run_assessment(register=bad), "UNAUTHORIZED_ROOT_AUTHORITY_CLAIM")

    def test_claimed_trading_rights_rejected(self):
        bad = deepcopy(self.register)
        bad["trading_authorized"] = True
        self.refused(lambda: self.run_assessment(register=bad), "UNAUTHORIZED_ROOT_AUTHORITY_CLAIM")

    def test_root_change_cannot_auto_escalate_to_apply(self):
        bad = deepcopy(self.register)
        bad["safe_next"] = "APPLY_WITNESS"
        self.refused(lambda: self.run_assessment(register=bad), "SCOPE_ESCALATION")

    def test_existing_owner_packet_cannot_be_replaced_by_approved_receipt(self):
        bad = deepcopy(self.packet)
        bad["gates"]["G01"]["owner_approved"] = True
        self.refused(lambda: self.run_assessment(packet=bad), "SECURITY_GATE_PREMATURE_CERTIFICATION")

    def test_actual_git_custody_witness_appears_requires_new_review(self):
        bad = deepcopy(self.custody)
        bad["github_witness_http_status"] = "VISIBLE"
        self.refused(lambda: self.run_assessment(custody=bad), "WITNESS_CHANGED_REQUIRES")

    def test_actual_readiness_cannot_claim_owner_approval(self):
        bad = deepcopy(self.readiness)
        bad["owner_approval_verified"] = True
        self.refused(lambda: self.run_assessment(readiness=bad), "LIVE_READINESS_CANNOT_AUTHORIZE")

    def test_drive_snapshot_cannot_claim_independent_root(self):
        bad = deepcopy(self.drive)
        bad["independent_trust_root_verified"] = True
        self.refused(lambda: self.run_assessment(drive=bad), "DRIVE_SNAPSHOT_SELF_AUTHORIZATION")


if __name__ == "__main__":
    unittest.main()
