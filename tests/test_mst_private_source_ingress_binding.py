"""§193 all GET-to-stage evidence is fabricated; no live market-data calls."""
from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts import mst_mfx_style_appowned_pipeline as cloud
from scripts import mst_ssi_native_stage as ssi_stage
from scripts.mst_private_source_ingress_binding import (
    SourceBindingDenied, make_source_binding, binding_sha256,
    verify_source_binding, verify_archived_source_binding,
)
from test_mst_mfx_style_appowned_pipeline import (
    FakeQuarantineDrive, DnseNative, stage_owner_env,
)
from test_mst_ssi_native_stage import (
    Drive as SsiDrive, env as ssi_env, source_rows,
)


class InProcessSourceIngressBinding(unittest.TestCase):
    def dnse(self):
        env=stage_owner_env(GITHUB_ACTIONS="true")
        return env,DnseNative().payload()

    def ssi(self, tf="M5"):
        env=ssi_env(tf,GITHUB_ACTIONS="true")
        return env,source_rows(tf)

    def test_dnse_live_workflow_requires_same_run_observation(self):
        env,payload=self.dnse()
        drive=FakeQuarantineDrive()
        with self.assertRaisesRegex(
            cloud.CloudGateDenied,"GITHUB_INGRESS_BINDING_REQUIRED",
        ):
            cloud.stage_unpublished_dnse_source(drive,env,payload)
        self.assertEqual(drive.post_calls,0)

        expected=make_source_binding("DNSE",env,payload)
        result=cloud.stage_unpublished_dnse_source(
            drive,env,payload,ingress_binding=expected,
        )
        saved=json.loads(drive.media)
        self.assertEqual(saved["source_ingress_binding"],expected)
        self.assertEqual(
            drive.file_info["appProperties"]["source_ingress_binding_sha256"],
            binding_sha256(expected),
        )
        self.assertTrue(verify_archived_source_binding(
            saved,drive.file_info["appProperties"]))
        self.assertTrue(result["unpublished_private_source_document_stored"])
        self.assertEqual(drive.post_calls,1)
        self.assertEqual(drive.media_reads,2)
        self.assertFalse(saved["eligible_for_signals"])
        self.assertFalse(expected["issuer_attested"])
        self.assertFalse(expected["cache_publisher_authorized"])

    def test_ssi_live_workflow_requires_same_run_observation(self):
        env,rows=self.ssi()
        drive=SsiDrive()
        with self.assertRaisesRegex(
            cloud.CloudGateDenied,"GITHUB_INGRESS_BINDING_REQUIRED",
        ):
            ssi_stage.stage_ssi_native_source(drive,env,rows)
        self.assertEqual(drive.post_count,0)
        binding=make_source_binding("SSI",env,list(reversed(rows)))
        result=ssi_stage.stage_ssi_native_source(
            drive,env,rows,ingress_binding=binding,
        )
        saved=json.loads(drive.new_body)
        self.assertEqual(saved["source_ingress_binding"],binding)
        self.assertTrue(verify_archived_source_binding(
            saved,drive.new_info["appProperties"]))
        self.assertEqual(
            drive.new_info["appProperties"]["source_ingress_binding_sha256"],
            binding_sha256(binding),
        )
        self.assertTrue(result["unpublished_private_source_document_stored"])
        self.assertEqual(drive.post_count,1)
        self.assertEqual(drive.new_media_count,2)
        self.assertFalse(saved["eligible_for_signals"])

    def test_wrong_source_symbol_tf_run_window_row_fails_before_post(self):
        env,payload=self.dnse()
        baseline=make_source_binding("DNSE",env,payload)
        bad=[]
        for key,value in [
            ("symbol","DCM"),("native_tf","H1"),
            ("github_run_id","43270010002"),
            ("github_run_attempt","2"),("source","SSI_FASTCONNECT_V3_MARKET_DATA"),
            ("source_endpoint","https://invalid.example"),
            ("row_count",1),
            ("requested_window",{"from_unix":1794000001,"to_unix":1794500000}),
            ("issuer_attested",True),("cache_publisher_authorized",True),
        ]:
            r=dict(baseline);r[key]=value;bad.append(r)
        bad.append({**baseline,"unexpected":"UNTRUSTED"})
        payload_changed=deepcopy(payload)
        payload_changed["v"][1]+=100
        bad.append((baseline,payload_changed))
        for item in bad:
            with self.subTest(case=str(item)[:60]):
                receipt,raw=(item if type(item) is tuple else (item,payload))
                drive=FakeQuarantineDrive()
                with self.assertRaisesRegex(
                    cloud.CloudGateDenied,"GITHUB_INGRESS_BINDING_INVALID",
                ):
                    cloud.stage_unpublished_dnse_source(
                        drive,env,raw,ingress_binding=receipt,
                    )
                self.assertEqual(drive.post_calls,0)

    def test_ssi_changed_native_data_and_request_window_denied(self):
        env,rows=self.ssi()
        binding=make_source_binding("SSI",env,rows)
        altered=deepcopy(rows)
        altered[0]["close"]="100.8"
        drive=SsiDrive()
        with self.assertRaisesRegex(
            cloud.CloudGateDenied,"INGRESS_BINDING_INVALID",
        ):
            ssi_stage.stage_ssi_native_source(
                drive,env,altered,ingress_binding=binding,
            )
        self.assertEqual(drive.post_count,0)
        wrong_window=dict(env,MST_SSI_TO_DATE="2026-11-13")
        with self.assertRaisesRegex(
            cloud.CloudGateDenied,"INGRESS_BINDING_INVALID",
        ):
            ssi_stage.stage_ssi_native_source(
                drive,wrong_window,rows,ingress_binding=binding,
            )
        self.assertEqual(drive.post_count,0)

    def test_archive_binding_tamper_denied_even_with_valid_body_hash(self):
        env,raw=self.dnse()
        drive=FakeQuarantineDrive()
        binding=make_source_binding("DNSE",env,raw)
        cloud.stage_unpublished_dnse_source(
            drive,env,raw,ingress_binding=binding,
        )
        drive.file_info["appProperties"]["source_ingress_binding_sha256"]="0"*64
        with self.assertRaisesRegex(
            cloud.CloudGateDenied,"MST_MFX_STAGED_SOURCE_BINDING_INVALID",
        ):
            cloud._quarantine_metadata(
                drive,drive.FILE_ID,drive.file_info["parents"][0],
                drive.file_info["name"],drive.media,
            )

    def test_legacy_candidate_is_unpublished_not_source_bound(self):
        env=stage_owner_env()
        drive=FakeQuarantineDrive()
        cloud.stage_unpublished_dnse_source(drive,env,DnseNative().payload())
        archive=json.loads(drive.media)
        self.assertNotIn("source_ingress_binding",archive)
        self.assertFalse(verify_archived_source_binding(
            archive,drive.file_info["appProperties"]))
        self.assertFalse(archive["eligible_for_signals"])

    def test_binding_rejects_cross_provider_run_and_malformed_date(self):
        e,raw=self.dnse()
        with self.assertRaises(SourceBindingDenied):
            make_source_binding("SSI",e,raw)
        with self.assertRaises(SourceBindingDenied):
            make_source_binding("DNSE",dict(e,GITHUB_RUN_ATTEMPT="2"),raw)
        with self.assertRaises(SourceBindingDenied):
            make_source_binding("DNSE",dict(e,GITHUB_REF="refs/heads/draft"),raw)
        es,rows=self.ssi()
        for invalid in ("2026-11-31","2026/11/13","2026-11-13T00:00:00"):
            with self.subTest(invalid=invalid),self.assertRaises(
                SourceBindingDenied
            ):
                make_source_binding(
                    "SSI",dict(es,MST_SSI_FROM_DATE=invalid),rows
                )

    def test_receipt_body_hash_is_own_proof_not_vendor_signature(self):
        es,raw=self.dnse()
        r=make_source_binding("DNSE",es,raw)
        self.assertEqual(verify_source_binding("DNSE",es,raw,r),binding_sha256(r))
        self.assertEqual(r["scope"],"IN_PROCESS_REQUEST_TO_PRIVATE_STAGE_UNATTESTED")
        self.assertFalse(r["issuer_attested"])
        self.assertFalse(r["cache_publisher_authorized"])
        for change in ({"row_count":-1},{"schema":"vendor.signed"},{},):
            with self.subTest(change=change):
                tampered=dict(r,**change)
                if not change:
                    tampered.pop("scope")
                with self.assertRaises(SourceBindingDenied):
                    verify_source_binding("DNSE",es,raw,tampered)


if __name__=="__main__":
    unittest.main()
