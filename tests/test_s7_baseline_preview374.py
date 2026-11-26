"""§374 exact bound S7 chain, synthetic-only."""
from dataclasses import replace
import unittest
from decimal import Decimal as D

from swing_trading.contracts import Strategy, DecisionStatus
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import BaselineResolvedInputs, BASELINE_CORE_TF
from swing_trading.s7_retest_evidence import (
    S7OriginPlan374, S7MicroPlan374, S7EarlyMode,
    inspect_s7_baseline_preview, inspect_s7_confirmation_evidence,
)
from swing_trading.source_quality import ResolvedBarSnapshotV12
import test_s7_retest_evidence as legacy_fixture
from test_causal_indicators import snap

MICRO = "S7/F_MICRO_BREAK"
CONT = "S7/F_CONTINUATION"


def fixture(later=False, *, conflict=False):
    p = legacy_fixture.S7ConfirmationEvidenceTests().chain()
    m15 = (p["prior_retest"], p["retest"])
    if later:
        e, follow = legacy_fixture.S7EarlyEvidenceTests().later()
        p["retest"] = e["retest"]
        p["mode"] = S7EarlyMode.LATER_CLOSE_BELOW
        p["followup"] = follow
        m15 = (p["prior_retest"], p["retest"], follow)
    d1 = p["atr_d1_history"] + p["pivot_history"] + (p["previous"], p["breakdown"])
    d1 += p["micro_history"] + (p["micro_previous"], p["confirmation"])
    if conflict:
        s = m15[1]
        m15 = (m15[0], ResolvedBarSnapshotV12(s.market_bar_key, None, 2,
               "SOURCE_OR_REVISION_CONFLICT")) + m15[2:]
    first = d1[0].market_bar_key
    model = BaselineResolvedInputs(first.instrument_id, first.exchange, p["as_of_utc"],
        False, tuple((tf, d1 if tf is Timeframe.D1 else m15 if tf is Timeframe.M15 else ())
                     for tf in BASELINE_CORE_TF))
    origin = S7OriginPlan374(Timeframe.D1, 15, 20, 2, 1, 1, 0, 15, 0, 15, 1,
                            p["mode"], 2 if later else None, p["tie_policy"], D(".25"))
    micro = S7MicroPlan374(Timeframe.D1, 21, 25, 1, 1, 1, 0, 15,
                           p["micro_tie_policy"], D(".1"))
    return model, origin, micro, p


def run(data=None, *, variant=MICRO, strategy=Strategy.SHORT):
    m,o,f,_ = fixture() if data is None else data
    return inspect_s7_baseline_preview(m, strategy=strategy, variant_id=variant,
                                       origin_plan=o, micro_plan=f)


class BoundS7374Tests(unittest.TestCase):
    def test_both_modes_and_strategies_match_exact_legacy_chain(self):
        for later in (False, True):
            for strategy in Strategy:
                data = fixture(later)
                r = run(data, strategy=strategy)
                self.assertEqual(r.confirmation, inspect_s7_confirmation_evidence(
                    **dict(data[3], strategy=strategy)))
                self.assertEqual(r.reason, "RF_CHAIN_GEOMETRY_UNCALIBRATED")
                self.assertEqual(r.retest.retest_preview_id, r.early.retest_preview_id)
                self.assertEqual(r.early.early_preview_id, r.confirmation.early_preview_id)
                self.assertEqual([x.phase for x in r.routed_phases], ["R0","R_C","R_E","R_F"])
                self.assertEqual(r.status, DecisionStatus.UNVERIFIED)
                self.assertFalse(r.action_eligible)

    def test_continuation_explicit_pending_never_uses_micro_break(self):
        m,o,f,p = fixture()
        r = run((m,o,None,p), variant=CONT)
        self.assertEqual(r.reason, "CONTINUATION_PREDICATE_SPEC_PENDING")
        self.assertTrue(r.early.shape_observed)
        self.assertIsNone(r.confirmation)
        self.assertFalse(r.action_eligible)
        with self.assertRaisesRegex(ValueError, "CONTINUATION_NOT_MICRO_FALLBACK"):
            run((m,o,f,p), variant=CONT)

    def test_conflicting_retest_blocks_chain(self):
        r = run(fixture(conflict=True))
        self.assertIsNone(r.retest.origin_preview_id)
        self.assertIsNone(r.early.early_preview_id)
        self.assertIsNone(r.confirmation.confirmation_preview_id)
        self.assertIn("UNRESOLVED_REVISION_M15", r.routed_phases[2].unresolved)

    def test_missing_independent_buckets_never_fallback(self):
        m,o,f,p = fixture()
        changed = replace(m, buckets=tuple((tf, () if tf is Timeframe.M15 else rows)
                                           for tf,rows in m.buckets))
        r = run((changed,o,f,p))
        self.assertEqual(r.reason, "ORIGIN_OR_RETEST_INPUT_MISSING")
        self.assertIsNone(r.confirmation)

    def test_revision_change_updates_exact_confirmation_not_origin(self):
        m,o,f,p = fixture()
        old = run((m,o,f,p))
        rows = m.snapshots_for(Timeframe.D1)
        last = rows[-1].selected
        rev = replace(last.observation_revision, source_revision_or_payload_digest="s7-corrected")
        fresh = snap(replace(last, observation_revision=rev, close=D(".6")))
        changed = replace(m, buckets=tuple((tf, rows[:-1]+(fresh,) if tf is Timeframe.D1 else rr)
                                           for tf,rr in m.buckets))
        new = run((changed,o,f,p))
        self.assertEqual(old.retest.origin_preview_id,new.retest.origin_preview_id)
        self.assertNotEqual(old.confirmation.confirmation_preview_id,new.confirmation.confirmation_preview_id)

    def test_explicit_plan_indices_and_modes(self):
        m,o,f,p = fixture()
        for bad in (replace(o, timeframe=Timeframe.H4),replace(o, retest_index=True),
                    replace(o, followup_index=2),replace(o, breakdown_index=99),
                    replace(o, mode=S7EarlyMode.LATER_CLOSE_BELOW)):
            with self.assertRaises(ValueError):
                run((m,bad,f,p))
        with self.assertRaises(ValueError):
            run((m,o,replace(f,pivot_index=4),p))
        with self.assertRaises(ValueError):
            run((m,o,None,p))
