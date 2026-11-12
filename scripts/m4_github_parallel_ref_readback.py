"""Read-only remote GitHub proof for two synthetic parallel ref-update trials.

All inputs are pinned fixture Git commits on explicitly isolated test branches.
The only live operations are GitHub REST GET in an Actions runner. No write
access, Drive market cache, provider credentials, independent writer IDs,
witness signatures, market-data or trading permissions are provided.

Readback cannot itself prove that two API requests arrived concurrently at
GitHub, or that a rejected write happened: those are separate connector events.
"""
from __future__ import annotations

import json
import os

from scripts.m4_github_ref_readback import _get

_PARENT = "4048f91beaaa3410116d97e35896c8b688384e19"
_TRIALS = {
    "r1": {
        "branch": "mst/m4-witness-test-only/race-20261109-r1",
        "winner": "eb74a8c9cbfaa1fc6376b9b02ff837bfb7e7b19f",
        "loser": "98d01322aa057de429f4cf24afb9ecbd7ee1ae13",
        "winner_tree": "ff390765d3e21a89be29167e39607dbd5be59565",
        "loser_tree": "80f999f5dfe28a47699e417f275f37ad517b1372",
    },
    "r2": {
        "branch": "mst/m4-witness-test-only/race-20261109-r2",
        "winner": "3487a1c08faa404aab311ff6fff719f8ba9b8b6a",
        "loser": "8cf9b8340de70422ff7ecc714d11b172df438273",
        "winner_tree": "0a1dc89f5f284b7e9891da4d75ec8f4be46ce027",
        "loser_tree": "bd44cd6315d178a179b023977b508558129699c4",
    },
}
_FALSE_AUTHORITY = {
    "distributed_multiaccount_cas_proven": False,
    "simultaneous_server_arrival_proven": False,
    "connector_requests_were_different_authenticated_accounts": False,
    "server_http_422_proven_by_readback_alone": False,
    "independently_protected_rollback_floor": False,
    "real_google_drive_payload_verified": False,
    "provider_rights_verified": False,
    "trading_authorized": False,
}


def verify_trial(trial_id: str, ref: dict, winner: dict, loser: dict) -> dict:
    if trial_id not in _TRIALS:
        raise ValueError("UNKNOWN_TEST_TRIAL")
    if any(type(value) is not dict for value in (ref, winner, loser)):
        raise TypeError("INVALID_GITHUB_OBJECT_SHAPE")
    cfg = _TRIALS[trial_id]
    if ref.get("ref") != "refs/heads/" + cfg["branch"]:
        raise ValueError("CROSS_BRANCH_READBACK")
    obj = ref.get("object")
    if type(obj) is not dict or obj.get("type") != "commit" or obj.get("sha") != cfg["winner"]:
        raise ValueError("FINAL_HEAD_NOT_EXPECTED_WINNER")
    for label, candidate, sha_key, tree_key in (
        ("WINNER", winner, "winner", "winner_tree"),
        ("LOSER", loser, "loser", "loser_tree"),
    ):
        if candidate.get("sha") != cfg[sha_key]:
            raise ValueError(label + "_COMMIT_SHA_MISMATCH")
        parents = candidate.get("parents")
        if type(parents) is not list or len(parents) != 1 or type(parents[0]) is not dict or parents[0].get("sha") != _PARENT:
            raise ValueError(label + "_SINGLE_PARENT_MISMATCH")
        tree = candidate.get("tree")
        if type(tree) is not dict or tree.get("sha") != cfg[tree_key]:
            raise ValueError(label + "_TREE_SHA_MISMATCH")
    if cfg["winner"] == cfg["loser"] or cfg["winner_tree"] == cfg["loser_tree"]:
        raise ValueError("NOT_DISTINCT_SIBLING_COMMITS")
    return {
        "status": "REMOTE_GITHUB_PARALLEL_ATTEMPT_REF_READBACK_VERIFIED_UNATTESTED",
        "trial": trial_id,
        "branch": cfg["branch"],
        "observed_head": cfg["winner"],
        "losing_sibling": cfg["loser"],
        "shared_parent": _PARENT,
        "remote_git_ref_read_verified": True,
        **_FALSE_AUTHORITY,
    }


def main() -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise PermissionError("GITHUB_HOSTED_ACTIONS_REQUIRED")
    if os.environ.get("GITHUB_REPOSITORY") != "ngluonghoa/MST":
        raise PermissionError("MST_REPOSITORY_REQUIRED")
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        raise PermissionError("PR_EVENT_REQUIRED")
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise PermissionError("READ_ONLY_TOKEN_REQUIRED")
    for trial_id, cfg in _TRIALS.items():
        ref = _get("/git/ref/heads/" + cfg["branch"], token)
        winner = _get("/git/commits/" + cfg["winner"], token)
        loser = _get("/git/commits/" + cfg["loser"], token)
        print(json.dumps(verify_trial(trial_id, ref, winner, loser), sort_keys=True))


if __name__ == "__main__":
    main()
