"""M4 main PR governance proposal: fail closed without actual independent review."""
from copy import deepcopy
import json
from unittest import TestCase

from scripts import m4_main_positive_review_preflight as m


class OwnerMainReviewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=json.loads(m.PROPOSAL.read_text())
        cls.m4=json.loads(m.M4.read_text())
        cls.head="a"*40
        cls.rule=dict(id=m.RULE_ID,name="MST - Protect Main",source=m.REPO,
            target="branch",enforcement="active",
            conditions={"ref_name":{"include":["~DEFAULT_BRANCH"],"exclude":[]}},
            rules=[{"type":"deletion"},{"type":"non_fast_forward"},
                   {"type":"pull_request","parameters":{
                    "required_approving_review_count":0,
                    "require_code_owner_review":False,
                    "dismiss_stale_reviews_on_push":False,
                    "require_last_push_approval":False,
                    "required_review_thread_resolution":False}},
                   {"type":"required_status_checks","parameters":{
                    "required_status_checks":[{"context":x} for x in m.CONTEXTS]}}])
        cls.main=dict(name="main",protected=True,commit={"sha":m.PIN})
        cls.pr=dict(number=8,state="open",draft=True,merged=False,
            base={"ref":"main","sha":m.PIN},
            head={"sha":cls.head,"repo":{"full_name":m.REPO}})
        cls.locations={x:"MISSING_404" for x in m.CODEOWNERS}

    def result(self,plan=None,rule=None,branch=None,pr=None,reviews=None,
               locations=None,head=None,m4=None):
        return m.observe(
            self.plan if plan is None else plan,
            self.m4 if m4 is None else m4,
            self.rule if rule is None else rule,
            self.main if branch is None else branch,
            self.pr if pr is None else pr,
            [] if reviews is None else reviews,
            self.locations if locations is None else locations,
            self.head if head is None else head)

    def test_01_base_pass_is_no_go(self):
        self.assertEqual(self.result()["status"],
                         "NO_MANDATORY_POSITIVE_HUMAN_REVIEW_OWNER_DECISION_REQUIRED")

    def test_02_no_approved_policy(self):
        self.assertFalse(self.result()["policy_applied"])

    def test_03_exact_source_pins(self):
        self.assertEqual(self.plan["source_upstream"],m.UPSTREAM)
        self.assertEqual(self.plan["source_tree"],m.TREE)

    def test_04_seven_existing_owner_crosswalks(self):
        self.assertEqual([tuple(x[k] for k in ("proof","decision","gate"))
             for x in self.plan["owner_conditions"]],list(m.EVIDENCE))

    def test_05_minimum_human_approval_proposed_not_applied(self):
        self.assertEqual(self.plan["proposal"]["minimum_approvals"],1)
        self.assertEqual(self.result()["current_positive_reviews_required"],0)

    def test_06_three_foundation_checks_unchanged(self):
        self.assertTrue(self.result()["three_foundation_ci_required"])

    def test_07_codeowners_locations_scope_limited(self):
        self.assertEqual(len(self.result()["codeowners_scope_states"]),3)

    def test_08_pr_review_count_does_not_prove_independence(self):
        r=self.result(reviews=[{"state":"APPROVED"}])
        self.assertEqual(r["pr8_review_events_seen"],1)
        self.assertFalse(r["reviewer_identity_independently_verified"])

    def test_09_hidden_codeowners_does_not_prove_identity(self):
        p=dict(self.locations);p[".github/CODEOWNERS"]="UNKNOWN_403"
        self.assertFalse(self.result(locations=p)["reviewer_identity_independently_verified"])

    def test_10_no_bypass_authority(self):
        self.assertFalse(self.result()["effective_admin_bypass_independently_verified"])

    def test_11_forged_owner_approval_denied(self):
        p=deepcopy(self.plan);p["permissions"]["owner_approved"]=True
        with self.assertRaises(PermissionError):self.result(plan=p)

    def test_12_forged_trading_denied(self):
        p=deepcopy(self.plan);p["permissions"]["trading_authorized"]=True
        with self.assertRaises(PermissionError):self.result(plan=p)

    def test_13_removed_precondition_denied(self):
        p=deepcopy(self.plan);p["owner_conditions"].pop()
        with self.assertRaises(ValueError):self.result(plan=p)

    def test_14_private_id_field_denied(self):
        p=deepcopy(self.plan);p["private_account"]="fake"
        with self.assertRaises(ValueError):self.result(plan=p)

    def test_15_changed_target_needs_owner_decision(self):
        p=deepcopy(self.plan);p["proposal"]["minimum_approvals"]=0
        with self.assertRaises(ValueError):self.result(plan=p)

    def test_16_main_source_drift_denied(self):
        b=deepcopy(self.main);b["commit"]["sha"]="f"*40
        with self.assertRaises(ValueError):self.result(branch=b)

    def test_17_policy_approved_live_change_requires_reaudit(self):
        r=deepcopy(self.rule)
        next(x for x in r["rules"] if x["type"]=="pull_request")[
            "parameters"]["required_approving_review_count"]=1
        with self.assertRaises(ValueError):self.result(rule=r)

    def test_18_wrong_pr_head_denied(self):
        with self.assertRaises(ValueError):self.result(head="f"*40)

    def test_19_undrafted_pr_denied(self):
        p=deepcopy(self.pr);p["draft"]=False
        with self.assertRaises(ValueError):self.result(pr=p)

    def test_20_remove_deletion_guard_denied(self):
        r=deepcopy(self.rule);r["rules"]=[
            x for x in r["rules"] if x["type"]!="deletion"]
        with self.assertRaises(ValueError):self.result(rule=r)

    def test_21_missing_source_rights_do_not_authorize_release(self):
        self.assertFalse(self.result()["production_authorized"])

    def test_22_all_owner_proofs_still_not_received(self):
        self.assertTrue(all(x["state"]=="NOT_RECEIVED"
                            for x in self.m4["evidence_requirements"]))
