"""§465 synthetic scope, causal freshness and settled long sell feasibility."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_holdings445 import S1HoldingsPlan445
from swing_trading.s3_context454 import S3State454
from swing_trading.s3_holdings465 import S3SellScenario465,S3HoldingsPlan465,S3HoldingsIngredient465
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s3_context454 import run
from test_s3_confirm457 import fixture as micro_fixture
from test_s3_tp_confirm464 import setup as tp_fixture
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile

TP="S3/F_TP"
MICRO="S3/F_MICRO_BREAK"


def setup(variant=TP,strategy=Strategy.SHORT,tf=Timeframe.M15,*,match=True):
    if variant==TP:
        inputs,g=tp_fixture(strategy,close=D(20) if match else D(19))
        t=g.event.context.target
        target=inputs.snapshots_for(Timeframe.M15)[g.confirmation.target_index].selected
        s=S3SellScenario465(t.instrument_id,strategy,variant,t.plan_id,t.plan_version,
                            t.known_at_utc,t.expires_at_utc,30)
    else:
        inputs,g=micro_fixture(tf,close=D(11) if match else D(12))
        anchor=inputs.snapshots_for(Timeframe.M15)[g.anchor_index].selected
        target=inputs.snapshots_for(tf)[g.rf.target_index].selected
        s=S3SellScenario465(inputs.instrument_id,strategy,variant,"fictional-exit-465","v1",
                            anchor.market_bar_key.bar_start_utc-timedelta(minutes=1),
                            target.verified_at_utc+timedelta(hours=1),30)
    h=S1HoldingsPlan445(inputs.instrument_id,strategy,"fictional-settlement",target.verified_at_utc,
                        60,100,50,20,30)
    return inputs,S3HoldingsPlan465(g,s,h)


def rf(inputs,p,strategy=Strategy.SHORT,variant=TP):
    r,s=run(inputs,p,strategy,variant)
    return r.private_preview.assessments[3][1],s


class S3Holdings465Tests(unittest.TestCase):
    def test_all_confirm_branches_and_strategies(self):
        for strategy in Strategy:
            for variant,tf in ((TP,Timeframe.M15),(MICRO,Timeframe.M15),(MICRO,Timeframe.H1)):
                inputs,p=setup(variant,strategy,tf)
                g,s=rf(inputs,p,strategy,variant)
                self.assertIsInstance(g,S3HoldingsIngredient465)
                self.assertIs(g.state,S3State454.MATCH)
                self.assertEqual(g.private_holdings.available_shares,30)
                self.assertFalse(g.private_holdings.action_eligible)
                self.assertEqual(s["status"],"UNVERIFIED")

    def test_no_unsettled_or_reserved_balance_credit(self):
        inputs,p=setup()
        for settled,reserved in ((49,20),(0,0),(50,50)):
            h=replace(p.holdings,settled_shares=settled,reserved_shares=reserved)
            g,_=rf(inputs,replace(p,holdings=h))
            self.assertIs(g.state,S3State454.NONMATCH)
        for h in (replace(p.holdings,sell_shares=0),replace(p.holdings,settled_shares=101),
                  replace(p.holdings,open_shares=True)):
            _,s=run(inputs,replace(p,holdings=h),variant=TP)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_holdings_scope_freshness_and_plan_quantity(self):
        inputs,p=setup()
        for h in (replace(p.holdings,instrument_id="other"),replace(p.holdings,strategy=Strategy.SWING),
                  replace(p.holdings,sell_shares=29),
                  replace(p.holdings,known_at_utc=p.holdings.known_at_utc+timedelta(seconds=1)),
                  replace(p.holdings,known_at_utc=p.holdings.known_at_utc-timedelta(seconds=61))):
            g,_=rf(inputs,replace(p,holdings=h))
            self.assertIs(g.state,S3State454.BLOCKED)

    def test_preexisting_exit_and_exact_tp_plan_link(self):
        inputs,p=setup()
        for s in (replace(p.exit_plan,plan_id="other"),replace(p.exit_plan,plan_version="v2"),
                  replace(p.exit_plan,known_at_utc=p.exit_plan.known_at_utc+timedelta(seconds=1)),
                  replace(p.exit_plan,expires_at_utc=p.exit_plan.expires_at_utc+timedelta(seconds=1)),
                  replace(p.exit_plan,variant_id=MICRO)):
            self.assertIs(rf(inputs,replace(p,exit_plan=s))[0].state,S3State454.BLOCKED)
        inputs,p=setup(MICRO)
        a=inputs.snapshots_for(Timeframe.M15)[p.geometry.anchor_index].selected
        s=replace(p.exit_plan,known_at_utc=a.market_bar_key.bar_start_utc+timedelta(seconds=1))
        self.assertIs(rf(inputs,replace(p,exit_plan=s),variant=MICRO)[0].state,S3State454.BLOCKED)

    def test_no_geometry_bypass_or_wrong_variant(self):
        for variant in (TP,MICRO):
            inputs,p=setup(variant,match=False)
            g,_=rf(inputs,p,variant=variant)
            self.assertIs(g.state,S3State454.NONMATCH)
            self.assertNotIsInstance(g,S3HoldingsIngredient465)
            _,s=run(inputs,p,variant=MICRO if variant==TP else TP)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_same_modes_no_publication_and_legacy_unchanged(self):
        inputs,p=setup()
        candidate=profile((request("S3",p,variant=TP),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(r.private_preview,"S3").private_preview.assessments[3][1].state,S3State454.MATCH)
            s=r.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for private in (p.exit_plan.plan_id,p.holdings.policy_version,"private_holdings","available_shares"):
                self.assertNotIn(private,json.dumps(s))
        g,_=rf(inputs,p.geometry)
        self.assertNotIsInstance(g,S3HoldingsIngredient465)
        self.assertIs(g.state,S3State454.MATCH)
