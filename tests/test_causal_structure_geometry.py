"""§206 synthetic-only causal pivot, BOS and existing Wilder ATR14 integration.

These fixtures CLAIM source quality only inside tests. They cannot attest
SSI/DNSE/VCBS licensing, first-known venue clock, source history continuity,
H4 aggregation, exchange calendar, actual signal, or future trade profits.
"""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import unittest

from swing_trading.causal_structure_geometry import (
    BosGeometry, GeometryState, PivotGeometry, StructureSide, TiePolicy,
    inspect_causal_pivot, inspect_closed_bos_geometry,
)
from swing_trading.market_data import PriceBasis, Timeframe
from swing_trading.source_quality import (
    QualityState, CoverageState, resolve_as_known,
)
from test_causal_indicators import AS_OF, START, make_bar, snap

PIVOT0 = START + timedelta(days=25)


def series(items, *, timeframe=Timeframe.M15):
    data=[]
    for i,(high,low,close) in enumerate(items):
        begin=PIVOT0+timedelta(minutes=i*30)
        row=make_bar(
            i+100, timeframe=timeframe, start=begin,
            open_price=D("10"), high=D(high),
            low=D(low), close=D(close),
        )
        data.append(snap(row))
    return tuple(data)


def highs():
    return series([
        ("12","8","10"), ("13","8","11"),
        ("16","8","14"), ("14","8","12"),
        ("16","8","16"), ("20","8","18"),
    ])


def lows():
    return series([
        ("12","7","10"), ("12","6","10"),
        ("12","3","5"), ("12","5","8"),
        ("12","4","4"), ("12","1","1"),
    ])


def atr_d1():
    return tuple(snap(make_bar(i)) for i in range(15))


def pivot(hist=None, side=StructureSide.HIGH, **changes):
    return inspect_causal_pivot(
        highs()[:4] if hist is None else hist,
        candidate_index=changes.get("candidate_index",2),
        left_count=changes.get("left_count",1),
        right_count=changes.get("right_count",1),
        side=side, tie_policy=changes.get("tie_policy",TiePolicy.STRICT_V1),
        as_of_utc=changes.get("as_of_utc",AS_OF),
    )


def bos(*, side=StructureSide.HIGH, hist=None,
        eps=D("0.25"), atr=None, **changes):
    data=(highs() if side is StructureSide.HIGH else lows()) if hist is None else hist
    return inspect_closed_bos_geometry(
        data[:4],
        pivot_index=changes.get("pivot_index",2),
        left_count=changes.get("left_count",1),
        right_count=changes.get("right_count",1),
        previous=changes.get("previous",data[4]),
        breakout=changes.get("breakout",data[5]),
        atr_d1_history=atr_d1() if atr is None else atr,
        side=side,
        tie_policy=changes.get("tie_policy",TiePolicy.STRICT_V1),
        candidate_epsilon=eps,
        as_of_utc=changes.get("as_of_utc",AS_OF),
    )


