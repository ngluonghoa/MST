"""MST §243 SSI manual CHUNK_ONLY vs separately gated UNPUBLISHED MANIFEST."""
from pathlib import Path
import json
import unittest
from unittest.mock import patch

from scripts import mst_ssi_cloud_private_chunk241 as m
from scripts.mst_private_unpublished_manifest242 import ManifestDenied
from test_mst_ssi_cloud_private_chunk241 import (
    FakeDiscovery, Response, ROOT, CHUNKS, owner_env, report, rows,
    saved_candidate,
)

MANIFESTS = "MSTAppOwnedManifestFolder0001"


class FakeWithManifests(FakeDiscovery):
    def __init__(self):
        super().__init__()
        self.manifests_shared = False
        self.manifests_wrong_parent = False
        self.manifests_missing = False

    def get(self, url, *, params, timeout, allow_redirects):
        if "name = 'MANIFESTS'" in params.get("q", ""):
            self.calls.append((url, params))
            return Response({
                "files": [] if self.manifests_missing else [{
                    "id": MANIFESTS, "name": "MANIFESTS",
                    "mimeType": m.FOLDER_MIME,
                    "parents": (["UnrelatedOwnerRoot0001"]
                                if self.manifests_wrong_parent else [ROOT]),
                    "trashed": False, "shared": self.manifests_shared,
                    "ownedByMe": True, "isAppAuthorized": True,
                }],
                "incompleteSearch": False,
                "nextPageToken": None,
            })
        return super().get(url, params=params, timeout=timeout,
                           allow_redirects=allow_redirects)


def gated(**changes):
    return owner_env(
        MST_MANIFEST_STAGE_MODE="UNPUBLISHED_MANIFEST",
        MST_PRIVATE_MANIFEST_WRITE_ACCEPTED="true",
        **changes,
    )


