"""§395 fictional normalized ATR percentile candidate regressions."""
from dataclasses import replace
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_compression_candidate395 import AtrPercentilePlan395, inspect_atr_percentile_candidate
from swing_trading.market_data import Timeframe
from test_causal_indicators import AS_OF, make_bar, snap


def fixture(last_range=D(2), count=3):
    rows=[snap(make_bar(i,open_price=D(100),close=D(100),high=D(102),low=D(98)))
          for i in range(14+count)]
    rows.append(snap(make_bar(len(rows),open_price=D(100),close=D(100),
                              high=D(100)+last_range/2,low=D(100)-last_range/2)))
    return tuple(rows)


def run(rows=None, plan=AtrPercentilePlan395(3,D("0.2"))):
    return inspect_atr_percentile_candidate(fixture() if rows is None else rows,
                                             plan=plan,as_of_utc=AS_OF)


class Compression395Tests(unittest.TestCase):
    def test_normalized_atr_lower_equal_higher(self):
        for width, expected in ((D(2),True),(D(4),True),(D(10),False)):
            r=run(fixture(width))
            self.assertEqual(r.reference_threshold_percent,D(4))
            self.assertEqual(r.target_atr_percent,((D(52)+width)/D(14))*D(100)/D(100))
            self.assertIs(r.at_or_below,expected)
            self.assertEqual(r.reference_count,3)

    def test_nearest_rank_and_target_excluded(self):
        rows=list(fixture())
        for i,width in ((15,D(18)),(16,D(10))):
            r=rows[i].selected
            rows[i]=snap(replace(r,high=D(100)+width/2,low=D(100)-width/2))
        low=run(tuple(rows),AtrPercentilePlan395(3,D("0.2")))
        high=run(tuple(rows),AtrPercentilePlan395(3,D(1)))
        self.assertEqual(low.reference_threshold_percent,D(4))
        self.assertGreater(high.reference_threshold_percent,low.reference_threshold_percent)
        self.assertGreater(high.reference_threshold_percent,high.target_atr_percent)

    def test_late_prior_revision_blocks(self):
        rows=list(fixture())
        rows[-2]=snap(replace(rows[-2].selected,verified_at_utc=rows[-1].selected.bar_end_utc))
        r=run(tuple(rows))
        self.assertEqual(r.reason,"REFERENCE_BAR_NOT_QUALIFIED_AT_CUTOFF")
        self.assertIsNone(r.target_atr_percent)

    def test_wrong_tf_missing_duplicate_and_source(self):
        rows=fixture()
        mixed=snap(make_bar(17,timeframe=Timeframe.H1,start=rows[-1].market_bar_key.bar_start_utc))
        for data in (rows[:-1],list(rows),rows[:-1]+(mixed,),
                     rows[:3]+(rows[2],)+rows[4:]):
            r=run(data)
            self.assertIsNone(r.at_or_below)
            self.assertIsNone(r.reference_threshold_percent)

    def test_zero_atr_and_explicit_parameters(self):
        rows=tuple(snap(make_bar(i,open_price=D(100),close=D(100),high=D(100),low=D(100))) for i in range(18))
        self.assertEqual(run(rows).reason,"NORMALIZED_ATR_UNAVAILABLE")
        for plan in (AtrPercentilePlan395(True,D("0.2")),AtrPercentilePlan395(1,D("0.2")),
                     AtrPercentilePlan395(3,D(0)),AtrPercentilePlan395(3,D("NaN"))):
            with self.assertRaises(ValueError):
                run(plan=plan)

    def test_redacted_and_never_approved(self):
        safe=run().safe_summary()
        self.assertTrue(safe["at_or_below"])
        for key in ("compression_verified","parameter_approved","source_qualified","action_eligible"):
            self.assertFalse(safe[key])
        for secret in ("target_atr_percent","reference_threshold_percent","quantile","reference_count"):
            self.assertNotIn(secret,json.dumps(safe))
