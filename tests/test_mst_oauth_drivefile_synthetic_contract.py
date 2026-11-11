"""Nonproduction MST OAuth 2.0 drive.file readiness; all objects are fake."""

from dataclasses import replace
from pathlib import Path
import copy
import json
import unittest

from scripts.mst_oauth_drivefile_synthetic_contract import (
    BOOTSTRAP_WORKFLOW,
    CACHE_ROOT,
    CACHE_SUBFOLDERS,
    DRIVE_FILE_SCOPE,
    EVENT,
    MAIN,
    OWNER_ID,
    REPO,
    REPO_ID,
    OAuthGate,
    OAuthReadinessError,
    SyntheticFolders,
    assert_private_app_owned_folder_tree,
    mock_tree,
    synthetic_self_test,
    validate_synthetic_gate,
)


def valid_gate():
    return OAuthGate(
        REPO, REPO_ID, OWNER_ID, MAIN, EVENT,
        BOOTSTRAP_WORKFLOW, DRIVE_FILE_SCOPE,
        True, True, True, True,
    )


class SyntheticOAuthIdentityContractTests(unittest.TestCase):
    def deny(self, **values):
        with self.assertRaises(OAuthReadinessError):
            validate_synthetic_gate(replace(valid_gate(), **values))

    def test_01_complete_fake_config_passes(self):
        validate_synthetic_gate(valid_gate())

    def test_02_repository_drift_denied(self):
        self.deny(repository="ngluonghoa/MFX")

    def test_03_repository_spoof_denied(self):
        self.deny(repository="attacker/MST")

    def test_04_numeric_repo_id_denied(self):
        self.deny(repository_id="123")

    def test_05_numeric_owner_id_denied(self):
        self.deny(repository_owner_id="123")

    def test_06_ref_release_denied(self):
        self.deny(ref="refs/tags/v1.0")

    def test_07_ref_feature_denied(self):
        self.deny(ref="refs/heads/testing")

    def test_08_ref_pull_request_denied(self):
        self.deny(ref="refs/pull/1/merge")

    def test_09_scheduled_event_denied(self):
        self.deny(event_name="schedule")

    def test_10_push_event_denied(self):
        self.deny(event_name="push")

    def test_11_pull_request_target_denied(self):
        self.deny(event_name="pull_request_target")

    def test_12_other_workflow_denied(self):
        self.deny(workflow_ref="ngluonghoa/MST/.github/workflows/bad.yml@refs/heads/main")

    def test_13_untrusted_pr_workflow_ref_denied(self):
        self.deny(workflow_ref=BOOTSTRAP_WORKFLOW.replace("main", "feature"))

    def test_14_broad_drive_scope_denied(self):
        self.deny(oauth_scope="https://www.googleapis.com/auth/drive")

    def test_15_drive_readonly_scope_denied(self):
        self.deny(oauth_scope="https://www.googleapis.com/auth/drive.readonly")

    def test_16_sheets_scope_denied(self):
        self.deny(oauth_scope="https://www.googleapis.com/auth/spreadsheets")

    def test_17_client_id_missing_denied(self):
        self.deny(client_id_present=False)

    def test_18_client_secret_missing_denied(self):
        self.deny(client_secret_present=False)

    def test_19_refresh_token_missing_denied(self):
        self.deny(refresh_token_present=False)

    def test_20_all_secrets_missing_denied(self):
        self.deny(client_id_present=False, client_secret_present=False,
                  refresh_token_present=False)

    def test_21_service_account_fallback_denied(self):
        self.deny(service_account_present=True)

    def test_22_drive_write_not_authorized_by_ready_check(self):
        self.deny(allow_drive_write=True)

    def test_23_provider_market_api_denied(self):
        self.deny(allow_vendor_call=True)

    def test_24_production_cache_denied(self):
        self.deny(allow_cache_activation=True)

    def test_25_bool_spoof_rejected(self):
        self.deny(client_secret_present=1)

    def test_26_scope_exact_match(self):
        self.assertEqual(DRIVE_FILE_SCOPE, "https://www.googleapis.com/auth/drive.file")

    def test_27_trusted_context_is_only_placeholder(self):
        self.assertEqual(EVENT, "workflow_dispatch")
        self.assertEqual(MAIN, "refs/heads/main")

    def test_28_testing_mode_not_authorization(self):
        g = valid_gate()
        self.assertTrue(g.provider_testing_mode)
        self.deny(allow_cache_activation=True, provider_testing_mode=False)


