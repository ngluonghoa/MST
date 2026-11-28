"""§500 fictional two-bottom candidate regressions."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b1_bottom500 import B1BottomPlan500
from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.unified_mode459 import EngineMode
from test_b1_decline499 import fixture as decline_fixture,run,VARIANTS
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter


def fixture(*,second=D(6),threshold=D("0.2"),weekly_fall=True):
    inputs,p=decline_fixture(weekly_fall=weekly_fall)
    a=inputs.snapshots_for(Timeframe.M15)[0]
    start=a.selected.market_bar_key.bar_start_utc
    base=tuple(snap(make_bar(910+i,start=start+timedelta(days=i+1),
                low=D(6) if i==1 else second if i==7 else D(8))) for i in range(9))
    rows=inputs.snapshots_for(Timeframe.D1)+base
    anchor=snap(make_bar(950,timeframe=Timeframe.M15,start=start+timedelta(days=10)))
    inputs=alter(alter(inputs,Timeframe.D1,rows),Timeframe.M15,(a,anchor))
    return inputs,B1BottomPlan500(p,1,9,18,1,7,1,1,TiePolicy.STRICT_V1,0,16,threshold)


def proof(inputs,p,strategy=Strategy.SHORT,variant=VARIANTS[0],mode=EngineMode.RESEARCH):
    r,s=run(inputs,p,strategy,variant,mode)
    return r.private_preview.assessments[0][1],s


class B1Bottom500Tests(unittest.TestCase):
    def test_both_strategies_variants(self):
        for strategy in Strategy:
            for variant in VARIANTS:
                inputs,p=fixture()
                g,s=proof(inputs,p,strategy,variant)
                self.assertIs(g.state,S1State439.MATCH)
                self.assertEqual(g.private_support,D(6))
                self.assertFalse(s["publication_allowed"])

    def test_second_test_far_and_no_default(self):
        for kwargs,state in ((dict(second=D(4)),S1State439.NONMATCH),(dict(threshold=None),S1State439.DISTANCE)):
            inputs,p=fixture(**kwargs)
            self.assertIs(proof(inputs,p)[0].state,state)

    def test_no_decline_bypass(self):
        inputs,p=fixture(weekly_fall=False)
        g,_=proof(inputs,p)
        self.assertIs(g.state,S1State439.NONMATCH)
        self.assertFalse(hasattr(g,"private_support"))

    def test_missing_and_stale(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(Timeframe.D1)
        self.assertIs(proof(alter(inputs,Timeframe.D1,rows[:-1]),p)[0].state,S1State439.MISSING)
        self.assertIs(proof(inputs,replace(p,stop=17))[0].state,S1State439.BLOCKED)

    def test_late_witness_and_invalid_plan(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(Timeframe.D1)
        late=snap(replace(rows[11].selected,verified_at_utc=rows[16].selected.bar_end_utc))
        self.assertIs(proof(alter(inputs,Timeframe.D1,rows[:11]+(late,)+rows[12:]),p)[0].state,S1State439.BLOCKED)
        r,_=run(inputs,replace(p,atr_stop=17))
        self.assertIsNone(r.private_preview)

    def test_mode_redaction_and_no_authority(self):
        inputs,p=fixture()
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            g,s=proof(inputs,p,mode=mode)
            self.assertIs(g.state,S1State439.MATCH)
            for k in ("private_support","private_atr","private_decline"):
                self.assertNotIn(k,json.dumps(s))
            self.assertFalse(s["production_qualified"])
