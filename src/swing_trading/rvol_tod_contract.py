"""P0.11 source-aligned intraday cumulative-volume RVOL_TOD candidate.

The true same-local-slot denominator is the mean cumulative volume of
20 distinct PRIOR sessions, not 20 prior candles, not RVOL_TF and not
daily volume. All quality claims remain supplied evidence, not SSI
entitlement/calendar validation. NO live signals/trading authority.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum

from .causal_indicators import (
    CausalIndicatorResult, IndicatorState, VolumeSessionClass,
    _source_context, _qualified, VolumeBasis, VolumeBasisWitness,
)
from .market_data import InstrumentClass, PriceBasis, Timeframe
from .replay import require_utc
from .source_quality import ResolvedBarSnapshotV12
from .session_calendar import CalendarSnapshot, SessionType
from .vwap_contract343 import _expected_minutes


_VN_OFFSET = timezone(timedelta(hours=7))
_SUPPORTED_TF = frozenset({Timeframe.M1, Timeframe.M5, Timeframe.M15})


class CumulativeVolumeDefinition(str, Enum):
    MATCHED_CONTINUOUS_ONLY = "MATCHED_CONTINUOUS_ONLY"
    MATCHED_INCLUDING_AUCTIONS = "MATCHED_INCLUDING_AUCTIONS"


@dataclass(frozen=True)
class TODCumulativeObservation:
    """Synthetic-friendly, source-referenced *claim* for one closed slot.

    A complete minute-by-minute source reconstruction/parity proof
    and a versioned official exchange calendar are not provided here.
    """
    snapshot: ResolvedBarSnapshotV12
    trading_date_local: date
    slot_end_local_hhmm: str
    session_class: VolumeSessionClass
    elapsed_trading_minutes: int
    cumulative_matched_volume: int | None
    volume_definition: CumulativeVolumeDefinition
    volume_event_id: str
    cumulative_first_known_utc: datetime
    cumulative_verified_utc: datetime
    volume_policy_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot, ResolvedBarSnapshotV12):
            raise TypeError("v1.2 resolved bar required")
        if not isinstance(self.trading_date_local, date) or isinstance(
            self.trading_date_local, datetime
        ):
            raise TypeError("Explicit local trading date required")
        if (not isinstance(self.slot_end_local_hhmm, str)
                or len(self.slot_end_local_hhmm) != 5
                or self.slot_end_local_hhmm[2] != ":"):
            raise ValueError("Slot must use local HH:MM")
        try:
            hour, minute = map(int, (
                self.slot_end_local_hhmm[:2], self.slot_end_local_hhmm[3:]
            ))
            if not 0 <= hour <= 23 or not 0 <= minute <= 59:
                raise ValueError("Invalid time")
        except (TypeError, ValueError) as exc:
            raise ValueError("Slot must use valid local HH:MM") from exc
        if not isinstance(self.session_class, VolumeSessionClass):
            raise TypeError("Explicit session segment class required")
        if (type(self.elapsed_trading_minutes) is not int
                or self.elapsed_trading_minutes <= 0):
            raise ValueError("Positive explicit elapsed trading minutes required")
        if (self.cumulative_matched_volume is not None
                and (type(self.cumulative_matched_volume) is not int
                     or self.cumulative_matched_volume < 0)):
            raise ValueError("Cumulative volume must be nonnegative int or unknown")
        if not isinstance(self.volume_definition, CumulativeVolumeDefinition):
            raise TypeError("Explicit matched-volume definition required")
        for name in ("volume_event_id", "volume_policy_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(name + " must be explicit nonempty text")
        require_utc(self.cumulative_first_known_utc)
        require_utc(self.cumulative_verified_utc)
        if self.cumulative_verified_utc < self.cumulative_first_known_utc:
            raise ValueError("Cumulative verification predates first knowledge")


def _validate_observation(item, *, as_of_utc, cutoff_utc):
    """Return (row, reason); never silently fix source conflicts."""
    row = _qualified(item.snapshot, as_of_utc, cutoff_utc)
    if row is None:
        return None, "CLOSED_BAR_OR_SOURCE_NOT_QUALIFIED"
    if row.market_bar_key.timeframe not in _SUPPORTED_TF:
        return None, "RVOL_TOD_REQUIRES_NATIVE_INTRADAY_TF"
    local_end = row.bar_end_utc.astimezone(_VN_OFFSET)
    if (local_end.date() != item.trading_date_local
            or local_end.strftime("%H:%M") != item.slot_end_local_hhmm):
        return None, "SLOT_END_NOT_EXCHANGE_LOCAL_CLOCK"
    if item.session_class is VolumeSessionClass.DAILY:
        return None, "DAILY_SESSION_CLASS_NOT_TOD"
    if (item.cumulative_matched_volume is None
            or row.volume is None
            or item.cumulative_matched_volume < row.volume):
        return None, "CUMULATIVE_VOLUME_NOT_SOURCE_USABLE"
    if item.volume_event_id not in row.source_event_ids:
        return None, "CUMULATIVE_EVENT_NOT_LINKED_TO_SOURCE_BAR"
    if (item.cumulative_first_known_utc < row.bar_end_utc
            or item.cumulative_verified_utc < row.verified_at_utc
            or item.cumulative_first_known_utc > cutoff_utc
            or item.cumulative_verified_utc > cutoff_utc):
        return None, "CUMULATIVE_EVIDENCE_NOT_CAUSALLY_KNOWN"
    return row, ""


def calculate_rvol_tod20(
    target: TODCumulativeObservation,
    prior_sessions: tuple[TODCumulativeObservation, ...],
    *,
    as_of_utc: datetime,
) -> CausalIndicatorResult:
    """Source-lineage-gated SAME-LOCAL-SLOT cumulative RVOL (N=20).

    The 20 prior observations must belong to 20 DIFFERENT market dates.
    Their selected price-bar and cumulative snapshots have to be known before
    the target bar STARTS. There is no approval of historical completeness.
    """
    require_utc(as_of_utc)

    def finish(state, reason, value=None, count=0):
        return CausalIndicatorResult(
            "RVOL_TOD20", as_of_utc, state, reason, value, count,
            "RVOL_TOD_SAME_SLOT_20_CANDIDATE_V0_1",
        )

    if not isinstance(target, TODCumulativeObservation):
        return finish(IndicatorState.BLOCKED, "INVALID_TARGET_TYPE")
    if (not isinstance(prior_sessions, tuple)
            or any(not isinstance(x, TODCumulativeObservation) for x in prior_sessions)):
        return finish(IndicatorState.BLOCKED, "INVALID_IMMUTABLE_PRIOR_SESSIONS")
    if len(prior_sessions) != 20:
        return finish(IndicatorState.BLOCKED, "REQUIRE_EXACTLY_20_PRIOR_SESSIONS")

    current, issue = _validate_observation(
        target, as_of_utc=as_of_utc, cutoff_utc=as_of_utc,
    )
    if current is None:
        return finish(IndicatorState.BLOCKED, "TARGET_" + issue)

    cutoff_utc = current.market_bar_key.bar_start_utc
    context = _source_context(current)
    previous_date = None
    previous_end = None
    total = 0
    seen_sessions = set()
    for item in prior_sessions:
        bar, issue = _validate_observation(
            item, as_of_utc=as_of_utc, cutoff_utc=cutoff_utc,
        )
        if bar is None:
            return finish(IndicatorState.BLOCKED, "PRIOR_" + issue)
        if _source_context(bar) != context:
            return finish(IndicatorState.BLOCKED, "PRIOR_SOURCE_BASIS_OR_POLICY_MISMATCH")
        if (item.slot_end_local_hhmm != target.slot_end_local_hhmm
                or item.session_class is not target.session_class
                or item.elapsed_trading_minutes != target.elapsed_trading_minutes
                or item.volume_definition is not target.volume_definition
                or item.volume_policy_version != target.volume_policy_version):
            return finish(IndicatorState.BLOCKED, "LOCAL_SLOT_SEGMENT_OR_VOLUME_POLICY_MISMATCH")
        session_id = bar.market_bar_key.session_period_id
        if (item.trading_date_local >= target.trading_date_local
                or session_id in seen_sessions
                or (previous_date is not None
                    and item.trading_date_local <= previous_date)
                or (previous_end is not None
                    and bar.market_bar_key.bar_start_utc < previous_end)):
            return finish(IndicatorState.BLOCKED, "DUPLICATE_OR_NONPRIOR_MARKET_SESSION")
        seen_sessions.add(session_id)
        previous_date = item.trading_date_local
        previous_end = bar.bar_end_utc
        total += item.cumulative_matched_volume

    if total <= 0:
        return finish(IndicatorState.BLOCKED, "ZERO_PRIOR_CUMULATIVE_DENOMINATOR")
    value = Decimal(target.cumulative_matched_volume) * Decimal(20) / Decimal(total)
    return finish(
        IndicatorState.COMPUTED_UNCALIBRATED,
        "SAME_LOCAL_SLOT_MATH_ONLY_CUMULATIVE_SOURCE_AND_MARKET_UNVERIFIED",
        value, 21,
    )


@dataclass(frozen=True)
class TODRawPrefix:
    """Supplied calendar and complete raw M1 prefix, not issuer certification."""
    calendar: CalendarSnapshot
    calendar_verified_at_utc: datetime
    minutes: tuple[ResolvedBarSnapshotV12, ...]
    witnesses: tuple[VolumeBasisWitness, ...]


def _prefix_scope(row):
    key, obs, rev = row.market_bar_key, row.observation_key, row.observation_revision
    return (key.instrument_id, key.exchange, key.instrument_class,
            key.price_basis, key.calendar_version, obs.project_id,
            obs.provider_id, obs.source_stream_id, rev.adjustment_revision)


def _prefix_expected(item, row, prefix):
    if not isinstance(prefix, TODRawPrefix):
        return None
    calendar = prefix.calendar
    if not isinstance(calendar, CalendarSnapshot) or not calendar.verified:
        return None
    require_utc(prefix.calendar_verified_at_utc)
    if prefix.calendar_verified_at_utc > item.cumulative_verified_utc:
        return None
    if item.session_class is not VolumeSessionClass.CONTINUOUS:
        return None
    if item.volume_definition is not CumulativeVolumeDefinition.MATCHED_CONTINUOUS_ONLY:
        return None
    key = row.market_bar_key
    duration = {Timeframe.M1: 1, Timeframe.M5: 5, Timeframe.M15: 15}.get(key.timeframe)
    if (duration is None or key.price_basis is not PriceBasis.RAW
            or key.instrument_class is not InstrumentClass.STOCK
            or row.bar_end_utc - key.bar_start_utc != timedelta(minutes=duration)
            or calendar.resolve_intraday(key, row.bar_end_utc) is None):
        return None
    continuous = [s for s in calendar.sessions if s.session_type is SessionType.CONTINUOUS]
    if not continuous:
        return None
    expected = _expected_minutes(calendar, min(s.start_utc for s in continuous), row.bar_end_utc)
    if expected is None or len(expected) != item.elapsed_trading_minutes:
        return None
    if not isinstance(prefix.minutes, tuple) or not isinstance(prefix.witnesses, tuple):
        return None
    if len(prefix.minutes) != len(expected) or len(prefix.witnesses) != len(expected):
        return None
    return expected


def _minute_matches(row, slot, calendar, minute, session_id):
    key = row.market_bar_key
    return (key.timeframe is Timeframe.M1
            and key.bar_start_utc == minute
            and row.bar_end_utc == minute + timedelta(minutes=1)
            and key.session_period_id == session_id
            and calendar.resolve_intraday(key, row.bar_end_utc) is not None
            and row.observed_minutes == row.expected_minutes == 1
            and _prefix_scope(row) == _prefix_scope(slot))


def _prefix_witness_ok(row, witness, cutoff):
    return (isinstance(witness, VolumeBasisWitness)
            and witness.candle == row
            and witness.basis is VolumeBasis.RAW_MATCHED_SHARES
            and row.verified_at_utc <= witness.verified_at_utc <= cutoff)


def _prefix_rows(item, slot, prefix, expected, as_of):
    rows, events = [], set()
    scope = None
    for snapshot, witness, (minute, session_id) in zip(
            prefix.minutes, prefix.witnesses, expected):
        row = _qualified(snapshot, as_of, item.cumulative_verified_utc)
        if row is None or not _minute_matches(row, slot, prefix.calendar, minute, session_id):
            return None, None
        if not _prefix_witness_ok(row, witness, item.cumulative_verified_utc):
            return None, None
        now = (_source_context(row), witness.share_regime_id)
        if scope is not None and now != scope:
            return None, None
        ids = set(row.source_event_ids)
        if not ids or len(ids) != len(row.source_event_ids) or events.intersection(ids):
            return None, None
        events.update(ids)
        scope = now
        rows.append(row)
    return rows, scope


def _prefix_reconciles(item, slot, rows):
    if sum(row.volume for row in rows) != item.cumulative_matched_volume:
        return False
    selected = [row for row in rows
                if row.market_bar_key.bar_start_utc >= slot.market_bar_key.bar_start_utc]
    if not selected:
        return False
    if slot.market_bar_key.timeframe is Timeframe.M1:
        return len(selected) == 1 and selected[0] == slot
    ids = {event for row in selected for event in row.source_event_ids}
    return (ids == set(slot.source_event_ids)
            and len(ids) == len(slot.source_event_ids)
            and sum(row.volume for row in selected) == slot.volume
            and selected[0].open == slot.open and selected[-1].close == slot.close
            and max(row.high for row in selected) == slot.high
            and min(row.low for row in selected) == slot.low)


def _validate_prefix(item, prefix, as_of, cutoff):
    slot, issue = _validate_observation(item, as_of_utc=as_of, cutoff_utc=cutoff)
    if slot is None:
        return None, issue
    expected = _prefix_expected(item, slot, prefix)
    if expected is None:
        return None, "CALENDAR_OR_COMPLETE_PREFIX_SCOPE_MISMATCH"
    rows, scope = _prefix_rows(item, slot, prefix, expected, as_of)
    if rows is None:
        return None, "MINUTE_RAW_VOLUME_WITNESS_OR_LINEAGE_UNVERIFIED"
    if not _prefix_reconciles(item, slot, rows):
        return None, "CUMULATIVE_OR_SLOT_OHLCV_EVENT_MISMATCH"
    return scope, ""


def calculate_rvol_tod20_from_raw_prefixes(
    target: TODCumulativeObservation,
    prior_sessions: tuple[TODCumulativeObservation, ...],
    *,
    target_prefix: TODRawPrefix,
    prior_prefixes: tuple[TODRawPrefix, ...],
    as_of_utc: datetime,
) -> CausalIndicatorResult:
    """Opt-in exact continuous M1 reconstruction; no source or trade approval."""
    require_utc(as_of_utc)

    def blocked(reason):
        return CausalIndicatorResult(
            "RVOL_TOD20", as_of_utc, IndicatorState.BLOCKED, reason, None, 0,
            "RVOL_TOD_RAW_M1_PREFIX_V0_1",
        )

    legacy = calculate_rvol_tod20(target, prior_sessions, as_of_utc=as_of_utc)
    if legacy.state is IndicatorState.BLOCKED:
        return blocked(legacy.reason)
    if not isinstance(prior_prefixes, tuple) or len(prior_prefixes) != 20:
        return blocked("REQUIRE_20_IMMUTABLE_PRIOR_PREFIXES")
    scope, issue = _validate_prefix(target, target_prefix, as_of_utc, as_of_utc)
    if scope is None:
        return blocked("TARGET_" + issue)
    cutoff = target.snapshot.selected.market_bar_key.bar_start_utc
    for item, prefix in zip(prior_sessions, prior_prefixes):
        prior_scope, issue = _validate_prefix(item, prefix, as_of_utc, cutoff)
        if prior_scope is None:
            return blocked("PRIOR_" + issue)
        if prior_scope != scope:
            return blocked("PRIOR_MINUTE_SOURCE_OR_SHARE_REGIME_MISMATCH")
    return CausalIndicatorResult(
        legacy.indicator_id, legacy.as_of_utc, legacy.state, legacy.reason,
        legacy.value, legacy.used_bar_count, "RVOL_TOD_RAW_M1_PREFIX_V0_1",
    )
