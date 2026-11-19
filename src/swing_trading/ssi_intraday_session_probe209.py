"""§209 SSI 1-day minute source preview; no approved M15/H1 bar aggregation.

Direct private MCP observation 2026-11-17: the SSI intraday-range endpoint
returned 226 per-minute OHLCV rows with a DD/MM/YYYY date label, while the
endpoint description says MM/DD/YYYY. Summed minute volume matched D1,
including an unusual 14:45 closing-auction observation. None of this proves
minute start/end/last-trade semantics, missing-slot policy, provider first
known, pagination completeness or an official exchange-session calendar.

The original ssi_source_qualification.inspect_timestamp and
DailyVsMinuteVolumeParity remain the authorities for known limitations.
Raw provider rows must stay private, not in this public GitHub repository.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Mapping, Any
import re

from .replay import require_utc
from .ssi_source_qualification import (
    DailyVsMinuteVolumeParity, DateOrder, EndpointTimestampPolicy,
    ParityState, inspect_timestamp,
)

STAMP = re.compile(r"[0-9]{2}/[0-9]{2}/[0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2}\Z")
MAX_ROWS = 512


class MinuteProbeState(str, Enum):
    BLOCKED = "BLOCKED"
    OBSERVED_UNVERIFIED = "OBSERVED_UNVERIFIED"


class MinuteProbeDenied(ValueError):
    """Fixed error codes only; no source rows or credentials in messages."""


@dataclass(frozen=True)
class SsiMinuteSessionPreview:
    state: MinuteProbeState
    symbol: str
    trading_day: date
    observed_rows: int
    summed_minute_volume: int | None
    numeric_match_to_d1: bool | None
    timestamp_policy_reason: str
    latest_label: str | None
    earliest_label: str | None
    auction_1445_present: bool
    volume_parity_state: ParityState
    source_clock_verified: bool = False
    official_calendar_verified: bool = False
    pagination_complete_verified: bool = False
    first_known_verified: bool = False
    m15_source_qualified: bool = False
    h1_source_qualified: bool = False
    action_eligible: bool = False

    def __post_init__(self) -> None:
        if (not isinstance(self.state, MinuteProbeState)
                or type(self.symbol) is not str
                or not re.fullmatch("[A-Z]{3}",self.symbol)
                or type(self.trading_day) is not date
                or type(self.observed_rows) is not int
                or not 0 <= self.observed_rows <= MAX_ROWS
                or type(self.timestamp_policy_reason) is not str
                or not self.timestamp_policy_reason
                or not isinstance(self.volume_parity_state, ParityState)
                or self.source_clock_verified is not False
                or self.official_calendar_verified is not False
                or self.pagination_complete_verified is not False
                or self.first_known_verified is not False
                or self.m15_source_qualified is not False
                or self.h1_source_qualified is not False
                or self.action_eligible is not False
                or type(self.auction_1445_present) is not bool):
            raise MinuteProbeDenied("MST_209_MINUTE_FALSE_SOURCE_AUTHORITY")
        if self.state is MinuteProbeState.BLOCKED:
            if (self.observed_rows or self.summed_minute_volume is not None
                    or self.numeric_match_to_d1 is not None
                    or self.latest_label is not None or self.earliest_label is not None
                    or self.auction_1445_present):
                raise MinuteProbeDenied("MST_209_BLOCKED_WITH_FAKE_MINUTES")
        else:
            if (self.observed_rows < 1
                    or type(self.summed_minute_volume) is not int
                    or self.summed_minute_volume < 0
                    or type(self.latest_label) is not str
                    or type(self.earliest_label) is not str
                    or self.volume_parity_state is not ParityState.MISSING_UNKNOWN
                    or self.numeric_match_to_d1 not in (True,False,None)):
                raise MinuteProbeDenied("MST_209_BAD_MINUTE_OBSERVATION")


def inspect_ssi_minute_session_reference(
    response: Mapping[str,Any], *, symbol: str, trading_day: date,
    as_of_utc: datetime, daily_matched_volume: int | None,
) -> SsiMinuteSessionPreview:
    """Reference-only SSI per-minute rows; refuses to certify even equal D1.

    Rows are latest-first, observed labels DD/MM/YYYY; date/clock semantics
    remain conflicting with the documented month-first format. An exchange
    calendar must decide which minutes/auction slots are actually expected.
    """
    require_utc(as_of_utc)
    if (not isinstance(response,Mapping) or type(symbol) is not str
            or not re.fullmatch("[A-Z]{3}",symbol)
            or type(trading_day) is not date
            or (daily_matched_volume is not None and
                (type(daily_matched_volume) is not int or
                 not 0<=daily_matched_volume<2**63))):
        raise MinuteProbeDenied("MST_209_MINUTE_INPUT_SHAPE")

    def blocked(reason: str) -> SsiMinuteSessionPreview:
        return SsiMinuteSessionPreview(
            MinuteProbeState.BLOCKED, symbol, trading_day,
            0,None,None,reason,None,None,False,ParityState.MISSING_UNKNOWN,
        )
    if response.get("status")!="ok":
        error=response.get("error")
        if isinstance(error,Mapping) and error.get("code")=="DOWNSTREAM_UNAVAILABLE":
            return blocked("SSI_INTRADAY_DOWNSTREAM_UNAVAILABLE")
        raise MinuteProbeDenied("MST_209_MINUTE_UNCLASSIFIED_PROVIDER_ERROR")
    data=response.get("data")
    if not isinstance(data,Mapping) or type(data.get("ticks")) is not list:
        raise MinuteProbeDenied("MST_209_MINUTE_TICK_LIST_MISSING")
    rows=data["ticks"]
    if len(rows)>MAX_ROWS:
        raise MinuteProbeDenied("MST_209_MINUTE_TOO_MANY_ROWS")
    if not rows:
        return blocked("SSI_INTRADAY_TARGET_EMPTY_NOT_ZERO_VOLUME")
    unique=set()
    last=None
    total=0
    auction=False
    for row in rows:
        if type(row) is not dict or row.get("symbol")!=symbol:
            raise MinuteProbeDenied("MST_209_MINUTE_SYMBOL_OR_SHAPE")
        stamp=row.get("trading_date")
        if type(stamp) is not str or not STAMP.fullmatch(stamp):
            raise MinuteProbeDenied("MST_209_MINUTE_TIMESTAMP_SHAPE")
        try:
            local=datetime.strptime(stamp,"%d/%m/%Y %H:%M:%S")
        except ValueError:
            raise MinuteProbeDenied("MST_209_MINUTE_UNPARSEABLE_DAY_FIRST") from None
        if local.date()!=trading_day:
            raise MinuteProbeDenied("MST_209_MINUTE_SESSION_DATE_MISMATCH")
        if stamp in unique or (last is not None and local>=last):
            raise MinuteProbeDenied("MST_209_MINUTE_DUPLICATE_OR_REORDERED")
        unique.add(stamp)
        last=local
        if local.hour==14 and local.minute==45:
            auction=True  # possible auction row; NEVER treat as normal minute bar
        try:
            prices=tuple(Decimal(str(row.get(k))) for k in
                         ("open","high","low","close"))
        except (InvalidOperation,ValueError,TypeError):
            raise MinuteProbeDenied("MST_209_MINUTE_BAD_PRICES") from None
        if (any(not p.is_finite() or p<=0 for p in prices)
                or prices[2]>min(prices[0],prices[3])
                or prices[1]<max(prices[0],prices[3],prices[2])):
            raise MinuteProbeDenied("MST_209_MINUTE_BAD_OHLC")
        volume=row.get("volume")
        if type(volume) is str and re.fullmatch("[0-9]{1,19}",volume):
            n=int(volume)
        elif type(volume) is int:
            n=volume
        else:
            raise MinuteProbeDenied("MST_209_MINUTE_VOLUME_TYPE")
        if not 0<=n<2**63:
            raise MinuteProbeDenied("MST_209_MINUTE_VOLUME_RANGE")
        total+=n
        if total>=2**63:
            raise MinuteProbeDenied("MST_209_MINUTE_VOLUME_SUM_OVERFLOW")

    # Explicitly keep documented and observed date conventions contradictory:
    # this connector description says MM/DD, rows here observed DD/MM.
    policy=EndpointTimestampPolicy(
        "SSI.marketdata_list_intraday_stock_infor.range",
        "SSI/INTRADAY_DATE_POLICY_CANDIDATE_20261117",
        DateOrder.MONTH_FIRST,DateOrder.DAY_FIRST,False,False,
    )
    time_assessment=inspect_timestamp(
        rows[0]["trading_date"],trading_day,policy,intraday=True,
    )
    parity=DailyVsMinuteVolumeParity(
        symbol,trading_day,daily_matched_volume,total,
        minute_pagination_complete=False,
        aggregation_policy_verified=False,
    )
    return SsiMinuteSessionPreview(
        MinuteProbeState.OBSERVED_UNVERIFIED,
        symbol,trading_day,len(rows),total,
        total==daily_matched_volume if daily_matched_volume is not None else None,
        time_assessment.reason_code,
        rows[0]["trading_date"],rows[-1]["trading_date"],
        auction,parity.parity_state,
    )
