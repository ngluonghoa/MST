"""Read-only Option A GitHub & Drive evidence: no fake custody promotion."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError

from scripts.m4_option_a_live_custody_audit import (
    MAIN_PIN, REPO, REQUIRED_CONTEXTS, RULESET_NAME, WITNESS,
    _classify_rest_error, inspect_drive_snapshot, inspect_github_custody,
)

DRIVE = json.loads(Path(
    "docs/MST_M4_OPTION_A_DRIVE_ACL_OBSERVATION_20261109.json"
).read_text(encoding="utf-8"))


def main():
    return {"name": "main", "protected": True, "commit": {"sha": MAIN_PIN}}


def ruleset():
    return {
        "id": 26801439,
        "name": RULESET_NAME,
        "target": "branch",
        "source_type": "Repository",
        "source": REPO,
        "enforcement": "active",
        "conditions": {"ref_name": {
            "include": ["~DEFAULT_BRANCH"], "exclude": [],
        }},
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {"type": "pull_request", "parameters": {
                "required_approving_review_count": 0,
                "allowed_merge_methods": ["merge", "squash", "rebase"],
            }},
            {"type": "required_status_checks", "parameters": {
                "required_status_checks": [
                    {"context": ctx, "integration_id": 15368}
                    for ctx in sorted(REQUIRED_CONTEXTS)
                ],
            }},
        ],
        "bypass_actors": [],
        "current_user_can_bypass": "never",
    }


def witness():
    return {"ref": WITNESS, "object": {"sha": "a" * 40, "type": "commit"}}


class OptionAGithubLiveRulesetContracts(unittest.TestCase):
    def inspect(self, *, m=None, summary=None, rule=None, witness_ref=None,
                classic="INACCESSIBLE_TO_TOKEN_403"):
        r = ruleset() if rule is None else rule
        return inspect_github_custody(
            main() if m is None else m,
            [r] if summary is None else summary,
            {r["id"]: r},
            witness_ref,
            classic,
        )

    def assert_denied(self, x):
        self.assertIn("BLOCKED", x["status"])
        for field in (
            "witness_owner_control_independently_attested",
            "github_admin_reset_impossible_proven",
            "two_independent_principals_verified",
            "global_signer_revocation_verified",
            "protected_external_monotonic_floor_verified",
            "physical_drive_market_cache_verified",
            "cache_read_authorized", "cache_write_authorized",
            "trading_authorized",
        ):
            self.assertIs(x[field], False, field)

    def test_actual_main_ruleset_shape_and_zero_approval_accurately_labeled(self):
        x = self.inspect()
        self.assertTrue(x["main_requires_pr_in_visible_rule"])
        self.assertEqual(x["main_required_approval_count"], 0)
        self.assertFalse(x["main_has_positive_approval_requirement"])
        self.assertFalse(x["main_requires_signed_commits_in_visible_rule"])
        self.assertTrue(x["all_three_foundation_checks_required"])
        self.assertTrue(x["main_bypass_actor_list_empty_for_this_read"])
        self.assertFalse(x["witness_ref_exists_in_readback"])
        self.assert_denied(x)

    def test_hypothetical_positive_reviews_do_not_authorize_witness(self):
        r = ruleset()
        r["rules"][2]["parameters"]["required_approving_review_count"] = 2
        x = self.inspect(rule=r, witness_ref=witness())
        self.assertTrue(x["main_has_positive_approval_requirement"])
        self.assertTrue(x["witness_ref_exists_in_readback"])
        self.assert_denied(x)

    def test_hypothetical_signed_commits_do_not_prove_owner_signer(self):
        r = ruleset()
        r["rules"].append({"type": "required_signatures"})
        x = self.inspect(rule=r)
        self.assertTrue(x["main_requires_signed_commits_in_visible_rule"])
        self.assert_denied(x)

    def test_unknown_bypass_list_cannot_claim_empty(self):
        r = ruleset()
        del r["bypass_actors"]
        x = self.inspect(rule=r)
        self.assertFalse(x["main_bypass_actor_list_visible"])
        self.assertFalse(x["main_bypass_actor_list_empty_for_this_read"])
        self.assert_denied(x)

    def test_explicit_admin_bypass_does_not_promote(self):
        r = ruleset()
        r["bypass_actors"] = [{"actor_type": "OrganizationAdmin", "actor_id": 9}]
        r["current_user_can_bypass"] = "always"
        x = self.inspect(rule=r)
        self.assertFalse(x["main_bypass_actor_list_empty_for_this_read"])
        self.assertEqual(x["current_token_can_bypass"], "always")
        self.assert_denied(x)

    def test_missing_required_check_is_detected_without_fake_ready(self):
        r = ruleset()
        r["rules"][3]["parameters"]["required_status_checks"].pop()
        x = self.inspect(rule=r)
        self.assertFalse(x["all_three_foundation_checks_required"])
        self.assert_denied(x)

    def test_pinned_main_sha_drift_fails_closed(self):
        m = main()
        m["commit"]["sha"] = "f" * 40
        with self.assertRaisesRegex(ValueError, "PIN_DRIFT"):
            self.inspect(m=m)

    def test_main_protection_false_fails_closed(self):
        m = main()
        m["protected"] = False
        with self.assertRaisesRegex(ValueError, "PROTECTION_OR_SOURCE_PIN_DRIFT"):
            self.inspect(m=m)

    def test_main_metadata_untyped_denied(self):
        for m in ([], None, True, "main"):
            with self.subTest(m=m), self.assertRaises(ValueError):
                self.inspect(m=m)

    def test_duplicate_ruleset_name_fails_closed(self):
        r = ruleset()
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS"):
            self.inspect(summary=[r, deepcopy(r)])

    def test_unknown_ruleset_missing_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "MISSING"):
            self.inspect(summary=[])

    def test_wrong_owner_denied(self):
        r = ruleset()
        r["source"] = "someone/MST"
        with self.assertRaisesRegex(ValueError, "WRONG_RULESET_OWNER"):
            self.inspect(rule=r)

    def test_inactive_ruleset_denied(self):
        r = ruleset()
        r["enforcement"] = "disabled"
        with self.assertRaisesRegex(ValueError, "WRONG_RULESET_OWNER_OR_INACTIVE"):
            self.inspect(rule=r)

    def test_wrong_ref_scope_denied(self):
        r = ruleset()
        r["conditions"]["ref_name"]["include"] = ["refs/heads/develop"]
        with self.assertRaisesRegex(ValueError, "DEFAULT_BRANCH_NOT_COVERED"):
            self.inspect(rule=r)

    def test_missing_non_ff_rule_denied(self):
        r = ruleset()
        r["rules"] = [x for x in r["rules"] if x["type"] != "non_fast_forward"]
        with self.assertRaisesRegex(ValueError, "EXPECTED_PROTECTIONS_MISSING"):
            self.inspect(rule=r)

    def test_missing_required_pr_review_parameter_denied(self):
        r = ruleset()
        del r["rules"][2]["parameters"]["required_approving_review_count"]
        with self.assertRaisesRegex(ValueError, "REVIEW_COUNT_NOT_VISIBLE"):
            self.inspect(rule=r)

    def test_bool_review_count_denied(self):
        r = ruleset()
        r["rules"][2]["parameters"]["required_approving_review_count"] = False
        with self.assertRaisesRegex(ValueError, "REVIEW_COUNT_NOT_VISIBLE"):
            self.inspect(rule=r)

    def test_duplicate_required_ci_context_denied(self):
        r = ruleset()
        r["rules"][3]["parameters"]["required_status_checks"].append(
            {"context": "unittest (3.11)"}
        )
        with self.assertRaisesRegex(ValueError, "DUPLICATE_REQUIRED_CHECKS"):
            self.inspect(rule=r)

    def test_witness_unexpected_ref_rejected(self):
        with self.assertRaisesRegex(ValueError, "WITNESS_REF_METADATA_MALFORMED"):
            self.inspect(witness_ref={"ref": "refs/heads/main"})

    def test_403_classic_protection_is_not_equivalent_to_unprotected(self):
        x = self.inspect(classic="INACCESSIBLE_TO_TOKEN_403")
        self.assertEqual(x["classic_branch_protection_endpoint_status"],
                         "INACCESSIBLE_TO_TOKEN_403")
        self.assert_denied(x)

    def test_invalid_classic_status_denied(self):
        with self.assertRaisesRegex(ValueError, "INVALID_CLASSIC"):
            self.inspect(classic="PROTECTED_AUTHORIZED")

    def test_only_exact_404_is_witness_absence(self):
        for code in (401, 403):
            exc = HTTPError("https://api.github.com", code, "no", {}, None)
            with self.subTest(code=code):
                result, status = _classify_rest_error(
                    Mock(side_effect=exc), "/witness", "token", allow_missing=True
                )
                self.assertIsNone(result)
                self.assertEqual(status, "INACCESSIBLE_TO_TOKEN_" + str(code))
        exc = HTTPError("https://api.github.com", 404, "no", {}, None)
        result, status = _classify_rest_error(
            Mock(side_effect=exc), "/witness", "token", allow_missing=True
        )
        self.assertIsNone(result)
        self.assertEqual(status, "NOT_FOUND_404")

    def test_non404_transient_exception_not_swallowed(self):
        for code in (429, 500):
            exc = HTTPError("https://api.github.com", code, "no", {}, None)
            with self.subTest(code=code), self.assertRaises(HTTPError):
                _classify_rest_error(
                    Mock(side_effect=exc), "/witness", "token",
                    allow_missing=True,
                )


class OptionADriveAclObservationContracts(unittest.TestCase):
    def test_five_real_observed_folder_scopes_are_unattested(self):
        x = inspect_drive_snapshot(DRIVE)
        self.assertEqual(x["drive_scope_folder_metadata_observed"], 5)
        self.assertEqual(x["drive_metadata_shared_false_count"], 5)
        self.assertEqual(x["drive_visible_owner_role_per_folder"], 1)
        self.assertTrue(x["drive_observation_is_historical_not_live_ci"])
        self.assertFalse(x["drive_two_independent_owner_principals_attested"])
        self.assertFalse(x["drive_real_licensed_immutable_cache_proven"])
        self.assertFalse(x["drive_cache_write_authorized"])

    def test_drive_acl_provenance_cannot_be_upgraded(self):
        r = deepcopy(DRIVE)
        r["visibility"] = "INDEPENDENTLY_ATTESTED_LIVE"
        with self.assertRaisesRegex(ValueError, "DRIVE_ACL_OVERCLAIM"):
            inspect_drive_snapshot(r)

    def test_two_unverified_owners_cannot_be_claimed_from_one_permission(self):
        r = deepcopy(DRIVE)
        r["folders"][0]["visible_permissions_count"] = 2
        with self.assertRaisesRegex(ValueError, "PERMISSIONS_OR_AUTHORITY_DRIFT"):
            inspect_drive_snapshot(r)

    def test_owner_aliases_not_published_in_public_repo(self):
        self.assertFalse(DRIVE["owner_identifiers_in_public_repo"])
        s = json.dumps(DRIVE)
        self.assertNotIn("emailAddress", s)
        self.assertNotIn("@gmail", s)

    def test_no_fake_drive_cache_immutability_flag(self):
        for key in (
            "distinct_owner_custody_verified",
            "drive_object_immutability_verified",
            "real_drive_market_cache_verified",
            "approved_writer_identities_verified",
            "drive_permission_change_alerting_verified",
            "independent_trust_root_verified",
            "production_cache_read_authorized",
            "production_cache_write_authorized",
            "trading_authorized",
        ):
            r = deepcopy(DRIVE)
            r[key] = True
            with self.subTest(key=key), self.assertRaises(PermissionError):
                inspect_drive_snapshot(r)

    def test_dropped_folder_row_denied(self):
        r = deepcopy(DRIVE)
        r["folders"].pop()
        with self.assertRaisesRegex(ValueError, "MISSING_DRIVE_FOLDER"):
            inspect_drive_snapshot(r)

    def test_reordered_folder_scopes_denied(self):
        r = deepcopy(DRIVE)
        r["folders"].reverse()
        with self.assertRaisesRegex(ValueError, "INVALID_DRIVE_FOLDER_SCOPES"):
            inspect_drive_snapshot(r)

    def test_forged_drive_status_denied(self):
        r = deepcopy(DRIVE)
        r["decision"] = "PRODUCTION_ALLOWED"
        with self.assertRaises(PermissionError):
            inspect_drive_snapshot(r)

    def test_untyped_drive_snapshot_denied(self):
        for v in (None, [], "ready", 123):
            with self.subTest(v=v), self.assertRaises(ValueError):
                inspect_drive_snapshot(v)

    def test_drive_owner_role_change_not_silently_accepted(self):
        r = deepcopy(DRIVE)
        r["folders"][1]["visible_roles"] = ["writer"]
        with self.assertRaisesRegex(ValueError, "PERMISSIONS_OR_AUTHORITY_DRIFT"):
            inspect_drive_snapshot(r)


if __name__ == "__main__":
    unittest.main()
