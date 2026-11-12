"""M4 owner-gated ruleset proposal and independently read-only audit tests."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.m4_witness_ruleset_preflight import validate_proposal, inspect_rulesets


PROPOSAL = json.loads(
    Path("docs/MST_M4_WITNESS_RULESET_PROPOSAL_20261109.json").read_text()
)
RULE_ID = 985031


def live_fixture():
    conf = PROPOSAL["proposed_ruleset"]
    summary = {"id": RULE_ID, "name": conf["name"], "enforcement": "active"}
    actual = {
        "id": RULE_ID, "name": conf["name"], "target": "branch",
        "source_type": "Repository", "source": "ngluonghoa/MST",
        "enforcement": "active",
        "conditions": deepcopy(conf["conditions"]),
        "rules": deepcopy(conf["rules"]), "bypass_actors": [],
        "current_user_can_bypass": "never",
    }
    return [summary], {RULE_ID: actual}


class WitnessRulePolicyTests(unittest.TestCase):
    def test_valid_draft_is_never_an_authorized_publisher(self):
        proposed = validate_proposal(PROPOSAL)
        self.assertEqual(proposed["conditions"]["ref_name"]["include"],
                         ["refs/heads/mst/m4-witness/v1"])
        missing = inspect_rulesets(PROPOSAL, [], {})
        self.assertEqual(missing["status"], "WITNESS_RULESET_NOT_PROVISIONED")
        self.assertFalse(missing["owner_approval_verified"])
        self.assertFalse(missing["protected_independent_floor"])
        self.assertFalse(missing["trading_authorized"])

    def test_main_only_ruleset_does_not_match_witness(self):
        other = [{"name": "MST - Protect Main", "id": 26801439,
                  "enforcement": "active"}]
        result = inspect_rulesets(PROPOSAL, other, {})
        self.assertEqual(result["status"], "WITNESS_RULESET_NOT_PROVISIONED")

    def test_exact_active_ruleset_remains_unattested(self):
        summaries, detail = live_fixture()
        result = inspect_rulesets(PROPOSAL, summaries, detail)
        self.assertEqual(result["status"], "WITNESS_RULESET_METADATA_MATCHED_UNATTESTED")
        self.assertTrue(result["ruleset_scope_verified"])
        self.assertTrue(result["bypass_list_verified"])
        self.assertFalse(result["witness_authoritative"])
        self.assertFalse(result["distributed_two_account_cas"])
        self.assertFalse(result["vendor_entitlement_verified"])
        self.assertFalse(result["market_data_use_authorized"])
        self.assertFalse(result["trading_authorized"])

    def test_actor_scoped_bypass_list_omitted_does_not_prove_absence(self):
        summaries, detail = live_fixture()
        detail[RULE_ID].pop("bypass_actors")
        result = inspect_rulesets(PROPOSAL, summaries, detail)
        self.assertFalse(result["bypass_list_verified"])
        self.assertFalse(result["owner_approval_verified"])

    def test_nonempty_bypass_list_rejected(self):
        summaries, detail = live_fixture()
        detail[RULE_ID]["bypass_actors"] = [
            {"actor_id": 1, "actor_type": "OrganizationAdmin", "bypass_mode": "always"}
        ]
        with self.assertRaisesRegex(ValueError, "UNREVIEWED_BYPASS"):
            inspect_rulesets(PROPOSAL, summaries, detail)

    def test_wrong_scope_including_main_or_all_rejected(self):
        for refs in (["~ALL"], ["~DEFAULT_BRANCH"], [
            "refs/heads/main", "refs/heads/mst/m4-witness/v1"
        ], ["refs/heads/mst/m4-witness/*"]):
            with self.subTest(refs=refs):
                summaries, detail = live_fixture()
                detail[RULE_ID]["conditions"]["ref_name"]["include"] = refs
                with self.assertRaisesRegex(ValueError, "WRONG_OR_OVERBROAD_SCOPE"):
                    inspect_rulesets(PROPOSAL, summaries, detail)

    def test_inactive_policy_and_wrong_repo_rejected(self):
        for field, value in (("enforcement", "evaluate"), ("source", "bad/repo"),
                             ("target", "tag")):
            summaries, detail = live_fixture()
            detail[RULE_ID][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                inspect_rulesets(PROPOSAL, summaries, detail)

    def test_required_signatures_and_nonforce_and_deletion_all_mandatory(self):
        for kind in ("required_signatures", "non_fast_forward", "deletion"):
            with self.subTest(kind=kind):
                summaries, detail = live_fixture()
                detail[RULE_ID]["rules"] = [
                    x for x in detail[RULE_ID]["rules"] if x["type"] != kind
                ]
                with self.assertRaisesRegex(ValueError, "PROTECTIONS_MISSING"):
                    inspect_rulesets(PROPOSAL, summaries, detail)

    def test_unsafe_update_or_creation_freeze_rules_denied(self):
        for kind in ("creation", "update"):
            summaries, detail = live_fixture()
            detail[RULE_ID]["rules"].append({"type": kind})
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "FREEZES"):
                inspect_rulesets(PROPOSAL, summaries, detail)

    def test_duplicate_ruleset_name_or_missing_detail_rejected(self):
        s, d = live_fixture()
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            inspect_rulesets(PROPOSAL, s + deepcopy(s), d)
        with self.assertRaisesRegex(ValueError, "DETAIL_REQUIRED"):
            inspect_rulesets(PROPOSAL, s, {})

    def test_proposal_ref_or_approval_cannot_be_mutated(self):
        for mutation in ("ref", "approved", "writes", "bypass", "scope"):
            with self.subTest(mutation=mutation):
                p = deepcopy(PROPOSAL)
                if mutation == "ref":
                    p["witness_ref"] = "refs/heads/main"
                elif mutation == "approved":
                    p["guardrails"]["owner_approval_received"] = True
                elif mutation == "writes":
                    p["guardrails"]["published_cache_authorized"] = True
                elif mutation == "bypass":
                    p["proposed_ruleset"]["bypass_actors"] = [{"actor_id": 1}]
                else:
                    p["proposed_ruleset"]["conditions"]["ref_name"]["include"] = ["~ALL"]
                with self.assertRaises(ValueError):
                    validate_proposal(p)

    def test_proposal_rejects_wrong_rules_or_bad_shape(self):
        for bad in (None, {"schema": "different"}, []):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_proposal(bad)
        p = deepcopy(PROPOSAL)
        p["proposed_ruleset"]["rules"].remove({"type": "required_signatures"})
        with self.assertRaisesRegex(ValueError, "RULES_DRIFT"):
            validate_proposal(p)

    def test_current_actor_bypass_and_double_rule_type_rejected(self):
        s, d = live_fixture()
        d[RULE_ID]["current_user_can_bypass"] = "always"
        with self.assertRaisesRegex(ValueError, "CURRENT_ACTOR_CAN_BYPASS"):
            inspect_rulesets(PROPOSAL, s, d)
        s, d = live_fixture()
        d[RULE_ID]["rules"].append({"type": "deletion"})
        with self.assertRaisesRegex(ValueError, "DUPLICATED_RULE"):
            inspect_rulesets(PROPOSAL, s, d)
