"""MST source lock: check actual GitHub upstream/main/pr-head Git object trees.

This is a GitHub-hosted, READ-ONLY source-parity audit. It verifies the exact
legacy *bytes and tree* but does not certify runtime behavior, licensed market
data, signer custody, protected M4 rollback floor, owner signoff or release.
"""
from __future__ import annotations

import argparse
import json
import os
from urllib.request import Request, urlopen

_UPSTREAM = "ngluonghoa/swing-trading-1-8"
_TARGET = "ngluonghoa/MST"
_SOURCE_COMMIT = "cd90c1babae8912db31490ad614fc2ad2f868042"
_MAIN_COMMIT = "4048f91beaaa3410116d97e35896c8b688384e19"
_TREE = "d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e"
_MAIN_ENTRY_COUNT = 216
_MAIN_BLOB_COUNT = 208
_LEGACY_PY_COUNT = 63
_SRC_PREFIX = "src/swing_trading/"
# Already-known, separate opt-in V2 source modules: additive and NOT V1 rewrites.
# An unreviewed extra package module must fail until explicitly dispositioned.
_ALLOWED_V2_PATHS = frozenset({
    "src/swing_trading/strict_contract_v2.py",
    "src/swing_trading/v2_cache_fencing_lab.py",
    "src/swing_trading/v2_cache_partition_plan.py",
    "src/swing_trading/v2_cloud_publish_verify_lab.py",
    "src/swing_trading/v2_cloud_ref_witness_plan.py",
    "src/swing_trading/v2_provider_readiness.py",
    "src/swing_trading/v2_replay_port.py",
    "src/swing_trading/v2_source_adapter.py",
})


def _objects(data, *, expected_tree=None):
    if type(data) is not dict or data.get("truncated") is not False:
        raise ValueError("REMOTE_GIT_TREE_MISSING_OR_TRUNCATED")
    if expected_tree is not None and data.get("sha") != expected_tree:
        raise ValueError("REMOTE_GIT_TREE_SHA_DRIFT")
    items = data.get("tree")
    if type(items) is not list:
        raise ValueError("REMOTE_GIT_TREE_ENTRY_ARRAY_REQUIRED")
    seen = set()
    for row in items:
        if type(row) is not dict or type(row.get("path")) is not str:
            raise ValueError("REMOTE_GIT_ENTRY_NOT_A_PATH")
        path = row["path"]
        if not path or path.startswith("/") or "\\" in path or any(
            part in ("", ".", "..") for part in path.split("/")
        ):
            raise ValueError("UNSAFE_REMOTE_GIT_PATH")
        if path in seen:
            raise ValueError("DUPLICATE_REMOTE_GIT_PATH")
        seen.add(path)
        if row.get("type") not in ("tree", "blob") or (
            type(row.get("sha")) is not str or len(row["sha"]) != 40
            or any(c not in "0123456789abcdef" for c in row["sha"])
        ):
            raise ValueError("MALFORMED_REMOTE_GIT_ENTRY")
        if type(row.get("mode")) is not str:
            raise ValueError("REMOTE_GIT_MODE_MISSING")
    return {row["path"]: (row["type"], row["mode"], row["sha"]) for row in items}


def _commit_tree(payload, expected_sha):
    if type(payload) is not dict or payload.get("sha") != expected_sha:
        raise ValueError("PINNED_REMOTE_COMMIT_DRIFT")
    tree = payload.get("tree")
    if type(tree) is not dict or tree.get("sha") != _TREE:
        raise ValueError("PINNED_REMOTE_COMMIT_TREE_DRIFT")
    return tree["sha"]


def inspect_live_protected_main(branch_payload):
    """Guard current remote HEAD, not merely a retrievable historical commit."""
    if type(branch_payload) is not dict or branch_payload.get("name") != "main":
        raise ValueError("LIVE_MAIN_BRANCH_NOT_AVAILABLE")
    info = branch_payload.get("commit")
    if (branch_payload.get("protected") is not True
            or type(info) is not dict
            or info.get("sha") != _MAIN_COMMIT):
        raise ValueError("LIVE_PROTECTED_MAIN_MOVED_OR_UNVERIFIABLE")
    return True


