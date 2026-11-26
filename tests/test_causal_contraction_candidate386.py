"""§386 causal swing contractions on fictional D1 histories."""
from dataclasses import replace
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_contraction_candidate386 import ContractionPlan386, inspect_d1_contraction_candidate
from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.market_data import Timeframe
from swing_trading.source_quality import QualityState
from test_causal_indicators import AS_OF, make_bar, snap


def fixture(pairs=((120,80),(115,90),(110,95)), *, timeframe=Timeframe.D1):
    highs={3+8*i:D(h) for i,(h,l) in enumerate(pairs)}
    lows={7+8*i:D(l) for i,(h,l) in enumerate(pairs)}
    return tuple(snap(make_bar(i,timeframe=timeframe,open_price=D(100),close=D(100),
                          high=highs.get(i,D(102)),low=lows.get(i,D(98))))
                 for i in range(8*len(pairs)+2))


def plan(count=3):
    return ContractionPlan386(tuple((3+8*i,7+8*i) for i in range(count)),1,1,TiePolicy.STRICT_V1)


def inspect(rows=None, config=None):
    return inspect_d1_contraction_candidate(fixture() if rows is None else rows,
                               plan=plan() if config is None else config,as_of_utc=AS_OF)


class Contraction386Tests(unittest.TestCase):
    def test_three_swings_two_normalized_contractions(self):
        result=inspect()
        self.assertEqual(result.depths,(D(40)/D(120),D(25)/D(115),D(15)/D(110)))
        self.assertEqual(result.relations,("NARROWER","NARROWER"))
        self.assertEqual(result.low_relations,("HIGHER","HIGHER"))
        self.assertEqual(result.trailing_contractions,2)
        self.assertFalse(result.compression_verified)
        self.assertFalse(result.action_eligible)

    def test_interrupted_chain_and_exact_equal_depth(self):
        equal=inspect(fixture(((120,90),(128,96),(112,84))))
        self.assertEqual(equal.relations,("EQUAL","EQUAL"))
        self.assertEqual(equal.trailing_contractions,0)
        interrupted=inspect(fixture(((120,80),(115,90),(125,80),(110,95))),plan(4))
        self.assertEqual(interrupted.relations,("NARROWER","WIDER","NARROWER"))
        self.assertEqual(interrupted.trailing_contractions,1)

    def test_insufficient_duplicate_reversed_and_wrong_tf(self):
        self.assertEqual(inspect(config=plan(2)).reason,"INSUFFICIENT_SWINGS_FOR_TWO_COMPARISONS")
        for pairs in (((3,7),(7,15),(19,23)),((7,3),(11,15),(19,23))):
            self.assertEqual(inspect(config=replace(plan(),swings=pairs)).reason,
                             "DUPLICATE_OR_UNORDERED_SWINGS")
        self.assertEqual(inspect(fixture(timeframe=Timeframe.H1)).reason,"MISSING_OR_INVALID_D1_HISTORY")

    def test_local_extremum_and_missing_right_bar(self):
        self.assertEqual(inspect(config=replace(plan(),swings=((4,7),(11,15),(19,23)))).reason,
                         "SWING_NOT_LOCAL_EXTREMUM")
        self.assertEqual(inspect(fixture()[:24]).reason,"PIVOT_INPUT_BLOCKED")

    def test_late_knowledge_and_bad_quality_rejected(self):
        rows=list(fixture())
        rows[4]=snap(replace(rows[4].selected,verified_at_utc=rows[7].selected.bar_end_utc))
        self.assertEqual(inspect(tuple(rows)).reason,"EARLIER_EXTREMUM_NOT_KNOWN_BEFORE_NEXT")
        rows=list(fixture())
        rows[1]=snap(replace(rows[1].selected,quality_state=QualityState.UNVERIFIED))
        self.assertEqual(inspect(tuple(rows)).reason,"PIVOT_INPUT_BLOCKED")

    def test_explicit_plan_and_redaction(self):
        for config in (replace(plan(),swings=((True,7),(11,15),(19,23))),
                       replace(plan(),tie_policy="STRICT_V1"),replace(plan(),right_count=0)):
            with self.assertRaises(ValueError):
                inspect(config=config)
        safe=inspect().safe_summary()
        self.assertTrue(safe["two_observed_contractions"])
        self.assertNotIn("depths",safe)
        self.assertNotIn("120",json.dumps(safe))
        for flag in ("compression_verified","source_qualified","parameter_approved","action_eligible"):
            self.assertFalse(safe[flag])
