"""M4 witness owner packet must remain unapproved and unexecuted."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.m4_option_a_witness_change_preflight import (
    _DECISIONS, _FALSE, _ROLES, _STEPS, validate_change_packet,
)

ROOT = Path("docs")
def doc(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))

PACKET = doc("MST_M4_OPTION_A_WITNESS_OWNER_CHANGE_PACKET_20261109.json")
WITNESS = doc("MST_M4_WITNESS_RULESET_PROPOSAL_20261109.json")
ROLES = doc("MST_M4_OPTION_A_ROLE_SEPARATION_PROPOSAL_20261109.json")
CHOICE = doc("MST_M4_OPTION_A_SCOPE_SELECTION_20261109.json")


class OptionAWitnessChangeContractTests(unittest.TestCase):
    def check(self, edit=None, witness=None, roles=None, choice=None):
        packet = deepcopy(PACKET)
        if edit is not None:
            edit(packet)
        return validate_change_packet(
            packet, deepcopy(WITNESS) if witness is None else witness,
            deepcopy(ROLES) if roles is None else roles,
            deepcopy(CHOICE) if choice is None else choice,
        )

    def test_owner_packet_is_draft_only(self):
        r = self.check()
        self.assertEqual(r["owner_approval_gates_open"], 8)
        self.assertEqual(r["change_steps_not_executed"], 10)
        self.assertEqual(r["privileged_change_steps_require_owner"], 8)
        self.assertFalse(r["witness_ref_provisioned"])
        self.assertFalse(r["real_signer_enrolled"])
        self.assertFalse(r["real_writer_credentials_provisioned"])
        self.assertFalse(r["cache_read_authorized"])
        self.assertFalse(r["cache_write_authorized"])
        self.assertFalse(r["trading_authorized"])

    def test_exact_main_witness_and_option_a_scope(self):
        self.assertEqual(PACKET["repository"], "ngluonghoa/MST")
        self.assertEqual(PACKET["user_selected_platform_scope"],
                         "GITHUB_AND_GOOGLE_DRIVE_ONLY")
        self.assertEqual(PACKET["source_baseline"],
                         "4048f91beaaa3410116d97e35896c8b688384e19")
        self.assertEqual(PACKET["witness_ref"],
                         "refs/heads/mst/m4-witness/v1")

    def test_exact_ref_only_does_not_cover_main(self):
        self.assertEqual(PACKET["expected_ruleset_condition"], {
            "include": ["refs/heads/mst/m4-witness/v1"], "exclude": [],
        })
        self.assertNotIn("refs/heads/main",
                         PACKET["expected_ruleset_condition"]["include"])

    def test_rule_proposal_has_no_unenrolled_writer_lockout(self):
        self.assertEqual(PACKET["suggested_rule_types"],
                         ["deletion", "non_fast_forward", "required_signatures"])
        self.assertEqual(PACKET["forbidden_rule_types_for_unenrolled_writers"],
                         ["creation", "update"])
        self.assertEqual(PACKET["proposed_bypass_actors"], [])

    def test_all_role_boundaries_must_be_reviewed(self):
        self.assertEqual(PACKET["privileged_roles_to_verify"], list(_ROLES))
        self.assertEqual(len(_ROLES), 7)
        self.assertNotIn("PULL_REQUEST_CI", _ROLES)

    def test_all_change_steps_unexecuted(self):
        self.assertEqual([r["operation"] for r in PACKET["change_sequence"]],
                         list(_STEPS))
        for i, s in enumerate(PACKET["change_sequence"]):
            self.assertEqual(s["status"], "NOT_EXECUTED")
            self.assertIsNone(s["execution_evidence_uri"])
            self.assertFalse(s["actual_resource_mutation"])
            self.assertEqual(s["requires_independent_owner_authorization"], i >= 2)

    def test_bootstrap_before_witness_ruleset_required(self):
        operations = [v["operation"] for v in PACKET["change_sequence"]]
        self.assertLess(operations.index("OWNER_GATED_GENESIS_BRANCH_CREATION"),
                        operations.index("OWNER_GATED_RULESET_INSTALLATION"))

    def test_all_owner_decisions_open(self):
        self.assertEqual(len(_DECISIONS), 8)
        for i, d in enumerate(PACKET["owner_approvals"]):
            self.assertEqual(d["id"], f"C{i+1:02d}")
            self.assertEqual(d["decision"], _DECISIONS[i])
            self.assertEqual(d["status"], "OPEN_OWNER_REVIEW_REQUIRED")
            self.assertIsNone(d["owner_principal"])
            self.assertIsNone(d["approval_receipt_uri"])

    def test_fake_production_flags_denied(self):
        for key in _FALSE:
            with self.subTest(flag=key), self.assertRaises(PermissionError):
                self.check(lambda d, k=key: d.__setitem__(k, True))

    def test_missing_production_flag_denied(self):
        with self.assertRaisesRegex(ValueError, "NONCANONICAL"):
            self.check(lambda d: d.pop("production_cache_write_authorized"))

    def test_unknown_approval_field_denied(self):
        with self.assertRaisesRegex(ValueError, "NONCANONICAL"):
            self.check(lambda d: d.update(owner_authorized=True))

    def test_force_main_ruleset_update_denied(self):
        with self.assertRaisesRegex(ValueError, "WITNESS_OWNER_CHANGE_IDENTITY"):
            self.check(lambda d: d.update(
                proposed_witness_ruleset_path="docs/MAIN_FORCE_EDIT.json"
            ))

    def test_change_to_gcp_scope_denied(self):
        with self.assertRaisesRegex(ValueError, "WITNESS_OWNER_CHANGE_IDENTITY"):
            self.check(lambda d: d.update(
                user_selected_platform_scope="GITHUB_DRIVE_AND_FIRESTORE"
            ))

    def test_wrong_witness_ref_denied(self):
        with self.assertRaisesRegex(ValueError, "WITNESS_OWNER_CHANGE_IDENTITY"):
            self.check(lambda d: d.update(witness_ref="refs/heads/main"))

    def test_wrong_main_source_pin_denied(self):
        with self.assertRaisesRegex(ValueError, "WITNESS_OWNER_CHANGE_IDENTITY"):
            self.check(lambda d: d.update(source_baseline="f" * 40))

    def test_current_main_approval_count_cannot_be_misreported(self):
        with self.assertRaisesRegex(ValueError, "LIVE_MAIN_RULESET_BASELINE_DRIFT"):
            self.check(lambda d: d.update(current_main_required_approving_reviews=2))

    def test_review_count_bool_false_is_not_zero_integer(self):
        with self.assertRaisesRegex(ValueError, "LIVE_MAIN_RULESET_BASELINE_DRIFT"):
            self.check(lambda d: d.update(current_main_required_approving_reviews=False))

    def test_main_ruleset_id_cannot_be_forged(self):
        with self.assertRaisesRegex(ValueError, "LIVE_MAIN_RULESET_BASELINE_DRIFT"):
            self.check(lambda d: d.update(current_main_ruleset_id=1))

    def test_new_witness_has_no_bypass_actors(self):
        with self.assertRaises(PermissionError):
            self.check(lambda d: d.update(proposed_bypass_actors=[
                {"actor_id": 1, "actor_type": "RepositoryRole", "bypass_mode": "always"}
            ]))

    def test_witness_ruleset_must_be_exact_ref_only(self):
        with self.assertRaisesRegex(ValueError, "WITNESS_RULESET_EXACT_SCOPE_DRIFT"):
            self.check(lambda d: d["expected_ruleset_condition"]["include"].append(
                "~DEFAULT_BRANCH"
            ))

    def test_remove_signature_rule_denied(self):
        with self.assertRaisesRegex(ValueError, "WITNESS_PROTECTIONS_DRIFT"):
            self.check(lambda d: d["suggested_rule_types"].remove("required_signatures"))

    def test_creation_rule_cannot_be_silently_added(self):
        with self.assertRaisesRegex(ValueError, "WITNESS_PROTECTIONS_DRIFT"):
            self.check(lambda d: d["suggested_rule_types"].append("creation"))

    def test_unenrolled_writer_lockout_caveat_cannot_be_removed(self):
        with self.assertRaisesRegex(ValueError, "WITNESS_WRITER_LOCKOUT_RISK"):
            self.check(lambda d: d.update(
                forbidden_rule_types_for_unenrolled_writers=["creation"]
            ))

    def test_scope_actor_roles_cannot_be_dropped(self):
        with self.assertRaisesRegex(ValueError, "WITNESS_REQUIRED_OWNER_ROLES_DRIFT"):
            self.check(lambda d: d["privileged_roles_to_verify"].pop())

    def test_remove_one_owner_decision_denied(self):
        with self.assertRaisesRegex(ValueError, "EIGHT_OPEN_WITNESS_OWNER_APPROVALS"):
            self.check(lambda d: d["owner_approvals"].pop())

    def test_fake_approval_status_denied(self):
        with self.assertRaises(PermissionError):
            self.check(lambda d: d["owner_approvals"][0].update(
                status="APPROVED"
            ))

    def test_fake_owner_approval_evidence_uri_denied(self):
        with self.assertRaises(PermissionError):
            self.check(lambda d: d["owner_approvals"][3].update(
                approval_receipt_uri="https://example.invalid/owner-signed"
            ))

    def test_approval_identity_prematurely_filled_denied(self):
        with self.assertRaises(PermissionError):
            self.check(lambda d: d["owner_approvals"][0].update(
                owner_principal="fake-admin"
            ))

    def test_owner_approval_extra_field_denied(self):
        with self.assertRaisesRegex(ValueError, "NONCANONICAL_WITNESS_OWNER_APPROVAL"):
            self.check(lambda d: d["owner_approvals"][0].update(
                passed_ci_so_approved=True
            ))

    def test_drop_change_step_denied(self):
        with self.assertRaisesRegex(ValueError, "TEN_ORDERED_WITNESS_CHANGE_STEPS"):
            self.check(lambda d: d["change_sequence"].pop())

    def test_swap_bootstrap_and_apply_step_denied(self):
        with self.assertRaises(PermissionError):
            self.check(lambda d: d["change_sequence"].reverse())

    def test_any_change_step_execution_forbidden_now(self):
        with self.assertRaises(PermissionError):
            self.check(lambda d: d["change_sequence"][3].update(
                status="EXECUTED", actual_resource_mutation=True
            ))

    def test_owner_gated_bootstrap_cannot_be_reclassified_no_approval(self):
        with self.assertRaises(PermissionError):
            self.check(lambda d: d["change_sequence"][3].update(
                requires_independent_owner_authorization=False
            ))

    def test_unapproved_owner_step_evidence_denied(self):
        with self.assertRaises(PermissionError):
            self.check(lambda d: d["change_sequence"][4].update(
                execution_evidence_uri="https://example.invalid/fake"
            ))

    def test_change_step_forged_prepared_execution_denied(self):
        with self.assertRaises(PermissionError):
            self.check(lambda d: d["change_sequence"][2].update(
                status="READY_TO_APPLY"
            ))

    def test_current_witness_cannot_be_self_reported_created(self):
        with self.assertRaises(PermissionError):
            self.check(lambda d: d.update(current_witness_ref_exists=True))

    def test_pr_ci_bypass_visibility_missing_cannot_be_claimed_present(self):
        with self.assertRaises(PermissionError):
            self.check(lambda d: d.update(current_ci_token_bypass_list_visible=True))

    def test_root_admin_reset_risk_cannot_be_omitted(self):
        with self.assertRaisesRegex(ValueError, "WITNESS_OWNER_CHANGE_IDENTITY"):
            self.check(lambda d: d.update(residual_risk="SAFE_ALL_ADMIN"))

    def test_recovery_cannot_automatically_restart_generation_one(self):
        with self.assertRaisesRegex(ValueError, "WITNESS_OWNER_CHANGE_IDENTITY"):
            self.check(lambda d: d.update(
                recovery_rule="AUTOMATICALLY_RESTART_GENERATION_ONE"
            ))

    def test_historical_draft_witness_proposal_is_valid(self):
        self.check()
        self.assertEqual(WITNESS["guardrails"]["owner_approval_received"], False)

    def test_prior_ruleset_proposal_drift_detected(self):
        w = deepcopy(WITNESS)
        w["proposed_ruleset"]["rules"] = [
            {"type": "deletion"}, {"type": "non_fast_forward"},
        ]
        with self.assertRaises(ValueError):
            self.check(witness=w)

    def test_prior_role_proposal_drift_detected(self):
        roles = deepcopy(ROLES)
        roles["roles"][0]["principal_binding"] = "unapproved-controller"
        with self.assertRaises(PermissionError):
            self.check(roles=roles)

    def test_platform_decision_record_drift_detected(self):
        choice = deepcopy(CHOICE)
        choice["selected_architecture"] = "B_CLOUD_KMS_FIRESTORE"
        with self.assertRaises(ValueError):
            self.check(choice=choice)

    def test_nonstrict_input_type_denied(self):
        for raw in ([], None, True, "APPROVED"):
            with self.subTest(value=raw), self.assertRaises(ValueError):
                validate_change_packet(raw, WITNESS, ROLES, CHOICE)


if __name__ == "__main__":
    unittest.main()
