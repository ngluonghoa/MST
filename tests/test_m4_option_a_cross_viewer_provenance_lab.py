"""Option A two-viewer evidence collision tests — NO REAL OWNER ATTESTATION.

These tests use only synthetic fixture aliases and mocked BLOCKING REST
receipts. The separate GitHub Actions job fetches real read-only GitHub
metadata before validating the public, never-authorized scope ledger.
"""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.m4_option_a_cross_viewer_provenance_lab import (
    LEDGER_PATH, SCHEMA, compare_synthetic_views, validate_cross_view_ledger,
)
from scripts.m4_option_a_private_owner_evidence_intake_preflight import INTAKE_PATH
from scripts.m4_option_a_effective_authority_threat_preflight import THREAT_PATH
from scripts.m4_option_a_g01_g03_owner_packet_preflight import (
    PACKET_PATH, ROLE_PATH, DRIVE_PATH, OPTION_PATH,
)
from scripts.m4_option_a_live_custody_audit import inspect_drive_snapshot
from scripts.m4_reader_readiness_preflight import _BASE, _DENIED, _GATES, _REF


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def mocked_prior_custody(drive):
    old = inspect_drive_snapshot(drive)
    return {
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
            "cache_read_authorized": False,
            "cache_write_authorized": False, "trading_authorized": False,
        },
        "drive_historical_connector_snapshot": old,
        "github_witness_http_status": "NOT_FOUND_404",
        "independent_g01_root_attested": False,
        "external_g02_floor_attested": False,
        "two_writer_real_cas_attested": False,
        "source_vendor_rights_verified": False,
        "production_cache_authorized": False,
        "trading_authorized": False,
    }


