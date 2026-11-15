"""§203 opt-in real GitHub GET-only preflight; CI exercises FAKE transport.

The production CLI has no connected credentials or automatic workflow trigger.
This file NEVER sends HTTP; no personal token, private repo, ref or price data.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from io import BytesIO, StringIO
from copy import deepcopy
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.mst_highwater_owner_cloud_readonly_probe import (
    OwnerCloudProbeDenied, _http_getter, _strict_json, main,
    probe_private_highwater_access,
)

PRIVATE_REPO = "fake-owner/highwater-custody-test"
SERIES = "MST_FAKE_SERIES_20261115"
BRANCH = "highwater/" + SERIES
BASE = "/repos/" + PRIVATE_REPO
REF = "refs/heads/" + BRANCH
OLD_SHA = "a" * 40


def replies():
    return {
        BASE: {
            "id": 13579, "full_name": PRIVATE_REPO,
            "owner": {"login": "fake-owner"},
            "private": True, "visibility": "private", "archived": False,
        },
        BASE + "/git/ref/heads/" + BRANCH: {
            "ref": REF, "object": {"type": "commit", "sha": OLD_SHA},
        },
        BASE + "/rules/branches/highwater%2F" + SERIES + "?per_page=100&page=1": [
            {"type": "deletion"}, {"type": "non_fast_forward"},
            {"type": "required_linear_history"},
        ],
        BASE + "/rulesets?includes_parents=true&per_page=100&page=1": [
            {"id": 2, "target": "branch", "enforcement": "active"},
        ],
        BASE + "/rulesets/2?includes_parents=true": {
            "id": 2, "target": "branch", "enforcement": "active",
            "bypass_actors": [],
        },
    }


def fake_transport(data, calls):
    def get(path):
        calls.append(path)
        if path not in data:
            raise AssertionError("unexpected fake GitHub path")
        return deepcopy(data[path])
    return get


def examine(*, data=None, mode="inspect-ref", repo=PRIVATE_REPO,
            series=SERIES):
    logs = []
    result = probe_private_highwater_access(
        repo=repo, series=series, mode=mode,
        read_json=fake_transport(data if data is not None else replies(), logs),
    )
    return result, logs


class OwnerHighwaterCloudReadOnlyProbeTests(unittest.TestCase):
    def test_repository_only_makes_exactly_one_fake_get(self):
        r, calls = examine(mode="repo-only")
        self.assertEqual(calls, [BASE])
        self.assertTrue(r["private_repo_response_matches_request"])
        self.assertFalse(r["exact_series_ref_observed"])
        self.assertFalse(r["highwater_ref_write_authorized"])
        self.assertFalse(r["production_cache_published"])

    def test_full_fake_private_repo_reads_no_write(self):
        r, calls = examine()
        self.assertEqual(len(calls), 5)
        self.assertEqual(calls[0], BASE)
        self.assertEqual(calls[-1], BASE + "/rulesets/2?includes_parents=true")
        self.assertTrue(r["exact_series_ref_observed"])
        self.assertTrue(r["effective_rules_observed"])
        self.assertTrue(r["required_branch_rule_types_reported"])
        self.assertTrue(r["active_ruleset_observed"])
        self.assertTrue(r["all_ruleset_bypass_actor_details_visible"])
        for key in (
            "owner_key_or_tip_externally_authenticated",
            "plan_entitlement_confirmed",
            "real_private_repo_immutable_or_monotone",
            "atomic_cas_proven", "highwater_ref_write_authorized",
            "production_cache_published", "signals_eligible",
        ):
            self.assertFalse(r[key], key)

    def test_missing_bypass_metadata_never_becomes_empty_bypass_proof(self):
        data = replies()
        data[BASE + "/rulesets/2?includes_parents=true"].pop("bypass_actors")
        r, _ = examine(data=data)
        self.assertFalse(r["all_ruleset_bypass_actor_details_visible"])
        self.assertFalse(r["highwater_ref_write_authorized"])

    def test_reported_bypass_actors_do_not_authorize(self):
        data = replies()
        data[BASE + "/rulesets/2?includes_parents=true"][
            "bypass_actors"
        ] = [{"actor_id": 1, "actor_type": "RepositoryRole",
              "bypass_mode": "always"}]
        r, _ = examine(data=data)
        self.assertFalse(r["all_ruleset_bypass_actor_details_visible"])
        self.assertFalse(r["atomic_cas_proven"])

    def test_missing_one_required_rule_stays_ineligible(self):
        data = replies()
        data[BASE + "/rules/branches/highwater%2F" + SERIES + "?per_page=100&page=1"].pop()
        r, _ = examine(data=data)
        self.assertFalse(r["required_branch_rule_types_reported"])
        self.assertFalse(r["highwater_ref_write_authorized"])

    def test_ruleset_disabled_or_evaluate_not_active(self):
        for status in ("disabled", "evaluate"):
            with self.subTest(status=status):
                data = replies()
                data[BASE + "/rulesets?includes_parents=true&per_page=100&page=1"][0][
                    "enforcement"
                ] = status
                r, calls = examine(data=data)
                self.assertFalse(r["active_ruleset_observed"])
                self.assertFalse(r["all_ruleset_bypass_actor_details_visible"])
                self.assertEqual(len(calls), 4)

    def test_public_mismatched_or_archived_repository_denied(self):
        for key, value in (
            ("private", False), ("visibility", "public"),
            ("full_name", "ngluonghoa/MST"), ("archived", True),
            ("id", True), ("id", 0),
        ):
            with self.subTest(key=key), self.assertRaisesRegex(
                OwnerCloudProbeDenied, "OWNER_PRIVATE_REPO_NOT_VERIFIED"
            ):
                data = replies()
                data[BASE][key] = value
                examine(data=data, mode="repo-only")

    def test_missing_git_ref_or_wrong_commit_type_sha_denied(self):
        for key, value in (
            ("ref", "refs/heads/main"),
            ("object", {"type": "tag", "sha": OLD_SHA}),
            ("object", {"type": "commit", "sha": "bad"}),
            ("object", None),
        ):
            with self.subTest(key=key), self.assertRaisesRegex(
                OwnerCloudProbeDenied, "EXACT_GIT_REF_NOT_VERIFIED"
            ):
                data = replies()
                data[BASE + "/git/ref/heads/" + BRANCH][key] = value
                examine(data=data)

    def test_private_repo_input_never_accepts_source_mst_or_injection(self):
        for bad in ("ngluonghoa/MST", "owner/repo/extra",
                    "bad", "../repo", "owner/..", "owner/repo?token",
                    "owner/repo\nleak"):
            with self.subTest(bad=bad), self.assertRaises(
                OwnerCloudProbeDenied
            ):
                examine(repo=bad, mode="repo-only")

    def test_series_id_wrong_or_unbounded_denied(self):
        for series in ("", "BAD", "a" * 81, "../main", "bad/ref",
                       True, None):
            with self.subTest(series=series), self.assertRaises(
                OwnerCloudProbeDenied,
            ):
                examine(series=series, mode="repo-only")

    def test_missing_or_invalid_probe_mode_denied(self):
        for mode in ("", "write", "test-cas", None, True):
            with self.subTest(mode=mode), self.assertRaisesRegex(
                OwnerCloudProbeDenied, "PROBE_MODE_INVALID"
            ):
                examine(mode=mode)

    def test_effective_rules_incomplete_page_malformed_denied(self):
        path = BASE + "/rules/branches/highwater%2F" + SERIES + "?per_page=100&page=1"
        for value in ({}, [1], [{"type": True}],
                      [{"type": "a"}] * 100):
            with self.subTest(type=type(value).__name__), self.assertRaises(
                OwnerCloudProbeDenied
            ):
                data = replies()
                data[path] = value
                examine(data=data)

    def test_ruleset_list_pagination_missing_or_bad_denied(self):
        path = BASE + "/rulesets?includes_parents=true&per_page=100&page=1"
        for value in ({}, [1], [None], [{"id": 1}] * 100):
            with self.subTest(type=type(value).__name__), self.assertRaises(
                OwnerCloudProbeDenied
            ):
                data = replies()
                data[path] = value
                examine(data=data)

    def test_active_ruleset_malformed_or_inconsistent_denied(self):
        path = BASE + "/rulesets/2?includes_parents=true"
        for key, value in (
            ("id", 3), ("target", "tag"),
            ("enforcement", "disabled"),
            ("bypass_actors", None),
        ):
            with self.subTest(key=key), self.assertRaises(
                OwnerCloudProbeDenied
            ):
                data = replies()
                data[path][key] = value
                examine(data=data)

    def test_active_ruleset_id_bad_or_count_over_limit_denied(self):
        path = BASE + "/rulesets?includes_parents=true&per_page=100&page=1"
        for value in (True, "2", -1, None):
            with self.subTest(value=value), self.assertRaisesRegex(
                OwnerCloudProbeDenied, "ACTIVE_RULESET_ID_INVALID"
            ):
                data = replies()
                data[path][0]["id"] = value
                examine(data=data)
        data = replies()
        data[path] = [
            {"id": i+1, "target": "branch", "enforcement": "active"}
            for i in range(17)
        ]
        def count_transport(p):
            if p == path:
                return data[path]
            if p.startswith(BASE + "/rulesets/"):
                rid = int(p.split("/rulesets/")[1].split("?")[0])
                return {"id": rid, "target": "branch", "enforcement": "active",
                        "bypass_actors": []}
            return deepcopy(data[p])
        with self.assertRaisesRegex(
            OwnerCloudProbeDenied, "ACTIVE_RULESET_COUNT_EXCEEDED"
        ):
            probe_private_highwater_access(
                repo=PRIVATE_REPO, series=SERIES, mode="inspect-ref",
                read_json=count_transport,
            )

    def test_strict_json_rejects_duplicate_keys_invalid_nan_or_long_bytes(self):
        for value in (
            b'{"a":1,"a":2}', b'{"nan":NaN}',
            b"{" + b"x" * (256 * 1024 + 1), b"", None,
        ):
            with self.subTest(value=str(value)[:20]), self.assertRaises(
                OwnerCloudProbeDenied,
            ):
                _strict_json(value)
        self.assertEqual(_strict_json(b'{"ok":true}')["ok"], True)

    def test_missing_or_invalid_token_never_gets_network_client(self):
        for token in ("", "contains\nnewline", "a" * 4097, None):
            with self.subTest(length=len(token) if token else 0), self.assertRaisesRegex(
                OwnerCloudProbeDenied, "READ_TOKEN_UNAVAILABLE"
            ):
                _http_getter(token)

    def test_http_url_scope_is_fixed_to_github_repository(self):
        get = _http_getter("FAKE_SHOULD_NOT_BE_USED")
        for url in (
            "https://attacker.invalid/steal", "//evil.invalid/repo",
            "/orgs/o", "/repos/o/../private", "/repos/o/a?evil=1\nanything",
        ):
            with self.subTest(url=url), self.assertRaisesRegex(
                OwnerCloudProbeDenied, "URL_SCOPE_INVALID"
            ):
                get(url)

    def test_main_without_env_secrets_returns_only_safe_no_go(self):
        with patch.dict(os.environ, {}, clear=True):
            capture = StringIO()
            with redirect_stdout(capture):
                rc = main()
            self.assertEqual(rc, 2)
            result = json.loads(capture.getvalue())
            self.assertEqual(result["status"], "NO_GO")
            self.assertFalse(any(x in capture.getvalue() for x in (
                "Bearer", "FAKE", "private repo",
            )))

    def test_main_can_execute_fake_get_only_without_printing_private_ids(self):
        data = replies()
        with patch.dict(os.environ, {
            "MST_HIGHWATER_CUSTODY_REPO": PRIVATE_REPO,
            "MST_HIGHWATER_SERIES_ID": SERIES,
            "MST_HIGHWATER_PROBE_MODE": "inspect-ref",
            "MST_HIGHWATER_READ_TOKEN": "FICTIONAL_ONLY_123",
        }, clear=True):
            with patch(
                "scripts.mst_highwater_owner_cloud_readonly_probe._http_getter",
                return_value=fake_transport(data, []),
            ):
                capture = StringIO()
                with redirect_stdout(capture):
                    rc = main()
        self.assertEqual(rc, 0)
        out = capture.getvalue()
        for sensitive in (PRIVATE_REPO, SERIES, OLD_SHA, "FICTIONAL_ONLY_123"):
            self.assertNotIn(sensitive, out)
        self.assertFalse(json.loads(out)["highwater_ref_write_authorized"])

    def test_actual_transport_never_sends_non_get_requests(self):
        calls = []
        class FakeResponse:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return False
            def read(self, *_):
                return b'{"private":true}'
        class FakeOpener:
            def open(self, req, timeout):
                calls.append((req.get_method(), req.full_url, timeout,
                              req.get_header("Authorization")))
                return FakeResponse()
        with patch(
            "scripts.mst_highwater_owner_cloud_readonly_probe.build_opener",
            return_value=FakeOpener(),
        ):
            value = _http_getter("FAKE_TOKEN_123")("/repos/owner/private")
        self.assertEqual(value, {"private": True})
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:3],
                         ("GET", "https://api.github.com/repos/owner/private", 10))
        self.assertEqual(calls[0][3], "Bearer FAKE_TOKEN_123")

    def test_sanitized_http_404_does_not_expose_token_or_private_url(self):
        class FakeOpener:
            def open(self, req, timeout):
                raise HTTPError(
                    req.full_url, 404, "secret/not-found", {}, BytesIO(b"secret"),
                )
        with patch(
            "scripts.mst_highwater_owner_cloud_readonly_probe.build_opener",
            return_value=FakeOpener(),
        ):
            with self.assertRaisesRegex(
                OwnerCloudProbeDenied, "^MST_203_HTTP_READ_FAILED$"
            ):
                _http_getter("FAKE_SECRET_TOKEN_123")(
                    "/repos/fake-owner/highwater-secret"
                )


if __name__ == "__main__":
    unittest.main()
