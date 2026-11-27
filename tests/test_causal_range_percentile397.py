"""§397 normalized D1 candle-range percentile, fictional regressions."""
from dataclasses import replace
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_range_percentile397 import RangePercentilePlan397, inspect_range_percentile_candidate
from swing_trading.market_data import Timeframe
from test_causal_indicators import AS_OF, make_bar, snap
from swing_trading.source_quality import resolve_as_known


def fixture(width=D(2)):
    bars=[]
    for i,(close,spread) in enumerate(((D(100),D(4)),(D(200),D(12)),(D(50),D(1)),(D(100),width))):
        bars.append(snap(make_bar(i,open_price=close,close=close,high=close+spread/2,low=close-spread/2)))
    return tuple(bars)


def run(rows=None, plan=RangePercentilePlan397(3,D("0.5"))):
    return inspect_range_percentile_candidate(fixture() if rows is None else rows,
                                               plan=plan,as_of_utc=AS_OF)


class RangePercentile397Tests(unittest.TestCase):
    def test_own_close_normalization_and_exact_nearest_rank(self):
        for width,expected in ((D(2),True),(D(4),True),(D(5),False)):
            r=run(fixture(width))
            self.assertEqual(r.reference_threshold_percent,D(4))
            self.assertEqual(r.target_range_percent,width)
            self.assertIs(r.at_or_below,expected)
            self.assertEqual(r.reference_count,3)

    def test_target_excluded_and_quantile_explicit(self):
        rows=fixture(D(100))
        for q,threshold in ((D("0.01"),D(2)),(D("0.5"),D(4)),(D(1),D(6))):
            r=run(rows,RangePercentilePlan397(3,q))
            self.assertEqual(r.reference_threshold_percent,threshold)
            self.assertFalse(r.at_or_below)

    def test_late_reference_and_unavailable_target_block(self):
        rows=list(fixture())
        rows[-2]=snap(replace(rows[-2].selected,verified_at_utc=rows[-1].selected.bar_end_utc))
        self.assertEqual(run(tuple(rows)).reason,"REFERENCE_BAR_NOT_QUALIFIED_AT_CUTOFF")
        target=fixture()[-1]
        missing=resolve_as_known(target.market_bar_key,(),AS_OF)
        self.assertIsNone(run(fixture()[:-1]+(missing,)).at_or_below)

    def test_wrong_tf_missing_reordered_or_duplicate_blocks(self):
        rows=fixture()
        mixed=snap(make_bar(3,timeframe=Timeframe.H1,start=rows[-1].market_bar_key.bar_start_utc))
        for data in (rows[:-1],list(rows),rows[:-1]+(mixed,),
                     (rows[1],rows[0],rows[2],rows[3]),(rows[0],rows[0],rows[2],rows[3])):
            r=run(data)
            self.assertIsNone(r.at_or_below)
            self.assertIsNone(r.reference_threshold_percent)

    def test_flat_range_and_invalid_configuration(self):
        self.assertEqual(run(fixture(D(0))).target_range_percent,D(0))
        for p in (RangePercentilePlan397(True,D("0.5")),RangePercentilePlan397(512,D("0.5")),
                  RangePercentilePlan397(3,D(0)),RangePercentilePlan397(3,D("NaN"))):
            with self.assertRaises(ValueError):
                run(plan=p)

    def test_safe_summary_no_authority_or_numeric_values(self):
        safe=run().safe_summary()
        self.assertTrue(safe["at_or_below"])
        for key in ("compression_verified","parameter_approved","source_qualified","action_eligible"):
            self.assertFalse(safe[key])
        for secret in ("target_range_percent","reference_threshold_percent","quantile","reference_count"):
            self.assertNotIn(secret,json.dumps(safe))
