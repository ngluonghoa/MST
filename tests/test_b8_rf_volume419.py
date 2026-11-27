"""§419 B8 RF raw matched same-frame RVOL, fictional."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b6_rf_volume405 import B6RFVolumePlan389, B6H1VolumePlan394
from swing_trading.causal_indicators import VolumeBasis, VolumeBasisWitness, VolumeSessionClass
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from test_b8_rf418 import fixture as rf_fixture
from test_b8_base415 import run
from test_causal_indicators import make_bar, snap


def fixture(tf=Timeframe.H1, *, missing=False, low_volume=False, early_bad=False):
    inputs,p=rf_fixture(tf=tf,early_bad=early_bad)
    rows=inputs.snapshots_for(tf)
    first=rows[0].market_bar_key.bar_start_utc
    count=20-p.rf.breakout_index
    prefix=[]
    for i in range(count):
        begin=first-timedelta(days=count-i)
        bar=make_bar(1400+i,timeframe=tf,start=begin)
        if tf is Timeframe.H1:
            end=begin+timedelta(hours=1)
            rev=replace(bar.observation_revision,first_known_time_utc=end,
                        retrieved_at_utc=end+timedelta(minutes=1))
            bar=replace(bar,bar_end_utc=end,retrieved_at_utc=rev.retrieved_at_utc,
                        verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
        prefix.append(snap(bar))
    rows=tuple(prefix)+rows[:-1]+(snap(replace(rows[-1].selected,volume=50 if low_volume else 250)),)
    witnesses=tuple(VolumeBasisWitness(s.selected,VolumeBasis.RAW_MATCHED_SHARES,
                       "fixture-regime","fixture-evidence-"+str(i),s.selected.verified_at_utc)
                    for i,s in enumerate(rows))
    volume=(B6RFVolumePlan389("fixture-comparison",witnesses) if tf is Timeframe.D1 else
            B6H1VolumePlan394("fixture-comparison",(VolumeSessionClass.CONTINUOUS,)*21,witnesses))
    if tf is Timeframe.D1:
        p=replace(p,base_start=p.base_start+count,base_stop=p.base_stop+count,
                  atr_start=p.atr_start+count,atr_stop=p.atr_stop+count)
    if missing:
        rows=rows[1:]
        if tf is Timeframe.D1:
            p=replace(p,base_start=p.base_start-1,base_stop=p.base_stop-1,
                      atr_start=p.atr_start-1,atr_stop=p.atr_stop-1)
    inputs=replace(inputs,buckets=tuple((f,rows if f is tf else items) for f,items in inputs.buckets))
    return inputs,replace(p,rf=replace(p.rf,breakout_index=19 if missing else 20,volume=volume))


class B8RFVolume419Tests(unittest.TestCase):
    def test_both_frames_variants_strategies(self):
        for tf in (Timeframe.H1,Timeframe.D1):
            for strategy in Strategy:
                for variant in ("B8/BASE","B8/INTRADAY_RVOL_TOD_PENDING"):
                    data,p=fixture(tf)
                    row,safe=run(data,p,strategy=strategy,variant=variant)
                    proof=row.private_preview.assessments[-1][1]
                    self.assertEqual(proof.volume_state,"RVOL_COMPUTED_UNCALIBRATED")
                    self.assertEqual(proof.rvol.value,D("2.5"))
                    self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_low_volume_no_implicit_threshold(self):
        data,p=fixture(low_volume=True)
        row,_=run(data,p)
        self.assertEqual(row.private_preview.assessments[-1][1].rvol.value,D("0.5"))

    def test_exact_history_missing(self):
        for tf in (Timeframe.H1,Timeframe.D1):
            data,p=fixture(tf,missing=True)
            _,safe=run(data,p)
            self.assertEqual(safe["phases"][3]["ingredient_state"],"MISSING_INPUT")

    def test_wrong_witness_or_regime_blocks(self):
        data,p=fixture()
        v=p.rf.volume
        for w in (replace(v.witnesses[0],basis=VolumeBasis.UNKNOWN),
                  replace(v.witnesses[0],share_regime_id="different"),
                  replace(v.witnesses[0],verified_at_utc=v.witnesses[-1].verified_at_utc)):
            altered=replace(v,witnesses=(w,)+v.witnesses[1:])
            _,safe=run(data,replace(p,rf=replace(p.rf,volume=altered)))
            self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_wrong_frame_plan_and_legacy(self):
        data,p=fixture()
        v=p.rf.volume
        for bad in (B6RFVolumePlan389(v.comparison_policy_version,v.witnesses),
                    replace(v,witnesses=v.witnesses[:-1])):
            _,safe=run(data,replace(p,rf=replace(p.rf,volume=bad)))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        row,_=run(data,replace(p,rf=replace(p.rf,volume=None)))
        self.assertEqual(row.private_preview.assessments[-1][1].volume_state,"NOT_REQUESTED")

    def test_no_geometry_no_volume_authority_or_leak(self):
        data,p=fixture(early_bad=True)
        row,safe=run(data,p)
        self.assertIsNone(row.private_preview.assessments[-1][1].rvol)
        data,p=fixture()
        row,safe=run(data,p)
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("fixture-regime","fixture-evidence","rvol","volume_state",data.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
