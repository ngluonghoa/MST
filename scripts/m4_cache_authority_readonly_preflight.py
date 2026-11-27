"""MST M4 read-only *negative* authority preflight for an EXISTING lab ref.

This script does not write to GitHub or Google Drive; does not implement CAS,
and can NEVER grant production authority. Read-only metadata is not an
enforcement test. Reuse PR8 M4's observed ref/ruleset evidence, but inspect
the CURRENT control-plane policy instead of replaying a hard-coded fixture.
"""
from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO = "ngluonghoa/MST"
REPO_ID = 1450356304
REF = "refs/heads/mst/m4-ref-cas-lab-20261109"
EXPECTED_LAB_SHA = "869b64d348b88ceb272408d1a1dabd668ba720d6"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
API_ROOT = "https://api.github.com/repos/" + REPO
MAX_BODY = 1024 * 1024
MAX_RULESETS = 50

# Independently unproven until an owner-approved private authority exists.
INDEPENDENT_GATES = (
    "NO_PRIVATE_CONTROL_REPO",
    "NO_AUTHENTICATED_INDEPENDENT_WRITER",
    "NO_NONROLLBACKABLE_SIGNED_LATEST_FLOOR",
    "NO_DURABLE_TRANSACTIONAL_PUBLISH_RECEIPT",
    "NO_REAL_TWO_WRITER_ENFORCEMENT_TEST",
    "NO_VENDOR_SOURCE_RIGHTS_OR_SIX_TF_ATTESTATION",
    "NO_APPROVED_REAL_DRIVE_WRITER",
)


class PreflightError(RuntimeError):
    """No authority statement can be made from incomplete/invalid evidence."""


def _object(value, label):
    if type(value) is not dict:
        raise PreflightError("INVALID_" + label)
    return value


def _get(path: str, token: str):
    """Fixed-path GitHub REST GET; reject non-allowlisted paths, bound bytes."""
    if type(token) is not str or not token:
        raise PreflightError("READ_ONLY_TOKEN_REQUIRED")
    paths = {"", "/rulesets", "/git/ref/heads/mst/m4-ref-cas-lab-20261109",
             "/branches/mst/m4-ref-cas-lab-20261109"}
    if path not in paths and not re.fullmatch(r"/rulesets/[1-9][0-9]{0,12}", path):
        raise PreflightError("NON_READONLY_OR_OUT_OF_SCOPE_ENDPOINT")
    req = Request(
        API_ROOT + path,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "MST-M4-Authority-ReadOnly-NOGO",
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=15) as response:
            if response.status != 200:
                raise PreflightError("GITHUB_READ_NON_200")
            if response.headers.get("Link", "").find('rel="next"') != -1:
                raise PreflightError("GITHUB_RESULT_PAGINATED_INCOMPLETE")
            body = response.read(MAX_BODY + 1)
    except (HTTPError, URLError, OSError):
        # No URLs, bearer tokens, or raw exception details in status/logs.
        raise PreflightError("GITHUB_READ_UNAVAILABLE") from None
    if len(body) > MAX_BODY:
        raise PreflightError("GITHUB_READ_OVERSIZE")
    try:
        return json.loads(body)
    except (UnicodeError, ValueError):
        raise PreflightError("GITHUB_READ_INVALID_JSON") from None