def mocked_prior_readiness():
    return {
        "schema": "mst.m4.reader-readiness.blocking-audit.v1",
        "status": "M4_READER_AND_PUBLISHER_BLOCKED_PENDING_EXTERNAL_OWNER_GATES",
        "main_baseline_verified_for_this_read": True,
        "main_head_sha": _BASE,
        "witness_ref_name": _REF, "witness_ref_exists_for_this_read": False,
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


def synthetic_view(
    *, source="OWNER_ADMIN_REST_SIMULATED",
    view_tag="FIXTURE_VIEW_A",
    controller_tag="FIXTURE_COMMON_CONTROLLER",
    credential_tag="FIXTURE_SAME_CREDENTIAL",
    epoch=1000000, visible=False, bypass_count=None,
):
    return {
        "source": source, "view_tag": view_tag,
        "controller_tag": controller_tag,
        "credential_tag": credential_tag, "captured_epoch": epoch,
        "main_head": _BASE, "main_ruleset": 26801439,
        "review_min": 0, "witness_exists": False,
        "bypass_visible": visible, "bypass_count": bypass_count,
    }


class CrossViewerSyntheticCollisionTests(unittest.TestCase):
    def setUp(self):
        self.a = synthetic_view()
        self.b = synthetic_view(source="ACTIONS_READONLY_REST_SIMULATED",
                                view_tag="FIXTURE_VIEW_B", epoch=1000001)

    def compare(self, a=None, b=None):
        return compare_synthetic_views(self.a if a is None else a,
                                       self.b if b is None else b)

    def denied(self, callable_, pattern):
        with self.assertRaisesRegex((ValueError, PermissionError, TypeError), pattern):
            callable_()

    def test_two_views_with_same_controller_are_not_independent(self):
        r = self.compare()
        self.assertEqual(r["controller_relation"], "REPORTED_SHARED_CONTROLLER")
        self.assertEqual(r["individual_authenticated_controllers_proven"], 0)

    def test_two_views_with_same_credential_are_not_two_principals(self):
        self.assertEqual(self.compare()["credential_relation"], "REPORTED_SAME_CREDENTIAL")

    def test_changed_view_label_not_new_controller(self):
        self.assertEqual(self.compare()["view_relation"],
                         "DIFFERENT_REPORTED_VIEW_TAGS_NOT_ATTESTED")

    def test_different_controller_aliases_not_independently_verified(self):
        b = deepcopy(self.b); b["controller_tag"] = "FIXTURE_OTHER_CONTROLLER"
        self.assertEqual(self.compare(b=b)["controller_relation"],
                         "REPORTED_DIFFERENT_CONTROLLERS_NOT_VERIFIED")
        self.assertEqual(self.compare(b=b)["individual_authenticated_controllers_proven"], 0)

    def test_different_credential_aliases_not_proof(self):
        b = deepcopy(self.b); b["credential_tag"] = "FIXTURE_OTHER_TOKEN"
        self.assertEqual(self.compare(b=b)["credential_relation"],
                         "REPORTED_DIFFERENT_CREDENTIAL_TAGS_NOT_VERIFIED")
        self.assertFalse(self.compare(b=b)["independent_signer_root_proven"])

    def test_all_result_security_rights_false(self):
        result=self.compare()
        for k in ("global_admin_bypass_graph_proven",
                  "independent_signer_root_proven",
                  "protected_external_monotonic_floor_proven",
                  "two_real_authenticated_writers_proven",
                  "owner_production_authorization_proven"):
            with self.subTest(k=k):
                self.assertFalse(result[k])

    def test_result_does_not_echo_private_tag_identifiers(self):
        r=self.compare()
        self.assertNotIn("view_tag", r)
        self.assertNotIn("credential_tag", r)
        self.assertNotIn("controller_tag", r)

    def test_both_bypass_omitted_are_unknown(self):
        self.assertEqual(self.compare()["bypass_classification"],
                         "BOTH_UNAVAILABLE_UNKNOWN")

    def test_partially_visible_bypass_not_proven_empty(self):
        b=deepcopy(self.b);b["bypass_visible"]=True;b["bypass_count"]=0
        self.assertEqual(self.compare(b=b)["bypass_classification"],
                         "PARTIAL_VISIBILITY_UNKNOWN_GLOBAL_BYPASS")

    def test_visible_empty_lists_not_proven_future_safe(self):
        a=deepcopy(self.a);b=deepcopy(self.b)
        a.update(bypass_visible=True,bypass_count=0)
        b.update(bypass_visible=True,bypass_count=0)
        self.assertEqual(self.compare(a,b)["bypass_classification"],
                         "MATCHING_COUNTS_NOT_GLOBAL_BYPASS_PROOF")
        self.assertFalse(self.compare(a,b)["global_admin_bypass_graph_proven"])

    def test_conflicting_visible_bypass_counts_block(self):
        a=deepcopy(self.a);b=deepcopy(self.b)
        a.update(bypass_visible=True,bypass_count=0)
        b.update(bypass_visible=True,bypass_count=2)
        self.assertEqual(self.compare(a,b)["bypass_classification"],
                         "CONFLICTING_VISIBLE_COUNTS_BLOCK")

    def test_bypass_visible_count_nonnegative(self):
        a=deepcopy(self.a);a.update(bypass_visible=True,bypass_count=-1)
        self.denied(lambda:self.compare(a), "VISIBLE_BYPASS_COUNT_REQUIRED")

    def test_bypass_count_with_invisible_list_is_forbidden(self):
        a=deepcopy(self.a);a["bypass_count"]=0
        self.denied(lambda:self.compare(a), "OMITTED_BYPASS")

    def test_bypass_none_when_field_visible_not_accepted(self):
        a=deepcopy(self.a);a["bypass_visible"]=True
        self.denied(lambda:self.compare(a), "VISIBLE_BYPASS_COUNT_REQUIRED")

    def test_stale_cross_view_snapshots_require_new_review(self):
        b=deepcopy(self.b);b["captured_epoch"]+=1000
        self.assertEqual(self.compare(b=b)["freshness"],"STALE_SNAPSHOTS_REVIEW_REQUIRED")

    def test_300_second_skew_is_not_atomic(self):
        b=deepcopy(self.b);b["captured_epoch"]=1000300
        self.assertEqual(self.compare(b=b)["freshness"],"CLOSE_IN_TIME_NOT_ATOMIC")

    def test_301_second_skew_is_stale(self):
        b=deepcopy(self.b);b["captured_epoch"]=1000301
        self.assertEqual(self.compare(b=b)["freshness"],"STALE_SNAPSHOTS_REVIEW_REQUIRED")

    def test_identical_view_tag_detected(self):
        b=deepcopy(self.b);b["view_tag"]="FIXTURE_VIEW_A"
        self.assertEqual(self.compare(b=b)["view_relation"],"REPEATED_VIEW_TAG")

    def test_no_actual_user_source_admitted(self):
        a=deepcopy(self.a);a["source"]="GITHUB_CONNECTED_REAL_ACCOUNT"
        self.denied(lambda:self.compare(a=a),"REAL_IDENTITY_OR_EXTERNAL_PROVENANCE")

    def test_extra_identity_field_forbidden(self):
        a=deepcopy(self.a);a["email"]="not-allowed"
        self.denied(lambda:self.compare(a=a),"SYNTHETIC_VIEW_FIELDS_REQUIRED")

    def test_missing_required_view_field_forbidden(self):
        a=deepcopy(self.a);a.pop("controller_tag")
        self.denied(lambda:self.compare(a=a),"SYNTHETIC_VIEW_FIELDS_REQUIRED")

    def test_nonfixture_controller_tag_forbidden(self):
        a=deepcopy(self.a);a["controller_tag"]="real-person-identity"
        self.denied(lambda:self.compare(a=a),"ONLY_SYNTHETIC_OPAQUE_VIEW_TAGS_ALLOWED")

    def test_nonfixture_credential_tag_forbidden(self):
        a=deepcopy(self.a);a["credential_tag"]="ghp_not_allowed"
        self.denied(lambda:self.compare(a=a),"ONLY_SYNTHETIC_OPAQUE_VIEW_TAGS_ALLOWED")

    def test_overlong_fixture_tag_forbidden(self):
        a=deepcopy(self.a);a["view_tag"]="FIXTURE_"+"X"*70
        self.denied(lambda:self.compare(a=a),"ONLY_SYNTHETIC_OPAQUE_VIEW_TAGS_ALLOWED")

    def test_blank_fixture_suffix_forbidden(self):
        a=deepcopy(self.a);a["view_tag"]="FIXTURE_"
        self.denied(lambda:self.compare(a=a),"ONLY_SYNTHETIC_OPAQUE_VIEW_TAGS_ALLOWED")

    def test_main_head_drift_denied(self):
        a=deepcopy(self.a);a["main_head"]="f"*40
        self.denied(lambda:self.compare(a=a),"SOURCE_PIN_DRIFT_QUARANTINE")

    def test_wrong_ruleset_denied(self):
        a=deepcopy(self.a);a["main_ruleset"]=123
        self.denied(lambda:self.compare(a=a),"MAIN_RULESET_ID_DRIFT")

    def test_min_positive_reviews_change_requires_owner_recheck(self):
        a=deepcopy(self.a);a["review_min"]=1
        self.denied(lambda:self.compare(a=a),"MAIN_REVIEW_METADATA_DRIFT")

    def test_witness_ref_appearance_cannot_self_approve(self):
        a=deepcopy(self.a);a["witness_exists"]=True
        self.denied(lambda:self.compare(a=a),"WITNESS_STATE_CHANGED_NO_AUTO_ACCEPT")

    def test_bool_epoch_forbidden(self):
        a=deepcopy(self.a);a["captured_epoch"]=True
        self.denied(lambda:self.compare(a=a),"INVALID_SYNTHETIC_CAPTURE_EPOCH")

    def test_bool_bypass_count_forbidden(self):
        a=deepcopy(self.a);a.update(bypass_visible=True,bypass_count=False)
        self.denied(lambda:self.compare(a=a),"VISIBLE_BYPASS_COUNT_REQUIRED")

    def test_review_result_stays_no_go(self):
        self.assertEqual(self.compare()["status"],
                         "NO_GO_REVIEW_ONLY_ALL_REAL_OWNER_GATES_OPEN")


class OwnerThreeScopeLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger=read(LEDGER_PATH)
        cls.intake=read(INTAKE_PATH)
        cls.threats=read(THREAT_PATH)
        cls.owner=read(PACKET_PATH)
        cls.roles=read(ROLE_PATH)
        cls.drive=read(DRIVE_PATH)
        cls.option=read(OPTION_PATH)
        cls.live=mocked_prior_custody(cls.drive)
        cls.readiness=mocked_prior_readiness()

    def check(self, ledger=None, intake=None, live=None):
        return validate_cross_view_ledger(
            self.ledger if ledger is None else ledger,
            self.intake if intake is None else intake,
            self.threats, self.owner, self.roles, self.drive, self.option,
            self.live if live is None else live, self.readiness,
        )

    def refused(self, fn, pattern):
        with self.assertRaisesRegex((ValueError, PermissionError, TypeError),pattern):
            fn()

    def mutate(self, f):
        item=deepcopy(self.ledger);f(item);return item

    def test_three_scopes_not_independent_controllers(self):
        r=self.check()
        self.assertEqual(r["reported_view_scopes"],3)
        self.assertEqual(r["authenticated_independent_controllers"],0)

    def test_no_security_authorizations_from_three_views(self):
        r=self.check()
        for k in ("actual_g01_signer_root","actual_g02_floor",
                  "actual_g03_two_writer_remote_cas",
                  "production_cache_read_authorized",
                  "production_cache_write_authorized",
                  "production_trading_authorized","private_evidence_ingested"):
            with self.subTest(k=k):
                self.assertFalse(r[k])

    def test_two_actions_snapshots_are_same_credential_scope(self):
        self.assertTrue(self.check()["two_actions_readbacks_are_same_token_not_independent_principals"])

    def test_drive_view_not_live_actions_acl(self):
        self.assertTrue(self.check()["drive_connected_view_is_not_live_actions_acl"])

    def test_six_owner_experiments_all_unapproved(self):
        self.assertEqual(self.check()["private_owner_experiments_approved"],0)

    def test_owner_evidence_items_still_zero(self):
        self.assertEqual(self.check()["owner_evidence_classes_received"],0)

    def test_gates_all_open(self):
        self.assertEqual(self.check()["security_gates_open"],[f"G{i:02d}" for i in range(1,9)])

    def test_changed_original_main_denied(self):
        z=self.mutate(lambda x:x.update(source_main="a"*40))
        self.refused(lambda:self.check(ledger=z),"TWO_VIEWER_LEDGER_DRIFT")

    def test_scope_escape_denied(self):
        z=self.mutate(lambda x:x.update(scope="KMS"))
        self.refused(lambda:self.check(ledger=z),"TWO_VIEWER_LEDGER_DRIFT")

    def test_wrong_role_concordance_denied(self):
        z=self.mutate(lambda x:x.update(relevant_evidence=["E01"]))
        self.refused(lambda:self.check(ledger=z),"TWO_VIEWER_LEDGER_DRIFT")

    def test_new_secret_or_subject_key_in_view_forbidden(self):
        z=self.mutate(lambda x:x["evidence_channels"][0].update(subject_email="not allowed"))
        self.refused(lambda:self.check(ledger=z),"UNREVIEWED_VIEWER_OR_PRIVATE_DATA_FIELD")

    def test_marking_connected_admin_as_root_proven_denied(self):
        z=self.mutate(lambda x:x["evidence_channels"][0].update(signed_root_proven=True))
        self.refused(lambda:self.check(ledger=z),"UNVERIFIED_READER_MUST_STAY_UNTRUSTED")

    def test_marking_actions_as_independent_controller_denied(self):
        z=self.mutate(lambda x:x["evidence_channels"][1].update(viewer_controller_independence_verified=True))
        self.refused(lambda:self.check(ledger=z),"UNVERIFIED_READER_MUST_STAY_UNTRUSTED")

    def test_omitting_connected_drive_scope_denied(self):
        z=self.mutate(lambda x:x["evidence_channels"].pop())
        self.refused(lambda:self.check(ledger=z),"EXACT_GH_CONNECTOR_ACTIONS_DRIVE_SCOPES_REQUIRED")

    def test_claiming_two_controller_proof_denied(self):
        z=self.mutate(lambda x:x.update(independently_verified_controller_count=2))
        self.refused(lambda:self.check(ledger=z),"INDEPENDENT_CONTROL_NOT_PROVEN")

    def test_claiming_distinct_credential_pair_denied(self):
        z=self.mutate(lambda x:x.update(actual_credential_pair_verified=True))
        self.refused(lambda:self.check(ledger=z),"PRODUCTION_AUTHORIZATION_PREMATURE")

    def test_claiming_private_intake_approved_denied(self):
        z=self.mutate(lambda x:x["consent_and_custody"].update(private_owner_evidence_channel_approved=True))
        self.refused(lambda:self.check(ledger=z),"UNAPPROVED_IDENTITY_OR_PRIVATE_EVIDENCE")

    def test_weakening_no_secret_protocol_denied(self):
        z=self.mutate(lambda x:x["protocol"].update(no_secrets_in_pr_logs=False))
        self.refused(lambda:self.check(ledger=z),"READONLY_PRIVACY_OR_SCOPE_WEAKENED")

    def test_weakening_single_vendor_scope_denied(self):
        z=self.mutate(lambda x:x["protocol"].update(no_vendor_data_ingestion=False))
        self.refused(lambda:self.check(ledger=z),"READONLY_PRIVACY_OR_SCOPE_WEAKENED")

    def test_private_experiment_self_authorized_denied(self):
        z=self.mutate(lambda x:x["owner_required_experiments"][0].update(state="APPROVED"))
        self.refused(lambda:self.check(ledger=z),"UNAPPROVED_OWNER_EXPERIMENT")

    def test_private_experiment_missing_denied(self):
        z=self.mutate(lambda x:x["owner_required_experiments"].pop())
        self.refused(lambda:self.check(ledger=z),"SIX_PRIVATE_OWNER_TESTS")

    def test_g03_gate_cannot_be_removed(self):
        z=self.mutate(lambda x:x["security_gates_open"].remove("G03"))
        self.refused(lambda:self.check(ledger=z),"G01_G08_NOT_ALL_OPEN")

    def test_reader_rights_cannot_self_approve(self):
        z=self.mutate(lambda x:x.update(production_cache_read_authorized=True))
        self.refused(lambda:self.check(ledger=z),"PRODUCTION_AUTHORIZATION_PREMATURE")

    def test_owner_signoff_cannot_self_approve(self):
        z=self.mutate(lambda x:x.update(owner_approval_received=True))
        self.refused(lambda:self.check(ledger=z),"PRODUCTION_AUTHORIZATION_PREMATURE")

    def test_existing_intake_forgery_denied(self):
        intake=deepcopy(self.intake)
        intake["evidence_requirements"][0]["independently_verified"]=True
        self.refused(lambda:self.check(intake=intake),"UNSIGNED_OWNER_EVIDENCE_SELF_ATTESTED")

    def test_live_github_view_claims_independence_denied(self):
        live=deepcopy(self.live)
        live["two_writer_real_cas_attested"]=True
        self.refused(lambda:self.check(live=live),"LIVE_CUSTODY_UNAUTHORIZED_PROMOTION")

    def test_trying_to_auto_apply_denied(self):
        z=self.mutate(lambda x:x.update(next_owner_action="APPLY_SIGNER"))
        self.refused(lambda:self.check(ledger=z),"UNAPPROVED_PRIVILEGED_APPLY_SCOPE")


if __name__ == "__main__":
    unittest.main()
