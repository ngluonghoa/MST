"""GitHub Actions synthetic cross-RUN cache continuity probe.

Untrusted CI CACHE, not vendor rights, protected source head, signed publisher,
cross-account CAS, durable rollback floor, market payload, Drive data or trade.
Contains NO network/credential access. All data is made up.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

_SCHEMA = "mst.m4.synthetic-cross-run-unattested.v1"
_HEX = re.compile(r"^[a-f0-9]{64}$")
_GIT = re.compile(r"^[a-f0-9]{40}$")
_SOURCE_HEAD = "1" * 40
_PARTITION = "a" * 64
_CONTENT = "b" * 64
_NON_AUTH = {
    "real_google_drive_readback": False,
    "independent_witness": False,
    "durable_rollback_floor": False,
    "distributed_cas": False,
    "vendor_entitlement": False,
    "market_data_authorized": False,
    "trading_authorized": False,
}


def canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")


def emit_claim(run_id: int, pr_number: int) -> dict:
    if type(run_id) is not int or run_id < 1:
        raise ValueError("RUN_ID_MUST_BE_POSITIVE")
    if type(pr_number) is not int or pr_number < 1:
        raise ValueError("PR_NUMBER_MUST_BE_POSITIVE")
    claim = {
        "schema": _SCHEMA,
        "run_id": run_id,
        "pr_number": pr_number,
        "phase": "SYNTHETIC_JOURNAL_STAGED_ONLY",
        "partition_sha256": _PARTITION,
        "expected_git_head_sha1": _SOURCE_HEAD,
        "content_sha256": _CONTENT,
        "operation_id": f"fixture-pr{pr_number}-run{run_id}",
        "witness_authorized": False,
    }
    return {"claim": claim, "claim_sha256": sha256(canonical(claim)).hexdigest()}


def recover_claim(raw: str | None, *, current_run_id: int,
                  pr_number: int, require_prior: bool = False) -> dict:
    if type(current_run_id) is not int or current_run_id < 1:
        raise ValueError("INVALID_CURRENT_RUN_ID")
    if type(pr_number) is not int or pr_number < 1:
        raise ValueError("INVALID_EXPECTED_PR")
    if raw is None:
        if require_prior:
            raise ValueError("NO_CROSS_RUN_CACHE_FOUND")
        return {
            "status": "BOOTSTRAP_NO_PRIOR_CACHE",
            "prior_run_id": None,
            "current_run_id": current_run_id,
            "pr_number": pr_number,
            **_NON_AUTH,
        }
    try:
        receipt = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("INVALID_FIXTURE_JSON") from exc
    if type(receipt) is not dict or set(receipt) != {"claim", "claim_sha256"}:
        raise ValueError("NON_CANONICAL_RECEIPT_SHAPE")
    claim = receipt["claim"]
    if type(claim) is not dict or set(claim) != {
        "schema", "run_id", "pr_number", "phase", "partition_sha256",
        "expected_git_head_sha1", "content_sha256", "operation_id",
        "witness_authorized",
    }:
        raise ValueError("NON_CANONICAL_CLAIM_SHAPE")
    if type(receipt["claim_sha256"]) is not str or not _HEX.fullmatch(receipt["claim_sha256"]):
        raise ValueError("INVALID_CONTENT_CHECKSUM")
    if sha256(canonical(claim)).hexdigest() != receipt["claim_sha256"]:
        raise ValueError("CORRUPTED_CACHED_FIXTURE")
    prior_run_id = claim["run_id"]
    if type(prior_run_id) is not int or not (0 < prior_run_id < current_run_id):
        raise ValueError("SAME_RUN_OR_NON_MONOTONIC_RUN_ID")
    if type(claim["pr_number"]) is not int or claim["pr_number"] != pr_number:
        raise ValueError("CROSS_PR_CACHE_REUSE")
    if (claim["schema"] != _SCHEMA or
        claim["phase"] != "SYNTHETIC_JOURNAL_STAGED_ONLY" or
        claim["partition_sha256"] != _PARTITION or
        claim["expected_git_head_sha1"] != _SOURCE_HEAD or
        claim["content_sha256"] != _CONTENT or
        claim["operation_id"] != f"fixture-pr{pr_number}-run{prior_run_id}" or
        claim["witness_authorized"] is not False):
        raise ValueError("MISMATCHED_OR_UNTRUSTED_CLAIM")
    return {
        "status": "CROSS_RUN_CACHE_BYTES_VERIFIED_UNATTESTED",
        "prior_run_id": prior_run_id,
        "current_run_id": current_run_id,
        "pr_number": pr_number,
        **_NON_AUTH,
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("emit", "recover"))
    parser.add_argument("--path", required=True, type=Path)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--require-prior", action="store_true")
    args = parser.parse_args(argv)
    if args.mode == "emit":
        args.path.parent.mkdir(parents=True, exist_ok=True)
        value = emit_claim(args.run_id, args.pr)
        args.path.write_text(json.dumps(value, sort_keys=True,
                                        separators=(",", ":")) + "\n")
        print(json.dumps({
            "status": "SYNTHETIC_INTENT_EMITTED_UNATTESTED",
            "run_id": args.run_id, "pr_number": args.pr,
            **_NON_AUTH,
        }, sort_keys=True))
    else:
        text = args.path.read_text() if args.path.exists() else None
        result = recover_claim(text, current_run_id=args.run_id,
                               pr_number=args.pr, require_prior=args.require_prior)
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
