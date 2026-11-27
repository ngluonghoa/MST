"""§422 B8 RF later same-definition adjusted D1 RS, fictional."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.relative_strength421 import RSPlan421, RSBenchmark421
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from test_b8_rf418 import fixture as rf_fixture
from test_b8_rs421 import adjusted
from test_b8_base415 import run
from test_causal_indicators import make_bar, snap


def fixture(tf=Timeframe.D1, *, weak=False):
    inputs,p=rf_fixture(tf=tf)
    buckets=tuple((f,tuple(adjusted(s.selected) for s in rows)) for f,rows in inputs.buckets)
    inputs=replace(inputs,buckets=buckets)
    daily=inputs.snapshots_for(Timeframe.D1)
    if tf is Timeframe.H1:
        target=inputs.snapshots_for(tf)[p.rf.breakout_index].selected
        start=target.market_bar_key.bar_start_utc-timedelta(days=2)
        extra=tuple(adjusted(make_bar(1600+i,start=start+timedelta(days=i),
                    open_price=price,close=price,high=D(18),low=D(8)))
                    for i,price in enumerate((D(14),D(17))))
        daily+=extra
        inputs=replace(inputs,buckets=tuple((f,daily if f is Timeframe.D1 else rows)
                                            for f,rows in inputs.buckets))
    prices=(D(10),D(10),D(10),D(9),D(8),D(7),D(6) if not weak else D(30))
    bench=tuple(adjusted(x.selected,benchmark=True,close=c)
                for x,c in zip(daily[10:17],prices))
    r0=RSPlan421(10,15,2,2,RSBenchmark421.SECTOR,"fixture-index","fixture-alignment-v1",
                bench[:5],D("0.01"))
    rf=replace(r0,stock_start=12,stock_stop=17,benchmark_rows=bench[2:])
    return inputs,replace(p,rs=r0,rf=replace(p.rf,rs=rf))


class B8RF_RS422Tests(unittest.TestCase):
    def test_both_frames_strategies_variants(self):
        for tf in (Timeframe.D1,Timeframe.H1):
            for strategy in Strategy:
                for variant in ("B8/BASE","B8/INTRADAY_RVOL_TOD_PENDING"):
                    inputs,p=fixture(tf)
                    row,safe=run(inputs,p,strategy=strategy,variant=variant)
                    proof=row.private_preview.assessments[-1][1]
                    self.assertTrue(proof.rs.candidate_match)
                    self.assertGreater(proof.rs.current_rs,row.private_preview.assessments[0][1].rs.current_rs)
                    self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_weak_and_uncalibrated(self):
        inputs,p=fixture(weak=True)
        row,safe=run(inputs,p)
        self.assertFalse(row.private_preview.assessments[-1][1].rs.candidate_match)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")
        inputs,p=fixture()
        row,_=run(inputs,replace(p,rf=replace(p.rf,rs=replace(p.rf.rs,candidate_min_slope=None))))
        self.assertIsNone(row.private_preview.assessments[-1][1].rs.candidate_match)

    def test_definition_change_and_absent_r0(self):
        inputs,p=fixture()
        for changed in (replace(p.rf.rs,benchmark_kind=RSBenchmark421.INDEX),
                        replace(p.rf.rs,alignment_policy_version="other")):
            _,safe=run(inputs,replace(p,rf=replace(p.rf,rs=changed)))
            self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")
        for r0 in (None,replace(p.rs,candidate_min_slope=None)):
            _,safe=run(inputs,replace(p,rs=r0))
            self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_overlap_revision_and_late_benchmark(self):
        inputs,p=fixture()
        rs=p.rf.rs
        overlap=adjusted(rs.benchmark_rows[0].selected,benchmark=True,close=D(11))
        late=snap(replace(rs.benchmark_rows[-1].selected,verified_at_utc=inputs.as_of_utc))
        for rows in ((overlap,)+rs.benchmark_rows[1:],rs.benchmark_rows[:-1]+(late,)):
            _,safe=run(inputs,replace(p,rf=replace(p.rf,rs=replace(rs,benchmark_rows=rows))))
            self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_stale_d1_window_and_wrong_plan(self):
        inputs,p=fixture()
        for rs in (p.rs,replace(p.rf.rs,stock_start=11,stock_stop=16)):
            _,safe=run(inputs,replace(p,rf=replace(p.rf,rs=rs)))
            self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")
        _,safe=run(inputs,replace(p,rf=replace(p.rf,rs=True)))
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_legacy_and_no_authority(self):
        inputs,p=fixture()
        row,safe=run(inputs,p)
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("fixture-index","current_rs","candidate_min_slope",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
        row,_=run(inputs,replace(p,rf=replace(p.rf,rs=None)))
        self.assertIsNone(row.private_preview.assessments[-1][1].rs)
