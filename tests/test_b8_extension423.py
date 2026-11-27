"""§423 B8 RF same-resistance anti-chase arithmetic, fictional."""
from dataclasses import replace
from decimal import Decimal as D
import json
import unittest

from swing_trading.b8_base_preview415 import B8ExtensionPlan423
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from test_b8_rf418 import fixture
from test_b8_base415 import run


def plan(p,k):
    return replace(p,rf=replace(p.rf,extension=B8ExtensionPlan423(k)))


class B8Extension423Tests(unittest.TestCase):
    def test_both_frames_strategies_variants(self):
        for tf in (Timeframe.H1,Timeframe.D1):
            for strategy in Strategy:
                for variant in ("B8/BASE","B8/INTRADAY_RVOL_TOD_PENDING"):
                    inputs,p=fixture(tf=tf)
                    row,safe=run(inputs,plan(p,D("0.7")),strategy=strategy,variant=variant)
                    base,rf=row.private_preview.assessments[0][1],row.private_preview.assessments[-1][1]
                    self.assertEqual(rf.extension_atr,D(2)/base.private_atr)
                    self.assertTrue(rf.extension_candidate_match)
                    self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_chase_and_zero_threshold(self):
        for close,k in ((D(20),D("0.7")),(D(17),D(0))):
            inputs,p=fixture(close=close)
            row,safe=run(inputs,plan(p,k))
            self.assertFalse(row.private_preview.assessments[-1][1].extension_candidate_match)
            self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_exact_boundary_inclusive(self):
        inputs,p=fixture()
        row,_=run(inputs,p)
        atr=row.private_preview.assessments[0][1].private_atr
        inputs,p=fixture(close=D(15)+atr)
        row,_=run(inputs,plan(p,D(1)))
        self.assertTrue(row.private_preview.assessments[-1][1].extension_candidate_match)

    def test_uncalibrated_and_legacy(self):
        inputs,p=fixture()
        row,safe=run(inputs,plan(p,None))
        proof=row.private_preview.assessments[-1][1]
        self.assertIsNone(proof.extension_candidate_match)
        self.assertIsNotNone(proof.extension_atr)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"DISTANCE_ONLY")
        row,_=run(inputs,p)
        self.assertIsNone(row.private_preview.assessments[-1][1].extension_atr)

    def test_invalid_and_nonmatch_geometry(self):
        inputs,p=fixture()
        for k in (D("-1"),D("NaN"),True):
            _,safe=run(inputs,plan(p,k))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        inputs,p=fixture(close=D(14))
        row,_=run(inputs,plan(p,D("0.7")))
        self.assertIsNone(row.private_preview.assessments[-1][1].extension_atr)

    def test_no_authority_or_raw_leakage(self):
        inputs,p=fixture()
        row,safe=run(inputs,plan(p,D("0.7")))
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("extension_atr","candidate_max_extension_atr",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
