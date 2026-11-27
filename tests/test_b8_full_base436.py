"""§436 B8 strict BASE single-input fictional integration."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b6_rf_volume405 import B6RFVolumePlan389, B6H1VolumePlan394
from swing_trading.causal_indicators import VolumeBasis, VolumeBasisWitness, VolumeSessionClass
from swing_trading.contracts import Strategy
from swing_trading.market_data import PriceBasis, Timeframe
from test_b8_base415 import run
from test_b8_dual_basis434 import model, rekey
from test_b8_entry_cap425 import combined
from test_b8_r0_band433 import bind as r0_band
from test_b8_band426 import bind as rf_band
from test_b8_settlement427 import bind as settlement
from test_b8_liquidity428 import bind as liquidity
from test_b8_portfolio429 import bind as portfolio
from test_causal_indicators import make_bar, snap


def _prefix(tf, first, count):
    rows=[]
    for i in range(count):
        begin=first-timedelta(days=count-i)
        bar=make_bar(1700+i,timeframe=tf,start=begin)
        if tf is Timeframe.H1:
            end=begin+timedelta(hours=1)
            rev=replace(bar.observation_revision,first_known_time_utc=end,
                        retrieved_at_utc=end+timedelta(minutes=1))
            bar=replace(bar,bar_end_utc=end,retrieved_at_utc=rev.retrieved_at_utc,
                        verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
        rows.append(rekey(bar,PriceBasis.RAW,"raw-stream"))
    return tuple(rows)


def _replace_bucket(inputs,tf,rows):
    return replace(inputs,buckets=tuple((f,rows if f is tf else old)
                                       for f,old in inputs.buckets))


def _shift_rs(rs,count):
    return replace(rs,stock_start=rs.stock_start+count,stock_stop=rs.stock_stop+count)


def full_base(tf=Timeframe.D1,strategy=Strategy.SHORT):
    inputs,p=model(tf)
    rows=inputs.snapshots_for(tf)
    count=20-p.rf.breakout_index
    prefix=_prefix(tf,rows[0].market_bar_key.bar_start_utc,count)
    inputs=_replace_bucket(inputs,tf,prefix+rows)
    if tf is Timeframe.D1:
        adj=tuple(rekey(x.selected,PriceBasis.ADJUSTED,"adjusted-stream") for x in prefix)
        p=replace(p,base_start=p.base_start+count,base_stop=p.base_stop+count,
                  atr_start=p.atr_start+count,atr_stop=p.atr_stop+count,
                  rs=_shift_rs(p.rs,count),
                  rs_stock=replace(p.rs_stock,adjusted_daily=adj+p.rs_stock.adjusted_daily),
                  rf=replace(p.rf,rs=_shift_rs(p.rf.rs,count)))
    p=replace(p,rf=replace(p.rf,breakout_index=20))
    inputs,p=liquidity(inputs,combined(p),strategy)
    rows=inputs.snapshots_for(tf)
    rows=rows[:-1]+(snap(replace(rows[-1].selected,volume=250)),)
    inputs=_replace_bucket(inputs,tf,rows)
    witnesses=tuple(VolumeBasisWitness(s.selected,VolumeBasis.RAW_MATCHED_SHARES,
                         "fixture-regime","fixture-evidence-"+str(i),s.selected.verified_at_utc)
                    for i,s in enumerate(rows))
    volume=(B6RFVolumePlan389("fixture-comparison",witnesses) if tf is Timeframe.D1 else
            B6H1VolumePlan394("fixture-comparison",(VolumeSessionClass.CONTINUOUS,)*21,witnesses))
    p=replace(p,rf=replace(p.rf,volume=volume,candidate_min_rvol=D("2.5")),
              strict_candidate_evidence=True)
    p=portfolio(inputs,settlement(inputs,rf_band(inputs,r0_band(inputs,p)),strategy),strategy)
    return inputs,p


class B8FullBase436Tests(unittest.TestCase):
    def test_single_input_all_phases_both_frames_strategies(self):
        for tf in (Timeframe.H1,Timeframe.D1):
            for strategy in Strategy:
                with self.subTest(tf=tf,strategy=strategy):
                    inputs,p=full_base(tf,strategy)
                    row,safe=run(inputs,p,strategy=strategy)
                    proofs=[g for _,g in row.private_preview.assessments]
                    self.assertEqual([g.candidate_evidence_complete for g in proofs],[True]*4,
                                     [(g.state,g.reason,g.mandatory_gaps) for g in proofs])
                    self.assertTrue(all(not g.mandatory_gaps for g in proofs))
                    self.assertEqual([x["ingredient_state"] for x in safe["phases"]],
                                     ["GEOMETRY_MATCH_ONLY"]*4)
                    rf=proofs[-1]
                    self.assertEqual(rf.rvol.value,D("2.5"))
                    self.assertEqual(rf.band.grid_entry_ceiling,D(17))
                    self.assertEqual(rf.liquidity.volume_fraction,D(".1"))
                    self.assertEqual(rf.portfolio.cash_required,D(170))
                    self.assertEqual(rf.portfolio.total_risk,D(150))
                    self.assertTrue(rf.settlement.candidate_match)

    def test_missing_final_evidence_is_not_complete(self):
        inputs,p=full_base()
        row,safe=run(inputs,replace(p,rf=replace(p.rf,portfolio=None)))
        proof=row.private_preview.assessments[-1][1]
        self.assertFalse(proof.candidate_evidence_complete)
        self.assertIn("RF_PORTFOLIO_SCENARIO",proof.mandatory_gaps)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"MISSING_INPUT")

    def test_threshold_nonmatch_not_promoted(self):
        inputs,p=full_base()
        row,safe=run(inputs,replace(p,rf=replace(p.rf,candidate_min_rvol=D("2.6"))))
        proof=row.private_preview.assessments[-1][1]
        self.assertFalse(proof.candidate_evidence_complete)
        self.assertFalse(proof.rvol_candidate_match)
        self.assertIsNone(proof.portfolio)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_mismatched_raw_witness_blocks_full_chain(self):
        inputs,p=full_base(Timeframe.H1)
        v=p.rf.volume
        v=replace(v,witnesses=(replace(v.witnesses[0],basis=VolumeBasis.UNKNOWN),)+v.witnesses[1:])
        row,safe=run(inputs,replace(p,rf=replace(p.rf,volume=v)))
        self.assertFalse(row.private_preview.assessments[-1][1].candidate_evidence_complete)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_selected_tod_not_implicitly_satisfied(self):
        inputs,p=full_base()
        row,safe=run(inputs,p,variant="B8/INTRADAY_RVOL_TOD_PENDING")
        self.assertEqual(safe["phases"][2]["ingredient_state"],"MISSING_INPUT")
        self.assertFalse(row.private_preview.assessments[-1][1].candidate_evidence_complete)

    def test_deterministic_and_no_authority_or_leakage(self):
        inputs,p=full_base()
        a,sa=run(inputs,p)
        b,sb=run(inputs,p)
        self.assertEqual(a.private_preview,b.private_preview)
        self.assertEqual(sa,sb)
        self.assertFalse(a.private_preview.action_eligible)
        self.assertEqual(sa["status"],"UNVERIFIED")
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in sa["phases"]))
        for secret in ("mandatory_gaps","candidate_evidence_complete","fixture-regime",
                       "cash_required","raw-stream",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(sa))
