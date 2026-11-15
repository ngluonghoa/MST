"""§201 read-only *CLAIMED* GitHub custody and owner-key rotation diagnostics.

This module has NO GitHub API calls, network, ref updates, credential use,
seller/vendor source reads, Cache publish, or trade path. It binds two caller
supplied REST-like ref snapshots and one REST-like object observation to
§200 raw commit/tree/blob/signed-source verification, then verifies a separate
Ed25519 owner signature over the evidence *claim*. The key, snapshots and
expected pins are supplied by the caller, NOT independently authenticated.

Neither a valid signed claim nor the reported host/method validates that a
GitHub response was obtained over trusted TLS, that a signer owns the repo,
that the pinned key/tip is external, or that a real atomic ref update occurred.
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

from scripts.mst_github_highwater_commit_custody import (
    GitObjectCustodyDenied, verify_supplied_highwater_git_objects,
)

CLAIM_SCHEMA = "mst.cloud.github_readonly_owner_evidence_claim.v0.1"
CLAIM_BODY_SCHEMA = "mst.cloud.github_readonly_owner_evidence_body.v0.1"
REF_OBS_SCHEMA = "mst.cloud.github_readonly_ref_observation.v0.1"
OBJECT_OBS_SCHEMA = "mst.cloud.github_readonly_objects_observation.v0.1"
ROTATION_SCHEMA = "mst.cloud.owner_key_rotation_candidate.v0.1"
ROTATION_BODY_SCHEMA = "mst.cloud.owner_key_rotation_body.v0.1"
OWNER_ENVELOPE_FIELDS = frozenset(("schema", "key_id", "body", "signature_b64"))
REF_FIELDS = frozenset(("schema", "repository", "ref", "sha", "host", "method"))
OBJECT_FIELDS = frozenset((
    "schema", "repository", "host", "method", "commit_sha", "tree_sha",
    "blob_git_sha1", "blob_sha256",
))
BODY_FIELDS = frozenset((
    "schema", "repository", "ref", "series_id", "request_id",
    "owner_key_epoch", "expected_old_ref_sha", "candidate_commit_sha",
    "candidate_tree_sha", "candidate_blob_sha256",
    "previous_checkpoint_tip_sha256", "proposed_checkpoint_tip_sha256",
    "intent_sha256", "proposal_sha256", "ref_read_one_sha256",
    "ref_read_two_sha256", "object_read_sha256",
    "remote_transport_authenticated", "owner_iam_proven",
    "remote_atomic_cas_proven", "cache_published", "signals_eligible",
))
ROTATION_ENVELOPE_FIELDS = frozenset((
    "schema", "body", "old_signature_b64", "new_signature_b64",
))
ROTATION_FIELDS = frozenset((
    "schema", "repository", "ref", "series_id", "old_key_id", "new_key_id",
    "old_key_sha256", "new_key_sha256", "old_epoch", "new_epoch",
    "old_ref_sha", "old_checkpoint_tip_sha256",
    "status", "activated", "owner_iam_verified", "cache_published",
))
SHA = re.compile(r"[0-9a-f]{64}\Z")
GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
KEY_ID = re.compile(r"[A-Za-z0-9_-]{8,80}\Z")
MAX_BYTES = 8192
MAX_EPOCH = 2**31 - 2


class GitReadEvidenceDenied(ValueError):
    """Fixed error codes only; never log signed claim, credentials or bytes."""


def _canonical(value: Any, limit: int = MAX_BYTES) -> bytes:
    try:
        raw = json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError):
        raise GitReadEvidenceDenied("MST_READ_EVIDENCE_JSON_INVALID") from None
    if not 0 < len(raw) <= limit:
        raise GitReadEvidenceDenied("MST_READ_EVIDENCE_SIZE_INVALID")
    return raw


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _sig(value: Any) -> bytes:
    if type(value) is not str or len(value) != 88:
        raise GitReadEvidenceDenied("MST_READ_EVIDENCE_SIGNATURE_ENCODING")
    try:
        sig = base64.b64decode(value, validate=True)
        if len(sig) != 64 or base64.b64encode(sig).decode("ascii") != value:
            raise ValueError()
    except (ValueError, binascii.Error):
        raise GitReadEvidenceDenied("MST_READ_EVIDENCE_SIGNATURE_ENCODING") from None
    return sig


def _verify(public: bytes, signature_b64: Any, body: Any) -> None:
    signature = _sig(signature_b64)
    try:
        Ed25519PublicKey.from_public_bytes(public).verify(
            signature, _canonical(body, limit=4096),
        )
    except (InvalidSignature, ValueError, TypeError):
        raise GitReadEvidenceDenied("MST_READ_EVIDENCE_SIGNATURE_INVALID") from None


def _sha(value: Any) -> bool:
    return type(value) is str and SHA.fullmatch(value) is not None


def _git_sha(value: Any) -> bool:
    return type(value) is str and GIT_SHA.fullmatch(value) is not None


def _owner_id(value: Any) -> bool:
    return type(value) is str and KEY_ID.fullmatch(value) is not None


def verify_signed_readonly_git_evidence_claim(
    *, custody_inputs: Any, readonly_ref_observations: Any,
    readonly_object_observation: Any, signed_owner_claim: Any,
    trusted_owner_key_id: str, supplied_owner_public_key: bytes,
    pinned_owner_public_key_sha256: str, pinned_signed_claim_sha256: str,
    pinned_external_old_ref_sha: str,
    pinned_external_old_checkpoint_tip_sha256: str,
    pinned_owner_key_epoch: int,
) -> dict[str, Any]:
    """Verify a caller-signed observation report, never authenticate its origin.

    All pins and public keys MUST come from a truly independent owner boundary
    in any future production use. The current function cannot establish that
    independence; even a matching private key is just a caller-supplied signer.
    """
    if type(custody_inputs) is not dict:
        raise GitReadEvidenceDenied("MST_READ_EVIDENCE_CUSTODY_INPUT_INVALID")
    try:
        custody = verify_supplied_highwater_git_objects(**custody_inputs)
    except (GitObjectCustodyDenied, TypeError, KeyError):
        raise GitReadEvidenceDenied("MST_READ_EVIDENCE_GIT_CUSTODY_INVALID") from None
    proposal = custody_inputs["proposal"]
    if (not _owner_id(trusted_owner_key_id)
            or type(supplied_owner_public_key) is not bytes
            or len(supplied_owner_public_key) != 32
            or not _sha(pinned_owner_public_key_sha256)
            or sha256(supplied_owner_public_key).hexdigest()
               != pinned_owner_public_key_sha256
            or supplied_owner_public_key
               == custody_inputs["supplied_ed25519_public_key"]
            or not _sha(pinned_signed_claim_sha256)
            or not _sha(pinned_external_old_checkpoint_tip_sha256)
            or not _git_sha(pinned_external_old_ref_sha)
            or type(pinned_owner_key_epoch) is not int
            or not 1 <= pinned_owner_key_epoch <= MAX_EPOCH):
        raise GitReadEvidenceDenied("MST_READ_EVIDENCE_EXTERNAL_PINS_INVALID")
    if (pinned_external_old_ref_sha != proposal["expected_parent_sha"]
            or pinned_external_old_checkpoint_tip_sha256
               != proposal["expected_tip_checkpoint_sha256"]):
        raise GitReadEvidenceDenied("MST_READ_EVIDENCE_EXTERNAL_FLOOR_MISMATCH")
    if (type(readonly_ref_observations) is not list
            or len(readonly_ref_observations) != 2):
        raise GitReadEvidenceDenied("MST_READ_EVIDENCE_TWO_REF_READS_REQUIRED")
    for ref in readonly_ref_observations:
        if (type(ref) is not dict or set(ref) != REF_FIELDS
                or ref["schema"] != REF_OBS_SCHEMA
                or ref["repository"] != proposal["repository"]
                or ref["ref"] != proposal["ref"]
                or ref["host"] != "api.github.com"
                or ref["method"] != "GET"
                or ref["sha"] != pinned_external_old_ref_sha):
            raise GitReadEvidenceDenied("MST_READ_EVIDENCE_REF_DRIFT_OR_SCOPE")
    obj = readonly_object_observation
    if (type(obj) is not dict or set(obj) != OBJECT_FIELDS
            or obj["schema"] != OBJECT_OBS_SCHEMA
            or obj["repository"] != proposal["repository"]
            or obj["host"] != "api.github.com"
            or obj["method"] != "GET"
            or obj["commit_sha"] != custody["candidate_commit_sha"]
            or obj["tree_sha"] != custody["candidate_tree_sha"]
            or obj["blob_git_sha1"] != custody["candidate_blob_git_sha1"]
            or obj["blob_sha256"] != custody["candidate_blob_sha256"]):
        raise GitReadEvidenceDenied("MST_READ_EVIDENCE_OBJECT_DRIFT_OR_SCOPE")
    envelope = signed_owner_claim
    if (type(envelope) is not dict or set(envelope) != OWNER_ENVELOPE_FIELDS
            or envelope["schema"] != CLAIM_SCHEMA
            or envelope["key_id"] != trusted_owner_key_id
            or type(envelope["body"]) is not dict
            or set(envelope["body"]) != BODY_FIELDS):
        raise GitReadEvidenceDenied("MST_READ_EVIDENCE_CLAIM_SCHEMA_INVALID")
    body = envelope["body"]
    expected = {
        "schema": CLAIM_BODY_SCHEMA,
        "repository": proposal["repository"],
        "ref": proposal["ref"],
        "series_id": proposal["series_id"],
        "request_id": proposal["request_id"],
        "owner_key_epoch": pinned_owner_key_epoch,
        "expected_old_ref_sha": pinned_external_old_ref_sha,
        "candidate_commit_sha": custody["candidate_commit_sha"],
        "candidate_tree_sha": custody["candidate_tree_sha"],
        "candidate_blob_sha256": custody["candidate_blob_sha256"],
        "previous_checkpoint_tip_sha256":
            pinned_external_old_checkpoint_tip_sha256,
        "proposed_checkpoint_tip_sha256": custody["signed_tip_sha256"],
        "intent_sha256": proposal["intent_sha256"],
        "proposal_sha256": proposal["proposal_sha256"],
        "ref_read_one_sha256": _digest(readonly_ref_observations[0]),
        "ref_read_two_sha256": _digest(readonly_ref_observations[1]),
        "object_read_sha256": _digest(obj),
        "remote_transport_authenticated": False,
        "owner_iam_proven": False,
        "remote_atomic_cas_proven": False,
        "cache_published": False,
        "signals_eligible": False,
    }
    if body != expected or any(
        type(body[k]) is not type(v) for k, v in expected.items()
    ):
        raise GitReadEvidenceDenied("MST_READ_EVIDENCE_CLAIM_MISMATCH")
    if _digest(envelope) != pinned_signed_claim_sha256:
        raise GitReadEvidenceDenied("MST_READ_EVIDENCE_SIGNED_CLAIM_PIN_MISMATCH")
    _verify(supplied_owner_public_key, envelope["signature_b64"], body)
    return {
        "schema": "mst.cloud.github_readonly_evidence_diagnostic.v0.1",
        "signed_claim_sha256": pinned_signed_claim_sha256,
        "candidate_commit_sha": custody["candidate_commit_sha"],
        "supplied_ref_reads_consistent": True,
        "supplied_object_readback_consistent": True,
        "supplied_checkpoint_ed25519_verified": True,
        "owner_evidence_signature_valid_for_supplied_key": True,
        "separate_owner_evidence_key_bytes": True,
        "independent_owner_key_and_external_floor_authenticated": False,
        "github_rest_response_origin_authenticated": False,
        "git_sha1_collision_protected": False,
        "owner_repo_ref_rules_and_iam_verified": False,
        "owner_key_rotation_or_revocation_activated": False,
        "remote_ref_update_or_atomic_cas_proven": False,
        "production_cache_published": False,
        "signals_eligible": False,
    }


def review_dual_signed_owner_key_rotation_candidate(
    *, rotation: Any, old_owner_public_key: bytes,
    new_owner_public_key: bytes, old_owner_key_id: str,
    new_owner_key_id: str, pinned_old_owner_key_sha256: str,
    pinned_rotation_sha256: str, expected_old_epoch: int,
    expected_repository: str, expected_ref: str,
    expected_series_id: str, pinned_old_ref_sha: str,
    pinned_old_tip_sha256: str,
) -> dict[str, Any]:
    """Dual-signature candidate only. No key rotation, revocation or IAM.

    A copied old external anchor can still be replayed if not independently
    pinned in a monotone source controlled outside this process/repository.
    """
    if (not _owner_id(old_owner_key_id) or not _owner_id(new_owner_key_id)
            or old_owner_key_id == new_owner_key_id
            or type(old_owner_public_key) is not bytes
            or type(new_owner_public_key) is not bytes
            or len(old_owner_public_key) != 32
            or len(new_owner_public_key) != 32
            or old_owner_public_key == new_owner_public_key
            or not _sha(pinned_old_owner_key_sha256)
            or sha256(old_owner_public_key).hexdigest()
               != pinned_old_owner_key_sha256
            or not _sha(pinned_rotation_sha256)
            or type(expected_old_epoch) is not int
            or not 1 <= expected_old_epoch < MAX_EPOCH
            or not _git_sha(pinned_old_ref_sha)
            or not _sha(pinned_old_tip_sha256)
            or type(expected_repository) is not str
            or type(expected_ref) is not str
            or type(expected_series_id) is not str):
        raise GitReadEvidenceDenied("MST_KEY_ROTATION_EXTERNAL_INPUT_INVALID")
    if (type(rotation) is not dict
            or set(rotation) != ROTATION_ENVELOPE_FIELDS
            or rotation["schema"] != ROTATION_SCHEMA
            or type(rotation["body"]) is not dict
            or set(rotation["body"]) != ROTATION_FIELDS):
        raise GitReadEvidenceDenied("MST_KEY_ROTATION_SCHEMA_INVALID")
    body = rotation["body"]
    expected = {
        "schema": ROTATION_BODY_SCHEMA,
        "repository": expected_repository,
        "ref": expected_ref,
        "series_id": expected_series_id,
        "old_key_id": old_owner_key_id,
        "new_key_id": new_owner_key_id,
        "old_key_sha256": pinned_old_owner_key_sha256,
        "new_key_sha256": sha256(new_owner_public_key).hexdigest(),
        "old_epoch": expected_old_epoch,
        "new_epoch": expected_old_epoch + 1,
        "old_ref_sha": pinned_old_ref_sha,
        "old_checkpoint_tip_sha256": pinned_old_tip_sha256,
        "status": "PROPOSED_NOT_ACTIVATED",
        "activated": False,
        "owner_iam_verified": False,
        "cache_published": False,
    }
    if body != expected or any(
        type(body[k]) is not type(v) for k, v in expected.items()
    ):
        raise GitReadEvidenceDenied("MST_KEY_ROTATION_SCOPE_OR_EPOCH_INVALID")
    if _digest(rotation) != pinned_rotation_sha256:
        raise GitReadEvidenceDenied("MST_KEY_ROTATION_PIN_MISMATCH")
    _verify(old_owner_public_key, rotation["old_signature_b64"], body)
    _verify(new_owner_public_key, rotation["new_signature_b64"], body)
    return {
        "schema": "mst.cloud.owner_key_rotation_diagnostic.v0.1",
        "dual_signatures_valid_for_supplied_keys": True,
        "previous_epoch": expected_old_epoch,
        "proposed_epoch": expected_old_epoch + 1,
        "independent_old_key_pin_authenticated": False,
        "new_key_owner_iam_authorized": False,
        "key_rotation_activated": False,
        "old_key_revoked": False,
        "external_monotone_key_epoch_verified": False,
        "remote_ref_update_or_atomic_cas_proven": False,
        "production_cache_published": False,
        "signals_eligible": False,
    }
