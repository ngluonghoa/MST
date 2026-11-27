"""§490 S7 hypothetical settled holdings only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.s1_holdings445 import S1HoldingsPlan445
from swing_trading.s7_holdings490 import S7SellScenario490,S7HoldingsPlan490
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s7_confirm489 import fixture as confirm_fixture,rf
from test_s7_breakdown486 import evaluate
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def fixture(tf=Timeframe.H1,strategy=Strategy.SHORT,**kw):
    inputs,g=confirm_fixture(tf,**kw)
    c=g.early.retest.breakdown
    anchor=inputs.snapshots_for(c.timeframe)[c.target_index].selected
    target=inputs.snapshots_for(g.timeframe)[g.target_index].selected
    s=S7SellScenario490(inputs.instrument_id,strategy,"S7/F_MICRO_BREAK","fictional-s7","v1",c.event_id,
                        anchor.market_bar_key.bar_start_utc,target.verified_at_utc,40)
    h=S1HoldingsPlan445(inputs.instrument_id,strategy,"fictional-policy",target.verified_at_utc,
                        60,100,80,40,40)
    return inputs,S7HoldingsPlan490(g,s,h)


class S7Holdings490Tests(unittest.TestCase):
    def test_all_strategies_and_origin_frames(self):
        for strategy in Strategy:
            for tf in (Timeframe.H1,Timeframe.D1):
                inputs,p=fixture(tf,strategy)
                g,s=rf(inputs,p,strategy)
                self.assertIs(g.state,S1State439.MATCH)
                self.assertEqual(g.private_holdings.available_shares,40)
                self.assertFalse(g.private_holdings.action_eligible)
                self.assertEqual(s["status"],"UNVERIFIED")

    def test_insufficient_and_impossible_balance(self):
        inputs,p=fixture()
        g,_=rf(inputs,replace(p,holdings=replace(p.holdings,reserved_shares=41)))
        self.assertIs(g.state,S1State439.NONMATCH)
        _,s=evaluate(inputs,replace(p,holdings=replace(p.holdings,settled_shares=101)))
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_exit_scope_and_window(self):
        inputs,p=fixture()
        s=p.exit_plan
        for bad in (replace(s,instrument_id="other"),replace(s,strategy=Strategy.SWING),replace(s,breakdown_event_id="wrong"),
                    replace(s,known_at_utc=s.known_at_utc+timedelta(seconds=1)),
                    replace(s,expires_at_utc=s.expires_at_utc-timedelta(seconds=1))):
            self.assertIs(rf(inputs,replace(p,exit_plan=bad))[0].state,S1State439.BLOCKED)
        _,safe=evaluate(inputs,replace(p,exit_plan=replace(s,variant_id="S4/E_BOS_DOWN")))
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_holdings_scope_size_and_freshness(self):
        inputs,p=fixture()
        h=p.holdings
        for bad in (replace(h,instrument_id="other"),replace(h,sell_shares=39),
                    replace(h,known_at_utc=h.known_at_utc+timedelta(seconds=1)),
                    replace(h,known_at_utc=h.known_at_utc-timedelta(seconds=61))):
            self.assertIs(rf(inputs,replace(p,holdings=bad))[0].state,S1State439.BLOCKED)

    def test_no_bypass_geometry(self):
        inputs,p=fixture(close=D(3))
        g,_=rf(inputs,p)
        self.assertIs(g.state,S1State439.NONMATCH)
        self.assertFalse(hasattr(g,"private_holdings"))
        inputs,p=fixture()
        r,s=evaluate(inputs,p,variant="S7/F_CONTINUATION")
        proof=r.private_preview.assessments[3][1]
        self.assertIs(proof.state,S1State439.BLOCKED)
        self.assertEqual(proof.reason,"CONTINUATION_PREDICATE_SPEC_PENDING")
        self.assertFalse(hasattr(proof,"private_holdings"))

    def test_shared_modes_and_redaction(self):
        inputs,p=fixture()
        candidate=profile((request("S7",p,variant="S7/F_MICRO_BREAK"),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            result=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(result.private_preview,"S7").private_preview.assessments[3][1].state,S1State439.MATCH)
            s=result.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for secret in ("private_holdings","available_shares","fictional-policy",p.exit_plan.breakdown_event_id,inputs.instrument_id):
                self.assertNotIn(secret,json.dumps(s))
