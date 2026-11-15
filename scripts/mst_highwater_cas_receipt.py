"""§198 Signed *claim* of independent CAS, receipt/readback diagnostics.

A signed receipt may prove WHO signed a claim only if its Ed25519 key has an
independently authenticated owner-controlled trust root. Even a valid
signature does NOT prove the storage backend really used atomic CAS, that
the trust root is independent, or that the store is immutable/monotone.
This is pure read-only verification: no HTTP, IAM, source write, signer,
production publisher, or broker action.
"""
from __future__ import annotations

import base64
import binascii
from hashlib import sha256
import json
import re
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from scripts.mst_highwater_cas_intent import (
    CasIntentDenied, _anchor, verify_pre_submit_snapshot,
)

SCHEMA="mst.cloud.cas_commit_receipt_candidate.v0.1"
BODY_SCHEMA="mst.cloud.cas_commit_receipt_claim.v0.1"
RECEIPT_FIELDS=frozenset(("schema","key_id","body","signature_b64"))
BODY_FIELDS=frozenset((
    "schema","repository","series_id","request_id","intent_sha256",
    "previous_receipt_sha256","previous_fence","committed_fence",
    "expected_generation","committed_generation",
    "expected_revision","committed_revision",
    "expected_tip_checkpoint_sha256","committed_tip_checkpoint_sha256",
    "expected_head_pin","committed_head_pin",
    "atomic_cas_reported","publisher_activated","signals_eligible",
))
KEY_ID=re.compile(r"[A-Za-z0-9_-]{8,80}\Z")
SHA=re.compile(r"[0-9a-f]{64}\Z")
MAX_FENCE=2**63-1
MAX_RECEIPT_BYTES=4096


class CasReceiptDenied(ValueError):
    """Fixed error codes only; never log tokens, prices, keys, signed bytes."""


def canonical(value: Any, *, limit: int) -> bytes:
    try:
        out=json.dumps(value,sort_keys=True,separators=(",",":"),
                       ensure_ascii=True,allow_nan=False).encode("utf-8")
    except (TypeError,ValueError,OverflowError):
        raise CasReceiptDenied("MST_CAS_RECEIPT_JSON_INVALID") from None
    if not 0<len(out)<=limit:
        raise CasReceiptDenied("MST_CAS_RECEIPT_SIZE_INVALID")
    return out


def receipt_sha256(receipt: Any) -> str:
    """SHA covers every signed envelope attribute. Not independent highwater."""
    return sha256(canonical(receipt,limit=MAX_RECEIPT_BYTES)).hexdigest()


def verify_cas_receipt_claim(
    *,
    prepared_intent: Any,
    originally_observed_anchor: Any,
    resulting_anchor_readback: Any,
    receipt: Any,
    original_intent_sha256: str,
    expected_previous_receipt_sha256: str | None,
    expected_previous_fence: int,
    trusted_backend_key_id: str,
    trusted_backend_public_key: bytes,
) -> dict[str, Any]:
    """Check exact full readback and an Ed25519 signed conditional-commit claim.

    The caller must provide separately authenticated signer identity, fence
    and latest expected receipt pin in a future production integration. None
    is established or fetched by this module.
    """
    if (type(trusted_backend_key_id) is not str
            or KEY_ID.fullmatch(trusted_backend_key_id) is None
            or type(trusted_backend_public_key) is not bytes
            or len(trusted_backend_public_key)!=32
            or type(expected_previous_fence) is not int
            or not 0<=expected_previous_fence<MAX_FENCE
            or (expected_previous_receipt_sha256 is not None
                and (type(expected_previous_receipt_sha256) is not str
                     or SHA.fullmatch(expected_previous_receipt_sha256)
                     is None))
            or (expected_previous_fence==0)
               !=(expected_previous_receipt_sha256 is None)):
        raise CasReceiptDenied("MST_CAS_RECEIPT_EXTERNAL_TRUST_INPUT_INVALID")
    try:
        verify_pre_submit_snapshot(
            prepared_intent,
            observed_external_anchor=originally_observed_anchor,
            expected_prepared_intent_sha256=original_intent_sha256,
        )
        previous=_anchor(originally_observed_anchor)
        updated=_anchor(resulting_anchor_readback)
    except CasIntentDenied:
        raise CasReceiptDenied("MST_CAS_RECEIPT_ANCHOR_OR_INTENT_INVALID") from None
    if (type(receipt) is not dict or set(receipt)!=RECEIPT_FIELDS
            or receipt["schema"]!=SCHEMA
            or receipt["key_id"]!=trusted_backend_key_id
            or type(receipt["signature_b64"]) is not str
            or len(receipt["signature_b64"])!=88):
        raise CasReceiptDenied("MST_CAS_RECEIPT_ENVELOPE_INVALID")
    try:
        signature=base64.b64decode(receipt["signature_b64"],validate=True)
        if (len(signature)!=64
                or base64.b64encode(signature).decode()
                   !=receipt["signature_b64"]):
            raise ValueError()
    except (ValueError,binascii.Error):
        raise CasReceiptDenied("MST_CAS_RECEIPT_SIGNATURE_ENCODING_INVALID") from None
    body=receipt["body"]
    if type(body) is not dict or set(body)!=BODY_FIELDS:
        raise CasReceiptDenied("MST_CAS_RECEIPT_BODY_FIELDS_INVALID")
    if (body["schema"]!=BODY_SCHEMA
            or body["repository"]!="ngluonghoa/MST"
            or body["atomic_cas_reported"] is not True
            or body["publisher_activated"] is not False
            or body["signals_eligible"] is not False
            or type(body["previous_fence"]) is not int
            or type(body["committed_fence"]) is not int
            or body["previous_fence"]!=expected_previous_fence
            or body["committed_fence"]!=expected_previous_fence+1
            or body["previous_receipt_sha256"]
               !=expected_previous_receipt_sha256):
        raise CasReceiptDenied("MST_CAS_RECEIPT_CLAIMS_INVALID")
    comparisons=(
        ("series_id","series_id","series_id"),
        ("request_id","request_id",None),
        ("intent_sha256","intent_sha256",None),
        ("expected_generation","observed_generation","generation"),
        ("committed_generation","proposed_generation",None),
        ("expected_revision","expected_revision","revision"),
        ("committed_revision","proposed_revision",None),
        ("expected_tip_checkpoint_sha256",
         "expected_tip_checkpoint_sha256","tip_checkpoint_sha256"),
        ("committed_tip_checkpoint_sha256",
         "proposed_tip_checkpoint_sha256",None),
        ("expected_head_pin","expected_head_pin","head_pin"),
        ("committed_head_pin","proposed_head_pin",None),
    )
    for receipt_key,intent_key,anchor_key in comparisons:
        value=body[receipt_key]
        if (type(value) is not type(prepared_intent[intent_key])
                or value!=prepared_intent[intent_key]
                or (anchor_key is not None and value!=previous[anchor_key])):
            raise CasReceiptDenied("MST_CAS_RECEIPT_REQUEST_MISMATCH")
    if (body["committed_generation"]!=updated["generation"]
            or body["committed_revision"]!=updated["revision"]
            or body["committed_tip_checkpoint_sha256"]
               !=updated["tip_checkpoint_sha256"]
            or body["committed_head_pin"]!=updated["head_pin"]
            or body["series_id"]!=updated["series_id"]):
        raise CasReceiptDenied("MST_CAS_RECEIPT_READBACK_MISMATCH")
    try:
        Ed25519PublicKey.from_public_bytes(trusted_backend_public_key).verify(
            signature,canonical(body,limit=3072),
        )
    except (InvalidSignature,ValueError,TypeError):
        raise CasReceiptDenied("MST_CAS_RECEIPT_SIGNATURE_INVALID") from None
    return {
        "schema":"mst.cloud.cas_receipt_diagnostic.v0.1",
        "receipt_sha256":receipt_sha256(receipt),
        "observed_fence":body["committed_fence"],
        "generation":updated["generation"],
        "revision":updated["revision"],
        "ed25519_valid_for_supplied_backend_key":True,
        "readback_matches_signed_claim":True,
        "independent_backend_key_authenticated":False,
        "atomic_cas_independently_proven":False,
        "immutable_monotone_receipt_ledger_verified":False,
        "publisher_activated":False,
        "cache_published":False,
        "signals_eligible":False,
    }


