"""§431 explicit same-frame RF RVOL threshold candidate, fictional."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from test_b8_base415 import run
from test_b8_rf_volume419 import fixture


def threshold(p,k):
    return replace(p,rf=replace(p.rf,candidate_min_rvol=k))


class B8RFThreshold431Tests(unittest.TestCase):
    def test_inclusive_both_frames_strategies_variants(self):
        for tf in (Timeframe.H1,Timeframe.D1):
            for strategy in Strategy:
                for variant in ("B8/BASE","B8/INTRADAY_RVOL_TOD_PENDING"):
                    inputs,p=fixture(tf)
                    row,safe=run(inputs,threshold(p,D("2.5")),strategy=strategy,variant=variant)
                    proof=row.private_preview.assessments[-1][1]
                    self.assertTrue(proof.rvol_candidate_match)
                    self.assertEqual(proof.rvol.value,D("2.5"))
                    self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_below_explicit_threshold(self):
        inputs,p=fixture(low_volume=True)
        row,safe=run(inputs,threshold(p,D("1.3")))
        self.assertFalse(row.private_preview.assessments[-1][1].rvol_candidate_match)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_explicit_threshold_requires_raw_witness(self):
        inputs,p=fixture()
        p=replace(p,rf=replace(p.rf,volume=None,candidate_min_rvol=D(1)))
        _,safe=run(inputs,p)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"MISSING_INPUT")

    def test_later_target_witness_blocks(self):
        inputs,p=fixture()
        v=p.rf.volume
        w=v.witnesses[-1]
        later=replace(w,verified_at_utc=w.verified_at_utc+timedelta(minutes=1))
        p=replace(p,rf=replace(p.rf,volume=replace(v,witnesses=v.witnesses[:-1]+(later,)),
                               candidate_min_rvol=D(1)))
        _,safe=run(inputs,p)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_no_default_and_invalid(self):
        inputs,p=fixture(low_volume=True)
        row,_=run(inputs,p)
        self.assertIsNone(row.private_preview.assessments[-1][1].rvol_candidate_match)
        for k in (D(0),D("-1"),D("NaN"),True,1.3):
            _,safe=run(inputs,threshold(p,k))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_redaction_no_authority(self):
        inputs,p=fixture()
        row,safe=run(inputs,threshold(p,D(1)))
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("candidate_min_rvol","rvol_candidate_match",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
