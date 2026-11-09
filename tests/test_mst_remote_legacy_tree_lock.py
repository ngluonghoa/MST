"""Synthetic negative checks for REAL GitHub remote 1:1 source-tree audit."""
from copy import deepcopy
import unittest

from scripts.mst_remote_legacy_tree_lock import (
    _MAIN_COMMIT, _SOURCE_COMMIT, _TREE,
    _objects, inspect_remote_legacy_parity,
)


def fixture_tree():
    # Exactly 216 Git entries = 8 tree entries + 208 blob entries.
    trees = ("src", "src/swing_trading", "docs", "scripts",
             "tests", ".github", ".github/workflows", "data")
    result = []
    for i, path in enumerate(trees):
        result.append({"path": path, "type": "tree", "mode": "040000",
                       "sha": f"{i+1:040x}"})
    for i in range(63):
        result.append({
            "path": f"src/swing_trading/legacy_{i:02d}.py",
            "type": "blob", "mode": "100644", "sha": f"{i+10:040x}",
        })
    for i in range(145):
        result.append({
            "path": f"docs/original_{i:03d}.md",
            "type": "blob", "mode": "100644", "sha": f"{i+100:040x}",
        })
    return {"sha": _TREE, "truncated": False, "tree": result}


def commit(sha):
    return {"sha": sha, "tree": {"sha": _TREE}}


