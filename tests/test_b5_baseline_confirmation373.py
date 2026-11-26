"""§373 fictional bound B5 confirmation and raw-share RVOL checks."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import unittest

from swing_trading.b5_formula_geometry import (
    B5RFPlan373, B5RFVolumePlan373, B5RFState373, inspect_b5_baseline_confirmation,
)
from swing_trading.causal_indicators import IndicatorState, VolumeBasis, VolumeBasisWitness, VolumeSessionClass
from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import DecisionStatus, Strategy
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import BaselineResolvedInputs
from test_b5_baseline_retest372 import setup, RECLAIM, FAILED
from test_causal_indicators import make_bar, snap
from test_causal_structure_geometry import PIVOT0

TIE = TiePolicy.STRICT_V1


def fixture(variant=RECLAIM, *, support_start=None, close=D("18")):
    original, plan = setup(Timeframe.D1, variant)
    start = PIVOT0 + timedelta(days=7)
    support = snap(make_bar(1001, timeframe=Timeframe.D1, start=support_start or start,
                            open_price=D("16"), high=D("19"), low=D("15"), close=D("17"),
                            volume=200))
    d1 = original.snapshots_for(Timeframe.D1) + (support,)
    items = (("12","8","10"), ("13","8","11"), ("16","8","14"),
             ("14","8","12"), ("16","8","16"), ("20","8",str(close)))
    micro = tuple(snap(make_bar(1100+i, timeframe=Timeframe.M15,
                         start=start+timedelta(hours=7, minutes=i*30),
                         open_price=D("10"), high=D(h), low=D(l), close=D(c)))
                  for i, (h,l,c) in enumerate(items))
    m15 = original.snapshots_for(Timeframe.M15) + micro
    inputs = BaselineResolvedInputs(original.instrument_id, original.exchange,
        original.as_of_utc, False, tuple(
            (tf, d1 if tf is Timeframe.D1 else m15 if tf is Timeframe.M15 else rows)
            for tf, rows in original.buckets))
    offset = plan.retest_index + 1
    rf = B5RFPlan373(Timeframe.D1, len(d1)-1, offset+2, offset+5,
                     1, 1, TIE, D("0.25"))
    return inputs, plan, rf


def witnesses(inputs, rf):
    rows = inputs.snapshots_for(rf.support_tf)[rf.support_index-20:rf.support_index+1]
    return B5RFVolumePlan373((VolumeSessionClass.DAILY,)*21, "fictional-policy",
        tuple(VolumeBasisWitness(s.selected, VolumeBasis.RAW_MATCHED_SHARES,
            "fictional-regime", "fixture-volume-"+str(i), s.selected.verified_at_utc)
              for i,s in enumerate(rows)))


def run(variant=RECLAIM, *, data=None, volume=None, strategy=Strategy.SHORT):
    inputs, plan, rf = fixture(variant) if data is None else data
    return inspect_b5_baseline_confirmation(inputs, strategy=strategy, variant_id=variant,
        retest_plan=plan, rf_plan=rf, volume_plan=volume)


class B5RF373Tests(unittest.TestCase):
    def test_all_four_bound_phases_both_variants_and_strategies(self):
        for variant in (RECLAIM, FAILED):
            for strategy in Strategy:
                r = run(variant, strategy=strategy)
                self.assertEqual(r.state, B5RFState373.RAW_CONFIRMATION_UNCALIBRATED)
                self.assertEqual(r.metrics.support_close_minus_former_pivot_atr, D("0.25"))
                self.assertEqual(r.metrics.micro_high_price, D("16"))
                self.assertEqual(r.metrics.micro_break_close_minus_micro_high_atr, D("0.5"))
                self.assertEqual(r.routed_rf.phase, "R_F")
                self.assertEqual(r.routed_rf.selected_frame, Timeframe.D1)
                self.assertEqual(r.status, DecisionStatus.UNVERIFIED)
                self.assertFalse(r.action_eligible)
                self.assertFalse(r.risk_policy_verified)
                self.assertIsNone(r.rvol)
                self.assertEqual(r.volume_reason, "RAW_MATCHED_VOLUME_WITNESS_MISSING")

    def test_exact_bound_raw_share_witness_rvol_only(self):
        data = fixture()
        plan = witnesses(data[0], data[2])
        r = run(data=data, volume=plan)
        self.assertEqual(r.rvol.value, D("2"))
        self.assertEqual(r.rvol.state, IndicatorState.COMPUTED_UNCALIBRATED)
        self.assertFalse(r.rvol.data_certified)
        self.assertFalse(r.rvol.actionable)
        self.assertFalse(r.action_eligible)

    def test_adjusted_or_wrong_row_witness_never_promoted(self):
        data = fixture()
        plan = witnesses(data[0], data[2])
        last = plan.witnesses[-1]
        for changed in (replace(last, basis=VolumeBasis.ADJUSTED_SHARES),
                        replace(last, candle=plan.witnesses[-2].candle)):
            r = run(data=data, volume=replace(plan, witnesses=plan.witnesses[:-1]+(changed,)))
            self.assertEqual(r.rvol.state, IndicatorState.BLOCKED)
            self.assertIsNone(r.rvol.value)
            self.assertFalse(r.action_eligible)

    def test_support_must_start_after_retest_verification(self):
        r = run(data=fixture(support_start=PIVOT0+timedelta(days=6)))
        self.assertEqual(r.reason, "RF_SUPPORT_STARTED_BEFORE_RETEST_VERIFIED")
        self.assertIsNone(r.metrics)

    def test_no_micro_cross_not_negative_signal(self):
        r = run(data=fixture(close=D("16")))
        self.assertEqual(r.state, B5RFState373.NONCROSS_GEOMETRY_ONLY)
        self.assertEqual(r.status, DecisionStatus.UNVERIFIED)
        self.assertIsNone(r.metrics)

    def test_base_pending_or_unknown_rf_parameter_blocks(self):
        inputs, base, rf = fixture()
        r = run(data=(inputs, replace(base, candidate_epsilon=None), rf))
        self.assertTrue(r.reason.startswith("BASE_"))
        r = run(data=(inputs, base, replace(rf, candidate_epsilon=None)))
        self.assertTrue(r.reason.startswith("RF_MICRO_"))
        self.assertIsNone(r.metrics)

    def test_wrong_frame_indices_and_malformed_witness_plan_denied(self):
        inputs, base, rf = fixture()
        for bad in (replace(rf, support_tf=Timeframe.H4),
                    replace(rf, support_index=999),
                    replace(rf, micro_pivot_index=base.retest_index-1),
                    replace(rf, micro_break_index=True)):
            with self.assertRaises(ValueError):
                run(data=(inputs, base, bad))
        p = witnesses(inputs, rf)
        with self.assertRaises(ValueError):
            run(data=(inputs, base, rf), volume=replace(p, witnesses=p.witnesses[:-1]))
