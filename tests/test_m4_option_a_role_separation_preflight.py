"""G01/G02 owner-role proposal: synthetic collisions never authorize access."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.m4_option_a_role_separation_preflight import (
    _FALSE, _OPEN, _PAIRS, _PRIVILEGED, _ROLES,
    analyze_hypothetical_aliases, check_role_topology,
)

PROPOSAL = json.loads(Path(
    "docs/MST_M4_OPTION_A_ROLE_SEPARATION_PROPOSAL_20261109.json"
).read_text(encoding="utf-8"))


class OptionARoleSeparationTests(unittest.TestCase):
    def check(self, edit=None):
        raw = deepcopy(PROPOSAL)
        if edit:
            edit(raw)
        return check_role_topology(raw)

    def test_zero_real_identities_eight_roles_and_eight_open_decisions(self):
        r = self.check()
        self.assertEqual(r["roles_proposed"], 8)
        self.assertEqual(r["roles_with_actual_principals"], 0)
        self.assertEqual(r["role_owner_decisions_open"], 8)
        self.assertEqual(r["required_distinct_principal_pairs"], 25)
        self.assertEqual(r["privileged_actions_blocked"], 9)
        self.assertIn("UNASSIGNED", r["status"])
        self.assertFalse(r["external_monotonic_floor_verified"])
        self.assertFalse(r["production_cache_read_authorized"])
        self.assertFalse(r["production_cache_write_authorized"])
        self.assertFalse(r["trading_authorized"])

    def test_all_roles_and_separation_pairs_are_locked(self):
        self.assertEqual([r["role"] for r in PROPOSAL["roles"]], list(_ROLES))
        self.assertEqual(PROPOSAL["required_distinct_principal_pairs"],
                         [list(pair) for pair in _PAIRS])
        self.assertEqual(len(_PAIRS), 25)
        self.assertEqual(len(set(_PAIRS)), len(_PAIRS))

    def test_all_owner_decisions_still_open(self):
        self.assertEqual(len(_OPEN), 8)
        for i, row in enumerate(PROPOSAL["owner_signoff_decisions"]):
            self.assertEqual(row["code"], f"R{i+1:02d}")
            self.assertEqual(row["state"], "OPEN")
            self.assertIsNone(row["approver_identity"])
            self.assertIsNone(row["proof_uri"])

    def test_pr_ci_stays_readonly_and_outside_privileged_roles(self):
        role = PROPOSAL["roles"][-1]
        self.assertEqual(role["role"], "PULL_REQUEST_CI")
        self.assertEqual(role["proposed_capabilities"],
                         ["read_repo_source", "run_synthetic_tests"])
        self.assertIn("access_signer_private_key", role["forbidden_capabilities"])
        self.assertIn("access_real_vendor_token", role["forbidden_capabilities"])
        self.assertIn("PULL_REQUEST_CI", {a for a,b in _PAIRS})

    def test_pr_ci_cannot_gain_owner_admin_capability(self):
        with self.assertRaisesRegex(ValueError, "ROLE_CAPABILITIES"):
            self.check(lambda r: r["roles"][-1]["proposed_capabilities"].append(
                "modify_ruleset"
            ))

    def test_pr_ci_cannot_drop_signer_secret_deny(self):
        with self.assertRaisesRegex(ValueError, "ROLE_FORBIDDEN"):
            self.check(lambda r: r["roles"][-1]["forbidden_capabilities"].remove(
                "access_signer_private_key"
            ))

    def test_signer_custodian_cannot_become_witness_publisher(self):
        with self.assertRaisesRegex(ValueError, "ROLE_CAPABILITIES"):
            self.check(lambda r: r["roles"][1]["proposed_capabilities"].append(
                "publish_cache"
            ))

    def test_policy_controller_cannot_grow_writer_role(self):
        with self.assertRaisesRegex(ValueError, "ROLE_CAPABILITIES"):
            self.check(lambda r: r["roles"][0]["proposed_capabilities"].append(
                "propose_append_candidate"
            ))

    def test_reader_cannot_gain_drive_write(self):
        with self.assertRaisesRegex(ValueError, "ROLE_CAPABILITIES"):
            self.check(lambda r: r["roles"][6]["proposed_capabilities"].append(
                "stage_immutable_chunk"
            ))

    def test_first_writer_cannot_gain_ruleset_change(self):
        with self.assertRaisesRegex(ValueError, "ROLE_CAPABILITIES"):
            self.check(lambda r: r["roles"][3]["proposed_capabilities"].append(
                "modify_ruleset"
            ))

    def test_role_binding_false_attestation_denied(self):
        with self.assertRaises(PermissionError):
            self.check(lambda r: r["roles"][3].update(
                principal_binding="writer-alpha", independent_identity_verified=True
            ))

    def test_declared_root_or_floor_proven_without_evidence_denied(self):
        for k in _FALSE:
            with self.subTest(k=k), self.assertRaisesRegex(
                PermissionError, "ROLE_PROPOSAL_CANNOT_SELF_AUTHORIZE"
            ):
                self.check(lambda r, key=k: r.__setitem__(key, True))

    def test_missing_authority_field_is_not_false(self):
        with self.assertRaises(PermissionError):
            self.check(lambda r: r.pop("licensed_vendor_rights_verified"))

    def test_unrecognized_owner_approval_field_denied(self):
        with self.assertRaisesRegex(ValueError, "NONCANONICAL_ROLE_POLICY"):
            self.check(lambda r: r.update(approved_by_owner=True))

    def test_alter_github_drive_only_choice_denied(self):
        with self.assertRaisesRegex(ValueError, "ROLE_POLICY_SOURCE_OR_SCOPE"):
            self.check(lambda r: r.update(scope_choice="B_CLOUD_KMS_FIRESTORE"))

    def test_drift_pinned_main_denied(self):
        with self.assertRaisesRegex(ValueError, "ROLE_POLICY_SOURCE_OR_SCOPE"):
            self.check(lambda r: r.update(baseline_main_commit="f" * 40))

    def test_claim_witness_exists_denied(self):
        with self.assertRaises(PermissionError):
            self.check(lambda r: r.update(witness_ref_provisioned=True))

    def test_legacy_review_count_0_fact_cannot_be_reclassified_as_positive(self):
        with self.assertRaisesRegex(ValueError, "ROLE_BASELINE_OBSERVATION"):
            self.check(lambda r: r.update(
                historical_observed_main_pr_review_approval_count=1
            ))

    def test_observed_review_zero_bool_false_is_not_integer_zero(self):
        with self.assertRaisesRegex(ValueError, "ROLE_BASELINE_OBSERVATION"):
            self.check(lambda r: r.update(
                historical_observed_main_pr_review_approval_count=False
            ))

    def test_historical_drive_visible_owner_count_is_not_two(self):
        with self.assertRaisesRegex(ValueError, "ROLE_BASELINE_OBSERVATION"):
            self.check(lambda r: r.update(
                historical_google_drive_visible_owner_count_per_project_folder=2
            ))

    def test_remove_any_pairwise_constraint_denied(self):
        with self.assertRaisesRegex(ValueError, "ROLE_SEPARATION_REQUIREMENTS_DRIFT"):
            self.check(lambda r: r["required_distinct_principal_pairs"].pop())

    def test_remove_policy_signer_constraint_denied(self):
        with self.assertRaisesRegex(ValueError, "ROLE_SEPARATION_REQUIREMENTS_DRIFT"):
            self.check(lambda r: r["required_distinct_principal_pairs"].remove(
                ["POLICY_CONTROLLER", "SIGNER_ROOT_CUSTODIAN"]
            ))

    def test_remove_writer_collision_constraint_denied(self):
        with self.assertRaisesRegex(ValueError, "ROLE_SEPARATION_REQUIREMENTS_DRIFT"):
            self.check(lambda r: r["required_distinct_principal_pairs"].remove(
                ["WITNESS_WRITER_A", "WITNESS_WRITER_B"]
            ))

    def test_drop_recovery_invariant_denied(self):
        with self.assertRaisesRegex(ValueError, "ROLE_DENY_POLICY_INCOMPLETE"):
            self.check(lambda r: r["failure_policy"].pop(
                "on_owner_admin_policy_reset"
            ))

    def test_forced_allow_on_missing_external_floor_denied(self):
        with self.assertRaisesRegex(ValueError, "UNSAFE_ROLE_FAILURE_POLICY"):
            self.check(lambda r: r["failure_policy"].update(
                on_missing_external_floor="ALLOW"
            ))

    def test_try_to_unblock_witness_provisioning_denied(self):
        self.assertEqual(len(_PRIVILEGED), 9)
        with self.assertRaises(PermissionError):
            self.check(lambda r: r["pending_privileged_actions"].remove(
                "CREATE_PROTECTED_WITNESS_REF"
            ))

    def test_owner_signoff_forged_proof_denied(self):
        with self.assertRaises(PermissionError):
            self.check(lambda r: r["owner_signoff_decisions"][0].update(
                proof_uri="https://example.invalid/fake"
            ))

    def test_owner_decision_self_closed_denied(self):
        with self.assertRaises(PermissionError):
            self.check(lambda r: r["owner_signoff_decisions"][1].update(
                state="CLOSED"
            ))

    def test_owner_decision_dropped_denied(self):
        with self.assertRaisesRegex(ValueError, "EIGHT_OPEN_ROLE_DECISIONS"):
            self.check(lambda r: r["owner_signoff_decisions"].pop())

    def test_role_tombstone_denied(self):
        with self.assertRaisesRegex(ValueError, "EIGHT_UNASSIGNED_ROLES"):
            self.check(lambda r: r["roles"].pop())

    def test_role_boundary_swap_denied(self):
        with self.assertRaisesRegex(ValueError, "ROLE_TRUST_BOUNDARY"):
            self.check(lambda r: r["roles"][4].update(
                trust_boundary="GITHUB_WITNESS_POLICY_ADMIN"
            ))

    def test_unknown_role_field_denied(self):
        with self.assertRaisesRegex(ValueError, "NONCANONICAL_ROLE_FIELDS"):
            self.check(lambda r: r["roles"][0].update(owner_approved=True))

    def test_untyped_topology_denied(self):
        for value in (None, [], True, "ready"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                check_role_topology(value)


class HypotheticalAliasCollisionTests(unittest.TestCase):
    def test_all_dummy_aliases_distinct_remain_unattested(self):
        x = analyze_hypothetical_aliases({
            role: "synthetic-" + str(i) for i, role in enumerate(_ROLES)
        })
        self.assertTrue(x["pairwise_constraints_satisfied_in_simulation"])
        self.assertFalse(x["actual_independent_owner_identity_verified"])
        self.assertFalse(x["production_cache_authorized"])
        self.assertEqual(x["pairwise_conflicts"], [])

    def test_one_dummy_alias_covers_both_real_writer_roles(self):
        aliases = {"WITNESS_WRITER_A": "same-test-person",
                   "WITNESS_WRITER_B": "same-test-person"}
        x = analyze_hypothetical_aliases(aliases)
        self.assertEqual(x["pairwise_conflicts"],
                         [["WITNESS_WRITER_A", "WITNESS_WRITER_B"]])
        self.assertFalse(x["pairwise_constraints_satisfied_in_simulation"])

    def test_signer_and_policy_same_account_rejected(self):
        x = analyze_hypothetical_aliases({
            "POLICY_CONTROLLER": "same-opaque",
            "SIGNER_ROOT_CUSTODIAN": "same-opaque",
        })
        self.assertIn(["POLICY_CONTROLLER", "SIGNER_ROOT_CUSTODIAN"],
                      x["pairwise_conflicts"])

    def test_untrusted_pr_ci_alias_admin_collision_rejected(self):
        x = analyze_hypothetical_aliases({
            "POLICY_CONTROLLER": "pr-bot",
            "PULL_REQUEST_CI": "pr-bot",
        })
        self.assertIn(["PULL_REQUEST_CI", "POLICY_CONTROLLER"],
                      x["pairwise_conflicts"])

    def test_revocation_controller_cannot_be_signer_or_writer(self):
        x = analyze_hypothetical_aliases({
            "SIGNER_ROOT_CUSTODIAN": "owner",
            "REVOCATION_CONTROLLER": "owner",
            "WITNESS_WRITER_A": "owner",
        })
        self.assertTrue(any("REVOCATION_CONTROLLER" in pair
                            for pair in x["pairwise_conflicts"]))

    def test_unknown_role_rejected(self):
        with self.assertRaisesRegex(ValueError, "UNRECOGNIZED_ROLE_BINDING"):
            analyze_hypothetical_aliases({"ROOT_ADMIN_GODMODE": "no"})

    def test_names_must_be_strings_no_credential_objects(self):
        for v in (None, True, 123, [], ""):
            with self.subTest(v=v), self.assertRaises(ValueError):
                analyze_hypothetical_aliases({"WITNESS_WRITER_A": v})

    def test_partial_assignment_not_evidence(self):
        x = analyze_hypothetical_aliases({"WITNESS_WRITER_A": "alice"})
        self.assertFalse(x["pairwise_constraints_satisfied_in_simulation"])
        self.assertFalse(x["production_cache_authorized"])

    def test_no_bindings_not_an_acceptance(self):
        x = analyze_hypothetical_aliases({})
        self.assertEqual(x["roles_declared_for_simulation"], 0)
        self.assertFalse(x["actual_independent_owner_identity_verified"])


if __name__ == "__main__":
    unittest.main()
