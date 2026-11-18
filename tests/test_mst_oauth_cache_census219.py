"""MST §219 synthetic tests: no live Drive calls, tokens, Cache or trading."""
import unittest

from scripts import mst_oauth_cache_census219 as m
from scripts.mst_oauth_manual_drive_bootstrap import CHILDREN, DRIVE_FILES, ROOT_NAME


def owner_env(**overrides):
    result = {
        "GITHUB_REPOSITORY": "ngluonghoa/MST",
        "GITHUB_REPOSITORY_ID": "1450356304",
        "GITHUB_REPOSITORY_OWNER_ID": "353049266",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_WORKFLOW_REF": m.WORKFLOW_REF,
        "MST_CACHE_CENSUS_CONFIRM": m.CONFIRM,
        "MST_GDRIVE_OAUTH_CLIENT_ID": "FAKE_NOT_A_CLIENT",
        "MST_GDRIVE_OAUTH_CLIENT_SECRET": "FAKE_NOT_A_SECRET",
        "MST_GDRIVE_OAUTH_REFRESH_TOKEN": "FAKE_NOT_A_REFRESH",
    }
    result.update(overrides)
    return result


class Response:
    def __init__(self, data, status=200):
        self.data = data
        self.status_code = status

    def json(self):
        return self.data


class FakeAppOwnedDrive:
    def __init__(self):
        self.root = "FAKE_ROOT_0123456789"
        self.children = {
            name: "FAKE_CHILD_" + name + "_0123456789"
            for name in CHILDREN
        }
        self.metadata = {}
        self.metadata[self.root] = self.folder(self.root, ROOT_NAME,
                                               "FAKE_MYDRIVE_0123456789")
        for name, item_id in self.children.items():
            self.metadata[item_id] = self.folder(item_id, name, self.root)
        self.items = {name: [] for name in CHILDREN}
        self.calls = []
        self.post_calls = 0
        self.response_status = 200
        self.page_behavior = None

    @staticmethod
    def folder(item_id, name, parent):
        return {
            "id": item_id, "name": name, "mimeType": m.FOLDER_MIME,
            "parents": [parent], "trashed": False, "shared": False,
            "ownedByMe": True, "isAppAuthorized": True,
        }

    def file(self, name, number=0):
        return {
            "id": "FAKE_FILE_" + name + "_" + str(number) + "_0123456789",
            "mimeType": "application/json", "parents": [self.children[name]],
            "trashed": False, "shared": False,
            "ownedByMe": True, "isAppAuthorized": True,
        }

    def get(self, url, *, params, timeout, **kwargs):
        self.calls.append(("GET", url, dict(params)))
        if self.response_status != 200:
            return Response({"error": "SECRET_PROVIDER_BODY"}, self.response_status)
        if url.startswith(DRIVE_FILES + "/"):
            return Response(self.metadata[url.rsplit("/", 1)[-1]])
        if url != DRIVE_FILES:
            raise AssertionError("unexpected network host")
        q = params.get("q", "")
        if "name = '" in q:
            name = q.split("name = '", 1)[1].split("'", 1)[0]
            parent = self.root if name != ROOT_NAME else "FAKE_MYDRIVE_0123456789"
            ids = [self.root] if name == ROOT_NAME else [self.children.get(name)]
            entries = [
                {k: v for k, v in self.metadata.get(item_id, {}).items()
                 if k in ("id", "name", "mimeType", "parents", "trashed")}
                for item_id in ids if item_id and
                self.metadata.get(item_id, {}).get("parents") == [parent]
            ]
            return Response({"files": entries})
        child_id = q.split("'", 2)[1]
        target = next((n for n, i in self.children.items() if i == child_id), None)
        if target is None:
            raise AssertionError("unrecognized parent in source list")
        if self.page_behavior is not None:
            return Response(self.page_behavior(target, params))
        return Response({"files": self.items[target]})

    def post(self, *args, **kwargs):
        self.post_calls += 1
        raise AssertionError("a read-only census must never POST to Drive")


