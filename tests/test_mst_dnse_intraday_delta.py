"""All HTTP, source bars and Drive objects here are fictional in-memory fakes.

No vendor API, local Cache, OAuth account, broker, or persistent Drive write.
"""
import hashlib
import json
import unittest

from scripts import mst_dnse_intraday_delta as nd
from scripts import mst_mfx_style_appowned_pipeline as m


class Response:
    def __init__(self, data=None, status=200, content=None):
        self.status_code = status
        self._data = data if data is not None else {}
        self.content = (json.dumps(self._data).encode()
                        if content is None else content)

    def json(self):
        return self._data


def env(tf="M5", **changes):
    source = {
        "GITHUB_REPOSITORY": m.REPO,
        "GITHUB_REPOSITORY_ID": m.REPO_ID,
        "GITHUB_REPOSITORY_OWNER_ID": m.OWNER_ID,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_WORKFLOW_REF": m.WORKFLOW,
        "MST_MFX_APP_OWNED_READONLY_ACCEPTED": "true",
        "MST_GDRIVE_OAUTH_CLIENT_ID": "FAKE_OAUTH_ID",
        "MST_GDRIVE_OAUTH_CLIENT_SECRET": "FAKE_OAUTH_SECRET",
        "MST_GDRIVE_OAUTH_REFRESH_TOKEN": "FAKE_OAUTH_REFRESH",
        "MST_OAUTH_BOOTSTRAP_ACCEPTED": "false",
        "MST_MFX_SOURCE_MODE": m.MODE_STAGE_NATIVE,
        "MST_SOURCE_TF": tf,
        "MST_DNSE_READONLY_OWNER_ACCEPTED": "true",
        "MST_DNSE_SOURCE_RIGHTS_CONFIRMED": "true",
        "MST_DNSE_STORAGE_RIGHTS_CONFIRMED": "true",
        "MST_MFX_SOURCE_QUARANTINE_WRITE_ACCEPTED": "true",
        "MST_DNSE_API_KEY": "FAKE_MARKETDATA_KEY",
        "MST_DNSE_API_SECRET": "FAKE_MARKETDATA_SECRET",
        "MST_DNSE_SYMBOL": "FPT",
        "MST_DNSE_FROM_UNIX": "1794000000",
        "MST_DNSE_TO_UNIX": "1794172800",
        "GITHUB_RUN_ID": "43270010001",
        "GITHUB_RUN_ATTEMPT": "1",
    }
    source.update(changes)
    return source


def raw(stamps, volume=None):
    n = len(stamps)
    return {
        "t": stamps,
        "o": [100+i for i in range(n)],
        "h": [102+i for i in range(n)],
        "l": [99+i for i in range(n)],
        "c": [101+i for i in range(n)],
        "v": volume if volume is not None else [200+i for i in range(n)],
        "nextTime": 0,
    }


def old_archive(tf="M5", *, symbol="FPT"):
    from scripts.mst_mfx_native_timeframes import provider_resolution
    return {
        "schema": "mst.cloud.dnse_native_unpublished_candidate.v0.1",
        "project": "MST",
        "source": "DNSE_OFFICIAL_OPENAPI",
        "symbol": symbol,
        "resolution": provider_resolution("DNSE", tf),
        "source_native_tf": tf,
        "from_unix": 1793999900,
        "to_unix": 1794001000,
        "issuer_first_known_verified": False,
        "official_venue_closed_verified": False,
        "independent_publish_cas_verified": False,
        "eligible_for_signals": False,
        "raw_native": raw([1794000000, 1794000300], [200, 250]),
    }


