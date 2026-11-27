"""§455 S3 near structural target / ATR extension; fictional inputs."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s3_context454 import S3NearPlan455,S3State454
from test_s3_context454 import fixture,run,VARIANTS
from test_s2_rally449 import alter
from test_causal_indicators import make_bar,snap


def setup(tf=Timeframe.D1,close=D(20),k=D(0),extension=D(0)):
    inputs,p=fixture(tf)
    daily=inputs.snapshots_for(Timeframe.D1)
    anchor=inputs.snapshots_for(Timeframe.M15)[0]
    start=daily[0].market_bar_key.bar_start_utc
    prefix=tuple(snap(make_bar(3200+i,start=start-timedelta(days=6-i))) for i in range(6))
    inputs=alter(inputs,Timeframe.D1,prefix+daily)
    r=replace(p.resistance,start=6,stop=15) if tf is Timeframe.D1 else p.resistance
    p=replace(p,d1=replace(p.d1,start=6,stop=15),resistance=r,near=S3NearPlan455(1,0,15,k,extension))
    target=snap(make_bar(3300,timeframe=Timeframe.M15,
        start=anchor.market_bar_key.bar_start_utc+timedelta(minutes=20),
        high=max(D(20),close),low=D(8),close=close))
    return alter(inputs,Timeframe.M15,(anchor,target)),p


class S3Near455Tests(unittest.TestCase):
    def test_exact_boundary_both_frames_strategies_variants(self):
        for tf in (Timeframe.D1,Timeframe.W1):
            for strategy in Strategy:
                for variant in VARIANTS:
                    inputs,p=setup(tf)
                    row,safe=run(inputs,p,strategy,variant)
                    g=row.private_preview.assessments[1][1]
                    self.assertIs(g.state,S3State454.MATCH)
                    self.assertEqual(g.private_distance,D(0))
                    self.assertGreater(g.private_extension_atr,D(0))
                    self.assertEqual(safe["phases"][1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_far_above_nonrally_and_insufficient_extension(self):
        for close,k,e in ((D(19),D(0),D(0)),(D(21),D(1),D(0)),
                          (D(10),D(1),D(0)),(D(20),D(0),D(100))):
            inputs,p=setup(close=close,k=k,extension=e)
            row,_=run(inputs,p)
            self.assertIs(row.private_preview.assessments[1][1].state,S3State454.NONMATCH)

    def test_missing_target_and_late_prior(self):
        inputs,p=setup()
        rows=inputs.snapshots_for(Timeframe.M15)
        row,_=run(alter(inputs,Timeframe.M15,rows[:1]),p)
        self.assertIs(row.private_preview.assessments[1][1].state,S3State454.MISSING)
        late=snap(replace(rows[0].selected,verified_at_utc=rows[1].market_bar_key.bar_start_utc+timedelta(minutes=1)))
        row,_=run(alter(inputs,Timeframe.M15,(late,rows[1])),p)
        self.assertIs(row.private_preview.assessments[1][1].state,S3State454.BLOCKED)

    def test_stale_context_and_late_atr(self):
        inputs,p=setup()
        daily=inputs.snapshots_for(Timeframe.D1)
        cutoff=inputs.snapshots_for(Timeframe.M15)[0].market_bar_key.bar_start_utc
        new=snap(make_bar(3400,start=cutoff-timedelta(hours=6)+timedelta(minutes=1)))
        row,_=run(alter(inputs,Timeframe.D1,daily+(new,)),p)
        self.assertIs(row.private_preview.assessments[1][1].state,S3State454.BLOCKED)
        late=snap(replace(daily[0].selected,verified_at_utc=cutoff+timedelta(hours=1)))
        row,_=run(alter(inputs,Timeframe.D1,(late,)+daily[1:]),p)
        self.assertIs(row.private_preview.assessments[1][1].state,S3State454.BLOCKED)

    def test_unset_thresholds_and_invalid_configuration(self):
        for k,e in ((None,D(0)),(D(0),None)):
            inputs,p=setup(k=k,extension=e)
            row,_=run(inputs,p)
            self.assertIs(row.private_preview.assessments[1][1].state,S3State454.DISTANCE)
        inputs,p=setup()
        for bad in (True,D(-1),D("NaN")):
            for field in ("candidate_k_near","candidate_min_extension"):
                _,safe=run(inputs,replace(p,near=replace(p.near,**{field:bad})))
                self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_legacy_redaction_and_no_authority(self):
        inputs,p=setup()
        a,sa=run(inputs,p)
        b,sb=run(inputs,p)
        self.assertEqual(a.private_preview,b.private_preview)
        self.assertEqual(sa,sb)
        self.assertEqual(sa["status"],"UNVERIFIED")
        self.assertFalse(a.private_preview.action_eligible)
        for secret in ("private_atr","private_distance","private_extension_atr",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(sa))
        old,_=run(inputs,replace(p,near=None))
        self.assertEqual(len(old.private_preview.assessments),1)