class CausalPivot206Tests(unittest.TestCase):
    def test_strict_high_pivot_only_after_right_bars(self):
        r=pivot()
        self.assertIs(r.state,GeometryState.DESCRIPTIVE_ONLY)
        self.assertTrue(r.geometric_extremum)
        self.assertEqual(r.pivot_price,D("16"))
        self.assertGreaterEqual(
            r.witness_known_at_utc,
            highs()[3].selected.verified_at_utc,
        )
        self.assertGreater(r.witness_known_at_utc,
                           highs()[2].selected.bar_end_utc)
        self.assertFalse(r.detector_approved)
        self.assertFalse(r.source_independently_attested)
        self.assertFalse(r.action_eligible)

    def test_strict_low_pivot(self):
        r=pivot(hist=lows()[:4],side=StructureSide.LOW)
        self.assertIs(r.state,GeometryState.DESCRIPTIVE_ONLY)
        self.assertTrue(r.geometric_extremum)
        self.assertEqual(r.pivot_price,D("3"))

    def test_no_right_bar_is_unverified_not_structural(self):
        r=pivot(hist=highs()[:3])
        self.assertIs(r.state,GeometryState.BLOCKED)
        self.assertEqual(r.reason,"INSUFFICIENT_CAUSAL_LEFT_OR_RIGHT_BARS")
        self.assertIsNone(r.geometric_extremum)

    def test_right_bar_after_asof_cannot_retroactively_confirm_pivot(self):
        right=highs()[3].selected
        cutoff=right.bar_end_utc+timedelta(seconds=20)
        self.assertLess(cutoff,right.verified_at_utc)
        r=pivot(as_of_utc=cutoff)
        self.assertEqual(r.state,GeometryState.BLOCKED)
        self.assertEqual(r.reason,"UNQUALIFIED_OR_NOT_YET_KNOWN_BAR")

    def test_equal_high_tie_policy_is_explicit(self):
        data=series([
            ("12","8","10"), ("16","8","10"),
            ("16","8","10"), ("14","8","10"),
        ])
        strict=pivot(hist=data,tie_policy=TiePolicy.STRICT_V1)
        equal=pivot(hist=data,tie_policy=TiePolicy.ALLOW_EQUAL_V1)
        self.assertFalse(strict.geometric_extremum)
        self.assertTrue(equal.geometric_extremum)

    def test_equal_low_tie_policy_is_explicit(self):
        data=series([
            ("12","5","10"), ("12","3","10"),
            ("12","3","10"), ("12","5","10"),
        ])
        strict=pivot(hist=data,side=StructureSide.LOW)
        equal=pivot(hist=data,side=StructureSide.LOW,
                    tie_policy=TiePolicy.ALLOW_EQUAL_V1)
        self.assertFalse(strict.geometric_extremum)
        self.assertTrue(equal.geometric_extremum)

    def test_monotone_without_pivot_is_descriptive_false(self):
        data=series([
            ("12","8","10"), ("13","8","10"),
            ("14","8","10"), ("15","8","10"),
        ])
        r=pivot(hist=data)
        self.assertIs(r.state,GeometryState.DESCRIPTIVE_ONLY)
        self.assertFalse(r.geometric_extremum)
        self.assertFalse(r.action_eligible)

    def test_duplicate_or_reordered_history_blocked(self):
        d=highs()
        for hist in (d[:3]+(d[2],), (d[1],d[0],d[2],d[3])):
            with self.subTest(series=hist):
                self.assertEqual(pivot(hist=hist).state,GeometryState.BLOCKED)

    def test_mixed_provider_calendar_adjustment_and_basis_blocked(self):
        original=highs()
        one=original[1].selected
        def rekey(row,**fields):
            k=replace(row.market_bar_key,**fields)
            o=replace(row.observation_key,market_bar_key=k)
            v=replace(row.observation_revision,observation_key=o)
            return replace(row,market_bar_key=k,observation_key=o,
                           observation_revision=v)
        newobs=replace(one.observation_key,provider_id="ANOTHER_PROVIDER")
        cases=(
            rekey(one,price_basis=PriceBasis.ADJUSTED),
            rekey(one,calendar_version="different_calendar"),
            rekey(one,aggregation_policy_version="different_aggregation"),
            replace(one, observation_key=newobs,
                    observation_revision=replace(
                        one.observation_revision,observation_key=newobs)),
            replace(one,observation_revision=replace(
                one.observation_revision,adjustment_revision="later_adjustment")),
        )
        for changed in cases:
            with self.subTest(case=changed.market_bar_key):
                self.assertEqual(
                    pivot(hist=(original[0],snap(changed))+original[2:4]).reason,
                    "MIXED_SOURCE_BASIS_OR_POLICY",
                )

    def test_quality_partial_coverage_and_future_first_known_block(self):
        original=highs()
        third=original[2].selected
        future=replace(third.observation_revision,
                       first_known_time_utc=AS_OF+timedelta(hours=2),
                       retrieved_at_utc=AS_OF+timedelta(hours=2))
        cases=(
            replace(third, quality_state=QualityState.UNVERIFIED),
            replace(third, coverage_state=CoverageState.SESSION_PARTIAL),
            replace(third, observation_revision=future,
                    retrieved_at_utc=future.retrieved_at_utc,
                    verified_at_utc=future.retrieved_at_utc+timedelta(minutes=1)),
        )
        for row in cases:
            with self.subTest(case=row.observation_revision):
                self.assertEqual(
                    pivot(hist=original[:2]+(snap(row),original[3])).state,
                    GeometryState.BLOCKED,
                )

    def test_h4_requires_independent_aggregation_not_fixture_label(self):
        data=series([
            ("12","8","10"), ("13","8","10"),
            ("16","8","14"), ("14","8","12"),
        ],timeframe=Timeframe.H4)
        r=pivot(hist=data)
        self.assertEqual(r.reason,"H4_DERIVED_SESSION_NOT_ATTESTED")

    def test_revision_conflict_and_future_correction_asof(self):
        original=highs()
        selected=original[0].selected
        amended_rev=replace(selected.observation_revision,
                            source_revision_or_payload_digest="later",
                            first_known_time_utc=AS_OF+timedelta(hours=1),
                            retrieved_at_utc=AS_OF+timedelta(hours=1))
        amended=replace(
            selected,observation_revision=amended_rev,
            retrieved_at_utc=amended_rev.retrieved_at_utc,
            verified_at_utc=amended_rev.retrieved_at_utc+timedelta(minutes=1),
        )
        before=resolve_as_known(selected.market_bar_key,(selected,amended),AS_OF)
        self.assertEqual(before.selected,selected)
        self.assertTrue(pivot(hist=(before,)+original[1:4]).geometric_extremum)
        after=resolve_as_known(
            selected.market_bar_key,(selected,amended),AS_OF+timedelta(hours=2)
        )
        self.assertEqual(after.reason,"SOURCE_OR_REVISION_CONFLICT")
        self.assertEqual(
            pivot(hist=(after,)+original[1:4],
                  as_of_utc=AS_OF+timedelta(hours=2)).state,
            GeometryState.BLOCKED,
        )

    def test_bad_warmup_counts_bool_indices_and_wrong_side_rejected(self):
        for changes in (
            {"candidate_index":True}, {"left_count":0},
            {"right_count":-1}, {"left_count":41},
            {"tie_policy":"STRICT_V1"},
        ):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                pivot(**changes)
        with self.assertRaises(ValueError):
            inspect_causal_pivot(
                highs()[:4],candidate_index=2,left_count=1,right_count=1,
                side="HIGH",tie_policy=TiePolicy.STRICT_V1,as_of_utc=AS_OF,
            )
        with self.assertRaises(ValueError):
            pivot(as_of_utc=AS_OF.replace(tzinfo=None))

    def test_no_false_approval_from_dataclass_replace(self):
        p=pivot()
        for edits in ({"action_eligible":True},
                      {"source_independently_attested":True},
                      {"detector_approved":True},
                      {"witness_known_at_utc":p.candidate_bar_end_utc-timedelta(seconds=1)}):
            with self.subTest(edits=edits),self.assertRaises(ValueError):
                replace(p,**edits)


