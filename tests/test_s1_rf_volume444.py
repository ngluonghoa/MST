"""§444 separate fictional RF volume/close evidence."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_indicators import VolumeBasis,VolumeBasisWitness
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_rf_volume444 import S1RFVolumePlan444
from test_s1_confirm443 import fixture as structural,FAILED,CHOCH
from test_s1_context439 import run
from test_causal_indicators import snap


def fixture(tf=Timeframe.M15,context=Timeframe.D1,variant=FAILED,*,volume=215,open_price=D(10)):
    inputs,p=structural(tf,context,variant)
    daily=inputs.snapshots_for(Timeframe.D1)
    i=p.rf.target_index
    target=snap(replace(daily[i].selected,open=open_price,high=D(13),low=D(5),volume=volume))
    daily=daily[:i]+(target,)+daily[i+1:]
    inputs=replace(inputs,buckets=tuple((f,daily if f is Timeframe.D1 else s) for f,s in inputs.buckets))
    witnesses=tuple(VolumeBasisWitness(s.selected,VolumeBasis.RAW_MATCHED_SHARES,
                      "fixture-rf-regime","rf-"+str(j),s.selected.verified_at_utc)
                    for j,s in enumerate(daily[i-20:i+1]))
    return inputs,replace(p,rf=replace(p.rf,volume=S1RFVolumePlan444(
                          "fixture-rf-volume-v1",witnesses,D(2),D(".25"))))


class S1RFVolume444Tests(unittest.TestCase):
    def test_all_selected_branches_strategies_contexts_frames(self):
        for tf in (Timeframe.H1,Timeframe.M15):
            for context in (Timeframe.W1,Timeframe.D1):
                for strategy in Strategy:
                    for variant in (FAILED,CHOCH):
                        inputs,p=fixture(tf,context,variant)
                        row,safe=run(inputs,p,strategy,variant)
                        proof=row.private_preview.assessments[-1][1]
                        self.assertEqual((proof.rvol.value,proof.close_location),(D(2),D(".25")))
                        self.assertEqual([x["ingredient_state"] for x in safe["phases"]],
                                         ["GEOMETRY_MATCH_ONLY"]*4)

    def test_low_volume_nonbearish_or_weak_location_nonmatch(self):
        for kw in ({"volume":214},{"open_price":D(7)}):
            inputs,p=fixture(**kw)
            _,safe=run(inputs,p)
            self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")
        inputs,p=fixture()
        _,safe=run(inputs,replace(p,rf=replace(p.rf,volume=replace(
                    p.rf.volume,candidate_max_close_location=D(".24")))))
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_late_wrong_basis_and_rc_reuse_block(self):
        inputs,p=fixture()
        v=p.rf.volume
        w=v.witnesses[-1]
        for changed in (replace(w,basis=VolumeBasis.UNKNOWN),
                        replace(w,verified_at_utc=w.verified_at_utc+timedelta(seconds=1))):
            _,safe=run(inputs,replace(p,rf=replace(p.rf,volume=replace(v,witnesses=v.witnesses[:-1]+(changed,)))))
            self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")
        _,safe=run(inputs,replace(p,rf=replace(p.rf,volume=replace(v,witnesses=p.distribution.witnesses))))
        self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_no_default_and_validation(self):
        inputs,p=fixture()
        v=p.rf.volume
        _,safe=run(inputs,replace(p,rf=replace(p.rf,volume=replace(v,candidate_min_rvol=None))))
        self.assertEqual(safe["phases"][3]["ingredient_state"],"DISTANCE_ONLY")
        for changed in (replace(v,candidate_min_rvol=D(0)),replace(v,candidate_max_close_location=D(2)),
                        replace(v,witnesses=v.witnesses[:-1])):
            _,safe=run(inputs,replace(p,rf=replace(p.rf,volume=changed)))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_nonmatch_never_promoted_and_legacy(self):
        inputs,p=fixture()
        _,safe=run(inputs,replace(p,rf=replace(p.rf,candidate_epsilon=D(10))))
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")
        row,safe=run(inputs,replace(p,rf=replace(p.rf,volume=None)))
        self.assertIsNone(row.private_preview.assessments[-1][1].rvol)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_redaction_no_authority(self):
        inputs,p=fixture()
        row,safe=run(inputs,p)
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("rvol","close_location","fixture-rf-regime",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