class SsiManifestManual243(unittest.TestCase):
    def test_opt_in_source_chunk_then_manifest_private_only(self):
        source, cloud = object(), FakeWithManifests()
        captured = []
        def fake_chunk(session, forwarded, folder, raw):
            self.assertIs(session, cloud)
            self.assertEqual(folder, CHUNKS)
            self.assertEqual(json.loads(raw)["raw_native"], rows())
            captured.append(("chunk", raw))
            return saved_candidate(raw)

        def fake_manifest(session, forwarded, chunks, manifests, receipt):
            self.assertIs(session, cloud)
            self.assertEqual(chunks, CHUNKS)
            self.assertEqual(manifests, MANIFESTS)
            self.assertEqual(forwarded["MST_PRIVATE_MANIFESTS_FOLDER_ID"], MANIFESTS)
            self.assertEqual(forwarded["MST_PRIVATE_CHUNKS_FOLDER_ID"], CHUNKS)
            self.assertEqual(receipt.bytes_verified, len(captured[0][1]))
            self.assertIs(receipt.published_to_market_cache, False)
            captured.append(("manifest", receipt))
            return object()

        with patch.object(m,"_fetch_ssi_native_once",return_value=(report(), rows())) as read, \
             patch.object(m,"upload_private_unpublished_chunk", side_effect=fake_chunk) as write, \
             patch.object(m,"stage_unpublished_manifest", side_effect=fake_manifest) as manifest:
            result = m.run_private_ssi_stage(source, cloud, gated())
        self.assertEqual(len(cloud.calls), 4)  # 2 root reads + CHUNKS + MANIFESTS
        self.assertEqual([x[0] for x in captured], ["chunk","manifest"])
        read.assert_called_once()
        write.assert_called_once()
        manifest.assert_called_once()
        self.assertIs(result["unpublished_private_manifest_staged"], True)
        self.assertIs(result["market_cache_promoted"], False)
        self.assertIs(result["independent_signed_monotone_cas_verified"], False)
        self.assertIs(result["signals_or_trade_eligible"], False)
        public = json.dumps(result)
        for secret in (CHUNKS, MANIFESTS, ROOT, "fake-oauth-secret",
                       "fake-secret-only", '"open"'):
            self.assertNotIn(secret, public)

    def test_default_and_explicit_chunk_only_do_not_touch_manifest_folder(self):
        for mode in (None, "CHUNK_ONLY"):
            e=owner_env()
            if mode is not None:
                e["MST_MANIFEST_STAGE_MODE"]=mode
            cloud=FakeDiscovery()
            with patch.object(m, "_fetch_ssi_native_once",
                              return_value=(report(),rows())) as read, \
                 patch.object(m, "upload_private_unpublished_chunk",
                              side_effect=lambda _,__,___,raw:saved_candidate(raw)) as write, \
                 patch.object(m, "stage_unpublished_manifest") as manifest:
                rec=m.run_private_ssi_stage(object(), cloud, e)
            self.assertEqual(len(cloud.calls),2)
            read.assert_called_once()
            write.assert_called_once()
            manifest.assert_not_called()
            self.assertIs(rec["unpublished_private_manifest_staged"],False)

    def test_separate_manifest_permission_required_before_provider_and_drive(self):
        for wrong in ("", "false", "FALSE"):
            cloud=FakeWithManifests()
            with patch.object(m, "_fetch_ssi_native_once") as read, \
                 patch.object(m, "upload_private_unpublished_chunk") as write, \
                 self.assertRaisesRegex(
                     m.SsiStageDenied, "MANIFEST_OWNER_GATE_REQUIRED"
                 ):
                m.run_private_ssi_stage(
                    object(), cloud,
                    owner_env(MST_MANIFEST_STAGE_MODE="UNPUBLISHED_MANIFEST",
                              MST_PRIVATE_MANIFEST_WRITE_ACCEPTED=wrong),
                )
            self.assertEqual(cloud.calls,[])
            read.assert_not_called()
            write.assert_not_called()

    def test_invalid_manifest_mode_rejected_before_io(self):
        cloud=FakeWithManifests()
        with patch.object(m,"_fetch_ssi_native_once") as read, \
             self.assertRaisesRegex(m.SsiStageDenied,"INVALID_MANIFEST_MODE"):
            m.run_private_ssi_stage(
                object(),cloud,owner_env(MST_MANIFEST_STAGE_MODE="PUBLISH")
            )
        self.assertEqual(cloud.calls,[])
        read.assert_not_called()

    def test_manifest_folder_scope_fails_before_issuer_access(self):
        for field in ("manifests_shared", "manifests_wrong_parent",
                      "manifests_missing"):
            cloud=FakeWithManifests()
            setattr(cloud,field,True)
            with self.subTest(field=field),patch.object(
                m,"_fetch_ssi_native_once"
            ) as read,self.assertRaises(m.SsiStageDenied):
                m.run_private_ssi_stage(object(),cloud,gated())
            read.assert_not_called()

    def test_manifest_integrity_failure_keeps_source_unpublished(self):
        cloud=FakeWithManifests()
        issued = []
        with patch.object(m, "_fetch_ssi_native_once",
                          return_value=(report(),rows())), \
             patch.object(m, "upload_private_unpublished_chunk",
                          side_effect=lambda _,__,___,raw:
                          (issued.append(raw) or saved_candidate(raw))), \
             patch.object(m, "stage_unpublished_manifest",
                          side_effect=ManifestDenied("MST_242_MANIFEST_VERSION_MUTATED")) as stage:
            with self.assertRaisesRegex(ManifestDenied, "VERSION_MUTATED"):
                m.run_private_ssi_stage(object(),cloud,gated())
        self.assertEqual(len(issued),1)
        stage.assert_called_once()

    def test_manual_workflow_has_off_by_default_manifest_input_and_no_cron(self):
        yaml=(Path(__file__).resolve().parents[1] /
              ".github/workflows/mst-private-source-chunks-manual.yml").read_text()
        self.assertIn('default: "CHUNK_ONLY"', yaml)
        self.assertIn('UNPUBLISHED_MANIFEST', yaml)
        self.assertIn('MST_PRIVATE_MANIFEST_WRITE_ACCEPTED:', yaml)
        self.assertIn('MST_MANIFEST_STAGE_MODE:', yaml)
        self.assertIn('workflow_dispatch:', yaml)
        self.assertNotIn("schedule:", yaml)
        self.assertNotIn("pull_request_target:", yaml)
        self.assertNotIn("push:", yaml)


if __name__ == "__main__":
    unittest.main()
