"""§402 compression upper pivot, fictional inputs only."""
from dataclasses import replace
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_compression_pivot402 import CompressionPivotPlan402
from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.b6_baseline_preview387 import B6CompressionPlan396, B6State387
from swing_trading.causal_range_percentile397 import RangePercentilePlan397
from swing_trading.contracts import Strategy
from test_b6_compression_rc396 import model, run
from test_b6_rc_dryup400 import witnesses, rc
from test_causal_indicators import make_bar, snap


def fixture(*, higher=False, tie=False, late=False):
    highs=(105,110,110 if tie else 104,115 if higher else 103,101)
    rows=tuple(snap(make_bar(i,open_price=D(100),close=D(100),high=D(h),
                       low=D(99),volume=200 if i<2 else 50)) for i,h in enumerate(highs))
    if late:
        rows=rows[:-1]+(snap(replace(rows[-1].selected,verified_at_utc=__import__('test_causal_indicators').AS_OF + __import__('datetime').timedelta(days=1))),)
    return rows


def plan(*, candidate=1,tie_policy=TiePolicy.STRICT_V1):
    return B6CompressionPlan396(4,RangePercentilePlan397(3,D("0.5")),
        upper_pivot=CompressionPivotPlan402(5,candidate,1,1,tie_policy))


class UpperPivot402Tests(unittest.TestCase):
    def test_both_strategies_exact_upper_pivot(self):
        for strategy in Strategy:
            row,safe=run(model(fixture()),plan(),strategy=strategy)
            self.assertIs(rc(row).state,B6State387.MATCH)
            self.assertTrue(rc(row).upper_pivot.upper_boundary)
            self.assertEqual(rc(row).upper_pivot.pivot.pivot_price,D(110))
            self.assertEqual(safe["phases"][2]["ingredient_state"],"NOT_REQUESTED")
            self.assertEqual(safe["phases"][3]["ingredient_state"],"NOT_REQUESTED")

    def test_higher_base_high_and_nonlocal_extremum(self):
        for rows,p in ((fixture(higher=True),plan()),(fixture(),plan(candidate=2))):
            row,_=run(model(rows),p)
            self.assertFalse(rc(row).upper_pivot.upper_boundary)
            self.assertIs(rc(row).state,B6State387.MATCH)

    def test_explicit_tie_policy(self):
        for policy,expected in ((TiePolicy.STRICT_V1,False),(TiePolicy.ALLOW_EQUAL_V1,True)):
            row,_=run(model(fixture(tie=True)),plan(tie_policy=policy))
            self.assertIs(rc(row).upper_pivot.upper_boundary,expected)

    def test_missing_right_and_late_base_block(self):
        row,_=run(model(fixture()),plan(candidate=4))
        self.assertIsNone(rc(row).upper_pivot.upper_boundary)
        self.assertIn("INSUFFICIENT",rc(row).upper_pivot.reason)
        row,_=run(model(fixture()[:-1]),plan())
        self.assertEqual(rc(row).upper_pivot.reason,"EXACT_COMPRESSION_BASE_MISSING")
        row,_=run(model(fixture(late=True)),plan())
        self.assertIsNone(rc(row).upper_pivot.upper_boundary)

    def test_dryup_base_mismatch_and_config_rejected(self):
        rows=fixture()
        p=plan()
        for bad in (replace(p,upper_pivot=replace(p.upper_pivot,candidate_index=True)),
                    replace(p,dryup=witnesses(rows,2,3))):
            _,safe=run(model(rows),bad)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_no_plan_and_redaction(self):
        row,_=run(model(fixture()),replace(plan(),upper_pivot=None))
        self.assertIsNone(rc(row).upper_pivot)
        row,safe=run(model(fixture()),plan())
        self.assertFalse(rc(row).upper_pivot.safe_summary()["pivot_approved"])
        self.assertFalse(row.private_preview.action_eligible)
        for secret in ("pivot_price","candidate_index","110","upper_pivot"):
            self.assertNotIn(secret,json.dumps(safe))
