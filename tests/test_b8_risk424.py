"""§424 measured-base net reward/risk, fictional."""
from dataclasses import replace
from decimal import Decimal as D, localcontext
import json
import unittest

from swing_trading.b8_risk_geometry424 import B8MeasuredBaseRisk424
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from test_b8_rf418 import fixture
from test_b8_base415 import run


def plan(p,k=D("0.5"),*,buffer=D(0),buy=D(0),sell=D(0),tax=D(0)):
    return replace(p,rf=replace(p.rf,risk=B8MeasuredBaseRisk424(buffer,buy,sell,tax,k)))


class B8Risk424Tests(unittest.TestCase):
    def test_both_frames_strategies_variants(self):
        for tf in (Timeframe.H1,Timeframe.D1):
            for strategy in Strategy:
                for variant in ("B8/BASE","B8/INTRADAY_RVOL_TOD_PENDING"):
                    inputs,p=fixture(tf=tf)
                    row,safe=run(inputs,plan(p),strategy=strategy,variant=variant)
                    proof=row.private_preview.assessments[-1][1].risk
                    self.assertEqual((proof.stop,proof.target,proof.net_reward,proof.net_risk),
                                     (D(7),D(23),D(6),D(10)))
                    self.assertTrue(proof.candidate_match)
                    self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_explicit_costs_reduce_ratio(self):
        inputs,p=fixture()
        row,_=run(inputs,plan(p,buy=D(".01"),sell=D(".02"),tax=D(".01")))
        proof=row.private_preview.assessments[-1][1].risk
        self.assertEqual(proof.net_reward,D("5.14"))
        self.assertEqual(proof.net_risk,D("10.38"))
        self.assertFalse(proof.candidate_match)

    def test_stop_buffer_and_threshold(self):
        inputs,p=fixture()
        row,safe=run(inputs,plan(p,D(1),buffer=D(".5")))
        base,rf=row.private_preview.assessments[0][1],row.private_preview.assessments[-1][1]
        with localcontext() as ctx:
            ctx.prec=50
            self.assertEqual(rf.risk.stop,D(7)-base.private_atr*D(".5"))
        self.assertFalse(rf.risk.candidate_match)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_target_already_reached_and_invalid_stop(self):
        for close,buffer in ((D(23),D(0)),(D(17),D(10))):
            inputs,p=fixture(close=close)
            row,safe=run(inputs,plan(p,buffer=buffer))
            self.assertEqual(row.private_preview.assessments[-1][1].risk.state,"NONMATCH")
            self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_uncalibrated_and_invalid(self):
        inputs,p=fixture()
        row,safe=run(inputs,plan(p,None))
        self.assertIsNone(row.private_preview.assessments[-1][1].risk.candidate_match)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"DISTANCE_ONLY")
        for args in ({"k":D(0)},{"buy":D("-1")},{"sell":D(".8"),"tax":D(".2")},{"buffer":True}):
            _,safe=run(inputs,plan(p,**args))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_legacy_and_redaction(self):
        inputs,p=fixture()
        row,safe=run(inputs,plan(p))
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("net_reward","net_risk","net_rr","candidate_min_net_rr",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
        row,_=run(inputs,p)
        self.assertIsNone(row.private_preview.assessments[-1][1].risk)
