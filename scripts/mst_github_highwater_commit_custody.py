"""§200 cloud-only, read-only *supplied bytes* Git object custody diagnostic.

No GitHub fetch, ref write, credential, IAM mutation, production publisher or
trading. SHA-1 validates ordinary Git object identity for the *supplied*
commit/tree/blob, while SHA-256 and Ed25519 verify the supplied signed
checkpoint chain. This is NOT proof of GitHub remote source authenticity,
owner-controlled trust, immutable highwater, atomic CAS, Git commit signer,
licensed market data, or publication. A real caller must securely fetch raw
Git objects and separately authenticate the owner, key, tip and ref.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
import re
from typing import Any

from scripts.mst_github_highwater_ref_proposal import (
    GithubRefProposalDenied, verify_github_highwater_ff_reread,
)
from scripts.mst_highwater_cas_intent import (
    CasIntentDenied, verify_pre_submit_snapshot,
)
from scripts.mst_signed_highwater_diagnostic import (
    HighwaterDenied, checkpoint_digest, verify_signed_highwater_candidates,
)

PAYLOAD_SCHEMA = "mst.cloud.private_highwater_git_payload_candidate.v0.1"
PAYLOAD_FIELDS = frozenset((
    "schema", "series_id", "request_id", "intent_sha256",
    "checkpoint_sha256", "signed_checkpoint", "cache_published",
    "signals_eligible",
))
BLOB_NAME = b"highwater.json"
TREE_PREFIX = b"100644 " + BLOB_NAME + b"\x00"
GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
MAX_BLOB = 8192
MAX_COMMIT = 4096
REQUIRED_CONTROLS = frozenset((
    "independent_private_owner_repository",
    "separate_least_privilege_writer",
    "protected_ref_no_force_or_delete",
    "administrator_bypass_evaluated",
    "external_owner_signer_key_pinned",
    "independent_monotone_tip_pinned",
    "auditable_key_rotation_and_recovery",
    "licensed_vendor_ingress_rights",
))
CONTROL_SCHEMA = "mst.cloud.owner_highwater_controls_intake.v0.1"
CONTROL_FIELDS = frozenset(("control", "status", "evidence_reference"))


class GitObjectCustodyDenied(ValueError):
    """Fixed error codes: do not return source bytes, raw keys or credentials."""


def _git_sha(kind: bytes, data: bytes) -> str:
    return sha1(kind + b" " + str(len(data)).encode("ascii") +
                b"\x00" + data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    try:
        b = json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True, allow_nan=False,
        ).encode("utf-8")
    except (ValueError, TypeError, OverflowError):
        raise GitObjectCustodyDenied("MST_GIT_PAYLOAD_CANONICAL_INVALID") from None
    if not 0 < len(b) <= MAX_BLOB:
        raise GitObjectCustodyDenied("MST_GIT_PAYLOAD_SIZE_INVALID")
    return b


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise GitObjectCustodyDenied("MST_GIT_PAYLOAD_DUPLICATE_JSON_KEY")
        obj[key] = value
    return obj


def _parse_payload(raw: Any) -> dict[str, Any]:
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_BLOB:
        raise GitObjectCustodyDenied("MST_GIT_BLOB_BYTES_INVALID")
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except GitObjectCustodyDenied:
        raise
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise GitObjectCustodyDenied("MST_GIT_PAYLOAD_JSON_INVALID") from None
    if type(payload) is not dict or set(payload) != PAYLOAD_FIELDS:
        raise GitObjectCustodyDenied("MST_GIT_PAYLOAD_SCHEMA_INVALID")
    if raw != _json_bytes(payload):
        raise GitObjectCustodyDenied("MST_GIT_PAYLOAD_NONCANONICAL")
    if (payload["schema"] != PAYLOAD_SCHEMA
            or payload["cache_published"] is not False
            or payload["signals_eligible"] is not False):
        raise GitObjectCustodyDenied("MST_GIT_PAYLOAD_FALSE_AUTHORITY")
    return payload


def _commit_headers(raw: Any) -> tuple[str, str]:
    """Parse strict single-parent Git commit raw bytes, not a JSON summary.

    All bytes are hash-bound. We deliberately reject mergetags, multiline
    headers, embedded NUL, and extra parents rather than try to infer origin.
    """
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_COMMIT or b"\x00" in raw:
        raise GitObjectCustodyDenied("MST_GIT_COMMIT_BYTES_INVALID")
    header, delimiter, message = raw.partition(b"\n\n")
    if delimiter != b"\n\n" or not message or not message.endswith(b"\n"):
        raise GitObjectCustodyDenied("MST_GIT_COMMIT_HEADER_INVALID")
    lines = header.split(b"\n")
    if len(lines) != 4:
        raise GitObjectCustodyDenied("MST_GIT_COMMIT_NOT_SINGLE_PARENT")
    prefixes = (b"tree ", b"parent ", b"author ", b"committer ")
    if any(not line.startswith(prefix) for line, prefix in zip(lines, prefixes)):
        raise GitObjectCustodyDenied("MST_GIT_COMMIT_HEADER_INVALID")
    if (not lines[2][7:] or not lines[3][10:]
            or any(b"\r" in line for line in lines)
            or len(message) > 512):
        raise GitObjectCustodyDenied("MST_GIT_COMMIT_HEADER_INVALID")
    try:
        tree = lines[0][5:].decode("ascii")
        parent = lines[1][7:].decode("ascii")
    except UnicodeError:
        raise GitObjectCustodyDenied("MST_GIT_COMMIT_SHA_INVALID") from None
    if GIT_SHA.fullmatch(tree) is None or GIT_SHA.fullmatch(parent) is None:
        raise GitObjectCustodyDenied("MST_GIT_COMMIT_SHA_INVALID")
    if not message.startswith(b"MST highwater candidate (UNPUBLISHED)\n"):
        raise GitObjectCustodyDenied("MST_GIT_COMMIT_MESSAGE_INVALID")
    return tree, parent


def verify_supplied_highwater_git_objects(
    *, proposal: Any, pinned_proposal_sha256: str, ref_observation: Any,
    prepared_intent: Any, pinned_intent_sha256: str, old_anchor: Any,
    signed_checkpoint_history: Any, trusted_key_id: str,
    supplied_ed25519_public_key: bytes,
    raw_commit: Any, raw_tree: Any, raw_blob: Any,
) -> dict[str, Any]:
    """Verify exact Git object SHA/parent/tree/blob and signed payload.

    This verifies only a *candidate provided by the caller*. It cannot prove
    those objects were remotely fetched from an owner-controlled repository.
    """
    try:
        verify_github_highwater_ff_reread(
            proposal, originally_prepared_proposal_sha256=pinned_proposal_sha256,
            current_ref_observation=ref_observation,
        )
        verify_pre_submit_snapshot(
            prepared_intent, observed_external_anchor=old_anchor,
            expected_prepared_intent_sha256=pinned_intent_sha256,
        )
    except (GithubRefProposalDenied, CasIntentDenied):
        raise GitObjectCustodyDenied("MST_GIT_PRIOR_INTENT_OR_REF_INVALID") from None
    related = (
        ("series_id", "series_id"),
        ("request_id", "request_id"),
        ("intent_sha256", "intent_sha256"),
        ("observed_generation", "observed_generation"),
        ("proposed_generation", "proposed_generation"),
        ("expected_revision", "expected_revision"),
        ("proposed_revision", "proposed_revision"),
        ("expected_tip_checkpoint_sha256", "expected_tip_checkpoint_sha256"),
        ("proposed_tip_checkpoint_sha256", "proposed_tip_checkpoint_sha256"),
    )
    if (type(prepared_intent) is not dict or type(proposal) is not dict
            or any(proposal[p] != prepared_intent[i] for p, i in related)):
        raise GitObjectCustodyDenied("MST_GIT_PROPOSAL_INTENT_BINDING_INVALID")
    payload = _parse_payload(raw_blob)
    if (payload["series_id"] != proposal["series_id"]
            or payload["request_id"] != proposal["request_id"]
            or payload["intent_sha256"] != pinned_intent_sha256
            or type(payload["checkpoint_sha256"]) is not str
            or SHA256_RE.fullmatch(payload["checkpoint_sha256"]) is None):
        raise GitObjectCustodyDenied("MST_GIT_BLOB_INTENT_SCOPE_MISMATCH")
    envelope = payload["signed_checkpoint"]
    if (type(signed_checkpoint_history) is not list
            or not signed_checkpoint_history
            or len(signed_checkpoint_history) >= 128):
        raise GitObjectCustodyDenied("MST_GIT_SIGNED_HISTORY_INVALID")
    try:
        old_digest = checkpoint_digest(signed_checkpoint_history[-1])
        new_digest = checkpoint_digest(envelope)
        verify_signed_highwater_candidates(
            [*signed_checkpoint_history, envelope],
            trusted_key_id=trusted_key_id,
            trusted_ed25519_public_key=supplied_ed25519_public_key,
            expected_tip_checkpoint_sha256=new_digest,
        )
    except (HighwaterDenied, ValueError, TypeError):
        raise GitObjectCustodyDenied("MST_GIT_ED25519_CHAIN_INVALID") from None
    if (old_digest != proposal["expected_tip_checkpoint_sha256"]
            or new_digest != proposal["proposed_tip_checkpoint_sha256"]
            or new_digest != payload["checkpoint_sha256"]
            or envelope["body"]["series_id"] != proposal["series_id"]
            or envelope["body"]["sequence"] != proposal["proposed_generation"]
            or envelope["body"]["head_pin"] != prepared_intent["proposed_head_pin"]):
        raise GitObjectCustodyDenied("MST_GIT_SIGNED_TIP_OR_HEAD_MISMATCH")
    if type(raw_tree) is not bytes or len(raw_tree) != len(TREE_PREFIX) + 20:
        raise GitObjectCustodyDenied("MST_GIT_TREE_BYTES_INVALID")
    blob_sha = _git_sha(b"blob", raw_blob)
    if raw_tree != TREE_PREFIX + bytes.fromhex(blob_sha):
        raise GitObjectCustodyDenied("MST_GIT_TREE_SINGLE_BLOB_REQUIRED")
    tree_sha = _git_sha(b"tree", raw_tree)
    if tree_sha != proposal["proposed_tree_sha"]:
        raise GitObjectCustodyDenied("MST_GIT_TREE_SHA_MISMATCH")
    tree_in_commit, parent_in_commit = _commit_headers(raw_commit)
    if (parent_in_commit != proposal["expected_parent_sha"]
            or tree_in_commit != tree_sha):
        raise GitObjectCustodyDenied("MST_GIT_COMMIT_PARENT_OR_TREE_MISMATCH")
    if _git_sha(b"commit", raw_commit) != proposal["proposed_commit_sha"]:
        raise GitObjectCustodyDenied("MST_GIT_COMMIT_SHA_MISMATCH")
    return {
        "schema": "mst.cloud.git_highwater_candidate_custody_diagnostic.v0.1",
        "proposal_sha256": pinned_proposal_sha256,
        "candidate_commit_sha": proposal["proposed_commit_sha"],
        "candidate_tree_sha": tree_sha,
        "candidate_blob_git_sha1": blob_sha,
        "candidate_blob_sha256": sha256(raw_blob).hexdigest(),
        "signed_tip_sha256": new_digest,
        "supplied_git_objects_hash_consistent": True,
        "ed25519_valid_for_supplied_key": True,
        "git_sha1_collision_resistance_upgraded": False,
        "remote_git_object_fetch_authenticated": False,
        "owner_repo_iam_and_ref_protection_verified": False,
        "trusted_signer_and_external_tip_authenticated": False,
        "remote_ref_update_executed": False,
        "atomic_cas_proven": False,
        "production_cache_published": False,
        "signals_eligible": False,
    }


def review_owner_highwater_control_evidence(
    *, proposal: Any, entries: Any,
) -> dict[str, Any]:
    """Inventory untrusted evidence references; NEVER accept self-attestation.

    User-approved setup and independent owner verification require later
    provider-native reads by a separate principal. A complete checklist does
    NOT grant permissions or authorize ref mutation.
    """
    if type(proposal) is not dict or proposal.get("schema") != (
        "mst.cloud.github_highwater_ff_proposal.v0.1"
    ):
        raise GitObjectCustodyDenied("MST_OWNER_EVIDENCE_PROPOSAL_INVALID")
    if type(entries) is not list or len(entries) > len(REQUIRED_CONTROLS):
        raise GitObjectCustodyDenied("MST_OWNER_EVIDENCE_INPUT_INVALID")
    seen: set[str] = set()
    pending: list[str] = []
    for e in entries:
        if type(e) is not dict or set(e) != CONTROL_FIELDS:
            raise GitObjectCustodyDenied("MST_OWNER_EVIDENCE_FIELDS_INVALID")
        control, status, reference = (
            e["control"], e["status"], e["evidence_reference"]
        )
        if (type(control) is not str or control not in REQUIRED_CONTROLS
                or control in seen or type(status) is not str
                or status not in ("MISSING", "OWNER_REVIEW_PENDING")
                or (reference is not None and (
                    type(reference) is not str or len(reference) > 120
                    or re.fullmatch(r"[A-Za-z0-9_./:-]{8,120}", reference) is None
                ))
                or (status == "MISSING" and reference is not None)):
            raise GitObjectCustodyDenied("MST_OWNER_EVIDENCE_UNTRUSTED_OR_DUPLICATE")
        seen.add(control)
        if status == "OWNER_REVIEW_PENDING":
            pending.append(control)
    return {
        "schema": CONTROL_SCHEMA,
        "missing_controls": sorted(REQUIRED_CONTROLS - seen),
        "pending_unverified_controls": sorted(pending),
        "owner_approval_and_independent_review_proven": False,
        "real_private_repo_or_permissions_provisioned": False,
        "independent_signer_and_monotone_tip_verified": False,
        "remote_ref_write_authorized": False,
        "production_cache_published": False,
        "signals_eligible": False,
    }