class CacheCensus219Tests(unittest.TestCase):
    def test_owner_gate_positive_existing_oauth(self):
        secrets = m.authorize_manual_readonly(owner_env())
        self.assertEqual(secrets.client_id, "FAKE_NOT_A_CLIENT")

    def test_owner_gate_rejects_nonmain_wrong_workflow_or_unconfirmed(self):
        for changed in (
            {"GITHUB_REF": "refs/heads/draft"},
            {"GITHUB_REPOSITORY": "somefork/MST"},
            {"GITHUB_REPOSITORY_ID": "123"},
            {"GITHUB_REPOSITORY_OWNER_ID": "123"},
            {"GITHUB_EVENT_NAME": "schedule"},
            {"GITHUB_WORKFLOW_REF": "wrong"},
            {"MST_CACHE_CENSUS_CONFIRM": "NO"},
        ):
            with self.subTest(changed=changed), self.assertRaises(m.CensusDenied):
                m.authorize_manual_readonly(owner_env(**changed))

    def test_missing_secret_is_fail_closed(self):
        for key in m.OAUTH_KEYS:
            with self.subTest(key=key), self.assertRaisesRegex(
                m.CensusDenied, "EXISTING_OAUTH_SECRET_TRIO_REQUIRED"
            ):
                m.authorize_manual_readonly(owner_env(**{key: ""}))

    def test_no_bootstrap_or_service_account_fallback(self):
        for changed in (
            {"MST_OAUTH_MODE": "bootstrap"},
            {"MST_GDRIVE_SERVICE_ACCOUNT_JSON": "FAKE_KEY"},
        ):
            with self.subTest(changed=changed), self.assertRaisesRegex(
                m.CensusDenied, "NO_BOOTSTRAP_OR_WIF_FALLBACK"
            ):
                m.authorize_manual_readonly(owner_env(**changed))

    def test_empty_private_app_folders_verified_but_not_production(self):
        drive = FakeAppOwnedDrive()
        result = m.census_app_owned_cache(drive)
        self.assertEqual(result["state"], "BOOTSTRAPPED_FOLDERS_EMPTY")
        self.assertEqual(result["verified_app_owned_folder_count"], 5)
        self.assertEqual(result["observed_counts"], {n: 0 for n in CHILDREN})
        self.assertEqual(result["visibility_context"], "GITHUB_ACTIONS_OAUTH_APP_ONLY")
        for flag in (
            "google_drive_write_performed", "market_provider_called",
            "source_retention_rights_attested",
            "published_manifest_readback_attested",
            "independent_signed_highwater_attested",
            "production_cache_ready", "signals_and_trading_eligible",
        ):
            self.assertFalse(result[flag])
        self.assertEqual(drive.post_calls, 0)
        self.assertTrue(all(call[0] == "GET" for call in drive.calls))
        self.assertNotIn(drive.root, str(result))

    def test_nonempty_files_not_labeled_as_approved_cache(self):
        drive = FakeAppOwnedDrive()
        drive.items["CHUNKS"] = [drive.file("CHUNKS")]
        drive.items["MANIFESTS"] = [drive.file("MANIFESTS")]
        result = m.census_app_owned_cache(drive)
        self.assertEqual(result["state"], "PRIVATE_FILES_PRESENT_UNVERIFIED")
        self.assertEqual(result["observed_counts"]["CHUNKS"], 1)
        self.assertEqual(result["observed_counts"]["MANIFESTS"], 1)
        self.assertFalse(result["production_cache_ready"])

    def test_unshared_ownership_or_app_scope_drift_is_denied(self):
        for attr, bad in (("shared", True), ("ownedByMe", False),
                          ("isAppAuthorized", False), ("trashed", True)):
            drive = FakeAppOwnedDrive()
            drive.metadata[drive.children["CHUNKS"]][attr] = bad
            with self.subTest(attr=attr), self.assertRaisesRegex(
                m.CensusDenied, "FOLDER_SCOPE_UNVERIFIED"
            ):
                m.census_app_owned_cache(drive)
            self.assertEqual(drive.post_calls, 0)

    def test_misparented_folder_or_duplicate_id_fails_closed(self):
        drive = FakeAppOwnedDrive()
        drive.metadata[drive.children["AUDIT"]]["parents"] = ["FAKE_WRONG_PARENT_123"]
        with self.assertRaises(m.CensusDenied):
            m.census_app_owned_cache(drive)
        drive = FakeAppOwnedDrive()
        drive.children["MANIFESTS"] = drive.children["CHUNKS"]
        with self.assertRaises(m.CensusDenied):
            m.census_app_owned_cache(drive)

    def test_duplicate_file_across_folders_fails_closed(self):
        drive = FakeAppOwnedDrive()
        one = drive.file("CHUNKS")
        drive.items["CHUNKS"] = [one]
        drive.items["AUDIT"] = [
            dict(one, parents=[drive.children["AUDIT"]])
        ]
        with self.assertRaisesRegex(
            m.CensusDenied, "ITEM_SCOPE_INVALID"
        ):
            m.census_app_owned_cache(drive)

    def test_unowned_or_misparented_file_fails_closed(self):
        for changed in ({"ownedByMe": False},
                        {"shared": True},
                        {"parents": ["FAKE_FOREIGN_0123456789"]},
                        {"isAppAuthorized": False},
                        {"mimeType": m.FOLDER_MIME}):
            drive = FakeAppOwnedDrive()
            drive.items["AUDIT"] = [dict(drive.file("AUDIT"), **changed)]
            with self.subTest(changed=changed), self.assertRaises(
                m.CensusDenied
            ):
                m.census_app_owned_cache(drive)

    def test_provider_http_body_never_leaks(self):
        drive = FakeAppOwnedDrive()
        drive.response_status = 403
        with self.assertRaises(m.CensusDenied) as raised:
            m.census_app_owned_cache(drive)
        self.assertNotIn("SECRET_PROVIDER_BODY", str(raised.exception))

    def test_malformed_page_is_denied_not_partial_count(self):
        drive = FakeAppOwnedDrive()
        drive.page_behavior = lambda name, params: {"files": "SECRET"}
        with self.assertRaisesRegex(m.CensusDenied, "PAGE_INVALID"):
            m.census_app_owned_cache(drive)

    def test_empty_page_with_next_token_continues_to_real_items(self):
        # Google Drive files.list may legally return an empty nonfinal page.
        drive = FakeAppOwnedDrive()
        def pages(name, params):
            if name != "AUDIT":
                return {"files": [], "incompleteSearch": False}
            if not params.get("pageToken"):
                return {
                    "files": [], "nextPageToken": "PAGE_2",
                    "incompleteSearch": False,
                }
            self.assertEqual(params["pageToken"], "PAGE_2")
            self.assertIn("incompleteSearch", params["fields"])
            return {"files": [drive.file("AUDIT")], "incompleteSearch": False}
        drive.page_behavior = pages
        result = m.census_app_owned_cache(drive)
        self.assertEqual(result["observed_counts"]["AUDIT"], 1)
        self.assertEqual(result["state"], "PRIVATE_FILES_PRESENT_UNVERIFIED")
        self.assertFalse(result["production_cache_ready"])
        self.assertEqual(drive.post_calls, 0)

    def test_incomplete_search_or_malformed_flag_fails_closed(self):
        for flag in (True, None, "true", 1):
            drive = FakeAppOwnedDrive()
            drive.page_behavior = (
                lambda name, params, flag=flag:
                {"files": [], "incompleteSearch": flag}
            )
            with self.subTest(flag=flag), self.assertRaisesRegex(
                m.CensusDenied, "INCOMPLETE_SEARCH"
            ):
                m.census_app_owned_cache(drive)
            self.assertEqual(drive.post_calls, 0)

    def test_pagination_more_than_limit_fails_closed(self):
        drive = FakeAppOwnedDrive()
        def many_pages(name, params):
            if name != "AUDIT":
                return {"files": []}
            pos = int(params.get("pageToken", "0"))
            result = {"files": [drive.file("AUDIT", pos)]}
            result["nextPageToken"] = str(pos + 1)
            return result
        drive.page_behavior = many_pages
        with self.assertRaisesRegex(m.CensusDenied, "PAGE_LIMIT_REACHED"):
            m.census_app_owned_cache(drive)
        self.assertEqual(drive.post_calls, 0)

    def test_repeated_or_blank_pagination_token_denied(self):
        for token in ("same", "", 123, "x" * 1025):
            drive = FakeAppOwnedDrive()
            def pages(name, params):
                if name != "AUDIT":
                    return {"files": []}
                page = {"files": [drive.file("AUDIT", 0)]}
                page["nextPageToken"] = token
                return page
            drive.page_behavior = pages
            with self.subTest(token=str(token)[:20]), self.assertRaises(
                m.CensusDenied
            ):
                m.census_app_owned_cache(drive)

    def test_no_ids_or_secrets_in_public_receipt(self):
        drive = FakeAppOwnedDrive()
        result = m.census_app_owned_cache(drive)
        printed = str(result)
        self.assertNotIn("FAKE_ROOT_", printed)
        self.assertNotIn("FAKE_CHILD_", printed)
        self.assertNotIn("FAKE_NOT_A_REFRESH", printed)


if __name__ == "__main__":
    unittest.main()
