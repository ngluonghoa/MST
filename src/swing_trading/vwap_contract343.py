"""Session/anchored VWAP arithmetic, continuous-only candidate v0.1.

Source-locked 01 §24, P14 and 05 L2: verified matched value, never proxy.
This is an opt-in feature, not a live source, calendar or strategy approval.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

from .causal_indicators import _qualified, _source_context
from .market_data import InstrumentClass, PriceBasis, Timeframe
from .replay import require_utc
from .session_calendar import CalendarSnapshot, SessionType
from .source_quality import ResolvedBarSnapshotV12


class TurnoverMeaning(str, Enum):
    MATCHED_VND = "MATCHED_VND"
    CLOSE_TIMES_VOLUME = "CLOSE_TIMES_VOLUME"
    OHLC_PROXY = "OHLC_PROXY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TurnoverObservation:
    snapshot: ResolvedBarSnapshotV12
    meaning: TurnoverMeaning
    source_event_id: str
    source_revision: str
    verified_at_utc: datetime
    semantics_verified: bool


@dataclass(frozen=True)
class VwapAnchor:
    event_id: str
    source_revision: str
    start_utc: datetime
    first_known_utc: datetime
    verified_at_utc: datetime


@dataclass(frozen=True)
class VwapResult:
    indicator_id: str
    reason: str
    value: Decimal | None
    used_bar_count: int
    anchor_event_id: str | None
    anchor_revision: str | None
    data_certified: bool = False
    actionable: bool = False

    def __post_init__(self):
        if self.data_certified is not False or self.actionable is not False:
            raise ValueError("No VWAP source or trading certification")


def _expected_minutes(calendar, start, through):
    """Caller-supplied calendar, not an exchange attestation."""
    sessions = sorted(calendar.sessions, key=lambda s: s.start_utc)
    continuous = [s for s in sessions if s.session_type is SessionType.CONTINUOUS]
    if not continuous or any(not s.verified for s in continuous):
        return None
    expected = []
    for s in continuous:
        delta = s.end_utc - s.start_utc
        if delta % timedelta(minutes=1):
            return None
        for i in range(delta // timedelta(minutes=1)):
            t = s.start_utc + timedelta(minutes=i)
            if start <= t < through:
                expected.append((t, s.session_id))
    if not expected or expected[0][0] != start:
        return None
    if expected[-1][0] + timedelta(minutes=1) != through:
        return None
    return expected


def _turnover_issue(item, row, as_of):
    if item.meaning is not TurnoverMeaning.MATCHED_VND:
        return "TURNOVER_NOT_EXACT_MATCHED"
    if item.semantics_verified is not True:
        return "TURNOVER_SEMANTICS_UNVERIFIED"
    if (not item.source_event_id or item.source_event_id not in row.source_event_ids
            or item.source_revision != row.observation_revision.source_revision_or_payload_digest):
        return "TURNOVER_REVISION_OR_EVENT_MISMATCH"
    require_utc(item.verified_at_utc)
    if not row.verified_at_utc <= item.verified_at_utc <= as_of:
        return "TURNOVER_NOT_CAUSALLY_VERIFIED"
    if row.matched_value is None:
        return "MATCHED_VALUE_MISSING"
    if not row.low * row.volume <= row.matched_value <= row.high * row.volume:
        return "MATCHED_VALUE_OUTSIDE_OHLC_VOLUME_BOUNDS"
    return ""


def _anchor_issue(anchor, first, as_of):
    for value in (anchor.start_utc, anchor.first_known_utc, anchor.verified_at_utc):
        require_utc(value)
    if not anchor.start_utc <= anchor.first_known_utc <= anchor.verified_at_utc <= as_of:
        return "ANCHOR_NOT_CAUSALLY_KNOWN"
    if (not anchor.event_id or anchor.event_id not in first.source_event_ids
            or anchor.source_revision != first.observation_revision.source_revision_or_payload_digest
            or anchor.start_utc != first.market_bar_key.bar_start_utc):
        return "ANCHOR_EVENT_OR_REVISION_MISMATCH"
    return ""


def calculate_continuous_vwap(observations, *, calendar, through_utc,
                              as_of_utc, anchor=None):
    """Calculate on exact continuous M1 prefix, or same-day causal anchor.

    No lunch or auction mixing; zero-volume observed bars allowed only with
    zero turnover. Gaps never zero-filled. Caller evidence is not an issuer
    signature. Anchors are explicit event/revision inputs, not auto-selected.
    """
    require_utc(as_of_utc)
    require_utc(through_utc)
    anchored = isinstance(anchor, VwapAnchor)
    indicator = "ANCHORED_VWAP" if anchored else "SESSION_VWAP"

    def finish(reason, value=None, count=0):
        return VwapResult(indicator, reason, value, count,
                          anchor.event_id if anchored else None,
                          anchor.source_revision if anchored else None)

    if anchor is not None and not anchored:
        return finish("INVALID_ANCHOR")
    if not isinstance(calendar, CalendarSnapshot) or not calendar.verified:
        return finish("CALENDAR_UNVERIFIED")
    if not isinstance(observations, tuple) or not observations:
        return finish("IMMUTABLE_NONEMPTY_INPUT_REQUIRED")
    if any(not isinstance(x, TurnoverObservation) for x in observations):
        return finish("INVALID_TURNOVER_OBSERVATION")
    if through_utc > as_of_utc:
        return finish("FUTURE_WINDOW")
    continuous = [s for s in calendar.sessions if s.session_type is SessionType.CONTINUOUS]
    if not continuous:
        return finish("NO_CONTINUOUS_SESSION")
    start = anchor.start_utc if anchored else min(s.start_utc for s in continuous)
    require_utc(start)
    expected = _expected_minutes(calendar, start, through_utc)
    if expected is None or len(expected) != len(observations):
        return finish("INCOMPLETE_OR_INVALID_MINUTE_SCOPE")
    rows = []
    context = None
    used_events = set()
    for item, (minute, session_id) in zip(observations, expected):
        row = _qualified(item.snapshot, as_of_utc, as_of_utc)
        if row is None:
            return finish("BAR_NOT_QUALIFIED")
        key = row.market_bar_key
        if (key.timeframe is not Timeframe.M1 or key.price_basis is not PriceBasis.RAW
                or key.instrument_class is not InstrumentClass.STOCK
                or key.bar_start_utc != minute
                or row.bar_end_utc != minute + timedelta(minutes=1)
                or key.session_period_id != session_id
                or calendar.resolve_intraday(key, row.bar_end_utc) is None
                or row.observed_minutes != 1 or row.expected_minutes != 1):
            return finish("MINUTE_IDENTITY_OR_SESSION_MISMATCH")
        scope = _source_context(row)
        if context is not None and context != scope:
            return finish("SOURCE_BASIS_OR_POLICY_MISMATCH")
        context = scope
        issue = _turnover_issue(item, row, as_of_utc)
        if issue:
            return finish(issue)
        if item.source_event_id in used_events:
            return finish("DUPLICATE_TURNOVER_EVENT")
        used_events.add(item.source_event_id)
        rows.append(row)
    if anchored:
        issue = _anchor_issue(anchor, rows[0], as_of_utc)
        if issue:
            return finish(issue)
    volume = sum(row.volume for row in rows)
    if volume == 0:
        return finish("ZERO_VOLUME_DENOMINATOR")
    value = sum((row.matched_value for row in rows), Decimal(0)) / Decimal(volume)
    return finish("MATCHED_TURNOVER_MATH_ONLY_NO_SOURCE_CERTIFICATION", value, len(rows))
