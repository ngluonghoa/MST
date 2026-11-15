"""§198 owner-UNTRUSTED fake backend, signed receipt and lost-ACK races.

This file contains public deterministic TEST signing bytes, no production
credential. No network, actual atomic Cloud store, Drive files, publisher,
market-data vendor, cache head or broker trade is touched.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import json
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat

from scripts.mst_highwater_cas_receipt import (
    BODY_SCHEMA,SCHEMA,CasReceiptDenied,receipt_sha256,
    verify_cas_receipt_claim,verify_cas_receipt_claim_chain,
)
from test_mst_highwater_cas_intent import (
    FakeAuthoritativeAtomicStore,anchor,prepare,proposed,
)
from test_mst_signed_highwater_diagnostic import (
    PUBLIC as FAKE_CHECKPOINT_PUBLIC,snapshots,
)

FAKE_BACKEND_ID="FAKE_CAS_BACKEND_NOT_PRODUCTION"
FAKE_BACKEND_PRIVATE=Ed25519PrivateKey.from_private_bytes(bytes(range(65,97)))
FAKE_BACKEND_PUBLIC=FAKE_BACKEND_PRIVATE.public_key().public_bytes(
    encoding=Encoding.Raw,format=PublicFormat.Raw,
)
WRONG_BACKEND_PUBLIC=Ed25519PrivateKey.from_private_bytes(
    bytes(range(97,129))
).public_key().public_bytes(encoding=Encoding.Raw,format=PublicFormat.Raw)


def claim(intent,before,after,*,previous_digest=None,previous_fence=0,
          signer=FAKE_BACKEND_PRIVATE):
    body={
        "schema":BODY_SCHEMA,
        "repository":"ngluonghoa/MST",
        "series_id":intent["series_id"],
        "request_id":intent["request_id"],
        "intent_sha256":intent["intent_sha256"],
        "previous_receipt_sha256":previous_digest,
        "previous_fence":previous_fence,
        "committed_fence":previous_fence+1,
        "expected_generation":intent["observed_generation"],
        "committed_generation":intent["proposed_generation"],
        "expected_revision":intent["expected_revision"],
        "committed_revision":intent["proposed_revision"],
        "expected_tip_checkpoint_sha256":intent["expected_tip_checkpoint_sha256"],
        "committed_tip_checkpoint_sha256":intent["proposed_tip_checkpoint_sha256"],
        "expected_head_pin":deepcopy(intent["expected_head_pin"]),
        "committed_head_pin":deepcopy(intent["proposed_head_pin"]),
        "atomic_cas_reported":True,
        "publisher_activated":False,
        "signals_eligible":False,
    }
    wire=json.dumps(body,sort_keys=True,separators=(",",":"),
                    allow_nan=False,ensure_ascii=True).encode()
    return {
        "schema":SCHEMA,
        "key_id":FAKE_BACKEND_ID,
        "body":body,
        "signature_b64":base64.b64encode(signer.sign(wire)).decode(),
    }


def test_entry(chain,store,*,previous_digest=None,previous_fence=0,
               run="43270010004",request="FAKE_CAS_SIGNED_REQUEST_0001"):
    before=store.read()
    next_checkpoint=proposed(chain,run=run)
    intent=prepare(chain,next_checkpoint,before,request_id=request)
    if not store.atomic_compare_and_swap(intent):
        raise AssertionError("unexpected fake atomic rejection")
    after=store.read()
    signed_receipt=claim(
        intent,before,after,
        previous_digest=previous_digest,
        previous_fence=previous_fence,
    )
    return next_checkpoint,{
        "prepared_intent":intent,
        "before_anchor":before,
        "after_anchor":after,
        "original_intent_sha256":intent["intent_sha256"],
        "receipt":signed_receipt,
    }


def verify_entry(item,*,previous_digest=None,previous_fence=0,
                 key=FAKE_BACKEND_PUBLIC,backend_id=FAKE_BACKEND_ID):
    return verify_cas_receipt_claim(
        prepared_intent=item["prepared_intent"],
        originally_observed_anchor=item["before_anchor"],
        resulting_anchor_readback=item["after_anchor"],
        receipt=item["receipt"],
        original_intent_sha256=item["original_intent_sha256"],
        expected_previous_receipt_sha256=previous_digest,
        expected_previous_fence=previous_fence,
        trusted_backend_key_id=backend_id,
        trusted_backend_public_key=key,
    )


class SignedCasReceiptContractTests(unittest.TestCase):
    def setup_one(self):
        _,chain=snapshots()
        store=FakeAuthoritativeAtomicStore(anchor(chain))
        cp,entry=test_entry(chain,store)
        return chain,store,cp,entry

    def test_public_fake_backend_signer_is_distinct_from_checkpoint_key(self):
        self.assertNotEqual(FAKE_CHECKPOINT_PUBLIC,FAKE_BACKEND_PUBLIC)

    def test_signed_receipt_and_post_commit_readback_match_but_not_owner_trust(self):
        chain,store,cp,entry=self.setup_one()
        diag=verify_entry(entry)
        self.assertEqual(diag["observed_fence"],1)
        self.assertEqual(diag["generation"],4)
        self.assertEqual(diag["revision"],10)
        self.assertTrue(diag["ed25519_valid_for_supplied_backend_key"])
        self.assertTrue(diag["readback_matches_signed_claim"])
        for key in ("independent_backend_key_authenticated",
                    "atomic_cas_independently_proven",
                    "immutable_monotone_receipt_ledger_verified",
                    "publisher_activated","cache_published","signals_eligible"):
            self.assertFalse(diag[key],key)
        self.assertEqual(store.commits,1)

    def test_two_concurrent_writer_one_fake_commits_only_winner_gets_receipt(self):
        _,chain=snapshots()
        before=anchor(chain)
        store=FakeAuthoritativeAtomicStore(before)
        proposed_a=proposed(chain,run="43270010004")
        proposed_b=proposed(chain,run="43270010005")
        intent_a=prepare(chain,proposed_a,before,request_id="FAKE_WINNER_20261115")
        intent_b=prepare(chain,proposed_b,before,request_id="FAKE_LOSER_20261115")
        self.assertTrue(store.atomic_compare_and_swap(intent_a))
        self.assertFalse(store.atomic_compare_and_swap(intent_b))
        winning=claim(intent_a,before,store.read())
        entry={
            "prepared_intent":intent_a,"before_anchor":before,
            "after_anchor":store.read(),
            "original_intent_sha256":intent_a["intent_sha256"],
            "receipt":winning,
        }
        self.assertTrue(verify_entry(entry)["readback_matches_signed_claim"])
        self.assertEqual(store.commits,1)
        # A fabricated signed loser result cannot match actual new head.
        loser=deepcopy(entry)
        loser["prepared_intent"]=intent_b
        loser["original_intent_sha256"]=intent_b["intent_sha256"]
        loser["receipt"]=claim(intent_b,before,store.read())
        with self.assertRaisesRegex(
            CasReceiptDenied,"MST_CAS_RECEIPT_READBACK_MISMATCH"
        ):
            verify_entry(loser)

    def test_no_ack_recovery_requires_trusted_signed_readback_not_retry_claim(self):
        _,store,_,entry=self.setup_one()
        after=store.read()
        first=verify_entry(entry)
        self.assertFalse(store.atomic_compare_and_swap(entry["prepared_intent"]))
        self.assertEqual(store.commits,1)
        # Recovery is forensic validation of matching evidence, never
        # a second write or independent production acceptance.
        second=verify_entry(entry)
        self.assertEqual(first["receipt_sha256"],second["receipt_sha256"])
        self.assertEqual(after["generation"],4)

    def test_signed_receipt_chain_exact_fences_and_tip(self):
        _,chain=snapshots()
        store=FakeAuthoritativeAtomicStore(anchor(chain))
        cp1,entry1=test_entry(chain,store,run="43270010004")
        cp2,entry2=test_entry(
            [*chain,cp1],store,previous_digest=receipt_sha256(entry1["receipt"]),
            previous_fence=1,run="43270010005",
            request="FAKE_CAS_SIGNED_REQUEST_0002",
        )
        cp3,entry3=test_entry(
            [*chain,cp1,cp2],store,
            previous_digest=receipt_sha256(entry2["receipt"]),
            previous_fence=2,run="43270010006",
            request="FAKE_CAS_SIGNED_REQUEST_0003",
        )
        entries=[entry1,entry2,entry3]
        diag=verify_cas_receipt_claim_chain(
            entries,expected_start_receipt_sha256=None,
            expected_start_fence=0,
            expected_tip_receipt_sha256=receipt_sha256(entry3["receipt"]),
            trusted_backend_key_id=FAKE_BACKEND_ID,
            trusted_backend_public_key=FAKE_BACKEND_PUBLIC,
        )
        self.assertEqual(diag["verified_signed_claim_count"],3)
        self.assertEqual(diag["linked_claim_edges"],2)
        self.assertEqual(diag["last_claimed_fence"],3)
        self.assertFalse(diag["independent_atomic_storage_proven"])
        self.assertFalse(diag["append_only_ledger_independently_verified"])
        self.assertFalse(diag["production_cache_published"])

    def test_valid_signature_under_wrong_public_key_is_denied(self):
        _,_,_,entry=self.setup_one()
        with self.assertRaisesRegex(CasReceiptDenied,"SIGNATURE_INVALID"):
            verify_entry(entry,key=WRONG_BACKEND_PUBLIC)
        with self.assertRaisesRegex(CasReceiptDenied,"ENVELOPE_INVALID"):
            verify_entry(entry,backend_id="NOT_THE_PINNED_BACKEND_ID")

    def test_unsigned_and_resigned_false_trading_or_cas_claim_denied(self):
        _,_,_,entry=self.setup_one()
        for field,value in (("atomic_cas_reported",False),
                            ("publisher_activated",True),
                            ("signals_eligible",True)):
            with self.subTest(field=field):
                altered=deepcopy(entry)
                altered["receipt"]["body"][field]=value
                altered["receipt"]=claim(
                    altered["prepared_intent"],
                    altered["before_anchor"],altered["after_anchor"],
                )
                altered["receipt"]["body"][field]=value
                # Re-sign a FALSE AUTHORITY claim using public fixture key.
                payload=json.dumps(altered["receipt"]["body"],sort_keys=True,
                    separators=(",",":"),allow_nan=False,ensure_ascii=True).encode()
                altered["receipt"]["signature_b64"]=base64.b64encode(
                    FAKE_BACKEND_PRIVATE.sign(payload)
                ).decode()
                with self.assertRaisesRegex(CasReceiptDenied,"CLAIMS_INVALID"):
                    verify_entry(altered)

    def test_fake_signed_request_id_and_sha_drift_denied(self):
        _,_,_,entry=self.setup_one()
        for field,value in (("request_id","FAKE_OTHER_REQUEST_0001"),
                            ("intent_sha256","f"*64),
                            ("expected_revision",999),
                            ("committed_generation",99),
                            ("committed_tip_checkpoint_sha256","e"*64)):
            with self.subTest(field=field):
                altered=deepcopy(entry)
                altered["receipt"]["body"][field]=value
                # Even re-signed mismatched receipts are denied.
                payload=json.dumps(altered["receipt"]["body"],sort_keys=True,
                    separators=(",",":"),allow_nan=False,ensure_ascii=True).encode()
                altered["receipt"]["signature_b64"]=base64.b64encode(
                    FAKE_BACKEND_PRIVATE.sign(payload)
                ).decode()
                with self.assertRaisesRegex(
                    CasReceiptDenied,"REQUEST_MISMATCH"
                ):
                    verify_entry(altered)

    def test_false_readback_rollback_denied_even_with_signed_claim(self):
        _,_,_,entry=self.setup_one()
        altered=deepcopy(entry)
        altered["after_anchor"]=deepcopy(entry["before_anchor"])
        with self.assertRaisesRegex(CasReceiptDenied,"READBACK_MISMATCH"):
            verify_entry(altered)
        altered=deepcopy(entry)
        altered["after_anchor"]["tip_checkpoint_sha256"]="0"*64
        with self.assertRaisesRegex(CasReceiptDenied,"READBACK_MISMATCH"):
            verify_entry(altered)

    def test_broken_fence_or_wrong_prior_receipt_digest_denied(self):
        _,_,_,entry=self.setup_one()
        for field,val in (
            ("previous_fence",1),
            ("committed_fence",2),
            ("previous_receipt_sha256","f"*64),
        ):
            with self.subTest(field=field):
                altered=deepcopy(entry)
                altered["receipt"]["body"][field]=val
                with self.assertRaisesRegex(CasReceiptDenied,"CLAIMS_INVALID"):
                    verify_entry(altered)

    def test_missing_unknown_and_noncanonical_signature_encodings_denied(self):
        _,_,_,entry=self.setup_one()
        for field,val in (("signature_b64","!INVALID"),
                          ("signature_b64",None),
                          ("key_id",["UNHASHABLE"]),
                          ("extra","FAKE_FIELD")):
            with self.subTest(field=field):
                altered=deepcopy(entry)
                altered["receipt"][field]=val
                with self.assertRaises(CasReceiptDenied):
                    verify_entry(altered)

    def test_untrusted_prior_fence_and_key_type_denied(self):
        _,_,_,entry=self.setup_one()
        for fence,prior in ((True,None),(-1,None),(1,None),(0,"a"*64)):
            with self.subTest(fence=str(fence),prior=prior):
                with self.assertRaisesRegex(CasReceiptDenied,"EXTERNAL_TRUST_INPUT_INVALID"):
                    verify_entry(entry,previous_fence=fence,previous_digest=prior)

    def test_chains_missing_middle_reordered_duplicate_and_tip_rollback_denied(self):
        _,chain=snapshots()
        store=FakeAuthoritativeAtomicStore(anchor(chain))
        cp1,e1=test_entry(chain,store,run="43270010004")
        cp2,e2=test_entry([*chain,cp1],store,
            previous_digest=receipt_sha256(e1["receipt"]),
            previous_fence=1,run="43270010005",
            request="FAKE_CAS_SIGNED_REQUEST_0002")
        items=[e1,e2]
        original_tip=receipt_sha256(e2["receipt"])
        for candidate,tip in (
            ([e1],original_tip),
            ([e2,e1],original_tip),
            ([e1,e1],original_tip),
            ([e1,e2],"f"*64),
        ):
            with self.subTest(kind=str(len(candidate)),tip=tip[:3]):
                with self.assertRaises(CasReceiptDenied):
                    verify_cas_receipt_claim_chain(
                        candidate,expected_start_receipt_sha256=None,
                        expected_start_fence=0,
                        expected_tip_receipt_sha256=tip,
                        trusted_backend_key_id=FAKE_BACKEND_ID,
                        trusted_backend_public_key=FAKE_BACKEND_PUBLIC,
                    )

    def test_reused_request_id_across_new_signed_fence_is_replay(self):
        _,chain=snapshots()
        store=FakeAuthoritativeAtomicStore(anchor(chain))
        cp1,e1=test_entry(chain,store,run="43270010004",
                          request="FAKE_REUSED_CAS_REQUEST_0001")
        # Simulate a defect in the untrusted external backend: it lost its
        # durable idempotency index but kept the signed highwater history.
        store.seen_requests.clear()
        cp2,e2=test_entry(
            [*chain,cp1],store,previous_digest=receipt_sha256(e1["receipt"]),
            previous_fence=1,run="43270010005",
            request="FAKE_REUSED_CAS_REQUEST_0001",
        )
        self.assertEqual(cp2["body"]["sequence"],5)
        self.assertTrue(verify_entry(
            e2,previous_digest=receipt_sha256(e1["receipt"]),
            previous_fence=1,
        )["ed25519_valid_for_supplied_backend_key"])
        with self.assertRaisesRegex(
            CasReceiptDenied,"MST_CAS_RECEIPT_CHAIN_REPLAYED_REQUEST_ID"
        ):
            verify_cas_receipt_claim_chain(
                [e1,e2],expected_start_receipt_sha256=None,
                expected_start_fence=0,
                expected_tip_receipt_sha256=receipt_sha256(e2["receipt"]),
                trusted_backend_key_id=FAKE_BACKEND_ID,
                trusted_backend_public_key=FAKE_BACKEND_PUBLIC,
            )

    def test_valid_signatures_do_not_supply_immutable_external_monotone_trust(self):
        _,_,_,entry=self.setup_one()
        result=verify_entry(entry)
        self.assertTrue(result["ed25519_valid_for_supplied_backend_key"])
        self.assertFalse(result["independent_backend_key_authenticated"])
        self.assertFalse(result["atomic_cas_independently_proven"])
        self.assertFalse(result["immutable_monotone_receipt_ledger_verified"])
        self.assertFalse(result["cache_published"])


if __name__=="__main__":
    unittest.main()
