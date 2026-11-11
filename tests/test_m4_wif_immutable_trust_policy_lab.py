"""MST M4 immutable repository Google WIF trust: 50 completely fake tests.

This suite performs zero external calls, never decodes or trusts real JWTs and
never reads Google Drive source Docs. It audits the proposed workflow file in
the checkout and only models Google CEL claim equality as a local preview.
"""
from dataclasses import replace
from pathlib import Path
import unittest

from scripts.m4_wif_immutable_trust_policy_lab import (
    SCHEMA,STATUS,OWNER,REPO,OWNER_ID,REPO_ID,REF,EVENT,
    WORKFLOW_PATH,WORKFLOW_REF,ISSUER,SOURCE_LOCK_MAIN,EXPECTED_CLAIMS,
    ATTRIBUTE_MAPPING,candidate_attribute_condition,evaluate_synthetic_claims,
    example_principalset,static_manual_workflow_audit,PendingCloudReadiness,
    run_lab,
)

WF = Path(".github/workflows/m4-drive-wif-metadata-only-manual.yml")


class WifImmutableTrustPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text=WF.read_text(encoding="utf-8")
        cls.result=run_lab(cls.text)

    def test_01_schema(self):
        self.assertEqual(self.result["schema"],SCHEMA)
    def test_02_status(self):
        self.assertEqual(self.result["status"],STATUS)
    def test_03_immutable_repo_id(self):
        self.assertEqual(REPO_ID,"1450356304")
    def test_04_immutable_owner_id(self):
        self.assertEqual(OWNER_ID,"353049266")
    def test_05_repository_name(self):
        self.assertEqual(REPO,"ngluonghoa/MST")
    def test_06_owner_name(self):
        self.assertEqual(OWNER,"ngluonghoa")
    def test_07_main_only(self):
        self.assertEqual(REF,"refs/heads/main")
    def test_08_manual_only(self):
        self.assertEqual(EVENT,"workflow_dispatch")
    def test_09_workflow_ref_exact(self):
        self.assertEqual(WORKFLOW_REF,REPO+"/"+WORKFLOW_PATH+"@"+REF)
    def test_10_github_oidc_issuer(self):
        self.assertEqual(ISSUER,"https://token.actions.githubusercontent.com")
    def test_11_main_baseline_not_modified_in_fixture(self):
        self.assertEqual(SOURCE_LOCK_MAIN,"4048f91beaaa3410116d97e35896c8b688384e19")
    def test_12_cel_contains_numeric_repo_id(self):
        self.assertIn("assertion.repository_id=='1450356304'",candidate_attribute_condition())
    def test_13_cel_contains_numeric_owner_id(self):
        self.assertIn("assertion.repository_owner_id=='353049266'",candidate_attribute_condition())
    def test_14_cel_contains_exact_workflow(self):
        self.assertIn("assertion.workflow_ref=='"+WORKFLOW_REF+"'",candidate_attribute_condition())
    def test_15_cel_contains_main_ref(self):
        self.assertIn("assertion.ref=='refs/heads/main'",candidate_attribute_condition())
    def test_16_cel_contains_manual_event(self):
        self.assertIn("assertion.event_name=='workflow_dispatch'",candidate_attribute_condition())
    def test_17_cel_seven_required_claims(self):
        self.assertEqual(len(candidate_attribute_condition().split(" && ")),7)
    def test_18_mapping_subject(self):
        self.assertEqual(ATTRIBUTE_MAPPING["google.subject"],"assertion.sub")
    def test_19_mapping_numeric_repo_id(self):
        self.assertEqual(ATTRIBUTE_MAPPING["attribute.repository_id"],"assertion.repository_id")
    def test_20_mapping_numeric_owner_id(self):
        self.assertEqual(ATTRIBUTE_MAPPING["attribute.repository_owner_id"],"assertion.repository_owner_id")
    def test_21_mapping_workflow_ref(self):
        self.assertEqual(ATTRIBUTE_MAPPING["attribute.workflow_ref"],"assertion.workflow_ref")
    def test_22_matching_mock_claims_only_synthetic(self):
        x=evaluate_synthetic_claims(EXPECTED_CLAIMS)
        self.assertTrue(x["synthetic_claims_satisfy_candidate_condition"])
        self.assertFalse(x["externally_signed_oidc_token_verified"])
    def test_23_forged_repo_id_denied(self):
        x=evaluate_synthetic_claims({**EXPECTED_CLAIMS,"repository_id":"1"})
        self.assertFalse(x["synthetic_claims_satisfy_candidate_condition"])
    def test_24_forged_owner_id_denied(self):
        x=evaluate_synthetic_claims({**EXPECTED_CLAIMS,"repository_owner_id":"1"})
        self.assertFalse(x["synthetic_claims_satisfy_candidate_condition"])
    def test_25_renamed_repo_not_trusted_without_review(self):
        x=evaluate_synthetic_claims({**EXPECTED_CLAIMS,"repository":"renamed/MST"})
        self.assertFalse(x["synthetic_claims_satisfy_candidate_condition"])
    def test_26_changed_owner_name_denied(self):
        x=evaluate_synthetic_claims({**EXPECTED_CLAIMS,"repository_owner":"hijacked"})
        self.assertFalse(x["synthetic_claims_satisfy_candidate_condition"])
    def test_27_fork_denied(self):
        x=evaluate_synthetic_claims({**EXPECTED_CLAIMS,"repository":"other/MST","repository_id":"9999"})
        self.assertFalse(x["synthetic_claims_satisfy_candidate_condition"])
    def test_28_non_main_branch_denied(self):
        x=evaluate_synthetic_claims({**EXPECTED_CLAIMS,"ref":"refs/heads/develop"})
        self.assertFalse(x["synthetic_claims_satisfy_candidate_condition"])
    def test_29_tag_denied(self):
        x=evaluate_synthetic_claims({**EXPECTED_CLAIMS,"ref":"refs/tags/v1"})
        self.assertFalse(x["synthetic_claims_satisfy_candidate_condition"])
    def test_30_pull_request_denied(self):
        x=evaluate_synthetic_claims({**EXPECTED_CLAIMS,"event_name":"pull_request"})
        self.assertFalse(x["synthetic_claims_satisfy_candidate_condition"])
    def test_31_pull_request_target_denied(self):
        x=evaluate_synthetic_claims({**EXPECTED_CLAIMS,"event_name":"pull_request_target"})
        self.assertFalse(x["synthetic_claims_satisfy_candidate_condition"])
    def test_32_schedule_denied(self):
        x=evaluate_synthetic_claims({**EXPECTED_CLAIMS,"event_name":"schedule"})
        self.assertFalse(x["synthetic_claims_satisfy_candidate_condition"])
    def test_33_alternate_workflow_same_repo_denied(self):
        x=evaluate_synthetic_claims({**EXPECTED_CLAIMS,"workflow_ref":"ngluonghoa/MST/.github/workflows/other.yml@refs/heads/main"})
        self.assertFalse(x["synthetic_claims_satisfy_candidate_condition"])
    def test_34_wrong_workflow_branch_denied(self):
        x=evaluate_synthetic_claims({**EXPECTED_CLAIMS,"workflow_ref":WORKFLOW_REF.replace("main","dev")})
        self.assertFalse(x["synthetic_claims_satisfy_candidate_condition"])
    def test_35_missing_claim_denied(self):
        x=dict(EXPECTED_CLAIMS);x.pop("repository_id")
        self.assertFalse(evaluate_synthetic_claims(x)["synthetic_claims_satisfy_candidate_condition"])
    def test_36_integer_id_not_coerced(self):
        x=evaluate_synthetic_claims({**EXPECTED_CLAIMS,"repository_id":1450356304})
        self.assertFalse(x["synthetic_claims_satisfy_candidate_condition"])
    def test_37_nested_injected_claim_type_denied(self):
        x=evaluate_synthetic_claims({**EXPECTED_CLAIMS,"repository_owner_id":["353049266"]})
        self.assertFalse(x["synthetic_claims_satisfy_candidate_condition"])
    def test_38_wrong_fake_claim_type_denied(self):
        with self.assertRaisesRegex(TypeError,"EXACT_FAKE"):
            evaluate_synthetic_claims("oidc.jwt.secret")
    def test_39_synthetic_match_does_not_prove_drive_access(self):
        self.assertFalse(evaluate_synthetic_claims(EXPECTED_CLAIMS)["drive_access_granted"])
    def test_40_correct_principal_set_format_preview(self):
        got=example_principalset("123456789012","mst-readonly-pilot")
        self.assertEqual(got,"principalSet://iam.googleapis.com/projects/123456789012/locations/global/workloadIdentityPools/mst-readonly-pilot/attribute.repository_id/1450356304")
    def test_41_project_id_not_number_denied(self):
        with self.assertRaisesRegex(ValueError,"PROJECT_NUMBER"):
            example_principalset("my-google-project","mst-readonly-pilot")
    def test_42_pool_id_injection_denied(self):
        with self.assertRaisesRegex(ValueError,"POOL_ID"):
            example_principalset("123456789012","my-pool/../../unsafe")
    def test_43_google_live_manual_workflow_static_pass(self):
        self.assertTrue(static_manual_workflow_audit(self.text)["static_workflow_contract_pass"])
    def test_44_static_workflow_rejects_trigger_expansion(self):
        with self.assertRaisesRegex(PermissionError,"STATIC_GATE_FAIL"):
            static_manual_workflow_audit(self.text.replace("  workflow_dispatch:\n","  workflow_dispatch:\n  pull_request:\n"))
    def test_45_static_workflow_rejects_oidc_scope_removal(self):
        with self.assertRaisesRegex(PermissionError,"STATIC_GATE_FAIL"):
            static_manual_workflow_audit(self.text.replace("id-token: write","id-token: read"))
    def test_46_static_workflow_rejects_github_main_guard_removed(self):
        with self.assertRaisesRegex(PermissionError,"STATIC_GATE_FAIL"):
            static_manual_workflow_audit(self.text.replace("github.ref == 'refs/heads/main'","github.ref != ''"))
    def test_47_static_workflow_rejects_opaque_credentials_json(self):
        with self.assertRaisesRegex(PermissionError,"STATIC_GATE_FAIL"):
            static_manual_workflow_audit(self.text+"\ncredentials_json: UNSAFE\n")
    def test_48_no_fake_labs_can_mark_cloud_attested(self):
        with self.assertRaisesRegex(PermissionError,"LOCAL_REPORT_CANNOT"):
            PendingCloudReadiness(provider_condition_installed=True)
    def test_49_all_real_cloud_readiness_open(self):
        self.assertTrue(all(v is False for v in self.result["cloud_readiness"].values()))
    def test_50_no_real_cloud_or_market_i_o(self):
        self.assertFalse(self.result["actual_google_cloud_or_github_settings_modified"])
        self.assertFalse(self.result["real_gcp_oidc_credentials_or_drive_metadata_accessed"])
        self.assertFalse(self.result["real_market_data_or_private_quote_cache_retrieved"])
        self.assertFalse(self.result["production_cache_and_trading_enabled"])

if __name__=="__main__":
    unittest.main()
