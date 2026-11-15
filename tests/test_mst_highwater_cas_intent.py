"""§197 fake CAS race QA. All stores and Ed25519 credentials synthetic.

The fake store is deliberately only in TESTS. It models a genuine atomic
comparison on the authoritative generation/revision/tip. No production Drive
highwater, API rights, secret or trading path is touched.
"""
from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.mst_highwater_cas_intent import (
    ANCHOR_SCHEMA, CasIntentDenied, prepare_highwater_conditional_write,
    verify_pre_submit_snapshot,
)
from scripts.mst_signed_highwater_diagnostic import checkpoint_digest
from test_mst_signed_highwater_diagnostic import (
    KEY_ID, PUBLIC, OTHER_PUBLIC, signed, snapshots,
)
from test_mst_private_source_chain_diagnostic import synthetic


def anchor(ckpts, revision=9):
    body=ckpts[-1]["body"]
    return {
        "schema":ANCHOR_SCHEMA,
        "series_id":body["series_id"],
        "generation":body["sequence"],
        "tip_checkpoint_sha256":checkpoint_digest(ckpts[-1]),
        "head_pin":deepcopy(body["head_pin"]),
        "revision":revision,
    }


def proposed(ckpts, *, run="43270010004", tf="D1", provider="DNSE"):
    source=synthetic(provider,run,tf=tf)
    return signed(
        source,len(ckpts)+1,ckpts[-1],provider=provider,tf=tf,
    )


def prepare(ckpts, checkpoint, observed, *, request_id="FAKE_OWNER_REQUEST_0001",
            key=PUBLIC,tip=None):
    return prepare_highwater_conditional_write(
        current_signed_chain=ckpts,
        proposed_signed_checkpoint=checkpoint,
        observed_external_anchor=observed,
        trusted_key_id=KEY_ID,
        trusted_ed25519_public_key=key,
        expected_current_tip=tip or checkpoint_digest(ckpts[-1]),
        request_id=request_id,
    )


class FakeAuthoritativeAtomicStore:
    """Only an in-memory TEST implementation, never imported in production."""
    def __init__(self,snapshot):
        self.current=deepcopy(snapshot)
        self.commits=0
        self.seen_requests=set()

    def read(self):
        return deepcopy(self.current)

    def atomic_compare_and_swap(self,intent):
        # One indivisible compare+write in fake model; a real deployment
        # needs separately trusted, atomic persistent provider and fencing.
        key=intent["request_id"]
        if key in self.seen_requests:
            return False
        c=self.current
        if (intent["series_id"]!=c["series_id"]
                or intent["expected_revision"]!=c["revision"]
                or intent["observed_generation"]!=c["generation"]
                or intent["expected_tip_checkpoint_sha256"]
                   !=c["tip_checkpoint_sha256"]
                or intent["expected_head_pin"]!=c["head_pin"]):
            return False
        self.current={
            "schema":ANCHOR_SCHEMA,
            "series_id":c["series_id"],
            "generation":intent["proposed_generation"],
            "tip_checkpoint_sha256":intent["proposed_tip_checkpoint_sha256"],
            "head_pin":deepcopy(intent["proposed_head_pin"]),
            "revision":intent["proposed_revision"],
        }
        self.seen_requests.add(key)
        self.commits+=1
        return True


