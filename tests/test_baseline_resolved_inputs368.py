"""Fictional original analysis-scope and v1.2 snapshot routing."""
from dataclasses import replace
from datetime import timedelta
import unittest

from swing_trading.market_data import PriceBasis, Timeframe
from swing_trading.private_multitf_readiness import (
    BASELINE_CORE_TF, BaselineResolvedInputs, PrivateMultiTfDenied,
)
from swing_trading.source_quality import (
    CoverageState, LifecycleState, QualityState, ResolvedBarSnapshotV12,
    resolve_as_known,
)
from test_source_quality import T, candle

AS_OF = T + timedelta(days=14)
ID = "HOSE:ABC:registry-v1"


def snapshot(tf, *, start=T, basis=PriceBasis.RAW, provider="FIXTURE",
             adjustment="fixture-adjustment", quality=QualityState.VERIFIED):
    base = candle()
    key = replace(base.market_bar_key, instrument_id=ID, timeframe=tf,
                  bar_start_utc=start, price_basis=basis)
    obs = replace(base.observation_key, market_bar_key=key, provider_id=provider)
    end = start + timedelta(minutes=15)
    rev = replace(base.observation_revision, observation_key=obs,
                  first_known_time_utc=end, retrieved_at_utc=end,
                  adjustment_revision=adjustment)
    row = replace(base, market_bar_key=key, observation_key=obs,
                  observation_revision=rev, bar_end_utc=end,
                  retrieved_at_utc=end, verified_at_utc=end,
                  quality_state=quality, observed_minutes=None,
                  expected_minutes=None)
    return resolve_as_known(key, (row,), AS_OF)


def buckets(*, armed=False, populated=True):
    tfs = BASELINE_CORE_TF + ((Timeframe.M5,) if armed else ())
    return tuple((tf, (snapshot(tf),) if populated else ()) for tf in tfs)


def build(b=None, *, armed=False, asof=AS_OF):
    return BaselineResolvedInputs(ID, "HOSE", asof, armed,
                                  buckets(armed=armed) if b is None else b)


def change(b, tf, snaps):
    return tuple((key, snaps if key is tf else rows) for key, rows in b)


