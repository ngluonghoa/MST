"""§392 explicit cross-TF geometry regressions, fictional only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import unittest

from swing_trading.causal_cross_tf_candidate392 import inspect_h1_cross_of_d1_upper_pivot
from swing_trading.causal_structure_geometry import GeometryState, TiePolicy, StructureSide, inspect_closed_bos_geometry
from swing_trading.market_data import Timeframe
from swing_trading.source_quality import ObservationOrigin
from test_causal_contraction_candidate386 import fixture
from test_causal_indicators import AS_OF, make_bar, snap


def h1_pair(*, price=D(113), prior=D(109), early=False, mixed=False):
    d1=fixture()
    start=d1[-2 if early else -1].market_bar_key.bar_start_utc
    start+=timedelta(hours=1) if early else timedelta(days=1,hours=8)
    rows=[]
    for i,p in enumerate((prior,price)):
        row=make_bar(100+i,timeframe=Timeframe.H1,start=start+timedelta(hours=2*i),
                     open_price=p,close=p,high=max(p,D(114)),low=min(p,D(108)))
        obs=replace(row.observation_key,source_stream_id="fixture-h1-stream",
                    origin=ObservationOrigin.IMPORT if mixed else row.observation_key.origin)
        rows.append(snap(replace(row,observation_key=obs,
                   observation_revision=replace(row.observation_revision,observation_key=obs))))
    return tuple(rows)


def inspect(pair=None, rows=None, **kwargs):
    history=fixture() if rows is None else rows
    previous,target=h1_pair() if pair is None else pair
    config=dict(pivot_index=19,left_count=1,right_count=1,previous=previous,
                breakout=target,atr_d1_history=fixture()[:15],tie_policy=TiePolicy.STRICT_V1,
                candidate_epsilon=D("0.05"),as_of_utc=AS_OF)
    config.update(kwargs)
    return inspect_h1_cross_of_d1_upper_pivot(history,**config)


class CrossTF392Tests(unittest.TestCase):
    def test_exact_d1_upper_h1_closed_cross_no_approval(self):
        r=inspect()
        self.assertIs(r.state,GeometryState.DESCRIPTIVE_ONLY)
        self.assertTrue(r.candidate_cross)
        self.assertEqual(r.reason,"D1_UPPER_PIVOT_H1_CLOSED_CROSS_ONLY")
        self.assertGreater(r.boundary,D(110))
        for flag in ("action_eligible","parameter_approved","detector_approved","source_independently_attested"):
            self.assertFalse(getattr(r,flag))

    def test_wick_or_already_above_is_not_new_cross(self):
        for pair in (h1_pair(price=D(110)),h1_pair(prior=D(113))):
            r=inspect(pair)
            self.assertIs(r.state,GeometryState.DESCRIPTIVE_ONLY)
            self.assertFalse(r.candidate_cross)

    def test_prior_and_d1_pivot_context_must_be_known(self):
        self.assertIs(inspect(h1_pair(early=True)).state,GeometryState.BLOCKED)
        a,b=h1_pair()
        late=snap(replace(a.selected,verified_at_utc=b.selected.bar_end_utc))
        self.assertEqual(inspect((late,b)).reason,"H1_PREVIOUS_NOT_KNOWN_BEFORE_TARGET")
        self.assertIs(inspect(rows=fixture()[:20]).state,GeometryState.BLOCKED)

    def test_wrong_tf_or_cross_tf_origin_rejected(self):
        r=inspect(h1_pair(mixed=True))
        self.assertEqual(r.reason,"D1_PIVOT_H1_SOURCE_BASIS_MISMATCH")
        self.assertEqual(inspect(pair=fixture()[-2:]).reason,"H1_TARGET_NOT_CLOSED_OR_KNOWN")
        self.assertEqual(inspect(rows=h1_pair()).reason,"D1_PIVOT_HISTORY_MISSING_OR_WRONG_TF")

    def test_atr_unavailable_or_invalid_and_explicit_epsilon(self):
        self.assertTrue(inspect(atr_d1_history=()).reason.startswith("ATR14_"))
        for eps in (None,True,D("-1"),D("NaN")):
            with self.assertRaises(ValueError):
                inspect(candidate_epsilon=eps)

    def test_generic_bos_same_tf_guard_unchanged(self):
        a,b=h1_pair()
        generic=inspect_closed_bos_geometry(fixture(),pivot_index=19,left_count=1,right_count=1,
            previous=a,breakout=b,atr_d1_history=fixture()[:15],side=StructureSide.HIGH,
            tie_policy=TiePolicy.STRICT_V1,candidate_epsilon=D("0.05"),as_of_utc=AS_OF)
        self.assertIs(generic.state,GeometryState.BLOCKED)
        self.assertTrue(inspect((a,b)).candidate_cross)
