"""§196 signed-highwater tests use a PUBLIC, UNSAFE deterministic fake key.

The fixture signing key is committed ONLY to prove Ed25519 verification and
must never authorize a real GitHub workflow, Drive file, Cache publish or
independently anchored owner release. Every sample price and source fake.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import json
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat

from scripts.mst_signed_highwater_diagnostic import (
    CHECKPOINT_SCHEMA,BODY_SCHEMA,HighwaterDenied,
    checkpoint_digest,verify_signed_highwater_candidates,
    verify_signed_highwater_against_private_source_chain,
)
from test_mst_private_source_chain_diagnostic import (
    chain,pin,record,
)

KEY_ID="MST_FAKE_KEY_NOT_PRODUCTION"
SERIES="MST_FAKE_SERIES_20261115"
FAKE_PRIVATE=Ed25519PrivateKey.from_private_bytes(bytes(range(1,33)))
PUBLIC=FAKE_PRIVATE.public_key().public_bytes(
    encoding=Encoding.Raw,format=PublicFormat.Raw,
)
OTHER_PUBLIC=Ed25519PrivateKey.from_private_bytes(
    bytes(range(33,65))
).public_key().public_bytes(
    encoding=Encoding.Raw,format=PublicFormat.Raw,
)


def sign(body, *, private=FAKE_PRIVATE, key_id=KEY_ID):
    wire=json.dumps(
        body,sort_keys=True,separators=(",",":"),
        allow_nan=False,ensure_ascii=True,
    ).encode("utf-8")
    return {
        "schema":CHECKPOINT_SCHEMA,
        "key_id":key_id,
        "body":body,
        "signature_b64":base64.b64encode(private.sign(wire)).decode("ascii"),
    }


def signed(obj,seq,previous=None,*,provider="DNSE",tf="D1",series=SERIES):
    previous_body=previous["body"] if previous else None
    body={
        "schema":BODY_SCHEMA,
        "repository":"ngluonghoa/MST",
        "series_id":series,
        "sequence":seq,
        "previous_checkpoint_sha256":checkpoint_digest(previous) if previous else None,
        "previous_head_pin":previous_body["head_pin"] if previous_body else None,
        "head_pin":pin(obj,provider,tf),
        "source_finality_attested":False,
        "publisher_cas_executed":False,
        "source_licensed_for_storage_attested":False,
        "signals_eligible":False,
    }
    return sign(body)


def snapshots(provider="DNSE",tf="D1"):
    a,b,c=chain(provider,tf)
    s1=signed(a,1,provider=provider,tf=tf)
    s2=signed(b,2,s1,provider=provider,tf=tf)
    s3=signed(c,3,s2,provider=provider,tf=tf)
    return (a,b,c),[s1,s2,s3]


def check_signed(ckpts,**kwargs):
    return verify_signed_highwater_candidates(
        ckpts,trusted_key_id=kwargs.get("trusted_key_id",KEY_ID),
        trusted_ed25519_public_key=kwargs.get("key",PUBLIC),
        expected_tip_checkpoint_sha256=kwargs.get(
            "tip",checkpoint_digest(ckpts[-1])
        ),
    )


def check_both(records,ckpts,**kwargs):
    return verify_signed_highwater_against_private_source_chain(
        [record(x) for x in records],
        parent=records[0]["metadata"]["parents"][0],
        complete_census_supplied=kwargs.get("census",True),
        candidates=ckpts,trusted_key_id=kwargs.get("trusted_key_id",KEY_ID),
        trusted_ed25519_public_key=kwargs.get("key",PUBLIC),
        expected_tip_checkpoint_sha256=kwargs.get(
            "tip",checkpoint_digest(ckpts[-1])
        ),
    )


class SignedHighwaterCandidateTests(unittest.TestCase):
    def test_real_ed25519_signature_on_three_synthetic_generations(self):
        for provider,tf in (("DNSE","D1"),("SSI","D1"),("SSI","M5")):
            with self.subTest(provider=provider,tf=tf):
                records,ckpts=snapshots(provider,tf)
                a=check_signed(ckpts)
                self.assertEqual(a["checkpoint_count"],3)
                self.assertEqual(a["linked_checkpoint_edges"],2)
                self.assertTrue(a["ed25519_signatures_valid_for_supplied_public_key"])
                self.assertFalse(a["independent_owner_signer_identity_verified"])
                self.assertFalse(a["external_tip_pin_independently_authenticated"])
                self.assertFalse(a["atomic_compare_and_swap_executed"])
                b=check_both(records,ckpts)
                self.assertEqual(b["source_candidates_checked"],3)
                self.assertTrue(b["every_intermediate_pin_matches_candidate"])
                self.assertFalse(b["independently_anchored_monotone_highwater_verified"])
                self.assertFalse(b["cache_published"])
                self.assertFalse(b["signal_eligible"])

    def test_single_genesis_is_only_a_candidate_not_a_release(self):
        a,b,c=chain()
        s=signed(a,1)
        report=check_signed([s])
        self.assertEqual(report["linked_checkpoint_edges"],0)
        self.assertFalse(report["market_cache_published"])

    def test_signed_envelope_payload_tamper_rejected(self):
        _,ckpts=snapshots()
        for field,bad in (
            ("source_finality_attested",True),
            ("publisher_cas_executed",True),
            ("source_licensed_for_storage_attested",True),
            ("signals_eligible",True),
            ("series_id","MST_DIFFERENT_SERIES"),
            ("sequence",4),
        ):
            with self.subTest(field=field):
                changed=deepcopy(ckpts)
                changed[-1]["body"][field]=bad
                with self.assertRaisesRegex(
                    HighwaterDenied,"ED25519_SIGNATURE_INVALID|UNATTESTED_BODY_REQUIRED"
                ):
                    check_signed(changed)

    def test_re_signed_fraudulent_attestation_still_denied(self):
        _,ckpts=snapshots()
        for field in ("signals_eligible","publisher_cas_executed",
                      "source_finality_attested",
                      "source_licensed_for_storage_attested"):
            with self.subTest(field=field):
                replaced=deepcopy(ckpts)
                body=deepcopy(replaced[-1]["body"])
                body[field]=True
                replaced[-1]=sign(body)
                with self.assertRaisesRegex(
                    HighwaterDenied,"UNATTESTED_BODY_REQUIRED",
                ):
                    check_signed(replaced)

    def test_wrong_public_key_and_key_id_fail_closed(self):
        _,ckpts=snapshots()
        with self.assertRaisesRegex(HighwaterDenied,"ED25519_SIGNATURE_INVALID"):
            check_signed(ckpts,key=OTHER_PUBLIC)
        with self.assertRaisesRegex(HighwaterDenied,"ENVELOPE_INVALID"):
            check_signed(ckpts,trusted_key_id="DIFFERENT_TEST_KEY")
        with self.assertRaisesRegex(HighwaterDenied,"EXTERNAL_TRUST_INPUT_INVALID"):
            check_signed(ckpts,key=b"short")

    def test_invalid_signature_base64_or_noncanonical_encoding_rejected(self):
        _,ckpts=snapshots()
        for broken in ("!bad", "A"*88, "A"*87+"="):
            with self.subTest(broken=broken):
                data=deepcopy(ckpts)
                data[-1]["signature_b64"]=broken
                with self.assertRaises(HighwaterDenied):
                    check_signed(data)

    def test_re_signed_wrong_predecessor_sha_denied(self):
        _,ckpts=snapshots()
        changed=deepcopy(ckpts)
        body=deepcopy(changed[-1]["body"])
        body["previous_checkpoint_sha256"]="a"*64
        changed[-1]=sign(body)
        with self.assertRaisesRegex(HighwaterDenied,"CHAIN_LINK_INVALID"):
            check_signed(changed)

    def test_re_signed_previous_head_drift_denied(self):
        _,ckpts=snapshots()
        changed=deepcopy(ckpts)
        body=deepcopy(changed[-1]["body"])
        body["previous_head_pin"]["source_sha256"]="b"*64
        changed[-1]=sign(body)
        with self.assertRaisesRegex(HighwaterDenied,"CHAIN_LINK_INVALID"):
            check_signed(changed)

    def test_re_signed_run_decrease_or_same_head_denied(self):
        _,ckpts=snapshots()
        for edit in ("old_run","same_file"):
            changed=deepcopy(ckpts)
            body=deepcopy(changed[-1]["body"])
            if edit=="old_run":
                body["head_pin"]["run_id"]=changed[-2]["body"]["head_pin"]["run_id"]
            else:
                body["head_pin"]["file_id"]=changed[-2]["body"]["head_pin"]["file_id"]
            changed[-1]=sign(body)
            with self.subTest(edit=edit),self.assertRaisesRegex(
                HighwaterDenied,"CHAIN_LINK_INVALID",
            ):
                check_signed(changed)

    def test_re_signed_symbol_tf_provider_shift_denied(self):
        _,ckpts=snapshots()
        for field,v in (("symbol","DCM"),("native_tf","M15"),("provider","SSI")):
            with self.subTest(field=field):
                changed=deepcopy(ckpts)
                body=deepcopy(changed[-1]["body"])
                body["head_pin"][field]=v
                changed[-1]=sign(body)
                with self.assertRaisesRegex(HighwaterDenied,"CHAIN_LINK_INVALID"):
                    check_signed(changed)

    def test_missing_middle_replay_or_reversed_signed_sequence_denied(self):
        _,ckpts=snapshots()
        for different in ([ckpts[0],ckpts[2]],list(reversed(ckpts)),
                          [ckpts[0],ckpts[1],ckpts[1]]):
            with self.subTest(length=len(different)),self.assertRaises(
                HighwaterDenied,
            ):
                check_signed(different)

    def test_old_tip_digest_cannot_validate_newer_version(self):
        _,ckpts=snapshots()
        old_tip=checkpoint_digest(ckpts[1])
        with self.assertRaisesRegex(HighwaterDenied,"EXPECTED_TIP_MISMATCH"):
            check_signed(ckpts,tip=old_tip)

    def test_removed_latest_checkpoint_cannot_satisfy_known_latest_tip(self):
        _,ckpts=snapshots()
        anchored_tip=checkpoint_digest(ckpts[-1])
        with self.assertRaisesRegex(HighwaterDenied,"EXPECTED_TIP_MISMATCH"):
            check_signed(ckpts[:-1],tip=anchored_tip)

    def test_modified_head_source_rehashed_fails_signed_pin_readback(self):
        rows,ckpts=snapshots()
        latest=deepcopy(rows[-1])
        latest["metadata"]["appProperties"]["source_run_id"]="43270010009"
        recs=[rows[0],rows[1],latest]
        with self.assertRaisesRegex(
            HighwaterDenied,"PRIVATE_CHAIN_INVALID|INTERMEDIATE_PIN_MISMATCH"
        ):
            check_both(recs,ckpts)

    def test_source_chain_missing_middle_refused(self):
        rows,ckpts=snapshots()
        with self.assertRaisesRegex(HighwaterDenied,"SOURCE_CARDINALITY_INVALID"):
            check_both([rows[0],rows[2]],ckpts)

    def test_correct_signatures_cannot_bypass_incomplete_drive_census(self):
        rows,ckpts=snapshots()
        with self.assertRaisesRegex(HighwaterDenied,"PRIVATE_CHAIN_INVALID"):
            check_both(rows,ckpts,census=False)

    def test_missing_extra_repeated_source_record_denied(self):
        rows,ckpts=snapshots()
        fake=[rows[0],rows[0],rows[2]]
        with self.assertRaises(HighwaterDenied):
            check_both(fake,ckpts)

    def test_signed_intermediate_mismatch_even_when_floor_tip_match(self):
        rows,ckpts=snapshots()
        altered=deepcopy(ckpts)
        # Sign an alternative intermediate with a legitimate synthetic key.
        inner=deepcopy(altered[1]["body"])
        inner["head_pin"]["source_sha256"]="c"*64
        altered[1]=sign(inner)
        # Re-sign the tip with the new predecessor checkpoint hash/head.
        tail=deepcopy(altered[-1]["body"])
        tail["previous_checkpoint_sha256"]=checkpoint_digest(altered[1])
        tail["previous_head_pin"]=inner["head_pin"]
        altered[-1]=sign(tail)
        self.assertTrue(check_signed(altered)["ed25519_signatures_valid_for_supplied_public_key"])
        with self.assertRaisesRegex(
            HighwaterDenied,"INTERMEDIATE_PIN_MISMATCH",
        ):
            check_both(rows,altered)

    def test_invalid_input_types_deny_not_crash(self):
        _,ckpts=snapshots()
        for raw in ([],{},None,[ckpts[0]]*129):
            with self.subTest(raw_type=type(raw).__name__),self.assertRaises(
                HighwaterDenied,
            ):
                verify_signed_highwater_candidates(
                    raw,trusted_key_id=KEY_ID,
                    trusted_ed25519_public_key=PUBLIC,
                    expected_tip_checkpoint_sha256="a"*64,
                )
        for key,val in (("signature_b64",None),("body",None),
                        ("key_id",["fake"]),("extra","FAKE")):
            with self.subTest(field=key):
                altered=deepcopy(ckpts)
                altered[-1][key]=val
                with self.assertRaises(HighwaterDenied):
                    check_signed(altered)


if __name__=="__main__":
    unittest.main()
