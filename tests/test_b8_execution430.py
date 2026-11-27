"""§430 RF execution chain extraction regression; synthetic only."""
from dataclasses import replace
from decimal import Decimal as D
import json
import unittest

from swing_trading.b8_base_preview415 import B8State415, B8Ingredient415, B8ExtensionPlan423
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from test_b8_base415 import run
from test_b8_portfolio429 import model
from test_b8_band426 import bind as band
from test_b8_settlement427 import bind as settlement


def full(strategy=Strategy.SHORT,tf=Timeframe.H1):
    inputs,p=model(strategy,tf)
    p=band(inputs,p)
    return inputs,settlement(inputs,p,strategy)


class B8Execution430Tests(unittest.TestCase):
    def test_full_execution_chain_all_strategies_frames_variants(self):
        for tf in (Timeframe.H1,Timeframe.D1):
            for strategy in Strategy:
                for variant in ("B8/BASE","B8/INTRADAY_RVOL_TOD_PENDING"):
                    inputs,p=full(strategy,tf)
                    row,safe=run(inputs,p,strategy=strategy,variant=variant)
                    proof=row.private_preview.assessments[-1][1]
                    self.assertIs(type(proof),B8Ingredient415)
                    self.assertIs(proof.state,B8State415.MATCH)
                    for x in (proof.risk,proof.band,proof.settlement,proof.liquidity,proof.portfolio):
                        self.assertTrue(x.candidate_match)
                    self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_price_band_failure_preserves_earlier_risk(self):
        inputs,p=full()
        p=replace(p,rf=replace(p.rf,band=replace(p.rf.band,upper=D(16))))
        row,safe=run(inputs,p)
        proof=row.private_preview.assessments[-1][1]
        self.assertIsNotNone(proof.risk)
        self.assertIsNone(proof.settlement)
        self.assertIsNone(proof.liquidity)
        self.assertIsNone(proof.portfolio)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_settlement_failure_prevents_later_budget(self):
        inputs,p=full()
        p=replace(p,rf=replace(p.rf,settlement=replace(p.rf.settlement,instrument_id="other")))
        row,safe=run(inputs,p)
        proof=row.private_preview.assessments[-1][1]
        self.assertTrue(proof.band.candidate_match)
        self.assertIsNone(proof.liquidity)
        self.assertIsNone(proof.portfolio)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_anti_chase_nonmatch_never_promoted(self):
        inputs,p=full()
        p=replace(p,rf=replace(p.rf,extension=B8ExtensionPlan423(D(0))))
        row,safe=run(inputs,p)
        proof=row.private_preview.assessments[-1][1]
        self.assertFalse(proof.extension_candidate_match)
        self.assertIsNone(proof.portfolio)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_late_plan_validation_even_after_earlier_nonmatch(self):
        inputs,p=full()
        p=replace(p,rf=replace(p.rf,extension=B8ExtensionPlan423(D(0)),
                               portfolio=replace(p.rf.portfolio,equity=D(0))))
        _,safe=run(inputs,p)
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_chain_identity_and_redaction(self):
        inputs,p=full()
        row,safe=run(inputs,p)
        self.assertEqual(B8Ingredient415.__module__,"swing_trading.b8_base_preview415")
        self.assertEqual(B8State415.__module__,"swing_trading.b8_base_preview415")
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("cash_required","net_rr","grid_entry_ceiling","mean_turnover",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
