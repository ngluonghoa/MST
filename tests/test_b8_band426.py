"""§426 explicit raw session grid candidate, fictional."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b8_price_band426 import B8PriceBand426
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from test_b8_rf418 import fixture
from test_b8_base415 import run
from test_b8_entry_cap425 import combined
from test_b8_rs421 import adjusted


def bind(inputs,p,**kwargs):
    target=inputs.snapshots_for(p.rf.timeframe)[p.rf.breakout_index].selected
    k=target.market_bar_key
    b=B8PriceBand426(k.instrument_id,k.exchange,k.calendar_version,k.session_period_id,
                     "fixture-policy",k.bar_start_utc,D(7),D(30),D(1))
    return replace(p,rf=replace(p.rf,band=replace(b,**kwargs)))


class B8Band426Tests(unittest.TestCase):
    def test_raw_grid_both_frames_strategies_variants(self):
        for tf in (Timeframe.H1,Timeframe.D1):
            for strategy in Strategy:
                for variant in ("B8/BASE","B8/INTRADAY_RVOL_TOD_PENDING"):
                    inputs,p=fixture(tf=tf)
                    row,safe=run(inputs,bind(inputs,combined(p)),strategy=strategy,variant=variant)
                    proof=row.private_preview.assessments[-1][1].band
                    self.assertEqual(proof.grid_entry_ceiling,D(17))
                    self.assertTrue(proof.candidate_match)
                    self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_band_only_and_no_default(self):
        inputs,p=fixture()
        row,_=run(inputs,bind(inputs,p))
        self.assertIsNone(row.private_preview.assessments[-1][1].band.grid_entry_ceiling)
        row,_=run(inputs,p)
        self.assertIsNone(row.private_preview.assessments[-1][1].band)

    def test_wrong_scope_late_and_adjusted(self):
        inputs,p=fixture()
        for kw in ({"instrument_id":"other"},{"session_period_id":"other"},
                   {"calendar_version":"other"},{"known_at_utc":inputs.as_of_utc}):
            _,safe=run(inputs,bind(inputs,p,**kw))
            self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")
        adjusted_inputs=replace(inputs,buckets=tuple((f,tuple(adjusted(s.selected) for s in rows))
                                                   for f,rows in inputs.buckets))
        _,safe=run(adjusted_inputs,bind(adjusted_inputs,p))
        self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_ohlc_grid_and_band_mismatch(self):
        inputs,p=fixture()
        for kw in ({"upper":D(16)},{"lower":D(6),"tick":D(2)}):
            _,safe=run(inputs,bind(inputs,p,**kw))
            self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_no_grid_price_or_invalid_plan(self):
        inputs,p=fixture()
        p=bind(inputs,combined(p,k=D(0)))
        row,safe=run(inputs,p)
        self.assertFalse(row.private_preview.assessments[-1][1].band.candidate_match)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")
        for kw in ({"tick":D(0)},{"lower":D(31)},{"policy_version":""}):
            _,safe=run(inputs,bind(inputs,p,**kw))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_redacted_no_authority(self):
        inputs,p=fixture()
        row,safe=run(inputs,bind(inputs,combined(p)))
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("grid_entry_ceiling","fixture-policy",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
