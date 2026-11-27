"""§471 S4 hypothetical settled holdings only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.range_baseline_preview385 import RangeState385
from swing_trading.s1_holdings445 import S1HoldingsPlan445
from swing_trading.s4_holdings471 import S4SellScenario471,S4HoldingsPlan471
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s4_confirm470 import fixture as confirm_fixture,rf
from test_s4_rejection467 import VARIANTS
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def fixture(variant=VARIANTS[0],tf=Timeframe.H1,strategy=Strategy.SHORT,**kw):
    inputs,g=confirm_fixture(variant,tf,**kw)
    c=g.early.context.context
    anchor=inputs.snapshots_for(c.target_tf)[c.target_index].selected
    target=inputs.snapshots_for(tf)[g.target_index].selected
    s=S4SellScenario471(inputs.instrument_id,strategy,variant,"fictional","v1",
                        anchor.market_bar_key.bar_start_utc,target.verified_at_utc,40)
    h=S1HoldingsPlan445(inputs.instrument_id,strategy,"fictional-policy",target.verified_at_utc,
                        60,100,80,40,40)
    return inputs,S4HoldingsPlan471(g,s,h)


class S4Holdings471Tests(unittest.TestCase):
    def test_all_strategies_variants_frames(self):
        for strategy in Strategy:
            for variant in VARIANTS:
                for tf in (Timeframe.H1,Timeframe.D1):
                    inputs,p=fixture(variant,tf,strategy)
                    g,s=rf(inputs,p,strategy,variant)
                    self.assertIs(g.state,RangeState385.MATCH)
                    self.assertEqual(g.private_holdings.available_shares,40)
                    self.assertFalse(g.private_holdings.action_eligible)
                    self.assertEqual(s["status"],"UNVERIFIED")

    def test_insufficient_and_impossible_balance(self):
        inputs,p=fixture()
        g,_=rf(inputs,replace(p,holdings=replace(p.holdings,reserved_shares=41)))
        self.assertIs(g.state,RangeState385.NONMATCH)
        from test_s4_rejection467 import evaluate
        _,s=evaluate(inputs,replace(p,holdings=replace(p.holdings,settled_shares=101)),variant=VARIANTS[0])
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_exit_scope_and_window(self):
        inputs,p=fixture()
        s=p.exit_plan
        for bad in (replace(s,instrument_id="other"),replace(s,variant_id=VARIANTS[1]),
                    replace(s,known_at_utc=s.known_at_utc+timedelta(seconds=1)),
                    replace(s,expires_at_utc=s.expires_at_utc-timedelta(seconds=1))):
            self.assertIs(rf(inputs,replace(p,exit_plan=bad))[0].state,RangeState385.BLOCKED)

    def test_holdings_scope_size_and_freshness(self):
        inputs,p=fixture()
        h=p.holdings
        for bad in (replace(h,instrument_id="other"),replace(h,sell_shares=39),
                    replace(h,known_at_utc=h.known_at_utc+timedelta(seconds=1)),
                    replace(h,known_at_utc=h.known_at_utc-timedelta(seconds=61))):
            self.assertIs(rf(inputs,replace(p,holdings=bad))[0].state,RangeState385.BLOCKED)

    def test_no_bypass_geometry(self):
        inputs,p=fixture(close=D(101))
        g,_=rf(inputs,p)
        self.assertIs(g.state,RangeState385.NONMATCH)
        self.assertFalse(hasattr(g,"private_holdings"))

    def test_shared_modes_and_redaction(self):
        inputs,p=fixture()
        candidate=profile((request("S4",p,variant=VARIANTS[0]),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            result=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(result.private_preview,"S4").private_preview.assessments[3][1].state,RangeState385.MATCH)
            s=result.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for secret in ("private_holdings","available_shares","fictional-policy",inputs.instrument_id):
                self.assertNotIn(secret,json.dumps(s))