class CasIntentTests(unittest.TestCase):
    def data(self):
        _,ckpts=snapshots()
        observed=anchor(ckpts)
        next_signed=proposed(ckpts)
        return ckpts,observed,next_signed

    def test_valid_signed_successor_produces_only_unpublished_intent(self):
        ckpts,a,n=self.data()
        intent=prepare(ckpts,n,a)
        self.assertEqual(intent["observed_generation"],3)
        self.assertEqual(intent["proposed_generation"],4)
        self.assertEqual(intent["expected_revision"],9)
        self.assertEqual(intent["proposed_revision"],10)
        self.assertEqual(intent["proposed_tip_checkpoint_sha256"],checkpoint_digest(n))
        self.assertTrue(intent["external_atomic_cas_required"])
        self.assertFalse(intent["published"])
        self.assertFalse(intent["signals_eligible"])
        summary=verify_pre_submit_snapshot(intent,observed_external_anchor=a)
        self.assertTrue(summary["expected_tip_match"])
        self.assertFalse(summary["external_store_atomic_cas_executed"])
        self.assertFalse(summary["owner_trust_anchor_verified"])
        self.assertFalse(summary["production_cache_published"])

    def test_two_competing_writers_same_snapshot_only_one_mock_atomic_wins(self):
        ckpts,initial,n1=self.data()
        n2=proposed(ckpts,run="43270010005")
        i1=prepare(ckpts,n1,initial,request_id="FAKE_OWNER_WRITER_A_0001")
        i2=prepare(ckpts,n2,initial,request_id="FAKE_OWNER_WRITER_B_0002")
        store=FakeAuthoritativeAtomicStore(initial)
        # BOTH stale writers can pass an early reread. An early read is
        # not a substitute for a real single-step authoritative CAS.
        verify_pre_submit_snapshot(i1,observed_external_anchor=store.read())
        verify_pre_submit_snapshot(i2,observed_external_anchor=store.read())
        self.assertTrue(store.atomic_compare_and_swap(i1))
        self.assertFalse(store.atomic_compare_and_swap(i2))
        self.assertEqual(store.commits,1)
        self.assertEqual(store.read()["tip_checkpoint_sha256"],
                         checkpoint_digest(n1))
        with self.assertRaisesRegex(
            CasIntentDenied,"MST_CAS_STALE_OR_CHANGED_SNAPSHOT"
        ):
            verify_pre_submit_snapshot(i2,observed_external_anchor=store.read())

    def test_unknown_ack_retry_is_not_auto_success(self):
        ckpts,initial,n1=self.data()
        intent=prepare(ckpts,n1,initial)
        store=FakeAuthoritativeAtomicStore(initial)
        self.assertTrue(store.atomic_compare_and_swap(intent))
        # Model a lost ACK then exactly the SAME retry: it MUST NOT be
        # claimed as a successful second write or trigger unconditional PUT.
        self.assertFalse(store.atomic_compare_and_swap(intent))
        self.assertEqual(store.commits,1)

    def test_pre_submit_reread_detects_changed_revision_or_tip(self):
        ckpts,initial,n1=self.data()
        intent=prepare(ckpts,n1,initial)
        for field,value in (
            ("revision",10),
            ("tip_checkpoint_sha256","a"*64),
            ("generation",4),
            ("series_id","MST_FOREFIGN_FAKE_SERIES"),
            ("head_pin",dict(initial["head_pin"],run_id="43270010009")),
        ):
            with self.subTest(field=field):
                changed=deepcopy(initial)
                changed[field]=value
                with self.assertRaisesRegex(
                    CasIntentDenied,"MST_CAS_STALE_OR_CHANGED_SNAPSHOT"
                ):
                    verify_pre_submit_snapshot(intent,observed_external_anchor=changed)

    def test_proposal_from_wrong_public_key_rejected(self):
        ckpts,a,n=self.data()
        with self.assertRaisesRegex(
            CasIntentDenied,"MST_CAS_SIGNED_SUCCESSOR_INVALID"
        ):
            prepare(ckpts,n,a,key=OTHER_PUBLIC)

    def test_stale_tip_and_stale_external_anchor_rejected(self):
        ckpts,a,n=self.data()
        with self.assertRaisesRegex(CasIntentDenied,"MST_CAS_STALE_EXTERNAL_TIP"):
            prepare(ckpts,n,a,tip="0"*64)
        a["tip_checkpoint_sha256"]="f"*64
        with self.assertRaisesRegex(CasIntentDenied,"MST_CAS_STALE_EXTERNAL_TIP"):
            prepare(ckpts,n,a)

    def test_unchanged_anchor_but_wrong_generation_denied(self):
        ckpts,a,n=self.data()
        a["generation"]=4
        with self.assertRaisesRegex(
            CasIntentDenied,"MST_CAS_ANCHOR_SEQUENCE_OR_IDENTITY_DRIFT"
        ):
            prepare(ckpts,n,a)

    def test_altered_signed_new_head_and_previous_tip_denied(self):
        ckpts,a,n=self.data()
        for field,value in (
            ("previous_checkpoint_sha256","f"*64),
            ("series_id","FORGED_FAKE_SERIES"),
            ("sequence",5),
            ("signals_eligible",True),
        ):
            bad=deepcopy(n)
            bad["body"][field]=value
            with self.subTest(field=field),self.assertRaisesRegex(
                CasIntentDenied,"MST_CAS_SIGNED_SUCCESSOR_INVALID"
            ):
                prepare(ckpts,bad,a)

    def test_replay_existing_signed_checkpoint_as_successor_denied(self):
        ckpts,a,n=self.data()
        with self.assertRaisesRegex(
            CasIntentDenied,"MST_CAS_SIGNED_SUCCESSOR_INVALID"
        ):
            prepare(ckpts,ckpts[-1],a)

    def test_forged_prepared_intent_changes_never_accepted(self):
        ckpts,a,n=self.data()
        original=prepare(ckpts,n,a)
        for fld,val in (
            ("expected_revision",13),
            ("proposed_revision",19),
            ("external_atomic_cas_required",False),
            ("published",True),
            ("signals_eligible",True),
            ("request_id","FAKE_ANOTHER_REQUEST_9"),
        ):
            with self.subTest(field=fld):
                bad=dict(original,**{fld:val})
                with self.assertRaisesRegex(
                    CasIntentDenied,"MST_CAS_PREPARED_INTENT_INTEGRITY_INVALID"
                ):
                    verify_pre_submit_snapshot(bad,observed_external_anchor=a)
        bad=dict(original,superfluous="FAKE")
        with self.assertRaisesRegex(
            CasIntentDenied,"MST_CAS_PREPARED_INTENT_INVALID"
        ):
            verify_pre_submit_snapshot(bad,observed_external_anchor=a)

    def test_invalid_snapshot_identity_and_types_rejected(self):
        ckpts,a,n=self.data()
        for field,value in (
            ("revision",True),
            ("generation",True),
            ("head_pin",["D1"]),
            ("tip_checkpoint_sha256","INVALID"),
            ("series_id",["FAKE"]),
        ):
            with self.subTest(field=field):
                changed=dict(a,**{field:value})
                with self.assertRaises(CasIntentDenied):
                    prepare(ckpts,n,changed)

    def test_invalid_request_identity_and_oversized_limits_rejected(self):
        ckpts,a,n=self.data()
        for request in ("INVALID","!",None,{"fake":1}):
            with self.subTest(request=str(request)),self.assertRaises(
                CasIntentDenied
            ):
                prepare(ckpts,n,a,request_id=request)
        for field,value in (("revision",2**63-1),("generation",1_000_000_000)):
            with self.subTest(field=field),self.assertRaises(CasIntentDenied):
                prepare(ckpts,n,dict(a,**{field:value}))

    def test_retry_after_another_successful_writer_must_reprepare(self):
        ckpts,a,n1=self.data()
        n2=proposed(ckpts,run="43270010005")
        store=FakeAuthoritativeAtomicStore(a)
        i1=prepare(ckpts,n1,store.read())
        i2=prepare(ckpts,n2,store.read(),request_id="FAKE_OTHER_REQUEST_2026")
        self.assertTrue(store.atomic_compare_and_swap(i1))
        self.assertFalse(store.atomic_compare_and_swap(i2))
        # Rebuild against actual winning history (requires a new signed
        # successor to the winner; cannot recycle signed loser checkpoint).
        with self.assertRaisesRegex(CasIntentDenied,"STALE_EXTERNAL_TIP"):
            prepare(ckpts,n2,store.read(),request_id="FAKE_OTHER_REQUEST_2026")
        new_chain=[*ckpts,n1]
        next_after_winner=proposed(new_chain,run="43270010006")
        prepared=prepare(
            new_chain,next_after_winner,store.read(),
            request_id="FAKE_THIRD_REQUEST_2026",
        )
        self.assertTrue(store.atomic_compare_and_swap(prepared))
        self.assertEqual(store.commits,2)
        self.assertEqual(store.read()["generation"],5)


if __name__=="__main__":
    unittest.main()