class CausalBos206Tests(unittest.TestCase):
    def test_bullish_cross_closes_over_pivot_plus_unapproved_atr_buffer(self):
        result=bos()
        self.assertIs(result.state,GeometryState.DESCRIPTIVE_ONLY)
        self.assertIs(result.candidate_cross,True)
        self.assertEqual(result.boundary,D("17"))
        self.assertEqual(result.previous_close,D("16"))
        self.assertEqual(result.breakout_close,D("18"))
        self.assertFalse(result.source_independently_attested)
        self.assertFalse(result.parameter_approved)
        self.assertFalse(result.detector_approved)
        self.assertFalse(result.action_eligible)
        self.assertGreaterEqual(result.witness_known_at_utc,
                                highs()[5].selected.verified_at_utc)

    def test_bearish_cross_closes_below_pivot_minus_atr(self):
        result=bos(side=StructureSide.LOW)
        self.assertEqual(result.boundary,D("2"))
        self.assertIs(result.candidate_cross,True)
        self.assertEqual(result.breakout_close,D("1"))
        self.assertFalse(result.action_eligible)

    def test_open_wick_not_cross_when_close_below_boundary(self):
        d=highs()
        wick=replace(d[5].selected,high=D("20"),close=D("16"))
        result=bos(breakout=snap(wick))
        self.assertIs(result.state,GeometryState.DESCRIPTIVE_ONLY)
        self.assertFalse(result.candidate_cross)

    def test_preexisting_breakout_above_threshold_does_not_count_twice(self):
        d=highs()
        prior=replace(d[4].selected,close=D("17.5"),
                      high=D("18"))
        result=bos(previous=snap(prior))
        self.assertFalse(result.candidate_cross)

    def test_equal_boundary_is_not_cross_for_up_or_down(self):
        d=highs()
        result=bos(breakout=snap(replace(d[5].selected,close=D("17"))))
        self.assertFalse(result.candidate_cross)
        dl=lows()
        down=bos(side=StructureSide.LOW,
                 breakout=snap(replace(dl[5].selected,close=D("2"))))
        self.assertFalse(down.candidate_cross)

    def test_epsilon_unspecified_is_unknown_not_zero(self):
        result=bos(eps=None)
        self.assertEqual(result.state,GeometryState.BLOCKED)
        self.assertEqual(result.reason,"UNAPPROVED_EPSILON_NOT_SUPPLIED")
        self.assertIsNone(result.candidate_cross)
        self.assertIsNone(result.boundary)

    def test_fractional_epsilon_requires_decimal_finite_nonnegative(self):
        for eps in (0.25,"0.25",True,D("-1"),D("NaN"),D("Infinity")):
            with self.subTest(epsilon=eps),self.assertRaisesRegex(
                ValueError,"EPSILON_INVALID",
            ):
                bos(eps=eps)

    def test_missing_or_insufficient_atr_history_blocks_not_fabricates(self):
        for history in ((),atr_d1()[:14],tuple()):
            result=bos(atr=history)
            self.assertIs(result.state,GeometryState.BLOCKED)
            self.assertIsNone(result.candidate_cross)

    def test_atr_cross_tf_provider_basis_licensing_identity_must_match(self):
        daily=list(atr_d1())
        for field in ("instrument_id","exchange","calendar_version","price_basis"):
            rows=list(daily)
            # Amend ALL D1 rows consistently; we want the CROSS TF identity
            # gate, not an intra-ATR provider-mix false positive.
            for i,s in enumerate(rows):
                row=s.selected
                value={
                    "instrument_id":"HOSE:FOREIGN:registry-v1",
                    "exchange":"HNX",
                    "calendar_version":"other_venue_policy",
                    "price_basis":PriceBasis.ADJUSTED,
                }[field]
                key=replace(row.market_bar_key,**{field:value})
                obs=replace(row.observation_key,market_bar_key=key)
                rev=replace(row.observation_revision,observation_key=obs)
                rows[i]=snap(replace(
                    row,market_bar_key=key,observation_key=obs,
                    observation_revision=rev,
                ))
            with self.subTest(field=field):
                self.assertEqual(
                    bos(atr=tuple(rows)).reason,
                    "ATR14_CROSS_TF_PROVIDER_BASIS_MISMATCH",
                )

    def test_breakout_missing_source_closure_or_venue_attestation_blocks(self):
        d=highs()
        bad=replace(d[5].selected,quality_state=QualityState.UNVERIFIED)
        self.assertEqual(
            bos(breakout=snap(bad)).reason,
            "BREAKOUT_NOT_CLOSED_OR_CAUSALLY_KNOWN",
        )
        unknown=replace(
            d[5].selected,coverage_state=CoverageState.SESSION_PARTIAL,
        )
        self.assertEqual(
            bos(breakout=snap(unknown)).state,GeometryState.BLOCKED,
        )

    def test_previous_not_known_by_breakout_start(self):
        d=highs()
        previous=d[4].selected
        start=d[5].selected.market_bar_key.bar_start_utc
        assert previous.verified_at_utc < start
        revised=replace(previous,verified_at_utc=start+timedelta(minutes=1))
        self.assertEqual(
            bos(previous=snap(revised)).reason,
            "PREVIOUS_BAR_NOT_KNOWN_BEFORE_BREAKOUT",
        )

    def test_pivot_confirmation_right_bars_must_be_before_breakout(self):
        d=highs()
        late_right=d[3].selected
        start=d[5].selected.market_bar_key.bar_start_utc
        delayed=replace(late_right,verified_at_utc=start+timedelta(minutes=1))
        hist=d[:3]+(snap(delayed),)+d[4:]
        self.assertEqual(
            bos(hist=hist).reason,
            "PIVOT_UNQUALIFIED_OR_NOT_YET_KNOWN_BAR",
        )

    def test_wrong_previous_provider_or_different_tf_is_not_cross(self):
        d=highs()
        previous=d[4].selected
        changedobs=replace(previous.observation_key,provider_id="ALT")
        changed=replace(previous,observation_key=changedobs,
                        observation_revision=replace(
                            previous.observation_revision,
                            observation_key=changedobs,
                        ))
        self.assertEqual(
            bos(previous=snap(changed)).reason,
            "PREVIOUS_BAR_IDENTITY_OR_CLOCK_MISMATCH",
        )

    def test_failed_structural_pivot_not_silently_a_breakout(self):
        data=series([
            ("12","8","10"),("13","8","10"),
            ("14","8","10"),("15","8","10"),
            ("16","8","12"),("20","8","18"),
        ])
        r=bos(hist=data)
        self.assertEqual(r.reason,"PIVOT_NOT_STRUCTURAL_EXTREMUM")

    def test_no_backdating_or_fabricated_approved_event_when_future_asof(self):
        d=highs()
        before=d[5].selected.bar_end_utc-timedelta(seconds=1)
        result=bos(as_of_utc=before)
        self.assertEqual(result.reason,
                         "BREAKOUT_NOT_CLOSED_OR_CAUSALLY_KNOWN")
        after=bos()
        self.assertGreaterEqual(after.witness_known_at_utc,
                                d[5].selected.verified_at_utc)
        for edits in (
            {"action_eligible":True},
            {"detector_approved":True},
            {"source_independently_attested":True},
            {"parameter_approved":True},
            {"candidate_cross":None},
        ):
            with self.subTest(edits=edits),self.assertRaises(ValueError):
                replace(after,**edits)

    def test_h4_target_is_never_native_qualified(self):
        d=highs()
        target=d[5].selected
        key=replace(target.market_bar_key,timeframe=Timeframe.H4)
        obs=replace(target.observation_key,market_bar_key=key)
        rev=replace(target.observation_revision,observation_key=obs)
        h4=snap(replace(target,market_bar_key=key,observation_key=obs,
                       observation_revision=rev))
        self.assertEqual(
            bos(breakout=h4).reason,"H4_DERIVED_SESSION_NOT_ATTESTED"
        )


if __name__=="__main__":
    unittest.main()
