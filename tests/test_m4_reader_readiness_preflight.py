"""M4 reader readiness: deny all production uses of read-only REST metadata."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.m4_reader_readiness_preflight import (
    _BASE, _DENIED, _GATES, _REF, _get_witness_ref,
    read_only_readiness,
)

PROPOSAL = json.loads(Path(
    "docs/MST_M4_WITNESS_RULESET_PROPOSAL_20261109.json"
).read_text(encoding="utf-8"))


def main_branch():
    return {"name": "main", "protected": True, "commit": {"sha": _BASE}}


def witness_ref():
    return {"ref": _REF, "object": {"type": "commit", "sha": "a" * 40}}


def rule():
    return {
        "id": 701,
        "name": PROPOSAL["proposed_ruleset"]["name"],
        "source_type": "Repository",
        "source": "ngluonghoa/MST",
        "target": "branch",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": [_REF], "exclude": []}},
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {"type": "required_signatures"},
        ],
        "bypass_actors": [],
        "current_user_can_bypass": "never",
    }


class BlockingReadinessContractTests(unittest.TestCase):
    def inspect(self, *, proposal=None, main=None, summaries=None,
                details=None, witness=None):
        if summaries is None:
            summaries = []
        if details is None:
            details = {}
        return read_only_readiness(
            PROPOSAL if proposal is None else proposal,
            main_branch() if main is None else main,
            summaries, details, witness,
        )

    def assert_all_denied(self, result):
        self.assertIn("BLOCKED", result["status"])
        self.assertEqual(result["owner_gates_still_open"], list(_GATES))
        self.assertEqual(len(_GATES), 8)
        self.assertIs(result["witness_actual_owner_authorization"], False)
        self.assertIs(
            result["witness_active_protection_effective_end_to_end_verified"], False,
        )
        for k in _DENIED:
            self.assertIs(result[k], False, k)

    def test_realistic_main_only_and_no_witness_is_blocked(self):
        result = self.inspect()
        self.assertFalse(result["witness_ref_exists_for_this_read"])
        self.assertFalse(result["witness_ruleset_visible_for_this_token"])
        self.assertIsNone(result["witness_ref_head_sha_for_this_read"])
        self.assertTrue(result["main_baseline_verified_for_this_read"])
        self.assert_all_denied(result)

    def test_witness_branch_exists_but_no_protected_rule_is_blocked(self):
        result = self.inspect(witness=witness_ref())
        self.assertTrue(result["witness_ref_exists_for_this_read"])
        self.assertFalse(result["witness_ruleset_metadata_matches_for_this_token"])
        self.assert_all_denied(result)

    def test_perfect_looking_remote_witness_and_ruleset_still_not_owner_approved(self):
        r = rule()
        result = self.inspect(
            witness=witness_ref(), summaries=[r], details={r["id"]: r},
        )
        self.assertTrue(result["witness_ruleset_metadata_matches_for_this_token"])
        self.assertTrue(result["witness_bypass_list_visible_for_this_token"])
        self.assertEqual(result["witness_ref_head_sha_for_this_read"], "a" * 40)
        self.assert_all_denied(result)

    def test_matching_rule_without_branch_does_not_authorize(self):
        r = rule()
        result = self.inspect(summaries=[r], details={r["id"]: r})
        self.assertTrue(result["witness_ruleset_metadata_matches_for_this_token"])
        self.assertFalse(result["witness_ref_exists_for_this_read"])
        self.assert_all_denied(result)

    def test_token_missing_bypass_list_does_not_silently_prove_empty(self):
        r = rule()
        r.pop("bypass_actors")
        value = self.inspect(witness=witness_ref(), summaries=[r],
                             details={r["id"]: r})
        self.assertFalse(value["witness_bypass_list_visible_for_this_token"])
        self.assert_all_denied(value)

    def test_unreviewed_bypass_actor_is_rejected(self):
        r = rule()
        r["bypass_actors"] = [{"actor_id": 1, "actor_type": "OrganizationAdmin"}]
        with self.assertRaisesRegex(ValueError, "UNREVIEWED_BYPASS"):
            self.inspect(witness=witness_ref(), summaries=[r], details={r["id"]: r})

    def test_current_token_bypass_is_rejected(self):
        r = rule()
        r["current_user_can_bypass"] = "always"
        with self.assertRaisesRegex(ValueError, "CURRENT_ACTOR_CAN_BYPASS"):
            self.inspect(witness=witness_ref(), summaries=[r], details={r["id"]: r})

    def test_unprotected_or_wrong_main_is_not_treated_as_a_witness(self):
        for m in (
            {"name": "main", "protected": False, "commit": {"sha": _BASE}},
            {"name": "other", "protected": True, "commit": {"sha": _BASE}},
            {"name": "main", "protected": 1, "commit": {"sha": _BASE}},
        ):
            with self.subTest(m=m), self.assertRaisesRegex(
                ValueError, "MAIN_NOT_PROTECTED"
            ):
                self.inspect(main=m)

    def test_moved_main_head_breaks_pinned_baseline(self):
        with self.assertRaisesRegex(ValueError, "PINNED_SOURCE_MAIN_HEAD_DRIFT"):
            self.inspect(main={"name": "main", "protected": True,
                               "commit": {"sha": "f" * 40}})

    def test_missing_main_commit_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "MAIN_HEAD_DRIFT"):
            self.inspect(main={"name": "main", "protected": True})

    def test_untyped_main_is_rejected(self):
        for v in ([], True, "main", 7):
            with self.subTest(v=v), self.assertRaises(TypeError):
                self.inspect(main=v)

    def test_witness_ref_wrong_name_is_rejected(self):
        r = witness_ref()
        r["ref"] = "refs/heads/main"
        with self.assertRaisesRegex(ValueError, "WRONG_REMOTE_WITNESS_REF"):
            self.inspect(witness=r)

    def test_witness_ref_tree_or_tag_is_not_valid_head(self):
        for kind in ("tree", "tag", "blob", None):
            r = witness_ref()
            r["object"]["type"] = kind
            with self.subTest(kind=kind), self.assertRaisesRegex(
                ValueError, "NOT_COMMIT"
            ):
                self.inspect(witness=r)

    def test_malformed_remote_witness_sha_fails_closed(self):
        for sha in ("Z" * 40, "1" * 20, None, True, "A" * 40):
            r = witness_ref()
            r["object"]["sha"] = sha
            with self.subTest(sha=sha), self.assertRaisesRegex(
                ValueError, "MALFORMED_WITNESS_HEAD"
            ):
                self.inspect(witness=r)

    def test_remote_witness_must_be_object_or_real_404(self):
        for raw in ([], False, "missing", 0):
            with self.subTest(raw=raw), self.assertRaises(TypeError):
                self.inspect(witness=raw)

    def test_unverified_ruleset_detail_id_is_not_accepted(self):
        r = rule()
        with self.assertRaisesRegex(ValueError, "DETAIL_REQUIRED"):
            self.inspect(summaries=[r], details={})

    def test_cross_owner_ruleset_rejected(self):
        r = rule()
        r["source"] = "someone-else/MST"
        with self.assertRaisesRegex(ValueError, "WRONG_OWNER"):
            self.inspect(summaries=[r], details={701: r})

    def test_duplicate_matching_rulesets_are_ambiguous(self):
        r = rule()
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS_DUPLICATE"):
            self.inspect(summaries=[r, dict(r, id=702)], details={701: r})

    def test_wrong_exact_ref_ruleset_scope_is_rejected(self):
        r = rule()
        r["conditions"]["ref_name"]["include"] = ["~DEFAULT_BRANCH"]
        with self.assertRaisesRegex(ValueError, "WRONG_OR_OVERBROAD_SCOPE"):
            self.inspect(summaries=[r], details={701: r})

    def test_ruleset_does_not_have_required_signatures(self):
        r = rule()
        r["rules"] = [{"type": "deletion"}, {"type": "non_fast_forward"}]
        with self.assertRaisesRegex(ValueError, "PROTECTIONS_MISSING"):
            self.inspect(summaries=[r], details={701: r})

    def test_proposal_self_certification_is_not_owner_approval(self):
        p = deepcopy(PROPOSAL)
        p["guardrails"]["owner_approval_received"] = True
        with self.assertRaisesRegex(ValueError, "PREMATURE_APPROVAL"):
            self.inspect(proposal=p)

    def test_proposal_bypass_changes_are_rejected(self):
        p = deepcopy(PROPOSAL)
        p["proposed_ruleset"]["bypass_actors"] = [
            {"actor_id": 5, "actor_type": "RepositoryRole"}
        ]
        with self.assertRaisesRegex(ValueError, "PROPOSAL_BYPASS"):
            self.inspect(proposal=p)

    def test_main_protected_does_not_count_as_signer_root(self):
        result = self.inspect()
        self.assertTrue(result["main_baseline_verified_for_this_read"])
        self.assertFalse(result["independent_owner_signer_verified"])
        self.assertFalse(result["licensed_vendor_first_known_verified"])
        self.assertFalse(result["cache_read_authorized"])
        self.assert_all_denied(result)

    def test_real_404_means_missing_ref_not_empty_authorized_state(self):
        exc = HTTPError(
            "https://api.github.com/not-real", 404, "Not Found", {}, None,
        )
        with patch(
            "scripts.m4_reader_readiness_preflight._get_json", side_effect=exc
        ):
            self.assertIsNone(_get_witness_ref("fake-token"))

    def test_any_non_404_api_error_propagates(self):
        for code in (401, 403, 429, 500):
            exc = HTTPError(
                "https://api.github.com/not-real", code, "Error", {}, None,
            )
            with self.subTest(code=code), patch(
                "scripts.m4_reader_readiness_preflight._get_json", side_effect=exc
            ), self.assertRaises(HTTPError):
                _get_witness_ref("fake-token")

    def test_successful_git_ref_read_does_not_promote_source_rights(self):
        r = witness_ref()
        with patch(
            "scripts.m4_reader_readiness_preflight._get_json", return_value=r
        ):
            self.assertEqual(_get_witness_ref("fake-token"), r)
        self.assert_all_denied(self.inspect(witness=r))


if __name__ == "__main__":
    unittest.main()
