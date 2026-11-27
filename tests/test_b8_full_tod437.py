"""§437 selected TOD full strict B8 same-input fictional integration."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import PriceBasis, Timeframe
from test_b8_base415 import run
from test_b8_dual_basis434 import rekey
from test_b8_full_base436 import full_base, _replace_bucket
from test_b8_r0_band433 import bind as r0_band
from test_b8_tod420 import fixture as tod_fixture, VARIANT


def _raw(snapshot):
    return rekey(snapshot.selected,PriceBasis.RAW,"raw-stream")


def _pair(item,prefix):
    minutes=tuple(_raw(s) for s in prefix.minutes)
    witnesses=tuple(replace(w,candle=s.selected)
                    for w,s in zip(prefix.witnesses,minutes))
    return replace(item,snapshot=_raw(item.snapshot)),replace(prefix,minutes=minutes,
                                                               witnesses=witnesses)


def full_tod(tf=Timeframe.D1,strategy=Strategy.SHORT):
    inputs,p=full_base(tf,strategy)
    tod_inputs,tod_p=tod_fixture()
    tod=tod_p.early.tod
    target,prefix=_pair(tod.target,tod.target_prefix)
    prior=tuple(_pair(i,q) for i,q in zip(tod.prior_sessions,tod.prior_prefixes))
    tod=replace(tod,target=target,target_prefix=prefix,
                prior_sessions=tuple(i for i,_ in prior),
                prior_prefixes=tuple(q for _,q in prior))
    r0,rc=tuple(_raw(s) for s in tod_inputs.snapshots_for(Timeframe.M15)[20:22])
    rows=tuple(i.snapshot for i,_ in prior)+(r0,rc,target.snapshot)
    inputs=_replace_bucket(inputs,Timeframe.M15,rows)
    # Use one explicit fictional raw matched-share regime in both volume plans.
    v=p.rf.volume
    v=replace(v,witnesses=tuple(replace(w,share_regime_id="synthetic-regime") for w in v.witnesses))
    p=replace(p,target_index=20,early=replace(p.early,tod=tod,candidate_min_rvol_tod=D(2)),
              rf=replace(p.rf,volume=v))
    return inputs,r0_band(inputs,p)


class B8FullTOD437Tests(unittest.TestCase):
    def test_same_input_all_phases_both_frames_strategies(self):
        for tf in (Timeframe.H1,Timeframe.D1):
            for strategy in Strategy:
                with self.subTest(tf=tf,strategy=strategy):
                    inputs,p=full_tod(tf,strategy)
                    row,safe=run(inputs,p,strategy=strategy,variant=VARIANT)
                    proofs=[g for _,g in row.private_preview.assessments]
                    self.assertEqual([g.candidate_evidence_complete for g in proofs],[True]*4,
                                     [(g.state,g.reason,g.mandatory_gaps,
                                       g.rvol.reason if g.rvol else None) for g in proofs])
                    self.assertEqual([x["ingredient_state"] for x in safe["phases"]],
                                     ["GEOMETRY_MATCH_ONLY"]*4)
                    self.assertEqual(proofs[2].rvol.value,D(2))
                    self.assertTrue(proofs[2].tod_candidate_match)
                    self.assertEqual(proofs[3].rvol.value,D("2.5"))
                    self.assertEqual(proofs[3].portfolio.total_risk,D(150))

    def test_explicit_tod_threshold_failure_blocks_rf(self):
        inputs,p=full_tod()
        row,safe=run(inputs,replace(p,early=replace(p.early,candidate_min_rvol_tod=D("2.01"))),
                     variant=VARIANT)
        re,rf=[g for _,g in row.private_preview.assessments[-2:]]
        self.assertFalse(re.tod_candidate_match)
        self.assertFalse(re.candidate_evidence_complete)
        self.assertFalse(rf.candidate_evidence_complete)
        self.assertIsNone(rf.portfolio)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_late_tod_blocks_at_re_cutoff(self):
        inputs,p=full_tod()
        tod=p.early.tod
        target=replace(tod.target,cumulative_verified_utc=tod.target.cumulative_verified_utc+
                       timedelta(minutes=1))
        row,safe=run(inputs,replace(p,early=replace(p.early,tod=replace(tod,target=target))),
                     variant=VARIANT)
        self.assertEqual([x["ingredient_state"] for x in safe["phases"][2:]],["BLOCKED","BLOCKED"])
        self.assertFalse(row.private_preview.assessments[-1][1].candidate_evidence_complete)

    def test_missing_prefix_and_wrong_slot_binding(self):
        inputs,p=full_tod()
        tod=p.early.tod
        broken=replace(tod.target_prefix,minutes=tod.target_prefix.minutes[:-1])
        for changed in (replace(tod,target_prefix=broken),
                        replace(tod,target=tod.prior_sessions[-1])):
            _,safe=run(inputs,replace(p,early=replace(p.early,tod=changed)),variant=VARIANT)
            self.assertEqual([x["ingredient_state"] for x in safe["phases"][2:]],["BLOCKED","BLOCKED"])

    def test_no_implicit_tod_or_wrong_variant(self):
        inputs,p=full_tod()
        row,safe=run(inputs,replace(p,early=replace(p.early,tod=None)),variant=VARIANT)
        self.assertEqual(safe["phases"][2]["ingredient_state"],"MISSING_INPUT")
        self.assertFalse(row.private_preview.assessments[-1][1].candidate_evidence_complete)
        _,safe=run(inputs,p,variant="B8/BASE")
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_deterministic_redacted_nonactionable(self):
        inputs,p=full_tod()
        a,sa=run(inputs,p,variant=VARIANT)
        b,sb=run(inputs,p,variant=VARIANT)
        self.assertEqual(a.private_preview,b.private_preview)
        self.assertEqual(sa,sb)
        self.assertFalse(a.private_preview.action_eligible)
        self.assertEqual(sa["status"],"UNVERIFIED")
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in sa["phases"]))
        for secret in ("cumulative_matched_volume","prior_prefixes","synthetic-regime",
                       "mandatory_gaps","candidate_evidence_complete",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(sa))
