"""§466 strict S3 cumulative phase completeness, fictional only."""
from dataclasses import replace
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s3_context454 import S3State454
from swing_trading.s3_holdings465 import S3StrictPlan466,S3StrictIngredient466,_strict466
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s3_holdings465 import setup,TP,MICRO
from test_s3_context454 import run
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def strict(inputs,p,strategy=Strategy.SHORT,variant=TP):
    r,s=run(inputs,S3StrictPlan466(p),strategy,variant)
    return tuple(g for _,g in r.private_preview.assessments),s


class S3Strict466Tests(unittest.TestCase):
    def test_all_confirm_routes_and_strategies(self):
        for strategy in Strategy:
            for variant,tf in ((TP,Timeframe.M15),(MICRO,Timeframe.M15),(MICRO,Timeframe.H1)):
                inputs,p=setup(variant,strategy,tf)
                g,s=strict(inputs,p,strategy,variant)
                self.assertEqual(len(g),4)
                self.assertTrue(all(type(x) is S3StrictIngredient466 for x in g))
                self.assertTrue(all(x.candidate_evidence_complete for x in g))
                self.assertTrue(all(x.state is S3State454.MATCH for x in g))
                self.assertEqual(s["status"],"UNVERIFIED")
                self.assertTrue(all(not x["action_eligible"] and not x["phase_verified"] for x in s["phases"]))

    def test_missing_explicit_micro_phases(self):
        inputs,p=setup(MICRO)
        g,_=strict(inputs,replace(p,geometry=replace(p.geometry,near=None,choch=None)),variant=MICRO)
        self.assertEqual(g[1].mandatory_gaps,("PLAN_R_C",))
        self.assertEqual(g[2].mandatory_gaps,("PLAN_R_E",))
        self.assertFalse(g[3].candidate_evidence_complete)
        self.assertIs(g[3].state,S3State454.BLOCKED)

    def test_unmatched_rf_and_insufficient_holdings(self):
        for variant in (TP,MICRO):
            inputs,p=setup(variant,match=False)
            g,_=strict(inputs,p,variant=variant)
            self.assertIs(g[3].state,S3State454.NONMATCH)
            self.assertFalse(g[3].candidate_evidence_complete)
            inputs,p=setup(variant)
            g,_=strict(inputs,replace(p,holdings=replace(p.holdings,settled_shares=49)),variant=variant)
            self.assertIs(g[3].state,S3State454.NONMATCH)
            self.assertFalse(g[3].candidate_evidence_complete)

    def test_prior_and_holdings_proof_cannot_be_bypassed(self):
        inputs,p=setup()
        g,_=strict(inputs,p)
        proof=g[3].private_ingredient
        self.assertEqual(_strict466(proof,"R_F",False).mandatory_gaps,("PRIOR_PHASE",))
        self.assertFalse(_strict466(proof,"R_F",False).candidate_evidence_complete)
        self.assertEqual(_strict466(proof.private_geometry,"R_F",True).mandatory_gaps,
                         ("RF_SETTLED_HOLDINGS_SCENARIO",))
        self.assertFalse(_strict466(replace(proof,private_holdings=None),"R_F",True).candidate_evidence_complete)

    def test_wrong_scope_and_malformed_strict_plan(self):
        inputs,p=setup()
        for plan,variant in ((S3StrictPlan466(p),MICRO),(S3StrictPlan466(p.geometry),TP)):
            _,s=run(inputs,plan,variant=variant)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_shared_modes_and_redaction_and_legacy(self):
        inputs,p=setup()
        candidate=profile((request("S3",S3StrictPlan466(p),variant=TP),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertTrue(row(r.private_preview,"S3").private_preview.assessments[3][1].candidate_evidence_complete)
            s=r.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for private in ("candidate_evidence_complete","mandatory_gaps","private_ingredient",p.exit_plan.plan_id):
                self.assertNotIn(private,json.dumps(s))
        r,_=run(inputs,p,variant=TP)
        self.assertNotIsInstance(r.private_preview.assessments[3][1],S3StrictIngredient466)
