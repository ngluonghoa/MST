"""MST §245: fail-closed, read-only Ed25519 checkpoint-chain verifier.

Isolated §196 candidate-chain core. Does not sign, update Git refs,
authenticate external key/tip custody, execute CAS or publish a Cache head.
A public key/tip supplied by an untrusted writer can verify a FORGED chain.
Tests use ephemeral fictional keys only. Never log source IDs or signatures.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


CHECKPOINT_SCHEMA = "mst.private.signed_highwater_candidate.v0.1"
BODY_SCHEMA = "mst.private.highwater_candidate_body.v0.1"
MAX_CHECKPOINTS = 128
MAX_ENVELOPE_BYTES = 4096
KEY = re.compile(r"[A-Za-z0-9_-]{8,80}\Z")
SERIES = re.compile(r"[A-Za-z0-9_-]{8,80}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
ID = re.compile(r"[A-Za-z0-9_-]{8,160}\Z")
RUN = re.compile(r"[1-9][0-9]{5,19}\Z")
SYMBOL = re.compile(r"[A-Z]{3}\Z")
SCOPE = frozenset(("SSI", "DNSE"))
TFS = frozenset(("M5", "M15", "M30", "H1", "D1"))
ENVELOPE_FIELDS = frozenset(("schema", "key_id", "body", "signature_b64"))
BODY_FIELDS = frozenset((
    "schema", "repository", "series_id", "sequence",
    "previous_checkpoint_sha256", "previous_head_pin", "head_pin",
    "source_finality_attested", "publisher_cas_executed",
    "source_licensed_for_storage_attested", "signals_eligible",
))
PIN_FIELDS = frozenset((
    "provider", "symbol", "native_tf", "file_id", "run_id", "source_sha256",
))
FALSE_FIELDS = (
    "source_finality_attested", "publisher_cas_executed",
    "source_licensed_for_storage_attested", "signals_eligible",
)


class HighwaterDenied(ValueError):
    """Fixed non-sensitive errors; no market data or private key disclosure."""


def _canonical(data: Any, *, max_bytes: int) -> bytes:
    try:
        raw = json.dumps(
            data, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True, allow_nan=False,
        ).encode("utf-8")
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise HighwaterDenied("MST_245_CANONICAL_JSON_INVALID") from None
    if not 0 < len(raw) <= max_bytes:
        raise HighwaterDenied("MST_245_CANONICAL_BYTES_BOUNDS")
    return raw


def checkpoint_digest(envelope: Any) -> str:
    """Envelope hash includes signature, NOT an independently signed tip."""
    return hashlib.sha256(
        _canonical(envelope, max_bytes=MAX_ENVELOPE_BYTES)
    ).hexdigest()


def _pin(value: Any, *, label: str) -> dict[str, str]:
    if (type(value) is not dict or set(value) != PIN_FIELDS
        or type(value.get("provider")) is not str
        or value["provider"] not in SCOPE
        or type(value.get("symbol")) is not str
        or SYMBOL.fullmatch(value["symbol"]) is None
        or type(value.get("native_tf")) is not str
        or value["native_tf"] not in TFS
        or type(value.get("file_id")) is not str
        or ID.fullmatch(value["file_id"]) is None
        or type(value.get("run_id")) is not str
        or RUN.fullmatch(value["run_id"]) is None
        or type(value.get("source_sha256")) is not str
        or SHA.fullmatch(value["source_sha256"]) is None):
        raise HighwaterDenied("MST_245_"+label+"_PIN_INVALID")
    return value


def _envelope(value: Any, key_id: str) -> tuple[dict[str, Any], bytes]:
    if (type(value) is not dict or set(value) != ENVELOPE_FIELDS
        or value["schema"] != CHECKPOINT_SCHEMA
        or value["key_id"] != key_id
        or type(value["signature_b64"]) is not str
        or len(value["signature_b64"]) != 88):
        raise HighwaterDenied("MST_245_CHECKPOINT_ENVELOPE_INVALID")
    try:
        sig = base64.b64decode(value["signature_b64"], validate=True)
        if (len(sig) != 64
            or base64.b64encode(sig).decode("ascii") != value["signature_b64"]):
            raise ValueError("bad canonical signature")
    except (ValueError, binascii.Error):
        raise HighwaterDenied("MST_245_SIGNATURE_ENCODING_INVALID") from None
    body = value["body"]
    if (type(body) is not dict or set(body) != BODY_FIELDS
        or body["schema"] != BODY_SCHEMA
        or body["repository"] != "ngluonghoa/MST"
        or type(body["series_id"]) is not str
        or SERIES.fullmatch(body["series_id"]) is None
        or type(body["sequence"]) is not int
        or not 1 <= body["sequence"] <= 1_000_000_000
        or any(body.get(k) is not False for k in FALSE_FIELDS)):
        raise HighwaterDenied("MST_245_CHECKPOINT_BODY_DENIED")
    _pin(body["head_pin"], label="HEAD")
    if body["sequence"] == 1:
        if (body["previous_checkpoint_sha256"] is not None
            or body["previous_head_pin"] is not None):
            raise HighwaterDenied("MST_245_GENESIS_PREDECESSOR_DENIED")
    else:
        if (type(body["previous_checkpoint_sha256"]) is not str
            or SHA.fullmatch(body["previous_checkpoint_sha256"]) is None):
            raise HighwaterDenied("MST_245_PREVIOUS_DIGEST_DENIED")
        _pin(body["previous_head_pin"], label="PREVIOUS")
    # Refuse oversized/ill-typed body *before* attempting signature verify.
    _canonical(body, max_bytes=2048)
    return body, sig


def verify_signed_highwater_candidates(
    candidates: Any, *,
    trusted_key_id: str,
    trusted_ed25519_public_key: bytes,
    expected_tip_checkpoint_sha256: str,
) -> dict[str, Any]:
    """Verify complete genesis->tip candidate chain, never a trusted CAS.

    The supplied public key and expected tip must be checked OUTSIDE the
    public MST repo, Drive source writer and private Git ref before promotion.
    Neither the supplied bytes nor correct signatures establish owner trust.
    """
    if (type(trusted_key_id) is not str
        or KEY.fullmatch(trusted_key_id) is None
        or type(trusted_ed25519_public_key) is not bytes
        or len(trusted_ed25519_public_key) != 32
        or type(expected_tip_checkpoint_sha256) is not str
        or SHA.fullmatch(expected_tip_checkpoint_sha256) is None):
        raise HighwaterDenied("MST_245_EXTERNAL_TRUST_INPUT_INVALID")
    if type(candidates) is not list or not 1 <= len(candidates) <= MAX_CHECKPOINTS:
        raise HighwaterDenied("MST_245_CHAIN_LENGTH_INVALID")
    try:
        public = Ed25519PublicKey.from_public_bytes(
            trusted_ed25519_public_key
        )
    except (ValueError, TypeError):
        raise HighwaterDenied("MST_245_PUBLIC_KEY_INVALID") from None
    prev_body: dict[str, Any] | None = None
    prev_digest: str | None = None
    for position, candidate in enumerate(candidates, start=1):
        body, signature = _envelope(candidate, trusted_key_id)
        try:
            public.verify(signature, _canonical(body, max_bytes=2048))
        except (InvalidSignature, ValueError, TypeError):
            raise HighwaterDenied("MST_245_ED25519_SIGNATURE_INVALID") from None
        if body["sequence"] != position:
            raise HighwaterDenied("MST_245_CHECKPOINT_SEQUENCE_GAP")
        if prev_body is not None:
            old, new = prev_body["head_pin"], body["head_pin"]
            if (body["series_id"] != prev_body["series_id"]
                or body["repository"] != prev_body["repository"]
                or body["previous_checkpoint_sha256"] != prev_digest
                or body["previous_head_pin"] != old
                or any(new[k] != old[k]
                       for k in ("provider", "symbol", "native_tf"))
                or int(new["run_id"]) <= int(old["run_id"])
                or new["file_id"] == old["file_id"]
                or new["source_sha256"] == old["source_sha256"]):
                raise HighwaterDenied("MST_245_SIGNED_LINK_OR_REPLAY_DENIED")
        prev_digest = checkpoint_digest(candidate)
        prev_body = body
    if prev_digest != expected_tip_checkpoint_sha256:
        raise HighwaterDenied("MST_245_EXTERNAL_TIP_MISMATCH")
    assert prev_body is not None
    pin = prev_body["head_pin"]
    return {
        "schema": "mst.private.highwater_signature_readonly_check.v0.1",
        "status": "CRYPTOGRAPHIC_CANDIDATE_CHAIN_ONLY",
        "checkpoint_count": len(candidates),
        "linked_edges": len(candidates)-1,
        "signed_for_supplied_ed25519_key": True,
        "tip_matches_supplied_digest": True,
        "source_provider": pin["provider"],
        "native_tf": pin["native_tf"],
        "independent_owner_signer_authenticated": False,
        "external_tip_pin_independently_authenticated": False,
        "actual_git_ref_verified": False,
        "highwater_immutability_monotonicity_proven": False,
        "atomic_cas_executed": False,
        "source_rights_or_bar_finality_attested": False,
        "cache_head_published": False,
        "signals_or_trades_eligible": False,
    }