class SyntheticOAuthAppFolderTests(unittest.TestCase):
    def bad_metadata(self, mutator):
        folders, values = mock_tree()
        mutator(folders, values)
        with self.assertRaises(OAuthReadinessError):
            assert_private_app_owned_folder_tree(folders, values)

    def test_29_fake_tree_metadata_pass(self):
        folders, values = mock_tree()
        receipt = assert_private_app_owned_folder_tree(folders, values)
        self.assertEqual(receipt["folder_count"], 5)

    def test_30_separate_app_owned_cache_root(self):
        self.assertEqual(CACHE_ROOT, "MST_OAUTH_CACHE_V1")
        self.assertNotIn("MFX", CACHE_ROOT)

    def test_31_bounded_separate_subfolders(self):
        self.assertEqual(CACHE_SUBFOLDERS,
                         ("STAGING_ONLY", "CHUNKS", "MANIFESTS", "AUDIT"))

    def test_32_no_app_owned_folder_guarantees_watchlist_access(self):
        r = synthetic_self_test()
        self.assertTrue(r["no_user_created_watchlist_access_assumed"])

    def test_33_missing_folder_denied(self):
        self.bad_metadata(lambda f, v: v.pop(f.audit))

    def test_34_extra_folder_denied(self):
        self.bad_metadata(lambda f, v: v.update({"FAKE_UNKNOWN_12": {}}))

    def test_35_duplicate_ids_denied(self):
        f, v = mock_tree()
        f = replace(f, audit=f.staging)
        with self.assertRaises(OAuthReadinessError):
            assert_private_app_owned_folder_tree(f, v)

    def test_36_modified_name_denied(self):
        self.bad_metadata(lambda f, v: v[f.root].update(name="MFX_OAUTH_CACHE_V1"))

    def test_37_modified_id_denied(self):
        self.bad_metadata(lambda f, v: v[f.root].update(id="FAKE_WRONG_ID_01"))

    def test_38_deleted_folder_denied(self):
        self.bad_metadata(lambda f, v: v[f.staging].update(trashed=True))

    def test_39_unknown_trashed_status_denied(self):
        self.bad_metadata(lambda f, v: v[f.audit].pop("trashed"))

    def test_40_wrong_mime_denied(self):
        self.bad_metadata(lambda f, v: v[f.audit].update(mimeType="text/plain"))

    def test_41_not_app_owned_denied(self):
        self.bad_metadata(lambda f, v: v[f.audit].update(appOwned=False))

    def test_42_owner_created_folder_not_assumed_accessible(self):
        self.bad_metadata(lambda f, v: v[f.root].pop("appOwned"))

    def test_43_non_root_parent_denied(self):
        self.bad_metadata(lambda f, v: v[f.root].update(parents=["existing-human-folder"]))

    def test_44_child_parent_drift_denied(self):
        self.bad_metadata(lambda f, v: v[f.chunks].update(parents=["FAKE_OTHER_PARENT"]))

    def test_45_nested_child_parent_denied(self):
        self.bad_metadata(lambda f, v: v[f.audit].update(parents=[f.chunks]))

    def test_46_mixed_broken_metadata_container_denied(self):
        self.bad_metadata(lambda f, v: v.update({f.staging: []}))

    def test_47_id_not_valid_denied(self):
        f, v = mock_tree()
        f = replace(f, manifests="../")
        with self.assertRaises(OAuthReadinessError):
            assert_private_app_owned_folder_tree(f, v)

    def test_48_receipt_claims_no_real_auth(self):
        receipt = synthetic_self_test()
        self.assertEqual(receipt["mode"], "SYNTHETIC_NOT_AUTHENTICATED")
        self.assertFalse(receipt["google_oauth_token_exchanged"])
        self.assertFalse(receipt["actual_google_drive_accessed"])
        self.assertFalse(receipt["refresh_token_lifetime_verified"])

    def test_49_receipt_claims_no_market_or_drive_writes(self):
        receipt = synthetic_self_test()
        for field in ("google_drive_write_performed", "vendor_market_api_called",
                      "market_ohlcv_downloaded", "real_cache_activated",
                      "production_trading_enabled"):
            self.assertFalse(receipt[field], field)

    def test_50_no_private_ids_in_receipt(self):
        receipt = json.dumps(synthetic_self_test())
        self.assertNotIn("FAKE_MST_ROOT_0001", receipt)
        self.assertNotIn("refresh_token", receipt.lower().replace("refresh_token_lifetime_verified", ""))
        self.assertNotIn("1nbnx", receipt)

    def test_51_no_google_io_in_fake_module(self):
        source = (Path(__file__).resolve().parents[1] /
                  "scripts/mst_oauth_drivefile_synthetic_contract.py").read_text()
        for forbidden in (
            "import requests", "import urllib.request", "from google",
            "import google", "httpx", "AuthorizedSession(",
            "credentials.Credentials", "http.client", "socket.create_connection",
        ):
            self.assertNotIn(forbidden, source)

    def test_52_no_real_cache_or_watchlist_paths(self):
        source = (Path(__file__).resolve().parents[1] /
                  "scripts/mst_oauth_drivefile_synthetic_contract.py").read_text()
        self.assertNotIn("MST_GDRIVE_OAUTH_CLIENT_SECRET=", source)
        self.assertNotIn("MST_GDRIVE_OAUTH_REFRESH_TOKEN=", source)
        self.assertNotIn("MST_PILOT_MANIFEST_ID=", source)

    def test_53_no_shared_scope_or_service_keys(self):
        r = synthetic_self_test()
        self.assertEqual(r["scope"], DRIVE_FILE_SCOPE)
        self.assertNotIn("service_account_json", json.dumps(r).lower())

    def test_54_receipt_serializable_deterministically(self):
        a = json.dumps(synthetic_self_test(), sort_keys=True)
        b = json.dumps(synthetic_self_test(), sort_keys=True)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
