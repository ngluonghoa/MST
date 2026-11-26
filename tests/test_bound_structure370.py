"""§370 baseline-bound structural ingredient regressions (fictional only)."""
from dataclasses import replace
from decimal import Decimal as D
import unittest

from swing_trading.contracts import DecisionStatus, Strategy
from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import BASELINE_CORE_TF, BaselineResolvedInputs
from swing_trading.source_quality import ResolvedBarSnapshotV12, resolve_as_known
from swing_trading.structural_phase_evidence import (
    ROUTES, PhaseEvidenceDenied, PhaseEvidenceState, inspect_phase_bos_evidence,
    inspect_routed_phase_bos,
)
from test_causal_structure_geometry import AS_OF, atr_d1
from test_structural_phase_evidence213 import bars_for


def model(key, tf, *, bars=None, atr=None):
    history = bars_for(ROUTES[key][0], tf) if bars is None else bars
    atr = atr_d1() if atr is None else atr
    first = atr_d1()[0].market_bar_key
    d1 = atr + history if tf is Timeframe.D1 else atr
    buckets = tuple((frame, d1 if frame is Timeframe.D1 else
                     history if frame is tf else ()) for frame in BASELINE_CORE_TF)
    return BaselineResolvedInputs(first.instrument_id, first.exchange, AS_OF, False, buckets)


def run(key, tf, inputs=None, **options):
    kwargs = dict(zone_id=key[0], variant_id=key[1], phase=key[2],
                  strategy=Strategy.SHORT, timeframe=tf,
                  breakout_index=20 if tf is Timeframe.D1 else 5,
                  pivot_index=17 if tf is Timeframe.D1 else 2,
                  left_count=1, right_count=1, atr_start=0, atr_stop=15,
                  tie_policy=TiePolicy.STRICT_V1, candidate_epsilon=D("0.25"))
    kwargs.update(options)
    return inspect_routed_phase_bos(model(key, tf) if inputs is None else inputs, **kwargs)


KEY = ("B1", "B1/E_BOS_UP", "R_E")


class BoundStructure370Tests(unittest.TestCase):
    def test_every_explicit_route_and_timeframe_executes_existing_geometry(self):
        for key, (side, tfs) in ROUTES.items():
            for tf in tfs:
                with self.subTest(key=key, tf=tf):
                    routed, ev = run(key, tf)
                    self.assertEqual(ev.state, PhaseEvidenceState.CROSS_GEOMETRY_UNVERIFIED)
                    self.assertEqual(ev.predicate_ref, routed.predicate_ref)
                    self.assertEqual(ev.side, side)
                    self.assertEqual(ev.status, DecisionStatus.UNVERIFIED)
                    self.assertFalse(ev.action_eligible)
                    self.assertFalse(routed.action_eligible)
                    self.assertIn("PARAMETER_AND_PREDICATE_APPROVAL", routed.unresolved)

    def test_identity_matches_legacy_geometry_on_exact_same_slices(self):
        m = model(KEY, Timeframe.M15)
        rows = m.snapshots_for(Timeframe.M15)
        _, actual = run(KEY, Timeframe.M15, inputs=m)
        old = inspect_phase_bos_evidence(
            zone_id=KEY[0], strategy=Strategy.SHORT, variant_id=KEY[1], phase=KEY[2],
            pivot_history=rows[:4], pivot_index=2, left_count=1, right_count=1,
            previous=rows[4], breakout=rows[5], atr_d1_history=m.snapshots_for(Timeframe.D1),
            tie_policy=TiePolicy.STRICT_V1, candidate_epsilon=D("0.25"), as_of_utc=m.as_of_utc)
        self.assertEqual(actual, old)

    def test_explicit_choice_bound_and_independent_missing_not_promotion(self):
        key = ("B2", "B2/BASE", "R_F")
        routed, ev = run(key, Timeframe.H1)
        self.assertEqual(routed.selected_frame, Timeframe.H1)
        self.assertEqual(ev.timeframe, Timeframe.H1)
        self.assertFalse(ev.detector_approved)

    def test_missing_and_conflicting_snapshot_blocks_without_fallback(self):
        _, missing = run(KEY, Timeframe.M15, inputs=model(KEY, Timeframe.M15, bars=()))
        self.assertEqual(missing.state, PhaseEvidenceState.BLOCKED)
        self.assertIsNone(missing.bos_preview_id)
        bars = bars_for(ROUTES[KEY][0], Timeframe.M15)
        conflict = ResolvedBarSnapshotV12(bars[5].market_bar_key, None, 2, "SOURCE_OR_REVISION_CONFLICT")
        routed, blocked = run(KEY, Timeframe.M15, inputs=model(
            KEY, Timeframe.M15, bars=bars[:5]+(conflict,)))
        self.assertIn("UNRESOLVED_REVISION_M15", routed.unresolved)
        self.assertEqual(blocked.state, PhaseEvidenceState.BLOCKED)

    def test_late_atr_slice_and_missing_candidate_parameter_block(self):
        _, ev = run(KEY, Timeframe.M15, candidate_epsilon=None)
        self.assertEqual(ev.state, PhaseEvidenceState.BLOCKED)
        self.assertEqual(ev.reason, "UNAPPROVED_EPSILON_NOT_SUPPLIED")
        _, ev = run(KEY, Timeframe.M15, atr_stop=14)
        self.assertEqual(ev.state, PhaseEvidenceState.BLOCKED)

    def test_revision_change_changes_bound_event_identity(self):
        bars = bars_for(ROUTES[KEY][0], Timeframe.M15)
        r = bars[5].selected
        rev = replace(r.observation_revision, source_revision_or_payload_digest="fictional-corrected")
        changed = replace(r, observation_revision=rev, normalized_digest_sha256="f"*64)
        fresh = resolve_as_known(r.market_bar_key, (changed,), AS_OF)
        _, old = run(KEY, Timeframe.M15)
        _, new = run(KEY, Timeframe.M15, inputs=model(KEY, Timeframe.M15, bars=bars[:5]+(fresh,)))
        self.assertEqual(old.pivot_preview_id, new.pivot_preview_id)
        self.assertNotEqual(old.bos_preview_id, new.bos_preview_id)

    def test_external_rows_wrong_route_and_bad_indices_denied(self):
        for kwargs in ({"breakout_index": True}, {"pivot_index": 4},
                       {"atr_start": 15}, {"atr_stop": 16}, {"breakout_index": 6}):
            with self.subTest(kwargs=kwargs), self.assertRaises(PhaseEvidenceDenied):
                run(KEY, Timeframe.M15, **kwargs)
        with self.assertRaises(PhaseEvidenceDenied):
            run(KEY, Timeframe.H1, inputs=model(KEY, Timeframe.M15))
        with self.assertRaises(PhaseEvidenceDenied):
            run(KEY, Timeframe.M15, inputs={})
        with self.assertRaises(TypeError):
            run(KEY, Timeframe.M15, breakout=bars_for(ROUTES[KEY][0], Timeframe.M15)[5])
