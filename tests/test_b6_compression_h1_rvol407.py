"""§407 compression H1 RF bound exact raw matched RVOL20."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b6_baseline_preview387 import B6H1VolumePlan394, B6State387
from swing_trading.causal_indicators import IndicatorState, VolumeBasis, VolumeBasisWitness, VolumeSessionClass
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import BaselineResolvedInputs
from test_b6_compression_h1_rf405 import data, config
from test_b6_compression_d1_rf404 import config as daily_config
from test_b6_compression_rc396 import run as evaluate
from test_causal_indicators import make_bar, snap


def fixture(*, price=D(113), late=False):
    base=data(price=price,late=late)
    pair=base.snapshots_for(Timeframe.H1)
    prior=pair[0].selected
    rows=[]
    for i in range(19):
        row=make_bar(300+i,timeframe=Timeframe.H1,
                     start=prior.market_bar_key.bar_start_utc-timedelta(hours=2*(19-i)),
                     open_price=D(109),close=D(109),high=D(110),low=D(108))
        obs=replace(row.observation_key,source_stream_id=prior.observation_key.source_stream_id)
        rows.append(snap(replace(row,observation_key=obs,
                    observation_revision=replace(row.observation_revision,observation_key=obs))))
    rows.extend((pair[0],snap(replace(pair[1].selected,volume=250))))
    return BaselineResolvedInputs(base.instrument_id,base.exchange,base.as_of_utc,False,
        tuple((tf,tuple(rows) if tf is Timeframe.H1 else bucket) for tf,bucket in base.buckets))


def volume_plan(data):
    rows=data.snapshots_for(Timeframe.H1)
    return B6H1VolumePlan394("fixture-h1-class-v1",(VolumeSessionClass.CONTINUOUS,)*21,
        tuple(VolumeBasisWitness(x.selected,VolumeBasis.RAW_MATCHED_SHARES,
                   "fixture-shares","fixture-witness-"+str(i),x.selected.verified_at_utc)
              for i,x in enumerate(rows)))


def run(data, vol=None, *, strategy=Strategy.SHORT,index=20):
    plan=config(index=index)
    return evaluate(data,replace(plan,rf=replace(plan.rf,volume=vol)),strategy=strategy)


class CompressionH1Volume407Tests(unittest.TestCase):
    def test_both_strategies_exact_h1_rvol(self):
        data=fixture()
        for strategy in Strategy:
            row,safe=run(data,volume_plan(data),strategy=strategy)
            rf=row.private_preview.assessments[-1][1]
            self.assertIs(rf.state,B6State387.MATCH)
            self.assertEqual(rf.volume_state,"RVOL_COMPUTED_UNCALIBRATED")
            self.assertEqual(rf.rvol.value,D("2.5"))
            self.assertFalse(rf.rvol.actionable)
            self.assertFalse(rf.rvol.data_certified)
            self.assertEqual(safe["status"],"UNVERIFIED")

    def test_missing_exact_window_or_plan(self):
        data=fixture()
        vol=volume_plan(data)
        for index in (19,21):
            row,_=run(data,vol,index=index)
            self.assertEqual(row.private_preview.assessments[-1][1].volume_state,
                             "EXACT_TARGET_OR_PRIOR20_MISSING")
        row,_=run(data)
        self.assertEqual(row.private_preview.assessments[-1][1].volume_state,"H1_VOLUME_SPEC_PENDING")

    def test_session_mismatch_and_daily_class_block(self):
        data=fixture()
        vol=volume_plan(data)
        for classes in ((VolumeSessionClass.DAILY,)*21,
                         vol.session_classes[:-1]+(VolumeSessionClass.CLOSING_AUCTION,)):
            row,_=run(data,replace(vol,session_classes=classes))
            rf=row.private_preview.assessments[-1][1]
            self.assertIs(rf.state,B6State387.MATCH)
            self.assertIs(rf.rvol.state,IndicatorState.BLOCKED)

    def test_wrong_basis_wrong_row_and_late_prior_witness(self):
        data=fixture()
        vol=volume_plan(data)
        target=vol.witnesses[-1]
        for bad in (replace(target,basis=VolumeBasis.ADJUSTED_SHARES),
                    replace(target,candle=vol.witnesses[0].candle)):
            row,_=run(data,replace(vol,witnesses=vol.witnesses[:-1]+(bad,)))
            self.assertEqual(row.private_preview.assessments[-1][1].volume_state,"RVOL_BLOCKED")
        prior=replace(vol.witnesses[-2],verified_at_utc=target.verified_at_utc)
        row,_=run(data,replace(vol,witnesses=vol.witnesses[:-2]+(prior,target)))
        self.assertEqual(row.private_preview.assessments[-1][1].volume_state,"RVOL_BLOCKED")

    def test_geometry_and_volume_independent(self):
        for data in (fixture(price=D(110)),fixture(late=True)):
            row,_=run(data,volume_plan(data))
            rf=row.private_preview.assessments[-1][1]
            self.assertIn(rf.state,(B6State387.NONMATCH,B6State387.BLOCKED))
            self.assertEqual(rf.volume_state,"RVOL_COMPUTED_UNCALIBRATED")

    def test_invalid_plan_no_d1_fallback_and_redaction(self):
        data=fixture()
        vol=volume_plan(data)
        for bad in (replace(vol,session_classes=vol.session_classes[:-1]),
                    replace(vol,comparison_policy_version=""),daily_config().rf):
            _,safe=run(data,bad)
            self.assertTrue(all(p["ingredient_state"]=="CONFIG_REJECTED" for p in safe["phases"]))
        row,_=run(data,vol)
        safe=row.private_preview.safe_rf_volume_summary()
        self.assertFalse(safe["volume_approved"])
        for forbidden in (data.instrument_id,"2.5","fixture-witness","session_classes"):
            self.assertNotIn(forbidden,json.dumps(safe))
