"""Source parity and fictional per-phase routing regression."""
from pathlib import Path
import unittest

from swing_trading.contracts import DecisionStatus, Strategy, ZONE_IDS
from swing_trading.market_data import Timeframe
from swing_trading.phase_input_routing369 import SOURCE_CLAUSES, route_phase_inputs
from swing_trading.zone_manifest_v03 import MANIFESTS, PHASES
from test_baseline_resolved_inputs368 import build, buckets, change, snapshot


def route(zone, phase, variant=None, inputs=None, **kwargs):
    return route_phase_inputs(
        build() if inputs is None else inputs, zone_id=zone,
        strategy=kwargs.pop("strategy", Strategy.SWING),
        variant_id=variant or MANIFESTS[zone].variants[0], phase=phase, **kwargs)


class PhaseRouting369Tests(unittest.TestCase):
    def test_exact_frozen_source_required_and_optional_clauses(self):
        path = Path(__file__).resolve().parents[1] / "docs/source-snapshots/01_MASTER_SPEC_v1.0_DRAFT.txt"
        if not path.exists():
            self.skipTest("source snapshot not included in isolated wheel")
        import re
        text = path.read_text(encoding="utf-8")
        part = text.split("24.4. 16 PHASE MANIFESTS", 1)[1].split("24.5.", 1)[0]
        rows = [line.split(" | ") for line in part.splitlines()
                if re.match(r"^[BS][1-8] \| R0 ", line)]
        self.assertEqual(len(rows), 16)
        for z, req, opt, *_ in rows:
            self.assertEqual(SOURCE_CLAUSES[z], tuple(
                re.split(r"; (?=R_C |R_E |R_F )", req)) + (opt,))

    def test_all_variants_all_phases_both_strategies_unverified(self):
        for zone in ZONE_IDS:
            for variant in MANIFESTS[zone].variants:
                for phase in PHASES:
                    for strategy in Strategy:
                        result = route(zone, phase, variant, strategy=strategy)
                        self.assertEqual(result.predicate_ref, MANIFESTS[zone].predicate_for(phase))
                        self.assertIs(result.status, DecisionStatus.UNVERIFIED)
                        self.assertFalse(result.action_eligible)
                        self.assertIn("EXACT_FEATURE_IDS", result.unresolved)

    def test_fixed_frames_and_independent_missing_not_blanket_gate(self):
        m = build(change(buckets(), Timeframe.W1, ()))
        result = route("B2", "R_E", inputs=m)
        self.assertEqual(result.buckets, ((Timeframe.M15, m.snapshots_for(Timeframe.M15)),))
        self.assertNotIn("MISSING_W1", result.unresolved)
        self.assertIn("MISSING_W1", route("B1", "R0", inputs=m).unresolved)

    def test_slash_choice_explicit_no_automatic_fallback(self):
        m = build(change(buckets(), Timeframe.H1, ()))
        result = route("B2", "R_F", inputs=m)
        self.assertEqual(result.choice_frames, (Timeframe.H1, Timeframe.M15))
        self.assertIn("EXPLICIT_FRAME_CHOICE_PENDING", result.unresolved)
        self.assertEqual(tuple(tf for tf, _ in result.buckets), (Timeframe.D1,))
        result = route("B2", "R_F", inputs=m, selected_frame=Timeframe.H1)
        self.assertIn("MISSING_H1", result.unresolved)
        self.assertNotIn("MISSING_M15", result.unresolved)
        with self.assertRaisesRegex(ValueError, "EXPLICIT_FRAME_CHOICE_INVALID"):
            route("B2", "R_F", selected_frame=Timeframe.H4)

    def test_major_w1_condition_only_named_variant(self):
        self.assertNotIn(Timeframe.W1, route("B1", "R_F").fixed_frames)
        self.assertIn(Timeframe.W1, route("B1", "R_F", "B1/F_MAJOR_REVERSAL_PENDING").fixed_frames)
        self.assertIn(Timeframe.W1, route("S1", "R_F", "S1/F_MAJOR_CYCLE_TOP_PENDING").fixed_frames)

    def test_tp_and_structure_routes_not_silently_combined(self):
        self.assertEqual(route("S3", "R_E", "S3/E_TP").fixed_frames, ())
        self.assertEqual(route("S3", "R_E", "S3/E_MICRO_CHOCH").fixed_frames, (Timeframe.M15,))
        self.assertEqual(route("S3", "R_F", "S3/F_TP").choice_frames, ())
        self.assertEqual(route("S3", "R_F", "S3/F_MICRO_BREAK").choice_frames, (Timeframe.H1, Timeframe.M15))
        self.assertEqual(route("B3", "R_E", "B3/E_FALSE_BREAK").fixed_frames, ())
        self.assertEqual(route("B3", "R_E", "B3/E_BOS_UP").fixed_frames, (Timeframe.M15,))

    def test_optional_m5_only_armed_and_source_listed(self):
        self.assertIsNone(route("B2", "R_E").optional_m5)
        m = build(armed=True)
        self.assertEqual(route("B2", "R_E", inputs=m).optional_m5, m.snapshots_for(Timeframe.M5))
        self.assertIsNone(route("S2", "R_E", inputs=m).optional_m5)
        self.assertNotIn(Timeframe.M5, route("B2", "R_E", inputs=m).fixed_frames)

    def test_rvol_tod_required_when_explicitly_invoked(self):
        self.assertNotIn("REQUIRED_RVOL_TOD_UNVERIFIED", route("B8", "R_E").unresolved)
        self.assertIn("REQUIRED_RVOL_TOD_UNVERIFIED",
                      route("B8", "R_E", "B8/INTRADAY_RVOL_TOD_PENDING").unresolved)

    def test_unresolved_or_local_unverified_is_not_negative_signal(self):
        from swing_trading.source_quality import ResolvedBarSnapshotV12, QualityState
        s = snapshot(Timeframe.M15)
        conflict = ResolvedBarSnapshotV12(s.market_bar_key, None, 2, "SOURCE_OR_REVISION_CONFLICT")
        m = build(change(buckets(), Timeframe.M15, (conflict,)))
        self.assertIn("UNRESOLVED_REVISION_M15", route("B2", "R_E", inputs=m).unresolved)
        m = build(change(buckets(), Timeframe.M15, (snapshot(Timeframe.M15, quality=QualityState.UNVERIFIED),)))
        self.assertIn("LOCAL_PREREQUISITES_INCOMPLETE_M15", route("B2", "R_E", inputs=m).unresolved)
        self.assertEqual(route("B2", "R_E", inputs=m).status, DecisionStatus.UNVERIFIED)

    def test_wrong_variant_phase_type_rejected(self):
        for kwargs in (dict(zone_id="B2", variant_id="S2/BASE", phase="R_E"),
                       dict(zone_id="B2", variant_id="B2/BASE", phase="WRONG")):
            with self.assertRaises(ValueError):
                route_phase_inputs(build(), strategy=Strategy.SWING, **kwargs)
        with self.assertRaises(TypeError):
            route_phase_inputs({}, zone_id="B2", strategy=Strategy.SWING, variant_id="B2/BASE", phase="R_E")