def preflight(repo_info, refs, branch, ruleset_list, details) -> dict:
    """One-way proof of NO-GO from actual GitHub-shaped metadata.

    Does NOT assert effective protection, even when one matching ruleset
    exists; a separate signer, trust anchor, role split and race test are
    mandatory. Invalid/incomplete evidence throws and fails CI.
    """
    r = _object(repo_info, "REPO")
    ref = _object(refs, "REF")
    b = _object(branch, "BRANCH")
    if type(ruleset_list) is not list or type(details) is not list:
        raise PreflightError("INVALID_RULESET_COLLECTION")
    if len(ruleset_list) > MAX_RULESETS or len(details) != len(ruleset_list):
        raise PreflightError("INCOMPLETE_RULESET_CENSUS")
    if (r.get("full_name") != REPO or type(r.get("id")) is not int or
            r["id"] != REPO_ID or r.get("default_branch") != "main" or
            type(r.get("private")) is not bool):
        raise PreflightError("REPOSITORY_IDENTITY_MISMATCH")
    if ref.get("ref") != REF:
        raise PreflightError("LAB_REF_IDENTITY_MISMATCH")
    obj = _object(ref.get("object"), "REF_OBJECT")
    if obj.get("type") != "commit" or not HEX40.fullmatch(str(obj.get("sha", ""))):
        raise PreflightError("NONCANONICAL_LAB_REF")
    if b.get("name") != REF.removeprefix("refs/heads/"):
        raise PreflightError("BRANCH_NAME_MISMATCH")
    bc = _object(b.get("commit"), "BRANCH_COMMIT")
    if bc.get("sha") != obj["sha"] or type(b.get("protected")) is not bool:
        raise PreflightError("BRANCH_REF_READBACK_MISMATCH")
    if obj["sha"] != EXPECTED_LAB_SHA:
        raise PreflightError("EXISTING_LAB_HEAD_DRIFT_REVIEW_REQUIRED")

    active = []
    exact = []
    main_only = []
    seen = set()
    for listing, item in zip(ruleset_list, details):
        listing = _object(listing, "RULESET_SUMMARY")
        item = _object(item, "RULESET_DETAIL")
        rule_id = listing.get("id")
        if (type(rule_id) is not int or rule_id <= 0 or rule_id in seen or
                item.get("id") != rule_id):
            raise PreflightError("DUPLICATED_OR_MISSING_RULESET_DETAIL")
        seen.add(rule_id)
        if item.get("source") != REPO or item.get("target") != "branch":
            # Organization- or enterprise-scoped effective rules may differ.
            # We do not interpret foreign scope or presume it absent.
            continue
        if item.get("enforcement") != "active":
            continue
        active.append(rule_id)
        conditions = _object(item.get("conditions"), "RULESET_CONDITIONS")
        ref_name = _object(conditions.get("ref_name"), "RULESET_REF_CONDITIONS")
        include, exclude = ref_name.get("include"), ref_name.get("exclude")
        if type(include) is not list or type(exclude) is not list or any(
            type(x) is not str for x in include + exclude
        ):
            raise PreflightError("RULESET_SCOPE_NOT_VERIFIABLE")
        if include == ["~DEFAULT_BRANCH"] and not exclude:
            main_only.append(rule_id)
        # Only a LITERAL exact-path inclusion is structural evidence.
        # Wildcards may match but are not treated as demonstrated protection.
        if REF in include and not exclude:
            exact.append(rule_id)

    reasons = list(INDEPENDENT_GATES)
    if r["private"] is False:
        reasons.append("MST_REPOSITORY_IS_PUBLIC")
    if not exact:
        reasons.append("NO_EXPLICIT_EXACT_REF_RULESET")
    if b["protected"] is False:
        reasons.append("LAB_BRANCH_NOT_MARKED_PROTECTED")
    return {
        "decision": "NO_GO",
        "evidence": "READ_ONLY_GITHUB_METADATA_NOT_ENFORCEMENT",
        "repo": REPO,
        "repo_private": r["private"],
        "lab_ref": REF,
        "lab_ref_head": obj["sha"],
        "lab_branch_protected_metadata": b["protected"],
        "rulesets_examined": len(seen),
        "active_repository_ruleset_ids": sorted(active),
        "main_only_ruleset_ids": sorted(main_only),
        "literal_exact_ref_ruleset_ids": sorted(exact),
        "reasons": sorted(reasons),
        "external_cas_proven": False,
        "current_trusted_floor_proven": False,
        "market_cache_authorized": False,
        "production_authorized": False,
        "writes_performed": False,
    }


def main() -> None:
    if (os.environ.get("GITHUB_ACTIONS") != "true" or
        os.environ.get("GITHUB_REPOSITORY") != REPO or
        os.environ.get("GITHUB_EVENT_NAME") != "pull_request"):
        raise PreflightError("GITHUB_ACTIONS_EXACT_REPO_PR_ONLY")
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise PreflightError("READ_ONLY_TOKEN_REQUIRED")
    info = _get("", token)
    ref = _get("/git/ref/heads/mst/m4-ref-cas-lab-20261109", token)
    branch = _get("/branches/mst/m4-ref-cas-lab-20261109", token)
    rulesets = _get("/rulesets", token)
    if type(rulesets) is not list or len(rulesets) > MAX_RULESETS:
        raise PreflightError("RULESET_CENSUS_UNVERIFIABLE")
    detailed = []
    for item in rulesets:
        item = _object(item, "RULESET_SUMMARY")
        rule_id = item.get("id")
        if type(rule_id) is not int or rule_id <= 0:
            raise PreflightError("RULESET_ID_INVALID")
        detailed.append(_get("/rulesets/" + str(rule_id), token))
    print(json.dumps(preflight(info, ref, branch, rulesets, detailed), sort_keys=True))


if __name__ == "__main__":
    main()
