"""Option A architecture choice is real; production permission is still FALSE."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.m4_option_a_selection_preflight import (
    BLOCKED_ACTIONS, CONTROLS, FALSE_FLAGS, OPEN_GATES,
    REQUIRED_STRINGS, SOURCE, TRUE_FLAGS, validate_option_a_choice,
)
from scripts.m4_owner_architecture_preflight import (
    validate_owner_architecture_draft,
)

CHOICE = json.loads(Path(
    "docs/MST_M4_OPTION_A_SCOPE_SELECTION_20261109.json"
).read_text(encoding="utf-8"))
PRIOR = json.loads(Path(
    "docs/MST_M4_G01_G02_OWNER_DECISIONS_20261109.json"
).read_text(encoding="utf-8"))


class OptionAArchitectureSelectionTests(unittest.TestCase):
    def check(self, changes=None):
        record = deepcopy(CHOICE)
        if changes is not None:
            changes(record)
        return validate_option_a_choice(record)

    def test_explicit_user_choice_a_is_recorded(self):
        receipt = self.check()
        self.assertEqual(receipt["architecture_option_selected"], "A_GITHUB_DRIVE_ONLY")
        self.assertTrue(receipt["owner_architecture_scope_choice_recorded"])
        self.assertEqual(receipt["allowed_platforms"], ["GitHub", "Google Drive"])
        self.assertIn("PRODUCTION_BLOCKED", receipt["status"])

    def test_no_production_privilege_follows_from_selected_architecture(self):
        result = self.check()
        for key in (
            "independent_owner_authentication_attested",
            "real_witness_or_signer_provisioning_authorized",
            "new_cloud_services_authorized", "cache_read_authorized",
            "cache_write_authorized", "trading_authorized",
        ):
            self.assertIs(result[key], False, key)
        self.assertEqual(result["signed_gates_open_count"], 8)

    def test_user_chat_choice_is_not_an_independent_cryptographic_signature(self):
        self.assertEqual(
            CHOICE["decision_origin_integrity"],
            "CHAT_INSTRUCTION_RECORDED_NOT_INDEPENDENTLY_SIGNED",
        )
        self.assertFalse(CHOICE["independent_owner_identity_attested"])

    def test_historical_unselected_draft_preserved_for_provenance(self):
        prior = validate_owner_architecture_draft(PRIOR)
        self.assertEqual(prior["owner_options_unselected"], 3)
        self.assertFalse(prior["g01_verified"])
        self.assertTrue(CHOICE["prior_proposal_is_historical_unselected_snapshot"])
        self.assertEqual(
            CHOICE["prior_proposal_snapshot"],
            "docs/MST_M4_G01_G02_OWNER_DECISIONS_20261109.json",
        )

    def test_deterministic_readonly_result(self):
        self.assertEqual(self.check(), self.check())

    def test_missing_new_choice_input_rejected(self):
        for value in (None, [], "A", 1, True):
            with self.subTest(value=value), self.assertRaises(TypeError):
                validate_option_a_choice(value)

    def test_unknown_self_approval_field_cannot_override_authority(self):
        with self.assertRaisesRegex(ValueError, "NONCANONICAL_OPTION_A"):
            self.check(lambda x: x.update(owner_production_approved=True))

    def test_missing_false_flag_is_not_false(self):
        for name in FALSE_FLAGS:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.check(lambda x, n=name: x.pop(n))

    def test_every_privilege_flag_true_is_rejected(self):
        for name in FALSE_FLAGS:
            with self.subTest(name=name), self.assertRaises(PermissionError):
                self.check(lambda x, n=name: x.__setitem__(n, True))

    def test_every_privilege_flag_null_is_rejected(self):
        for name in FALSE_FLAGS:
            with self.subTest(name=name), self.assertRaises(PermissionError):
                self.check(lambda x, n=name: x.__setitem__(n, None))

    def test_required_choice_booleans_must_be_explicitly_true(self):
        for name in TRUE_FLAGS:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.check(lambda x, n=name: x.__setitem__(n, 1))

    def test_change_from_a_to_b_requires_new_owner_scope(self):
        with self.assertRaisesRegex(ValueError, "OPTION_A_CHOICE_IDENTITY"):
            self.check(lambda x: x.update(selected_architecture="B_CLOUD_KMS_FIRESTORE"))

    def test_option_c_cache_root_cannot_be_silently_selected(self):
        with self.assertRaisesRegex(ValueError, "OPTION_A_CHOICE_IDENTITY"):
            self.check(lambda x: x.update(selected_architecture="C_ACTIONS_CACHE_AS_ROOT"))

    def test_out_of_scope_platform_is_rejected(self):
        for platforms in (
            ["GitHub", "Google Drive", "Firestore"],
            ["GitHub", "Google Drive", "Cloud KMS"],
            ["Google Drive"],
            ["GitHub", "Google Drive", "MOCHI"],
            [],
        ):
            with self.subTest(platforms=platforms), self.assertRaises(PermissionError):
                self.check(lambda x, p=platforms: x.update(allowed_platforms=p))

    def test_git_and_drive_reordered_requires_explicit_new_contract(self):
        with self.assertRaises(PermissionError):
            self.check(lambda x: x.update(allowed_platforms=["Google Drive", "GitHub"]))

    def test_changed_legacy_source_pin_denied(self):
        with self.assertRaisesRegex(ValueError, "PINNED_SOURCE_LOCK"):
            self.check(lambda x: x["source_lock"].update(mst_main_commit="f" * 40))

    def test_original_v1_module_count_remains_63(self):
        self.assertEqual(SOURCE["inherited_v1_modules"], 63)
        with self.assertRaisesRegex(ValueError, "PINNED_SOURCE_LOCK"):
            self.check(lambda x: x["source_lock"].update(inherited_v1_modules=62))

    def test_all_signed_gates_remain_open(self):
        self.assertEqual(OPEN_GATES, [f"SIGNED-G{i:02d}" for i in range(1, 9)])
        self.assertEqual(CHOICE["signed_gates_open"], OPEN_GATES)

    def test_single_closed_gate_not_allowed_by_choice(self):
        with self.assertRaisesRegex(PermissionError, "SIGNED_G01_G08"):
            self.check(lambda x: x["signed_gates_open"].pop())

    def test_reordered_gates_are_not_accepted(self):
        with self.assertRaises(PermissionError):
            self.check(lambda x: x["signed_gates_open"].reverse())

    def test_option_a_custody_controls_must_be_kept(self):
        self.assertEqual(len(CONTROLS), 9)
        self.assertEqual(CHOICE["option_a_controls_to_design"], CONTROLS)
        with self.assertRaisesRegex(ValueError, "REQUIRED_OPTION_A"):
            self.check(lambda x: x["option_a_controls_to_design"].pop())

    def test_root_admin_reset_risk_cannot_be_dropped(self):
        self.assertIn("ADMIN_BYPASS_TAMPER_RESPONSE_AND_ROOT_RESET_TEST", CONTROLS)
        with self.assertRaisesRegex(ValueError, "REQUIRED_OPTION_A"):
            self.check(lambda x: x["option_a_controls_to_design"].remove(
                "ADMIN_BYPASS_TAMPER_RESPONSE_AND_ROOT_RESET_TEST"
            ))

    def test_none_of_the_privileged_operations_are_allowed(self):
        self.assertEqual(len(BLOCKED_ACTIONS), 7)
        self.assertEqual(CHOICE["blocked_principal_actions"], BLOCKED_ACTIONS)

    def test_owner_provisioning_unblocked_by_mutation_denied(self):
        with self.assertRaisesRegex(PermissionError, "OWNER_GATED_ACTIONS"):
            self.check(lambda x: x["blocked_principal_actions"].remove(
                "CREATE_OR_MODIFY_PROTECTED_WITNESS_REF"
            ))

    def test_deletion_of_merge_guard_denied(self):
        with self.assertRaisesRegex(PermissionError, "OWNER_GATED_ACTIONS"):
            self.check(lambda x: x["blocked_principal_actions"].remove("MERGE_PR8"))

    def test_source_of_choice_must_remain_exact(self):
        for name in (
            "decision_source", "decision_source_quote",
            "decision_origin_integrity", "recorded_date",
        ):
            with self.subTest(name=name), self.assertRaisesRegex(
                ValueError, "OPTION_A_CHOICE_IDENTITY"
            ):
                self.check(lambda x, n=name: x.__setitem__(n, "other"))

    def test_no_unverified_revised_approval_scope(self):
        with self.assertRaisesRegex(ValueError, "OPTION_A_CHOICE_IDENTITY"):
            self.check(lambda x: x.update(
                implementation_status="G01_G02_PRODUCTION_APPROVED"
            ))

    def test_recorded_option_a_selected_scope_not_publisher_authorization(self):
        for name in (
            "privileged_witness_repo_or_ruleset_provisioning_approved",
            "licensed_vendor_data_ingestion_approved",
            "real_google_drive_market_cache_promotion_approved",
            "production_credentials_approved",
        ):
            self.assertIs(CHOICE[name], False)
        self.assertTrue(self.check()["owner_architecture_scope_choice_recorded"])

    def test_every_identity_field_is_version_locked(self):
        for name in REQUIRED_STRINGS:
            if name in ("selected_architecture", "recorded_date"):
                continue
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.check(lambda x, n=name: x.__setitem__(n, None))

    def test_legacy_module_count_float_coercion_denied(self):
        with self.assertRaisesRegex(ValueError, "PINNED_SOURCE_LOCK"):
            self.check(lambda x: x["source_lock"].update(
                inherited_v1_modules=63.0
            ))

    def test_legacy_source_commit_untyped_denied(self):
        with self.assertRaisesRegex(ValueError, "PINNED_SOURCE_LOCK"):
            self.check(lambda x: x["source_lock"].update(
                swing_commit=None
            ))

    def test_legacy_source_lock_must_be_mapping(self):
        with self.assertRaisesRegex(ValueError, "PINNED_SOURCE_LOCK"):
            self.check(lambda x: x.update(source_lock=[SOURCE]))

    def test_source_lock_extra_field_denied(self):
        with self.assertRaisesRegex(ValueError, "PINNED_SOURCE_LOCK"):
            self.check(lambda x: x["source_lock"].update(unapproved_new_service="GCP"))


if __name__ == "__main__":
    unittest.main()
