"""§432 explicit selected-variant raw TOD threshold, fictional."""
from dataclasses import replace
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from test_b8_base415 import run
from test_b8_tod420 import fixture, VARIANT


def threshold(p,k):
    return replace(p,early=replace(p.early,candidate_min_rvol_tod=k))


class B8TODThreshold432Tests(unittest.TestCase):
    def test_inclusive_both_strategies(self):
        for strategy in Strategy:
            inputs,p=fixture()
            row,safe=run(inputs,threshold(p,D(2)),strategy=strategy,variant=VARIANT)
            proof=row.private_preview.assessments[2][1]
            self.assertTrue(proof.tod_candidate_match)
            self.assertEqual(proof.rvol.value,D(2))
            self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_below_threshold_prevents_rf(self):
        inputs,p=fixture()
        row,safe=run(inputs,threshold(p,D("2.1")),variant=VARIANT)
        self.assertFalse(row.private_preview.assessments[2][1].tod_candidate_match)
        self.assertEqual(safe["phases"][2]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")
        self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_explicit_threshold_missing_witness(self):
        inputs,p=fixture()
        p=replace(p,early=replace(p.early,tod=None,candidate_min_rvol_tod=D(1)))
        _,safe=run(inputs,p,variant=VARIANT)
        self.assertEqual(safe["phases"][2]["ingredient_state"],"MISSING_INPUT")

    def test_late_cumulative_at_re_verification_blocks(self):
        inputs,p=fixture(late=True)
        _,safe=run(inputs,threshold(p,D(1)),variant=VARIANT)
        self.assertEqual(safe["phases"][2]["ingredient_state"],"BLOCKED")

    def test_no_default_wrong_variant_invalid(self):
        inputs,p=fixture()
        row,_=run(inputs,p,variant=VARIANT)
        self.assertIsNone(row.private_preview.assessments[2][1].tod_candidate_match)
        _,safe=run(inputs,threshold(p,D(1)))
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        for k in (D(0),D("-1"),D("NaN"),True,1.3):
            _,safe=run(inputs,threshold(p,k),variant=VARIANT)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_redaction_and_no_authority(self):
        inputs,p=fixture()
        row,safe=run(inputs,threshold(p,D(1)),variant=VARIANT)
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("candidate_min_rvol_tod","tod_candidate_match",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
