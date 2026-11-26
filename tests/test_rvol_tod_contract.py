"""P0.11 synthetic cumulative RVOL-TOD20: exact local slots, no source claims."""
import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from swing_trading.causal_indicators import (
    IndicatorState, VolumeSessionClass, VolumeBasis, VolumeBasisWitness,
)
from swing_trading.market_data import PriceBasis, Timeframe
from swing_trading.rvol_tod_contract import (
    CumulativeVolumeDefinition, TODCumulativeObservation, calculate_rvol_tod20,
    TODRawPrefix, calculate_rvol_tod20_from_raw_prefixes,
)
from swing_trading.source_quality import QualityState, resolve_as_known
from swing_trading.session_calendar import CalendarSnapshot, TradingSession, SessionType
from test_causal_indicators import AS_OF, make_bar, snap


UTC = timezone.utc
VN = timezone(timedelta(hours=7))
START = datetime(2026, 9, 7, 2, 15, tzinfo=UTC)


def make_slot(i, *, cumulative=1000, bar_volume=10, session_kind=VolumeSessionClass.CONTINUOUS,
              elapsed=30, definition=CumulativeVolumeDefinition.MATCHED_CONTINUOUS_ONLY):
    # These days include weekends: strictly arithmetic fixtures, NEVER
    # official HOSE/HNX/UPCoM trading-session evidence.
    row = make_bar(
        i, timeframe=Timeframe.M15, volume=bar_volume,
        start=START + timedelta(days=i),
    )
    return TODCumulativeObservation(
        snapshot=snap(row),
        trading_date_local=row.bar_end_utc.astimezone(VN).date(),
        slot_end_local_hhmm="09:30",
        session_class=session_kind,
        elapsed_trading_minutes=elapsed,
        cumulative_matched_volume=cumulative,
        volume_definition=definition,
        volume_event_id=row.source_event_ids[0],
        cumulative_first_known_utc=row.bar_end_utc,
        cumulative_verified_utc=row.verified_at_utc,
        volume_policy_version="synthetic-volume-v1",
    )


def sample():
    return make_slot(20), tuple(make_slot(i) for i in range(20))


def calculate(*, target=None, prior=None, asof=AS_OF):
    t, p = sample()
    return calculate_rvol_tod20(t if target is None else target,
                                p if prior is None else prior,
                                as_of_utc=asof)