def inspect_remote_legacy_parity(upstream_commit, mst_main_commit,
                                 upstream_tree, mst_main_tree,
                                 candidate_tree, *, candidate_sha):
    """Insist on exact full-tree parity on main and original package parity in PR."""
    if type(candidate_sha) is not str or len(candidate_sha) != 40 or any(
        c not in "0123456789abcdef" for c in candidate_sha
    ):
        raise ValueError("INVALID_CANDIDATE_SHA")
    _commit_tree(upstream_commit, _SOURCE_COMMIT)
    _commit_tree(mst_main_commit, _MAIN_COMMIT)
    original = _objects(upstream_tree, expected_tree=_TREE)
    baseline = _objects(mst_main_tree, expected_tree=_TREE)
    candidate = _objects(candidate_tree)
    if original != baseline:
        raise ValueError("REMOTE_BASELINE_TREE_CONTENT_MISMATCH")
    if len(original) != _MAIN_ENTRY_COUNT or sum(
        v[0] == "blob" for v in original.values()
    ) != _MAIN_BLOB_COUNT:
        raise ValueError("REMOTE_PINNED_SOURCE_TREE_COUNT_DRIFT")
    package = {p: meta for p, meta in original.items()
               if p.startswith(_SRC_PREFIX) and meta[0] == "blob"}
    package_py = [p for p in package if p.endswith(".py")]
    if len(package_py) != _LEGACY_PY_COUNT:
        raise ValueError("REMOTE_LEGACY_MODULE_COUNT_DRIFT")
    original_source_paths = {p: v for p, v in original.items()
                             if p.startswith(_SRC_PREFIX)}
    candidate_source_paths = {p: v for p, v in candidate.items()
                              if p.startswith(_SRC_PREFIX)}
    # Original 63 Python modules and any inherited package metadata remain
    # byte-identical. Additive V2 is allowed ONLY at eight reviewed filenames.
    for path, original_meta in original_source_paths.items():
        if candidate_source_paths.get(path) != original_meta:
            raise ValueError("PR_CANDIDATE_INHERITED_SOURCE_CHANGED")
    extras = set(candidate_source_paths) - set(original_source_paths)
    if extras != _ALLOWED_V2_PATHS:
        raise ValueError("PR_CANDIDATE_V2_SIDECAR_ALLOWLIST_DRIFT")
    for path in extras:
        if candidate_source_paths[path][0:2] != ("blob", "100644"):
            raise ValueError("PR_CANDIDATE_V2_SIDECAR_OBJECT_TYPE_DRIFT")
    return {
        "schema": "mst.source-1to1.github-remote-tree-lock.readonly.v1",
        "status": "ORIGINAL_TREE_1TO1_LEGACY_63_UNCHANGED_AND_EIGHT_V2_SIDECARS",
        "upstream_source_commit": _SOURCE_COMMIT,
        "mst_main_commit": _MAIN_COMMIT,
        "shared_original_tree_sha": _TREE,
        "current_remote_main_protected_and_pinned": True,
        "original_git_tree_entry_count": len(original),
        "original_git_blob_count": sum(
            meta[0] == "blob" for meta in original.values()
        ),
        "original_python_module_count": len(package_py),
        "candidate_head_sha_checked": candidate_sha,
        "all_original_tree_entries_match_between_source_and_main": True,
        "inherited_python_source_unchanged_on_pr": True,
        "all_inherited_package_paths_unchanged_on_pr": True,
        "approved_opt_in_v2_sidecar_module_count": len(extras),
        "only_exact_eight_known_v2_sidecars_added_on_pr": True,
        "v2_business_behavior_parity_verified": False,
        "a02_owner_module_review_signed_off": False,
        "license_and_real_cache_authorized": False,
        "m4_witness_admin_independence_proven": False,
        "production_release_authorized": False,
        "trading_authorized": False,
    }


def _get(repo, endpoint, *, token):
    url = f"https://api.github.com/repos/{repo}/{endpoint}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "mst-original-source-parity-readonly-ci",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    with urlopen(Request(url, headers=headers), timeout=20) as resp:
        return json.load(resp)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    if not (os.getenv("GITHUB_ACTIONS") == "true"
            and os.getenv("GITHUB_REPOSITORY") == _TARGET
            and os.getenv("GITHUB_EVENT_NAME") == "pull_request"):
        raise PermissionError("ONLY_SAME_REPO_HOSTED_PR_REVIEW_SUPPORTED")
    head = os.getenv("GITHUB_HEAD_SHA")
    token = os.getenv("GITHUB_TOKEN", "")
    live_main = _get(_TARGET, "branches/main", token=token)
    inspect_live_protected_main(live_main)
    up_commit = _get(_UPSTREAM, "git/commits/" + _SOURCE_COMMIT, token=token)
    mst_commit = _get(_TARGET, "git/commits/" + _MAIN_COMMIT, token=token)
    up_tree = _get(_UPSTREAM, "git/trees/" + _TREE + "?recursive=1", token=token)
    mst_tree = _get(_TARGET, "git/trees/" + _TREE + "?recursive=1", token=token)
    candidate_commit = _get(_TARGET, "git/commits/" + head, token=token)
    if candidate_commit.get("sha") != head:
        raise ValueError("REMOTE_PR_CANDIDATE_HEAD_DRIFT")
    tree_sha = candidate_commit.get("tree", {}).get("sha")
    if type(tree_sha) is not str or len(tree_sha) != 40:
        raise ValueError("REMOTE_PR_CANDIDATE_TREE_NOT_AVAILABLE")
    candidate_tree = _get(_TARGET, "git/trees/" + tree_sha + "?recursive=1", token=token)
    if candidate_tree.get("sha") != tree_sha:
        raise ValueError("REMOTE_PR_CANDIDATE_TREE_SHA_DRIFT")
    report = inspect_remote_legacy_parity(
        up_commit, mst_commit, up_tree, mst_tree, candidate_tree,
        candidate_sha=head,
    )
    if args.out:
        from pathlib import Path
        Path(args.out).write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                                  encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
