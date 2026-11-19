"""MST §242 fictional HTTP regression for unpublished MANIFESTS; zero network."""
from __future__ import annotations

from dataclasses import replace
from hashlib import md5, sha256
import json
import unittest

from scripts import mst_private_unpublished_manifest242 as m
from scripts.mst_private_chunk_readback240 import PrivateUnpublishedChunk
from test_mst_private_chunk_readback240 import (
    FakeSession, Reply, env as source_env, PARENT, FILE, RUN,
)

ROOT = "MSTOAuthRoot0001"
MANIFESTS = "MSTAppOwnedManifestFolder0001"
MANIFEST_FILE = "MSTPrivateManifestFile000001"


def env(**updates):
    e = source_env()
    e.update({
        "MST_PRIVATE_MANIFEST_WRITE_ACCEPTED": "true",
        "MST_PRIVATE_CHUNKS_FOLDER_ID": PARENT,
        "MST_PRIVATE_MANIFESTS_FOLDER_ID": MANIFESTS,
    })
    e.update(updates)
    return e


def chunk(fake):
    return PrivateUnpublishedChunk(
        file_id=FILE, sha256=fake.digest,
        provider="DNSE", symbol="FPT", native_tf="D1",
        bytes_verified=len(fake.raw),
    )


class FakeManifestDrive(FakeSession):
    def __init__(self):
        super().__init__()
        self.uploaded = True  # an existing, already verified unpublished CHUNK
        self.manifest_uploaded = False
        self.manifest_raw = None
        self.manifest_name = None
        self.manifest_props = None
        self.manifest_media_reads = 0
        self.manifest_metadata_reads = 0
        self.manifest_tamper_second = False
        self.manifest_shared = False
        self.manifest_wrong_md5 = False
        self.manifest_version_drift = False
        self.manifest_existing = False
        self.manifest_duplicate_after = False
        self.manifest_wrong_parent = False
        self.root_shared = False
        self.manifests_shared = False
        self.fail_manifest_post = False

    def get(self, url, *, params, timeout, allow_redirects):
        if url == m.FILES + "/" + ROOT:
            self.calls.append(("GET", url, params))
            return Reply({
                "id": ROOT, "name": "MST_OAUTH_CACHE_V1",
                "mimeType": m.FOLDER_MIME, "parents": ["PrivateMyDriveRoot0001"],
                "trashed": False, "shared": self.root_shared,
                "ownedByMe": True, "isAppAuthorized": True,
            })
        if url == m.FILES + "/" + MANIFESTS:
            self.calls.append(("GET", url, params))
            return Reply({
                "id": MANIFESTS, "name": "MANIFESTS",
                "mimeType": m.FOLDER_MIME,
                "parents": ["AnotherParent00001" if self.manifest_wrong_parent else ROOT],
                "trashed": False, "shared": self.manifests_shared,
                "ownedByMe": True, "isAppAuthorized": True,
            })
        if url == m.FILES and "'" + MANIFESTS + "' in parents" in params.get("q", ""):
            self.calls.append(("GET", url, params))
            entries = []
            if self.manifest_uploaded or self.manifest_existing:
                entries = [{
                    "id": MANIFEST_FILE,
                    "name": self.manifest_name or params["q"].split("name = '", 1)[1].split("'", 1)[0],
                    "mimeType": m.MIME,
                    "parents": [MANIFESTS], "trashed": False,
                }]
                if self.manifest_duplicate_after:
                    entries = [entries[0], dict(entries[0])]
            return Reply({"files": entries, "incompleteSearch": False})
        if url == m.FILES + "/" + MANIFEST_FILE:
            self.calls.append(("GET", url, params))
            if params == {"alt": "media"}:
                self.manifest_media_reads += 1
                raw = (b"tampered manifest payload" if self.manifest_tamper_second
                       and self.manifest_media_reads == 2 else self.manifest_raw)
                return Reply(media=raw)
            self.manifest_metadata_reads += 1
            return Reply({
                "id": MANIFEST_FILE, "name": self.manifest_name,
                "mimeType": m.MIME, "parents": [MANIFESTS], "trashed": False,
                "shared": self.manifest_shared,
                "ownedByMe": True, "isAppAuthorized": True,
                "size": str(len(self.manifest_raw)),
                "md5Checksum": (
                    "0"*32 if self.manifest_wrong_md5
                    else md5(self.manifest_raw).hexdigest()
                ),
                "version": (
                    "2" if self.manifest_version_drift
                    and self.manifest_metadata_reads >= 2 else "1"
                ),
                "appProperties": self.manifest_props,
            })
        return super().get(url, params=params, timeout=timeout,
                           allow_redirects=allow_redirects)

    def post(self, url, *, params, headers, data, timeout, allow_redirects):
        assert url == m.UPLOAD and params["uploadType"] == "multipart"
        assert headers["Content-Type"].startswith(
            "multipart/related; boundary=mstmanifest"
        )
        assert not allow_redirects and timeout == 35
        self.calls.append(("POST", url, params))
        if self.fail_manifest_post:
            return Reply({"error":"SECRET_DO_NOT_ECHO"}, status=403)
        self.manifest_raw = data.split(
            b"Content-Type: application/json\r\n\r\n", 1
        )[1].rsplit(b"\r\n--", 1)[0]
        meta = json.loads(data.split(
            b"Content-Type: application/json; charset=UTF-8\r\n\r\n", 1
        )[1].split(b"\r\n--", 1)[0])
        self.manifest_name = meta["name"]
        self.manifest_props = meta["appProperties"]
        assert meta["parents"] == [MANIFESTS]
        assert meta["mimeType"] == m.MIME
        self.manifest_uploaded = True
        return Reply({
            "id": MANIFEST_FILE, "name": self.manifest_name,
            "mimeType": m.MIME, "parents": [MANIFESTS], "trashed": False,
        }, status=200)


