"""§438 full strict H1-base B8 matrix, fictional only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import PriceBasis, Timeframe
from test_b8_base415 import fixture as base_fixture, run
from test_b8_dual_basis434 import rekey
from test_b8_full_base436 import full_base, _replace_bucket
from test_b8_full_tod437 import full_tod, VARIANT
from test_causal_indicators import snap


def full_h1_base(tf=Timeframe.D1,strategy=Strategy.SHORT,variant="B8/BASE"):
    inputs,p=(full_tod(tf,strategy) if variant==VARIANT else full_base(tf,strategy))
    b,bp=base_fixture(Timeframe.H1)
    history=tuple(rekey(s.selected,PriceBasis.RAW,"raw-stream")
                  for s in b.snapshots_for(Timeframe.H1))
    if tf is Timeframe.H1:
        h1=inputs.snapshots_for(Timeframe.H1)
        start=p.rf.breakout_index-1-len(history)
        rows=h1[:start]+history+h1[p.rf.breakout_index-1:]
        volume=p.rf.volume
        witnesses=tuple(replace(w,candle=s.selected,verified_at_utc=s.selected.verified_at_utc)
                        for w,s in zip(volume.witnesses,rows))
        p=replace(p,rf=replace(p.rf,volume=replace(volume,witnesses=witnesses)))
    else:
        rows=history
        start=0
    inputs=_replace_bucket(inputs,Timeframe.H1,rows)
    return inputs,replace(p,timeframe=Timeframe.H1,base_start=start,
                          base_stop=start+len(history),pivot_index=bp.pivot_index)


class B8FullH1Base438Tests(unittest.TestCase):
    def test_full_matrix_all_evidence_complete(self):
        for tf in (Timeframe.H1,Timeframe.D1):
            for strategy in Strategy:
                for variant in ("B8/BASE",VARIANT):
                    with self.subTest(tf=tf,strategy=strategy,variant=variant):
                        inputs,p=full_h1_base(tf,strategy,variant)
                        row,safe=run(inputs,p,strategy=strategy,variant=variant)
                        proofs=[g for _,g in row.private_preview.assessments]
                        self.assertEqual([g.candidate_evidence_complete for g in proofs],[True]*4,
                                         [(g.state,g.reason,g.mandatory_gaps) for g in proofs])
                        self.assertIs(row.private_preview.assessments[0][0].selected_frame,Timeframe.H1)
                        self.assertIs(row.private_preview.assessments[-1][0].selected_frame,tf)
                        self.assertEqual([x["ingredient_state"] for x in safe["phases"]],
                                         ["GEOMETRY_MATCH_ONLY"]*4)
                        self.assertEqual((proofs[-1].risk.stop,proofs[-1].risk.target,
                                          proofs[-1].portfolio.total_risk),(D(8),D(22),D(140)))
                        self.assertEqual(proofs[-1].rvol.value,D("2.5"))
                        if variant==VARIANT:
                            self.assertEqual(proofs[2].rvol.value,D(2))

    def test_no_substitution_when_h1_base_missing(self):
        inputs,p=full_h1_base()
        inputs=_replace_bucket(inputs,Timeframe.H1,())
        row,safe=run(inputs,p)
        self.assertEqual(safe["phases"][0]["ingredient_state"],"MISSING_INPUT")
        self.assertFalse(row.private_preview.assessments[-1][1].candidate_evidence_complete)

    def test_late_h1_pivot_right_bar_blocks_chain(self):
        inputs,p=full_h1_base(Timeframe.H1)
        h1=inputs.snapshots_for(Timeframe.H1)
        i=p.base_start+p.pivot_index+1
        cutoff=inputs.snapshots_for(Timeframe.M15)[p.target_index].market_bar_key.bar_start_utc
        changed=snap(replace(h1[i].selected,verified_at_utc=cutoff+timedelta(seconds=1)))
        inputs=_replace_bucket(inputs,Timeframe.H1,h1[:i]+(changed,)+h1[i+1:])
        row,safe=run(inputs,p)
        self.assertEqual(safe["phases"][0]["ingredient_state"],"BLOCKED")
        self.assertFalse(row.private_preview.assessments[-1][1].candidate_evidence_complete)

    def test_rr_uses_h1_floor_not_daily_floor(self):
        inputs,p=full_h1_base()
        p=replace(p,rf=replace(p.rf,risk=replace(p.rf.risk,candidate_min_net_rr=D(".6"))))
        row,safe=run(inputs,p)
        rf=row.private_preview.assessments[-1][1]
        self.assertEqual((rf.risk.stop,rf.risk.target),(D(8),D(22)))
        self.assertFalse(rf.risk.candidate_match)
        self.assertFalse(rf.candidate_evidence_complete)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_explicit_selected_frame_not_implicit_fallback(self):
        inputs,p=full_h1_base()
        p=replace(p,timeframe=Timeframe.M15)
        _,safe=run(inputs,p)
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_tod_deterministic_redacted_nonactionable(self):
        inputs,p=full_h1_base(Timeframe.H1,Strategy.SWING,VARIANT)
        a,sa=run(inputs,p,strategy=Strategy.SWING,variant=VARIANT)
        b,sb=run(inputs,p,strategy=Strategy.SWING,variant=VARIANT)
        self.assertEqual(a.private_preview,b.private_preview)
        self.assertEqual(sa,sb)
        self.assertFalse(a.private_preview.action_eligible)
        self.assertEqual(sa["status"],"UNVERIFIED")
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in sa["phases"]))
        for secret in ("candidate_evidence_complete","mandatory_gaps","raw-stream",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(sa))
