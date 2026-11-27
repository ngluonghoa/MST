"""§420 B8 raw-prefix TOD arithmetic, exact M15 binding, fictional."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b8_base_preview415 import B8TODPlan420
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from test_b8_rf418 import fixture as rf_fixture
from test_b8_base415 import run
from test_causal_indicators import make_bar, snap
from test_rvol_tod_contract import raw_prefix_fixture

VARIANT="B8/INTRADAY_RVOL_TOD_PENDING"


def fixture(*, late=False, bad_cross=False):
    inputs,p=rf_fixture()
    pairs=tuple(raw_prefix_fixture(i) for i in range(1,21))
    target,prefix=raw_prefix_fixture(21,multiplier=2)
    close=D(14) if bad_cross else D(17)
    def repriced(row):
        return replace(row,open=close,close=close,high=D(18),low=D(8))
    minutes=prefix.minutes[:-15]+tuple(snap(repriced(x.selected)) for x in prefix.minutes[-15:])
    witnesses=tuple(replace(w,candle=x.selected) for w,x in zip(prefix.witnesses,minutes))
    prefix=replace(prefix,minutes=minutes,witnesses=witnesses)
    slot=repriced(target.snapshot.selected)
    target=replace(target,snapshot=snap(slot))
    begin=slot.market_bar_key.bar_start_utc
    r0=snap(make_bar(1500,timeframe=Timeframe.M15,start=begin-timedelta(minutes=60)))
    rc=snap(make_bar(1501,timeframe=Timeframe.M15,start=begin-timedelta(minutes=30),
                     open_price=D(14),close=D(14),high=D(16),low=D(8)))
    if late:
        rf=inputs.snapshots_for(p.rf.timeframe)[p.rf.breakout_index].selected
        target=replace(target,cumulative_verified_utc=rf.bar_end_utc)
    priors=tuple(a for a,b in pairs)
    rows=tuple(x.snapshot for x in priors)+(r0,rc,target.snapshot)
    inputs=replace(inputs,buckets=tuple((f,rows if f is Timeframe.M15 else items)
                                       for f,items in inputs.buckets))
    tod=B8TODPlan420(target,priors,prefix,tuple(b for a,b in pairs))
    return inputs,replace(p,target_index=20,early=replace(p.early,tod=tod))


class B8TOD420Tests(unittest.TestCase):
    def test_raw_prefix_double_and_both_strategies(self):
        for strategy in Strategy:
            inputs,p=fixture()
            row,safe=run(inputs,p,strategy=strategy,variant=VARIANT)
            proof=row.private_preview.assessments[2][1]
            self.assertEqual(proof.volume_state,"TOD_COMPUTED_UNCALIBRATED")
            self.assertEqual(proof.rvol.value,D(2))
            self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_wrong_variant_and_explicit_plan(self):
        inputs,p=fixture()
        _,safe=run(inputs,p)
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        for tod in (replace(p.early.tod,prior_sessions=p.early.tod.prior_sessions[:-1]),True):
            _,safe=run(inputs,replace(p,early=replace(p.early,tod=tod)),variant=VARIANT)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_target_and_prior_exact_binding(self):
        inputs,p=fixture()
        tod=p.early.tod
        other=replace(tod.target,snapshot=tod.prior_sessions[-1].snapshot)
        wrong=replace(tod.prior_sessions[0],snapshot=snap(replace(
            tod.prior_sessions[0].snapshot.selected,volume=99)))
        for bad in (replace(tod,target=other),replace(tod,prior_sessions=(wrong,)+tod.prior_sessions[1:])):
            _,safe=run(inputs,replace(p,early=replace(p.early,tod=bad)),variant=VARIANT)
            self.assertEqual(safe["phases"][2]["ingredient_state"],"BLOCKED")
            self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_missing_raw_prefix_and_late_cumulative(self):
        inputs,p=fixture()
        tod=p.early.tod
        broken=replace(tod.target_prefix,minutes=tod.target_prefix.minutes[:-1])
        _,safe=run(inputs,replace(p,early=replace(p.early,tod=replace(tod,target_prefix=broken))),variant=VARIANT)
        self.assertEqual(safe["phases"][2]["ingredient_state"],"BLOCKED")
        inputs,p=fixture(late=True)
        _,safe=run(inputs,p,variant=VARIANT)
        self.assertEqual(safe["phases"][2]["ingredient_state"],"GEOMETRY_MATCH_ONLY")
        self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_geometry_nonmatch_and_legacy(self):
        inputs,p=fixture(bad_cross=True)
        row,safe=run(inputs,p,variant=VARIANT)
        self.assertIsNone(row.private_preview.assessments[2][1].rvol)
        self.assertEqual(safe["phases"][2]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")
        inputs,p=fixture()
        row,_=run(inputs,replace(p,early=replace(p.early,tod=None)),variant=VARIANT)
        self.assertEqual(row.private_preview.assessments[2][1].volume_state,"NOT_REQUESTED")

    def test_redacted_no_authority(self):
        inputs,p=fixture()
        row,safe=run(inputs,p,variant=VARIANT)
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("cumulative_matched_volume","prior_prefixes","rvol","synthetic-regime",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
