"""A02 real 63 module AST/API/dependency review, owner not signed.

Repository package runs on GitHub-hosted CI only; temp cases use copies on
the hosted runner. Source tree parity uses a separate real GitHub remote
readback workflow stage. No target Python imports/exec.
"""
import ast
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from scripts.m2_a02_legacy_63_interface_review import (
    DEFAULT_H3, DEFAULT_PACKAGE, HIGH_IMPACT, SCHEMA,
    TARGET_COUNT, V2_COUNT, inventory, module_static_api, parse_provisional_h3,
)
from scripts.mst_remote_legacy_tree_lock import _ALLOWED_V2_PATHS


class LegacySourceReviewPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = inventory()
        cls.by_name = {r["module"]: r for r in cls.result["modules"]}

    def test_complete_exact_v1_source_module_count(self):
        self.assertEqual(self.result["original_module_count"], 63)
        self.assertEqual(len(self.by_name), 63)

    def test_v2_eight_modules_never_mixed_into_v1_signoff(self):
        self.assertEqual(self.result["existing_v2_sidecar_count_excluded"], 8)
        for path in _ALLOWED_V2_PATHS:
            self.assertNotIn(Path(path).stem, self.by_name)

    def test_h3_provisional_crosswalk_has_71_exact_names(self):
        self.assertEqual(self.result["provisional_h3_total_modules"], 71)
        self.assertEqual(len(parse_provisional_h3(DEFAULT_H3.read_text())), 71)

    def test_api_packet_labels_not_approvals(self):
        self.assertIn("OWNER_NOT_SIGNED", self.result["status"])
        self.assertEqual(self.result["schema"], SCHEMA)

    def test_all_63_unsigned(self):
        self.assertEqual(self.result["module_owner_dispositions_received"], 0)
        self.assertTrue(all(r["owner_decision"] == "NOT_SIGNED"
                            for r in self.by_name.values()))

    def test_zero_behavior_and_abi_owner_approvals(self):
        self.assertEqual(self.result["module_owner_abi_approvals_received"], 0)
        self.assertEqual(self.result["module_owner_behavior_approvals_received"], 0)
        self.assertTrue(all(not r["owner_abi_approved"]
                            and not r["owner_behavior_parity_approved"]
                            for r in self.by_name.values()))

    def test_source_lock_remote_readback_separate(self):
        self.assertTrue(self.result["remote_source_lock_requires_separate_live_github_api_check"])
        self.assertFalse(self.result["source_tree_remote_readback_in_this_function"])

    def test_all_production_rights_false(self):
        self.assertFalse(self.result["independent_real_market_provider_rights_verified"])
        self.assertFalse(self.result["v1_v2_full_behavior_parity_claimed"])
        self.assertFalse(self.result["production_release_authorized"])
        self.assertFalse(self.result["trading_authorized"])

    def test_real_source_files_digests_have_64_hex_chars(self):
        self.assertTrue(all(len(r["checkout_sha256"]) == 64
                            and len(r["interface_sha256"]) == 64
                            for r in self.by_name.values()))

    def test_no_unreviewed_modules_in_inventory(self):
        names = {p.stem for p in DEFAULT_PACKAGE.glob("*.py")}
        expected = names - {Path(p).stem for p in _ALLOWED_V2_PATHS}
        self.assertEqual(expected, set(self.by_name))

    def test_current_h3_categories_bound_to_each_original_module(self):
        for x in self.by_name.values():
            self.assertIn(x["provisional_h3_disposition"],
                          ("KEEP", "IMPROVE", "REPLACE", "REMOVE"))
            self.assertTrue(x["provisional_h3_group"])

    def test_foundational_contracts_present(self):
        self.assertIn("contracts", self.by_name)
        self.assertIn("engine", self.by_name)
        self.assertIn("incremental_cache", self.by_name)
        self.assertIn("source_quality", self.by_name)

    def test_priority_review_contains_eight_modules(self):
        self.assertEqual(len(HIGH_IMPACT), 8)
        self.assertTrue(set(HIGH_IMPACT) <= set(self.by_name))

    def test_contracts_have_public_classes(self):
        self.assertGreaterEqual(self.by_name["contracts"]["public_class_count"], 4)

    def test_engine_has_public_function(self):
        self.assertGreaterEqual(self.by_name["engine"]["public_function_count"], 1)

    def test_canonical_market_data_depending_on_replay(self):
        self.assertIn("replay", self.by_name["market_data"]["direct_package_imports"])

    def test_cross_module_consumer_has_dependency(self):
        self.assertGreater(self.by_name["contracts"]["direct_internal_consumer_modules"], 0)

    def test_public_functions_exclude_private_helpers(self):
        s = "def _hidden(): pass\ndef visible(a): pass\n"
        r = module_static_api(s, module_name="synthetic")
        self.assertEqual([f["name"] for f in r["interface"]["functions"]], ["visible"])

    def test_public_methods_and_init_captured(self):
        r = module_static_api(
            "class Demo:\n    def __init__(self,x): pass\n    def public(self): pass\n    def _secret(self): pass\n",
            module_name="synthetic")
        self.assertEqual([m["name"] for m in r["interface"]["classes"][0]["methods"]],
                         ["__init__", "public"])

    def test_annotations_and_defaults_affect_surface_fingerprint(self):
        plain = module_static_api("def api(x): pass\n", module_name="synthetic")
        annotated = module_static_api("def api(x: int=1): pass\n", module_name="synthetic")
        self.assertNotEqual(plain["interface_sha256"], annotated["interface_sha256"])

    def test_changing_method_decorator_affects_surface_fingerprint(self):
        a = module_static_api("class X:\n    def api(self,x): pass\n", module_name="synthetic")
        b = module_static_api("class X:\n    @staticmethod\n    def api(x): pass\n", module_name="synthetic")
        self.assertNotEqual(a["interface_sha256"], b["interface_sha256"])

    def test_changing_class_base_affects_surface_fingerprint(self):
        a = module_static_api("class X: pass\n", module_name="synthetic")
        b = module_static_api("class X(str): pass\n", module_name="synthetic")
        self.assertNotEqual(a["interface_sha256"], b["interface_sha256"])

    def test_changing_field_affects_interface_fingerprint(self):
        a = module_static_api("class X:\n    count: int\n", module_name="synthetic")
        b = module_static_api("class X:\n    other: int\n", module_name="synthetic")
        self.assertNotEqual(a["interface_sha256"], b["interface_sha256"])

    def test_syntax_only_does_not_execute_module(self):
        danger = "raise RuntimeError('should never run')\ndef safe():pass\n"
        r = module_static_api(danger, module_name="synthetic")
        self.assertEqual(r["public_function_count"], 1)

    def test_function_body_mutation_not_wrongly_called_full_parity(self):
        a = module_static_api("def api(x):\n    return 1\n", module_name="synthetic")
        b = module_static_api("def api(x):\n    return 2\n", module_name="synthetic")
        self.assertEqual(a["interface_sha256"], b["interface_sha256"])
        self.assertTrue(self.result["remote_source_lock_requires_separate_live_github_api_check"])

    def test_invalid_python_fails_closed(self):
        with self.assertRaises(SyntaxError):
            module_static_api("def broken(", module_name="synthetic")

    def test_wrong_h3_double_module_rejected(self):
        source = DEFAULT_H3.read_text()
        row = next(line for line in source.splitlines()
                   if line.startswith("| engine |"))
        with self.assertRaisesRegex(ValueError, "H3_DUPLICATED_MODULE"):
            parse_provisional_h3(source + "\n" + row)

    def test_h3_missing_module_rejected(self):
        source = DEFAULT_H3.read_text()
        row = next(line for line in source.splitlines()
                   if line.startswith("| engine |"))
        with self.assertRaisesRegex(ValueError, "H3_NOT_EXACTLY_71"):
            parse_provisional_h3(source.replace(row + "\n", ""))

    def test_h3_invalid_loc_rejected(self):
        source = DEFAULT_H3.read_text()
        row = next(line for line in source.splitlines()
                   if line.startswith("| engine |"))
        with self.assertRaisesRegex(ValueError, "H3_INVALID_STATIC_REVIEW_METADATA"):
            parse_provisional_h3(source.replace(row, row.replace("| 14 |", "| not-a-number |", 1)))

    def test_inventory_missing_original_module_rejected(self):
        with TemporaryDirectory() as td:
            d = Path(td)
            # A complete path-level checkout copy is disposable on GitHub CI.
            copy = d / "src"
            shutil.copytree(DEFAULT_PACKAGE, copy)
            (copy / "engine.py").unlink()
            with self.assertRaisesRegex(ValueError, "SOURCE_PACKAGE_NOT_EXACTLY"):
                inventory(copy, DEFAULT_H3)

    def test_inventory_extra_source_module_rejected(self):
        with TemporaryDirectory() as td:
            copy = Path(td) / "src"
            shutil.copytree(DEFAULT_PACKAGE, copy)
            (copy / "rogue_undispositioned.py").write_text("pass\n")
            with self.assertRaisesRegex(ValueError, "SOURCE_PACKAGE_NOT_EXACTLY"):
                inventory(copy, DEFAULT_H3)

    def test_inventory_source_and_h3_name_replacement_rejected(self):
        with TemporaryDirectory() as td:
            copy = Path(td) / "src"
            shutil.copytree(DEFAULT_PACKAGE, copy)
            (copy / "engine.py").rename(copy / "unknown_replacement.py")
            with self.assertRaisesRegex(ValueError, "SOURCE_AND_EXISTING_H3"):
                inventory(copy, DEFAULT_H3)

    def test_interface_fingerprint_is_deterministic(self):
        self.assertEqual(inventory()["package_interface_fingerprint"],
                         self.result["package_interface_fingerprint"])

    def test_interface_fingerprint_not_credential_signature(self):
        self.assertNotIn("verified_signature", self.result)
        self.assertNotIn("owner_approved", self.result)
        self.assertEqual(self.result["module_owner_dispositions_received"], 0)

    def test_cold_import_not_used_as_evidence(self):
        # Target code only ast.parse; no execution/import of V1 classes occurs.
        import inspect
        from scripts import m2_a02_legacy_63_interface_review as impl
        src = inspect.getsource(impl.module_static_api)
        self.assertIn("ast.parse(", src)
        self.assertNotIn("importlib.import_module", src)


if __name__ == "__main__":
    unittest.main()
