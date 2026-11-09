"""MST M4 cross-GitHub-run signer registry + floor continuity lab.

Only disposable GitHub Actions cache bytes and synthetic identifiers. A cache
hit does NOT establish authenticated owner, authoritative signer or protected
monotonic source-clock floor. No network, keys, vendors or Drive I/O here.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

SCHEMA = "mst.m4.cross-run-registry-unattested.v1"
SOURCE_PARTITION = "a" * 64
RIGHTS_POLICY = "b" * 64
GENESIS_REGISTRY = "0" * 64
HEX64 = re.compile(r"^[0-9a-f]{64}$")
DENIED = {
    "independent_owner_root_verified": False,
    "global_revocation_verified": False,
    "protected_registry_floor_verified": False,
    "protected_receipt_floor_verified": False,
    "two_authenticated_writer_cas_verified": False,
    "licensed_vendor_first_known_verified": False,
    "physical_google_drive_bytes_verified": False,
    "trading_authorized": False,
}


def _positive(value, field):
    if type(value) is not int or value <= 0:
        raise ValueError("INVALID_" + field.upper())
    return value


def _hash(value):
    return sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")).hexdigest()


def emit_fixture(run_id: int, pr: int) -> dict:
    """Produce ONLY arbitrary claims, never sign or attest them."""
    _positive(run_id, "run_id")
    _positive(pr, "pr")
    registry = {
        "schema": SCHEMA,
        "pr": pr,
        "producer_run_id": run_id,
        "partition_digest": SOURCE_PARTITION,
        "rights_policy_digest": RIGHTS_POLICY,
        "registry_revision": 1,
        "registry_parent_digest": GENESIS_REGISTRY,
        "key_epoch": 1,
        "signer_label": "fixture.runner",
        "revoked": False,
        "floor_generation": 0,
        "floor_digest": GENESIS_REGISTRY,
        "owner_authorized": False,
        "vendor_authorized": False,
        "cache_write_authorized": False,
    }
    return {"claim": registry, "claim_digest": _hash(registry)}


def recover_fixture(
    raw: str | None, *, current_run_id: int, pr: int,
    require_prior: bool = False, caller_minimum_run_id: int | None = None,
) -> dict:
    _positive(current_run_id, "run_id")
    _positive(pr, "pr")
    if caller_minimum_run_id is not None:
        _positive(caller_minimum_run_id, "minimum_run_id")
    if raw is None:
        if require_prior:
            raise ValueError("CROSS_RUN_REGISTRY_CACHE_NOT_FOUND")
        return {
            "status": "BOOTSTRAP_NO_PRIOR_REGISTRY_CACHE_UNATTESTED",
            "prior_run_id": None,
            "current_run_id": current_run_id,
            **DENIED,
        }
    try:
        packet = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("INVALID_REGISTRY_CACHE_JSON") from exc
    if type(packet) is not dict or set(packet) != {"claim", "claim_digest"}:
        raise ValueError("NON_CANONICAL_REGISTRY_ENVELOPE")
    claim = packet["claim"]
    expected_keys = set(emit_fixture(1, 1)["claim"])
    if type(claim) is not dict or set(claim) != expected_keys:
        raise ValueError("NON_CANONICAL_REGISTRY_CLAIM")
    if type(packet["claim_digest"]) is not str or not HEX64.fullmatch(
        packet["claim_digest"]
    ):
        raise ValueError("INVALID_REGISTRY_DIGEST")
    if _hash(claim) != packet["claim_digest"]:
        raise ValueError("REGISTRY_CACHE_BYTES_TAMPERED")
    prior = _positive(claim["producer_run_id"], "prior_run_id")
    if prior >= current_run_id:
        raise ValueError("SAME_RUN_OR_FUTURE_REGISTRY_REPLAY")
    if type(claim["pr"]) is not int or claim["pr"] != pr:
        raise ValueError("CROSS_PR_REGISTRY_REPLAY")
    if (
        claim["schema"] != SCHEMA
        or claim["partition_digest"] != SOURCE_PARTITION
        or claim["rights_policy_digest"] != RIGHTS_POLICY
        or type(claim["registry_revision"]) is not int
        or claim["registry_revision"] != 1
        or claim["registry_parent_digest"] != GENESIS_REGISTRY
        or type(claim["key_epoch"]) is not int
        or claim["key_epoch"] != 1
        or claim["signer_label"] != "fixture.runner"
        or claim["revoked"] is not False
        or type(claim["floor_generation"]) is not int
        or claim["floor_generation"] != 0
        or claim["floor_digest"] != GENESIS_REGISTRY
        or claim["owner_authorized"] is not False
        or claim["vendor_authorized"] is not False
        or claim["cache_write_authorized"] is not False
    ):
        raise ValueError("UNAUTHORIZED_REGISTRY_OR_FLOOR_CLAIM")
    # A caller-provided minimum can reject rollback, but the caller could reset it.
    if caller_minimum_run_id is not None and prior < caller_minimum_run_id:
        raise ValueError("REGISTRY_BELOW_CALLER_ONLY_FLOOR")
    return {
        "status": "CROSS_RUN_REGISTRY_CACHE_BYTES_VERIFIED_UNATTESTED",
        "prior_run_id": prior,
        "current_run_id": current_run_id,
        "registry_digest": packet["claim_digest"],
        "claim_floor_generation": 0,
        "caller_minimum_was_external": False,
        **DENIED,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("emit", "recover"))
    p.add_argument("--path", required=True, type=Path)
    p.add_argument("--run-id", required=True, type=int)
    p.add_argument("--pr", required=True, type=int)
    p.add_argument("--require-prior", action="store_true")
    p.add_argument("--caller-minimum-run-id", type=int)
    a = p.parse_args(argv)
    if a.mode == "emit":
        a.path.parent.mkdir(parents=True, exist_ok=True)
        a.path.write_text(
            json.dumps(emit_fixture(a.run_id, a.pr), sort_keys=True) + "\n",
            encoding="utf-8",
        )
        result = {
            "status": "CROSS_RUN_REGISTRY_EMITTED_UNATTESTED",
            "run_id": a.run_id,
            "pr": a.pr,
            **DENIED,
        }
    else:
        raw = a.path.read_text(encoding="utf-8") if a.path.is_file() else None
        result = recover_fixture(
            raw, current_run_id=a.run_id, pr=a.pr,
            require_prior=a.require_prior,
            caller_minimum_run_id=a.caller_minimum_run_id,
        )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
