"""§194: strict new-format source candidate/Drive metadata identity checks.

All bytes, OAuth responses, market prices, history and runs are fictional.
No vendor request and no persistent app-owned Google Drive write.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import md5, sha256
import json
import unittest

from scripts import mst_mfx_style_appowned_pipeline as cloud
from scripts import mst_ssi_native_stage as ssi_stage
from scripts.mst_native_source_fingerprint import native_canonical_sha256
from scripts.mst_private_candidate_identity import (
    CandidateIdentityDenied, verify_new_candidate_identity,
)
from test_mst_mfx_style_appowned_pipeline import (
    FakeQuarantineDrive, DnseNative, stage_owner_env,
)
from test_mst_ssi_native_stage import (
    Drive as SsiDrive, env as ssi_env, source_rows,
)


def reseal_native(drive, *, provider, mutate):
    """Simulate self-consistent checksum tamper; no cryptographic issuer proof."""
    if provider=="DNSE":
        body=drive.media
        info=drive.file_info
    else:
        body=drive.new_body
        info=drive.new_info
    data=json.loads(body)
    mutate(data,info)
    if "native_canonical_sha256" in data:
        digest=native_canonical_sha256(
            provider,data["symbol"],data["source_native_tf"],data["raw_native"],
        )
        data["native_canonical_sha256"]=digest
        info["appProperties"]["native_canonical_sha256"]=digest
    updated=json.dumps(
        data,sort_keys=True,separators=(",",":"),allow_nan=False,
    ).encode()
    info["size"]=str(len(updated))
    info["md5Checksum"]=md5(updated).hexdigest()
    info["appProperties"]["source_sha256"]=sha256(updated).hexdigest()
    if provider=="DNSE":
        drive.media=updated
    else:
        drive.new_body=updated
    return data,info,updated


class StrictCandidateIdentity(unittest.TestCase):
    def dnse(self):
        d=FakeQuarantineDrive()
        cloud.stage_unpublished_dnse_source(d,stage_owner_env(),DnseNative().payload())
        return d

    def ssi(self,tf="M5"):
        d=SsiDrive()
        ssi_stage.stage_ssi_native_source(d,ssi_env(tf),source_rows(tf))
        return d

    def test_valid_direct_stage_has_exact_identity_for_dnse_and_ssi(self):
        for kind in ("DNSE","SSI"):
            with self.subTest(provider=kind):
                d=self.dnse() if kind=="DNSE" else self.ssi()
                info=d.file_info if kind=="DNSE" else d.new_info
                body=d.media if kind=="DNSE" else d.new_body
                data=json.loads(body)
                self.assertTrue(verify_new_candidate_identity(data,info))
                self.assertFalse(data["eligible_for_signals"])
                self.assertFalse(data["independent_publish_cas_verified"])

    def test_drive_properties_drift_denied_with_correct_full_body_checksum(self):
        cases=(
            ("source_symbol","DCM"),
            ("source_native_tf","H1"),
            ("source_run_id","43270010002"),
            ("schema","not_a_supported_candidate"),
            ("mst_unpublished","false"),
        )
        for kind in ("DNSE","SSI"):
            for field,value in cases:
                with self.subTest(provider=kind,field=field):
                    d=self.dnse() if kind=="DNSE" else self.ssi()
                    info=d.file_info if kind=="DNSE" else d.new_info
                    body=d.media if kind=="DNSE" else d.new_body
                    info["appProperties"][field]=value
                    with self.assertRaisesRegex(
                        cloud.CloudGateDenied,
                        "MST_MFX_STAGED_(CANDIDATE_IDENTITY|SOURCE_METADATA_INTEGRITY)_INVALID",
                    ):
                        cloud._quarantine_metadata(
                            d,info["id"],info["parents"][0],info["name"],body,
                        )

    def test_file_name_not_forgivable_by_recomputing_sha(self):
        for kind in ("DNSE","SSI"):
            d=self.dnse() if kind=="DNSE" else self.ssi()
            info=d.file_info if kind=="DNSE" else d.new_info
            body=d.media if kind=="DNSE" else d.new_body
            info["name"]=info["name"].replace("43270010001","43270010002")
            with self.subTest(provider=kind),self.assertRaisesRegex(
                cloud.CloudGateDenied,"MST_MFX_STAGED_CANDIDATE_IDENTITY_INVALID",
            ):
                cloud._quarantine_metadata(
                    d,info["id"],info["parents"][0],info["name"],body,
                )

    def test_fake_verified_vendor_claim_denied_even_after_full_rehash(self):
        for kind in ("DNSE","SSI"):
            d=self.dnse() if kind=="DNSE" else self.ssi()
            for field in (
                "issuer_first_known_verified",
                "official_venue_closed_verified",
                "eligible_for_signals",
                "independent_publish_cas_verified",
            ):
                with self.subTest(provider=kind,claim=field):
                    fresh=self.dnse() if kind=="DNSE" else self.ssi()
                    data,info,body=reseal_native(
                        fresh,provider=kind,
                        mutate=lambda payload,meta:payload.__setitem__(field,True),
                    )
                    self.assertFalse(data.get("source_ingress_binding",{}).get(
                        "issuer_attested",False))
                    with self.assertRaisesRegex(
                        cloud.CloudGateDenied,"MST_MFX_STAGED_CANDIDATE_IDENTITY_INVALID",
                    ):
                        cloud._quarantine_metadata(
                            fresh,info["id"],info["parents"][0],
                            info["name"],body,
                        )

    def test_native_ohlc_corruption_denied_even_with_recomputed_both_sha(self):
        for kind in ("DNSE","SSI"):
            with self.subTest(provider=kind):
                d=self.dnse() if kind=="DNSE" else self.ssi()
                def mutate(data,info):
                    if kind=="DNSE":
                        data["raw_native"]["l"][0]=data["raw_native"]["h"][0]+9
                    else:
                        data["raw_native"][0]["low"]="999.99"
                data,info,body=reseal_native(d,provider=kind,mutate=mutate)
                self.assertFalse(data["eligible_for_signals"])
                with self.assertRaisesRegex(
                    cloud.CloudGateDenied,"MST_MFX_STAGED_CANDIDATE_IDENTITY_INVALID",
                ):
                    cloud._quarantine_metadata(
                        d,info["id"],info["parents"][0],info["name"],body,
                    )

    def test_new_archive_missing_required_or_injected_unknown_field_denied(self):
        for kind in ("DNSE","SSI"):
            for extra in ("injected", "missing"):
                with self.subTest(provider=kind,extra=extra):
                    d=self.dnse() if kind=="DNSE" else self.ssi()
                    def mutate(data,info):
                        if extra=="injected":
                            data["token_exfiltration"]="FAKE_NOT_A_SECRET"
                        else:
                            data.pop("eligible_for_signals")
                    data,info,body=reseal_native(d,provider=kind,mutate=mutate)
                    with self.assertRaisesRegex(
                        cloud.CloudGateDenied,"MST_MFX_STAGED_CANDIDATE_IDENTITY_INVALID",
                    ):
                        cloud._quarantine_metadata(
                            d,info["id"],info["parents"][0],info["name"],body,
                        )

    def test_historical_legacy_source_without_new_digest_remains_nonactionable(self):
        d=self.dnse()
        source=json.loads(d.media)
        source.pop("native_canonical_sha256")
        d.file_info["appProperties"].pop("native_canonical_sha256")
        self.assertFalse(verify_new_candidate_identity(source,d.file_info))
        self.assertFalse(source["eligible_for_signals"])
        source["source_ingress_binding"]={"schema":"fake"}
        with self.assertRaises(CandidateIdentityDenied):
            verify_new_candidate_identity(source,d.file_info)


if __name__=="__main__":
    unittest.main()
