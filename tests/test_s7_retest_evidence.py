"""Fictional source-contract tests, never market/source qualification."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import unittest

from swing_trading.contracts import DecisionStatus, Strategy
from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.market_data import Timeframe
from swing_trading.s7_retest_evidence import inspect_s7_retest_evidence
from test_causal_indicators import AS_OF, START, make_bar, snap, d1


def inputs():
    hist = tuple(snap(make_bar(i+25, low=D(low), close=D(close),
                               open_price=D(close)))
                 for i,(low,close) in enumerate(
                     [("7","9"),("6","9"),("3","5"),("5","8"),
                      ("4","4"),("1","1")]))
    start = START+timedelta(days=31)
    prior = snap(make_bar(100,timeframe=Timeframe.M15,start=start,
                          open_price=D("2"),low=D("1"),close=D("2")))
    retest = snap(make_bar(101,timeframe=Timeframe.M15,
                           start=start+timedelta(minutes=30),
                           open_price=D("2"),low=D("2"),close=D("3")))
    return dict(pivot_history=hist[:4],pivot_index=2,left_count=1,right_count=1,
                tie_policy=TiePolicy.STRICT_V1,previous=hist[4],breakdown=hist[5],
                prior_retest=prior,retest=retest,atr_d1_history=d1(),
                retest_atr_d1_history=d1(),candidate_epsilon=D(".25"),
                strategy=Strategy.SHORT,as_of_utc=AS_OF)


class S7RetestEvidenceTests(unittest.TestCase):
    def test_exact_pivot_and_origin_remain_unverified(self):
        p = inputs()
        r = inspect_s7_retest_evidence(**p)
        self.assertEqual(r.reason,"EXACT_PIVOT_GEOMETRY_UNCALIBRATED")
        self.assertEqual(r.close_distance_atr,D("0"))
        self.assertEqual(r.range_distance_atr,D("0"))
        self.assertIs(r.status,DecisionStatus.UNVERIFIED)
        self.assertFalse(r.action_eligible)
        self.assertEqual(r,inspect_s7_retest_evidence(**p))
        p["strategy"]=Strategy.SWING
        self.assertEqual(r.origin_preview_id,inspect_s7_retest_evidence(**p).origin_preview_id)

    def test_no_prior_breakdown_no_geometry(self):
        p = inputs()
        p["breakdown"]=snap(replace(p["breakdown"].selected,close=D("3")))
        r=inspect_s7_retest_evidence(**p)
        self.assertEqual(r.reason,"NO_CAUSAL_LOW_PIVOT_CROSS")
        self.assertIsNone(r.origin_preview_id)

    def test_approach_from_above_rejected(self):
        p=inputs()
        p["prior_retest"]=snap(replace(p["prior_retest"].selected,close=D("4")))
        self.assertEqual(inspect_s7_retest_evidence(**p).reason,"NO_APPROACH_FROM_BELOW")

    def test_missing_atr_and_missing_epsilon(self):
        p=inputs()
        self.assertEqual(inspect_s7_retest_evidence(**dict(p,retest_atr_d1_history=())).reason,
                         "RETEST_ATR_UNAVAILABLE")
        self.assertEqual(inspect_s7_retest_evidence(**dict(p,candidate_epsilon=None)).reason,
                         "NO_CAUSAL_LOW_PIVOT_CROSS")

    def test_future_retest_blocked(self):
        p=inputs()
        p["as_of_utc"]=p["retest"].selected.bar_end_utc
        self.assertEqual(inspect_s7_retest_evidence(**p).reason,"SOURCE_OR_ASOF_UNVERIFIED")

    def test_distinct_observation_changes_evidence_not_origin(self):
        p=inputs()
        a=inspect_s7_retest_evidence(**p)
        p["retest"]=snap(replace(p["retest"].selected,close=D("4")))
        b=inspect_s7_retest_evidence(**p)
        self.assertEqual(a.origin_preview_id,b.origin_preview_id)
        self.assertNotEqual(a.retest_preview_id,b.retest_preview_id)
        self.assertTrue(b.close_above_pivot)
        self.assertEqual(b.close_distance_atr,D(".25"))

    def test_authority_forgery_rejected(self):
        r=inspect_s7_retest_evidence(**inputs())
        for key in ("action_eligible","parameter_approved","detector_approved"):
            for value in (True,0,None):
                with self.assertRaises(ValueError):
                    replace(r,**{key:value})

if __name__ == "__main__":
    unittest.main()
