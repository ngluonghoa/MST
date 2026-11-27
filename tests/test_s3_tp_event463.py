"""§463 synthetic closed TP events with exact private identity and mode parity."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s3_context454 import S3State454
from swing_trading.s3_tp_event463 import S3TPEvent463, S3TPEventPlan463
from swing_trading.unified_mode459 import EngineMode, evaluate_candidate
from test_s3_tp458 import fixture
from test_s3_context454 import run
from test_s2_rally449 import alter
from test_causal_indicators import make_bar,snap
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def setup(strategy=Strategy.SHORT,*,same=True,close=D(20)):
    inputs,p=fixture(strategy,close=D(20) if same else D(19),k=D(1))
    rows=inputs.snapshots_for(Timeframe.M15)
    if not same:
        target=snap(make_bar(3500,timeframe=Timeframe.M15,
            start=rows[-1].market_bar_key.bar_start_utc+timedelta(minutes=20),
            high=max(D(21),close),low=D(8),close=close))
        rows=rows+(target,)
        inputs=alter(inputs,Timeframe.M15,rows)
    bar=rows[-1].selected
    event=S3TPEvent463(len(rows)-1,p.target.plan_id,p.target.plan_version,
        bar.source_event_ids[0],bar.observation_revision.source_revision_or_payload_digest,
        bar.market_bar_key.bar_start_utc,bar.verified_at_utc,p.d1)
    return inputs,S3TPEventPlan463(p,event)


def early(inputs,p,strategy=Strategy.SHORT,variant="S3/E_TP"):
    r,s=run(inputs,p,strategy,variant)
    return r.private_preview.assessments[2][1],s


class S3TPEvent463Tests(unittest.TestCase):
    def test_same_or_later_closed_target_both_variants_and_strategies(self):
        for strategy in Strategy:
            for same in (True,False):
                inputs,p=setup(strategy,same=same)
                for variant in ("S3/E_TP","S3/F_TP"):
                    g,s=early(inputs,p,strategy,variant)
                    self.assertIs(g.state,S3State454.MATCH)
                    self.assertEqual(s["phases"][2]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_wick_only_does_not_establish_closed_attainment(self):
        inputs,p=setup(same=False,close=D(19))
        g,_=early(inputs,p)
        self.assertIs(g.state,S3State454.NONMATCH)

    def test_exact_event_identity_and_clock(self):
        inputs,p=setup()
        changes=(dict(plan_id="other"),dict(plan_version="other"),dict(source_event_id="other"),
                 dict(revision_digest="other"),dict(bar_start_utc=p.early.bar_start_utc+timedelta(seconds=1)),
                 dict(event_known_at_utc=p.early.event_known_at_utc-timedelta(seconds=1)),
                 dict(event_known_at_utc=inputs.as_of_utc+timedelta(seconds=1)))
        for change in changes:
            g,_=early(inputs,replace(p,early=replace(p.early,**change)))
            self.assertIs(g.state,S3State454.BLOCKED)

    def test_no_later_event_when_supplied_near_already_attained(self):
        inputs,p=setup(same=False)
        rows=inputs.snapshots_for(Timeframe.M15)
        near=snap(replace(rows[1].selected,close=D(20)))
        g,_=early(alter(inputs,Timeframe.M15,(rows[0],near,rows[2])),p)
        self.assertIs(g.state,S3State454.NONMATCH)

    def test_missing_and_no_early_phase_bypass(self):
        inputs,p=setup(same=False)
        rows=inputs.snapshots_for(Timeframe.M15)
        g,_=early(alter(inputs,Timeframe.M15,rows[:-1]),p)
        self.assertIs(g.state,S3State454.MISSING)
        p=replace(p,context=replace(p.context,near=replace(p.context.near,candidate_k_near=D(0))))
        g,_=early(inputs,p)
        self.assertIs(g.state,S3State454.BLOCKED)

    def test_same_mode_path_no_release_and_legacy_unchanged(self):
        inputs,p=setup()
        candidate=profile((request("S3",p,variant="S3/E_TP"),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(r.private_preview,"S3").private_preview.assessments[2][1].state,S3State454.MATCH)
            summary=r.safe_summary()
            self.assertFalse(summary["publication_allowed"])
            for private in (p.early.source_event_id,p.early.revision_digest,p.early.plan_id,"private_target_close"):
                self.assertNotIn(private,json.dumps(summary))
        old,s=run(inputs,p.context,variant="S3/E_TP")
        self.assertEqual(len(old.private_preview.assessments),2)
        self.assertEqual(s["phases"][2]["ingredient_state"],"NOT_REQUESTED")