class OriginalGitTreeParityTests(unittest.TestCase):
    def setUp(self):
        self.upstream = commit(_SOURCE_COMMIT)
        self.main = commit(_MAIN_COMMIT)
        self.a = fixture_tree()
        self.b = deepcopy(self.a)
        self.c = deepcopy(self.a)
        self.c["sha"] = "f" * 40
        self.head = "b" * 40

    def verify(self):
        return inspect_remote_legacy_parity(
            self.upstream, self.main, self.a, self.b, self.c,
            candidate_sha=self.head,
        )

    def test_full_original_tree_and_package_remain_exact(self):
        x = self.verify()
        self.assertIn("MATCH", x["status"])
        self.assertEqual(x["original_git_tree_entry_count"], 216)
        self.assertEqual(x["original_git_blob_count"], 208)
        self.assertEqual(x["original_python_module_count"], 63)
        self.assertEqual(x["shared_original_tree_sha"], _TREE)
        self.assertTrue(x["all_original_tree_entries_match_between_source_and_main"])
        self.assertTrue(x["all_inherited_package_paths_unchanged_on_pr"])
        self.assertFalse(x["a02_owner_module_review_signed_off"])
        self.assertFalse(x["m4_witness_admin_independence_proven"])
        self.assertFalse(x["production_release_authorized"])

    def test_candidate_may_add_safe_nonlegacy_sidecars(self):
        self.c["tree"].append({
            "path": "scripts/cloud_new_test.py", "mode": "100644",
            "type": "blob", "sha": "f" * 40,
        })
        self.verify()

    def test_candidate_legacy_python_content_mutation_denied(self):
        self.c["tree"][10]["sha"] = "f" * 40
        with self.assertRaisesRegex(ValueError, "INHERITED_SOURCE_CHANGED"):
            self.verify()

    def test_candidate_legacy_module_deleted_denied(self):
        self.c["tree"] = [
            item for item in self.c["tree"]
            if item["path"] != "src/swing_trading/legacy_00.py"
        ]
        with self.assertRaisesRegex(ValueError, "INHERITED_SOURCE_CHANGED"):
            self.verify()

    def test_candidate_new_module_in_inherited_namespace_denied(self):
        self.c["tree"].append({
            "path": "src/swing_trading/unapproved_new.py",
            "type": "blob", "mode": "100644", "sha": "a" * 40,
        })
        with self.assertRaisesRegex(ValueError, "INHERITED_SOURCE_CHANGED"):
            self.verify()

    def test_candidate_extra_legacy_directory_denied(self):
        self.c["tree"].append({
            "path": "src/swing_trading/accidental_dir",
            "type": "tree", "mode": "040000", "sha": "a" * 40,
        })
        with self.assertRaisesRegex(ValueError, "INHERITED_NAMESPACE_CHANGED"):
            self.verify()

    def test_candidate_legacy_module_file_mode_change_denied(self):
        self.c["tree"][10]["mode"] = "100755"
        with self.assertRaisesRegex(ValueError, "INHERITED_SOURCE_CHANGED"):
            self.verify()

    def test_candidate_deleted_nonlegacy_file_allowed_by_package_lock(self):
        self.c["tree"] = [r for r in self.c["tree"]
                          if r["path"] != "docs/original_000.md"]
        self.verify()

    def test_upstream_main_tree_different_entries_fail_even_with_same_claimed_sha(self):
        self.b["tree"][-1]["sha"] = "a" * 40
        with self.assertRaisesRegex(ValueError, "BASELINE_TREE_CONTENT_MISMATCH"):
            self.verify()

    def test_upstream_original_tree_sha_drift_rejected(self):
        self.a["sha"] = "f" * 40
        with self.assertRaisesRegex(ValueError, "TREE_SHA_DRIFT"):
            self.verify()

    def test_original_source_commit_drift_rejected(self):
        self.upstream["sha"] = "f" * 40
        with self.assertRaisesRegex(ValueError, "COMMIT_DRIFT"):
            self.verify()

    def test_main_commit_drift_rejected(self):
        self.main["sha"] = "f" * 40
        with self.assertRaisesRegex(ValueError, "COMMIT_DRIFT"):
            self.verify()

    def test_main_commit_points_to_wrong_tree_rejected(self):
        self.main["tree"]["sha"] = "f" * 40
        with self.assertRaisesRegex(ValueError, "COMMIT_TREE_DRIFT"):
            self.verify()

    def test_original_tree_truncated_rejected(self):
        self.a["truncated"] = True
        with self.assertRaisesRegex(ValueError, "MISSING_OR_TRUNCATED"):
            self.verify()

    def test_original_tree_wrong_entry_count_denied(self):
        self.a["tree"] = self.a["tree"][:-1]
        self.b["tree"] = self.b["tree"][:-1]
        with self.assertRaisesRegex(ValueError, "SOURCE_TREE_COUNT_DRIFT"):
            self.verify()

    def test_original_legacy_source_module_count_drift_denied(self):
        orig = next(r for r in self.a["tree"]
                    if r["path"] == "src/swing_trading/legacy_00.py")
        copy = next(r for r in self.b["tree"]
                    if r["path"] == "src/swing_trading/legacy_00.py")
        orig["path"] = "docs/reclassified_000.txt"
        copy["path"] = "docs/reclassified_000.txt"
        with self.assertRaisesRegex(ValueError, "LEGACY_MODULE_COUNT_DRIFT"):
            self.verify()

    def test_duplicate_git_path_rejected(self):
        self.c["tree"].append(deepcopy(self.c["tree"][9]))
        with self.assertRaisesRegex(ValueError, "DUPLICATE_REMOTE"):
            self.verify()

    def test_github_api_malformed_object_sha_denied(self):
        self.c["tree"][9]["sha"] = "Z" * 40
        with self.assertRaisesRegex(ValueError, "MALFORMED_REMOTE"):
            self.verify()

    def test_path_traversal_rejected(self):
        self.c["tree"][9]["path"] = "../src/swing_trading/unsafe.py"
        with self.assertRaisesRegex(ValueError, "UNSAFE_REMOTE"):
            self.verify()

    def test_untyped_remote_tree_denied(self):
        for v in (None, [], "", {"truncated": True}):
            with self.subTest(v=v), self.assertRaises(ValueError):
                _objects(v)

    def test_nonlowercase_candidate_head_rejected(self):
        self.head = "F" * 40
        with self.assertRaisesRegex(ValueError, "INVALID_CANDIDATE_SHA"):
            self.verify()

    def test_candidate_empty_sha_rejected(self):
        self.head = ""
        with self.assertRaisesRegex(ValueError, "INVALID_CANDIDATE_SHA"):
            self.verify()

    def test_main_and_source_parent_commit_shas_may_differ(self):
        self.main["parents"] = ["c" * 40]
        self.upstream["parents"] = ["d" * 40]
        self.verify()


if __name__ == "__main__":
    unittest.main()
