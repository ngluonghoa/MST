"""MST M4: machine-readable owner gate dossier from a BLOCKING GitHub audit.

This emits a review packet, NOT an authorization, credential, signature, release
receipt, durable witness or market data right. It deliberately refuses to ingest
a purported "ready" result: a different owner-approved control and external
trust root must be designed/approved before production can be considered.

All project work runs in GitHub-hosted CI. This module has no API/network I/O.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

from scripts.m4_reader_readiness_preflight import (
    _BASE, _DENIED, _GATES, _REF,
)

_SCHEMA = "mst.m4.owner-gate-dossier.unattested.v1"
_AUDIT_SCHEMA = "mst.m4.reader-readiness.blocking-audit.v1"
_AUDIT_STATUS = "M4_READER_AND_PUBLISHER_BLOCKED_PENDING_EXTERNAL_OWNER_GATES"
_AUDIT_CLASS = "GITHUB_REST_READ_ONLY_METADATA_FOR_THIS_TOKEN"
_SHA1 = re.compile(r"^[a-f0-9]{40}$")
_RE = re.compile(r"^[a-f0-9]{64}$")

# Acceptance items are requirements for owners to *supply independently*.
# They are NOT proven by existence of a URL or a successful CI run.
_REQUIREMENTS = (
    ("G01", "Independent signer root and enrollment",
     "Owner-signed identity, key provenance, role binding and auditable approval"),
    ("G02", "Protected per-namespace immutable/monotonic floor",
     "Independent durable registry and receipt head, enforced across accounts and crashes"),
    ("G03", "Server-side two-principal atomic CAS",
     "Two authenticated writers racing one head; one winner; loser readback and recovery"),
    ("G04", "Licensed vendor source and as-of rights",
     "Provider-approved permissions, first-known revisions, corrections and Drive retention"),
    ("G05", "Real Drive bytes and GitHub protected witness",
     "Authenticated Google Drive chunk SHA and Git commit/tree/ref, fault-injected 2-service journal"),
    ("G06", "Global credential/entitlement revocation",
     "Independent key epoch fencing across runners, accounts and publisher readers"),
    ("G07", "Independently verifiable evidence tiers",
     "Verifier-controlled external roots, non-self-attested transition and negative acceptance"),
    ("G08", "A02/A03/M3/M4/M8 owner release approval",
     "63 module final owner dispositions, ABI signoff, license, recovery and release approval"),
)

_REQUIRED_FALSE = (
    "witness_actual_owner_authorization",
    "witness_active_protection_effective_end_to_end_verified",
    *_DENIED.keys(),
)


def _canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    ).encode("ascii")


def build_dossier(audit, *, workflow_run_id: int, candidate_head_sha: str):
    """Validate *untrusted* read-only metadata and emit blocking owner TODOs."""
    if type(audit) is not dict:
        raise TypeError("GITHUB_READINESS_DICT_REQUIRED")
    if type(workflow_run_id) is not int or workflow_run_id < 1:
        raise ValueError("INVALID_WORKFLOW_RUN_ID")
    if type(candidate_head_sha) is not str or not _SHA1.fullmatch(candidate_head_sha):
        raise ValueError("INVALID_CANDIDATE_HEAD_SHA")
    for key, expected in (
        ("schema", _AUDIT_SCHEMA),
        ("status", _AUDIT_STATUS),
        ("evidence_class", _AUDIT_CLASS),
        ("main_head_sha", _BASE),
        ("witness_ref_name", _REF),
    ):
        if audit.get(key) != expected:
            raise ValueError("UNEXPECTED_AUDIT_IDENTITY_OR_STATUS_" + key)
    if audit.get("main_baseline_verified_for_this_read") is not True:
        raise ValueError("PINNED_MAIN_NOT_VERIFIED")
    if audit.get("owner_gates_still_open") != list(_GATES):
        raise ValueError("OWNER_GATES_CHANGED_OR_CLAIMED_CLOSED")
    for key in _REQUIRED_FALSE:
        if audit.get(key) is not False:
            raise PermissionError("SELF_ATTESTED_PRODUCTION_RIGHT_" + key)
    for key in (
        "witness_ref_exists_for_this_read",
        "witness_ruleset_visible_for_this_token",
        "witness_ruleset_scope_visible_for_this_token",
        "witness_ruleset_metadata_matches_for_this_token",
        "witness_bypass_list_visible_for_this_token",
    ):
        if type(audit.get(key)) is not bool:
            raise ValueError("UNVERIFIABLE_GITHUB_READBACK_FIELD_" + key)
    if audit["witness_ruleset_metadata_matches_for_this_token"] and not (
        audit["witness_ruleset_scope_visible_for_this_token"]
        and audit["witness_ruleset_visible_for_this_token"]
    ):
        raise ValueError("IMPOSSIBLE_RULESET_SCOPE_CLAIM")
    ref_sha = audit.get("witness_ref_head_sha_for_this_read")
    if audit["witness_ref_exists_for_this_read"]:
        if type(ref_sha) is not str or not _SHA1.fullmatch(ref_sha):
            raise ValueError("MISSING_OR_INVALID_WITNESS_HEAD")
    elif ref_sha is not None:
        raise ValueError("UNEXPLAINED_WITNESS_SHA_WITHOUT_REF")

    fingerprint = sha256(_canonical(audit)).hexdigest()
    # An audit JSON hash is a checksum of caller-supplied bytes, NOT a signature.
    gates = []
    for expected, (name, label, requirement) in zip(_GATES, _REQUIREMENTS):
        if not expected.startswith("SIGNED_" + name + "_"):
            raise ValueError("INCONSISTENT_SIGNED_GATE_TAXONOMY")
        gates.append({
            "gate": expected,
            "status": "OPEN_OWNER_EVIDENCE_REQUIRED",
            "review_question": label,
            "required_independent_evidence": requirement,
            "source_evidence_level": "CURRENT_GITHUB_METADATA_OR_SYNTHETIC_ONLY",
            "externally_attested": False,
            "release_authorized": False,
        })
    return {
        "schema": _SCHEMA,
        "status": "OWNER_DECISION_PACKET_ONLY_PRODUCTION_BLOCKED",
        "provenance": "GITHUB_ACTIONS_READ_ONLY_AUDIT_CHECKSUM_NOT_AUTHORITY",
        "readiness_audit_sha256_untrusted": fingerprint,
        "workflow_run_id": workflow_run_id,
        "candidate_head_sha_for_review_only": candidate_head_sha,
        "main_sha_at_readback": _BASE,
        "witness_ref_exists_in_readback": audit["witness_ref_exists_for_this_read"],
        "witness_ruleset_visible_for_this_token": audit["witness_ruleset_visible_for_this_token"],
        "owner_decision_gates": gates,
        "owner_decisions_accepted": False,
        "independent_root_evidence_accepted": False,
        "external_protected_floor_evidence_accepted": False,
        "licensed_vendor_rights_accepted": False,
        "real_drive_custody_evidence_accepted": False,
        "production_cache_read_authorized": False,
        "production_cache_write_authorized": False,
        "trading_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--head", required=True)
    args = parser.parse_args(argv)
    raw = json.loads(args.readiness.read_text(encoding="utf-8"))
    dossier = build_dossier(
        raw, workflow_run_id=args.run_id, candidate_head_sha=args.head,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(dossier, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8")
    print(json.dumps({
        "status": dossier["status"],
        "owner_gates_open": len(dossier["owner_decision_gates"]),
        "readiness_checksum_untrusted": dossier["readiness_audit_sha256_untrusted"],
        "cache_read_authorized": False,
        "trading_authorized": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
