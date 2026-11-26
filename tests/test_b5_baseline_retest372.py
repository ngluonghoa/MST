"""B5 strict baseline-bound retrospective geometry, fictional only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import unittest

from swing_trading.b5_formula_geometry import (
    B5RetestPlan372, B5RetestState372, inspect_b5_baseline_retest,
)
from swing_trading.causal_structure_geometry import StructureSide, TiePolicy
from swing_trading.contracts import DecisionStatus, Strategy
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import BASELINE_CORE_TF, BaselineResolvedInputs
from swing_trading.source_quality import ResolvedBarSnapshotV12
from test_causal_indicators import make_bar, snap
from test_causal_structure_geometry import AS_OF, PIVOT0, atr_d1
from test_structural_phase_evidence213 import bars_for

RECLAIM = "B5/E_RECLAIM"
FAILED = "B5/E_FAILED_BREAK"


def setup(tf=Timeframe.H1, variant=RECLAIM, *, higher=None, m15=None):
    history = bars_for(StructureSide.HIGH, tf) if higher is None else higher
    atr = atr_d1()
    retest_start = PIVOT0 + timedelta(days=6)
    if m15 is None:
        retest = snap(make_bar(701, timeframe=Timeframe.M15, start=retest_start,
                              open_price=D("16"), high=D("18"), low=D("15.5"), close=D("16.5")))
        failed = snap(make_bar(700, timeframe=Timeframe.M15,
                              start=retest_start-timedelta(hours=1),
                              open_price=D("16"), high=D("17"), low=D("14"), close=D("15")))
        m15 = (failed, retest) if variant == FAILED else (retest,)
    d1 = atr + history if tf is Timeframe.D1 else atr
    first = atr[0].market_bar_key
    lookup = {Timeframe.D1: d1, Timeframe.M15: m15}
    if tf is Timeframe.H1:
        lookup[Timeframe.H1] = history
    inputs = BaselineResolvedInputs(first.instrument_id, first.exchange, AS_OF, False,
                                     tuple((f, lookup.get(f, ())) for f in BASELINE_CORE_TF))
    offset = 15 if tf is Timeframe.D1 else 0
    plan = B5RetestPlan372(tf, offset+5, offset+2, 1, 1, 0, 15,
                           1 if variant == FAILED else 0,
                           0 if variant == FAILED else None, TiePolicy.STRICT_V1, D("0.25"))
    return inputs, plan


def run(tf=Timeframe.H1, variant=RECLAIM, *, inputs=None, plan=None, strategy=Strategy.SHORT):
    a, b = setup(tf, variant)
    return inspect_b5_baseline_retest(
        a if inputs is None else inputs, strategy=strategy, variant_id=variant,
        plan=b if plan is None else plan)


class B5BaselineRetest372Tests(unittest.TestCase):
    def test_both_variants_frames_strategies_compute_raw_math_only(self):
        for tf in (Timeframe.D1, Timeframe.H1):
            for variant in (RECLAIM, FAILED):
                for strategy in Strategy:
                    with self.subTest(tf=tf, variant=variant, strategy=strategy):
                        r = run(tf, variant, strategy=strategy)
                        self.assertEqual(r.state, B5RetestState372.RAW_RETEST_UNCALIBRATED)
                        self.assertEqual(r.metrics.pivot_price, D("16"))
                        self.assertEqual(r.metrics.retest_low_minus_pivot_atr, D("-0.125"))
                        self.assertEqual(r.metrics.retest_close_minus_pivot_atr, D("0.125"))
                        self.assertEqual(r.metrics.failed_break_close_minus_pivot_atr,
                                         D("-0.25") if variant == FAILED else None)
                        self.assertEqual(r.status, DecisionStatus.UNVERIFIED)
                        self.assertFalse(r.actionable)
                        self.assertFalse(r.rf_evaluated)
                        self.assertEqual([x.phase for x in r.routed_phases], ["R0", "R_C", "R_E"])
                        self.assertEqual(r.routed_phases[0].selected_frame, tf)

    def test_breakout_retrieved_but_verified_after_retest_start_blocks(self):
        bars = bars_for(StructureSide.HIGH, Timeframe.H1)
        late = replace(bars[-1].selected, verified_at_utc=PIVOT0+timedelta(days=6, minutes=1))
        inputs, plan = setup(higher=bars[:-1]+(snap(late),))
        r = run(inputs=inputs, plan=plan)
        self.assertEqual(r.reason, "BREAKOUT_NOT_VERIFIED_BEFORE_RETEST")
        self.assertIsNone(r.metrics)

    def test_failed_branch_requires_closed_below_and_known_before_retest(self):
        inputs, plan = setup(variant=FAILED)
        failed, target = inputs.snapshots_for(Timeframe.M15)
        for changed, reason in (
            (replace(failed.selected, close=D("16")), "FAILED_BREAK_GEOMETRY_NOT_BELOW_PIVOT"),
            (replace(failed.selected, verified_at_utc=target.market_bar_key.bar_start_utc+timedelta(minutes=1)),
             "FAILED_BREAK_NOT_CAUSALLY_BETWEEN_BREAKOUT_AND_RETEST"),
        ):
            m, p = setup(variant=FAILED, m15=(snap(changed), target))
            r = run(variant=FAILED, inputs=m, plan=p)
            self.assertEqual(r.reason, reason)
            self.assertIsNone(r.metrics)

    def test_conflict_in_target_or_breakout_blocks_without_fallback(self):
        inputs, plan = setup()
        target = inputs.snapshots_for(Timeframe.M15)[0]
        conflict = ResolvedBarSnapshotV12(target.market_bar_key, None, 2, "SOURCE_OR_REVISION_CONFLICT")
        m, p = setup(m15=(conflict,))
        self.assertEqual(run(inputs=m, plan=p).reason, "RETEST_NOT_CLOSED_OR_KNOWN")
        bars = inputs.snapshots_for(Timeframe.H1)
        bad = ResolvedBarSnapshotV12(bars[-1].market_bar_key, None, 2, "SOURCE_OR_REVISION_CONFLICT")
        m, p = setup(higher=bars[:-1]+(bad,))
        self.assertEqual(run(inputs=m, plan=p).state, B5RetestState372.BLOCKED)

    def test_noncross_and_unknown_epsilon_not_negative_detection(self):
        bars = bars_for(StructureSide.HIGH, Timeframe.H1)
        changed = snap(replace(bars[-1].selected, close=D("16")))
        inputs, plan = setup(higher=bars[:-1]+(changed,))
        r = run(inputs=inputs, plan=plan)
        self.assertEqual(r.state, B5RetestState372.NONCROSS_GEOMETRY_ONLY)
        self.assertEqual(r.status, DecisionStatus.UNVERIFIED)
        _, p = setup()
        self.assertEqual(run(plan=replace(p, candidate_epsilon=None)).state, B5RetestState372.BLOCKED)

    def test_correction_and_strategy_namespace_change_retest_fingerprint(self):
        inputs, plan = setup()
        old = run(inputs=inputs, plan=plan)
        row = inputs.snapshots_for(Timeframe.M15)[0].selected
        revised = replace(row.observation_revision, source_revision_or_payload_digest="retest-correction")
        m, p = setup(m15=(snap(replace(row, observation_revision=revised, normalized_digest_sha256="f"*64)),))
        new = run(inputs=m, plan=p)
        self.assertEqual(new.metrics.breakout_preview_id, old.metrics.breakout_preview_id)
        self.assertNotEqual(new.metrics.retest_preview_id, old.metrics.retest_preview_id)
        swing = run(strategy=Strategy.SWING)
        self.assertNotEqual(swing.metrics.retest_preview_id, old.metrics.retest_preview_id)

    def test_no_implicit_branch_index_or_external_row(self):
        _, p = setup()
        for bad in (replace(p, failed_break_index=0), replace(p, breakout_tf=Timeframe.H4),
                    replace(p, pivot_index=4), replace(p, retest_index=True),
                    replace(p, atr_stop=100)):
            with self.assertRaises(ValueError):
                run(plan=bad)
        _, failed = setup(variant=FAILED)
        with self.assertRaises(ValueError):
            run(variant=FAILED, plan=replace(failed, failed_break_index=None))
        with self.assertRaises(TypeError):
            run(inputs={})
