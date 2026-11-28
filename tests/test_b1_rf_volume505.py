"""§505 fictional exact RF matched D1 raw volume tests."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_indicators import VolumeBasis,VolumeBasisWitness,VolumeSessionClass
from swing_trading.b1_rf_volume505 import B1RFVolumePlan505,B1VolumePlan505
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.unified_mode459 import EngineMode
from test_b1_confirm504 import fixture as confirm_fixture,proof
from test_b1_decline499 import run
from test_causal_indicators import snap
from test_s2_rally449 import alter


def fixture(variant="B1/E_RECLAIM",*,volume=250,threshold=D("2.5")):
    inputs,g=confirm_fixture(variant)
    rows=inputs.snapshots_for(Timeframe.D1)
    i=g.target_index
    rows=rows[:i]+(snap(replace(rows[i].selected,volume=volume)),)+rows[i+1:]
    w=tuple(VolumeBasisWitness(s.selected,VolumeBasis.RAW_MATCHED_SHARES,"fixture-b1-regime",
                               "fixture-b1-witness-"+str(j),s.selected.verified_at_utc)
            for j,s in enumerate(rows[i-20:i+1]))
    return alter(inputs,Timeframe.D1,rows),B1VolumePlan505(g,B1RFVolumePlan505(
        "fixture-b1-policy",(VolumeSessionClass.DAILY,)*21,w,threshold))


class B1Volume505Tests(unittest.TestCase):
    def test_both_variants_and_strategies(self):
        for variant in ("B1/E_RECLAIM","B1/E_BOS_UP"):
            for strategy in Strategy:
                inputs,p=fixture(variant)
                g,s=proof(inputs,p,variant,strategy)
                self.assertIs(g.state,S1State439.MATCH)
                self.assertFalse(g.private_rvol.actionable)
                self.assertFalse(s["publication_allowed"])

    def test_threshold_and_no_default(self):
        for kw,state in ((dict(volume=1),S1State439.NONMATCH),(dict(threshold=None),S1State439.DISTANCE)):
            inputs,p=fixture(**kw)
            self.assertIs(proof(inputs,p)[0].state,state)

    def test_basis_scope_clock(self):
        inputs,p=fixture()
        v=p.volume
        w=v.witnesses[-1]
        for bad in (replace(w,basis=VolumeBasis.UNKNOWN),replace(w,candle=v.witnesses[0].candle),
                    replace(w,verified_at_utc=w.verified_at_utc+timedelta(seconds=1))):
            q=replace(p,volume=replace(v,witnesses=v.witnesses[:-1]+(bad,)))
            self.assertIs(proof(inputs,q)[0].state,S1State439.BLOCKED)

    def test_mismatched_session(self):
        inputs,p=fixture()
        v=p.volume
        q=replace(p,volume=replace(v,session_classes=v.session_classes[:-1]+(VolumeSessionClass.CLOSING_AUCTION,)))
        self.assertIs(proof(inputs,q)[0].state,S1State439.BLOCKED)

    def test_no_geometry_bypass_or_bad_config(self):
        inputs,p=fixture()
        self.assertIs(proof(inputs,replace(p,geometry=replace(p.geometry,candidate_epsilon=D(10))))[0].state,S1State439.NONMATCH)
        for v in (replace(p.volume,candidate_min_rvol=D(0)),replace(p.volume,witnesses=p.volume.witnesses[:-1])):
            r,_=run(inputs,replace(p,volume=v),variant="B1/E_RECLAIM")
            self.assertIsNone(r.private_preview)

    def test_shared_modes_redaction(self):
        inputs,p=fixture()
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            g,s=proof(inputs,p,mode=mode)
            self.assertIs(g.state,S1State439.MATCH)
            for key in ("private_rvol","fixture-b1-regime","fixture-b1-witness","fixture-b1-policy"):
                self.assertNotIn(key,json.dumps(s))
            self.assertFalse(s["production_qualified"])
