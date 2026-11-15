"""§192: fabricated source-native payloads; never contact brokers or vendors."""
from __future__ import annotations

import copy
import json
import unittest

from scripts.mst_native_source_fingerprint import (
    native_canonical_sha256, NativeFingerprintDenied,
)
from scripts import mst_mfx_style_appowned_pipeline as cloud
from test_mst_mfx_style_appowned_pipeline import (
    DnseNative, FakeQuarantineDrive, stage_owner_env,
)
from test_mst_ssi_native_stage import (
    Drive as FakeSsiDrive, env as ssi_env, source_rows,
)
from scripts import mst_ssi_native_stage as ssi_stage


class NativeFingerprintTests(unittest.TestCase):
    def sample(self):
        return DnseNative().payload()

    def test_dnse_order_independent_digest_but_price_value_sensitive(self):
        data=self.sample()
        a=native_canonical_sha256("DNSE","FPT","D1",data)
        b=native_canonical_sha256("DNSE","FPT","D1",{
            k:data[k] for k in reversed(list(data))
        })
        self.assertEqual(a,b)
        self.assertEqual(len(a),64)
        changed=copy.deepcopy(data)
        changed["v"][1]+=1
        self.assertNotEqual(a,native_canonical_sha256("DNSE","FPT","D1",changed))
        self.assertNotEqual(a,native_canonical_sha256("DNSE","DCM","D1",data))
        self.assertNotEqual(a,native_canonical_sha256("DNSE","FPT","M5",data))

    def test_ssi_payload_native_units_and_row_sequence_are_preserved(self):
        rows=source_rows("M5")
        a=native_canonical_sha256("SSI","FPT","M5",rows)
        b=native_canonical_sha256("SSI","FPT","M5",list(reversed(rows)))
        self.assertNotEqual(a,b)
        changed=copy.deepcopy(rows)
        changed[0]["close"]="100.500"
        self.assertNotEqual(a,native_canonical_sha256("SSI","FPT","M5",changed))
        self.assertNotEqual(a,native_canonical_sha256("SSI","HPG","M5",[
            dict(r,symbol="HPG") for r in rows
        ]))

    def test_dnse_unknown_field_must_fail_before_storing_source(self):
        for extra in ({"accessToken":"SIMULATED_NOT_REAL"},
                      {"broker_account":"SIMULATED"},
                      {"new_vendor_version":1}):
            payload={**self.sample(),**extra}
            with self.subTest(extra=list(extra)),self.assertRaisesRegex(
                cloud.CloudGateDenied,"MST_MFX_DNSE_NATIVE_FIELD_SET_DRIFT"
            ):
                cloud.validate_dnse_native(
                    payload,1794000000,1794500000)
            d=FakeQuarantineDrive()
            with self.assertRaisesRegex(
                cloud.CloudGateDenied,"MST_MFX_DNSE_NATIVE_FIELD_SET_DRIFT"
            ):
                cloud.stage_unpublished_dnse_source(
                    d,stage_owner_env(),payload)
            self.assertEqual(d.post_calls,0)

    def test_malformed_or_unknown_provider_native_fingerprint_denied(self):
        payload=self.sample()
        cases=[
            ("VCBS","FPT","D1",payload),
            ("DNSE","EURUSD","D1",payload),
            ("DNSE","FPT","H4",payload),
            ("DNSE","FPT","D1",{**payload,"unknown":True}),
            ("DNSE","FPT","D1",{**payload,"nextTime":99}),
            ("DNSE","FPT","D1",{**payload,"t":[1794000000]}),
            ("SSI","FPT","M5",[dict(source_rows("M5")[0],token="FAKE")]),
            ("SSI","FPT","M5",[dict(source_rows("M5")[0],symbol="DCM")]),
        ]
        for p,s,tf,data in cases:
            with self.subTest(p=p,s=s,tf=tf),self.assertRaises(
                NativeFingerprintDenied
            ):
                native_canonical_sha256(p,s,tf,data)

    def test_noncanonical_json_and_bounded_size_rejected(self):
        sample=self.sample()
        damaged=copy.deepcopy(sample)
        damaged["o"][0]=float("nan")
        with self.assertRaisesRegex(
            NativeFingerprintDenied,"MST_NATIVE_DIGEST_NONCANONICAL"
        ):
            native_canonical_sha256("DNSE","FPT","D1",damaged)
        huge=copy.deepcopy(sample)
        huge["o"][0]=int("9"*1500001)
        with self.assertRaises(NativeFingerprintDenied):
            native_canonical_sha256("DNSE","FPT","D1",huge)

    def test_real_dnse_stage_path_stores_two_separate_digest_proofs(self):
        payload=self.sample()
        d=FakeQuarantineDrive()
        receipt=cloud.stage_unpublished_dnse_source(
            d,stage_owner_env(),payload)
        archive=json.loads(d.media)
        native=archive["native_canonical_sha256"]
        self.assertEqual(native,native_canonical_sha256(
            "DNSE","FPT","D1",archive["raw_native"]))
        self.assertEqual(d.file_info["appProperties"]["native_canonical_sha256"],native)
        self.assertEqual(d.media_reads,2)
        self.assertTrue(receipt["unpublished_private_source_document_stored"])
        self.assertFalse(receipt["signals_and_trading_eligible"])
        self.assertNotEqual(native,d.file_info["appProperties"]["source_sha256"])
        d.file_info["appProperties"]["native_canonical_sha256"]="0"*64
        with self.assertRaisesRegex(
            cloud.CloudGateDenied,"MST_MFX_STAGED_NATIVE_FINGERPRINT_INVALID"
        ):
            cloud._quarantine_metadata(
                d,d.FILE_ID,d.file_info["parents"][0],d.file_info["name"],d.media)

    def test_real_ssi_stage_path_stores_two_separate_digest_proofs(self):
        rows=source_rows("M5")
        d=FakeSsiDrive()
        receipt=ssi_stage.stage_ssi_native_source(d,ssi_env("M5"),rows)
        archive=json.loads(d.new_body)
        expected=native_canonical_sha256(
            "SSI","FPT","M5",archive["raw_native"])
        self.assertEqual(archive["native_canonical_sha256"],expected)
        self.assertEqual(d.new_info["appProperties"]["native_canonical_sha256"],expected)
        self.assertEqual(d.new_media_count,2)
        self.assertTrue(receipt["unpublished_private_source_document_stored"])
        self.assertFalse(receipt["signals_and_trading_eligible"])
        d.new_info["appProperties"]["native_canonical_sha256"]="0"*64
        with self.assertRaisesRegex(
            cloud.CloudGateDenied,"MST_MFX_STAGED_NATIVE_FINGERPRINT_INVALID"
        ):
            cloud._quarantine_metadata(
                d,d.NEW,d.CHUNKS,d.new_info["name"],d.new_body)

    def test_legacy_private_candidate_without_new_digest_is_readable(self):
        d=FakeQuarantineDrive()
        cloud.stage_unpublished_dnse_source(d,stage_owner_env(),self.sample())
        legacy=json.loads(d.media)
        legacy.pop("native_canonical_sha256")
        d.media=json.dumps(legacy,sort_keys=True,separators=(",",":")).encode()
        from hashlib import sha256, md5
        d.file_info["appProperties"].pop("native_canonical_sha256")
        d.file_info["appProperties"]["source_sha256"]=sha256(d.media).hexdigest()
        d.file_info["size"]=str(len(d.media))
        d.file_info["md5Checksum"]=md5(d.media).hexdigest()
        version=cloud._quarantine_metadata(
            d,d.FILE_ID,d.file_info["parents"][0],d.file_info["name"],d.media)
        self.assertEqual(version,"1")
        self.assertFalse(legacy["eligible_for_signals"])


if __name__=="__main__":
    unittest.main()