class TODContractTests(unittest.TestCase):
    def test_same_local_slot_20_distinct_sessions_returns_one_nonactionable(self):
        v=calculate()
        self.assertEqual(v.value, Decimal("1"))
        self.assertEqual(v.used_bar_count,21)
        self.assertEqual(v.state,IndicatorState.COMPUTED_UNCALIBRATED)
        self.assertFalse(v.data_certified)
        self.assertFalse(v.parameter_approved)
        self.assertFalse(v.actionable)
        self.assertEqual(v.indicator_id,"RVOL_TOD20")

    def test_target_cumulative_double_is_two(self):
        t,p=sample()
        v=calculate(target=replace(t,cumulative_matched_volume=2000),prior=p)
        self.assertEqual(v.value,Decimal("2"))

    def test_zero_target_volume_is_valid_not_missing(self):
        t,p=sample()
        row=replace(t.snapshot.selected,volume=0)
        v=calculate(target=replace(t,snapshot=snap(row),cumulative_matched_volume=0),prior=p)
        self.assertEqual(v.value,Decimal("0"))

    def test_all_zero_prior_requires_nonzero_denominator(self):
        t,p=sample()
        new=tuple(
            replace(item, snapshot=snap(replace(item.snapshot.selected,volume=0)),
                    cumulative_matched_volume=0) for item in p
        )
        self.assertEqual(calculate(prior=new).reason,
                         "ZERO_PRIOR_CUMULATIVE_DENOMINATOR")

    def test_excluding_target_exactly_twenty_prior_sessions(self):
        t,p=sample()
        for cases in (p[:-1],p+(p[-1],)):
            self.assertEqual(calculate(prior=cases).reason,
                             "REQUIRE_EXACTLY_20_PRIOR_SESSIONS")
        self.assertEqual(calculate(prior=p[:-1]+(t,)).state,IndicatorState.BLOCKED)

    def test_current_local_slot_must_match_bar_utc_end(self):
        t,p=sample()
        self.assertEqual(calculate(target=replace(t,slot_end_local_hhmm="09:45")).reason,
                         "TARGET_SLOT_END_NOT_EXCHANGE_LOCAL_CLOCK")
        self.assertEqual(calculate(target=replace(t,trading_date_local=date(2026,9,1))).reason,
                         "TARGET_SLOT_END_NOT_EXCHANGE_LOCAL_CLOCK")

    def test_different_local_slot_on_prior_cannot_be_in_denominator(self):
        t,p=sample()
        # 09:45 belongs to another slot; even if its own bar ends at that
        # time, it must not be compared against target's 09:30.
        candidate=p[7]
        key=replace(candidate.snapshot.selected.market_bar_key,
                    bar_start_utc=candidate.snapshot.selected.market_bar_key.bar_start_utc+
                    timedelta(minutes=15))
        obs=replace(candidate.snapshot.selected.observation_key,market_bar_key=key)
        rev=replace(candidate.snapshot.selected.observation_revision,observation_key=obs)
        old=candidate.snapshot.selected
        end=old.bar_end_utc+timedelta(minutes=15)
        retrieved=old.retrieved_at_utc+timedelta(minutes=15)
        verified=old.verified_at_utc+timedelta(minutes=15)
        revision=replace(rev,first_known_time_utc=end,retrieved_at_utc=retrieved)
        row=replace(old,market_bar_key=key,observation_key=obs,
                    observation_revision=revision,bar_end_utc=end,
                    retrieved_at_utc=retrieved,verified_at_utc=verified)
        altered=replace(candidate,snapshot=snap(row),slot_end_local_hhmm="09:45",
                        cumulative_first_known_utc=row.bar_end_utc,
                        cumulative_verified_utc=row.verified_at_utc)
        seq=list(p);seq[7]=altered
        self.assertEqual(calculate(prior=tuple(seq)).reason,
                         "LOCAL_SLOT_SEGMENT_OR_VOLUME_POLICY_MISMATCH")

    def test_auction_vs_continuous_never_mixed(self):
        t,p=sample()
        seq=list(p)
        seq[0]=replace(seq[0],session_class=VolumeSessionClass.CLOSING_AUCTION)
        self.assertEqual(calculate(prior=tuple(seq)).reason,
                         "LOCAL_SLOT_SEGMENT_OR_VOLUME_POLICY_MISMATCH")

    def test_elapsed_trading_minutes_cannot_differ(self):
        t,p=sample()
        seq=list(p);seq[0]=replace(seq[0],elapsed_trading_minutes=35)
        self.assertEqual(calculate(prior=tuple(seq)).state,IndicatorState.BLOCKED)

    def test_market_cumulative_definitions_cannot_mix(self):
        t,p=sample()
        seq=list(p)
        seq[0]=replace(seq[0],volume_definition=
                       CumulativeVolumeDefinition.MATCHED_INCLUDING_AUCTIONS)
        self.assertEqual(calculate(prior=tuple(seq)).reason,
                         "LOCAL_SLOT_SEGMENT_OR_VOLUME_POLICY_MISMATCH")

    def test_policy_versions_are_part_of_comparator_identity(self):
        t,p=sample()
        seq=list(p);seq[0]=replace(seq[0],volume_policy_version="other-v1")
        self.assertEqual(calculate(prior=tuple(seq)).state,IndicatorState.BLOCKED)

    def test_prior_sessions_must_be_strictly_ordered(self):
        t,p=sample()
        self.assertEqual(calculate(prior=(p[1],p[0])+p[2:]).reason,
                         "DUPLICATE_OR_NONPRIOR_MARKET_SESSION")

    def test_duplicate_session_id_or_duplicate_local_date_rejected(self):
        t,p=sample()
        changed=list(p);changed[4]=p[3]
        self.assertEqual(calculate(prior=tuple(changed)).reason,
                         "DUPLICATE_OR_NONPRIOR_MARKET_SESSION")

    def test_late_known_cumulative_volume_never_backfilled_into_history(self):
        t,p=sample()
        changed=list(p)
        changed[2]=replace(changed[2],
                           cumulative_first_known_utc=t.snapshot.selected.bar_end_utc,
                           cumulative_verified_utc=t.snapshot.selected.bar_end_utc)
        self.assertEqual(calculate(prior=tuple(changed)).reason,
                         "PRIOR_CUMULATIVE_EVIDENCE_NOT_CAUSALLY_KNOWN")

    def test_prior_revised_bar_known_after_target_start_blocked(self):
        t,p=sample()
        changed=list(p)
        c=changed[3].snapshot.selected
        # Maintain valid first-known/retrieved/verified chronology, but
        # a late historical source revision is NOT eligible for prior average.
        when=t.snapshot.selected.market_bar_key.bar_start_utc+timedelta(minutes=1)
        rev=replace(c.observation_revision,
                    first_known_time_utc=when,retrieved_at_utc=when)
        row=replace(c,observation_revision=rev,retrieved_at_utc=when,
                    verified_at_utc=when+timedelta(minutes=1))
        changed[3]=replace(changed[3],snapshot=snap(row))
        self.assertEqual(calculate(prior=tuple(changed)).reason,
                         "PRIOR_CLOSED_BAR_OR_SOURCE_NOT_QUALIFIED")

    def test_target_cumulative_can_be_known_after_close_but_not_future(self):
        t,p=sample()
        future=AS_OF+timedelta(minutes=1)
        t=replace(t,cumulative_first_known_utc=future,cumulative_verified_utc=future)
        self.assertEqual(calculate(target=t).reason,
                         "TARGET_CUMULATIVE_EVIDENCE_NOT_CAUSALLY_KNOWN")

    def test_cumulative_event_must_belong_to_source_bar(self):
        t,p=sample()
        t=replace(t,volume_event_id="totally-another-source-id")
        self.assertEqual(calculate(target=t).reason,
                         "TARGET_CUMULATIVE_EVENT_NOT_LINKED_TO_SOURCE_BAR")

    def test_missing_cumulative_or_below_source_bar_volume_blocks(self):
        t,p=sample()
        self.assertEqual(calculate(target=replace(t,cumulative_matched_volume=None)).reason,
                         "TARGET_CUMULATIVE_VOLUME_NOT_SOURCE_USABLE")
        self.assertEqual(calculate(target=replace(t,cumulative_matched_volume=5)).state,
                         IndicatorState.BLOCKED)

    def test_wrong_timeframe_or_source_quality_is_refused(self):
        t,p=sample()
        candle=t.snapshot.selected
        key=replace(candle.market_bar_key,timeframe=Timeframe.D1)
        obs=replace(candle.observation_key,market_bar_key=key)
        rev=replace(candle.observation_revision,observation_key=obs)
        row=replace(candle,market_bar_key=key,observation_key=obs,
                    observation_revision=rev)
        self.assertEqual(calculate(target=replace(t,snapshot=snap(row))).reason,
                         "TARGET_RVOL_TOD_REQUIRES_NATIVE_INTRADAY_TF")
        bad=replace(candle,quality_state=QualityState.UNVERIFIED)
        self.assertEqual(calculate(target=replace(t,snapshot=snap(bad))).reason,
                         "TARGET_CLOSED_BAR_OR_SOURCE_NOT_QUALIFIED")

    def test_source_adjustment_provider_and_basis_must_match(self):
        t,p=sample()
        old=p[6].snapshot.selected
        obs=replace(old.observation_key,provider_id="OTHER_SYNTHETIC")
        rev=replace(old.observation_revision,observation_key=obs)
        row=replace(old,observation_key=obs,observation_revision=rev)
        changed=list(p);changed[6]=replace(changed[6],snapshot=snap(row))
        self.assertEqual(calculate(prior=tuple(changed)).reason,
                         "PRIOR_SOURCE_BASIS_OR_POLICY_MISMATCH")

    def test_invalid_input_and_clock_are_not_coerced(self):
        t,p=sample()
        self.assertEqual(calculate_rvol_tod20(t,list(p),as_of_utc=AS_OF).reason,
                         "INVALID_IMMUTABLE_PRIOR_SESSIONS")
        with self.assertRaises(ValueError):
            calculate(asof=AS_OF.replace(tzinfo=None))
        with self.assertRaises(ValueError):
            replace(t,elapsed_trading_minutes=True)
        with self.assertRaises(ValueError):
            replace(t,cumulative_matched_volume=-1)
        with self.assertRaises(ValueError):
            replace(t,slot_end_local_hhmm="25:60")
        with self.assertRaises(ValueError):
            replace(t,volume_policy_version="")
        with self.assertRaises(TypeError):
            replace(t,volume_definition="MATCHED_CONTINUOUS_ONLY")

    def test_future_source_verification_and_revision_conflicts(self):
        t,p=sample()
        c=t.snapshot.selected
        later=replace(c,verified_at_utc=AS_OF+timedelta(minutes=5))
        self.assertEqual(calculate(target=replace(t,snapshot=snap(later))).state,
                         IndicatorState.BLOCKED)
        revision=replace(c.observation_revision,
                         source_revision_or_payload_digest="changed",
                         first_known_time_utc=c.bar_end_utc,
                         retrieved_at_utc=c.retrieved_at_utc)
        altered=replace(c,observation_revision=revision)
        ambiguous=resolve_as_known(c.market_bar_key,(c,altered),AS_OF)
        self.assertEqual(calculate(target=replace(t,snapshot=ambiguous)).state,
                         IndicatorState.BLOCKED)


