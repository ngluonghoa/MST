"""M4 PR8 review-event freshness and account-dedup screening, read-only NO-GO.

Classifies GitHub REST user-account review events under a single CI token.
A current-head APPROVED event is neither independently controlled identity
nor proof of code-owner permission, last-push approval, signer or rights.
No raw login, user ID, review body or private account data is printed.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re

from scripts.m4_main_positive_review_preflight import (
    _get, REPO, PIN,
)

SCHEMA = "mst.m4.pr8.review-freshness-technical-observation.no-go.v1"
_SHA = re.compile(r"^[a-f0-9]{40}$")
_STATES = {"APPROVED", "CHANGES_REQUESTED", "COMMENTED", "DISMISSED", "PENDING"}
_MAX_PAGES = 20
_PAGE_SIZE = 100


def _timestamp(value):
    if type(value) is not str or not value:
        return None
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return t if t.tzinfo is not None else None
    except ValueError:
        return None


def _author(pr):
    user = pr.get("user")
    if type(user) is not dict or type(user.get("id")) is not int or user["id"] <= 0:
        raise ValueError("PR_AUTHOR_ID_NOT_VISIBLE_CANNOT_ASSIGN_INDEPENDENCE")
    return user["id"]


def inspect(pr: dict, reviews: list, head: str, *, pages_complete: bool) -> dict:
    """Return only counts, not IDs. Review events never authorize a merge."""
    if type(pr) is not dict or type(reviews) is not list:
        raise TypeError("REAL_PR_AND_REVIEW_ARRAY_REQUIRED")
    if type(head) is not str or not _SHA.fullmatch(head):
        raise ValueError("EXACT_PR_HEAD_SHA_REQUIRED")
    base = pr.get("base")
    tip = pr.get("head")
    if (pr.get("number") != 8 or pr.get("state") != "open"
        or pr.get("draft") is not True or pr.get("merged") is not False
        or type(base) is not dict or base.get("ref") != "main"
        or base.get("sha") != PIN or type(tip) is not dict
        or tip.get("sha") != head or type(tip.get("repo")) is not dict
        or tip["repo"].get("full_name") != REPO):
        raise ValueError("DRAFT_PR8_OR_BASE_OR_HEAD_CHANGED")
    if pages_complete is not True:
        raise PermissionError("PAGINATION_INCOMPLETE_NO_REVIEW_PROOF")
    if len(reviews) > _MAX_PAGES * _PAGE_SIZE:
        raise ValueError("UNBOUNDED_REVIEW_COLLECTION")
    author_id = _author(pr)
    events = []
    seen_ids = set()
    for event in reviews:
        if type(event) is not dict:
            raise TypeError("REVIEW_EVENT_INVALID")
        review_id = event.get("id")
        if type(review_id) is not int or review_id < 1 or review_id in seen_ids:
            raise ValueError("REVIEW_ID_MISSING_OR_DUPLICATE")
        seen_ids.add(review_id)
        state = event.get("state")
        if state not in _STATES:
            raise ValueError("REVIEW_STATE_UNKNOWN")
        if event.get("commit_id") is not None and (
                type(event["commit_id"]) is not str
                or _SHA.fullmatch(event["commit_id"]) is None):
            raise ValueError("REVIEW_COMMIT_INVALID")
        user = event.get("user")
        if user is not None and type(user) is not dict:
            raise TypeError("REVIEWER_USER_OBJECT_INVALID")
        user_id = user.get("id") if user is not None else None
        user_type = user.get("type") if user is not None else None
        if user_id is not None and (type(user_id) is not int or user_id < 1):
            raise ValueError("REVIEWER_ID_INVALID")
        if user_type is not None and user_type not in ("User", "Bot"):
            raise ValueError("REVIEWER_ACCOUNT_TYPE_UNSUPPORTED")
        timestamp = _timestamp(event.get("submitted_at"))
        # Pending, incomplete and unknown-time records cannot earn approval.
        events.append((user_id, user_type, review_id, state,
                       event.get("commit_id"), timestamp))
    latest = {}
    missing_identity = 0
    malformed_time = 0
    for user_id, user_type, event_id, state, commit, stamp in events:
        if user_id is None or user_type is None:
            missing_identity += 1
            continue
        if stamp is None:
            malformed_time += 1
            continue
        prev = latest.get(user_id)
        if prev is None or (stamp, event_id) > (prev[0], prev[1]):
            latest[user_id] = (stamp, event_id, user_type, state, commit)
    current_head_non_author_user_accounts = 0
    stale_commit_approvals = 0
    author_events_excluded = 0
    bot_events_excluded = 0
    blocked_latest = 0
    non_approval_latest = 0
    for user_id, (_, _, kind, state, commit) in latest.items():
        if state in ("CHANGES_REQUESTED", "DISMISSED"):
            blocked_latest += 1
            continue
        if state != "APPROVED":
            non_approval_latest += 1
            continue
        if user_id == author_id:
            author_events_excluded += 1
            continue
        if kind != "User":
            bot_events_excluded += 1
            continue
        if commit != head:
            stale_commit_approvals += 1
            continue
        current_head_non_author_user_accounts += 1
    return {
        "schema": SCHEMA,
        "status": "PR_REVIEW_ACCOUNT_EVENTS_SCANNED_INDEPENDENT_AUTHORITY_NOT_PROVEN_NO_GO",
        "readback_complete_under_page_cap": True,
        "pr8_event_head_matches_readback": True,
        "review_events_seen": len(events),
        "distinct_review_account_ids_seen": len(latest),
        "current_head_non_author_user_account_approval_candidates":
            current_head_non_author_user_accounts,
        "stale_commit_approvals_not_counted": stale_commit_approvals,
        "self_author_approvals_not_counted": author_events_excluded,
        "bot_approvals_not_counted": bot_events_excluded,
        "blocked_latest_review_states": blocked_latest,
        "comment_or_pending_latest_not_counted": non_approval_latest,
        "events_without_verified_account_fields": missing_identity,
        "events_without_submitted_timestamp": malformed_time,
        "reviewer_account_is_distinct_human_controller_proven": False,
        "reviewer_has_effective_write_or_codeowner_permission_proven": False,
        "last_pusher_identity_independently_proven": False,
        "github_policy_positive_review_enforced_proven": False,
        "github_diff_and_merge_base_freshness_proven": False,
        "reviewed_candidate_is_signed_owner_acceptance": False,
        "source_rights_and_signer_root_verified": False,
        "main_policy_or_acl_modified": False,
        "pr8_merge_authorized": False,
        "production_release_authorized": False,
        "trading_authorized": False,
    }


def fetch_paginated_reviews(token: str) -> list:
    """Fetch each page explicitly; fail closed on a full terminal page."""
    output = []
    for page in range(1, _MAX_PAGES + 1):
        item, _ = _get(f"/pulls/8/reviews?per_page={_PAGE_SIZE}&page={page}", token)
        if type(item) is not list:
            raise ValueError("REVIEW_PAGINATION_SHAPE_INVALID")
        if len(item) > _PAGE_SIZE:
            raise ValueError("REVIEW_PAGINATION_PAGE_EXCEEDS_LIMIT")
        output.extend(item)
        if len(item) < _PAGE_SIZE:
            return output
    raise PermissionError("REVIEW_PAGINATION_NOT_EXHAUSTIVE_NO_GO")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if (os.getenv("GITHUB_ACTIONS") != "true"
        or os.getenv("GITHUB_REPOSITORY") != REPO
        or os.getenv("GITHUB_EVENT_NAME") != "pull_request"):
        raise PermissionError("PR8_GITHUB_ACTIONS_READONLY_ONLY")
    token = os.getenv("GITHUB_TOKEN")
    head = os.getenv("GITHUB_HEAD_SHA")
    if not token or not head:
        raise PermissionError("GITHUB_HEAD_SHA_AND_READ_ONLY_TOKEN_REQUIRED")
    pr, _ = _get("/pulls/8", token)
    events = fetch_paginated_reviews(token)
    pr_again, _ = _get("/pulls/8", token)
    if (pr.get("head", {}).get("sha") != pr_again.get("head", {}).get("sha")
        or pr.get("base", {}).get("sha") != pr_again.get("base", {}).get("sha")
        or pr.get("draft") != pr_again.get("draft")):
        raise PermissionError("PR_HEAD_MOVED_DURING_REVIEW_SCAN_RETRY_SEPARATELY")
    result = inspect(pr_again, events, head, pages_complete=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
