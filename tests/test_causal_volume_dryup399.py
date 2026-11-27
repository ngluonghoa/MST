"""§399 fictional raw matched D1 volume dry-up regressions."""
from dataclasses import replace
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_indicators import VolumeBasis, VolumeBasisWitness
from swing_trading.causal_volume_dryup399 import DryUpPlan399, inspect_d1_volume_dryup
from swing_trading.market_data import Timeframe
from test_causal_indicators import AS_OF, make_bar, snap


def fixture(volumes=(100, 200, 300, 50, 150)):
    return tuple(snap(make_bar(i,volume=v)) for i,v in enumerate(volumes))


def plan(rows):
    return DryUpPlan399(3,2,D("0.5"),"fixture-daily-policy",
        tuple(VolumeBasisWitness(x.selected,VolumeBasis.RAW_MATCHED_SHARES,
            "fixture-regime","fixture-proof-"+str(i),x.selected.verified_at_utc)
            for i,x in enumerate(rows)))


def run(rows=None,p=None):
    rows=fixture() if rows is None else rows
    return inspect_d1_volume_dryup(rows,plan=plan(rows) if p is None else p,as_of_utc=AS_OF)


class VolumeDryUp399Tests(unittest.TestCase):
    def test_exact_means_and_inclusive_threshold(self):
        for vols,ratio,expected in (((100,200,300,50,150),D("0.5"),True),
                                    ((100,200,300,100,300),D(1),False),
                                    ((100,200,300,0,0),D(0),True)):
            r=run(fixture(vols))
            self.assertEqual(r.mean_ratio,ratio)
            self.assertIs(r.at_or_below,expected)

    def test_wrong_basis_row_regime_and_late_reference_witness(self):
        rows=fixture()
        p=plan(rows)
        first=p.witnesses[0]
        for bad in (replace(first,basis=VolumeBasis.ALL_TRADES_SHARES),
                    replace(first,candle=p.witnesses[1].candle),
                    replace(first,share_regime_id="different"),
                    replace(first,verified_at_utc=rows[-1].selected.verified_at_utc)):
            r=run(rows,replace(p,witnesses=(bad,)+p.witnesses[1:]))
            self.assertIsNone(r.mean_ratio)

    def test_reference_late_revision_blocked(self):
        rows=list(fixture())
        rows[2]=snap(replace(rows[2].selected,verified_at_utc=rows[3].selected.bar_end_utc))
        self.assertEqual(run(tuple(rows)).reason,"REFERENCE_BAR_NOT_QUALIFIED_AT_CUTOFF")

    def test_exact_window_order_and_timeframe(self):
        rows=fixture()
        mixed=snap(make_bar(4,timeframe=Timeframe.H1,start=rows[-1].market_bar_key.bar_start_utc))
        for data in (rows[:-1],list(rows),rows[:-1]+(mixed,),rows[:2]+(rows[1],)+rows[3:]):
            self.assertIsNone(run(data,plan(rows)).mean_ratio)

    def test_zero_reference_and_invalid_explicit_plan(self):
        self.assertEqual(run(fixture((0,0,0,50,150))).reason,"ZERO_REFERENCE_VOLUME")
        p=plan(fixture())
        for bad in (replace(p,reference_count=True),replace(p,base_count=1),
                    replace(p,max_ratio=D("NaN")),replace(p,max_ratio=D("1.1")),
                    replace(p,comparison_policy_version=""),replace(p,witnesses=p.witnesses[:-1])):
            with self.assertRaises(ValueError):
                run(p=bad)

    def test_no_numeric_value_or_authority_in_safe_summary(self):
        safe=run().safe_summary()
        self.assertTrue(safe["at_or_below"])
        for flag in ("volume_approved","source_qualified","parameter_approved","action_eligible"):
            self.assertFalse(safe[flag])
        for secret in ("mean_ratio","max_ratio","fixture-proof","fixture-regime"):
            self.assertNotIn(secret,json.dumps(safe))