def raw_prefix_fixture(i, timeframe=Timeframe.M15, multiplier=1, afternoon=False):
    length = {Timeframe.M1: 1, Timeframe.M5: 5, Timeframe.M15: 15}[timeframe]
    opening = START + timedelta(days=i)
    if afternoon:
        slot_start = opening + timedelta(hours=4)
        starts = [opening + timedelta(minutes=j) for j in range(2)]
        starts += [slot_start + timedelta(minutes=j) for j in range(length)]
    else:
        slot_start = opening + timedelta(minutes=length)
        starts = [opening + timedelta(minutes=j) for j in range(2 * length)]
    rows = []
    for j, start in enumerate(starts):
        end = start + timedelta(minutes=1)
        row = make_bar(i, timeframe=Timeframe.M1, start=start, volume=10 * multiplier)
        sid = row.market_bar_key.session_period_id
        if afternoon and start < slot_start:
            sid += "-morning"
        key = replace(row.market_bar_key, session_period_id=sid)
        obs = replace(row.observation_key, market_bar_key=key)
        rev = replace(row.observation_revision, observation_key=obs,
                      source_revision_or_payload_digest=f"synthetic-{i}-{j}",
                      first_known_time_utc=end, retrieved_at_utc=end + timedelta(minutes=1))
        rows.append(replace(row, market_bar_key=key, observation_key=obs,
                            observation_revision=rev, bar_end_utc=end,
                            retrieved_at_utc=rev.retrieved_at_utc,
                            verified_at_utc=end + timedelta(minutes=2),
                            observed_minutes=1, expected_minutes=1,
                            source_event_ids=(f"synthetic-event-{i}-{j}",)))
    last = rows[-1]
    key = last.market_bar_key
    day = opening.astimezone(VN).date()
    def session(sid, start, end):
        return TradingSession(key.exchange, day, sid, SessionType.CONTINUOUS,
                              start, end, key.calendar_version, "synthetic",
                              "synthetic-calendar", True)
    if afternoon:
        sessions = (session(rows[0].market_bar_key.session_period_id,
                            opening, opening + timedelta(minutes=2)),
                    session(key.session_period_id, slot_start, last.bar_end_utc))
    else:
        sessions = (session(key.session_period_id, opening, last.bar_end_utc),)
    cal = CalendarSnapshot(key.exchange, day, key.calendar_version,
                           "synthetic-calendar", True, sessions)
    if timeframe is Timeframe.M1:
        slot = last
    else:
        slot = make_bar(i, timeframe=timeframe, start=slot_start,
                        volume=10 * multiplier * length)
        rev = replace(slot.observation_revision, first_known_time_utc=last.bar_end_utc,
                      retrieved_at_utc=last.retrieved_at_utc)
        slot = replace(slot, observation_revision=rev, bar_end_utc=last.bar_end_utc,
                       retrieved_at_utc=last.retrieved_at_utc,
                       verified_at_utc=last.verified_at_utc, observed_minutes=length,
                       expected_minutes=length,
                       source_event_ids=tuple(r.source_event_ids[0] for r in rows[-length:]))
    item = TODCumulativeObservation(
        snapshot=snap(slot), trading_date_local=day,
        slot_end_local_hhmm=slot.bar_end_utc.astimezone(VN).strftime("%H:%M"),
        session_class=VolumeSessionClass.CONTINUOUS,
        elapsed_trading_minutes=len(rows), cumulative_matched_volume=sum(r.volume for r in rows),
        volume_definition=CumulativeVolumeDefinition.MATCHED_CONTINUOUS_ONLY,
        volume_event_id=slot.source_event_ids[0],
        cumulative_first_known_utc=slot.bar_end_utc,
        cumulative_verified_utc=slot.verified_at_utc,
        volume_policy_version="synthetic-prefix-v1",
    )
    prefix = TODRawPrefix(cal, opening - timedelta(minutes=1),
                          tuple(snap(r) for r in rows),
                          tuple(VolumeBasisWitness(r, VolumeBasis.RAW_MATCHED_SHARES,
                                                   "synthetic-regime", f"evidence-{i}-{j}",
                                                   r.verified_at_utc)
                                for j, r in enumerate(rows)))
    return item, prefix


