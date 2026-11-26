"""Four independent B2/S2 ingredient paths, fictional snapshots only."""
from dataclasses import replace
from decimal import Decimal as D
import unittest

from swing_trading.b2s2_swing_evidence215 import (
    B2S2PivotDenied215, PivotPairState215, PairSlice371, NearSlice371,
    BosSlice371, B2S2PreviewPlan371, inspect_b2s2_baseline_preview,
    inspect_b2s2_two_pivot215,
)
from swing_trading.causal_structure_geometry import StructureSide, TiePolicy
from swing_trading.contracts import DecisionStatus, Strategy
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import BASELINE_CORE_TF, BaselineResolvedInputs
from swing_trading.source_quality import ResolvedBarSnapshotV12
from swing_trading.structural_phase_evidence import NearEvidenceState214, PhaseEvidenceState
from test_b2s2_swing_evidence215 import synthetic_rows
from test_structural_phase_evidence214 import make_target
from test_structural_phase_evidence213 import bars_for
from test_causal_structure_geometry import AS_OF, atr_d1

TIE = TiePolicy.STRICT_V1


def model(zone, *, missing_h1=False, conflict=False):
    d1 = atr_d1() + synthetic_rows(zone, "R0")
    m15 = synthetic_rows(zone, "R_E") + (make_target(zone),)
    if conflict:
        bad = ResolvedBarSnapshotV12(m15[5].market_bar_key, None, 2,
                                      "SOURCE_OR_REVISION_CONFLICT")
        m15 = m15[:5] + (bad,) + m15[6:]
    h1 = () if missing_h1 else bars_for(
        StructureSide.HIGH if zone == "B2" else StructureSide.LOW, Timeframe.H1)
    lookup = {Timeframe.D1: d1, Timeframe.M15: m15, Timeframe.H1: h1}
    first = d1[0].market_bar_key
    return BaselineResolvedInputs(first.instrument_id, first.exchange, AS_OF, False,
                                   tuple((tf, lookup.get(tf, ())) for tf in BASELINE_CORE_TF))


def config():
    return B2S2PreviewPlan371(
        PairSlice371(15, 23, 2, 5, 1, 1, TIE),
        NearSlice371(8, Timeframe.D1, 15, 19, 2, 1, 1, 0, 15, TIE, D("0.2")),
        PairSlice371(0, 8, 2, 5, 1, 1, TIE),
        BosSlice371(Timeframe.H1, 5, 2, 1, 1, 0, 15, TIE, D("0.25")),
    )


def run(zone="B2", strategy=Strategy.SHORT, inputs=None, plan=None):
    return inspect_b2s2_baseline_preview(
        model(zone) if inputs is None else inputs, zone_id=zone, strategy=strategy,
        plan=config() if plan is None else plan)


class B2S2Baseline371Tests(unittest.TestCase):
    def test_both_mirrors_both_strategies_run_four_independent_ingredients(self):
        for zone in ("B2", "S2"):
            for strategy in Strategy:
                with self.subTest(zone=zone, strategy=strategy):
                    p = run(zone, strategy)
                    self.assertEqual([r.phase for r, _ in p.assessments], ["R0", "R_C", "R_E", "R_F"])
                    states = [ev.state for _, ev in p.assessments]
                    self.assertEqual(states, [PivotPairState215.GEOMETRY_MATCH_UNVERIFIED,
                        NearEvidenceState214.CAUSAL_DISTANCE_UNCALIBRATED,
                        PivotPairState215.GEOMETRY_MATCH_UNVERIFIED,
                        PhaseEvidenceState.CROSS_GEOMETRY_UNVERIFIED])
                    for r, ev in p.assessments:
                        self.assertEqual(r.predicate_ref, ev.predicate_ref if hasattr(ev, "predicate_ref")
                                         else r.predicate_ref)
                        self.assertIs(ev.status, DecisionStatus.UNVERIFIED)
                        self.assertFalse(ev.action_eligible)
                        self.assertIn("PARAMETER_AND_PREDICATE_APPROVAL", r.unresolved)
                    self.assertFalse(p.phase_sequence_verified)
                    self.assertFalse(p.action_eligible)
                    self.assertIs(p.status, DecisionStatus.UNVERIFIED)

    def test_missing_h1_does_not_block_independent_d1_and_m15_math(self):
        p = run(inputs=model("B2", missing_h1=True))
        self.assertEqual(p.assessments[0][1].state, PivotPairState215.GEOMETRY_MATCH_UNVERIFIED)
        self.assertEqual(p.assessments[1][1].state, NearEvidenceState214.CAUSAL_DISTANCE_UNCALIBRATED)
        self.assertEqual(p.assessments[3][1].state, PhaseEvidenceState.BLOCKED)
        self.assertIn("MISSING_H1", p.assessments[3][0].unresolved)

    def test_conflict_in_r_e_slice_not_silently_removed(self):
        p = run(inputs=model("B2", conflict=True))
        self.assertEqual(p.assessments[2][1].state, PivotPairState215.BLOCKED)
        self.assertEqual(p.assessments[2][1].reason, "PIVOT_UNRESOLVED_SOURCE_REVISION")
        self.assertIn("UNRESOLVED_REVISION_M15", p.assessments[2][0].unresolved)
        self.assertEqual(p.assessments[0][1].state, PivotPairState215.GEOMETRY_MATCH_UNVERIFIED)

    def test_exact_pair_identity_matches_previous_implementation(self):
        m = model("B2")
        p = run(inputs=m)
        old = inspect_b2s2_two_pivot215(
            zone_id="B2", strategy=Strategy.SHORT, phase="R0",
            history=m.snapshots_for(Timeframe.D1)[15:23],
            first_index=2, second_index=5, left_count=1, right_count=1,
            tie_policy=TIE, as_of_utc=m.as_of_utc)
        self.assertEqual(p.assessments[0][1], old)

    def test_separate_strategy_fingerprints_and_no_phase_progression_claim(self):
        a = run(strategy=Strategy.SHORT)
        b = run(strategy=Strategy.SWING)
        self.assertNotEqual(a.assessments[0][1].preview_id, b.assessments[0][1].preview_id)
        self.assertNotEqual(a.assessments[3][1].bos_preview_id, b.assessments[3][1].bos_preview_id)
        self.assertFalse(a.phase_sequence_verified)
        self.assertFalse(b.phase_sequence_verified)

    def test_bad_slice_plan_and_pivot_frame_rejected(self):
        p = config()
        for bad in (replace(p, r0=replace(p.r0, start=-1)),
                    replace(p, rc=replace(p.rc, pivot_tf=Timeframe.H4)),
                    replace(p, rc=replace(p.rc, target_index=99)),
                    replace(p, re=replace(p.re, stop=99))):
            with self.assertRaises(B2S2PivotDenied215):
                run(plan=bad)
        with self.assertRaises(B2S2PivotDenied215):
            run(plan={})
