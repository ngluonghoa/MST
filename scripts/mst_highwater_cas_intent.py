"""§197 PREPARE-ONLY monotone highwater CAS request contract.

A cryptographic checkpoint verifier does NOT make Google Drive CAS-atomic.
This module prepares a deterministic conditional-write *intent* from a
trusted-by-caller anchor snapshot and a complete signed checkpoint chain.
The anchor, public key, tip, readbacks, and atomic compare-and-swap service
MUST be independently authenticated. No I/O, secrets, signer, publisher,
checkpoints uploaded, or trading. A pre-submit reread narrows stale reads
but is NOT atomic fencing; only an external atomic CAS primitive can be.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Mapping

from scripts.mst_signed_highwater_diagnostic import (
    HighwaterDenied, checkpoint_digest, verify_signed_highwater_candidates,
    _pin,
)


def _proof(value: Any, label: str) -> dict[str, str]:
    # Exact six-field source CHUNK pin contract from isolated §245 verifier.
    return _pin(value, label=label)

ANCHOR_SCHEMA = "mst.private.external_highwater_snapshot_candidate.v0.1"
INTENT_SCHEMA = "mst.private.highwater_conditional_write_intent.v0.1"
SCOPE_FIELDS = ("provider", "symbol", "native_tf")
ANCHOR_FIELDS = frozenset((
    "schema","series_id","generation","tip_checkpoint_sha256",
    "head_pin","revision",
))
INTENT_FIELDS = frozenset((
    "schema","series_id","observed_generation","proposed_generation",
    "expected_tip_checkpoint_sha256","proposed_tip_checkpoint_sha256",
    "expected_revision","proposed_revision","expected_head_pin",
    "proposed_head_pin","request_id","intent_sha256",
    "external_atomic_cas_required","published","signals_eligible",
))
SERIES = re.compile(r"[A-Za-z0-9_-]{8,80}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
REQUEST = re.compile(r"[A-Za-z0-9_-]{12,80}\Z")
MAX_GENERATION = 1_000_000_000
MAX_REVISION = 2**63-2


class CasIntentDenied(ValueError):
    """Never leak signed bytes, credentials, keys, or native market prices."""


def _digest(value: Mapping[str, Any]) -> str:
    try:
        content=json.dumps(
            value, sort_keys=True, separators=(",",":"),
            ensure_ascii=True, allow_nan=False,
        ).encode("utf-8")
    except (ValueError, TypeError, OverflowError):
        raise CasIntentDenied("MST_CAS_INTENT_CANONICAL_INVALID") from None
    if not 0 < len(content) <= 2048:
        raise CasIntentDenied("MST_CAS_INTENT_SIZE_INVALID")
    return sha256(content).hexdigest()


def _anchor(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != ANCHOR_FIELDS:
        raise CasIntentDenied("MST_CAS_ANCHOR_SCHEMA_INVALID")
    try:
        pin=_proof(value["head_pin"], "HEAD")
    except (HighwaterDenied, ValueError):
        raise CasIntentDenied("MST_CAS_ANCHOR_PIN_INVALID") from None
    if (value["schema"] != ANCHOR_SCHEMA
            or type(value["series_id"]) is not str
            or SERIES.fullmatch(value["series_id"]) is None
            or type(value["generation"]) is not int
            or not 1 <= value["generation"] < MAX_GENERATION
            or type(value["revision"]) is not int
            or not 1 <= value["revision"] <= MAX_REVISION
            or type(value["tip_checkpoint_sha256"]) is not str
            or SHA.fullmatch(value["tip_checkpoint_sha256"]) is None
            or type(pin) is not dict):
        raise CasIntentDenied("MST_CAS_ANCHOR_VALUE_INVALID")
    return value


def _same_anchor(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    return all(a[k] == b[k] for k in ANCHOR_FIELDS)


def prepare_highwater_conditional_write(
    *, current_signed_chain: Any, proposed_signed_checkpoint: Any,
    observed_external_anchor: Any, trusted_key_id: str,
    trusted_ed25519_public_key: bytes, expected_current_tip: str,
    request_id: str,
) -> dict[str, Any]:
    """Build exact, idempotent compare-and-swap intent; NEVER execute it.

    The proposed signed checkpoint is verified by cryptographic rechecking of
    the ENTIRE genesis-to-proposal chain, then bound to the observed anchor.
    This routine cannot prove independent key/pin trust or execute CAS.
    """
    if (type(current_signed_chain) is not list
            or not 1 <= len(current_signed_chain) < 128
            or type(proposed_signed_checkpoint) is not dict
            or type(request_id) is not str
            or REQUEST.fullmatch(request_id) is None):
        raise CasIntentDenied("MST_CAS_PREPARE_INPUT_INVALID")
    anchor=_anchor(observed_external_anchor)
    if (type(expected_current_tip) is not str
            or SHA.fullmatch(expected_current_tip) is None):
        raise CasIntentDenied("MST_CAS_EXPECTED_TIP_INVALID")
    last=current_signed_chain[-1]
    try:
        old_digest=checkpoint_digest(last)
        new_digest=checkpoint_digest(proposed_signed_checkpoint)
    except HighwaterDenied:
        raise CasIntentDenied("MST_CAS_CHECKPOINT_ENCODING_INVALID") from None
    if (old_digest != expected_current_tip
            or anchor["tip_checkpoint_sha256"] != expected_current_tip):
        raise CasIntentDenied("MST_CAS_STALE_EXTERNAL_TIP")
    try:
        # Full-chain reverify prevents comparing a standalone signed but
        # unlinked foreign proposal against a locally supplied old tip.
        verify_signed_highwater_candidates(
            [*current_signed_chain, proposed_signed_checkpoint],
            trusted_key_id=trusted_key_id,
            trusted_ed25519_public_key=trusted_ed25519_public_key,
            expected_tip_checkpoint_sha256=new_digest,
        )
    except HighwaterDenied:
        raise CasIntentDenied("MST_CAS_SIGNED_SUCCESSOR_INVALID") from None
    old_body=last["body"]
    new_body=proposed_signed_checkpoint["body"]
    if (anchor["series_id"] != old_body["series_id"]
            or anchor["generation"] != old_body["sequence"]
            or anchor["head_pin"] != old_body["head_pin"]
            or new_body["series_id"] != anchor["series_id"]
            or new_body["sequence"] != anchor["generation"] + 1
            or new_body["previous_checkpoint_sha256"] != old_digest
            or new_body["previous_head_pin"] != anchor["head_pin"]
            or anchor["revision"] >= MAX_REVISION):
        raise CasIntentDenied("MST_CAS_ANCHOR_SEQUENCE_OR_IDENTITY_DRIFT")
    body={
        "schema":INTENT_SCHEMA,
        "series_id":anchor["series_id"],
        "observed_generation":anchor["generation"],
        "proposed_generation":anchor["generation"]+1,
        "expected_tip_checkpoint_sha256":old_digest,
        "proposed_tip_checkpoint_sha256":new_digest,
        "expected_revision":anchor["revision"],
        "proposed_revision":anchor["revision"]+1,
        "expected_head_pin":old_body["head_pin"],
        "proposed_head_pin":new_body["head_pin"],
        "request_id":request_id,
        "external_atomic_cas_required":True,
        "published":False,
        "signals_eligible":False,
    }
    digest=_digest(body)
    return {**body,"intent_sha256":digest}


def verify_pre_submit_snapshot(
    prepared_intent: Any, *, observed_external_anchor: Any,
    expected_prepared_intent_sha256: str,
) -> dict[str, Any]:
    """Fail closed when the reread differs, but NEVER call this atomic CAS.

    The caller binds this reread to its EXACT originally prepared intent
    digest. A malicious store could still show the same stale anchor to two
    writers. Identical snapshots don't authorize unconditional write: a
    separately controlled storage CAS primitive must perform atomic compare.
    """
    if (type(prepared_intent) is not dict
            or set(prepared_intent) != INTENT_FIELDS):
        raise CasIntentDenied("MST_CAS_PREPARED_INTENT_INVALID")
    unsigned={k:v for k,v in prepared_intent.items() if k!="intent_sha256"}
    if (type(expected_prepared_intent_sha256) is not str
            or SHA.fullmatch(expected_prepared_intent_sha256) is None
            or expected_prepared_intent_sha256 != prepared_intent["intent_sha256"]):
        raise CasIntentDenied("MST_CAS_PREPARED_INTENT_REPLACED")
    if (type(prepared_intent["intent_sha256"]) is not str
            or SHA.fullmatch(prepared_intent["intent_sha256"]) is None
            or prepared_intent["intent_sha256"] != _digest(unsigned)
            or prepared_intent["schema"] != INTENT_SCHEMA
            or prepared_intent["external_atomic_cas_required"] is not True
            or prepared_intent["published"] is not False
            or prepared_intent["signals_eligible"] is not False):
        raise CasIntentDenied("MST_CAS_PREPARED_INTENT_INTEGRITY_INVALID")
    current=_anchor(observed_external_anchor)
    if (prepared_intent["series_id"] != current["series_id"]
            or prepared_intent["expected_revision"] != current["revision"]
            or prepared_intent["observed_generation"] != current["generation"]
            or prepared_intent["expected_tip_checkpoint_sha256"]
               != current["tip_checkpoint_sha256"]
            or prepared_intent["expected_head_pin"] != current["head_pin"]
            or prepared_intent["proposed_generation"]
               != current["generation"]+1
            or prepared_intent["proposed_revision"]
               != current["revision"]+1):
        raise CasIntentDenied("MST_CAS_STALE_OR_CHANGED_SNAPSHOT")
    return {
        "schema":"mst.private.pre_submit_cas_diagnostic.v0.1",
        "observed_generation":current["generation"],
        "observed_revision":current["revision"],
        "expected_tip_match":True,
        "prepared_intent_sha256":prepared_intent["intent_sha256"],
        "external_store_atomic_cas_executed":False,
        "owner_trust_anchor_verified":False,
        "production_cache_published":False,
        "signals_eligible":False,
    }