def stage(fake=None, *, own=None, src=None):
    instance = FakeManifestDrive() if fake is None else fake
    receipt = chunk(instance) if src is None else src
    result = m.stage_unpublished_manifest(
        instance, env() if own is None else own,
        PARENT, MANIFESTS, receipt,
    )
    return result, instance


class PrivateUnpublishedManifest242(unittest.TestCase):
    def test_full_custody_roundtrip_remains_unpublished(self):
        outcome, drive = stage()
        self.assertEqual(drive.manifest_media_reads, 2)
        self.assertEqual(drive.manifest_metadata_reads, 3)
        self.assertEqual(drive.media_reads, 3)
        self.assertEqual(drive.metadata_reads, 3)
        payload = json.loads(drive.manifest_raw)
        self.assertEqual(payload["source_chunk_sha256"], drive.digest)
        self.assertEqual(payload["source_chunk_file_id"], FILE)
        self.assertEqual(payload["source_run_id"], RUN)
        self.assertEqual(payload["status"], "UNPUBLISHED")
        self.assertIs(payload["cache_head_published"], False)
        self.assertIs(payload["trading_eligible"], False)
        self.assertNotIn("raw_native", payload)
        self.assertNotIn("open", payload)
        self.assertEqual(outcome.manifest_sha256,
                         sha256(drive.manifest_raw).hexdigest())
        self.assertEqual(outcome.verified_readback_count, 2)
        self.assertFalse(outcome.independent_signed_cas_proven)
        receipt = json.dumps(outcome.public_receipt())
        for private in (FILE, MANIFEST_FILE, RUN, drive.digest, PARENT,
                        MANIFESTS, "FICTIONAL_ONLY"):
            self.assertNotIn(private, receipt)

    def test_strict_rights_all_gated_before_http(self):
        for key,value in (
            ("GITHUB_REPOSITORY", "attacker/MST"),
            ("GITHUB_REF", "refs/heads/feature"),
            ("GITHUB_EVENT_NAME", "push"),
            ("GITHUB_RUN_ATTEMPT", "2"),
            ("GITHUB_WORKFLOW_REF", "arbitrary"),
            ("MST_PRIVATE_MANIFEST_WRITE_ACCEPTED", "false"),
            ("MST_PRIVATE_CHUNKS_WRITE_ACCEPTED", "false"),
            ("MST_SOURCE_RETENTION_RIGHTS_CONFIRMED", "false"),
            ("MST_DNSE_SOURCE_RIGHTS_CONFIRMED", "false"),
            ("MST_SOURCE_PROVIDER", "SSI"),
            ("MST_SOURCE_SYMBOL", "HPG"),
            ("MST_SOURCE_TF", "H4"),
            ("GITHUB_RUN_ID", "garbage"),
        ):
            drive = FakeManifestDrive()
            with self.subTest(key=key), self.assertRaises(m.ManifestDenied):
                stage(drive, own=env(**{key:value}))
            self.assertEqual(drive.calls, [])

    def test_unauthorized_folders_or_parent_fail_prewrite(self):
        for flag in ("root_shared", "manifests_shared",
                     "manifest_wrong_parent"):
            drive = FakeManifestDrive()
            setattr(drive, flag, True)
            with self.subTest(flag=flag), self.assertRaisesRegex(
                m.ManifestDenied, "PRIVATE_FOLDER_CUSTODY_DENIED"
            ):
                stage(drive)
            self.assertFalse(drive.manifest_uploaded)

    def test_chunk_media_bitflip_rejected_without_manifest_write(self):
        drive = FakeManifestDrive()
        drive.raw = b"tampered source bytes"
        with self.assertRaisesRegex(m.ManifestDenied,"CHUNK_MEDIA_REHASH_DENIED"):
            stage(drive)
        self.assertFalse(drive.manifest_uploaded)

    def test_chunk_second_read_corruption_rejected(self):
        drive = FakeManifestDrive()
        drive.tamper_second = True
        with self.assertRaises(m.ChunkDenied):
            stage(drive)
        self.assertFalse(drive.manifest_uploaded)

    def test_stale_chunk_source_identity_denied(self):
        drive = FakeManifestDrive()
        forged = replace(chunk(drive), sha256="b"*64)
        with self.assertRaisesRegex(m.ChunkDenied, "CENSUS_SCOPE_INVALID"):
            stage(drive, src=forged)
        self.assertFalse(drive.manifest_uploaded)

    def test_manifest_second_media_read_tamper_blocks_receipt(self):
        drive = FakeManifestDrive()
        drive.manifest_tamper_second = True
        with self.assertRaisesRegex(m.ChunkDenied, "MEDIA_READBACK_MISMATCH"):
            stage(drive)
        self.assertTrue(drive.manifest_uploaded)

    def test_manifest_md5_drift_denied(self):
        drive = FakeManifestDrive()
        drive.manifest_wrong_md5 = True
        with self.assertRaisesRegex(m.ManifestDenied,"METADATA_CUSTODY_DENIED"):
            stage(drive)
        self.assertTrue(drive.manifest_uploaded)

    def test_manifest_version_drift_denied(self):
        drive = FakeManifestDrive()
        drive.manifest_version_drift = True
        with self.assertRaisesRegex(m.ManifestDenied,"VERSION_MUTATED"):
            stage(drive)
        self.assertTrue(drive.manifest_uploaded)

    def test_shared_manifest_rejected(self):
        drive = FakeManifestDrive()
        drive.manifest_shared = True
        with self.assertRaisesRegex(m.ManifestDenied,"METADATA_CUSTODY_DENIED"):
            stage(drive)

    def test_existing_manifest_name_denied(self):
        drive = FakeManifestDrive()
        drive.manifest_existing = True
        with self.assertRaises(m.ManifestDenied):
            stage(drive)
        self.assertFalse(drive.manifest_uploaded)

    def test_duplicate_after_upload_denied(self):
        drive = FakeManifestDrive()
        drive.manifest_duplicate_after = True
        with self.assertRaises(m.ChunkDenied):
            stage(drive)
        self.assertTrue(drive.manifest_uploaded)

    def test_failed_upload_does_not_leak_google_response(self):
        drive = FakeManifestDrive()
        drive.fail_manifest_post = True
        with self.assertRaisesRegex(m.ChunkDenied,"^MST_240_DRIVE_HTTP_DENIED$"):
            stage(drive)
        self.assertFalse(drive.manifest_uploaded)

    def test_dataclass_false_public_authority_is_enforced(self):
        result,_ = stage()
        for field in (
            "manifest_published", "source_finality_attested",
            "rights_independently_attested", "independent_signed_cas_proven",
            "eligible_for_signals_or_trades"
        ):
            with self.subTest(field=field),self.assertRaises(m.ManifestDenied):
                replace(result,**{field:True})

    def test_do_not_mutate_real_cloud_or_cas(self):
        import inspect
        body = inspect.getsource(m)
        for forbidden in ("session.delete(", "session.patch(",
                          "git push", "private_key=", "MST_SEND_ORDER"):
            self.assertNotIn(forbidden, body)


if __name__ == "__main__":
    unittest.main()
