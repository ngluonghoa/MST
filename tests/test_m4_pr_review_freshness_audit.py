"""Synthetic negative cases for PR8 review events. Never owner acceptance."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from scripts import m4_pr_review_freshness_audit as audit


class ReviewFreshnessAuditTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.head = "a" * 40
        cls.pr = {
            "number": 8, "state": "open", "draft": True, "merged": False,
            "base": {"ref": "main", "sha": audit.PIN},
            "head": {"sha": cls.head, "repo": {"full_name": audit.REPO}},
            "user": {"id": 11, "type": "User"},
        }

    def review(self, index, actor=22, *, kind="User", state="APPROVED",
               commit=None, when=None):
        return {
            "id": index, "user": {"id": actor, "type": kind},
            "state": state, "commit_id": self.head if commit is None else commit,
            "submitted_at": when if when is not None else
            "2026-11-10T10:30:00Z",
        }

    def check(self, events, **kwargs):
        return audit.inspect(self.pr, events, self.head, pages_complete=True, **kwargs)

    def test_01_no_events_still_no_go(self):
        r = self.check([])
        self.assertEqual(r["review_events_seen"], 0)
        self.assertFalse(r["pr8_merge_authorized"])

    def test_02_one_correct_head_non_author_user_is_only_candidate(self):
        r = self.check([self.review(1)])
        self.assertEqual(r["current_head_non_author_user_account_approval_candidates"], 1)
        self.assertFalse(r["reviewer_account_is_distinct_human_controller_proven"])

    def test_03_two_events_same_identity_not_two_approvers(self):
        r = self.check([self.review(1), self.review(2)])
        self.assertEqual(r["current_head_non_author_user_account_approval_candidates"], 1)

    def test_04_two_distinct_user_ids_still_not_independent_control_proof(self):
        r = self.check([self.review(1), self.review(2, actor=33)])
        self.assertEqual(r["current_head_non_author_user_account_approval_candidates"], 2)
        self.assertFalse(r["reviewer_has_effective_write_or_codeowner_permission_proven"])

    def test_05_self_author_approval_is_excluded(self):
        r = self.check([self.review(1, actor=11)])
        self.assertEqual(r["self_author_approvals_not_counted"], 1)
        self.assertEqual(r["current_head_non_author_user_account_approval_candidates"], 0)

    def test_06_bot_review_never_counts(self):
        r = self.check([self.review(1, kind="Bot")])
        self.assertEqual(r["bot_approvals_not_counted"], 1)

    def test_07_stale_commit_approval_never_counts(self):
        r = self.check([self.review(1, commit="b"*40)])
        self.assertEqual(r["stale_commit_approvals_not_counted"], 1)

    def test_08_changes_requested_after_approval_blocks(self):
        r = self.check([self.review(1),
            self.review(2, state="CHANGES_REQUESTED",
                        when="2026-11-10T11:30:00Z")])
        self.assertEqual(r["blocked_latest_review_states"], 1)
        self.assertEqual(r["current_head_non_author_user_account_approval_candidates"], 0)

    def test_09_dismissed_after_approval_blocks(self):
        r = self.check([self.review(1),
            self.review(2, state="DISMISSED",
                        when="2026-11-10T11:30:00Z")])
        self.assertEqual(r["blocked_latest_review_states"], 1)

    def test_10_comment_after_approval_not_promoted(self):
        r = self.check([self.review(1),
            self.review(2, state="COMMENTED",
                        when="2026-11-10T11:30:00Z")])
        self.assertEqual(r["comment_or_pending_latest_not_counted"], 1)

    def test_11_pending_review_does_not_count(self):
        r = self.check([self.review(1, state="PENDING")])
        self.assertEqual(r["current_head_non_author_user_account_approval_candidates"], 0)

    def test_12_new_valid_approval_after_changes_requested_is_candidate(self):
        r = self.check([self.review(1, state="CHANGES_REQUESTED"),
            self.review(2, when="2026-11-10T12:30:00Z")])
        self.assertEqual(r["current_head_non_author_user_account_approval_candidates"], 1)
        self.assertFalse(r["pr8_merge_authorized"])

    def test_13_review_order_input_can_be_reversed(self):
        r = self.check([self.review(2, state="CHANGES_REQUESTED",
                                   when="2026-11-10T12:30:00Z"),
                        self.review(1, when="2026-11-10T10:30:00Z")])
        self.assertEqual(r["blocked_latest_review_states"], 1)

    def test_14_timestamp_timezone_normalization(self):
        r = self.check([self.review(1, when="2026-11-10T10:30:00+00:00")])
        self.assertEqual(r["current_head_non_author_user_account_approval_candidates"], 1)

    def test_15_missing_timestamp_does_not_gain_approval(self):
        event = self.review(1)
        event["submitted_at"] = None
        r = self.check([event])
        self.assertEqual(r["events_without_submitted_timestamp"], 1)

    def test_16_missing_user_does_not_gain_approval(self):
        event = self.review(1)
        event["user"] = None
        r = self.check([event])
        self.assertEqual(r["events_without_verified_account_fields"], 1)

    def test_17_nonpositive_id_rejected(self):
        event = self.review(0)
        with self.assertRaises(ValueError):
            self.check([event])

    def test_18_duplicate_review_event_id_rejected(self):
        with self.assertRaises(ValueError):
            self.check([self.review(1), self.review(1, actor=33)])

    def test_19_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            self.check([self.review(1, state="ALLEGED_APPROVAL")])

    def test_20_invalid_commit_sha_rejected(self):
        event = self.review(1)
        event["commit_id"] = "valid!"
        with self.assertRaises(ValueError):
            self.check([event])

    def test_21_incomplete_pagination_never_proves_review(self):
        with self.assertRaises(PermissionError):
            audit.inspect(self.pr, [self.review(1)], self.head, pages_complete=False)

    def test_22_wrong_event_head_denied(self):
        with self.assertRaises(ValueError):
            audit.inspect(self.pr, [], "f"*40, pages_complete=True)

    def test_23_wrong_base_sha_denied(self):
        pr = deepcopy(self.pr)
        pr["base"]["sha"] = "f"*40
        with self.assertRaises(ValueError):
            audit.inspect(pr, [], self.head, pages_complete=True)

    def test_24_undrafted_pr_denied(self):
        pr = deepcopy(self.pr)
        pr["draft"] = False
        with self.assertRaises(ValueError):
            audit.inspect(pr, [], self.head, pages_complete=True)

    def test_25_no_last_push_authority_proven(self):
        r = self.check([self.review(1)])
        self.assertFalse(r["last_pusher_identity_independently_proven"])
        self.assertFalse(r["github_diff_and_merge_base_freshness_proven"])

    def test_26_no_source_rights_or_trading_ever_granted(self):
        r = self.check([self.review(1), self.review(2, actor=33)])
        self.assertFalse(r["source_rights_and_signer_root_verified"])
        self.assertFalse(r["trading_authorized"])

    def test_27_input_event_keeps_account_ids_out_of_receipt(self):
        r = self.check([self.review(1, actor=987654321)])
        self.assertNotIn("987654321", str(r))
        self.assertNotIn("user_id", str(r))

    def test_28_user_id_boolean_treated_as_invalid(self):
        event = self.review(1)
        event["user"]["id"] = True
        with self.assertRaises(ValueError):
            self.check([event])

    def test_29_pr_author_identity_missing_denied(self):
        pr = deepcopy(self.pr)
        pr["user"] = None
        with self.assertRaises(ValueError):
            audit.inspect(pr, [], self.head, pages_complete=True)

    def test_30_invalid_review_account_type_denied(self):
        event = self.review(1)
        event["user"]["type"] = "Owner"
        with self.assertRaises(ValueError):
            self.check([event])

    def test_31_paginated_fetch_complete_after_partial_last_page(self):
        items = [[self.review(i+1, actor=i+101)
                  for i in range(100)], [self.review(201, actor=202)]]
        calls = []
        def fake_get(path, token):
            calls.append(path)
            return items[len(calls)-1], "VISIBLE"
        with patch.object(audit, "_get", side_effect=fake_get):
            actual = audit.fetch_paginated_reviews("TEST_ONLY")
        self.assertEqual(len(actual), 101)
        self.assertEqual(len(calls), 2)

    def test_32_paginated_fetch_fails_if_page_not_a_list(self):
        with patch.object(audit, "_get", return_value=({}, "VISIBLE")):
            with self.assertRaises(ValueError):
                audit.fetch_paginated_reviews("TEST_ONLY")

    def test_33_future_authority_not_inferred_from_candidate_count(self):
        r = self.check([self.review(1), self.review(2, actor=33)])
        for key in ("reviewed_candidate_is_signed_owner_acceptance",
                    "github_policy_positive_review_enforced_proven",
                    "main_policy_or_acl_modified", "pr8_merge_authorized",
                    "production_release_authorized"):
            self.assertFalse(r[key], key)
