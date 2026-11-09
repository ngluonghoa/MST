"""Read-only GitHub-hosted M4 ref integrity proof for one synthetic test ref.

The only live I/O is three GitHub REST GETs, from a GitHub-hosted Actions
runner with contents:read. Never mutate refs, Drive, provider data or main.
A remote Git commit relationship is not a signed source, an independently
protected rollback floor, a distributed writer CAS or production authority.
"""
from __future__ import annotations

import json
import os
import re
from urllib.request import Request, urlopen

_REPO = "ngluonghoa/MST"
_BRANCH = "mst/m4-witness-test-only/cas-proof-20261109-1543"
_BASE = "4048f91beaaa3410116d97e35896c8b688384e19"
_A = "c3e4e91670766d416d9eaedfce36ba12189a9427"
_B = "e4faef0f83bc925ec8b511fc1aa5ad321fa79f74"
_TREE_A = "e40b8463438eb359145a3d027a7aaa74a8df3a4c"
_TREE_B = "4bd4a4a7585ec54ab668cb327af2a55638aeb376"
_HEX40 = re.compile(r"^[a-f0-9]{40}$")

_AUTH_FLAGS = {
    "vendor_rights_verified": False,
    "source_clock_authenticated": False,
    "google_drive_payload_verified": False,
    "independently_protected_floor": False,
    "distributed_multiaccount_cas_verified": False,
    "production_write_authorized": False,
    "trading_authorized": False,
}


def verify_readback(ref, a, b):
    """Strictly verify three independently retrieved GitHub-shaped resources.

    Returns a TEST-ONLY observation, not a cross-service transaction receipt.
    """
    if any(type(x) is not dict for x in (ref, a, b)):
        raise TypeError("EXACT_GITHUB_OBJECTS_REQUIRED")
    if ref.get("ref") != "refs/heads/" + _BRANCH:
        raise ValueError("WRONG_BRANCH_REF")
    item = ref.get("object")
    if type(item) is not dict or item.get("type") != "commit" or item.get("sha") != _A:
        raise ValueError("UNEXPECTED_FINAL_HEAD")
    for label, candidate, commit, expected_tree in (
        ("A", a, _A, _TREE_A), ("B", b, _B, _TREE_B),
    ):
        if candidate.get("sha") != commit:
            raise ValueError("CANDIDATE_" + label + "_SHA_MISMATCH")
        parents = candidate.get("parents")
        if type(parents) is not list or len(parents) != 1 or type(parents[0]) is not dict:
            raise ValueError("CANDIDATE_" + label + "_PARENT_SHAPE")
        if parents[0].get("sha") != _BASE:
            raise ValueError("CANDIDATE_" + label + "_NOT_CHILD_OF_BASE")
        tree = candidate.get("tree")
        if type(tree) is not dict or tree.get("sha") != expected_tree:
            raise ValueError("CANDIDATE_" + label + "_TREE_MISMATCH")
        if not _HEX40.fullmatch(commit) or not _HEX40.fullmatch(expected_tree):
            raise ValueError("NON_CANONICAL_GIT_ID")
    if _A == _B or _TREE_A == _TREE_B:
        raise ValueError("CANDIDATES_NOT_DISTINCT")
    return {
        "status": "REMOTE_GITHUB_REF_AND_SIBLING_COMMITS_VERIFIED_TEST_ONLY",
        "branch": _BRANCH,
        "observed_head": _A,
        "losing_candidate": _B,
        "shared_parent": _BASE,
        "github_ref_observed": True,
        "remote_non_fast_forward_denial_proven_by_this_read": False,
        **_AUTH_FLAGS,
    }


def _get(path: str, token: str) -> dict:
    if type(token) is not str or not token:
        raise ValueError("GITHUB_TOKEN_REQUIRED")
    req = Request(
        "https://api.github.com/repos/" + _REPO + path,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "MST-M4-ReadOnly-Fixture-20261109",
        },
    )
    with urlopen(req, timeout=15) as resp:
        result = json.load(resp)
    if type(result) is not dict:
        raise ValueError("UNEXPECTED_GITHUB_RESPONSE")
    return result


def main() -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise PermissionError("GITHUB_HOSTED_ACTIONS_REQUIRED")
    if os.environ.get("GITHUB_REPOSITORY") != _REPO:
        raise PermissionError("EXACT_MST_REPOSITORY_REQUIRED")
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        raise PermissionError("PR_EVENT_REQUIRED")
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise PermissionError("READ_ONLY_ACTIONS_TOKEN_REQUIRED")
    ref = _get("/git/ref/heads/" + _BRANCH, token)
    a = _get("/git/commits/" + _A, token)
    b = _get("/git/commits/" + _B, token)
    print(json.dumps(verify_readback(ref, a, b), sort_keys=True))


if __name__ == "__main__":
    main()
