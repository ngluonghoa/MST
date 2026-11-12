"""Review-only metadata classifier tests; NO real GitHub/Drive writes or CAS."""
from copy import deepcopy
import unittest

from scripts import m4_cache_authority_readonly_preflight as m


def sample():
    repo = {
        "full_name": m.REPO,
        "id": m.REPO_ID,
        "default_branch": "main",
        "private": False,
    }
    ref = {"ref": m.REF, "object": {"type": "commit", "sha": m.EXPECTED_LAB_SHA}}
    branch = {
        "name": "mst/m4-ref-cas-lab-20261109",
        "protected": False,
        "commit": {"sha": m.EXPECTED_LAB_SHA},
    }
    listing = [{"id": 26801439, "name": "MST - Protect Main"}]
    detail = [{
        "id": 26801439, "name": "MST - Protect Main",
        "source": m.REPO, "target": "branch", "enforcement": "active",
        "conditions": {"ref_name": {
            "include": ["~DEFAULT_BRANCH"], "exclude": [],
        }},
        "bypass_actors": [],
        "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}],
    }]
    return repo, ref, branch, listing, detail


class M4CacheAuthorityReadonlyPreflightTests(unittest.TestCase):
    def test_actual_main_only_ruleset_is_not_cache_witness_evidence(self):
        receipt = m.preflight(*sample())
        self.assertEqual(receipt["decision"], "NO_GO")
        self.assertEqual(receipt["main_only_ruleset_ids"], [26801439])
        self.assertEqual(receipt["literal_exact_ref_ruleset_ids"], [])
        self.assertFalse(receipt["lab_branch_protected_metadata"])
        self.assertIn("NO_EXPLICIT_EXACT_REF_RULESET", receipt["reasons"])
        self.assertIn("MST_REPOSITORY_IS_PUBLIC", receipt["reasons"])
        self.assertFalse(receipt["writes_performed"])
        self.assertFalse(receipt["market_cache_authorized"])
        self.assertFalse(receipt["external_cas_proven"])

    def test_even_literal_exact_rule_does_not_prove_usable_authority(self):
        values = sample()
        values[-1][0]["conditions"]["ref_name"]["include"] = [m.REF]
        values[2]["protected"] = True
        values[0]["private"] = True
        receipt = m.preflight(*values)
        self.assertEqual(receipt["literal_exact_ref_ruleset_ids"], [26801439])
        self.assertEqual(receipt["decision"], "NO_GO")
        self.assertNotIn("NO_EXPLICIT_EXACT_REF_RULESET", receipt["reasons"])
        self.assertTrue(receipt["lab_branch_protected_metadata"])
        self.assertIn("NO_NONROLLBACKABLE_SIGNED_LATEST_FLOOR", receipt["reasons"])
        self.assertFalse(receipt["production_authorized"])

    def test_wildcard_only_is_not_called_exact_ref_proof(self):
        values = sample()
        values[-1][0]["conditions"]["ref_name"]["include"] = ["refs/heads/mst/**"]
        receipt = m.preflight(*values)
        self.assertEqual(receipt["literal_exact_ref_ruleset_ids"], [])
        self.assertIn("NO_EXPLICIT_EXACT_REF_RULESET", receipt["reasons"])

    def test_stale_lab_ref_head_or_branch_mismatch_is_a_hard_error(self):
        for kind in ("ref-sha", "branch-sha", "name", "type", "protected"):
            with self.subTest(kind=kind):
                v = sample()
                if kind == "ref-sha":
                    v[1]["object"]["sha"] = "e" * 40
                    v[2]["commit"]["sha"] = "e" * 40
                elif kind == "branch-sha":
                    v[2]["commit"]["sha"] = "e" * 40
                elif kind == "name":
                    v[2]["name"] = "main"
                elif kind == "type":
                    v[1]["object"]["type"] = "tree"
                else:
                    v[2]["protected"] = "False"
                with self.assertRaises(m.PreflightError):
                    m.preflight(*v)

    def test_repository_identity_and_shape_drift_fail_closed(self):
        for key, value in (
            ("id", True), ("id", 1), ("full_name", "evil/MST"),
            ("default_branch", "dev"), ("private", "false"),
        ):
            with self.subTest(key=key, val=value):
                values = sample()
                values[0][key] = value
                with self.assertRaises(m.PreflightError):
                    m.preflight(*values)
        with self.assertRaises(m.PreflightError):
            m.preflight(None, *sample()[1:])

    def test_ruleset_details_incomplete_duplicate_or_malformed_are_denied(self):
        for case in ("duplicate", "bad-id", "shape", "bad-includes", "wrong-length"):
            with self.subTest(case=case):
                v = sample()
                if case == "duplicate":
                    v[3].append(deepcopy(v[3][0]))
                    v[4].append(deepcopy(v[4][0]))
                elif case == "bad-id":
                    v[4][0]["id"] = 1
                elif case == "shape":
                    v[4][0]["conditions"] = "not valid"
                elif case == "bad-includes":
                    v[4][0]["conditions"]["ref_name"]["include"] = "main"
                else:
                    v[4].clear()
                with self.assertRaises(m.PreflightError):
                    m.preflight(*v)

    def test_disabled_or_foreign_ruleset_never_attests_ref(self):
        for field, value in (
            ("enforcement", "disabled"), ("source", "someone/other"),
            ("target", "tag"),
        ):
            with self.subTest(field=field):
                v = sample()
                v[4][0][field] = value
                self.assertEqual(m.preflight(*v)["literal_exact_ref_ruleset_ids"], [])
                self.assertEqual(m.preflight(*v)["decision"], "NO_GO")

    def test_non_allowlisted_endpoint_rejected_before_http(self):
        for bad in (
            "/git/refs/heads/main", "/actions/runs", "/rulesets/0",
            "/rulesets/1?x=2", "https://evil.example/", "/contents/README.md",
        ):
            with self.subTest(path=bad), self.assertRaises(m.PreflightError):
                m._get(bad, "not-a-real-token")

    def test_empty_ruleset_list_remains_no_go_not_an_authority(self):
        v = sample()
        v[3].clear()
        v[4].clear()
        r = m.preflight(*v)
        self.assertEqual(r["rulesets_examined"], 0)
        self.assertEqual(r["decision"], "NO_GO")
        self.assertEqual(r["active_repository_ruleset_ids"], [])


if __name__ == "__main__":
    unittest.main()