class RawPrefixTOD358Tests(unittest.TestCase):
    def setUp(self):
        pairs = tuple(raw_prefix_fixture(i) for i in range(21))
        self.t, self.tp = pairs[-1]
        self.p = tuple(x[0] for x in pairs[:-1])
        self.pp = tuple(x[1] for x in pairs[:-1])

    def run_prefix(self, target=None, prefix=None, priors=None, prior_prefixes=None):
        return calculate_rvol_tod20_from_raw_prefixes(
            self.t if target is None else target,
            self.p if priors is None else priors,
            target_prefix=self.tp if prefix is None else prefix,
            prior_prefixes=self.pp if prior_prefixes is None else prior_prefixes,
            as_of_utc=AS_OF,
        )

    def test_m15_raw_prefix_and_double_target(self):
        self.assertEqual(self.run_prefix().value, Decimal("1"))
        t, tp = raw_prefix_fixture(20, multiplier=2)
        result = self.run_prefix(t, tp)
        self.assertEqual(result.value, Decimal("2"))
        self.assertFalse(result.data_certified)
        self.assertFalse(result.actionable)

    def test_m1_m5_and_afternoon_carry(self):
        for tf, afternoon in ((Timeframe.M1, False), (Timeframe.M5, True)):
            pairs = tuple(raw_prefix_fixture(i, tf, afternoon=afternoon) for i in range(21))
            result = self.run_prefix(pairs[-1][0], pairs[-1][1],
                                     tuple(x[0] for x in pairs[:-1]),
                                     tuple(x[1] for x in pairs[:-1]))
            self.assertEqual(result.value, Decimal("1"))

    def test_missing_prior_minute_not_zero_filled(self):
        p = self.pp[0]
        broken = replace(p, minutes=p.minutes[1:], witnesses=p.witnesses[1:])
        self.assertEqual(self.run_prefix(prior_prefixes=(broken,) + self.pp[1:]).state,
                         IndicatorState.BLOCKED)

    def test_unverified_or_late_calendar(self):
        for broken in (replace(self.tp, calendar=replace(self.tp.calendar, verified=False)),
                       replace(self.tp, calendar_verified_at_utc=AS_OF)):
            self.assertEqual(self.run_prefix(prefix=broken).state, IndicatorState.BLOCKED)

    def test_adjusted_volume_and_future_witness(self):
        witness = self.tp.witnesses[0]
        for w in (replace(witness, basis=VolumeBasis.ADJUSTED_SHARES),
                  replace(witness, verified_at_utc=AS_OF)):
            prefix = replace(self.tp, witnesses=(w,) + self.tp.witnesses[1:])
            self.assertEqual(self.run_prefix(prefix=prefix).state, IndicatorState.BLOCKED)

    def test_regime_change_between_days(self):
        p = self.pp[0]
        changed = replace(p, witnesses=tuple(replace(w, share_regime_id="other")
                                             for w in p.witnesses))
        self.assertEqual(self.run_prefix(prior_prefixes=(changed,) + self.pp[1:]).reason,
                         "PRIOR_MINUTE_SOURCE_OR_SHARE_REGIME_MISMATCH")

    def test_claimed_cumulative_does_not_reconcile(self):
        target = replace(self.t, cumulative_matched_volume=self.t.cumulative_matched_volume + 1)
        self.assertEqual(self.run_prefix(target=target).reason,
                         "TARGET_CUMULATIVE_OR_SLOT_OHLCV_EVENT_MISMATCH")

    def test_slot_volume_does_not_reconcile(self):
        row = replace(self.t.snapshot.selected, volume=self.t.snapshot.selected.volume + 1)
        target = replace(self.t, snapshot=snap(row))
        self.assertEqual(self.run_prefix(target=target).reason,
                         "TARGET_CUMULATIVE_OR_SLOT_OHLCV_EVENT_MISMATCH")

    def test_repeated_event_cannot_count_twice(self):
        old = self.tp.minutes[1].selected
        row = replace(old, source_event_ids=self.tp.minutes[0].selected.source_event_ids)
        broken = replace(self.tp, minutes=(self.tp.minutes[0], snap(row)) + self.tp.minutes[2:],
                         witnesses=(self.tp.witnesses[0],
                                    replace(self.tp.witnesses[1], candle=row)) + self.tp.witnesses[2:])
        self.assertEqual(self.run_prefix(prefix=broken).state, IndicatorState.BLOCKED)


if __name__ == "__main__":
    unittest.main()
