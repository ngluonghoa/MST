"""Synthetic-only tests of MST GitHub OAuth manual Drive probe/bootstrap.

No Google Cloud credentials, no network I/O, no Drive/market data writes.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from scripts import mst_oauth_manual_drive_bootstrap as m


def context(**overrides):
    env = {
        "GITHUB_REPOSITORY": m.OWNER_REPO,
        "GITHUB_REPOSITORY_ID": m.REPO_ID,
        "GITHUB_REPOSITORY_OWNER_ID": m.OWNER_ID,
        "GITHUB_REF": m.HEAD_REF,
        "GITHUB_EVENT_NAME": m.RUN_EVENT,
        "GITHUB_WORKFLOW_REF": m.EXPECTED_WORKFLOW_REF,
        "MST_GDRIVE_OAUTH_CLIENT_ID": "FAKE_CLIENT_ID_NOBODY_USE",
        "MST_GDRIVE_OAUTH_CLIENT_SECRET": "FAKE_NOT_REAL_SECRET",
        "MST_GDRIVE_OAUTH_REFRESH_TOKEN": "FAKE_NOT_REAL_REFRESH",
    }
    env.update(overrides)
    return env


class FakeResponse:
    def __init__(self, payload, status=200):
        self.status_code = status
        self.payload = payload

    def json(self):
        return self.payload


class FakeDrive:
    """In-memory fake Drive files.list/get/create, no real HTTP."""
    def __init__(self, *, fail_list=False, fail_get=False, fail_post=False):
        self.files = {}
        self.next_id = 1
        self.calls = []
        self.fail_list = fail_list
        self.fail_get = fail_get
        self.fail_post = fail_post
        self.fail_pagination = False
        self.bad_json = False
        self.duplicate_list = False

    def get(self, url, *, params, timeout):
        self.calls.append(("GET", url, params))
        if url == m.DRIVE_FILES:
            if self.fail_list:
                return FakeResponse({}, 403)
            if self.bad_json:
                return FakeResponse([])
            q = params["q"]
            parent_expr = q.split(" in parents")[0].strip("'")
            name = q.split("name = '", 1)[1].split("'", 1)[0]
            parent = "FAKE_MY_DRIVE_ROOT" if parent_expr == "root" else parent_expr
            files = [dict(x) for x in self.files.values()
                     if x["name"] == name and x["parents"] == [parent]]
            if self.duplicate_list and files:
                files.append(dict(files[0], id="FAKE_DUPLICATE_ID"))
            result = {"files": files}
            if self.fail_pagination:
                result["nextPageToken"] = "FAKE_PAGE"
            return FakeResponse(result)
        if self.fail_get:
            return FakeResponse({}, 404)
        file_id = url.rsplit("/", 1)[-1]
        if file_id not in self.files:
            return FakeResponse({}, 404)
        return FakeResponse(dict(self.files[file_id]))

    def post(self, url, *, params, json, timeout):
        self.calls.append(("POST", url, params))
        if self.fail_post:
            return FakeResponse({}, 403)
        file_id = f"FAKE_MST_ID_{self.next_id:04}"
        self.next_id += 1
        p = json.get("parents", ["FAKE_MY_DRIVE_ROOT"])
        self.files[file_id] = {
            "id": file_id, "name": json["name"], "parents": p,
            "mimeType": json["mimeType"], "trashed": False,
        }
        return FakeResponse(dict(self.files[file_id]), 200)


class TestManualOnlyOAuthGate(unittest.TestCase):
    def assert_denied(self, **override):
        with self.assertRaises(m.BootstrapDenied):
            m.require_manual_main_context(context(**override))

    def test_01_readonly_gate_valid_without_write_var(self):
        secrets = m.require_manual_main_context(context())
        self.assertEqual(secrets.client_id, "FAKE_CLIENT_ID_NOBODY_USE")

    def test_02_write_requires_owner_var(self):
        with self.assertRaisesRegex(m.BootstrapDenied, "WRITE_OWNER_GATE"):
            m.require_manual_main_context(context(), allow_write=True)

    def test_03_write_explicitly_accepted(self):
        r = m.require_manual_main_context(
            context(MST_OAUTH_BOOTSTRAP_ACCEPTED="true"), allow_write=True)
        self.assertEqual(r.refresh_token, "FAKE_NOT_REAL_REFRESH")

    def test_04_false_write_var_denied(self):
        with self.assertRaises(m.BootstrapDenied):
            m.require_manual_main_context(
                context(MST_OAUTH_BOOTSTRAP_ACCEPTED="false"), allow_write=True)

    def test_05_uppercase_write_var_denied(self):
        with self.assertRaises(m.BootstrapDenied):
            m.require_manual_main_context(
                context(MST_OAUTH_BOOTSTRAP_ACCEPTED="TRUE"), allow_write=True)

    def test_06_repository_drift_denied(self):
        self.assert_denied(GITHUB_REPOSITORY="ngluonghoa/MFX")

    def test_07_owner_id_drift_denied(self):
        self.assert_denied(GITHUB_REPOSITORY_OWNER_ID="1")

    def test_08_repo_id_drift_denied(self):
        self.assert_denied(GITHUB_REPOSITORY_ID="1")

    def test_09_nonmain_branch_denied(self):
        self.assert_denied(GITHUB_REF="refs/heads/feature")

    def test_10_pull_request_ref_denied(self):
        self.assert_denied(GITHUB_REF="refs/pull/2/merge")

    def test_11_push_denied(self):
        self.assert_denied(GITHUB_EVENT_NAME="push")

    def test_12_schedule_denied(self):
        self.assert_denied(GITHUB_EVENT_NAME="schedule")

    def test_13_pr_target_denied(self):
        self.assert_denied(GITHUB_EVENT_NAME="pull_request_target")

    def test_14_wrong_workflow_denied(self):
        self.assert_denied(GITHUB_WORKFLOW_REF="ngluonghoa/MST/.github/workflows/evil.yml@refs/heads/main")

    def test_15_wrong_workflow_branch_denied(self):
        self.assert_denied(GITHUB_WORKFLOW_REF=m.EXPECTED_WORKFLOW_REF.replace("main", "branch"))

    def test_16_missing_client_id_denied(self):
        self.assert_denied(MST_GDRIVE_OAUTH_CLIENT_ID="")

    def test_17_missing_client_secret_denied(self):
        self.assert_denied(MST_GDRIVE_OAUTH_CLIENT_SECRET="")

    def test_18_missing_refresh_token_denied(self):
        self.assert_denied(MST_GDRIVE_OAUTH_REFRESH_TOKEN="")

    def test_19_whitespace_only_secret_denied(self):
        self.assert_denied(MST_GDRIVE_OAUTH_CLIENT_SECRET=" ")

    def test_20_no_service_account_fallback(self):
        self.assert_denied(MST_GDRIVE_SERVICE_ACCOUNT_JSON="{fake}")

    def test_21_representations_never_include_secret(self):
        a = m.require_manual_main_context(context())
        self.assertNotIn("FAKE_NOT_REAL_REFRESH", repr(a))
        self.assertNotIn("FAKE_NOT_REAL_SECRET", repr(a))

    def test_22_bool_write_flag_rejected(self):
        with self.assertRaises(m.BootstrapDenied):
            m.require_manual_main_context(context(), allow_write="false")

    def test_23_readonly_gate_ignores_bootstrap_var_if_false(self):
        m.require_manual_main_context(context(MST_OAUTH_BOOTSTRAP_ACCEPTED="false"))


class TestDriveFakeProbe(unittest.TestCase):
    def test_24_probe_empty_app_root_no_write(self):
        drive = FakeDrive()
        receipt = m.probe_readonly_from_session(drive)
        self.assertTrue(receipt["actual_google_drive_metadata_read"])
        self.assertFalse(receipt["app_owned_cache_root_discovered"])
        self.assertEqual(len(drive.files), 0)
        self.assertFalse(any(c[0] == "POST" for c in drive.calls))

    def test_25_probe_existing_app_root_discovered(self):
        drive = FakeDrive()
        root = m.find_or_create_app_folder(drive, m.ROOT_NAME, None)
        drive.calls.clear()
        receipt = m.probe_readonly_from_session(drive)
        self.assertTrue(receipt["app_owned_cache_root_discovered"])
        self.assertFalse(any(c[0] == "POST" for c in drive.calls))
        self.assertIn(root, drive.files)

    def test_26_probe_no_quote_or_watchlist_claim(self):
        receipt = m.probe_readonly_from_session(FakeDrive())
        for key in ("google_drive_write_performed","watchlist_access_proven",
                    "market_provider_called", "ohlcv_downloaded",
                    "market_cache_or_trading_activated",
                    "oauth_refresh_token_continuity_proven"):
            self.assertFalse(receipt[key], key)

    def test_27_probe_403_fail_closed(self):
        with self.assertRaises(m.BootstrapDenied):
            m.probe_readonly_from_session(FakeDrive(fail_list=True))

    def test_28_probe_nonobject_json_fail_closed(self):
        with self.assertRaises(m.BootstrapDenied):
            m.probe_readonly_from_session(FakeDrive(bad_json=True))

    def test_29_probe_multipage_denied(self):
        d = FakeDrive()
        d.fail_pagination = True
        with self.assertRaises(m.BootstrapDenied):
            m.probe_readonly_from_session(d)

    def test_30_probe_duplicate_names_denied(self):
        d = FakeDrive()
        m.find_or_create_app_folder(d, m.ROOT_NAME, None)
        d.duplicate_list = True
        with self.assertRaises(m.BootstrapDenied):
            m.probe_readonly_from_session(d)

    def test_31_probe_readback_404_denied(self):
        d = FakeDrive()
        m.find_or_create_app_folder(d, m.ROOT_NAME, None)
        d.fail_get = True
        with self.assertRaises(m.BootstrapDenied):
            m.probe_readonly_from_session(d)

    def test_32_probe_has_no_secret_id_logs(self):
        d = FakeDrive()
        r = m.probe_readonly_from_session(d)
        self.assertNotIn("FAKE_MST_ID", str(r))


class TestFakeAppOwnedFolderBootstrap(unittest.TestCase):
    def test_33_bounded_five_folders(self):
        d = FakeDrive()
        result = m.bootstrap_from_session(d)
        self.assertEqual(result["app_owned_folder_count"], 5)
        self.assertEqual(len(d.files), 5)

    def test_34_second_run_idempotent(self):
        d = FakeDrive()
        m.bootstrap_from_session(d)
        ids = set(d.files)
        m.bootstrap_from_session(d)
        self.assertEqual(set(d.files), ids)
        self.assertEqual(len(d.files), 5)

    def test_35_expected_parent_tree(self):
        d = FakeDrive()
        m.bootstrap_from_session(d)
        root = [x for x in d.files.values() if x["name"] == m.ROOT_NAME][0]
        self.assertEqual(root["parents"], ["FAKE_MY_DRIVE_ROOT"])
        self.assertEqual(
            {x["name"] for x in d.files.values() if x["parents"] == [root["id"]]},
            set(m.CHILDREN))

    def test_36_no_market_or_live_cache_claim(self):
        d = FakeDrive()
        r = m.bootstrap_from_session(d)
        for k in ("existing_watchlist_sheet_access_proven", "google_sheets_contents_read",
                  "market_provider_called", "ohlcv_downloaded",
                  "drive_cache_data_written", "market_cache_or_trading_activated",
                  "oauth_refresh_token_continuity_proven"):
            self.assertFalse(r[k], k)

    def test_37_failure_to_create_denied(self):
        with self.assertRaises(m.BootstrapDenied):
            m.bootstrap_from_session(FakeDrive(fail_post=True))

    def test_38_metadata_wrong_mime_denied(self):
        d = FakeDrive()
        root = m.find_or_create_app_folder(d, m.ROOT_NAME, None)
        d.files[root]["mimeType"] = "text/plain"
        with self.assertRaises(m.BootstrapDenied):
            m.probe_readonly_from_session(d)

    def test_39_metadata_trashed_denied(self):
        d = FakeDrive()
        root = m.find_or_create_app_folder(d, m.ROOT_NAME, None)
        d.files[root]["trashed"] = True
        with self.assertRaises(m.BootstrapDenied):
            m._verify_exact(d, root, m.ROOT_NAME, None)

    def test_40_metadata_wrong_parent_denied(self):
        d = FakeDrive()
        root = m.find_or_create_app_folder(d, m.ROOT_NAME, None)
        child = m.find_or_create_app_folder(d, "STAGING_ONLY", root)
        d.files[child]["parents"] = ["FAKE_WRONG_PARENT"]
        with self.assertRaises(m.BootstrapDenied):
            m._verify_exact(d, child, "STAGING_ONLY", root)

    def test_41_no_arbitrary_name_creation(self):
        with self.assertRaises(m.BootstrapDenied):
            m.find_or_create_app_folder(FakeDrive(), "MFX_OAUTH_CACHE_V1", None)

    def test_42_unsafe_parent_denied(self):
        with self.assertRaises(m.BootstrapDenied):
            m.find_or_create_app_folder(FakeDrive(), "AUDIT", "' OR 1")

    def test_43_receipt_no_folder_ids(self):
        d = FakeDrive()
        r = m.bootstrap_from_session(d)
        self.assertNotIn("FAKE_MST_ID", str(r))

    def test_44_no_root_ownership_assumption(self):
        d = FakeDrive()
        root = m.find_or_create_app_folder(d, m.ROOT_NAME, None)
        d.files[root]["parents"] = []
        with self.assertRaises(m.BootstrapDenied):
            m._verify_exact(d, root, m.ROOT_NAME, None)

    def test_45_wrong_root_name_denied(self):
        d = FakeDrive()
        root = m.find_or_create_app_folder(d, m.ROOT_NAME, None)
        d.files[root]["name"] = "MFX_OAUTH_CACHE_V1"
        with self.assertRaises(m.BootstrapDenied):
            m._verify_exact(d, root, m.ROOT_NAME, None)

    def test_46_no_access_to_user_created_drive_folders(self):
        d = FakeDrive()
        m.bootstrap_from_session(d)
        names = [x["name"] for x in d.files.values()]
        self.assertNotIn("06_WATCHLIST_CONTROL_PLANE_PRIVATE_NO_PRODUCTION", names)
        self.assertNotIn("MFX_OAUTH_CACHE_V1", names)

    def test_47_real_provider_api_never_present(self):
        source = (Path(__file__).resolve().parents[1] /
                  "scripts/mst_oauth_manual_drive_bootstrap.py").read_text()
        self.assertNotIn("ssi.com.vn", source.lower())
        self.assertNotIn("dnse.com.vn", source.lower())
        self.assertNotIn("vcbs.com.vn", source.lower())

    def test_48_no_scheduled_workflow(self):
        y = (Path(__file__).resolve().parents[1] /
             ".github/workflows/mst-oauth-manual-drive-bootstrap.yml").read_text()
        self.assertIn("workflow_dispatch:", y)
        self.assertIn("default: probe", y)
        self.assertNotIn("\n  schedule:", y)
        self.assertNotIn("\n  pull_request_target:", y)
        self.assertNotIn("id-token: write", y)

    def test_49_write_gate_is_runtime_not_only_ui(self):
        script = (Path(__file__).resolve().parents[1] /
                  "scripts/mst_oauth_manual_drive_bootstrap.py").read_text()
        self.assertIn('allow_write=(mode == "bootstrap")', script)
        self.assertIn('env.get("MST_OAUTH_BOOTSTRAP_ACCEPTED") != "true"', script)

    def test_50_no_user_secret_values_ever_logged(self):
        script = (Path(__file__).resolve().parents[1] /
                  "scripts/mst_oauth_manual_drive_bootstrap.py").read_text()
        self.assertNotIn("print(secrets)", script)
        self.assertNotIn("print(os.environ)", script)
        self.assertNotIn("print(response.text)", script)

    def test_51_source_oauth_scope_only(self):
        self.assertEqual(m.SCOPE, "https://www.googleapis.com/auth/drive.file")

    def test_52_github_workflow_manual_only(self):
        y = (Path(__file__).resolve().parents[1] /
             ".github/workflows/mst-oauth-manual-drive-bootstrap.yml").read_text()
        self.assertIn("github.ref == 'refs/heads/main'", y)
        self.assertIn("github.repository_id == '1450356304'", y)
        self.assertIn("vars.MST_OAUTH_BOOTSTRAP_ACCEPTED", y)

    def test_53_readonly_receipt_is_explicit(self):
        self.assertEqual(m.probe_readonly_from_session(FakeDrive())["status"],
                         "MST_OAUTH_DRIVE_FILE_READ_ONLY_PROBE_PASS")

    def test_54_staging_receipt_is_explicit(self):
        self.assertEqual(m.bootstrap_from_session(FakeDrive())["status"],
                         "MST_OAUTH_APP_OWNED_FOLDERS_METADATA_READBACK_PASS")


if __name__ == "__main__":
    unittest.main()
