"""§421 B8 R0 adjusted aligned log-RS candidate, fictional."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D, localcontext
import json
import unittest

from swing_trading.relative_strength421 import RSPlan421, RSBenchmark421
from swing_trading.contracts import Strategy
from swing_trading.market_data import InstrumentClass, PriceBasis, Timeframe
from test_b8_base415 import fixture as base_fixture, run
from test_causal_indicators import snap


def adjusted(row, *, benchmark=False, close=None):
    key=replace(row.market_bar_key,price_basis=PriceBasis.ADJUSTED)
    if benchmark:
        key=replace(key,instrument_class=InstrumentClass.INDEX,instrument_id="fixture-index")
    obs=replace(row.observation_key,market_bar_key=key)
    rev=replace(row.observation_revision,observation_key=obs)
    if close is not None:
        row=replace(row,open=close,close=close,high=close+D(1),low=close-D(1))
    return snap(replace(row,market_bar_key=key,observation_key=obs,observation_revision=rev))


def fixture(*, kind=RSBenchmark421.SECTOR, flat=False):
    inputs,p=base_fixture()
    buckets=tuple((f,tuple(adjusted(s.selected) for s in rows)) for f,rows in inputs.buckets)
    inputs=replace(inputs,buckets=buckets)
    daily=inputs.snapshots_for(Timeframe.D1)
    # Stock closes are constant; benchmark decelerates in latest window.
    prices=(D(10),D(10),D(10),D(9),D(8)) if not flat else (D(10),)*5
    benchmark=tuple(adjusted(x.selected,benchmark=True,close=c)
                    for x,c in zip(daily[-5:],prices))
    rs=RSPlan421(10,15,2,2,kind,"fixture-index","fixture-alignment-v1",benchmark,D("0.01"))
    return inputs,replace(p,rs=rs)


class B8RS421Tests(unittest.TestCase):
    def test_both_strategies_variants_and_benchmark_labels(self):
        for strategy in Strategy:
            for variant in ("B8/BASE","B8/INTRADAY_RVOL_TOD_PENDING"):
                for kind in RSBenchmark421:
                    inputs,p=fixture(kind=kind)
                    row,safe=run(inputs,p,strategy=strategy,variant=variant)
                    proof=row.private_preview.assessments[0][1].rs
                    with localcontext() as ctx:
                        ctx.prec=50
                        self.assertEqual(proof.current_rs,-(D(8)/D(10)).ln())
                        self.assertEqual(proof.slope,proof.current_rs/D(2))
                    self.assertTrue(proof.candidate_match)
                    self.assertEqual(safe["phases"][0]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_flat_nonmatch_and_no_default_threshold(self):
        inputs,p=fixture(flat=True)
        row,safe=run(inputs,p)
        self.assertFalse(row.private_preview.assessments[0][1].rs.candidate_match)
        self.assertEqual(safe["phases"][0]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")
        row,_=run(inputs,replace(p,rs=replace(p.rs,candidate_min_slope=None)))
        self.assertIsNone(row.private_preview.assessments[0][1].rs.candidate_match)

    def test_wrong_benchmark_and_raw_basis_block(self):
        inputs,p=fixture()
        _,safe=run(inputs,replace(p,rs=replace(p.rs,benchmark_id="wrong")))
        self.assertEqual(safe["phases"][0]["ingredient_state"],"BLOCKED")
        raw,_=base_fixture()
        _,safe=run(raw,p)
        self.assertEqual(safe["phases"][0]["ingredient_state"],"BLOCKED")

    def test_late_or_reordered_benchmark(self):
        inputs,p=fixture()
        rs=p.rs
        late=snap(replace(rs.benchmark_rows[-1].selected,
                          verified_at_utc=inputs.as_of_utc))
        for rows in (rs.benchmark_rows[:-1]+(late,),rs.benchmark_rows[::-1]):
            _,safe=run(inputs,replace(p,rs=replace(rs,benchmark_rows=rows)))
            self.assertEqual(safe["phases"][0]["ingredient_state"],"BLOCKED")

    def test_invalid_and_stale_windows(self):
        inputs,p=fixture()
        for rs in (replace(p.rs,horizon=True),replace(p.rs,benchmark_kind="INDEX"),
                   replace(p.rs,benchmark_rows=p.rs.benchmark_rows[:-1])):
            _,safe=run(inputs,replace(p,rs=rs))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        _,safe=run(inputs,replace(p,rs=replace(p.rs,stock_start=9,stock_stop=14)))
        self.assertEqual(safe["phases"][0]["ingredient_state"],"BLOCKED")

    def test_redacted_legacy_no_authority(self):
        inputs,p=fixture()
        row,safe=run(inputs,p)
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("fixture-index","current_rs","candidate_min_slope",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
        row,_=run(inputs,replace(p,rs=None))
        self.assertIsNone(row.private_preview.assessments[0][1].rs)
