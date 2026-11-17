"""§216 Drive cache census only: no source bytes, no actual OAuth writes."""
from contextlib import redirect_stdout
from io import StringIO
import json
import os
import unittest
from unittest.mock import patch

from scripts import mst_mfx_style_appowned_pipeline as m
from test_mst_mfx_style_appowned_pipeline import FakeDrive, FakeResponse, owner_env


class FakeCacheDrive(FakeDrive):
    def __init__(self, sizes=None):
        super().__init__()
        self.items = {}
        for name in m.DRIVE_CHILDREN:
            fid = next(k for k,v in self.files.items() if v["name"] == name)
            self.items[fid] = [
                {"id": f"FAKE_CENSUS_{name}_{i:05d}",
                 "mimeType": "application/json",
                 "parents": [fid],
                 "trashed": False,
                 "shared": False,
                 "ownedByMe": True,
                 "isAppAuthorized": True}
                for i in range((sizes or {}).get(name, 0))
            ]
        self.http_fail = False
        self.loop_page_token = False

    def get(self, url, *, params, timeout, **kwargs):
        if url == m.DRIVE_URL[:-1] and "name = '" not in params["q"]:
            self.calls.append(("GET", url, dict(params)))
            if self.http_fail:
                return FakeResponse({"error":"DO_NOT_ECHO"}, 403)
            fid = params["q"].split("'", 2)[1]
            if fid not in self.items:
                return FakeResponse({"error": "wrong parent"}, 404)
            page = params.get("pageToken")
            start = 0 if page is None else int(page.lstrip("p"))
            chunk = self.items[fid][start:start+100]
            following = start + 100
            token = (("p0" if self.loop_page_token else "p"+str(following))
                     if len(self.items[fid]) > following else None)
            return FakeResponse({"files":chunk, "nextPageToken":token})
        return super().get(url,params=params,timeout=timeout,**kwargs)