class Drive:
    root = "FAKE_APP_ROOT_1234567890"
    chunks = "FAKE_APP_CHUNKS_1234567890"
    prior_id = "FAKE_PRIOR_M5_1234567890"
    created_id = "FAKE_CURRENT_M5_1234567890"
    LIST = "https://www.googleapis.com/drive/v3/files"
    UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"

    def __init__(self, *, old=None):
        self.old_body = None
        self.old_info = None
        if old is not None:
            self.old_body = json.dumps(
                old, sort_keys=True, separators=(",",":"), allow_nan=False
            ).encode()
            tf = old["source_native_tf"]
            self.old_info = {
                "id": self.prior_id,
                "name": "MST_UNPUBLISHED_DNSE_NATIVE_" + tf + "_43269999999_1.json",
                "mimeType": "application/json",
                "parents": [self.chunks],
                "trashed": False,
                "shared": False,
                "ownedByMe": True,
                "isAppAuthorized": True,
                "size": str(len(self.old_body)),
                "version": "7",
                "md5Checksum": hashlib.md5(self.old_body).hexdigest(),
                "appProperties": {
                    "mst_unpublished": "true",
                    "source_symbol": old["symbol"],
                    "source_native_tf": tf,
                    "source_run_id": "43269999999",
                    "source_sha256": hashlib.sha256(self.old_body).hexdigest(),
                },
            }
        self.current_body = None
        self.current_info = None
        self.census_override = None
        self.post_calls = 0
        self.old_reads = 0
        self.current_reads = 0
        self.metadata_drift = False

    def _brief(self, item):
        return {k: item[k] for k in
                ("id", "name", "mimeType", "parents", "trashed", "appProperties")}

    def get(self, url, *, params, timeout, **kwargs):
        if url == self.LIST:
            q = params.get("q", "")
            if "name contains 'MST_UNPUBLISHED_DNSE_'" in q:
                if self.census_override is not None:
                    return Response(self.census_override)
                return Response({"files":
                    [self._brief(self.old_info)] if self.old_info else []
                })
            name = q.split("name = '", 1)[-1].split("'", 1)[0]
            if name == m.DRIVE_ROOT:
                return Response({"files": [{
                    "id": self.root, "name": name, "mimeType": m.MIME_FOLDER,
                    "parents": ["FAKE_MYDRIVE_ROOT"], "trashed": False,
                }]})
            if name == "CHUNKS":
                return Response({"files": [{
                    "id": self.chunks, "name": name, "mimeType": m.MIME_FOLDER,
                    "parents": [self.root], "trashed": False,
                }]})
            return Response({"files": [
                self._brief(item) for item in (self.old_info, self.current_info)
                if item and item["name"] == name
            ]})
        if url == m.DRIVE_URL + self.prior_id and self.old_info:
            if params.get("alt") == "media":
                self.old_reads += 1
                return Response(content=self.old_body)
            if self.metadata_drift and self.old_reads > 0:
                return Response(dict(self.old_info, version="8"))
            return Response(self.old_info)
        if url == m.DRIVE_URL + self.created_id and self.current_info:
            if params.get("alt") == "media":
                self.current_reads += 1
                return Response(content=self.current_body)
            return Response(self.current_info)
        return Response(status=404)

    def post(self, url, *, params, data, headers, timeout):
        self.post_calls += 1
        assert url == self.UPLOAD
        boundary = headers["Content-Type"].split("boundary=", 1)[1].encode()
        parts = data.split(b"--" + boundary)
        metadata = json.loads(parts[1].split(b"\r\n\r\n",1)[1].strip())
        body = parts[2].split(b"\r\n\r\n",1)[1].removesuffix(b"\r\n")
        self.current_body = body
        self.current_info = {
            "id": self.created_id,
            "name": metadata["name"],
            "mimeType": "application/json",
            "parents": metadata["parents"],
            "trashed": False,
            "shared": False,
            "ownedByMe": True,
            "isAppAuthorized": True,
            "version": "1",
            "size": str(len(body)),
            "md5Checksum": hashlib.md5(body).hexdigest(),
            "appProperties": metadata["appProperties"],
        }
        return Response({"id": self.created_id}, status=201)