class BaselineResolved368Tests(unittest.TestCase):
    def test_original_core_includes_w1_excludes_h4_and_unarmed_m5(self):
        self.assertEqual(BASELINE_CORE_TF, (Timeframe.W1, Timeframe.D1,
            Timeframe.H1, Timeframe.M30, Timeframe.M15))
        model = build()
        r = model.safe_readiness()
        self.assertEqual([x["timeframe"] for x in r["timeframes"]],
                         ["W1", "D1", "H1", "M30", "M15", "M5"])
        self.assertEqual(r["timeframes"][-1]["status"], "NOT_ARMED")
        self.assertFalse(r["source_released"])
        self.assertEqual(r["decision"], "NO_TRADE")
        for tf in (Timeframe.M1, Timeframe.M5, Timeframe.H4):
            with self.assertRaisesRegex(PrivateMultiTfDenied, "NOT_IN_ANALYSIS_SCOPE"):
                model.snapshots_for(tf)

    def test_armed_m5_is_explicit_and_missing_is_not_no_signal(self):
        b = buckets(armed=True)
        model = build(change(b, Timeframe.M5, ()), armed=True)
        self.assertEqual(model.snapshots_for(Timeframe.M5), ())
        self.assertEqual(model.safe_readiness()["timeframes"][-1]["status"], "MISSING")
        self.assertFalse(model.safe_readiness()["global_rule_decision_inferred"])
        self.assertEqual(len(build(armed=True).snapshots_for(Timeframe.M5)), 1)

    def test_wrong_scope_order_and_mutable_buckets_denied(self):
        b = buckets()
        for bad in (list(b), b[:-1], tuple(reversed(b)),
                    b + ((Timeframe.H4, ()),), b + ((Timeframe.M5, ()),),
                    change(b, Timeframe.D1, list(b[1][1]))):
            with self.subTest(kind=type(bad).__name__), self.assertRaises(PrivateMultiTfDenied):
                build(bad)
        with self.assertRaises(PrivateMultiTfDenied):
            build(b, armed=True)

    def test_unresolved_revision_counts_are_not_silently_discarded(self):
        s = snapshot(Timeframe.W1)
        empty = ResolvedBarSnapshotV12(s.market_bar_key, None, 0, "NO_VISIBLE_REVISION")
        c = snapshot(Timeframe.W1, start=T+timedelta(days=7))
        conflict = ResolvedBarSnapshotV12(c.market_bar_key, None, 2,
                                          "SOURCE_OR_REVISION_CONFLICT")
        model = build(change(buckets(), Timeframe.W1, (empty, conflict)))
        row = model.safe_readiness()["timeframes"][0]
        self.assertEqual(row["requested_snapshots"], 2)
        self.assertEqual(row["single_visible"], 0)
        self.assertEqual(row["no_visible_revision"], 1)
        self.assertEqual(row["conflicting_revision"], 1)
        self.assertEqual(row["local_prerequisites_only"], 0)
        self.assertEqual(model.snapshots_for(Timeframe.W1), (empty, conflict))

    def test_future_retrieval_cannot_enter_asof_input(self):
        s = snapshot(Timeframe.D1)
        row = s.selected
        future = AS_OF + timedelta(seconds=1)
        rev = replace(row.observation_revision, retrieved_at_utc=future)
        altered = replace(row, observation_revision=rev, retrieved_at_utc=future,
                          verified_at_utc=future)
        visible = resolve_as_known(row.market_bar_key, (altered,), AS_OF)
        with self.assertRaisesRegex(PrivateMultiTfDenied, "SELECTED_REVISION_LOOKAHEAD"):
            build(change(buckets(), Timeframe.D1, (visible,)))

    def test_open_bar_visible_but_never_qualified(self):
        s = snapshot(Timeframe.M15)
        row = replace(s.selected, lifecycle_state=LifecycleState.OPEN,
                      bar_end_utc=AS_OF+timedelta(minutes=1))
        snap = resolve_as_known(row.market_bar_key, (row,), AS_OF)
        m = build(change(buckets(), Timeframe.M15, (snap,)))
        self.assertEqual(m.safe_readiness()["timeframes"][4]["local_prerequisites_only"], 0)

    def test_mixed_provider_basis_and_adjustment_do_not_enter_core(self):
        for s in (snapshot(Timeframe.W1, provider="OTHER"),
                  snapshot(Timeframe.W1, basis=PriceBasis.ADJUSTED),
                  snapshot(Timeframe.W1, adjustment="other")):
            with self.subTest(s=s.reason), self.assertRaisesRegex(PrivateMultiTfDenied, "MIXED_CROSS_TF"):
                build(change(buckets(), Timeframe.W1, (s,)))

    def test_duplicates_overlap_and_wrong_tf_denied(self):
        s = snapshot(Timeframe.M15)
        overlap = snapshot(Timeframe.M15, start=T+timedelta(minutes=1))
        for bad in ((s, s), (s, overlap), (snapshot(Timeframe.D1),)):
            with self.assertRaises(PrivateMultiTfDenied):
                build(change(buckets(), Timeframe.M15, bad))

    def test_partial_and_unverified_are_local_counts_only(self):
        s = snapshot(Timeframe.H1, quality=QualityState.UNVERIFIED)
        row = replace(s.selected, coverage_state=CoverageState.SPARSE_UNVERIFIED)
        snap = resolve_as_known(row.market_bar_key, (row,), AS_OF)
        model = build(change(buckets(), Timeframe.H1, (snap,)))
        report = model.safe_readiness()
        self.assertEqual(report["timeframes"][2]["local_prerequisites_only"], 0)
        self.assertFalse(report["signal_engine_parity_verified"])
        self.assertNotIn("volume", str(report))