class AppOwnedCacheCensus216Tests(unittest.TestCase):
    def test_all_empty_means_bootstrap_only_not_published_cache(self):
        d=FakeCacheDrive()
        result=m.inspect_app_owned_cache_census216(d)
        self.assertEqual(result["state"],"BOOTSTRAPPED_FOLDERS_EMPTY")
        self.assertEqual(result["observed_counts"],{name:0 for name in m.DRIVE_CHILDREN})
        self.assertEqual(result["visibility_context"],"GITHUB_ACTIONS_OAUTH_APP_ONLY")
        self.assertEqual(result["schema"],"mst.cloud.app_owned_cache_inventory.v0.1")
        self.assertTrue(result["census_complete"])
        for key in ("cloud_cache_ready","source_retention_rights_attested",
                    "live_cache_producer_attested",
                    "published_manifest_readback_attested",
                    "independent_signed_highwater_attested","eligible_for_trades"):
            self.assertFalse(result[key])
        self.assertEqual(result["drive_writes"],0)
        self.assertTrue(all(call[0]=="GET" for call in d.calls))

    def test_staging_source_does_not_count_as_published_chunks(self):
        d=FakeCacheDrive({"STAGING_ONLY":3,"AUDIT":1})
        x=m.inspect_app_owned_cache_census216(d)
        self.assertEqual(x["state"],"PRIVATE_FILES_PRESENT_UNVERIFIED")
        self.assertEqual(x["observed_counts"]["STAGING_ONLY"],3)
        self.assertEqual(x["observed_counts"]["CHUNKS"],0)
        self.assertEqual(x["observed_counts"]["MANIFESTS"],0)
        self.assertFalse(x["cloud_cache_ready"])

    def test_even_manifest_and_chunks_do_not_authorize_release(self):
        d=FakeCacheDrive({"CHUNKS":1,"MANIFESTS":1,"AUDIT":2})
        x=m.inspect_app_owned_cache_census216(d)
        self.assertEqual(x["observed_counts"]["CHUNKS"],1)
        self.assertEqual(x["observed_counts"]["MANIFESTS"],1)
        self.assertFalse(x["published_manifest_readback_attested"])
        self.assertFalse(x["independent_signed_highwater_attested"])
        self.assertFalse(x["eligible_for_trades"])

    def test_metadata_census_never_emits_ids_or_provider_data(self):
        d=FakeCacheDrive({"CHUNKS":2})
        result=json.dumps(m.inspect_app_owned_cache_census216(d),sort_keys=True)
        self.assertNotIn("FAKE_CENSUS_",result)
        self.assertNotIn("FAKE_APP_ROOT_",result)
        self.assertNotIn("price",result.lower())
        self.assertNotIn("ohlc",result.lower())
        self.assertNotIn("secret",result.lower())

    def test_one_hundred_one_files_requires_two_complete_pages(self):
        d=FakeCacheDrive({"CHUNKS":101})
        x=m.inspect_app_owned_cache_census216(d)
        self.assertEqual(x["observed_counts"]["CHUNKS"],101)
        self.assertTrue(x["census_complete"])
        page_calls=[c[2] for c in d.calls
                    if "name = '" not in c[2].get("q","")]
        self.assertEqual(len(page_calls),5)
        self.assertEqual(sum("pageToken" in params for params in page_calls),1)

    def test_six_hundred_one_files_is_not_reported_complete(self):
        d=FakeCacheDrive({"CHUNKS":601})
        with self.assertRaisesRegex(m.CloudGateDenied,"PAGE_LIMIT"):
            m.inspect_app_owned_cache_census216(d)

    def test_wrong_parent_shared_unowned_and_duplicate_items_fail_closed(self):
        for changes in (
            {"parents":["UNRELATED_PARENT"]},
            {"shared":True},{"ownedByMe":False},
            {"isAppAuthorized":False},{"trashed":True},
            {"mimeType":m.MIME_FOLDER},{"id":"bad id!"}
        ):
            with self.subTest(changes=changes):
                d=FakeCacheDrive({"CHUNKS":1})
                chunk=next(k for k,v in d.files.items() if v["name"]=="CHUNKS")
                d.items[chunk][0].update(changes)
                with self.assertRaisesRegex(m.CloudGateDenied,"ITEM_SCOPE"):
                    m.inspect_app_owned_cache_census216(d)
        d=FakeCacheDrive({"CHUNKS":1,"AUDIT":1})
        chunks=next(k for k,v in d.files.items() if v["name"]=="CHUNKS")
        audit=next(k for k,v in d.files.items() if v["name"]=="AUDIT")
        d.items[audit][0]["id"]=d.items[chunks][0]["id"]
        with self.assertRaisesRegex(m.CloudGateDenied,"ITEM_SCOPE"):
            m.inspect_app_owned_cache_census216(d)

    def test_repeated_token_and_drive_error_refuse_partial_success(self):
        d=FakeCacheDrive({"CHUNKS":201})
        d.loop_page_token=True
        with self.assertRaisesRegex(m.CloudGateDenied,"PAGING_INVALID"):
            m.inspect_app_owned_cache_census216(d)
        d=FakeCacheDrive()
        d.http_fail=True
        with self.assertRaisesRegex(m.CloudGateDenied,"LIST_HTTP_FAILURE"):
            m.inspect_app_owned_cache_census216(d)

    def test_folder_privacy_drift_does_not_count_files(self):
        d=FakeCacheDrive({"CHUNKS":2})
        fid=next(k for k,v in d.files.items() if v["name"]=="CHUNKS")
        d.overrides[fid]={"shared":True}
        with self.assertRaises(m.CloudGateDenied):
            m.inspect_app_owned_cache_census216(d)

    def test_manual_drive_probe_receipt_has_cache_census_and_no_writes(self):
        d=FakeCacheDrive()
        out=StringIO()
        with patch.dict(os.environ,owner_env(),clear=True),patch.object(
                m,"_new_authorized_session",return_value=d),redirect_stdout(out):
            m.main()
        receipt=json.loads(out.getvalue())
        self.assertEqual(receipt["status"],"MST_MFX_STYLE_APP_OWNED_READONLY_PREFLIGHT")
        self.assertEqual(receipt["cache_inventory"]["state"],"BOOTSTRAPPED_FOLDERS_EMPTY")
        self.assertEqual(receipt["drive"]["app_owned_folder_count"],5)
        self.assertFalse(receipt["cloud_cache_publisher_ready"])
        self.assertFalse(receipt["independent_atomic_cas_ready"])
        self.assertEqual(receipt["trade_orders"],0)
        self.assertTrue(all(c[0]=="GET" for c in d.calls))


if __name__=="__main__":
    unittest.main()