def verify_cas_receipt_claim_chain(
    entries: Any, *,
    expected_start_receipt_sha256: str | None,
    expected_start_fence: int,
    expected_tip_receipt_sha256: str,
    trusted_backend_key_id: str,
    trusted_backend_public_key: bytes,
) -> dict[str, Any]:
    """Bounded complete claimed-CAS chain; still not a trusted monotone store.

    Each entry holds intent, originally observed anchor, resulting readback,
    original-intent SHA and signed receipt. Missing/duplicated intermediate
    receipts, reset fences, stale tip and replays fail closed.
    """
    if (type(entries) is not list or not 1<=len(entries)<=128
            or type(expected_tip_receipt_sha256) is not str
            or SHA.fullmatch(expected_tip_receipt_sha256) is None):
        raise CasReceiptDenied("MST_CAS_RECEIPT_CHAIN_INPUT_INVALID")
    previous_sha=expected_start_receipt_sha256
    previous_fence=expected_start_fence
    previous_after=None
    seen_request_ids: set[str]=set()
    for item in entries:
        if (type(item) is not dict
                or set(item)!={
                    "prepared_intent","before_anchor","after_anchor",
                    "original_intent_sha256","receipt"
                }):
            raise CasReceiptDenied("MST_CAS_RECEIPT_CHAIN_ENTRY_INVALID")
        if previous_after is not None and item["before_anchor"]!=previous_after:
            raise CasReceiptDenied("MST_CAS_RECEIPT_CHAIN_ANCHOR_GAP")
        result=verify_cas_receipt_claim(
            prepared_intent=item["prepared_intent"],
            originally_observed_anchor=item["before_anchor"],
            resulting_anchor_readback=item["after_anchor"],
            receipt=item["receipt"],
            original_intent_sha256=item["original_intent_sha256"],
            expected_previous_receipt_sha256=previous_sha,
            expected_previous_fence=previous_fence,
            trusted_backend_key_id=trusted_backend_key_id,
            trusted_backend_public_key=trusted_backend_public_key,
        )
        request_id=item["receipt"]["body"]["request_id"]
        if request_id in seen_request_ids:
            raise CasReceiptDenied("MST_CAS_RECEIPT_CHAIN_REPLAYED_REQUEST_ID")
        seen_request_ids.add(request_id)
        previous_fence=result["observed_fence"]
        previous_sha=result["receipt_sha256"]
        previous_after=item["after_anchor"]
    if previous_sha!=expected_tip_receipt_sha256:
        raise CasReceiptDenied("MST_CAS_RECEIPT_CHAIN_TIP_MISMATCH")
    return {
        "schema":"mst.cloud.cas_receipt_chain_diagnostic.v0.1",
        "verified_signed_claim_count":len(entries),
        "linked_claim_edges":len(entries)-1,
        "supplied_expected_tip_sha256_matched":True,
        "last_claimed_fence":previous_fence,
        "owner_trust_root_verified":False,
        "independent_atomic_storage_proven":False,
        "append_only_ledger_independently_verified":False,
        "production_cache_published":False,
        "signals_eligible":False,
    }
