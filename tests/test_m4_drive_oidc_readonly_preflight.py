"""MST M4: 48 OIDC Cloud Drive metadata-only and no secret-leak guards.

Tests are wholly fake. They never use Google credentials, actual Drive IDs
or provider prices and never call network.
"""
import copy
import json
import unittest
from dataclasses import replace

from scripts.m4_drive_oidc_readonly_preflight import (
    SCHEMA, STATUS, REPO, BRANCH, PROVIDERS, DOC_MIME, FOLDER_MIME,
    ReadOnlyIntent, _guard_metadata, intent_from_env, audit_metadata_only,
    read_google_file_metadata, run_live_oidc, synthetic_fixture, run_synthetic,
)

class FakeResponse:
    def __init__(self,status=200,body=None,throws=False):
        self.status_code=status
        self.body=body if body is not None else {}
        self.throws=throws
    def json(self):
        if self.throws:
            raise ValueError("sensitive value must not leak")
        return self.body

class FakeSession:
    def __init__(self,response):
        self.response=response
        self.calls=[]
    def get(self,url,*,params,timeout):
        self.calls.append({"url":url,"params":params,"timeout":timeout})
        return self.response

class DriveOidcReadOnlyPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=run_synthetic()

    def fresh(self):
        return synthetic_fixture()

    def test_01_schema_exact(self):
        self.assertEqual(self.receipt["schema"],SCHEMA)

    def test_02_no_production_status(self):
        self.assertEqual(self.receipt["status"],STATUS)

    def test_03_five_exact_fake_metadata_objects(self):
        self.assertEqual(self.receipt["metadata_object_count"],5)

    def test_04_all_provider_labels_explicit(self):
        self.assertEqual(self.receipt["provider_namespaces_checked"],["SSI","DNSE","VCBS"])

    def test_05_synthetic_report_not_google_auth_proof(self):
        self.assertFalse(self.receipt["real_google_drive_credentials_exchanged"])

    def test_06_synthetic_report_not_live_drive_metadata(self):
        self.assertFalse(self.receipt["real_google_drive_resource_metadata_retrieved"])

    def test_07_no_live_identity_claim(self):
        self.assertFalse(self.receipt["actual_live_github_identity_configured"])

    def test_08_no_docs_contents_downloaded(self):
        self.assertFalse(self.receipt["actual_docs_content_read"])

    def test_09_no_market_provider_request(self):
        self.assertFalse(self.receipt["vendor_market_api_called"])

    def test_10_no_ohlcv_in_test_artifacts(self):
        self.assertFalse(self.receipt["market_ohlcv_downloaded"])

    def test_11_no_gdrive_writes(self):
        self.assertFalse(self.receipt["google_drive_write_performed"])

    def test_12_no_schedule_activated(self):
        self.assertFalse(self.receipt["cloud_cache_automatic_refresh_active"])

    def test_13_no_vendor_cloud_rights_assumed(self):
        self.assertFalse(self.receipt["external_source_retention_license_attested"])

    def test_14_no_issuer_calendar_firstknown_assumed(self):
        self.assertFalse(self.receipt["issuer_first_known_and_official_calendar_attested"])

    def test_15_no_protected_cas_claim(self):
        self.assertFalse(self.receipt["external_signer_highwater_or_two_writer_cas_attested"])

    def test_16_no_trade_approval(self):
        self.assertFalse(self.receipt["production_cache_or_trading_enabled"])

    def test_17_correct_repo_main_manual_only(self):
        intent,_=self.fresh()
        self.assertEqual((intent.repo,intent.git_ref,intent.trigger),(REPO,BRANCH,"workflow_dispatch"))

    def test_18_pr_event_denied_even_same_repo(self):
        intent,_=self.fresh()
        with self.assertRaisesRegex(PermissionError,"MANUAL_DEFAULT_MAIN_REPO"):
            replace(intent,trigger="pull_request")

    def test_19_feature_branch_denied(self):
        intent,_=self.fresh()
        with self.assertRaisesRegex(PermissionError,"MANUAL_DEFAULT_MAIN_REPO"):
            replace(intent,git_ref="refs/heads/mst/experimental")

    def test_20_other_repo_denied(self):
        intent,_=self.fresh()
        with self.assertRaisesRegex(PermissionError,"MANUAL_DEFAULT_MAIN_REPO"):
            replace(intent,repo="ngluonghoa/MFX")

    def test_21_folder_id_noncanonical_denied(self):
        intent,_=self.fresh()
        with self.assertRaisesRegex(ValueError,"GOOGLE_DRIVE_FILE_ID"):
            replace(intent,folder_id="../../file/secret")

    def test_22_file_id_missing_denied(self):
        intent,_=self.fresh()
        with self.assertRaisesRegex(ValueError,"GOOGLE_DRIVE_FILE_ID"):
            replace(intent,manifest_doc_id="")

    def test_23_source_id_missing_denied(self):
        intent,_=self.fresh()
        with self.assertRaisesRegex(ValueError,"GOOGLE_DRIVE_FILE_ID"):
            replace(intent,source_doc_ids={"SSI":"", "DNSE":"FAKE_DNSE_012", "VCBS":"FAKE_VCBS_012"})

    def test_24_source_id_scope_exact_required(self):
        intent,_=self.fresh()
        with self.assertRaisesRegex(ValueError,"EXACT_SSI_DNSE_VCBS"):
            replace(intent,source_doc_ids={"SSI":"FAKE_SSI_001"})

    def test_25_source_id_duplicate_denied(self):
        intent,_=self.fresh()
        with self.assertRaisesRegex(ValueError,"DUPLICATED_DRIVE"):
            replace(intent,source_doc_ids={"SSI":intent.manifest_doc_id,"DNSE":intent.source_doc_ids["DNSE"],"VCBS":intent.source_doc_ids["VCBS"]})

    def test_26_source_content_download_permission_denied(self):
        intent,_=self.fresh()
        with self.assertRaisesRegex(PermissionError,"METADATA_READ_ONLY"):
            replace(intent,allow_content_download=True)

    def test_27_drive_write_permission_denied(self):
        intent,_=self.fresh()
        with self.assertRaisesRegex(PermissionError,"METADATA_READ_ONLY"):
            replace(intent,allow_drive_write=True)

    def test_28_ohlcv_ingest_permission_denied(self):
        intent,_=self.fresh()
        with self.assertRaisesRegex(PermissionError,"METADATA_READ_ONLY"):
            replace(intent,allow_licensed_ohlcv_ingestion=True)

    def test_29_cache_activation_denied(self):
        intent,_=self.fresh()
        with self.assertRaisesRegex(PermissionError,"METADATA_READ_ONLY"):
            replace(intent,allow_cache_activation=True)

    def test_30_bool_as_integer_not_accepted(self):
        intent,_=self.fresh()
        with self.assertRaisesRegex(PermissionError,"METADATA_READ_ONLY"):
            replace(intent,allow_drive_write=0)

    def test_31_folder_mime_must_be_folder(self):
        intent,items=self.fresh()
        items[intent.folder_id]["mimeType"]=DOC_MIME
        with self.assertRaisesRegex(PermissionError,"CACHE_FOLDER_MIME"):
            audit_metadata_only(intent,items.__getitem__)

    def test_32_manifest_mime_must_be_doc(self):
        intent,items=self.fresh()
        items[intent.manifest_doc_id]["mimeType"]=FOLDER_MIME
        with self.assertRaisesRegex(PermissionError,"DOC_MIME"):
            audit_metadata_only(intent,items.__getitem__)

    def test_33_wrong_source_parent_denied(self):
        intent,items=self.fresh()
        items[intent.source_doc_ids["DNSE"]]["parents"]=["OTHER_PARENT_123"]
        with self.assertRaisesRegex(PermissionError,"EXACT_PRIVATE_CACHE_PARENT"):
            audit_metadata_only(intent,items.__getitem__)

    def test_34_multiple_parents_denied(self):
        intent,items=self.fresh()
        items[intent.manifest_doc_id]["parents"].append("OTHER_PARENT_123")
        with self.assertRaisesRegex(PermissionError,"EXACT_PRIVATE_CACHE_PARENT"):
            audit_metadata_only(intent,items.__getitem__)

    def test_35_trashed_doc_denied(self):
        intent,items=self.fresh()
        items[intent.source_doc_ids["VCBS"]]["trashed"]=True
        with self.assertRaisesRegex(PermissionError,"TRASHED_OR_UNKNOWN"):
            audit_metadata_only(intent,items.__getitem__)

    def test_36_missing_trashed_status_denied(self):
        intent,items=self.fresh()
        items[intent.source_doc_ids["VCBS"]].pop("trashed")
        with self.assertRaisesRegex(PermissionError,"TRASHED_OR_UNKNOWN"):
            audit_metadata_only(intent,items.__getitem__)

    def test_37_wrong_id_response_denied(self):
        intent,items=self.fresh()
        items[intent.manifest_doc_id]["id"]="OTHER_SPOOFED_123"
        with self.assertRaisesRegex(PermissionError,"MISMATCHED_OR_INCOMPLETE"):
            audit_metadata_only(intent,items.__getitem__)

    def test_38_invalid_metadata_type_denied(self):
        intent,items=self.fresh()
        items[intent.manifest_doc_id]=["FAKE"]
        with self.assertRaisesRegex(PermissionError,"MISMATCHED_OR_INCOMPLETE"):
            audit_metadata_only(intent,items.__getitem__)

    def test_39_missing_folder_doc_metadata_denied(self):
        intent,items=self.fresh()
        items.pop(intent.source_doc_ids["SSI"])
        with self.assertRaises(KeyError):
            audit_metadata_only(intent,items.__getitem__)

    def test_40_no_raw_ids_in_audit_receipt(self):
        intent,items=self.fresh()
        result=audit_metadata_only(intent,items.__getitem__)
        serial=json.dumps(result)
        for target in [intent.folder_id,intent.manifest_doc_id,*intent.source_doc_ids.values()]:
            self.assertNotIn(target,serial)

    def test_41_provider_order_is_fixed(self):
        intent,items=self.fresh()
        seq=[]
        audit_metadata_only(intent,lambda k:(seq.append(k),items[k])[1])
        self.assertEqual(seq,[intent.folder_id,intent.manifest_doc_id]+[intent.source_doc_ids[p] for p in PROVIDERS])

    def test_42_no_credential_in_metadata_url(self):
        f=FakeSession(FakeResponse(body={"id":"FAKE_SSI_001"}))
        read_google_file_metadata("FAKE_SSI_001",f)
        self.assertEqual(len(f.calls),1)
        self.assertEqual(f.calls[0]["url"],"https://www.googleapis.com/drive/v3/files/FAKE_SSI_001")

    def test_43_only_exact_get_fields_and_no_files_list(self):
        f=FakeSession(FakeResponse())
        read_google_file_metadata("FAKE_SSI_001",f)
        self.assertEqual(f.calls[0]["params"]["fields"],"id,mimeType,parents,trashed")
        self.assertEqual(f.calls[0]["params"]["supportsAllDrives"],"true")

    def test_44_non200_gdrive_response_denied_no_body_log(self):
        f=FakeSession(FakeResponse(status=403,body={"access_token":"SENSITIVE_DO_NOT_LOG"}))
        with self.assertRaisesRegex(PermissionError,"RESOURCE_NOT_ACCESSIBLE"):
            read_google_file_metadata("FAKE_SSI_001",f)

    def test_45_corrupt_json_error_sanitized(self):
        f=FakeSession(FakeResponse(throws=True))
        with self.assertRaisesRegex(PermissionError,"FAILED_CLOSED") as e:
            read_google_file_metadata("FAKE_SSI_001",f)
        self.assertNotIn("sensitive",str(e.exception))

    def test_46_env_includes_all_three_sources(self):
        i,_=self.fresh()
        env={"MST_PILOT_FOLDER_ID":i.folder_id,"MST_PILOT_MANIFEST_ID":i.manifest_doc_id,
             "MST_PILOT_SOURCE_DOC_IDS_JSON":json.dumps(i.source_doc_ids),
             "GITHUB_REPOSITORY":REPO,"GITHUB_REF":BRANCH,
             "GITHUB_EVENT_NAME":"workflow_dispatch"}
        self.assertEqual(intent_from_env(env).ordered_targets,i.ordered_targets)

    def test_47_fake_env_pr_not_authorized(self):
        i,_=self.fresh()
        env={"MST_PILOT_FOLDER_ID":i.folder_id,"MST_PILOT_MANIFEST_ID":i.manifest_doc_id,
             "MST_PILOT_SOURCE_DOC_IDS_JSON":json.dumps(i.source_doc_ids),
             "GITHUB_REPOSITORY":REPO,"GITHUB_REF":BRANCH,
             "GITHUB_EVENT_NAME":"pull_request"}
        with self.assertRaisesRegex(PermissionError,"MANUAL_DEFAULT_MAIN_REPO"):
            intent_from_env(env)

    def test_48_live_without_oidc_context_fails_before_google_import(self):
        i,_=self.fresh()
        env={"MST_PILOT_FOLDER_ID":i.folder_id,"MST_PILOT_MANIFEST_ID":i.manifest_doc_id,
             "MST_PILOT_SOURCE_DOC_IDS_JSON":json.dumps(i.source_doc_ids),
             "GITHUB_REPOSITORY":REPO,"GITHUB_REF":BRANCH,
             "GITHUB_EVENT_NAME":"workflow_dispatch"}
        with self.assertRaisesRegex(PermissionError,"OIDC_REQUEST_CONTEXT"):
            run_live_oidc(env)


    # Security-critical static checks on the REAL manual workflow definition.
    # These only check repository source; they cannot attest a Google WIF login.
    def _workflow_source(self):
        from pathlib import Path
        return (Path(__file__).resolve().parents[1] /
                ".github/workflows/m4-drive-wif-metadata-only-manual.yml").read_text(
                    encoding="utf-8")

    def test_49_all_external_actions_pinned_to_github_verified_full_sha(self):
        import re
        s=self._workflow_source()
        pins={
            "actions/checkout":"11d5960a326750d5838078e36cf38b85af677262",
            "actions/setup-python":"a26af69be951a213d495a4c3e4e4022e16d87065",
            "google-github-actions/auth":"c200f3691d83b41bf9bbd8638997a462592937ed",
            "actions/upload-artifact":"ea165f8d65b6e75b540449e92b4886f43607fa02",
        }
        uses=re.findall(r"(?m)^\s+(?:- )?uses:\s+([A-Za-z0-9_./-]+)@([a-f0-9]{40})\b",s)
        self.assertEqual(dict(uses),pins)
        self.assertEqual(len(uses),len(pins))

    def test_50_workflow_has_no_mutable_action_tags(self):
        import re
        self.assertNotRegex(self._workflow_source(),r"(?m)^\s+(?:- )?uses:\s+\S+@v\d")

    def test_51_exact_immutable_git_hub_repository_id_job_guard(self):
        s=self._workflow_source()
        self.assertIn("github.repository_id == '1450356304'",s)
        self.assertIn("github.repository_owner_id == '353049266'",s)
        self.assertIn("github.repository == 'ngluonghoa/MST'",s)

    def test_52_manual_default_branch_job_guard(self):
        s=self._workflow_source()
        self.assertIn("github.ref == 'refs/heads/main'",s)
        self.assertIn("github.event_name == 'workflow_dispatch'",s)
        self.assertIn("  workflow_dispatch:",s)
        self.assertNotRegex(s,r"(?m)^\s{2}(?:push|pull_request|pull_request_target|schedule|workflow_run):")

    def test_53_checkout_credential_not_persisted(self):
        s=self._workflow_source()
        self.assertRegex(s,r"uses: actions/checkout@[a-f0-9]{40}.*\n\s+with:\n\s+persist-credentials: false")

    def test_54_readonly_scope_and_oidc_only(self):
        s=self._workflow_source()
        self.assertIn("  contents: read",s)
        self.assertIn("  id-token: write",s)
        self.assertNotIn("contents: write",s)
        self.assertNotIn("credentials_json:",s)

    def test_55_no_service_account_key_in_workflow(self):
        s=self._workflow_source()
        self.assertIn("workload_identity_provider: ${{ vars.MST_GCP_WIF_PROVIDER }}",s)
        self.assertIn("service_account: ${{ vars.MST_GCP_DRIVE_SA_EMAIL }}",s)
        self.assertNotIn("service_account_key",s)
        self.assertNotIn("private_key:",s)

    def test_56_no_scheduled_or_content_drive_reader(self):
        s=self._workflow_source()
        self.assertIn("--mode live-readonly",s)
        self.assertIn("metadata_object_count']==5",s)
        self.assertNotIn("--mode ingest",s)
        self.assertNotIn("--mode publish",s)
        self.assertNotIn("cache-refresh",s)

    def test_57_artifact_is_only_sanitized_metadata_receipt(self):
        s=self._workflow_source()
        self.assertIn("path: /tmp/mst-drive-oidc-metadata-READONLY.json",s)
        self.assertIn("retention-days: 7",s)
        self.assertNotIn("path: .",s)
        self.assertNotIn("path: ~",s)

    def test_58_wif_google_attribute_trust_is_external_to_workflow(self):
        s=self._workflow_source()
        self.assertIn("GCP WIF provider MUST independently enforce matching numeric IDs",s)
        self.assertIn("github.repository_owner_id == '353049266'",s)
        self.assertNotIn("principalSet://",s)

if __name__=="__main__":
    unittest.main()
