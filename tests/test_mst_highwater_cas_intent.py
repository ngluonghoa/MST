"""§246 synthetic signed CAS *intent* only: no remote atomic write."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from scripts import mst_highwater_cas_intent as m
from scripts.mst_signed_highwater_diagnostic import checkpoint_digest
from test_mst_signed_highwater_diagnostic import (
    PUBLIC, KEY_ID, genesis, successor, SERIES, pin,
)

REQUEST = "FAKE_OWNER_CAS_REQUEST_0001"


def examples():
    old = genesis()
    new = successor(old, 2)
    anchor = {
        "schema": m.ANCHOR_SCHEMA,
        "series_id": SERIES, "generation": 1,
        "tip_checkpoint_sha256": checkpoint_digest(old),
        "head_pin": deepcopy(old["body"]["head_pin"]),
        "revision": 9,
    }
    return old, new, anchor


def prepare(*, old=None, new=None, anchor=None, tip=None, req=REQUEST):
    a, b, current = examples()
    if old is not None:
        a=old
    if new is not None:
        b=new
    if anchor is not None:
        current=anchor
    return m.prepare_highwater_conditional_write(
        current_signed_chain=[a],
        proposed_signed_checkpoint=b,
        observed_external_anchor=current,
        trusted_key_id=KEY_ID,
        trusted_ed25519_public_key=PUBLIC,
        expected_current_tip=checkpoint_digest(a) if tip is None else tip,
        request_id=req,
    )


class SignedCasIntent246(unittest.TestCase):
    def test_prepare_and_reread_are_explicitly_not_a_cas(self):
        old, new, anchor=examples()
        intent=prepare(old=old,new=new,anchor=anchor)
        self.assertEqual(intent["schema"],m.INTENT_SCHEMA)
        self.assertEqual(intent["observed_generation"],1)
        self.assertEqual(intent["proposed_generation"],2)
        self.assertEqual(intent["expected_revision"],9)
        self.assertEqual(intent["proposed_revision"],10)
        self.assertEqual(intent["expected_tip_checkpoint_sha256"],checkpoint_digest(old))
        self.assertEqual(intent["proposed_tip_checkpoint_sha256"],checkpoint_digest(new))
        self.assertEqual(intent["expected_head_pin"],old["body"]["head_pin"])
        self.assertEqual(intent["proposed_head_pin"],new["body"]["head_pin"])
        self.assertIs(intent["external_atomic_cas_required"],True)
        self.assertIs(intent["published"],False)
        self.assertIs(intent["signals_eligible"],False)
        receipt=m.verify_pre_submit_snapshot(
            intent,observed_external_anchor=anchor,
            expected_prepared_intent_sha256=intent["intent_sha256"]
        )
        self.assertIs(receipt["external_store_atomic_cas_executed"],False)
        self.assertIs(receipt["owner_trust_anchor_verified"],False)
        self.assertIs(receipt["production_cache_published"],False)
        self.assertIs(receipt["signals_eligible"],False)

    def test_deterministic_replay_same_intent_and_exact_digest(self):
        p=prepare()
        q=prepare()
        self.assertEqual(p,q)
        self.assertEqual(m._digest({k:v for k,v in p.items()
                                    if k!="intent_sha256"}),p["intent_sha256"])

    def test_old_external_tip_changed_or_stale_denied(self):
        for key,value in (
            ("tip_checkpoint_sha256","0"*64),
            ("generation",2),
            ("series_id","OTHER_SERIES_1"),
            ("head_pin",pin(99)),
        ):
            old, new, anchor=examples()
            anchor[key]=value
            with self.subTest(key=key),self.assertRaises(m.CasIntentDenied):
                prepare(old=old,new=new,anchor=anchor)

    def test_expected_tip_not_matching_observed_chain(self):
        with self.assertRaisesRegex(m.CasIntentDenied,"STALE_EXTERNAL_TIP"):
            prepare(tip="a"*64)

    def test_proposed_checkpoint_with_forged_signature_denied(self):
        old, new, anchor=examples()
        new["body"]["head_pin"]["source_sha256"]="f"*64
        with self.assertRaisesRegex(m.CasIntentDenied,"SIGNED_SUCCESSOR_INVALID"):
            prepare(old=old,new=new,anchor=anchor)

    def test_proposed_wrong_series_or_reused_run_denied(self):
        old, new, anchor=examples()
        for wrong in (
            successor(old,2,series_id="OTHER_SERIES_1"),
            successor(old,2,head_pin=pin(1, file_id="DifferentOwnerFile1234")),
            successor(old,3),
        ):
            with self.subTest(seq=wrong["body"]["sequence"]),self.assertRaises(m.CasIntentDenied):
                prepare(old=old,new=wrong,anchor=anchor)

    def test_reject_non_genesis_untrusted_current_chain(self):
        old, new, anchor=examples()
        tampered=deepcopy(old)
        tampered["body"]["sequence"]=2
        # Keep the fake *observed* tip consistent so the signature-check
        # path, rather than the earlier stale-tip guard, is exercised.
        anchor["tip_checkpoint_sha256"]=checkpoint_digest(tampered)
        anchor["generation"]=2
        with self.assertRaisesRegex(m.CasIntentDenied,"SIGNED_SUCCESSOR_INVALID"):
            prepare(old=tampered,new=new,anchor=anchor,
                    tip=checkpoint_digest(tampered))

    def test_reject_generation_or_revision_rollback_and_bool(self):
        for key,value in (
            ("generation",True),("generation",0),("generation",1_000_000_000),
            ("revision",False),("revision",0),("revision",2**63),
        ):
            old,new,anchor=examples()
            anchor[key]=value
            with self.subTest(key=key),self.assertRaises(m.CasIntentDenied):
                prepare(old=old,new=new,anchor=anchor)

    def test_missing_and_invalid_request_id_denied(self):
        for request in ("", "short", "oops space", True, "a"*81):
            with self.subTest(request=request),self.assertRaisesRegex(
                m.CasIntentDenied,"PREPARE_INPUT_INVALID"
            ):
                prepare(req=request)

    def test_mutated_intent_is_not_accepted_on_reread(self):
        a=prepare()
        old,new,anchor=examples()
        for key,value in (
            ("proposed_generation",99),("expected_revision",10),
            ("proposed_revision",12),("signals_eligible",True),
            ("published",True),("external_atomic_cas_required",False),
            ("proposed_head_pin",pin(8)),
        ):
            bad=deepcopy(a)
            bad[key]=value
            with self.subTest(key=key),self.assertRaises(m.CasIntentDenied):
                m.verify_pre_submit_snapshot(
                    bad,observed_external_anchor=anchor,
                    expected_prepared_intent_sha256=a["intent_sha256"],
                )

    def test_reseal_modified_intent_but_external_pinned_digest_blocks(self):
        intent=prepare()
        old,new,anchor=examples()
        bad=deepcopy(intent)
        bad["proposed_head_pin"]=pin(80)
        bad["intent_sha256"]=m._digest({
            k:v for k,v in bad.items() if k!="intent_sha256"
        })
        with self.assertRaisesRegex(m.CasIntentDenied,"PREPARED_INTENT_REPLACED"):
            m.verify_pre_submit_snapshot(
                bad,observed_external_anchor=anchor,
                expected_prepared_intent_sha256=intent["intent_sha256"],
            )

    def test_external_anchor_drift_after_prepare_rejects_reread(self):
        intent=prepare()
        _,_,anchor=examples()
        for key,value in (
            ("revision",10),("tip_checkpoint_sha256","f"*64),
            ("head_pin",pin(91)),("generation",2),("series_id","OTHER_SERIES_1"),
        ):
            changed=deepcopy(anchor)
            changed[key]=value
            with self.subTest(key=key),self.assertRaises(m.CasIntentDenied):
                m.verify_pre_submit_snapshot(
                    intent,observed_external_anchor=changed,
                    expected_prepared_intent_sha256=intent["intent_sha256"],
                )

    def test_two_competing_offline_writers_get_same_intent_but_no_real_lock(self):
        old,new,anchor=examples()
        x=prepare(old=old,new=new,anchor=anchor)
        y=prepare(old=old,new=new,anchor=anchor)
        self.assertEqual(x,y)
        # Repeated exact snapshot is not independent atomic fencing.
        for prepared in (x,y):
            reply=m.verify_pre_submit_snapshot(
                prepared,observed_external_anchor=anchor,
                expected_prepared_intent_sha256=x["intent_sha256"],
            )
            self.assertFalse(reply["external_store_atomic_cas_executed"])

    def test_wrong_field_set_or_replaced_digest_denied(self):
        intent=prepare()
        _,_,anchor=examples()
        bad=deepcopy(intent)
        bad["sign_and_publish"]=True
        with self.assertRaisesRegex(m.CasIntentDenied,"PREPARED_INTENT_INVALID"):
            m.verify_pre_submit_snapshot(
                bad,observed_external_anchor=anchor,
                expected_prepared_intent_sha256=intent["intent_sha256"]
            )
        with self.assertRaisesRegex(m.CasIntentDenied,"PREPARED_INTENT_REPLACED"):
            m.verify_pre_submit_snapshot(
                intent,observed_external_anchor=anchor,
                expected_prepared_intent_sha256="a"*64
            )

    def test_no_network_or_actual_signing_or_publisher(self):
        source=(Path(__file__).resolve().parents[1] /
                "scripts/mst_highwater_cas_intent.py").read_text()
        for forbidden in (
            "Ed25519PrivateKey", "requests", "urllib.request",
            "session.post", "session.patch", "update_ref",
            "os.environ", "MST_TRADE_ORDER",
        ):
            self.assertNotIn(forbidden, source)


if __name__=="__main__":
    unittest.main()
