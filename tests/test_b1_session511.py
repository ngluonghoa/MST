"""§511 fictional later raw D1 session grid regressions."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b1_session511 import B1SessionPlan511
from swing_trading.b8_price_band426 import B8PriceBand426
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.unified_mode459 import EngineMode
from test_b1_entry510 import fixture as entry_fixture
from test_b1_major508 import MAJOR
from test_b1_market506 import proof
from test_b1_decline499 import run
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter


def fixture(early="B1/E_RECLAIM",major=False,*,close=D(21),low=D(19)):
    inputs,p=entry_fixture(early,major)
    rows=inputs.snapshots_for(Timeframe.D1)
    ref=inputs.snapshots_for(Timeframe.W1)[-1].selected if major else rows[-1].selected
    r=make_bar(1800,start=ref.verified_at_utc+timedelta(hours=1),
        open_price=D(20),high=max(D(24),close),low=low,close=close)
    k=r.market_bar_key
    band=B8PriceBand426(k.instrument_id,k.exchange,k.calendar_version,k.session_period_id,
        "fictional-band",k.bar_start_utc,D(1),D(100),D(1))
    return alter(inputs,Timeframe.D1,rows+(snap(r),)),B1SessionPlan511(p,len(rows),band)


class B1Session511Tests(unittest.TestCase):
    def test_all_variants_and_strategies(self):
        for early in ("B1/E_RECLAIM","B1/E_BOS_UP"):
            for major in (False,True):
                for strategy in Strategy:
                    inputs,p=fixture(early,major)
                    a,s=proof(inputs,p,MAJOR if major else early,strategy)
                    r=a[-1][1]
                    self.assertIs(r.state,S1State439.MATCH)
                    self.assertEqual(r.private_risk.private_reference,D(21))
                    self.assertFalse(s["publication_allowed"])

    def test_grid_and_max_entry(self):
        for close,state in ((D(21),S1State439.MATCH),(D(35),S1State439.NONMATCH),(D("21.5"),S1State439.BLOCKED)):
            inputs,p=fixture(close=close)
            self.assertIs(proof(inputs,p)[0][-1][1].state,state)

    def test_missing_and_signal_bar(self):
        inputs,p=fixture()
        self.assertIs(proof(inputs,replace(p,target_index=p.target_index+1))[0][-1][1].state,S1State439.MISSING)
        self.assertIs(proof(inputs,replace(p,target_index=p.target_index-1))[0][-1][1].state,S1State439.BLOCKED)

    def test_stop_touch_and_session_identity(self):
        inputs,p=fixture(low=D(1))
        self.assertIs(proof(inputs,p)[0][-1][1].state,S1State439.NONMATCH)
        inputs,p=fixture()
        q=replace(p,band=replace(p.band,session_period_id="wrong"))
        self.assertIs(proof(inputs,q)[0][-1][1].state,S1State439.BLOCKED)

    def test_late_band_and_bad_index(self):
        inputs,p=fixture()
        q=replace(p,band=replace(p.band,known_at_utc=inputs.as_of_utc+timedelta(seconds=1)))
        self.assertIs(proof(inputs,q)[0][-1][1].state,S1State439.BLOCKED)
        r,_=run(inputs,replace(p,target_index=True))
        self.assertIsNone(r.private_preview)

    def test_modes_and_redaction(self):
        inputs,p=fixture()
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            a,s=proof(inputs,p,mode=mode)
            self.assertIs(a[-1][1].state,S1State439.MATCH)
            self.assertFalse(s["production_qualified"])
            self.assertNotIn("private_candidate",json.dumps(s))
