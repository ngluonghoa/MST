"""§491 S7 strict cumulative candidate chain, fictional only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.s7_holdings490 import S7StrictPlan491,S7StrictIngredient491,_strict491
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s7_holdings490 import fixture
from test_s7_breakdown486 import evaluate
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def strict(inputs,p,strategy=Strategy.SHORT):
    r,s=evaluate(inputs,S7StrictPlan491(p),strategy)
    return tuple(g for _,g in r.private_preview.assessments),s


class S7Strict491Tests(unittest.TestCase):
    def test_all_strategies_and_origin_frames(self):
        for strategy in Strategy:
            for tf in (Timeframe.H1,Timeframe.D1):
                inputs,p=fixture(tf,strategy)
                g,s=strict(inputs,p,strategy)
                self.assertEqual(len(g),4)
                self.assertTrue(all(type(x) is S7StrictIngredient491 for x in g))
                self.assertTrue(all(x.candidate_evidence_complete for x in g))
                self.assertEqual(s["status"],"UNVERIFIED")
                self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in s["phases"]))

    def test_unmatched_early_and_confirmation(self):
        inputs,p=fixture(close=D(3))
        g,_=strict(inputs,p)
        self.assertIs(g[3].state,S1State439.NONMATCH)
        self.assertFalse(g[3].candidate_evidence_complete)
        inputs,p=fixture()
        p=replace(p,geometry=replace(p.geometry,early=replace(p.geometry.early,retest=replace(p.geometry.early.retest,candidate_max_sessions=1))))
        g,_=strict(inputs,p)
        self.assertFalse(g[2].candidate_evidence_complete)
        self.assertFalse(g[3].candidate_evidence_complete)

    def test_holdings_not_enough_or_stale(self):
        inputs,p=fixture()
        for h,state in ((replace(p.holdings,reserved_shares=41),S1State439.NONMATCH),
                        (replace(p.holdings,known_at_utc=p.holdings.known_at_utc-timedelta(seconds=61)),S1State439.BLOCKED)):
            g,_=strict(inputs,replace(p,holdings=h))
            self.assertIs(g[3].state,state)
            self.assertFalse(g[3].candidate_evidence_complete)

    def test_no_prior_or_holdings_bypass(self):
        inputs,p=fixture()
        g,_=strict(inputs,p)
        proof=g[3].private_ingredient
        self.assertEqual(_strict491(proof,"R_F",False).mandatory_gaps,("PRIOR_PHASE",))
        self.assertEqual(_strict491(proof.private_geometry,"R_F",True).mandatory_gaps,("RF_SETTLED_HOLDINGS_SCENARIO",))
        self.assertFalse(_strict491(replace(proof,private_holdings=None),"R_F",True).candidate_evidence_complete)
        self.assertEqual(_strict491(None,"R_C",True).mandatory_gaps,("PLAN_R_C",))
        self.assertEqual(_strict491(replace(proof,private_geometry=None),"R_F",True).mandatory_gaps,("RF_MICRO_GEOMETRY",))

    def test_bad_scope_or_malformed_plan(self):
        inputs,p=fixture()
        for plan in (S7StrictPlan491(p.geometry),
                     S7StrictPlan491(replace(p,exit_plan=replace(p.exit_plan,variant_id="S4/E_BOS_DOWN")))):
            _,s=evaluate(inputs,plan)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_shared_modes_redaction_and_legacy(self):
        inputs,p=fixture()
        candidate=profile((request("S7",S7StrictPlan491(p),variant="S7/F_MICRO_BREAK"),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            result=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertTrue(row(result.private_preview,"S7").private_preview.assessments[3][1].candidate_evidence_complete)
            s=result.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for key in ("candidate_evidence_complete","mandatory_gaps","private_ingredient","fictional-policy"):
                self.assertNotIn(key,json.dumps(s))
        r,_=evaluate(inputs,p)
        self.assertNotIsInstance(r.private_preview.assessments[3][1],S7StrictIngredient491)
        r,s=evaluate(inputs,S7StrictPlan491(p),variant="S7/F_CONTINUATION")
        final=r.private_preview.assessments[3][1]
        self.assertFalse(final.candidate_evidence_complete)
        self.assertIs(final.state,S1State439.BLOCKED)
        self.assertEqual(final.reason,"CONTINUATION_PREDICATE_SPEC_PENDING")
