"""§196 Read-only Ed25519 signed source-highwater candidate diagnostics.

Cryptographically verify a proposed append-only chain of checkpoint
*records* using an explicitly supplied external public key. A test fixture
public key / tip digest is NOT a trusted owner-managed signer or independent
immutable anchor. This module never signs, writes files, publishes a Cache
head, executes CAS, queries providers, or activates trading.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from scripts.mst_private_source_chain_diagnostic import (
    LineageDenied, _proof, verify_private_source_chain,
)

CHECKPOINT_SCHEMA = "mst.private.signed_highwater_candidate.v0.1"
BODY_SCHEMA = "mst.private.highwater_candidate_body.v0.1"
MAX_CHECKPOINTS = 128
MAX_ENVELOPE_BYTES = 4096
KEY_RE = re.compile(r"[A-Za-z0-9_-]{8,80}")
SHA_RE = re.compile(r"[0-9a-f]{64}")
ENVELOPE_FIELDS = frozenset(("schema", "key_id", "body", "signature_b64"))
BODY_FIELDS = frozenset((
    "schema", "repository", "series_id", "sequence",
    "previous_checkpoint_sha256", "previous_head_pin", "head_pin",
    "source_finality_attested", "publisher_cas_executed",
    "source_licensed_for_storage_attested", "signals_eligible",
))
SERIES_RE = re.compile(r"[A-Za-z0-9_-]{8,80}")


class HighwaterDenied(ValueError):
    """Never include raw OHLCV, signatures, keys or candidate bytes in errors."""


def _canonical(data: Any, *, max_bytes: int) -> bytes:
    try:
        raw = json.dumps(
            data, sort_keys=True, separators=(",", ":"),
            allow_nan=False, ensure_ascii=True,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError):
        raise HighwaterDenied("MST_HIGHWATER_CANONICAL_JSON_REQUIRED") from None
    if not 0 < len(raw) <= max_bytes:
        raise HighwaterDenied("MST_HIGHWATER_CANONICAL_BYTES_BOUNDED")
    return raw


def checkpoint_digest(envelope: Any) -> str:
    """Envelope SHA-256 including signature, never signed independently."""
    return hashlib.sha256(_canonical(
        envelope, max_bytes=MAX_ENVELOPE_BYTES
    )).hexdigest()


def _validate_envelope(envelope: Any, key_id: str) -> dict[str, Any]:
    if (type(envelope) is not dict
            or set(envelope) != ENVELOPE_FIELDS
            or envelope["schema"] != CHECKPOINT_SCHEMA
            or envelope["key_id"] != key_id
            or type(envelope["signature_b64"]) is not str
            or len(envelope["signature_b64"]) != 88):
        raise HighwaterDenied("MST_HIGHWATER_ENVELOPE_INVALID")
    try:
        signature = base64.b64decode(
            envelope["signature_b64"], validate=True
        )
        if (len(signature) != 64 or
                base64.b64encode(signature).decode("ascii")
                != envelope["signature_b64"]):
            raise ValueError()
    except (ValueError, binascii.Error):
        raise HighwaterDenied("MST_HIGHWATER_SIGNATURE_ENCODING_INVALID") from None
    body = envelope["body"]
    if type(body) is not dict or set(body) != BODY_FIELDS:
        raise HighwaterDenied("MST_HIGHWATER_BODY_FIELD_SET_INVALID")
    if (body["schema"] != BODY_SCHEMA
            or body["repository"] != "ngluonghoa/MST"
            or type(body["series_id"]) is not str
            or SERIES_RE.fullmatch(body["series_id"]) is None
            or type(body["sequence"]) is not int
            or not 1 <= body["sequence"] <= 1_000_000_000
            or any(body[k] is not False for k in (
                "source_finality_attested", "publisher_cas_executed",
                "source_licensed_for_storage_attested", "signals_eligible",
            ))):
        raise HighwaterDenied("MST_HIGHWATER_UNATTESTED_BODY_REQUIRED")
    try:
        _proof(body["head_pin"], "HEAD")
        if body["sequence"] == 1:
            if (body["previous_checkpoint_sha256"] is not None
                    or body["previous_head_pin"] is not None):
                raise ValueError("genesis cannot have prior")
        else:
            if (type(body["previous_checkpoint_sha256"]) is not str
                    or SHA_RE.fullmatch(body["previous_checkpoint_sha256"]) is None):
                raise ValueError("prior SHA missing")
            _proof(body["previous_head_pin"], "PRIOR")
    except (ValueError, LineageDenied):
        raise HighwaterDenied("MST_HIGHWATER_PREDECESSOR_FIELDS_INVALID") from None
    return {"body": body, "signature": signature}


def verify_signed_highwater_candidates(
    candidates: Any, *,
    trusted_key_id: str,
    trusted_ed25519_public_key: bytes,
    expected_tip_checkpoint_sha256: str,
) -> dict[str, Any]:
    """Verify each Ed25519 signature and complete genesis->tip link sequence.

    The public key and expected tip digest MUST eventually be authenticated
    out of band by an independent owner-managed trust boundary. This function
    deliberately does not certify their origin or perform highwater CAS.
    """
    if (type(trusted_key_id) is not str
            or KEY_RE.fullmatch(trusted_key_id) is None
            or type(trusted_ed25519_public_key) is not bytes
            or len(trusted_ed25519_public_key) != 32
            or type(expected_tip_checkpoint_sha256) is not str
            or SHA_RE.fullmatch(expected_tip_checkpoint_sha256) is None):
        raise HighwaterDenied("MST_HIGHWATER_EXTERNAL_TRUST_INPUT_INVALID")
    if type(candidates) is not list or not 1 <= len(candidates) <= MAX_CHECKPOINTS:
        raise HighwaterDenied("MST_HIGHWATER_CHECKPOINT_COUNT_INVALID")
    try:
        public = Ed25519PublicKey.from_public_bytes(trusted_ed25519_public_key)
    except (TypeError, ValueError):
        raise HighwaterDenied("MST_HIGHWATER_PUBLIC_KEY_INVALID") from None
    previous_digest = None
    previous_body = None
    results=[]
    for i, candidate in enumerate(candidates):
        verified = _validate_envelope(candidate, trusted_key_id)
        body, signature = verified["body"], verified["signature"]
        try:
            public.verify(signature, _canonical(body, max_bytes=2048))
        except (InvalidSignature, ValueError, TypeError):
            raise HighwaterDenied("MST_HIGHWATER_ED25519_SIGNATURE_INVALID") from None
        current_digest = checkpoint_digest(candidate)
        if body["sequence"] != i + 1:
            raise HighwaterDenied("MST_HIGHWATER_SEQUENCE_GAP_OR_ROLLBACK")
        if i > 0:
            assert previous_body is not None
            if (body["series_id"] != previous_body["series_id"]
                    or body["previous_checkpoint_sha256"] != previous_digest
                    or body["previous_head_pin"] != previous_body["head_pin"]
                    or any(body["head_pin"][k] != previous_body["head_pin"][k]
                           for k in ("provider","symbol","native_tf"))
                    or int(body["head_pin"]["run_id"])
                       <= int(previous_body["head_pin"]["run_id"])
                    or body["head_pin"]["file_id"]
                       == previous_body["head_pin"]["file_id"]):
                raise HighwaterDenied("MST_HIGHWATER_CHAIN_LINK_INVALID")
        previous_body = body
        previous_digest = current_digest
        results.append(body["head_pin"])
    if previous_digest != expected_tip_checkpoint_sha256:
        raise HighwaterDenied("MST_HIGHWATER_EXPECTED_TIP_MISMATCH")
    return {
        "schema":"mst.private.highwater_signature_diagnostic.v0.1",
        "checkpoint_count":len(results),
        "linked_checkpoint_edges":len(results)-1,
        "ed25519_signatures_valid_for_supplied_public_key":True,
        "expected_tip_digest_matched_supplied_pin":True,
        "candidate_scope": {
            k: results[0][k] for k in ("provider","symbol","native_tf")
        },
        "first_head_pin":results[0],
        "last_head_pin":results[-1],
        "independent_owner_signer_identity_verified":False,
        "external_tip_pin_independently_authenticated":False,
        "immutable_monotone_highwater_verified":False,
        "atomic_compare_and_swap_executed":False,
        "issuer_data_rights_or_source_finality_verified":False,
        "market_cache_published":False,
        "signal_eligible":False,
    }


def verify_signed_highwater_against_private_source_chain(
    source_records: Any, *, parent: str, complete_census_supplied: bool,
    candidates: Any, trusted_key_id: str,
    trusted_ed25519_public_key: bytes,
    expected_tip_checkpoint_sha256: str,
) -> dict[str, Any]:
    """Combine proposed Ed25519 highwater with §195 bounded source-chain QA.

    The method does not fetch Drive, authenticate census completeness, or
    promote any private source. It requires one signed checkpoint for each
    supplied source candidate, in a strict contiguous genesis->tip series.
    """
    signed = verify_signed_highwater_candidates(
        candidates, trusted_key_id=trusted_key_id,
        trusted_ed25519_public_key=trusted_ed25519_public_key,
        expected_tip_checkpoint_sha256=expected_tip_checkpoint_sha256,
    )
    if type(source_records) is not list or len(source_records) != signed["checkpoint_count"]:
        raise HighwaterDenied("MST_HIGHWATER_SOURCE_CARDINALITY_INVALID")
    # Stronger than checking only signed floor and tip: every intermediate
    # checkpoint head must match one actual supplied source file/body hash.
    signed_pins=[item["body"]["head_pin"] for item in candidates]
    seen: set[str]=set()
    for pin in signed_pins:
        if pin["file_id"] in seen:
            raise HighwaterDenied("MST_HIGHWATER_DUPLICATE_SIGNED_HEAD")
        seen.add(pin["file_id"])
    if any(type(rec) is not dict or rec.get("file_id") not in seen
           for rec in source_records):
        raise HighwaterDenied("MST_HIGHWATER_SOURCE_HEAD_CENSUS_MISMATCH")
    try:
        source = verify_private_source_chain(
            source_records, parent=parent,
            floor_pin=signed_pins[0],
            expected_head_pin=signed_pins[-1],
            complete_census_supplied=complete_census_supplied,
        )
    except (LineageDenied, ValueError, TypeError):
        raise HighwaterDenied("MST_HIGHWATER_PRIVATE_CHAIN_INVALID") from None
    # Confirm each signed intermediate matches exactly the source body
    # SHA + recorded GitHub run; other source validity is from §195.
    by_id={rec["file_id"]:rec for rec in source_records}
    for pin in signed_pins:
        rec=by_id[pin["file_id"]]
        props=rec["metadata"].get("appProperties",{})
        if (props.get("source_run_id") != pin["run_id"]
                or hashlib.sha256(rec["body"]).hexdigest()
                   != pin["source_sha256"]):
            raise HighwaterDenied("MST_HIGHWATER_INTERMEDIATE_PIN_MISMATCH")
    return {
        "schema":"mst.private.signed_source_chain_diagnostic.v0.1",
        "signatures_checked":signed["checkpoint_count"],
        "source_candidates_checked":source["candidate_count"],
        "chain_edges_checked":source["linked_edges_verified"],
        "ed25519_valid_for_supplied_public_key":True,
        "every_intermediate_pin_matches_candidate":True,
        "owner_signer_independently_authenticated":False,
        "independently_anchored_monotone_highwater_verified":False,
        "drive_census_independently_verified":False,
        "atomic_publish_cas_executed":False,
        "source_finality_verified":False,
        "cache_published":False,
        "signal_eligible":False,
    }
