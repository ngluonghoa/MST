"""MST public/private owner evidence intake: negative security checks only.

All GitHub API-shaped receipts in this unit test are explicit mock denials.
The production read-only workflow separately fetches current GitHub token-
scoped REST metadata and never treats these fixtures as authenticated proofs.
"""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.m4_option_a_private_owner_evidence_intake_preflight import (
    INTAKE_PATH, SCHEMA, verify_intake,
)
from scripts.m4_option_a_effective_authority_threat_preflight import THREAT_PATH
from scripts.m4_option_a_g01_g03_owner_packet_preflight import (
    PACKET_PATH, ROLE_PATH, DRIVE_PATH, OPTION_PATH,
)
from scripts.m4_option_a_live_custody_audit import inspect_drive_snapshot
from scripts.m4_reader_readiness_preflight import _BASE, _DENIED, _GATES, _REF


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def mocked_token_limited_readback(drive):
    historical = inspect_drive_snapshot(drive)
    custody = {
        "schema": "mst.m4.option-a.custody-gap-bundle.unattested.v1",
        "status": "OPTION_A_READONLY_METADATA_OBSERVED_REAL_CUSTODY_BLOCKED",
        "github_live_for_this_token": {
            "schema": "mst.m4.option-a.github-custody-readonly.v1",
            "evidence_class": "GITHUB_REST_METADATA_FOR_THIS_CI_TOKEN_ONLY",
            "main_sha": _BASE, "main_ruleset_active": True,
            "main_pin_verified": True, "main_ruleset_id": 26801439,
            "main_required_approval_count": 0,
            "all_three_foundation_checks_required": True,
            "main_bypass_actor_list_visible": False,
            "witness_ref_exists_in_readback": False,
            "witness_owner_control_independently_attested": False,
            "protected_external_monotonic_floor_verified": False,
            "two_independent_principals_verified": False,
            "physical_drive_market_cache_verified": False,
            "cache_read_authorized": False, "cache_write_authorized": False,
            "trading_authorized": False,
        },
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
        "main_head_sha": _BASE, "witness_ref_name": _REF,
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


class OwnerEvidenceIntakePrivacyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.intake = load(INTAKE_PATH)
        cls.threats = load(THREAT_PATH)
        cls.owner = load(PACKET_PATH)
        cls.roles = load(ROLE_PATH)
        cls.drive = load(DRIVE_PATH)
        cls.option = load(OPTION_PATH)
        cls.live, cls.readiness = mocked_token_limited_readback(cls.drive)

    def assess(self, intake=None, threats=None, owner=None, roles=None,
               drive=None, option=None, live=None, readiness=None):
        return verify_intake(
            self.intake if intake is None else intake,
            self.threats if threats is None else threats,
            self.owner if owner is None else owner,
            self.roles if roles is None else roles,
            self.drive if drive is None else drive,
            self.option if option is None else option,
            self.live if live is None else live,
            self.readiness if readiness is None else readiness,
        )

    def denies(self, f, pattern):
        with self.assertRaisesRegex((PermissionError, ValueError, TypeError), pattern):
            f()

    def modified(self, edit):
        x = deepcopy(self.intake)
        edit(x)
        return x

    def test_baseline_receipt_is_only_blocking_no_go(self):
        x = self.assess()
        self.assertEqual(x["schema"], SCHEMA)
        self.assertIn("ALL_UNRECEIVED_NO_GO", x["status"])

    def test_deterministic_no_go(self):
        self.assertEqual(self.assess(), self.assess())

    def test_fourteen_requirements_zero_received(self):
        x = self.assess()
        self.assertEqual((x["external_evidence_items_required"],
                          x["external_evidence_items_received"]), (14, 0))

    def test_all_six_owner_decisions_open(self):
        self.assertEqual(self.assess()["owner_decisions_open"], 6)

    def test_all_eight_security_gates_open(self):
        self.assertEqual(self.assess()["security_gates_open"],
                         ["G01", "G02", "G03", "G04", "G05", "G06", "G07", "G08"])

    def test_all_twelve_existing_root_threats_covered(self):
        self.assertEqual(self.assess()["root_threats_covered"], 12)

    def test_zero_authenticated_owner_roles(self):
        self.assertEqual(self.assess()["owner_role_principals_verified"], 0)

    def test_no_private_material_in_public_ledger(self):
        self.assertFalse(self.assess()["private_credential_or_principal_written_to_public_git"])

    def test_independent_private_store_not_claimed(self):
        self.assertFalse(self.assess()["actual_independently_controlled_private_intake_store_proven"])

    def test_all_trading_and_cache_rights_false(self):
        for k in (
            "external_signer", "nonresettable_external_floor",
            "real_two_writer_server_cas", "privileged_changes_performed",
            "production_cache_read_authorized",
            "production_cache_write_authorized",
            "production_release_authorized", "trading_authorized",
        ):
            with self.subTest(k=k):
                self.assertFalse(self.assess()[k])

    def test_not_a_new_cloud_scope(self):
        x = self.modified(lambda v: v.update(architecture="CLOUD_KMS"))
        self.denies(lambda: self.assess(intake=x), "PRIVATE_INTAKE_SCOPE_OR_AUTHORITY_DRIFT")

    def test_source_pin_cannot_be_changed(self):
        x = self.modified(lambda v: v.update(source_pin_main="f"*40))
        self.denies(lambda: self.assess(intake=x), "PRIVATE_INTAKE_SCOPE_OR_AUTHORITY_DRIFT")

    def test_public_private_uri_field_must_stay_null(self):
        x = self.modified(lambda v: v["evidence_requirements"][0].update(
            private_evidence_uri="private-file-not-allowed-in-public-git"))
        self.denies(lambda: self.assess(intake=x), "PRIVATE_EVIDENCE_OR_IDENTITY_IN_PUBLIC_REPO")

    def test_public_principal_binding_must_stay_null(self):
        x = self.modified(lambda v: v["evidence_requirements"][2].update(
            principal_binding="private-identity-opaque-alias"))
        self.denies(lambda: self.assess(intake=x), "PRIVATE_EVIDENCE_OR_IDENTITY_IN_PUBLIC_REPO")

    def test_public_signer_fingerprint_must_stay_null(self):
        x = self.modified(lambda v: v["evidence_requirements"][3].update(
            signer_fingerprint="example-fingerprint-not-a-key"))
        self.denies(lambda: self.assess(intake=x), "PRIVATE_EVIDENCE_OR_IDENTITY_IN_PUBLIC_REPO")

    def test_public_verifier_attestation_uri_must_stay_null(self):
        x = self.modified(lambda v: v["evidence_requirements"][4].update(
            verifier_attestation_uri="mock-unaudited-uri"))
        self.denies(lambda: self.assess(intake=x), "PRIVATE_EVIDENCE_OR_IDENTITY_IN_PUBLIC_REPO")

    def test_unexpected_account_email_field_rejected(self):
        x = self.modified(lambda v: v["evidence_requirements"][0].update(
            private_contact_address="person@example.test"))
        self.denies(lambda: self.assess(intake=x), "PUBLIC_INTAKE_ADDED_PRIVATE")

    def test_unexpected_public_root_account_field_rejected(self):
        x = self.modified(lambda v: v.update(root_account="private-identity-not-to-commit"))
        self.denies(lambda: self.assess(intake=x), "PUBLIC_PRIVATE_INTAKE_ADDED_UNREVIEWED")

    def test_email_in_acceptance_text_denied(self):
        x = self.modified(lambda v: v["evidence_requirements"][0].update(
            acceptance=v["evidence_requirements"][0]["acceptance"]+" person@example.test"))
        self.denies(lambda: self.assess(intake=x), "PRIVATE_IDENTIFIER_OR_SECRET_IN_PUBLIC")

    def test_url_in_acceptance_text_denied(self):
        x = self.modified(lambda v: v["evidence_requirements"][1].update(
            acceptance=v["evidence_requirements"][1]["acceptance"]+" https://private.example.test/receipt"))
        self.denies(lambda: self.assess(intake=x), "PRIVATE_IDENTIFIER_OR_SECRET_IN_PUBLIC")

    def test_fake_token_assignment_in_text_denied(self):
        x = self.modified(lambda v: v["evidence_requirements"][2].update(
            acceptance=v["evidence_requirements"][2]["acceptance"]+" token=PLACEHOLDER_NOT_REAL"))
        self.denies(lambda: self.assess(intake=x), "PRIVATE_IDENTIFIER_OR_SECRET_IN_PUBLIC")

    def test_fake_private_key_pem_header_denied(self):
        x = self.modified(lambda v: v["evidence_requirements"][2].update(
            acceptance=v["evidence_requirements"][2]["acceptance"]+" -----BEGIN PRIVATE KEY"))
        self.denies(lambda: self.assess(intake=x), "PRIVATE_IDENTIFIER_OR_SECRET_IN_PUBLIC")

    def test_self_attested_evidence_received_denied(self):
        x = self.modified(lambda v: v["evidence_requirements"][0].update(
            state="RECEIVED"))
        self.denies(lambda: self.assess(intake=x), "INTAKE_REQUIRED_EVIDENCE_DRIFT")

    def test_independently_verified_true_denied(self):
        x = self.modified(lambda v: v["evidence_requirements"][0].update(
            independently_verified=True))
        self.denies(lambda: self.assess(intake=x), "UNSIGNED_OWNER_EVIDENCE_SELF_ATTESTED")

    def test_owner_reviewed_true_denied(self):
        x = self.modified(lambda v: v["evidence_requirements"][0].update(
            owner_reviewed=True))
        self.denies(lambda: self.assess(intake=x), "UNSIGNED_OWNER_EVIDENCE_SELF_ATTESTED")

    def test_relabeling_signer_root_requirement_denied(self):
        x = self.modified(lambda v: v["evidence_requirements"][2].update(
            kind="SELF_SIGNED_PR_IS_ROOT"))
        self.denies(lambda: self.assess(intake=x), "INTAKE_REQUIRED_EVIDENCE_DRIFT")

    def test_duplicate_evidence_requirement_denied(self):
        x = self.modified(lambda v: v["evidence_requirements"].__setitem__(
            1, deepcopy(v["evidence_requirements"][0])))
        self.denies(lambda: self.assess(intake=x), "INTAKE_REQUIRED_EVIDENCE_DRIFT")

    def test_removed_evidence_requirement_denied(self):
        x = self.modified(lambda v: v["evidence_requirements"].pop())
        self.denies(lambda: self.assess(intake=x), "EXACT_FOURTEEN_PRIVATE_EVIDENCE")

    def test_missing_evidence_acceptance_text_denied(self):
        x = self.modified(lambda v: v["evidence_requirements"][8].update(
            acceptance="OK"))
        self.denies(lambda: self.assess(intake=x), "INDEPENDENT_ACCEPTANCE_EVIDENCE_DESCRIPTION_MISSING")

    def test_bypass_proof_requirement_cannot_be_removed(self):
        x = self.modified(lambda v: v["evidence_requirements"][0].update(
            threats=["T01"]))
        self.denies(lambda: self.assess(intake=x), "INTAKE_REQUIRED_EVIDENCE_DRIFT")

    def test_cas_credential_evidence_cannot_be_reassigned(self):
        x = self.modified(lambda v: v["evidence_requirements"][4].update(
            gates=["G02"]))
        self.denies(lambda: self.assess(intake=x), "INTAKE_REQUIRED_EVIDENCE_DRIFT")

    def test_owner_decision_queue_must_stay_open(self):
        x = self.modified(lambda v: v["existing_options_owner_decisions"].pop())
        self.denies(lambda: self.assess(intake=x), "OWNER_DECISIONS_NOT_ALL_OPEN")

    def test_g08_release_cannot_be_silently_removed(self):
        x = self.modified(lambda v: v["existing_security_gates"].pop())
        self.denies(lambda: self.assess(intake=x), "SECURITY_GATES_NOT_ALL_OPEN")

    def test_private_evidence_store_not_falsely_claimed(self):
        x = self.modified(lambda v: v["ingestion_safety"].update(
            access_controlled_external_evidence_store_proven=True))
        self.denies(lambda: self.assess(intake=x), "NONEXISTENT_PRIVATE_EVIDENCE_CUSTODY_CLAIMED")

    def test_owner_private_channel_not_falsely_provisioned(self):
        x = self.modified(lambda v: v["ingestion_safety"].update(
            private_owner_channel_provisioned=True))
        self.denies(lambda: self.assess(intake=x), "NONEXISTENT_PRIVATE_EVIDENCE_CUSTODY_CLAIMED")

    def test_single_connected_account_not_mistaken_for_independent_root(self):
        x = self.modified(lambda v: v["ingestion_safety"].update(
            evidence_from_single_connected_account_not_independent=False))
        self.denies(lambda: self.assess(intake=x), "PRIVATE_INTAKE_DATA_SAFETY_WEAKENED")

    def test_missing_data_safety_clause_denied(self):
        x = self.modified(lambda v: v["ingestion_safety"].pop("public_git_contains_requirements_only"))
        self.denies(lambda: self.assess(intake=x), "PRIVATE_INTAKE_POLICY_INCOMPLETE")

    def test_forged_signer_in_admission_denied(self):
        x = self.modified(lambda v: v["admissions"].update(
            externally_authenticated_signer=True))
        self.denies(lambda: self.assess(intake=x), "PREMATURE_G01_G08_RELEASE_APPROVAL")

    def test_forged_cas_in_admission_denied(self):
        x = self.modified(lambda v: v["admissions"].update(
            independent_multiwriter_server_cas=True))
        self.denies(lambda: self.assess(intake=x), "PREMATURE_G01_G08_RELEASE_APPROVAL")

    def test_forged_production_trading_denied(self):
        x = self.modified(lambda v: v["admissions"].update(
            trading_authorized=True))
        self.denies(lambda: self.assess(intake=x), "PREMATURE_G01_G08_RELEASE_APPROVAL")

    def test_missing_admission_field_denied(self):
        x = self.modified(lambda v: v["admissions"].pop("trading_authorized"))
        self.denies(lambda: self.assess(intake=x), "PRODUCTION_ADMISSION_GATES_INCOMPLETE")

    def test_owner_next_step_cannot_auto_apply(self):
        x = self.modified(lambda v: v.update(next_owner_action="APPLY_WITNESS"))
        self.denies(lambda: self.assess(intake=x), "OWNER_EVIDENCE_INTAKE_SCOPE_ESCALATION")

    def test_root_threat_register_cannot_be_approving_self(self):
        root = deepcopy(self.threats)
        root["independent_owner_signoff_received"] = True
        self.denies(lambda: self.assess(threats=root), "UNAUTHORIZED_ROOT_AUTHORITY_CLAIM")

    def test_connected_github_admin_claim_cannot_prove_bypass(self):
        root = deepcopy(self.threats)
        root["observed_static"]["admin_permission_does_not_prove_effective_bypass"] = False
        self.denies(lambda: self.assess(threats=root), "ROOT_THREAT_OBSERVATION_CHANGED")

    def test_actual_github_bypass_unavailable_no_allow(self):
        data = deepcopy(self.live)
        data["github_live_for_this_token"]["main_bypass_actor_list_visible"] = True
        self.denies(lambda: self.assess(live=data), "LIVE_GITHUB_CUSTODY_DRIFT")

    def test_witness_ref_appearance_demands_owner_review(self):
        data = deepcopy(self.live)
        data["github_witness_http_status"] = "VISIBLE"
        self.denies(lambda: self.assess(live=data), "WITNESS_CHANGED_REQUIRES")

    def test_readiness_owner_approval_forgery_denied(self):
        data = deepcopy(self.readiness)
        data["owner_approval_verified"] = True
        self.denies(lambda: self.assess(readiness=data), "LIVE_READINESS_CANNOT_AUTHORIZE")


if __name__ == "__main__":
    unittest.main()
