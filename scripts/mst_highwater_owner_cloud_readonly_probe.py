"""§203 opt-in GitHub Cloud REST read-only private highwater access probe.

Unlike §196–§202 synthetic diagnostics, the optional CLI can issue actual
GET requests to api.github.com with owner-supplied, repository-restricted
READ-ONLY installation credentials. CI unit tests always inject fake GETs;
no workflow invokes this CLI or provides credentials.

NO writes, GitHub App creation, OAuth change, branch update, vendor API, key
signing, production Cache, scheduled task, broker or trade.

A successfully fetched GitHub ruleset does not prove that it cannot later be
disabled or bypassed, that a principal is independently trustworthy, or
that a Git ref is a separate immutable, monotone CAS ledger. The GitHub API
may hide bypass_actors unless the requesting principal has ruleset-write
access. Missing bypass details are NEVER equivalent to empty bypass.
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import (
    HTTPRedirectHandler, HTTPSHandler, Request, build_opener,
)

REPO = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}\Z")
SERIES = re.compile(r"[A-Za-z0-9_-]{8,80}\Z")
GITSHA = re.compile(r"[0-9a-f]{40}\Z")
MAX_REPLY = 256 * 1024
REQUIRED_BRANCH_RULES = frozenset((
    "deletion", "non_fast_forward", "required_linear_history",
))


class OwnerCloudProbeDenied(ValueError):
    """Only stable sanitized errors: NEVER embed raw HTTP/keys/repo names."""


def _denied(code: str) -> None:
    raise OwnerCloudProbeDenied(code)


def _validate(target: Any, series: Any, mode: Any) -> tuple[str, str, str]:
    if (type(target) is not str or REPO.fullmatch(target) is None
            or target.lower() == "ngluonghoa/mst"):
        _denied("MST_203_PRIVATE_CUSTODY_REPOSITORY_INVALID")
    if type(mode) is not str or mode not in ("repo-only", "inspect-ref"):
        _denied("MST_203_PROBE_MODE_INVALID")
    if type(series) is not str or SERIES.fullmatch(series) is None:
        _denied("MST_203_SERIES_ID_INVALID")
    return target, series, mode


def _strict_json(raw: bytes) -> Any:
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_REPLY:
        _denied("MST_203_RESPONSE_SIZE_INVALID")

    def distinct(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for key, value in pairs:
            if key in data:
                _denied("MST_203_DUPLICATE_JSON_KEY")
            data[key] = value
        return data

    try:
        return json.loads(
            raw.decode("utf-8"), object_pairs_hook=distinct,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except OwnerCloudProbeDenied:
        raise
    except (ValueError, UnicodeError, RecursionError, TypeError):
        _denied("MST_203_RESPONSE_JSON_INVALID")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _denied("MST_203_HTTP_REDIRECT_REFUSED")


def _http_getter(token: str) -> Callable[[str], Any]:
    if (type(token) is not str or not 1 <= len(token) <= 4096
            or any(ord(c) < 33 or ord(c) > 126 for c in token)):
        _denied("MST_203_READ_TOKEN_UNAVAILABLE")
    opener = build_opener(HTTPSHandler(), _NoRedirect())

    def get(path: str) -> Any:
        if (type(path) is not str or not path.startswith("/repos/")
                or not re.fullmatch(r"[A-Za-z0-9_./?=&%+~-]{1,280}", path)
                or ".." in path or path.startswith("//")):
            _denied("MST_203_URL_SCOPE_INVALID")
        url = "https://api.github.com" + path
        req = Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + token,
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "MST-private-highwater-readonly-preflight",
            },
            method="GET",
        )
        try:
            with opener.open(req, timeout=10) as response:
                if response.status != 200:
                    _denied("MST_203_HTTP_NOT_SUCCESS")
                wire = response.read(MAX_REPLY + 1)
        except OwnerCloudProbeDenied:
            raise
        except (HTTPError, URLError, TimeoutError, OSError):
            # No untrusted HTTP/URL/headers/errors printed or persisted.
            _denied("MST_203_HTTP_READ_FAILED")
        return _strict_json(wire)

    return get


def probe_private_highwater_access(
    *, repo: Any, series: Any, mode: Any,
    read_json: Callable[[str], Any],
) -> dict[str, Any]:
    """Perform bounded GET-only observations, returning REDACTED status flags.

    The caller must provide a GitHub-App user/installation token with access
    to the separate private owner repo. Permission scoping must be externally
    reviewed. This method does not authenticate its injected fetcher.
    """
    target, series, mode = _validate(repo, series, mode)
    if not callable(read_json):
        _denied("MST_203_READ_TRANSPORT_INVALID")
    root = "/repos/" + target
    info = read_json(root)
    if (type(info) is not dict
            or info.get("full_name") != target
            or info.get("private") is not True
            or info.get("visibility") != "private"
            or info.get("archived") is not False
            or type(info.get("id")) is not int
            or info["id"] < 1
            or type(info.get("owner")) is not dict
            or info["owner"].get("login") != target.split("/")[0]):
        _denied("MST_203_OWNER_PRIVATE_REPO_NOT_VERIFIED")

    report = {
        "schema": "mst.cloud.owner_private_highwater_actual_read_probe.v0.1",
        "probe_mode": mode,
        "injected_get_transport_independently_authenticated": False,
        "private_repo_response_matches_request": True,
        "exact_series_ref_observed": False,
        "effective_rules_observed": False,
        "required_branch_rule_types_reported": False,
        "active_ruleset_observed": False,
        "all_ruleset_bypass_actor_details_visible": False,
        "owner_key_or_tip_externally_authenticated": False,
        "plan_entitlement_confirmed": False,
        "real_private_repo_immutable_or_monotone": False,
        "atomic_cas_proven": False,
        "highwater_ref_write_authorized": False,
        "production_cache_published": False,
        "signals_eligible": False,
    }
    if mode == "repo-only":
        return report

    branch = "highwater/" + series
    reference = read_json(root + "/git/ref/heads/" + branch)
    if (type(reference) is not dict
            or reference.get("ref") != "refs/heads/" + branch
            or type(reference.get("object")) is not dict
            or reference["object"].get("type") != "commit"
            or type(reference["object"].get("sha")) is not str
            or GITSHA.fullmatch(reference["object"]["sha"]) is None):
        _denied("MST_203_EXACT_GIT_REF_NOT_VERIFIED")
    report["exact_series_ref_observed"] = True

    rules_path = (root + "/rules/branches/" + quote(branch, safe="")
                  + "?per_page=100&page=1")
    effective = read_json(rules_path)
    if (type(effective) is not list or len(effective) >= 100
            or any(type(item) is not dict
                   or type(item.get("type")) is not str
                   for item in effective)):
        _denied("MST_203_EFFECTIVE_RULES_INVALID_OR_INCOMPLETE")
    types = {item["type"] for item in effective}
    report["effective_rules_observed"] = True
    report["required_branch_rule_types_reported"] = (
        REQUIRED_BRANCH_RULES.issubset(types)
    )

    # Only page 1 and <100 can be treated as potentially complete with this
    # narrow transport. 100 entries might have another page: fail closed.
    listed = read_json(root + "/rulesets?includes_parents=true&per_page=100&page=1")
    if (type(listed) is not list or len(listed) >= 100
            or any(type(item) is not dict for item in listed)):
        _denied("MST_203_RULESET_LIST_INCOMPLETE")
    active_count = 0
    has_unknown_bypass = False
    for item in listed:
        if item.get("target") != "branch" or item.get("enforcement") != "active":
            continue
        ruleset_id = item.get("id")
        if type(ruleset_id) is not int or ruleset_id < 1:
            _denied("MST_203_ACTIVE_RULESET_ID_INVALID")
        active_count += 1
        if active_count > 16:
            _denied("MST_203_ACTIVE_RULESET_COUNT_EXCEEDED")
        detail = read_json(root + "/rulesets/" + str(ruleset_id) +
                           "?includes_parents=true")
        if (type(detail) is not dict or detail.get("id") != ruleset_id
                or detail.get("target") != "branch"
                or detail.get("enforcement") != "active"):
            _denied("MST_203_ACTIVE_RULESET_DETAIL_MISMATCH")
        if "bypass_actors" not in detail:
            has_unknown_bypass = True
        elif type(detail["bypass_actors"]) is not list:
            _denied("MST_203_BYPASS_ACTORS_MALFORMED")
        elif detail["bypass_actors"]:
            has_unknown_bypass = True
    report["active_ruleset_observed"] = active_count > 0
    # Even if API returned an empty list, effective policies or privileges
    # can change after this read. This flag is only OBSERVABILITY, not trust.
    report["all_ruleset_bypass_actor_details_visible"] = (
        active_count > 0 and not has_unknown_bypass
    )
    return report


def main() -> int:
    """Opt-in via owner-supplied secrets; never run on CI automatically."""
    target = os.environ.get("MST_HIGHWATER_CUSTODY_REPO", "")
    series = os.environ.get("MST_HIGHWATER_SERIES_ID", "")
    mode = os.environ.get("MST_HIGHWATER_PROBE_MODE", "repo-only")
    token = os.environ.get("MST_HIGHWATER_READ_TOKEN", "")
    try:
        _validate(target, series, mode)
        fetch = _http_getter(token)
        result = probe_private_highwater_access(
            repo=target, series=series, mode=mode, read_json=fetch,
        )
    except OwnerCloudProbeDenied as exc:
        print(json.dumps({"schema": "mst.cloud.readonly_probe_denied.v0.1",
                          "status": "NO_GO", "code": str(exc)}))
        return 2
    # Only fixed safe booleans and status metadata; no repo name, ref SHA,
    # credential, private response, ruleset ID or raw market data emitted.
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
