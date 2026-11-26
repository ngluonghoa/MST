"""§382 fictional paired D1 structure and signed SMA candidate."""
from dataclasses import replace
from decimal import Decimal as D
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.causal_trend_candidate382 import inspect_d1_paired_trend_candidate
from swing_trading.source_quality import QualityState
from test_causal_sma50_381 import history
from test_causal_indicators import AS_OF, snap


def fixture(direction=1, flat=False):
    rows = list(history(direction))
    for i, price in ((10, 180), (20, 30), (30, 200), (40, 50)):
        if direction < 0:
            price = 230 - price
        if flat and i in (30, 40):
            price = 180 if i == 30 else 30
        row = rows[i].selected
        # A wide high/low envelope sets only the chosen extremum, not the close.
        if (i in (10,30)) == (direction >= 0):
            row = replace(row, high=D(price))
        else:
            row = replace(row, low=D(price))
        rows[i] = snap(row)
    return tuple(rows)


def inspect(rows, **overrides):
    plan = dict(high_indices=(10,30), low_indices=(20,40), left_count=1,
                right_count=1, tie_policy=TiePolicy.STRICT_V1, lookback=10,
                as_of_utc=AS_OF)
    plan.update(overrides)
    return inspect_d1_paired_trend_candidate(rows, **plan)


class PairedTrend382Tests(unittest.TestCase):
    def test_aligned_up_and_down_are_descriptive(self):
        up = inspect(fixture())
        down = inspect(fixture(-1), high_indices=(20,40), low_indices=(10,30))
        self.assertEqual((up["structure"], up["sma50_delta_direction"], up["relation"]),
                         ("HH_HL_GEOMETRY", "RISING", "ALIGNED_GEOMETRY_ONLY"))
        self.assertEqual((down["structure"], down["sma50_delta_direction"], down["relation"]),
                         ("LH_LL_GEOMETRY", "FALLING", "ALIGNED_GEOMETRY_ONLY"))
        for result in (up, down):
            for flag in ("trend_verified", "parameter_approved", "source_qualified", "action_eligible"):
                self.assertIs(result[flag], False)

    def test_missing_and_disordered_pairs_are_distinct(self):
        rows = fixture()
        self.assertEqual(inspect(rows, high_indices=())["structure"], "MISSING_PAIR")
        self.assertEqual(inspect(rows, high_indices=(30,10))["structure"], "INCONSISTENT_ORDER")
        self.assertEqual(inspect(rows, low_indices=(10,40))["structure"], "INCONSISTENT_ORDER")

    def test_not_extremum_and_missing_right_witness(self):
        rows = fixture()
        self.assertEqual(inspect(rows, high_indices=(11,30))["structure"], "NON_EXTREMUM")
        self.assertEqual(inspect(rows, low_indices=(20,59))["structure"], "BLOCKED_PIVOT")

    def test_flat_pairs_never_sideways(self):
        result = inspect(fixture(flat=True))
        self.assertEqual(result["structure"], "FLAT_PAIRS")
        self.assertEqual(result["relation"], "INSUFFICIENT_DIRECTIONAL_GEOMETRY")

    def test_conflicting_and_flat_sma_do_not_confirm_trend(self):
        for direction, expected in ((-1,"DIRECTION_CONFLICT"), (0,"SLOPE_FLAT")):
            rows = list(history(direction))
            geometry = fixture()
            for i in (10,20,30,40):
                r = rows[i].selected
                g = geometry[i].selected
                rows[i] = snap(replace(r, high=max(r.high,g.high), low=min(r.low,g.low)))
            result = inspect(tuple(rows))
            self.assertEqual(result["structure"], "HH_HL_GEOMETRY")
            self.assertEqual(result["relation"], expected)

    def test_same_input_rejects_bad_quality_and_wrong_history(self):
        rows = fixture()
        bad = snap(replace(rows[5].selected, quality_state=QualityState.UNVERIFIED))
        for series in (rows[:5]+(bad,)+rows[6:], rows[:-1], list(rows)):
            self.assertEqual(inspect(series)["relation"], "BLOCKED_INPUT")
        for plan in ({"high_indices":(True,30)}, {"low_indices":(20,)},
                     {"tie_policy":"STRICT_V1"}, {"lookback":True}):
            with self.assertRaises(ValueError):
                inspect(rows, **plan)
