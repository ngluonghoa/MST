"""§384 fictional D1 anchor/retest geometry, not an approved detector."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.causal_range_candidate384 import inspect_d1_range_candidate
from swing_trading.market_data import Timeframe
from swing_trading.source_quality import QualityState
from test_causal_indicators import AS_OF, make_bar, snap


def fixture(*, upper="110", lower="90"):
    start = AS_OF - timedelta(days=100)
    rows = []
    for i in range(35):
        h = D("110") if i == 17 else D(upper) if i == 25 else D("102")
        l = D("90") if i == 19 else D(lower) if i == 27 else D("98")
        rows.append(snap(make_bar(i, start=start+timedelta(days=i), high=h, low=l,
                                 open_price=D("100"), close=D("100"))))
    return tuple(rows)


def inspect(rows=None, **changes):
    plan = dict(high_indices=(17,25), low_indices=(19,27), left_count=1, right_count=1,
                tie_policy=TiePolicy.STRICT_V1, atr_stop=15,
                candidate_k_touch=D("0.25"), candidate_k_min_width=D("2"), as_of_utc=AS_OF)
    plan.update(changes)
    return inspect_d1_range_candidate(fixture() if rows is None else rows, **plan)


class RangeCandidate384Tests(unittest.TestCase):
    def test_same_reference_and_causal_atr_with_two_touches_each(self):
        result = inspect()
        self.assertEqual((result.upper, result.lower, result.atr), (D(110),D(90),D(4)))
        self.assertEqual(result.upper_touch, "NEAR_ONLY")
        self.assertEqual(result.lower_touch, "NEAR_ONLY")
        self.assertEqual(result.width_state, "MEETS_CANDIDATE_MINIMUM")
        self.assertEqual(result.close_state, "SUPPLIED_CLOSES_INSIDE_ONLY")
        self.assertFalse(result.range_verified)
        self.assertFalse(result.action_eligible)

    def test_inclusive_touch_and_width_edges_no_threshold_default(self):
        exact = inspect(fixture(upper="111",lower="89"),candidate_k_min_width=D(5))
        self.assertEqual((exact.upper_touch,exact.lower_touch),("NEAR_ONLY","NEAR_ONLY"))
        self.assertEqual(exact.width_state,"MEETS_CANDIDATE_MINIMUM")
        outside = inspect(fixture(upper="112",lower="88"),candidate_k_min_width=D("5.01"))
        self.assertEqual((outside.upper_touch,outside.lower_touch),("OUTSIDE_TOLERANCE","OUTSIDE_TOLERANCE"))
        self.assertEqual(outside.width_state,"BELOW_CANDIDATE_MINIMUM")

    def test_close_outside_reference_not_silently_range_verified(self):
        rows = list(fixture())
        rows[32] = snap(replace(rows[32].selected, high=D(112),close=D(111)))
        result = inspect(tuple(rows))
        self.assertEqual(result.close_state,"OUTSIDE_REFERENCE_CLOSE_OBSERVED")
        self.assertEqual(result.upper_touch,"NEAR_ONLY")
        self.assertFalse(result.range_verified)

    def test_duplicate_wrong_order_nonextremum_and_missing_right(self):
        for edits in ({"high_indices":(17,17)}, {"low_indices":(19,25)},
                      {"high_indices":(25,17)}):
            self.assertEqual(inspect(**edits).reason,"NON_DISTINCT_OR_UNORDERED_BOUNDARY_TESTS")
        self.assertEqual(inspect(high_indices=(18,25)).reason,"BOUNDARY_TEST_NOT_EXTREMUM")
        self.assertEqual(inspect(low_indices=(19,34)).reason,"PIVOT_INPUT_BLOCKED")

    def test_anchors_and_atr_have_to_be_known_before_retest(self):
        rows = list(fixture())
        late = rows[20].selected
        rows[20] = snap(replace(late, verified_at_utc=rows[25].selected.bar_end_utc))
        self.assertEqual(inspect(tuple(rows)).reason,"ANCHOR_NOT_KNOWN_BEFORE_TEST")
        self.assertEqual(inspect(atr_stop=26).reason,"ATR_PREFIX_NOT_BEFORE_TESTS")
        rows = list(fixture())
        late = rows[14].selected
        rows[14] = snap(replace(late, verified_at_utc=rows[25].selected.bar_end_utc))
        self.assertEqual(inspect(tuple(rows)).reason,"ATR_PREFIX_BLOCKED")

    def test_bad_scope_and_quality_block_and_redacted_output(self):
        rows = fixture()
        bad = snap(replace(rows[10].selected,quality_state=QualityState.UNVERIFIED))
        self.assertEqual(inspect(rows[:10]+(bad,)+rows[11:]).reason,"PIVOT_INPUT_BLOCKED")
        self.assertEqual(inspect(()).reason,"MISSING_OR_INVALID_D1_HISTORY")
        for edits in ({"candidate_k_touch":None},{"candidate_k_min_width":D("NaN")},
                      {"high_indices":(True,25)},{"atr_stop":True}):
            with self.assertRaises(ValueError):
                inspect(**edits)
        safe = inspect().safe_summary()
        for flag in ("range_verified","source_qualified","parameter_approved","action_eligible"):
            self.assertFalse(safe[flag])
        self.assertNotIn("110",json.dumps(safe))
