"""§210 HOSE official regular-board clock geometry; SSI minute labels UNVERIFIED.

HOSE exchange guidance (Feb 2026):
https://staticfile.hsx.vn/Uploads/UploadDocuments/2453338/HTGD_Quy%20dinh%20can%20biet%20khi%20GDCK%20tren%20HOSE_T2.2026.pdf
Regular stock matching: ATO 09:00–09:15, continuous 09:15–11:30,
lunch 11:30–13:00, continuous 13:00–14:30, ATC 14:30–14:45.
Restricted stocks have periodic matching instead. This public schedule is
NOT a date-specific exchange holiday/status attestation.

SSI 2026-11-17 observed intraday_stock_infor:
  latest=true uses MM/DD/YYYY, range=1d uses DD/MM/YYYY;
  range=1d had 225 continuous minute labels plus special 14:45 auction
  and summed numerically to SSI D1. Provider did NOT attest minute LABEL
  semantics (start/end/last), first-known clocks, date-mode contract,
  packet completeness, entitlement to retention, or provider bar closure.

This module accepts caller responses only. All M15/H1 candidate windows are
LABEL GEOMETRY, never market bar keys, resolved candles, signals or trades.
Source rows stay in memory and never flow to public reports/cache.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from enum import Enum

from .market_data import Timeframe
from .replay import require_utc
from .ssi_intraday_session_probe209 import (
    MinuteProbeState, inspect_ssi_minute_session_reference,
)

_TZ = timezone(timedelta(hours=7))
SCHEMA = "mst.hose.public_schedule_candidate_202602.v0.1"
OFFICIAL_HOSE_SCHEDULE = (
    "https://staticfile.hsx.vn/Uploads/UploadDocuments/2453338/"
    "HTGD_Quy%20dinh%20can%20biet%20khi%20GDCK%20tren%20HOSE_T2.2026.pdf"
)
REGULAR_WINDOWS = (
    (9 * 60 + 15, 11 * 60 + 30, "MORNING"),
    (13 * 60, 14 * 60 + 30, "AFTERNOON"),
)
EXPECTED_CONTINUOUS_MINUTES = 225


class SsiQueryMode(str, Enum):
    RANGE_DAY_FIRST_OBSERVED = "RANGE_DAY_FIRST_OBSERVED"
    LATEST_MONTH_FIRST_OBSERVED = "LATEST_MONTH_FIRST_OBSERVED"


class ClockPhase(str, Enum):
    ATO = "ATO"
    CONTINUOUS_AM = "CONTINUOUS_AM"
    LUNCH = "LUNCH"
    CONTINUOUS_PM = "CONTINUOUS_PM"
    ATC = "ATC"
    POST_ATC = "POST_ATC"
    OUTSIDE = "OUTSIDE"


class WindowLabelState(str, Enum):
    LABELS_PRESENT_UNVERIFIED = "LABELS_PRESENT_UNVERIFIED"
    LABELS_MISSING_UNCLASSIFIED = "LABELS_MISSING_UNCLASSIFIED"
    PARTIAL_SESSION_WINDOW = "PARTIAL_SESSION_WINDOW"


class HoseSessionState(str, Enum):
    BLOCKED = "BLOCKED"
    OBSERVED_SCHEDULE_SHAPE_UNVERIFIED = "OBSERVED_SCHEDULE_SHAPE_UNVERIFIED"
    MISSING_OR_EXTRA_LABELS_UNVERIFIED = "MISSING_OR_EXTRA_LABELS_UNVERIFIED"


class HoseClockDenied(ValueError):
    """Error codes are fixed to avoid leaking private vendor prices."""


def _clock_minutes(value: time) -> int:
    if type(value) is not time or value.tzinfo is not None:
        raise HoseClockDenied("MST_210_LOCAL_CLOCK_INVALID")
    if value.second or value.microsecond:
        raise HoseClockDenied("MST_210_EXPECT_MINUTE_LABEL")
    return value.hour * 60 + value.minute


def schedule_phase(local_clock: time) -> ClockPhase:
    """Classify local HOSE clock, NOT an authenticated stock observation."""
    minute = _clock_minutes(local_clock)
    if 9 * 60 <= minute < 9 * 60 + 15:
        return ClockPhase.ATO
    if 9 * 60 + 15 <= minute < 11 * 60 + 30:
        return ClockPhase.CONTINUOUS_AM
    if 11 * 60 + 30 <= minute < 13 * 60:
        return ClockPhase.LUNCH
    if 13 * 60 <= minute < 14 * 60 + 30:
        return ClockPhase.CONTINUOUS_PM
    if 14 * 60 + 30 <= minute < 14 * 60 + 45:
        return ClockPhase.ATC
    if 14 * 60 + 45 <= minute < 15 * 60:
        return ClockPhase.POST_ATC
    return ClockPhase.OUTSIDE


def inspect_mode_scoped_ssi_label(
    raw: str, *, session_day: date, mode: SsiQueryMode,
) -> tuple[time, ClockPhase]:
    """Keep SSI range-vs-latest date ordering separate and UNVERIFIED."""
    if (type(raw) is not str or len(raw) != 19
            or not isinstance(mode, SsiQueryMode)
            or type(session_day) is not date):
        raise HoseClockDenied("MST_210_MODE_OR_LABEL_INVALID")
    fmt = ("%d/%m/%Y %H:%M:%S" if mode is SsiQueryMode.RANGE_DAY_FIRST_OBSERVED
           else "%m/%d/%Y %H:%M:%S")
    try:
        local = datetime.strptime(raw, fmt)
    except ValueError:
        raise HoseClockDenied("MST_210_MODE_LABEL_DATE_CONFLICT") from None
    if local.date() != session_day:
        raise HoseClockDenied("MST_210_MODE_LABEL_OTHER_SESSION")
    if local.second or local.microsecond:
        raise HoseClockDenied("MST_210_LABEL_NOT_MINUTE")
    return local.time(), schedule_phase(local.time())


def _hhmm(n: int) -> str:
    return f"{n//60:02d}:{n%60:02d}"


@dataclass(frozen=True)
class CandidateWindow:
    timeframe: Timeframe
    session: str
    start_local: str
    end_local: str
    expected_labels: int
    observed_labels: int
    missing_labels: int
    state: WindowLabelState
    provider_clock_attested: bool = False
    provider_first_known_attested: bool = False
    price_aggregation_approved: bool = False
    action_eligible: bool = False

    def __post_init__(self) -> None:
        if (self.timeframe not in (Timeframe.M15, Timeframe.H1)
                or self.session not in ("MORNING", "AFTERNOON")
                or not isinstance(self.state, WindowLabelState)
                or type(self.expected_labels) is not int
                or type(self.observed_labels) is not int
                or type(self.missing_labels) is not int
                or not 1 <= self.expected_labels <= 60
                or not 0 <= self.observed_labels <= self.expected_labels
                or self.missing_labels != self.expected_labels-self.observed_labels
                or self.provider_clock_attested is not False
                or self.provider_first_known_attested is not False
                or self.price_aggregation_approved is not False
                or self.action_eligible is not False):
            raise HoseClockDenied("MST_210_WINDOW_AUTHORITY_OR_SHAPE")
        for label in (self.start_local, self.end_local):
            if (type(label) is not str or len(label)!=5
                    or not label[:2].isdigit() or not label[3:].isdigit()
                    or label[2] != ":"):
                raise HoseClockDenied("MST_210_WINDOW_LABEL_INVALID")
        start = int(self.start_local[:2])*60+int(self.start_local[-2:])
        end = int(self.end_local[:2])*60+int(self.end_local[-2:])
        if not start < end or end-start != self.expected_labels:
            raise HoseClockDenied("MST_210_WINDOW_SPAN_MISMATCH")
        if self.state is WindowLabelState.LABELS_PRESENT_UNVERIFIED:
            if self.missing_labels:
                raise HoseClockDenied("MST_210_PRESENT_WINDOW_HAS_MISSING_LABELS")
        elif self.state is WindowLabelState.LABELS_MISSING_UNCLASSIFIED:
            if not self.missing_labels:
                raise HoseClockDenied("MST_210_MISSING_WINDOW_WAS_COMPLETE")
        elif self.expected_labels == (15 if self.timeframe is Timeframe.M15 else 60):
            raise HoseClockDenied("MST_210_PARTIAL_WINDOW_WAS_FULL_LENGTH")


@dataclass(frozen=True)
class HoseCandidateSession:
    schema: str
    symbol: str
    trading_day: date
    state: HoseSessionState
    regular_minute_label_count: int
    missing_expected_labels: int
    unexpected_label_count: int
    auction_1445_captured: bool
    m15: tuple[CandidateWindow, ...]
    h1: tuple[CandidateWindow, ...]
    reason: str
    official_schedule_reference: str = OFFICIAL_HOSE_SCHEDULE
    venue_day_and_board_regime_verified: bool = False
    provider_minute_label_semantics_verified: bool = False
    first_known_and_revision_verified: bool = False
    history_pagination_verified: bool = False
    source_retention_rights_verified: bool = False
    m15_source_qualified: bool = False
    h1_source_qualified: bool = False
    action_eligible: bool = False

    def __post_init__(self) -> None:
        if (self.schema != SCHEMA or type(self.symbol) is not str
                or not self.symbol.isalpha() or len(self.symbol)!=3
                or not self.symbol.isupper()
                or type(self.trading_day) is not date
                or not isinstance(self.state, HoseSessionState)
                or type(self.regular_minute_label_count) is not int
                or type(self.missing_expected_labels) is not int
                or type(self.unexpected_label_count) is not int
                or min(self.regular_minute_label_count,
                       self.missing_expected_labels,self.unexpected_label_count)<0
                or type(self.auction_1445_captured) is not bool
                or type(self.m15) is not tuple or type(self.h1) is not tuple
                or type(self.reason) is not str or not self.reason
                or self.official_schedule_reference != OFFICIAL_HOSE_SCHEDULE
                or any((self.venue_day_and_board_regime_verified,
                        self.provider_minute_label_semantics_verified,
                        self.first_known_and_revision_verified,
                        self.history_pagination_verified,
                        self.source_retention_rights_verified,
                        self.m15_source_qualified,self.h1_source_qualified,
                        self.action_eligible))):
            raise HoseClockDenied("MST_210_CANDIDATE_SESSION_NOT_QUALIFIED")
        if self.state is HoseSessionState.BLOCKED:
            if (self.m15 or self.h1 or self.regular_minute_label_count
                    or self.missing_expected_labels
                    or self.unexpected_label_count or self.auction_1445_captured):
                raise HoseClockDenied("MST_210_BLOCKED_WITH_FABRICATED_BARS")
        elif len(self.m15)!=15 or len(self.h1)!=5:
            raise HoseClockDenied("MST_210_WINDOW_MATRIX_INCOMPLETE")


def inspect_hose_ssi_regular_schedule_candidate(
    response: dict, *, symbol: str, trading_day: date,
    as_of_utc: datetime, daily_matched_volume: int | None,
    regular_board_regime_independently_attested: bool = False,
) -> HoseCandidateSession:
    """Window LABEL counts, not OHLC candles and never a trading signal.

    We refuse to infer regular-board eligibility, even for a familiar symbol.
    The caller must explicitly supply a FALSE attestation bit. It cannot
    truthify itself; a future genuinely verified source uses another API.
    A partial minute interval is missing data UNKNOWN, never zero volume.
    """
    require_utc(as_of_utc)
    if regular_board_regime_independently_attested is not False:
        raise HoseClockDenied("MST_210_UNVERIFIED_BOARD_REGIME_CLAIM")
    if type(trading_day) is not date or type(symbol) is not str:
        raise HoseClockDenied("MST_210_SYMBOL_DAY_INVALID")
    # This is a CONDITIONAL regular-board shape for comparison only.
    checked = inspect_ssi_minute_session_reference(
        response, symbol=symbol, trading_day=trading_day,
        as_of_utc=as_of_utc, daily_matched_volume=daily_matched_volume,
    )

    def blocked(reason: str) -> HoseCandidateSession:
        return HoseCandidateSession(
            SCHEMA,symbol,trading_day,HoseSessionState.BLOCKED,
            0,0,0,False,(),(),reason,
        )
    if checked.state is MinuteProbeState.BLOCKED:
        return blocked("SSI_INTRADAY_"+checked.timestamp_policy_reason)
    if as_of_utc.astimezone(_TZ).date() < trading_day:
        return blocked("SESSION_NOT_YET_OBSERVED_AS_OF")
    points = set()
    extras = 0
    auction = False
    latest_seen = None
    for row in response["data"]["ticks"]:
        local,phase=inspect_mode_scoped_ssi_label(
            row["trading_date"],session_day=trading_day,
            mode=SsiQueryMode.RANGE_DAY_FIRST_OBSERVED,
        )
        minute = _clock_minutes(local)
        # Provider labels must not originate in the future even as candidate.
        label_dt=datetime.combine(trading_day,local,tzinfo=_TZ)
        if label_dt.astimezone(timezone.utc)>as_of_utc:
            return blocked("SOURCE_LABEL_FUTURE_VS_AS_OF")
        latest_seen = minute if latest_seen is None else max(latest_seen,minute)
        if phase in (ClockPhase.CONTINUOUS_AM,ClockPhase.CONTINUOUS_PM):
            points.add(minute)
        elif minute==14*60+45:
            auction=True  # ATC execution label at boundary, not 14:45 regular bar
        else:
            extras+=1

    # A future missing 14:45 row is not always an error in a pre-close probe.
    # But before 14:45 this function can never classify full-session output.
    if as_of_utc.astimezone(_TZ).date()==trading_day and (
        as_of_utc.astimezone(_TZ).hour*60
        +as_of_utc.astimezone(_TZ).minute < 14*60+45
    ):
        return blocked("DAY_SESSION_STILL_IN_PROGRESS")
    windows = {}
    for tf,step in ((Timeframe.M15,15),(Timeframe.H1,60)):
        out=[]
        for start,end,session in REGULAR_WINDOWS:
            for a in range(start,end,step):
                b=min(a+step,end)
                count=sum(n in points for n in range(a,b))
                missing=(b-a)-count
                if b-a < step:
                    state=WindowLabelState.PARTIAL_SESSION_WINDOW
                elif missing:
                    state=WindowLabelState.LABELS_MISSING_UNCLASSIFIED
                else:
                    state=WindowLabelState.LABELS_PRESENT_UNVERIFIED
                out.append(CandidateWindow(
                    tf,session,_hhmm(a),_hhmm(b),b-a,count,
                    missing,state,
                ))
        windows[tf]=tuple(out)
    missing = EXPECTED_CONTINUOUS_MINUTES-len(points)
    if missing<0:
        raise HoseClockDenied("MST_210_OVERFULL_EXPECTED_SESSION")
    state=(HoseSessionState.OBSERVED_SCHEDULE_SHAPE_UNVERIFIED
           if missing==0 and extras==0 and auction
           else HoseSessionState.MISSING_OR_EXTRA_LABELS_UNVERIFIED)
    return HoseCandidateSession(
        SCHEMA,symbol,trading_day,state,len(points),missing,extras,
        auction,windows[Timeframe.M15],windows[Timeframe.H1],
        "CLOCK_SLOT_GEOMETRY_ONLY_NO_PROVIDER_LABEL_OR_BAR_FINALITY",
    )

# §211: Compare label-START and label-END *hypotheses* without selecting one.
# SSI MCP minute labels and the distinct official FastConnect product have not
# established a publisher-attested label meaning, issuer first-known, stock
# board-regime/day calendar, or licensed historical source revisions.
SCHEMA_211 = "mst.ssi.minute_label_dual_hypothesis.v0.1"


class MinuteLabelMeaning211(str, Enum):
    START_UNVERIFIED = "MINUTE_START_UNVERIFIED"
    END_UNVERIFIED = "MINUTE_END_UNVERIFIED"


@dataclass(frozen=True)
class LabelHypothesis211:
    meaning: MinuteLabelMeaning211
    candidate: HoseCandidateSession
    input_row_count: int
    out_of_continuous_count: int
    timestamp_semantics_confirmed: bool = False
    zero_volume_imputation_allowed: bool = False
    carry_forward_allowed: bool = False
    provider_correction_first_known_confirmed: bool = False
    action_eligible: bool = False

    def __post_init__(self) -> None:
        if (not isinstance(self.meaning, MinuteLabelMeaning211)
                or not isinstance(self.candidate, HoseCandidateSession)
                or self.candidate.state is HoseSessionState.BLOCKED
                or type(self.input_row_count) is not int
                or type(self.out_of_continuous_count) is not int
                or self.input_row_count < 1 or self.out_of_continuous_count < 0
                or (self.candidate.regular_minute_label_count
                    + self.out_of_continuous_count
                    + int(self.candidate.auction_1445_captured)
                    != self.input_row_count)
                or self.candidate.unexpected_label_count
                    != self.out_of_continuous_count
                or (self.meaning is MinuteLabelMeaning211.START_UNVERIFIED
                    and self.candidate.reason
                    != "CLOCK_SLOT_GEOMETRY_ONLY_NO_PROVIDER_LABEL_OR_BAR_FINALITY")
                or (self.meaning is MinuteLabelMeaning211.END_UNVERIFIED
                    and self.candidate.reason
                    != "END_LABEL_IS_UNVERIFIED_HYPOTHESIS_NOT_PROVIDER_SEMANTICS")
                or self.timestamp_semantics_confirmed is not False
                or self.zero_volume_imputation_allowed is not False
                or self.carry_forward_allowed is not False
                or self.provider_correction_first_known_confirmed is not False
                or self.action_eligible is not False):
            raise HoseClockDenied("MST_211_HYPOTHESIS_CLAIMS_SOURCE_AUTHORITY")


@dataclass(frozen=True)
class DualLabelComparison211:
    schema: str
    start: LabelHypothesis211
    end: LabelHypothesis211
    selected_meaning: None = None
    source_timestamp_attested: bool = False
    venue_symbol_day_attested: bool = False
    licensed_revision_history_attested: bool = False
    source_m15_h1_eligible: bool = False
    action_eligible: bool = False

    def __post_init__(self) -> None:
        if (self.schema != SCHEMA_211
                or not isinstance(self.start, LabelHypothesis211)
                or not isinstance(self.end, LabelHypothesis211)
                or self.start.meaning is not MinuteLabelMeaning211.START_UNVERIFIED
                or self.end.meaning is not MinuteLabelMeaning211.END_UNVERIFIED
                or self.start.input_row_count != self.end.input_row_count
                or self.start.candidate.symbol != self.end.candidate.symbol
                or self.start.candidate.trading_day != self.end.candidate.trading_day
                or self.selected_meaning is not None
                or self.source_timestamp_attested is not False
                or self.venue_symbol_day_attested is not False
                or self.licensed_revision_history_attested is not False
                or self.source_m15_h1_eligible is not False
                or self.action_eligible is not False):
            raise HoseClockDenied("MST_211_COMPARISON_CANNOT_SELECT_OR_AUTHORIZE")


def inspect_ssi_dual_label_hypotheses211(
    response: dict, *, symbol: str, trading_day: date,
    as_of_utc: datetime, daily_matched_volume: int | None,
) -> DualLabelComparison211:
    """Compare plausible SSI range-label minute START vs END placements.

    A timestamp ending a minute hypothetically belongs to [label-1m,label).
    Exact 14:45 is isolated as an ATC *candidate* under either hypothesis,
    never shifted into regular continuous trading. Lunch/ATO/ATC spillovers
    remain unclassified, and absent labels are not assumed zero-volume.
    Better coverage is NOT publisher verification or a chosen clock policy.

    Deliberately returns only counts, window boundaries and false authorities:
    no source OHLC, MarketBarKey, first-known, backtest or trading outcome.
    """
    start = inspect_hose_ssi_regular_schedule_candidate(
        response, symbol=symbol, trading_day=trading_day,
        as_of_utc=as_of_utc, daily_matched_volume=daily_matched_volume,
    )
    if start.state is HoseSessionState.BLOCKED:
        raise HoseClockDenied("MST_211_SOURCE_DAY_NOT_ELIGIBLE_FOR_COMPARISON")

    rows = response["data"]["ticks"]  # shape and ordering validated by §209
    end_slots: set[int] = set()
    end_spillover = 0
    for row in rows:
        label, _ = inspect_mode_scoped_ssi_label(
            row["trading_date"], session_day=trading_day,
            mode=SsiQueryMode.RANGE_DAY_FIRST_OBSERVED,
        )
        minute = _clock_minutes(label)
        if minute == 14*60+45:
            continue  # Never claim an ATC print is a regular one-minute bar.
        hypothetical_bucket = minute-1
        within_continuous = any(
            lo <= hypothetical_bucket < hi for lo,hi,_ in REGULAR_WINDOWS
        )
        if within_continuous:
            end_slots.add(hypothetical_bucket)
        else:
            end_spillover += 1

    def windows_for(
        slots: set[int], tf: Timeframe, step: int,
    ) -> tuple[CandidateWindow, ...]:
        windows = []
        for lo,hi,session in REGULAR_WINDOWS:
            for start_minute in range(lo,hi,step):
                end_minute = min(start_minute+step,hi)
                count = sum(m in slots for m in range(start_minute,end_minute))
                length = end_minute-start_minute
                if count < length:
                    state = WindowLabelState.LABELS_MISSING_UNCLASSIFIED
                elif length < step:
                    state = WindowLabelState.PARTIAL_SESSION_WINDOW
                else:
                    state = WindowLabelState.LABELS_PRESENT_UNVERIFIED
                windows.append(CandidateWindow(
                    tf,session,_hhmm(start_minute),_hhmm(end_minute),
                    length,count,length-count,state,
                ))
        return tuple(windows)

    missing = EXPECTED_CONTINUOUS_MINUTES-len(end_slots)
    if missing < 0:
        raise HoseClockDenied("MST_211_HYPOTHESIS_EXCESS_MINUTE_SLOTS")
    end_state = (
        HoseSessionState.OBSERVED_SCHEDULE_SHAPE_UNVERIFIED
        if missing == 0 and end_spillover == 0 and start.auction_1445_captured
        else HoseSessionState.MISSING_OR_EXTRA_LABELS_UNVERIFIED
    )
    hypothetical_end = HoseCandidateSession(
        SCHEMA, symbol, trading_day, end_state, len(end_slots),
        missing, end_spillover, start.auction_1445_captured,
        windows_for(end_slots, Timeframe.M15, 15),
        windows_for(end_slots, Timeframe.H1, 60),
        "END_LABEL_IS_UNVERIFIED_HYPOTHESIS_NOT_PROVIDER_SEMANTICS",
    )
    return DualLabelComparison211(
        SCHEMA_211,
        LabelHypothesis211(
            MinuteLabelMeaning211.START_UNVERIFIED, start,
            len(rows),start.unexpected_label_count,
        ),
        LabelHypothesis211(
            MinuteLabelMeaning211.END_UNVERIFIED,hypothetical_end,
            len(rows),end_spillover,
        ),
    )
