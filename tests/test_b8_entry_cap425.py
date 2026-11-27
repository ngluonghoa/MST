"""§425 combined theoretical entry ceiling, fictional and uncalibrated."""
from dataclasses import replace
from decimal import Decimal as D, localcontext, ROUND_FLOOR
import json
import unittest

from swing_trading.b8_base_preview415 import B8ExtensionPlan423
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from test_b8_rf418 import fixture
from test_b8_base415 import run
from test_b8_risk424 import plan


def combined(p,k=D(".7"),rr=D(".5"),**cost):
    p=plan(p,rr,**cost)
    return replace(p,rf=replace(p.rf,extension=B8ExtensionPlan423(k)))


class B8EntryCap425Tests(unittest.TestCase):
    def test_rr_cap_is_tighter_both_frames_strategies_variants(self):
        for tf in (Timeframe.H1,Timeframe.D1):
            for strategy in Strategy:
                for variant in ("B8/BASE","B8/INTRADAY_RVOL_TOD_PENDING"):
                    inputs,p=fixture(tf=tf)
                    row,safe=run(inputs,combined(p),strategy=strategy,variant=variant)
                    proof=row.private_preview.assessments[-1][1].risk
                    with localcontext() as ctx:
                        ctx.prec=50
                        ctx.rounding=ROUND_FLOOR
                        self.assertEqual(proof.max_entry,(D(23)+D(".5")*D(7))/D("1.5"))
                    self.assertLess(proof.rr_entry_ceiling,proof.atr_entry_ceiling)
                    self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_atr_cap_tighter(self):
        inputs,p=fixture()
        row,_=run(inputs,combined(p,D(".5")))
        base,proof=row.private_preview.assessments[0][1],row.private_preview.assessments[-1][1].risk
        with localcontext() as ctx:
            ctx.prec=50
            ctx.rounding=ROUND_FLOOR
            self.assertEqual(proof.max_entry,D(15)+D(".5")*base.private_atr)
        self.assertLess(proof.atr_entry_ceiling,proof.rr_entry_ceiling)

    def test_excess_entry_retains_nonmatch_and_cap(self):
        inputs,p=fixture(close=D(18))
        row,safe=run(inputs,combined(p,D(".5")))
        proof=row.private_preview.assessments[-1][1]
        self.assertFalse(proof.extension_candidate_match)
        self.assertLess(proof.risk.max_entry,D(18))
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_cost_aware_cap(self):
        inputs,p=fixture()
        row,_=run(inputs,combined(p,buy=D(".01"),sell=D(".02"),tax=D(".01")))
        proof=row.private_preview.assessments[-1][1].risk
        with localcontext() as ctx:
            ctx.prec=50
            ctx.rounding=ROUND_FLOOR
            self.assertEqual(proof.rr_entry_ceiling,D("26.5")*D(".97")/(D("1.5")*D("1.01")))
        self.assertFalse(proof.candidate_match)

    def test_no_implicit_cap(self):
        inputs,p=fixture()
        row,_=run(inputs,plan(p))
        self.assertIsNone(row.private_preview.assessments[-1][1].risk.max_entry)
        row,_=run(inputs,combined(p,rr=None))
        self.assertIsNone(row.private_preview.assessments[-1][1].risk.max_entry)
        row,_=run(inputs,combined(p,k=None))
        self.assertIsNone(row.private_preview.assessments[-1][1].risk)

    def test_no_authority_or_leakage(self):
        inputs,p=fixture()
        row,safe=run(inputs,combined(p))
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("max_entry","atr_entry_ceiling","rr_entry_ceiling",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
