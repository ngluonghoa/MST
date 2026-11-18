"""§220 offline-only tests for one-shot private synthetic Drive canary."""
from __future__ import annotations

import json
import unittest

from scripts import mst_oauth_synthetic_canary220 as m
from test_mst_oauth_cache_census219 import FakeAppOwnedDrive, Response


class CanaryDrive(FakeAppOwnedDrive):
    def __init__(self):
        super().__init__()
        self.created = None
        self.media = None
        self.posts = 0
        self.upload_http = 200
        self.corrupt_media = False
        self.invalid_metadata = False
        self.hide_postwrite = False
        self.incomplete_name_lookup = False

    def get(self, url, *, params, timeout, **kwargs):
        if url.startswith(m.DRIVE_FILES + "/") and self.created is not None:
            if url.endswith("/" + self.created["id"]):
                self.calls.append(("GET", url, dict(params)))
                if params.get("alt") == "media":
                    raw = self.media
                    if self.corrupt_media:
                        raw += b"CHANGED"
                    response = Response({}, 200)
                    response.content = raw
                    return response
                obj = dict(self.created)
                if self.invalid_metadata:
                    obj["parents"] = ["FAKE_UNAUTHORIZED_PARENT_0123456789"]
                return Response(obj)
        if url == m.DRIVE_FILES and "name = '" in params.get("q", ""):
            query = params["q"]
            name = query.split("name = '", 1)[1].split("'", 1)[0]
            if name.startswith(m.CANARY_PREFIX):
                self.calls.append(("GET", url, dict(params)))
                found = []
                if self.created and not self.hide_postwrite:
                    found = [{
                        k: self.created[k] for k in
                        ("id", "name", "mimeType", "parents", "trashed")
                    }]
                if self.incomplete_name_lookup:
                    return Response({"files": found, "incompleteSearch": True})
                return Response({"files": found, "incompleteSearch": False})
        return super().get(url, params=params, timeout=timeout, **kwargs)

    def post(self, url, *, params, data, headers, timeout, **kwargs):
        self.posts += 1
        self.calls.append(("POST", url, dict(params)))
        if url != m.DRIVE_UPLOAD or params.get("uploadType") != "multipart":
            raise AssertionError("canary may only upload to Google Drive files")
        if self.upload_http != 200:
            return Response({"body": "SECRET_OAUTH_OR_TOKEN_DETAIL"}, self.upload_http)
        raw = bytes(data)
        boundary = b"MST_220_SYNTHETIC_BOUNDARY"
        media_start = raw.find(b'{"eligible_for_signals"')
        media_end = raw.find(b"\r\n--" + boundary + b"--", media_start)
        if media_start < 0 or media_end <= media_start:
            raise AssertionError("invalid MIME upload encoding")
        self.media = raw[media_start:media_end]
        payload = json.loads(self.media)
        self.assert_synthetic(payload)
        folder_id = self.children["STAGING_ONLY"]
        self.created = {
            "id": "FAKE_CANARY_FILE_0123456789",
            "name": m.CANARY_PREFIX + payload["run_id"] + "_1.json",
            "mimeType": "application/json",
            "parents": [folder_id], "trashed": False,
            "shared": False, "ownedByMe": True, "isAppAuthorized": True,
            "size": str(len(self.media)),
            "appProperties": {"synthetic_only": "true"},
        }
        return Response({"id": self.created["id"]}, 200)

    @staticmethod
    def assert_synthetic(payload):
        assert payload["sentinel"] == "MST_SYNTHETIC_ONLY_NO_MARKET_DATA"
        assert payload["market_data"] is None
        assert payload["eligible_for_signals"] is False


def owner_env(**changes):
    env = {
        "GITHUB_REPOSITORY": m.OWNER_REPO,
        "GITHUB_REPOSITORY_ID": m.REPO_ID,
        "GITHUB_REPOSITORY_OWNER_ID": m.OWNER_ID,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_WORKFLOW_REF": m.WORKFLOW_REF,
        "MST_CANARY_CONFIRM": m.CONFIRM,
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_RUN_ID": "44249999999",
        "MST_GDRIVE_OAUTH_CLIENT_ID": "FAKE_CLIENT_ID",
        "MST_GDRIVE_OAUTH_CLIENT_SECRET": "FAKE_CLIENT_SECRET",
        "MST_GDRIVE_OAUTH_REFRESH_TOKEN": "FAKE_REFRESH_TOKEN",
    }
    env.update(changes)
    return env


