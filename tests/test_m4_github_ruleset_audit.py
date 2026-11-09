"""Synthetic, fail-closed contract tests for read-only actual GitHub ruleset audit."""
from copy import deepcopy
import unittest

from scripts.m4_github_ruleset_audit import (
    _BASE, _REPO, _RULESET_ID, _TEST_HEADS, _TEST_REFS, _REQUIRED_CI,
    audit_ruleset,
)


def fixtures():
    rule = {
        "id": _RULESET_ID, "name": "MST - Protect Main", "target": "branch",
        "source_type": "Repository", "source": _REPO, "enforcement": "active",
        "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
        "bypass_actors": [], "current_user_can_bypass": "never",
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {"type": "pull_request", "parameters": {"required_approving_review_count": 0}},
            {"type": "required_status_checks", "parameters": {
                "required_status_checks": [{"context": c, "integration_id": 15368} for c in _REQUIRED_CI],
            }},
        ],
    }
    main = {"name": "main", "protected": True, "commit": {"sha": _BASE},
            "protection": {"enabled": False}}
    trial = [{"name": name, "protected": False, "commit": {"sha": _TEST_HEADS[i]}}
             for i, name in enumerate(_TEST_REFS)]
    return rule, main, trial


class M4RulesetAuditTests(unittest.TestCase):
    def test_active_main_ruleset_and_unprotected_tests_no_authority(self):
        result = audit_ruleset(*fixtures())
        self.assertEqual(result["status"], "MAIN_RULESET_ACTIVE_M4_TEST_REFS_UNPROTECTED")
        self.assertTrue(result["main_protected"])
        self.assertEqual(result["test_ref_protected"], [False, False])
        self.assertTrue(result["main_no_configured_bypass_for_this_actor"])
        self.assertFalse(result["protected_m4_witness_ref_present"])
        for key in (
            "independently_protected_rollback_floor", "force_delete_admin_bypass_tested",
            "two_credential_writer_cas_proven", "signed_vendor_data_source_verified",
            "real_drive_chunk_custody_verified", "trading_authorized",
        ):
            self.assertIs(result[key], False)

    def test_inactive_ruleset_denied(self):
        r, m, b = fixtures()
        r["enforcement"] = "disabled"
        with self.assertRaisesRegex(ValueError, "INACTIVE"):
            audit_ruleset(r, m, b)

    def test_default_branch_scoping_is_required(self):
        for conditions in (
            {"ref_name": {"include": ["refs/heads/mst/*"], "exclude": []}},
            {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": ["main"]}},
            None,
        ):
            with self.subTest(conditions=conditions):
                r, m, b = fixtures()
                r["conditions"] = conditions
                with self.assertRaisesRegex(ValueError, "RULESET_NOT_DEFAULT_BRANCH"):
                    audit_ruleset(r, m, b)

    def test_ruleset_identity_and_source_cannot_drift(self):
        for key, value in (("id", 999), ("name", "OTHER"),
                           ("source", "other/repo"), ("source_type", "Organization"),
                           ("target", "tag")):
            with self.subTest(key=key):
                r, m, b = fixtures()
                r[key] = value
                with self.assertRaises(ValueError):
                    audit_ruleset(r, m, b)

    def test_any_bypass_actor_or_current_actor_bypass_denied(self):
        for key, value in (("bypass_actors", [{"actor_id": 1, "actor_type": "Team"}]),
                           ("current_user_can_bypass", "always")):
            with self.subTest(key=key):
                r, m, b = fixtures()
                r[key] = value
                with self.assertRaisesRegex(ValueError, "BYPASS"):
                    audit_ruleset(r, m, b)

    def test_missing_deletion_or_non_fast_forward_or_pr_rule_denied(self):
        for rule in ("deletion", "non_fast_forward", "pull_request"):
            with self.subTest(rule=rule):
                r, m, b = fixtures()
                r["rules"] = [x for x in r["rules"] if x["type"] != rule]
                with self.assertRaisesRegex(ValueError, "MISSING_MAIN_RULE"):
                    audit_ruleset(r, m, b)

    def test_missing_or_replaced_required_ci_denied(self):
        for changed in (
            [],
            [{"context": "unittest (3.11)"}],
            [{"context": "unittest (3.11)"}, {"context": "unittest (3.12)"},
             {"context": "wrong-context"}],
        ):
            with self.subTest(checks=changed):
                r, m, b = fixtures()
                r["rules"][-1]["parameters"]["required_status_checks"] = changed
                with self.assertRaisesRegex(ValueError, "REQUIRED_CI_SET_DRIFT"):
                    audit_ruleset(r, m, b)

    def test_main_baseline_moved_or_unprotected_denied(self):
        for bad in (("protected", False), ("head", "f" * 40)):
            r, m, b = fixtures()
            if bad[0] == "head":
                m["commit"]["sha"] = bad[1]
            else:
                m["protected"] = bad[1]
            with self.subTest(field=bad[0]), self.assertRaises(ValueError):
                audit_ruleset(r, m, b)

    def test_trial_branch_replaced_or_ref_head_moved_denied(self):
        for i in (0, 1):
            for key in ("name", "head"):
                with self.subTest(i=i, key=key):
                    r, m, b = fixtures()
                    if key == "name":
                        b[i]["name"] = "main"
                    else:
                        b[i]["commit"]["sha"] = _BASE
                    with self.assertRaises(ValueError):
                        audit_ruleset(r, m, b)

    def test_test_ref_becoming_protected_requires_reassessment(self):
        # A policy change is not silently treated as if prior test evidence
        # had proved the new protection's force/delete constraints.
        r, m, b = fixtures()
        b[0]["protected"] = True
        with self.assertRaisesRegex(ValueError, "TEST_REF_POLICY_CHANGED_REEVALUATE"):
            audit_ruleset(r, m, b)

    def test_bad_shapes_fail_closed(self):
        for values in (
            ("not a dict", fixtures()[1], fixtures()[2]),
            (fixtures()[0], "not a dict", fixtures()[2]),
            (fixtures()[0], fixtures()[1], []),
            (fixtures()[0], fixtures()[1], [None, None]),
        ):
            with self.subTest(type=type(values[0]).__name__), self.assertRaises(
                (TypeError, ValueError)
            ):
                audit_ruleset(*values)


if __name__ == "__main__":
    unittest.main()