class NativeIntradayContinuity(unittest.TestCase):
    def newer(self):
        return raw([1794000300,1794000600], [255,300])

    def stage(self, drive, tf="M5", payload=None, **changes):
        return m.stage_unpublished_dnse_source(
            drive, env(tf, **changes), payload if payload is not None else self.newer()
        )

    def test_all_four_intraday_tfs_first_capture_and_unpublished(self):
        for tf in nd.NATIVE_TFS:
            with self.subTest(tf=tf):
                d = Drive()
                receipt = self.stage(d, tf)
                self.assertFalse(receipt["source_delta_linked_to_prior_private_d1"])
                self.assertFalse(receipt["source_delta_linked_to_prior_private_native_tf"])
                self.assertEqual(d.post_calls,1)
                self.assertEqual(d.current_reads,2)
                self.assertEqual(json.loads(d.current_body)["source_native_tf"],tf)
                self.assertFalse(json.loads(d.current_body)["eligible_for_signals"])

    def test_prior_link_retains_added_revised_and_exited_native_rows(self):
        d = Drive(old=old_archive())
        receipt = self.stage(d)
        self.assertTrue(receipt["source_delta_linked_to_prior_private_native_tf"])
        self.assertFalse(receipt["source_delta_linked_to_prior_private_d1"])
        self.assertEqual(receipt["source_delta_added_rows"],1)
        self.assertEqual(receipt["source_delta_revised_rows"],1)
        self.assertEqual(receipt["source_delta_window_exited_not_deleted"],1)
        self.assertEqual(d.old_reads,2)
        self.assertEqual(d.current_reads,2)
        self.assertEqual(d.post_calls,1)
        archive = json.loads(d.current_body)
        link = archive["prior_source_incremental_delta"]
        delta = link["delta"]
        self.assertEqual(delta["source_native_tf"],"M5")
        self.assertEqual(delta["revised"][0]["before"]["v"],250)
        self.assertEqual(delta["revised"][0]["after"]["v"],255)
        self.assertEqual(delta["window_exited_not_deleted"][0]["v"],200)
        self.assertEqual(delta["added"][0]["v"],300)
        self.assertFalse(link["eligible_for_signals"])
        self.assertFalse(delta["independent_signed_atomic_cas"])

    def test_corrupt_shared_tampered_and_changed_version_denied_preupload(self):
        for kind in ("shared","owner","sha","version","symbol","mime"):
            d = Drive(old=old_archive())
            if kind=="shared":d.old_info["shared"]=True
            if kind=="owner":d.old_info["ownedByMe"]=False
            if kind=="sha":d.old_info["appProperties"]["source_sha256"]="0"*64
            if kind=="version":d.metadata_drift=True
            if kind=="symbol":d.old_info["appProperties"]["source_symbol"]="NOT_A_STOCK"
            if kind=="mime":d.old_info["mimeType"]="text/plain"
            with self.subTest(kind=kind), self.assertRaises(m.CloudGateDenied):
                self.stage(d)
            self.assertEqual(d.post_calls,0)

    def test_missing_overlap_or_unread_page_never_creates_new_object(self):
        d=Drive(old=old_archive())
        nonoverlap=raw([1794001200,1794001500])
        with self.assertRaisesRegex(m.CloudGateDenied,"NO_OVERLAP"):
            self.stage(d,payload=nonoverlap)
        self.assertEqual(d.post_calls,0)
        broken=old_archive()
        broken["raw_native"]["nextTime"]=1794001000
        d=Drive(old=broken)
        with self.assertRaises(m.CloudGateDenied):
            self.stage(d)
        self.assertEqual(d.post_calls,0)

    def test_self_run_unlabeled_ambiguous_and_incomplete_census_denied(self):
        for kind in ("self","unlabeled","unknown","duplicate","incomplete","pages"):
            d=Drive(old=old_archive())
            if kind=="self":
                d.old_info["name"] = d.old_info["name"].replace(
                    "43269999999","43270010001")
                d.old_info["appProperties"]["source_run_id"]="43270010001"
            if kind=="unlabeled":
                del d.old_info["appProperties"]["source_native_tf"]
            if kind=="unknown":
                d.old_info["name"]="MST_UNPUBLISHED_DNSE_UNKNOWN_43269999999_1.json"
            if kind=="duplicate":
                d.census_override={"files":[d._brief(d.old_info)]*2}
            if kind=="incomplete":
                d.census_override={
                    "files":[d._brief(d.old_info)],"incompleteSearch":True}
            if kind=="pages":
                d.census_override={
                    "files":[d._brief(d.old_info)],"nextPageToken":"repeat"}
            with self.subTest(kind=kind),self.assertRaises(m.CloudGateDenied):
                self.stage(d)
            self.assertEqual(d.post_calls,0)

    def test_other_tf_and_other_symbol_cannot_be_reused(self):
        for kind in ("tf","symbol"):
            d=Drive(old=old_archive())
            if kind=="tf":
                d.old_info["name"] = d.old_info["name"].replace("NATIVE_M5","NATIVE_M15")
                d.old_info["appProperties"]["source_native_tf"]="M15"
            else:
                d.old_info["appProperties"]["source_symbol"]="HPG"
            receipt=self.stage(d)
            self.assertFalse(receipt["source_delta_linked_to_prior_private_native_tf"])
            self.assertEqual(d.old_reads,0)
            self.assertEqual(d.post_calls,1)

    def test_no_unapproved_or_unbounded_or_h4_stage(self):
        for updates in (
            {"GITHUB_REF":"refs/heads/feature"},
            {"GITHUB_RUN_ATTEMPT":"2"},
            {"MST_DNSE_STORAGE_RIGHTS_CONFIRMED":"false"},
            {"MST_DNSE_SOURCE_RIGHTS_CONFIRMED":"false"},
            {"MST_SOURCE_TF":"H4"},
        ):
            d=Drive(old=old_archive())
            with self.subTest(updates=updates),self.assertRaises(m.CloudGateDenied):
                m.stage_unpublished_dnse_source(d,env(**updates),self.newer())
            self.assertEqual(d.post_calls,0)

    def test_native_delta_is_deterministic_and_price_revisions_preserved(self):
        prior={
            "from_unix":1793999900,"to_unix":1794001000,
            "raw_native":old_archive()["raw_native"],
        }
        current={
            "from_unix":1794000000,"to_unix":1794172800,
            "raw_native":self.newer(),
        }
        one=nd.plan_intraday_delta(prior,current,tf="M5",symbol="FPT")
        two=nd.plan_intraday_delta(prior,current,tf="M5",symbol="FPT")
        self.assertEqual(one,two)
        self.assertEqual(len(one["plan_sha256"]),64)
        self.assertEqual(one["unchanged_overlap"],0)
        self.assertFalse(one["signal_eligible"])
