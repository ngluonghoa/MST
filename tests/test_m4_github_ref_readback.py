"""Offline negative-contract tests for live GitHub ref readback script."""
from copy import deepcopy
import unittest

from scripts.m4_github_ref_readback import verify_readback, _A, _B, _BASE, _BRANCH, _TREE_A, _TREE_B


def fixture():
    return (
        {"ref": "refs/heads/" + _BRANCH, "object": {"sha": _A, "type": "commit"}},
        {"sha": _A, "parents": [{"sha": _BASE}], "tree": {"sha": _TREE_A}},
        {"sha": _B, "parents": [{"sha": _BASE}], "tree": {"sha": _TREE_B}},
    )


class GithubRemoteRefReadbackFixtureTests(unittest.TestCase):
    def test_matching_head_and_sibling_commit_proof_is_non_authorizing(self):
        x = verify_readback(*fixture())
        self.assertEqual(x["observed_head"], _A)
        self.assertEqual(x["losing_candidate"], _B)
        self.assertEqual(x["shared_parent"], _BASE)
        self.assertTrue(x["github_ref_observed"])
        self.assertFalse(x["remote_non_fast_forward_denial_proven_by_this_read"])
        for field in (
            "vendor_rights_verified", "source_clock_authenticated",
            "google_drive_payload_verified", "independently_protected_floor",
            "distributed_multiaccount_cas_verified", "production_write_authorized",
            "trading_authorized",
        ):
            self.assertIs(x[field], False)

    def test_wrong_branch_is_denied(self):
        ref, a, b = fixture()
        ref["ref"] = "refs/heads/main"
        with self.assertRaisesRegex(ValueError, "WRONG_BRANCH_REF"):
            verify_readback(ref, a, b)

    def test_final_head_rollback_or_competitor_denied(self):
        for changed in (_B, _BASE):
            with self.subTest(sha=changed):
                ref, a, b = fixture()
                ref["object"]["sha"] = changed
                with self.assertRaisesRegex(ValueError, "UNEXPECTED_FINAL_HEAD"):
                    verify_readback(ref, a, b)

    def test_missing_or_noncommit_ref_denied(self):
        ref, a, b = fixture()
        ref["object"]["type"] = "tag"
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_FINAL_HEAD"):
            verify_readback(ref, a, b)

    def test_competing_candidate_sha_substitution_denied(self):
        ref, a, b = fixture()
        b["sha"] = _A
        with self.assertRaisesRegex(ValueError, "CANDIDATE_B_SHA_MISMATCH"):
            verify_readback(ref, a, b)

    def test_winning_candidate_sha_substitution_denied(self):
        ref, a, b = fixture()
        a["sha"] = _BASE
        with self.assertRaisesRegex(ValueError, "CANDIDATE_A_SHA_MISMATCH"):
            verify_readback(ref, a, b)

    def test_wrong_ancestry_denied_for_either_candidate(self):
        for target in (1, 2):
            with self.subTest(target=target):
                v = list(fixture())
                v[target]["parents"][0]["sha"] = _B if target == 1 else _A
                with self.assertRaisesRegex(ValueError, "NOT_CHILD_OF_BASE"):
                    verify_readback(*v)

    def test_merge_and_orphan_parent_shapes_denied(self):
        for invalid in ([], [{"sha": _BASE}, {"sha": _A}], None):
            with self.subTest(parents=invalid):
                ref, a, b = fixture()
                a["parents"] = invalid
                with self.assertRaisesRegex(ValueError, "PARENT_SHAPE"):
                    verify_readback(ref, a, b)

    def test_tree_tampering_denied_for_both_siblings(self):
        for target in (1, 2):
            with self.subTest(target=target):
                v = list(fixture())
                v[target]["tree"]["sha"] = "f" * 40
                with self.assertRaisesRegex(ValueError, "TREE_MISMATCH"):
                    verify_readback(*v)

    def test_wrong_python_shapes_denied(self):
        for which in range(3):
            with self.subTest(which=which):
                v = list(fixture())
                v[which] = ["untrusted", "non-git-object"]
                with self.assertRaises(TypeError):
                    verify_readback(*v)


if __name__ == "__main__":
    unittest.main()
