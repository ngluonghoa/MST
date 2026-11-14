"""Synthetic-only tests for real-Drive staging workflow boundaries.

All HTTP sessions and files are in-memory fakes; no secrets or network calls.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest
from scripts import mst_cache_v21_staging_fictional_manual as m


def env(**updates):
    base = {
        "GITHUB_REPOSITORY": m.OWNER_REPO,
        "GITHUB_REPOSITORY_ID": "1450356304",
        "GITHUB_REPOSITORY_OWNER_ID": "353049266",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_WORKFLOW_REF": m.EXPECTED_WORKFLOW_REF,
        "GITHUB_RUN_ID": "43037551110",
        "GITHUB_RUN_ATTEMPT": "1",
        "MST_STAGING_MODE": "probe",
        "MST_OAUTH_BOOTSTRAP_ACCEPTED": "false",
        "MST_CACHE_V21_STAGING_WRITE_ACCEPTED": "false",
        "MST_GDRIVE_OAUTH_CLIENT_ID": "FAKE_CLIENT_ID",
        "MST_GDRIVE_OAUTH_CLIENT_SECRET": "FAKE_CLIENT_SECRET",
        "MST_GDRIVE_OAUTH_REFRESH_TOKEN": "FAKE_REFRESH_TOKEN",
    }
    base.update(updates)
    return base


class FakeResponse:
    def __init__(self, data=None, code=200, content=None):
        self.data = data
        self.status_code = code
        self._content = content
        self.closed = False
        self.headers = {"Content-Length": str(len(content))} if content is not None else {}

    def json(self):
        return self.data

    def iter_content(self, chunk_size):
        yield self._content

    def close(self):
        self.closed = True


class FakeSession:
    ROOT_ID = "FAKE_ROOT_123456"
    STAGE_ID = "FAKE_STAGE_123456"
    FILE_ID = "FAKE_FILE_123456"

    def __init__(self):
        self.read_calls = 0
        self.upload_calls = 0
        self.list_calls = 0
        self.media_bytes = None
        self.body = None
        self.fail_root = False
        self.fail_stage = False
        self.fail_upload = False
        self.fail_media = False
        self.mutate_second_read = False
        self.metadata_tamper = False
        self.duplicate_list = False
        self.paginated_list = False
        self.payload_name = None
        self.post_headers = None
        self.post_params = None
        self.shared_root = False
        self.shared_stage = False
        self.shared_file = False
        self.unowned_stage = False
        self.unowned_file = False
        self.not_app_stage = False
        self.not_app_file = False
        self.stream_oversize_no_length = False
        self.last_media_response = None
        self.incomplete_search = False
        self.invalid_search_flag = False
        self.wrong_mime_existing = False
        self.list_queries = []
        self.version_drift_after_reads = False
        self.missing_version = False
        self.malformed_version = False
        self.share_root_after_media_reads = False
        self.share_stage_after_media_reads = False
        self.revoke_stage_app_after_media_reads = False
        self.reparent_stage_after_media_reads = False
        self.late_named_duplicate = False
        self.late_named_absent = False
        self.late_named_wrong_mime = False
        self.late_named_new_identity = False
        self.late_named_wrong_parent = False
        self.preexisting_extra_staging_file = False
        self.late_extra_staging_file = False

    def folder(self, name):
        root = name == m.ROOT
        return {
            "id": self.ROOT_ID if root else self.STAGE_ID,
            "name": name,
            "mimeType": m.FOLDER_MIME,
            "parents": (["FAKE_MY_DRIVE_ROOT"] if root else
                        ["FAKE_OTHER_PARENT"] if self.reparent_stage_after_media_reads and self.read_calls >= 2
                        else [self.ROOT_ID]),
            "trashed": False,
            "shared": (self.shared_root or (root and self.share_root_after_media_reads and self.read_calls >= 2)
                       if root else self.shared_stage or (self.share_stage_after_media_reads and self.read_calls >= 2)),
            "ownedByMe": True if root else not self.unowned_stage,
            "isAppAuthorized": (True if root else not (self.not_app_stage or
                               (self.revoke_stage_app_after_media_reads and self.read_calls >= 2))),
        }

    def file(self):
        name = self.payload_name
        return {
            "id": self.FILE_ID,
            "name": name,
            "mimeType": "application/json",
            "parents": [self.STAGE_ID],
            "trashed": False,
            "appProperties": {
                "mst_fixture_only": "true",
                "sha256": hashlib.sha256(self.media_bytes).hexdigest(),
                "schema": "fictional-v21",
            },
            "md5Checksum": hashlib.md5(self.media_bytes).hexdigest(),
            "size": str(len(self.media_bytes)),
            "version": (None if self.missing_version else
                        "invalid" if self.malformed_version else
                        "2" if self.version_drift_after_reads and self.read_calls >= 2 else "1"),
            "shared": self.shared_file,
            "ownedByMe": not self.unowned_file,
            "isAppAuthorized": not self.not_app_file,
        }

    def get(self, url, *, params, timeout, **kwargs):
        if url == m.DRIVE:
            self.list_calls += 1
            query = params["q"]
            self.list_queries.append(query)
            if f"name = '{m.ROOT}'" in query:
                payload = [] if self.fail_root else [self.folder(m.ROOT)]
            elif f"name = '{m.CHILD}'" in query:
                payload = [] if self.fail_stage else [self.folder(m.CHILD)]
            else:
                if self.wrong_mime_existing:
                    payload = [{"id": self.FILE_ID, "name": self.payload_name,
                                "mimeType": "text/plain", "parents": [self.STAGE_ID],
                                "trashed": False}]
                else:
                    payload = [self.file()] if self.media_bytes is not None else []
            # Fixture lookup now intentionally inventories the whole private
            # folder without filtering on the requested filename or MIME.
            is_stage_census = (f"'{self.STAGE_ID}' in parents" in query
                               and "name =" not in query)
            if is_stage_census and self.preexisting_extra_staging_file and payload:
                payload.append({**payload[0], "id": "FAKE_UNRELATED_FILE_1234",
                                "name": "FAKE_UNRELATED_DOCUMENT.txt", "mimeType": "text/plain"})
            if self.read_calls >= 2 and is_stage_census:
                if self.late_named_duplicate and payload:
                    payload.append({**payload[0], "id": "FAKE_LATE_OTHER_FILE_ID"})
                elif self.late_extra_staging_file and payload:
                    payload.append({**payload[0], "id": "FAKE_LATE_UNRELATED_FILE",
                                    "name": "README.txt", "mimeType": "text/plain"})
                elif self.late_named_absent:
                    payload = []
                elif self.late_named_wrong_mime and payload:
                    payload[0] = {**payload[0], "mimeType": "text/plain"}
                elif self.late_named_new_identity and payload:
                    payload[0] = {**payload[0], "id": "FAKE_LATE_NEW_FILE_ID"}
                elif self.late_named_wrong_parent and payload:
                    payload[0] = {**payload[0], "parents": ["FAKE_OTHER_PARENT"]}
            if self.duplicate_list and payload:
                payload.append(payload[0])
            response = {"files": payload,
                        "incompleteSearch": "false" if self.invalid_search_flag else self.incomplete_search}
            if self.paginated_list:
                response["nextPageToken"] = "FAKE_NEXT"
            return FakeResponse(response)
        if url.endswith(self.ROOT_ID):
            return FakeResponse(self.folder(m.ROOT))
        if url.endswith(self.STAGE_ID):
            return FakeResponse(self.folder(m.CHILD))
        if url.endswith(self.FILE_ID) and params.get("alt") == "media":
            self.read_calls += 1
            if self.fail_media:
                return FakeResponse(code=403, content=b"denied")
            data = self.media_bytes
            if self.read_calls == 2 and self.mutate_second_read:
                data = b"tampered"
            if self.stream_oversize_no_length:
                data = b"x" * (m.READ_LIMIT + 1)
            response = FakeResponse(content=data)
            if self.stream_oversize_no_length:
                response.headers = {}
            self.last_media_response = response
            return response
        if url.endswith(self.FILE_ID):
            data = self.file()
            if self.metadata_tamper:
                data["md5Checksum"] = "tampered"
            return FakeResponse(data)
        return FakeResponse(code=404)

    def post(self, url, *, params, headers, data, timeout):
        self.upload_calls += 1
        self.post_headers = headers
        self.post_params = params
        if self.fail_upload:
            return FakeResponse(code=403)
        boundary = b"--" + m.BOUNDARY.encode()
        # Fake parser for the two exact RFC2387 parts.
        parts = data.split(boundary)
        self.body = data
        self.media_bytes = parts[2].split(b"\r\n\r\n", 1)[1].removesuffix(b"\r\n")
        meta = json.loads(parts[1].split(b"\r\n\r\n", 1)[1].rstrip(b"\r\n"))
        self.payload_name = meta["name"]
        return FakeResponse(self.file(), code=201)


class GuardTests(unittest.TestCase):
    def denied(self, **updates):
        with self.assertRaises(m.StagingDenied):
            m.guard(env(**updates))

    def test_01_probe_defaults(self):
        mode, secrets, name = m.guard(env())
        self.assertEqual(mode, "probe")
        self.assertEqual(name, "MST_FAKE_V21_RUN_43037551110_1.json")
        self.assertNotIn("FAKE_REFRESH_TOKEN", repr(secrets))

    def test_02_explicit_staging_accepted(self):
        mode, _, _ = m.guard(env(MST_STAGING_MODE="synthetic-write",
                                 MST_CACHE_V21_STAGING_WRITE_ACCEPTED="true"))
        self.assertEqual(mode, "synthetic-write")

    def test_03_write_without_owner_acceptance_denied(self):
        self.denied(MST_STAGING_MODE="synthetic-write")

    def test_04_wrong_variable_case_denied(self):
        self.denied(MST_STAGING_MODE="synthetic-write",
                    MST_CACHE_V21_STAGING_WRITE_ACCEPTED="TRUE")

    def test_05_old_bootstrap_write_gate_must_be_false(self):
        self.denied(MST_OAUTH_BOOTSTRAP_ACCEPTED="true")

    def test_06_repo_mismatch_denied(self):
        self.denied(GITHUB_REPOSITORY="ngluonghoa/MFX")

    def test_07_repo_id_mismatch_denied(self):
        self.denied(GITHUB_REPOSITORY_ID="123")

    def test_08_owner_id_mismatch_denied(self):
        self.denied(GITHUB_REPOSITORY_OWNER_ID="123")

    def test_09_main_ref_required(self):
        self.denied(GITHUB_REF="refs/heads/dev")

    def test_10_dispatch_required(self):
        self.denied(GITHUB_EVENT_NAME="schedule")

    def test_11_exact_workflow_ref_required(self):
        self.denied(GITHUB_WORKFLOW_REF="ngluonghoa/MST/.github/workflows/other.yml@refs/heads/main")

    def test_12_secret_trio_client_missing(self):
        self.denied(MST_GDRIVE_OAUTH_CLIENT_ID="")

    def test_13_secret_trio_secret_missing(self):
        self.denied(MST_GDRIVE_OAUTH_CLIENT_SECRET=" ")

    def test_14_secret_trio_refresh_missing(self):
        self.denied(MST_GDRIVE_OAUTH_REFRESH_TOKEN="")

    def test_15_wif_serviceaccount_fallback_denied(self):
        self.denied(MST_GDRIVE_SERVICE_ACCOUNT_JSON="FAKE")

    def test_16_invalid_run_id(self):
        self.denied(GITHUB_RUN_ID="../../bad")

    def test_17_invalid_run_attempt(self):
        self.denied(GITHUB_RUN_ATTEMPT="0")

    def test_18_invalid_mode(self):
        self.denied(MST_STAGING_MODE="bootstrap")

    def test_19_invalid_file_id(self):
        with self.assertRaises(m.StagingDenied):
            m.validate_id("../../../")

    def test_20_fixture_requires_strict_filename(self):
        with self.assertRaises(m.StagingDenied):
            m.fixed_fixture("VCB.json")

    def test_21_fixture_contains_no_market(self):
        b = m.fixed_fixture("MST_FAKE_V21_RUN_43037551110_1.json")
        self.assertLess(len(b), 1024)
        data = json.loads(b)
        self.assertTrue(data["fixture_only"])
        self.assertNotIn("symbol", data)
        self.assertNotIn("ohlcv", data)
        self.assertNotIn("provider", data)

    def test_62_deny_write_on_second_github_attempt_even_with_approval(self):
        with self.assertRaisesRegex(m.StagingDenied, "WRITE_RERUN_DENIED"):
            m.guard(env(MST_STAGING_MODE="synthetic-write",
                        MST_CACHE_V21_STAGING_WRITE_ACCEPTED="true",
                        GITHUB_RUN_ATTEMPT="2"))

    def test_63_allow_read_only_probe_on_second_github_attempt(self):
        mode, _, name = m.guard(env(GITHUB_RUN_ATTEMPT="2"))
        self.assertEqual(mode, "probe")
        self.assertEqual(name, "MST_FAKE_V21_RUN_43037551110_2.json")


class CloudFakeDriveTests(unittest.TestCase):
    def setUp(self):
        self.s = FakeSession()
        self.name = "MST_FAKE_V21_RUN_43037551110_1.json"

    def test_22_probe_readonly_no_upload(self):
        result = m.run(self.s, self.name, "probe")
        self.assertEqual(result["status"], "MST_STAGING_EXISTING_FOLDER_READ_ONLY_PASS")
        self.assertEqual(self.s.upload_calls, 0)
        self.assertEqual(self.s.read_calls, 0)

    def test_23_upload_two_reads_success(self):
        result = m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(result["status"], "MST_STAGING_FICTIONAL_JSON_UPLOAD_TWO_REAL_READS_PASS")
        self.assertEqual(self.s.upload_calls, 1)
        self.assertEqual(self.s.read_calls, 2)
        self.assertTrue(result["sha256_integrity_verified"])
        self.assertFalse(result["google_drive_atomic_cas_proven"])
        self.assertFalse(result["production_cache_activated"])

    def test_24_repeat_run_exact_name_reuses_existing(self):
        m.run(self.s, self.name, "synthetic-write")
        m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.upload_calls, 1)
        self.assertEqual(self.s.read_calls, 4)

    def test_25_multipart_headers_and_order(self):
        m.run(self.s, self.name, "synthetic-write")
        self.assertIn("multipart/related; boundary=", self.s.post_headers["Content-Type"])
        self.assertLess(self.s.body.find(b'"name"'), self.s.body.find(b"FICTIONAL_INTEGRITY_PROBE"))

    def test_26_missing_root_denied_without_upload(self):
        self.s.fail_root = True
        with self.assertRaises(m.StagingDenied):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.upload_calls, 0)

    def test_27_missing_stage_denied_without_upload(self):
        self.s.fail_stage = True
        with self.assertRaises(m.StagingDenied):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.upload_calls, 0)

    def test_28_duplicate_name_fail_closed(self):
        self.s.duplicate_list = True
        with self.assertRaises(m.StagingDenied):
            m.run(self.s, self.name, "synthetic-write")

    def test_29_incomplete_page_fail_closed(self):
        self.s.paginated_list = True
        with self.assertRaises(m.StagingDenied):
            m.run(self.s, self.name, "probe")

    def test_30_upload_403_fail_closed(self):
        self.s.fail_upload = True
        with self.assertRaises(m.StagingDenied):
            m.run(self.s, self.name, "synthetic-write")

    def test_31_media_403_fail_closed(self):
        self.s.fail_media = True
        with self.assertRaises(m.StagingDenied):
            m.run(self.s, self.name, "synthetic-write")

    def test_32_second_read_mutation_denied(self):
        self.s.mutate_second_read = True
        with self.assertRaisesRegex(m.StagingDenied, "CONTENT_MISMATCH"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.read_calls, 2)

    def test_33_metadata_tamper_denied(self):
        self.s.metadata_tamper = True
        with self.assertRaises(m.StagingDenied):
            m.run(self.s, self.name, "synthetic-write")

    def test_34_return_no_internal_file_id(self):
        receipt = m.run(self.s, self.name, "synthetic-write")
        self.assertNotIn(self.s.FILE_ID, repr(receipt))
        self.assertNotIn(self.s.STAGE_ID, repr(receipt))

    def test_35_upload_is_one_file_only(self):
        m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.upload_calls, 1)

    def test_36_readonly_probe_no_fake_content(self):
        result = m.run(self.s, self.name, "probe")
        self.assertFalse(result["real_google_drive_file_written"])

    def test_37_no_existing_folder_creation(self):
        m.run(self.s, self.name, "synthetic-write")
        self.assertNotIn(b"application/vnd.google-apps.folder", self.s.body)

    def test_38_reject_invalid_mode_inside_runner(self):
        with self.assertRaises(m.StagingDenied):
            m.run(self.s, self.name, "delete")

    def test_39_empty_content_rejected(self):
        with self.assertRaises(m.StagingDenied):
            m.make_multipart({}, b"\n")

    def test_40_chunk_size_bounded(self):
        with self.assertRaises(m.StagingDenied):
            m.make_multipart({}, b"A"*1025)

    def test_41_no_actions_schedule_or_broad_permissions(self):
        y = (Path(__file__).resolve().parents[1] /
             ".github/workflows/mst-cache-v21-staging-fictional-manual.yml").read_text()
        self.assertIn("workflow_dispatch:", y)
        self.assertNotIn("\n  schedule:", y)
        self.assertNotIn("id-token: write", y)
        self.assertIn("contents: read", y)
        self.assertIn("default: probe", y)
        self.assertIn("MST_CACHE_V21_STAGING_WRITE_ACCEPTED", y)

    def test_42_no_vendor_or_gcp_privilege_scope(self):
        source = (Path(__file__).resolve().parents[1] /
                  "scripts/mst_cache_v21_staging_fictional_manual.py").read_text().lower()
        for vendor in ("ssi.com.vn", "dnse.com.vn", "vcbs.com.vn",
                       "https://www.googleapis.com/auth/drive\"",
                       "google cloud billing", "trading order"):
            self.assertNotIn(vendor, source)

    def test_43_receipt_explicit_no_live_cache(self):
        r = m.run(self.s, self.name, "synthetic-write")
        for key in ("market_source_called", "real_ohlcv_downloaded",
                    "market_cache_written", "production_cache_activated",
                    "google_drive_atomic_cas_proven", "independent_highwater_proven",
                    "user_created_watchlist_access_proven"):
            self.assertIs(r[key], False)

    def test_44_sha256_matches_metadata(self):
        m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.file()["appProperties"]["sha256"],
                         hashlib.sha256(self.s.media_bytes).hexdigest())

    def test_45_refuse_shared_root_before_any_upload(self):
        self.s.shared_root = True
        with self.assertRaisesRegex(m.StagingDenied, "ROOT_READBACK"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.upload_calls, 0)

    def test_46_refuse_shared_staging_folder_before_upload(self):
        self.s.shared_stage = True
        with self.assertRaisesRegex(m.StagingDenied, "CHILD_READBACK"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.upload_calls, 0)

    def test_47_refuse_staging_not_owned_by_same_google_user(self):
        self.s.unowned_stage = True
        with self.assertRaises(m.StagingDenied):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.upload_calls, 0)

    def test_48_refuse_staging_not_authorized_to_same_app(self):
        self.s.not_app_stage = True
        with self.assertRaises(m.StagingDenied):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.upload_calls, 0)

    def test_49_refuse_created_file_shared(self):
        self.s.shared_file = True
        with self.assertRaisesRegex(m.StagingDenied, "METADATA"):
            m.run(self.s, self.name, "synthetic-write")

    def test_50_refuse_created_file_not_owned(self):
        self.s.unowned_file = True
        with self.assertRaises(m.StagingDenied):
            m.run(self.s, self.name, "synthetic-write")

    def test_51_refuse_created_file_not_app_authorized(self):
        self.s.not_app_file = True
        with self.assertRaises(m.StagingDenied):
            m.run(self.s, self.name, "synthetic-write")

    def test_52_override_domain_default_visibility_on_file_create(self):
        m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.post_params["ignoreDefaultVisibility"], "true")
        self.assertEqual(self.s.post_params["uploadType"], "multipart")

    def test_53_reject_oversize_chunked_http_without_content_length(self):
        self.s.stream_oversize_no_length = True
        with self.assertRaisesRegex(m.StagingDenied, "MEDIA_OVERSIZE"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.read_calls, 1)
        self.assertTrue(self.s.last_media_response.closed)

    def test_54_metadata_parent_stays_staging_only(self):
        m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.file()["parents"], [self.s.STAGE_ID])

    def test_55_read_only_probe_refuses_public_staging(self):
        self.s.shared_stage = True
        with self.assertRaises(m.StagingDenied):
            m.run(self.s, self.name, "probe")
        self.assertEqual(self.s.upload_calls, 0)

    def test_56_file_version_changes_after_two_reads_denied(self):
        self.s.version_drift_after_reads = True
        with self.assertRaisesRegex(m.StagingDenied, "VERSION_DRIFT"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.upload_calls, 1)
        self.assertEqual(self.s.read_calls, 2)

    def test_57_missing_file_version_denied(self):
        self.s.missing_version = True
        with self.assertRaisesRegex(m.StagingDenied, "VERSION_UNAVAILABLE"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.read_calls, 0)

    def test_58_malformed_file_version_denied(self):
        self.s.malformed_version = True
        with self.assertRaisesRegex(m.StagingDenied, "VERSION_UNAVAILABLE"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.read_calls, 0)

    def test_59_incomplete_search_denies_probe_without_upload(self):
        self.s.incomplete_search = True
        with self.assertRaisesRegex(m.StagingDenied, "INCOMPLETE_DRIVE_SEARCH"):
            m.run(self.s, self.name, "probe")
        self.assertEqual(self.s.upload_calls, 0)

    def test_60_invalid_incomplete_flag_denies_writer(self):
        self.s.invalid_search_flag = True
        with self.assertRaisesRegex(m.StagingDenied, "INCOMPLETE_DRIVE_SEARCH"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.upload_calls, 0)

    def test_61_same_name_different_mime_denies_create(self):
        self.s.wrong_mime_existing = True
        self.s.payload_name = self.name
        with self.assertRaisesRegex(m.StagingDenied, "LIST_METADATA_DRIFT"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.upload_calls, 0)
        self.assertTrue(self.s.list_queries)
        self.assertTrue(all("mimeType =" not in q for q in self.s.list_queries))

    def test_64_refuse_root_shared_after_successful_file_reads(self):
        self.s.share_root_after_media_reads = True
        with self.assertRaisesRegex(m.StagingDenied, "ROOT_READBACK_DRIFT"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.read_calls, 2)
        self.assertEqual(self.s.upload_calls, 1)

    def test_65_refuse_stage_shared_after_successful_file_reads(self):
        self.s.share_stage_after_media_reads = True
        with self.assertRaisesRegex(m.StagingDenied, "CHILD_READBACK_DRIFT"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.read_calls, 2)

    def test_66_refuse_stage_app_access_revoked_after_reads(self):
        self.s.revoke_stage_app_after_media_reads = True
        with self.assertRaisesRegex(m.StagingDenied, "CHILD_READBACK_DRIFT"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.read_calls, 2)

    def test_67_refuse_stage_reparent_after_reads(self):
        self.s.reparent_stage_after_media_reads = True
        with self.assertRaisesRegex(m.StagingDenied, "WRONG_PARENT"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.read_calls, 2)

    def test_68_success_rechecks_both_folder_chain_metadata(self):
        m.run(self.s, self.name, "synthetic-write")
        # Root+stage preflight (2), filename preflight (1), folder
        # postcondition (2), and independent final same-name check (1).
        self.assertEqual(self.s.list_calls, 6)
        self.assertEqual(self.s.read_calls, 2)

    def test_69_duplicate_name_appears_after_media_reads_denied(self):
        self.s.late_named_duplicate = True
        with self.assertRaisesRegex(m.StagingDenied, "AMBIGUOUS_DRIVE_LIST"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.read_calls, 2)
        self.assertEqual(self.s.upload_calls, 1)

    def test_70_original_name_disappears_after_media_reads_denied(self):
        self.s.late_named_absent = True
        with self.assertRaisesRegex(m.StagingDenied, "FILE_IDENTITY_DRIFT"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.read_calls, 2)

    def test_71_original_name_changes_mime_after_media_reads_denied(self):
        self.s.late_named_wrong_mime = True
        with self.assertRaisesRegex(m.StagingDenied, "LIST_METADATA_DRIFT"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.read_calls, 2)

    def test_72_same_name_new_id_after_media_reads_denied(self):
        self.s.late_named_new_identity = True
        with self.assertRaisesRegex(m.StagingDenied, "FILE_IDENTITY_DRIFT"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.read_calls, 2)

    def test_73_file_reparented_after_media_reads_denied(self):
        self.s.late_named_wrong_parent = True
        with self.assertRaisesRegex(m.StagingDenied, "WRONG_PARENT"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.read_calls, 2)

    def test_74_second_distinct_dispatch_denied_if_prior_fixture_exists(self):
        prior_name = "MST_FAKE_V21_RUN_43037551111_1.json"
        self.s.payload_name = prior_name
        self.s.media_bytes = m.fixed_fixture(prior_name)
        with self.assertRaisesRegex(m.StagingDenied, "LIST_METADATA_DRIFT"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.upload_calls, 0)
        self.assertEqual(self.s.read_calls, 0)

    def test_75_unrelated_existing_staging_file_denies_upload(self):
        self.s.wrong_mime_existing = True
        self.s.payload_name = "README.txt"
        with self.assertRaisesRegex(m.StagingDenied, "LIST_METADATA_DRIFT"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.upload_calls, 0)

    def test_76_prior_same_run_plus_second_object_denies_upload(self):
        self.s.payload_name = self.name
        self.s.media_bytes = m.fixed_fixture(self.name)
        self.s.preexisting_extra_staging_file = True
        with self.assertRaisesRegex(m.StagingDenied, "AMBIGUOUS_DRIVE_LIST"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.upload_calls, 0)

    def test_77_late_unrelated_object_blocks_success_receipt(self):
        self.s.late_extra_staging_file = True
        with self.assertRaisesRegex(m.StagingDenied, "AMBIGUOUS_DRIVE_LIST"):
            m.run(self.s, self.name, "synthetic-write")
        self.assertEqual(self.s.upload_calls, 1)
        self.assertEqual(self.s.read_calls, 2)

    def test_78_writer_lists_all_staging_items_not_only_filename(self):
        m.run(self.s, self.name, "synthetic-write")
        stage_queries = [q for q in self.s.list_queries
                         if f"'{self.s.STAGE_ID}' in parents" in q]
        self.assertEqual(len(stage_queries), 2)
        self.assertTrue(all("name =" not in q and "mimeType =" not in q
                            for q in stage_queries))


if __name__ == "__main__":
    unittest.main()
