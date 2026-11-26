"""Fictional source-contract tests, never market/source qualification."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import unittest

from swing_trading.contracts import DecisionStatus, Strategy
from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.market_data import Timeframe
from swing_trading.source_quality import resolve_as_known
from swing_trading.s7_retest_evidence import (
    inspect_s7_retest_evidence, inspect_s7_early_evidence, S7EarlyMode,
    inspect_s7_confirmation_evidence,
)
from test_causal_indicators import AS_OF, START, make_bar, snap, d1


def inputs():
    hist = tuple(snap(make_bar(i+25, low=D(low), close=D(close),
                               open_price=D(close)))
                 for i,(low,close) in enumerate(
                     [("7","9"),("6","9"),("3","5"),("5","8"),
                      ("4","4"),("1","1")]))
    start = START+timedelta(days=31)
    prior = snap(make_bar(100,timeframe=Timeframe.M15,start=start,
                          open_price=D("2"),low=D("1"),close=D("2")))
    retest = snap(make_bar(101,timeframe=Timeframe.M15,
                           start=start+timedelta(minutes=30),
                           open_price=D("2"),low=D("2"),close=D("3")))
    return dict(pivot_history=hist[:4],pivot_index=2,left_count=1,right_count=1,
                tie_policy=TiePolicy.STRICT_V1,previous=hist[4],breakdown=hist[5],
                prior_retest=prior,retest=retest,atr_d1_history=d1(),
                retest_atr_d1_history=d1(),candidate_epsilon=D(".25"),
                strategy=Strategy.SHORT,as_of_utc=AS_OF)


class S7RetestEvidenceTests(unittest.TestCase):
    def test_exact_pivot_and_origin_remain_unverified(self):
        p = inputs()
        r = inspect_s7_retest_evidence(**p)
        self.assertEqual(r.reason,"EXACT_PIVOT_GEOMETRY_UNCALIBRATED")
        self.assertEqual(r.close_distance_atr,D("0"))
        self.assertEqual(r.range_distance_atr,D("0"))
        self.assertIs(r.status,DecisionStatus.UNVERIFIED)
        self.assertFalse(r.action_eligible)
        self.assertEqual(r,inspect_s7_retest_evidence(**p))
        p["strategy"]=Strategy.SWING
        self.assertEqual(r.origin_preview_id,inspect_s7_retest_evidence(**p).origin_preview_id)

    def test_no_prior_breakdown_no_geometry(self):
        p = inputs()
        p["breakdown"]=snap(replace(p["breakdown"].selected,close=D("3")))
        r=inspect_s7_retest_evidence(**p)
        self.assertEqual(r.reason,"NO_CAUSAL_LOW_PIVOT_CROSS")
        self.assertIsNone(r.origin_preview_id)

    def test_approach_from_above_rejected(self):
        p=inputs()
        p["prior_retest"]=snap(replace(p["prior_retest"].selected,close=D("4")))
        self.assertEqual(inspect_s7_retest_evidence(**p).reason,"NO_APPROACH_FROM_BELOW")

    def test_missing_atr_and_missing_epsilon(self):
        p=inputs()
        self.assertEqual(inspect_s7_retest_evidence(**dict(p,retest_atr_d1_history=())).reason,
                         "RETEST_ATR_UNAVAILABLE")
        self.assertEqual(inspect_s7_retest_evidence(**dict(p,candidate_epsilon=None)).reason,
                         "NO_CAUSAL_LOW_PIVOT_CROSS")

    def test_future_retest_blocked(self):
        p=inputs()
        p["as_of_utc"]=p["retest"].selected.bar_end_utc
        self.assertEqual(inspect_s7_retest_evidence(**p).reason,"SOURCE_OR_ASOF_UNVERIFIED")

    def test_distinct_observation_changes_evidence_not_origin(self):
        p=inputs()
        a=inspect_s7_retest_evidence(**p)
        p["retest"]=snap(replace(p["retest"].selected,close=D("4")))
        b=inspect_s7_retest_evidence(**p)
        self.assertEqual(a.origin_preview_id,b.origin_preview_id)
        self.assertNotEqual(a.retest_preview_id,b.retest_preview_id)
        self.assertTrue(b.close_above_pivot)
        self.assertEqual(b.close_distance_atr,D(".25"))

    def test_authority_forgery_rejected(self):
        r=inspect_s7_retest_evidence(**inputs())
        for key in ("action_eligible","parameter_approved","detector_approved"):
            for value in (True,0,None):
                with self.assertRaises(ValueError):
                    replace(r,**{key:value})


class S7EarlyEvidenceTests(unittest.TestCase):
    def touch(self, **changes):
        p = inputs()
        p["retest"] = snap(replace(p["retest"].selected, close=D("2.5"), **changes))
        return p

    def later(self):
        p = inputs()
        p["retest"] = snap(replace(p["retest"].selected, close=D("4")))
        start = p["retest"].selected.market_bar_key.bar_start_utc+timedelta(minutes=30)
        c = snap(make_bar(102,timeframe=Timeframe.M15,start=start,
                          open_price=D("4"),low=D("2"),close=D("2.5")))
        return p,c

    def test_touch_reject_geometry_and_exact_base_link(self):
        for strategy in (Strategy.SHORT, Strategy.SWING):
            p = dict(self.touch(),strategy=strategy)
            r = inspect_s7_early_evidence(mode=S7EarlyMode.TOUCH_CLOSE_BELOW,**p)
            base = inspect_s7_retest_evidence(**p)
            self.assertTrue(r.shape_observed)
            self.assertEqual(r.origin_preview_id,base.origin_preview_id)
            self.assertEqual(r.retest_preview_id,base.retest_preview_id)
            self.assertIs(r.status,DecisionStatus.UNVERIFIED)
            self.assertFalse(r.action_eligible)
            self.assertEqual(r,inspect_s7_early_evidence(mode=r.mode,**p))

    def test_touch_missing_and_equal_close_are_not_rejection(self):
        for p in (self.touch(high=D("2.9")),inputs()):
            r=inspect_s7_early_evidence(mode=S7EarlyMode.TOUCH_CLOSE_BELOW,**p)
            self.assertIs(r.shape_observed,False)
            self.assertIs(r.status,DecisionStatus.UNVERIFIED)

    def test_later_return_requires_strict_above_then_below(self):
        p,c=self.later()
        r=inspect_s7_early_evidence(mode=S7EarlyMode.LATER_CLOSE_BELOW,followup=c,**p)
        self.assertTrue(r.shape_observed)
        self.assertEqual(r.witness_known_at_utc,c.selected.verified_at_utc)
        c2=snap(replace(c.selected,close=D("3")))
        r2=inspect_s7_early_evidence(mode=r.mode,followup=c2,**p)
        self.assertFalse(r2.shape_observed)
        self.assertEqual(r.origin_preview_id,r2.origin_preview_id)
        self.assertNotEqual(r.early_preview_id,r2.early_preview_id)

    def test_explicit_modes_no_fallback(self):
        p,c=self.later()
        self.assertEqual(inspect_s7_early_evidence(mode=S7EarlyMode.LATER_CLOSE_BELOW,**p).reason,
                         "MISSING_FOLLOWUP")
        self.assertEqual(inspect_s7_early_evidence(mode=S7EarlyMode.TOUCH_CLOSE_BELOW,followup=c,**p).reason,
                         "UNEXPECTED_FOLLOWUP")
        with self.assertRaises(ValueError):
            inspect_s7_early_evidence(mode="TOUCH_CLOSE_BELOW",**p)

    def test_followup_future_or_duplicate_blocked(self):
        p,c=self.later()
        for candidate,cutoff in ((c,c.selected.bar_end_utc),(p["retest"],AS_OF)):
            r=inspect_s7_early_evidence(mode=S7EarlyMode.LATER_CLOSE_BELOW,
                                      followup=candidate,**dict(p,as_of_utc=cutoff))
            self.assertEqual(r.reason,"FOLLOWUP_SOURCE_OR_CLOCK_MISMATCH")
            self.assertIsNone(r.early_preview_id)

    def test_followup_wrong_tf_and_mixed_source_blocked(self):
        p,c=self.later()
        wrong=snap(make_bar(104,timeframe=Timeframe.M5,
                           start=c.selected.market_bar_key.bar_start_utc,
                           open_price=D("4"),low=D("2"),close=D("2.5")))
        raw=c.selected
        obs=replace(raw.observation_key,provider_id="DIFFERENT")
        other=snap(replace(raw,observation_key=obs,
                           observation_revision=replace(raw.observation_revision,observation_key=obs)))
        for candidate in (wrong,other):
            r=inspect_s7_early_evidence(mode=S7EarlyMode.LATER_CLOSE_BELOW,
                                       followup=candidate,**p)
            self.assertEqual(r.reason,"FOLLOWUP_SOURCE_OR_CLOCK_MISMATCH")

    def test_retest_not_known_by_followup_start_blocked(self):
        p,c=self.later()
        raw=p["retest"].selected
        p["retest"]=snap(replace(raw,verified_at_utc=c.selected.bar_end_utc))
        r=inspect_s7_early_evidence(mode=S7EarlyMode.LATER_CLOSE_BELOW,followup=c,**p)
        self.assertEqual(r.reason,"FOLLOWUP_SOURCE_OR_CLOCK_MISMATCH")

    def test_missing_base_and_forged_authority_blocked(self):
        p=self.touch()
        r=inspect_s7_early_evidence(mode=S7EarlyMode.TOUCH_CLOSE_BELOW,**p)
        blocked=inspect_s7_early_evidence(mode=r.mode,**dict(p,candidate_epsilon=None))
        self.assertTrue(blocked.reason.startswith("BASE_"))
        self.assertIsNone(blocked.early_preview_id)
        for key in ("action_eligible","detector_approved","source_independently_attested"):
            for value in (True,0,None):
                with self.assertRaises(ValueError):
                    replace(r,**{key:value})
        with self.assertRaises(ValueError):
            replace(r,witness_known_at_utc=AS_OF+timedelta(seconds=1))



class S7ConfirmationEvidenceTests(unittest.TestCase):
    def chain(self):
        p=inputs()
        p["retest"]=snap(replace(p["retest"].selected,close=D("2.5")))
        hist=tuple(snap(make_bar(i+32,low=D(low),close=D(close),
                                 open_price=D(close)))
                   for i,(low,close) in enumerate(
                       [("2","3"),("1.5","2"),("2","3"),
                        ("2","2"),(".4",".5")]))
        return dict(p, variant_id="S7/F_MICRO_BREAK",
                    mode=S7EarlyMode.TOUCH_CLOSE_BELOW,
                    confirmation=hist[4],micro_history=hist[:3],
                    micro_index=1,micro_left=1,micro_right=1,
                    micro_previous=hist[3],micro_atr_history=d1(),
                    micro_tie_policy=TiePolicy.STRICT_V1,micro_epsilon=D(".1"))

    def test_chain_reuses_early_and_micro_break_both_strategies(self):
        for strategy in (Strategy.SHORT,Strategy.SWING):
            p=dict(self.chain(),strategy=strategy)
            r=inspect_s7_confirmation_evidence(**p)
            self.assertEqual(r.reason,"RF_CHAIN_GEOMETRY_UNCALIBRATED")
            early=inspect_s7_early_evidence(**{
                k:v for k,v in p.items() if not k.startswith("micro_")
                and k not in ("variant_id","confirmation")})
            self.assertEqual(r.early_preview_id,early.early_preview_id)
            self.assertEqual(r.origin_preview_id,early.origin_preview_id)
            self.assertEqual(r.retest_preview_id,early.retest_preview_id)
            self.assertTrue(r.micro_bos_preview_id.startswith("MST_BOS_PREVIEW_V1:"))
            self.assertIs(r.status,DecisionStatus.UNVERIFIED)
            self.assertFalse(r.action_eligible)
            self.assertEqual(r,inspect_s7_confirmation_evidence(**p))

    def test_missing_or_false_early_blocks(self):
        p=self.chain()
        p["retest"]=inputs()["retest"]
        self.assertEqual(inspect_s7_confirmation_evidence(**p).reason,
                         "RF_EARLY_SHAPE_NOT_CAUSALLY_PRESENT")

    def test_old_support_equality_blocks(self):
        p=self.chain()
        p["confirmation"]=snap(replace(p["confirmation"].selected,close=D("3")))
        self.assertEqual(inspect_s7_confirmation_evidence(**p).reason,
                         "RF_CLOSE_NOT_BELOW_ORIGINAL_SUPPORT")

    def test_below_support_but_no_micro_cross_blocks(self):
        p=self.chain()
        p["confirmation"]=snap(replace(p["confirmation"].selected,close=D("2")))
        self.assertEqual(inspect_s7_confirmation_evidence(**p).reason,
                         "RF_MICRO_CROSS_NOT_PRESENT")

    def test_early_verified_after_target_start_blocks(self):
        p=self.chain()
        raw=p["retest"].selected
        p["retest"]=snap(replace(raw,verified_at_utc=p["confirmation"].selected.bar_end_utc))
        self.assertEqual(inspect_s7_confirmation_evidence(**p).reason,
                         "RF_EARLY_SHAPE_NOT_CAUSALLY_PRESENT")

    def test_wrong_target_timeframe_and_future_block(self):
        p=self.chain()
        for target,as_of in ((p["retest"],AS_OF),
                              (p["confirmation"],p["confirmation"].selected.bar_end_utc)):
            r=inspect_s7_confirmation_evidence(**dict(p,confirmation=target,as_of_utc=as_of))
            self.assertEqual(r.reason,"RF_TARGET_NOT_CLOSED_H1_D1")

    def test_pre_early_micro_anchor_and_mixed_tf_block(self):
        p=self.chain()
        r=inspect_s7_confirmation_evidence(**dict(p,micro_history=p["pivot_history"],micro_index=2))
        self.assertEqual(r.reason,"RF_MICRO_PIVOT_SOURCE_OR_SEQUENCE_MISMATCH")
        r=inspect_s7_confirmation_evidence(**dict(p,micro_history=(p["retest"],)+p["micro_history"][1:]))
        self.assertEqual(r.reason,"RF_MICRO_PIVOT_SOURCE_OR_SEQUENCE_MISMATCH")

    def test_variant_and_forged_authority_block(self):
        p=self.chain()
        with self.assertRaises(ValueError):
            inspect_s7_confirmation_evidence(**dict(p,variant_id="S7/F_CONTINUATION"))
        r=inspect_s7_confirmation_evidence(**p)
        for key in ("action_eligible","detector_approved","parameter_approved","source_independently_attested"):
            for value in (True,0,None):
                with self.assertRaises(ValueError):
                    replace(r,**{key:value})
        with self.assertRaises(ValueError):
            replace(r,witness_known_at_utc=AS_OF+timedelta(seconds=1))

    def test_revision_changes_chain_not_origin(self):
        p=self.chain()
        a=inspect_s7_confirmation_evidence(**p)
        p["confirmation"]=snap(replace(p["confirmation"].selected,close=D(".6")))
        b=inspect_s7_confirmation_evidence(**p)
        self.assertEqual(a.origin_preview_id,b.origin_preview_id)
        self.assertNotEqual(a.confirmation_preview_id,b.confirmation_preview_id)



class S7ChainAudit268Tests(unittest.TestCase):
    def chain(self):
        return S7ConfirmationEvidenceTests().chain()

    @staticmethod
    def h1(row):
        key = replace(row.market_bar_key,timeframe=Timeframe.H1)
        obs = replace(row.observation_key,market_bar_key=key)
        end = key.bar_start_utc+timedelta(hours=1)
        retrieved = end+timedelta(minutes=1)
        rev = replace(row.observation_revision,observation_key=obs,
                      first_known_time_utc=end,retrieved_at_utc=retrieved)
        return snap(replace(row,market_bar_key=key,observation_key=obs,
                            observation_revision=rev,bar_end_utc=end,
                            retrieved_at_utc=retrieved,
                            verified_at_utc=retrieved+timedelta(minutes=1)))

    def test_h1_full_hour_confirmation_both_strategies_and_origins(self):
        for strategy in (Strategy.SHORT,Strategy.SWING):
            for origin_tf in (Timeframe.D1,Timeframe.H1):
                p=self.chain()
                p["strategy"]=strategy
                p["micro_history"]=tuple(self.h1(x.selected) for x in p["micro_history"])
                for key in ("micro_previous","confirmation"):
                    p[key]=self.h1(p[key].selected)
                if origin_tf is Timeframe.H1:
                    p["pivot_history"]=tuple(self.h1(x.selected) for x in p["pivot_history"])
                    for key in ("previous","breakdown"):
                        p[key]=self.h1(p[key].selected)
                self.assertEqual(p["confirmation"].selected.bar_end_utc-
                                 p["confirmation"].market_bar_key.bar_start_utc,
                                 timedelta(hours=1))
                r=inspect_s7_confirmation_evidence(**p)
                self.assertEqual(r.reason,"RF_CHAIN_GEOMETRY_UNCALIBRATED")
                self.assertIs(r.status,DecisionStatus.UNVERIFIED)
                self.assertFalse(r.action_eligible)

    def test_base_repeated_identical_history_allowed_but_conflicting_payload_denied(self):
        p=inputs()
        a=inspect_s7_retest_evidence(**p)
        self.assertIsNotNone(a.origin_preview_id)
        rows=p["retest_atr_d1_history"]
        changed=snap(replace(rows[0].selected,close=D("10.5")))
        p["retest_atr_d1_history"]=(changed,)+rows[1:]
        r=inspect_s7_retest_evidence(**p)
        self.assertEqual(r.reason,"S7_CHAIN_REVISION_CONFLICT")
        self.assertIsNone(r.retest_preview_id)

    def test_cross_phase_conflicting_source_revision_blocks(self):
        p=self.chain()
        rows=p["micro_atr_history"]
        raw=rows[0].selected
        changed=snap(replace(raw,observation_revision=replace(
            raw.observation_revision,source_revision_or_payload_digest="other-revision")))
        p["micro_atr_history"]=(changed,)+rows[1:]
        r=inspect_s7_confirmation_evidence(**p)
        self.assertEqual(r.reason,"S7_CHAIN_REVISION_CONFLICT")
        self.assertIsNone(r.confirmation_preview_id)

    def test_cross_phase_identical_key_different_ohlc_blocks(self):
        p=self.chain()
        rows=p["micro_atr_history"]
        p["micro_atr_history"]=(snap(replace(rows[0].selected,close=D("10.5"))),)+rows[1:]
        self.assertEqual(inspect_s7_confirmation_evidence(**p).reason,
                         "S7_CHAIN_REVISION_CONFLICT")

    def test_resolved_revision_conflict_in_micro_history_blocks(self):
        p=self.chain()
        rows=p["micro_history"]
        raw=rows[0].selected
        changed=replace(raw,observation_revision=replace(
            raw.observation_revision,source_revision_or_payload_digest="conflict"))
        ambiguous=resolve_as_known(raw.market_bar_key,(raw,changed),AS_OF)
        p["micro_history"]=(ambiguous,)+rows[1:]
        r=inspect_s7_confirmation_evidence(**p)
        self.assertEqual(r.reason,"RF_MICRO_PIVOT_SOURCE_OR_SEQUENCE_MISMATCH")

    def test_late_retest_revision_cannot_enter_earlier_confirmation(self):
        p=self.chain()
        raw=p["retest"].selected
        cutoff=p["confirmation"].market_bar_key.bar_start_utc
        known=cutoff+timedelta(minutes=1)
        retrieved=known+timedelta(minutes=1)
        corrected=replace(raw,observation_revision=replace(
            raw.observation_revision,source_revision_or_payload_digest="late",
            first_known_time_utc=known,retrieved_at_utc=retrieved),
            retrieved_at_utc=retrieved,verified_at_utc=retrieved+timedelta(minutes=1))
        p["retest"]=snap(corrected)
        r=inspect_s7_confirmation_evidence(**p)
        self.assertEqual(r.reason,"RF_EARLY_SHAPE_NOT_CAUSALLY_PRESENT")

    def test_mixed_adjustment_revision_target_blocked(self):
        p=self.chain()
        raw=p["confirmation"].selected
        changed=replace(raw,observation_revision=replace(
            raw.observation_revision,adjustment_revision="different-adjustment"))
        p["confirmation"]=snap(changed)
        self.assertEqual(inspect_s7_confirmation_evidence(**p).reason,
                         "RF_TARGET_SOURCE_MISMATCH")


if __name__ == "__main__":
    unittest.main()
