"""Owner G01–G03 packet negative tests; CI green means still NO-GO.

Synthetic local API-shaped receipts are for unit tests only. The dedicated
workflow separately fetches live GitHub metadata with contents:read and never
uses these fixture receipts as authentication or production authority.
"""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.m4_option_a_g01_g03_owner_packet_preflight import (
    SCHEMA, PACKET_PATH, ROLE_PATH, DRIVE_PATH, OPTION_PATH, assess_packet,
)
from scripts.m4_option_a_live_custody_audit import inspect_drive_snapshot
from scripts.m4_reader_readiness_preflight import _BASE, _DENIED, _GATES, _REF


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fake_api_receipts(drive):
    """Known mocked denial only; never misclassify as a live read."""
    historical = inspect_drive_snapshot(drive)
    github = {
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
    }
    live = {
        "schema": "mst.m4.option-a.custody-gap-bundle.unattested.v1",
        "status": "OPTION_A_READONLY_METADATA_OBSERVED_REAL_CUSTODY_BLOCKED",
        "github_live_for_this_token": github,
        "drive_historical_connector_snapshot": historical,
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
    return live, readiness


class G01G03OwnerPacketFailClosedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = load(PACKET_PATH)
        cls.roles = load(ROLE_PATH)
        cls.drive = load(DRIVE_PATH)
        cls.choice = load(OPTION_PATH)
        cls.live, cls.readiness = fake_api_receipts(cls.drive)

    def assess(self, packet=None, role=None, drive=None, choice=None, live=None, readiness=None):
        return assess_packet(
            self.packet if packet is None else packet,
            self.roles if role is None else role,
            self.drive if drive is None else drive,
            self.choice if choice is None else choice,
            self.live if live is None else live,
            self.readiness if readiness is None else readiness,
        )

    def deny(self, op, pattern):
        with self.assertRaisesRegex((PermissionError, ValueError, TypeError), pattern):
            op()

    def test_known_blocked_packet_passes_only_as_no_go(self):
        p = self.assess()
        self.assertEqual(p["schema"], SCHEMA)
        self.assertIn("BLOCKED", p["status"])
        self.assertFalse(p["production_release_authorized"])

    def test_packet_fully_deterministic(self):
        self.assertEqual(self.assess(), self.assess())

    def test_eight_roles_zero_principals_and_twenty_five_pairs(self):
        p = self.assess()
        self.assertEqual((p["roles_proposed"], p["independently_bound_roles"],
                          p["required_distinct_principal_pairs"]), (8, 0, 25))

    def test_six_explicit_owner_decisions_open(self):
        p = self.assess()
        self.assertEqual(p["owner_decisions_open"], 6)
        self.assertEqual(p["owner_gates_open"], ["G01", "G02", "G03"])

    def test_known_token_scope_is_not_owner_signer(self):
        p = self.assess()
        self.assertFalse(p["independent_signer_proven"])
        self.assertFalse(p["durable_monotonic_floor_proven"])
        self.assertFalse(p["authenticated_two_writer_cas_proven"])

    def test_all_authorizations_stay_false(self):
        p = self.assess()
        for field in ("production_cache_read_authorized",
                      "production_cache_write_authorized",
                      "production_release_authorized", "trading_authorized"):
            with self.subTest(field=field):
                self.assertFalse(p[field])

    def test_original_source_lock_cannot_be_changed(self):
        bad = deepcopy(self.packet)
        bad["protected_main_source_sha"] = "f"*40
        self.deny(lambda: self.assess(packet=bad), "OWNER_BRIDGE_IDENTITY_DRIFT")

    def test_repo_scope_cannot_be_changed(self):
        bad = deepcopy(self.packet)
        bad["scope"] = "EXTRA_KMS"
        self.deny(lambda: self.assess(packet=bad), "OWNER_BRIDGE_IDENTITY_DRIFT")

    def test_pr_must_stay_draft(self):
        bad = deepcopy(self.packet)
        bad["work_branch_must_remain_draft"] = False
        self.deny(lambda: self.assess(packet=bad), "OWNER_BRIDGE_IDENTITY_DRIFT")

    def test_true_owner_approval_rejected(self):
        bad = deepcopy(self.packet)
        bad["owner_approval_received"] = True
        self.deny(lambda: self.assess(packet=bad), "PREMATURE_OWNER_AUTHORIZATION")

    def test_true_production_release_rejected(self):
        bad = deepcopy(self.packet)
        bad["production_release_authorized"] = True
        self.deny(lambda: self.assess(packet=bad), "PREMATURE_OWNER_AUTHORIZATION")

    def test_missing_production_release_false_rejected(self):
        bad = deepcopy(self.packet)
        del bad["production_release_authorized"]
        self.deny(lambda: self.assess(packet=bad), "PREMATURE_OWNER_AUTHORIZATION")

    def test_gate_g01_approval_forgery_rejected(self):
        bad = deepcopy(self.packet)
        bad["gates"]["G01"]["independent_root_identity_verified"] = True
        self.deny(lambda: self.assess(packet=bad), "SECURITY_GATE_PREMATURE_CERTIFICATION")

    def test_gate_g02_floor_forgery_rejected(self):
        bad = deepcopy(self.packet)
        bad["gates"]["G02"]["immutable_remote_floor_verified"] = True
        self.deny(lambda: self.assess(packet=bad), "SECURITY_GATE_PREMATURE_CERTIFICATION")

    def test_gate_g03_cas_forgery_rejected(self):
        bad = deepcopy(self.packet)
        bad["gates"]["G03"]["real_server_one_winner_loser_proven"] = True
        self.deny(lambda: self.assess(packet=bad), "SECURITY_GATE_PREMATURE_CERTIFICATION")

    def test_missing_gate_denied(self):
        bad = deepcopy(self.packet)
        del bad["gates"]["G03"]
        self.deny(lambda: self.assess(packet=bad), "EXACT_THREE_OWNER")

    def test_owner_decision_signoff_uri_forged_denied(self):
        bad = deepcopy(self.packet)
        bad["owner_decisions"][0]["owner_attestation_uri"] = "https://fake.example"
        self.deny(lambda: self.assess(packet=bad), "UNSIGNED_OWNER_DECISION")

    def test_owner_decision_marked_accepted_denied(self):
        bad = deepcopy(self.packet)
        bad["owner_decisions"][1]["state"] = "APPROVED"
        self.deny(lambda: self.assess(packet=bad), "UNSIGNED_OWNER_DECISION")

    def test_g04_or_other_related_gate_cannot_be_closed(self):
        bad = deepcopy(self.packet)
        bad["linked_gates"]["G04_licensed_market_source"] = "PASS"
        self.deny(lambda: self.assess(packet=bad), "DEPENDENT_PRODUCTION_GATE")

    def test_a02_63_dispositions_not_auto_signed(self):
        bad = deepcopy(self.packet)
        bad["linked_gates"]["A02_final_owner_module_signoff"] = "OPEN_63_OF_63"
        self.deny(lambda: self.assess(packet=bad), "DEPENDENT_PRODUCTION_GATE")

    def test_evidence_tier_cannot_be_promoted(self):
        bad = deepcopy(self.packet)
        bad["evidence_tiers"]["github_live_ci"] = "INDEPENDENT_SIGNER"
        self.deny(lambda: self.assess(packet=bad), "UNTRUSTED_EVIDENCE_PROMOTED")

    def test_required_forbidden_claim_cannot_be_removed(self):
        bad = deepcopy(self.packet)
        bad["forbidden_claims"].pop()
        self.deny(lambda: self.assess(packet=bad), "NO_GO_INTERPRETATION_CONSTRAINT")

    def test_role_principal_prematurely_enrolled_denied(self):
        bad = deepcopy(self.roles)
        bad["roles"][3]["principal_binding"] = "unverified-alias"
        self.deny(lambda: self.assess(role=bad), "ROLE_IDENTITY_PREMATURELY_ENROLLED")

    def test_duplicate_role_pair_policy_removed_denied(self):
        bad = deepcopy(self.roles)
        bad["required_distinct_principal_pairs"].pop()
        self.deny(lambda: self.assess(role=bad), "ROLE_SEPARATION_REQUIREMENTS_DRIFT")

    def test_historical_drive_acl_must_not_be_converted_to_signed_root(self):
        bad = deepcopy(self.drive)
        bad["independent_trust_root_verified"] = True
        self.deny(lambda: self.assess(drive=bad), "DRIVE_SNAPSHOT_SELF_AUTHORIZATION")

    def test_live_github_bypass_field_not_promoted_from_missing(self):
        bad = deepcopy(self.live)
        bad["github_live_for_this_token"]["main_bypass_actor_list_visible"] = True
        self.deny(lambda: self.assess(live=bad), "LIVE_GITHUB_CUSTODY_DRIFT")

    def test_live_witness_appears_requires_new_owner_review_not_auto_ready(self):
        bad = deepcopy(self.live)
        bad["github_witness_http_status"] = "VISIBLE"
        self.deny(lambda: self.assess(live=bad), "WITNESS_CHANGED_REQUIRES")

    def test_live_main_head_drift_denied(self):
        bad = deepcopy(self.live)
        bad["github_live_for_this_token"]["main_sha"] = "a"*40
        self.deny(lambda: self.assess(live=bad), "LIVE_GITHUB_CUSTODY_DRIFT")

    def test_live_main_approval_count_not_automatically_trusted_when_changed(self):
        bad = deepcopy(self.live)
        bad["github_live_for_this_token"]["main_required_approval_count"] = 1
        self.deny(lambda: self.assess(live=bad), "LIVE_GITHUB_CUSTODY_DRIFT")

    def test_live_custody_approved_cas_claim_denied(self):
        bad = deepcopy(self.live)
        bad["two_writer_real_cas_attested"] = True
        self.deny(lambda: self.assess(live=bad), "LIVE_CUSTODY_UNAUTHORIZED_PROMOTION")

    def test_live_drive_replacement_report_denied(self):
        bad = deepcopy(self.live)
        bad["drive_historical_connector_snapshot"]["drive_scope_folder_metadata_observed"] = 4
        self.deny(lambda: self.assess(live=bad), "HISTORICAL_DRIVE_SNAPSHOT")

    def test_readiness_unsigned_root_claim_denied(self):
        bad = deepcopy(self.readiness)
        bad["independent_owner_signer_verified"] = True
        self.deny(lambda: self.assess(readiness=bad), "LIVE_READINESS_CANNOT_AUTHORIZE")

    def test_readiness_witness_ref_appearance_demands_new_review(self):
        bad = deepcopy(self.readiness)
        bad["witness_ref_exists_for_this_read"] = True
        self.deny(lambda: self.assess(readiness=bad), "LIVE_READINESS_DRIFT")

    def test_readiness_owner_gate_removed_denied(self):
        bad = deepcopy(self.readiness)
        bad["owner_gates_still_open"].pop()
        self.deny(lambda: self.assess(readiness=bad), "OWNER_GATES_UNJUSTIFIABLY_CLOSED")

    def test_drive_absence_of_independent_reader_is_not_cache_authorization(self):
        p = self.assess()
        self.assertEqual(p["drive_folder_metadata_in_historical_snapshot"], 5)
        self.assertFalse(p["production_cache_read_authorized"])

    def test_live_all_three_ci_requirements_still_not_owner_signoff(self):
        p = self.assess()
        self.assertEqual(p["main_positive_human_approvals_required"], 0)
        self.assertEqual(p["witness_ref_exists"], False)


if __name__ == "__main__":
    unittest.main()