class SyntheticCanary220Tests(unittest.TestCase):
    def test_gate_accepts_only_existing_owner_main_manual_first_attempt(self):
        credentials, run = m.authorize_manual_synthetic_write(owner_env())
        self.assertEqual(credentials.client_id, "FAKE_CLIENT_ID")
        self.assertEqual(run, "44249999999")

    def test_gate_rejects_wrong_repo_owner_branch_event_workflow_confirmation(self):
        for changes in (
            {"GITHUB_REPOSITORY": "wrong/repo"},
            {"GITHUB_REPOSITORY_ID": "1"},
            {"GITHUB_REPOSITORY_OWNER_ID": "1"},
            {"GITHUB_REF": "refs/heads/test"},
            {"GITHUB_EVENT_NAME": "schedule"},
            {"GITHUB_WORKFLOW_REF": "fake"},
            {"MST_CANARY_CONFIRM": "NO"},
        ):
            with self.subTest(changes=changes), self.assertRaises(
                m.CanaryDenied
            ):
                m.authorize_manual_synthetic_write(owner_env(**changes))

    def test_refuse_reruns_or_noncanonical_identity(self):
        for changes in (
            {"GITHUB_RUN_ATTEMPT": "2"},
            {"GITHUB_RUN_ID": "0"},
            {"GITHUB_RUN_ID": "44249999999\nany"},
            {"GITHUB_RUN_ID": "9" * 1000},
        ):
            with self.subTest(changes=changes), self.assertRaises(m.CanaryDenied):
                m.authorize_manual_synthetic_write(owner_env(**changes))

    def test_refuse_incomplete_oauth_trio_and_fallback(self):
        for key in m.OAUTH_KEYS:
            with self.subTest(key=key), self.assertRaises(m.CanaryDenied):
                m.authorize_manual_synthetic_write(owner_env(**{key: ""}))
        for changes in (
            {"MST_GDRIVE_SERVICE_ACCOUNT_JSON": "FAKE_UNSAFE"},
            {"MST_OAUTH_MODE": "bootstrap"},
        ):
            with self.subTest(changes=changes), self.assertRaises(m.CanaryDenied):
                m.authorize_manual_synthetic_write(owner_env(**changes))

    def test_exactly_one_private_synthetic_upload_sha256_verified(self):
        d = CanaryDrive()
        receipt = m.synthetic_staging_canary(d, "44249999999")
        self.assertEqual(receipt["status"],
                         "MST_220_SYNTHETIC_STAGING_WRITE_SHA256_READBACK_PASS")
        self.assertEqual(d.posts, 1)
        self.assertEqual(d.created["parents"], [d.children["STAGING_ONLY"]])
        self.assertEqual(receipt["bytes_verified"], len(d.media))
        self.assertEqual(len(receipt["readback_sha256"]), 64)
        self.assertTrue(receipt["synthetic_only"])
        for item in ("market_cache_promoted", "manifest_published",
                     "stock_provider_called", "production_cache_ready",
                     "signals_and_trading_eligible"):
            self.assertFalse(receipt[item])
        self.assertNotIn(d.created["id"], str(receipt))
        self.assertNotIn("FAKE_REFRESH_TOKEN", str(receipt))

    def test_incomplete_name_search_denied_before_any_upload(self):
        drive = CanaryDrive()
        drive.incomplete_name_lookup = True
        with self.assertRaisesRegex(
            m.CanaryDenied, "CANARY_NAME_SEARCH_INCOMPLETE"
        ):
            m.synthetic_staging_canary(drive, "44249999999")
        self.assertEqual(drive.posts, 0)
        exact_queries = [
            call for call in drive.calls if call[0] == "GET"
            and call[1] == m.DRIVE_FILES
            and "name = '" in call[2].get("q", "")
            and m.CANARY_PREFIX in call[2].get("q", "")
        ]
        self.assertEqual(len(exact_queries), 1)
        self.assertIn("incompleteSearch", exact_queries[0][2]["fields"])

    def test_incomplete_postwrite_name_search_never_returns_pass(self):
        drive = CanaryDrive()
        original_get = drive.get

        def altered_get(url, *, params, timeout, **kwargs):
            if drive.posts == 1:
                drive.incomplete_name_lookup = True
            return original_get(url, params=params, timeout=timeout, **kwargs)

        drive.get = altered_get
        with self.assertRaisesRegex(
            m.CanaryDenied, "CANARY_NAME_SEARCH_INCOMPLETE"
        ):
            m.synthetic_staging_canary(drive, "44249999999")
        self.assertEqual(drive.posts, 1)
        self.assertIsNotNone(drive.created)

    def test_refuse_second_call_same_run_before_upload(self):
        d = CanaryDrive()
        m.synthetic_staging_canary(d, "44249999999")
        with self.assertRaisesRegex(m.CanaryDenied, "ALREADY_EXISTS"):
            m.synthetic_staging_canary(d, "44249999999")
        self.assertEqual(d.posts, 1)

    def test_refuse_duplicate_file_before_first_upload(self):
        d = CanaryDrive()
        d.created = {
            "id": "FAKE_OLD_FILE_0123456789",
            "name": m.CANARY_PREFIX + "44249999999_1.json",
            "mimeType": "application/json",
            "parents": [d.children["STAGING_ONLY"]], "trashed": False,
        }
        with self.assertRaisesRegex(m.CanaryDenied, "ALREADY_EXISTS"):
            m.synthetic_staging_canary(d, "44249999999")
        self.assertEqual(d.posts, 0)

    def test_refuse_nonprivate_root_or_children_before_any_upload(self):
        for attribute, bad in (("shared", True), ("ownedByMe", False),
                               ("isAppAuthorized", False)):
            d = CanaryDrive()
            d.metadata[d.children["CHUNKS"]][attribute] = bad
            with self.subTest(attribute=attribute), self.assertRaises(
                m.CanaryDenied
            ):
                m.synthetic_staging_canary(d, "44249999999")
            self.assertEqual(d.posts, 0)

    def test_upload_http_denied_with_no_body_exposed(self):
        d = CanaryDrive()
        d.upload_http = 403
        with self.assertRaises(m.CanaryDenied) as exc:
            m.synthetic_staging_canary(d, "44249999999")
        self.assertNotIn("SECRET_OAUTH_OR_TOKEN_DETAIL", str(exc.exception))
        self.assertEqual(d.posts, 1)

    def test_reject_mutated_media_after_file_created(self):
        d = CanaryDrive()
        d.corrupt_media = True
        with self.assertRaisesRegex(m.CanaryDenied, "SHA256_MISMATCH"):
            m.synthetic_staging_canary(d, "44249999999")
        self.assertEqual(d.posts, 1)

    def test_reject_bad_postwrite_file_metadata(self):
        d = CanaryDrive()
        d.invalid_metadata = True
        with self.assertRaisesRegex(m.CanaryDenied, "METADATA_READBACK_MISMATCH"):
            m.synthetic_staging_canary(d, "44249999999")
        self.assertEqual(d.posts, 1)

    def test_reject_postwrite_listing_drift(self):
        d = CanaryDrive()
        d.hide_postwrite = True
        with self.assertRaisesRegex(m.CanaryDenied, "POSTWRITE_LIST_DRIFT"):
            m.synthetic_staging_canary(d, "44249999999")
        self.assertEqual(d.posts, 1)

    def test_untrusted_run_id_denied_before_drive_read_or_write(self):
        d = CanaryDrive()
        with self.assertRaisesRegex(m.CanaryDenied, "RUN_ID_UNTRUSTED"):
            m.synthetic_staging_canary(d, "9' OR name='x")
        self.assertEqual(d.calls, [])
        self.assertEqual(d.posts, 0)


if __name__ == "__main__":
    unittest.main()
