"""§472 S4 cumulative strict candidate chain, fictional only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.range_baseline_preview385 import RangeState385
from swing_trading.s4_holdings471 import S4StrictPlan472,S4StrictIngredient472,_strict472
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s4_holdings471 import fixture
from test_s4_rejection467 import evaluate,VARIANTS
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def strict(inputs,p,strategy=Strategy.SHORT,variant=VARIANTS[0]):
    r,s=evaluate(inputs,S4StrictPlan472(p),strategy,variant)
    return tuple(g for _,g in r.private_preview.assessments),s


class S4Strict472Tests(unittest.TestCase):
    def test_all_branches_strategies_and_frames(self):
        for strategy in Strategy:
            for variant in VARIANTS:
                for tf in (Timeframe.H1,Timeframe.D1):
                    inputs,p=fixture(variant,tf,strategy)
                    g,s=strict(inputs,p,strategy,variant)
                    self.assertEqual(len(g),4)
                    self.assertTrue(all(type(x) is S4StrictIngredient472 for x in g))
                    self.assertTrue(all(x.candidate_evidence_complete for x in g))
                    self.assertEqual(s["status"],"UNVERIFIED")
                    self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in s["phases"]))

    def test_unmatched_early_and_confirmation(self):
        for variant in VARIANTS:
            inputs,p=fixture(variant,close=D(101))
            g,_=strict(inputs,p,variant=variant)
            self.assertIs(g[3].state,RangeState385.NONMATCH)
            self.assertFalse(g[3].candidate_evidence_complete)
            inputs,p=fixture(variant)
            p=replace(p,geometry=replace(p.geometry,early=replace(p.geometry.early,candidate_epsilon=D(100))))
            g,_=strict(inputs,p,variant=variant)
            self.assertFalse(g[2].candidate_evidence_complete)
            self.assertFalse(g[3].candidate_evidence_complete)

    def test_holdings_not_enough_or_stale(self):
        inputs,p=fixture()
        for h,state in ((replace(p.holdings,reserved_shares=41),RangeState385.NONMATCH),
                        (replace(p.holdings,known_at_utc=p.holdings.known_at_utc-timedelta(seconds=61)),RangeState385.BLOCKED)):
            g,_=strict(inputs,replace(p,holdings=h))
            self.assertIs(g[3].state,state)
            self.assertFalse(g[3].candidate_evidence_complete)

    def test_no_prior_or_holdings_bypass(self):
        inputs,p=fixture()
        g,_=strict(inputs,p)
        proof=g[3].private_ingredient
        self.assertEqual(_strict472(proof,"R_F",False).mandatory_gaps,("PRIOR_PHASE",))
        self.assertEqual(_strict472(proof.private_geometry,"R_F",True).mandatory_gaps,("RF_SETTLED_HOLDINGS_SCENARIO",))
        self.assertFalse(_strict472(replace(proof,private_holdings=None),"R_F",True).candidate_evidence_complete)
        self.assertEqual(_strict472(None,"R_C",True).mandatory_gaps,("PLAN_R_C",))

    def test_bad_variant_or_malformed_plan(self):
        inputs,p=fixture()
        for plan,variant in ((S4StrictPlan472(p),VARIANTS[1]),(S4StrictPlan472(p.geometry),VARIANTS[0])):
            _,s=evaluate(inputs,plan,variant=variant)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_shared_modes_redaction_and_legacy(self):
        inputs,p=fixture()
        candidate=profile((request("S4",S4StrictPlan472(p),variant=VARIANTS[0]),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            result=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertTrue(row(result.private_preview,"S4").private_preview.assessments[3][1].candidate_evidence_complete)
            s=result.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for key in ("candidate_evidence_complete","mandatory_gaps","private_ingredient","fictional-policy"):
                self.assertNotIn(key,json.dumps(s))
        r,_=evaluate(inputs,p,variant=VARIANTS[0])
        self.assertNotIsInstance(r.private_preview.assessments[3][1],S4StrictIngredient472)
