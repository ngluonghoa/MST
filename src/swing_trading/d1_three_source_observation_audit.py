"""§209 three-provider D1 observation parity, fail-closed on SOURCE AUTHORITY.

Source observed via private authenticated connected MCP on 2026-11-17:
SSI compact daily, SSI detailed daily, DNSE DAY and VCBS RAW D1 have
different price-basis/availability/finality semantics. This pure parser
normalizes unit/clock labels only; an identical OHLCV row from three tools
DOES NOT attest independently sourced exchange finality, price basis,
corp-actions, vendor rights, provider first-known, or any M15/H1 candle.

All tests use FICTIONAL payloads. Never commit live vendor rows, secrets or
provider payloads to public GitHub; store limited private QA observations
separately with appropriate licensing/retention policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
import re
from typing import Any, Mapping

from .market_data import PriceBasis
from .replay import require_utc

_VN = timezone(timedelta(hours=7))
_SYMBOL = re.compile(r"[A-Z]{3}\Z")
_DAY_SSI = re.compile(r"[0-9]{2}/[0-9]{2}/[0-9]{4}\Z")
MAX_ROWS = 512
MAX_PRICE_VND = Decimal("1000000000")
_SHARES_MAX = (1 << 63) - 1


class D1ProbeSource(str, Enum):
    SSI_COMPACT = "SSI_COMPACT"
    SSI_DETAIL = "SSI_DETAIL"
    DNSE_DAY = "DNSE_DAY"
    VCBS_RAW = "VCBS_RAW"


class D1ObservationState(str, Enum):
    ROW_OBSERVED = "ROW_OBSERVED"
    TARGET_ABSENT = "TARGET_ABSENT"
    DOWNSTREAM_UNAVAILABLE = "DOWNSTREAM_UNAVAILABLE"


class D1ParityState(str, Enum):
    INSUFFICIENT_SOURCES_UNVERIFIED = "INSUFFICIENT_SOURCES_UNVERIFIED"
    SOURCE_VALUES_CONFLICT = "SOURCE_VALUES_CONFLICT"
    VALUES_EQUAL_BASIS_UNVERIFIED = "VALUES_EQUAL_BASIS_UNVERIFIED"
    VALUES_EQUAL_BUT_UNATTESTED = "VALUES_EQUAL_BUT_UNATTESTED"


class D1ProbeDenied(ValueError):
    """Fixed-size diagnostic errors: do not echo input rows/provider secrets."""


def _decimal(value: Any, *, factor: int = 1) -> Decimal:
    if type(value) not in (str, int, float, Decimal):
        raise D1ProbeDenied("MST_209_PRICE_TYPE")
    try:
        p = Decimal(str(value)) * factor
    except (InvalidOperation, ValueError):
        raise D1ProbeDenied("MST_209_PRICE_PARSE") from None
    if not p.is_finite() or p <= 0 or p > MAX_PRICE_VND:
        raise D1ProbeDenied("MST_209_PRICE_OUT_OF_RANGE")
    return p


def _volume(value: Any) -> int:
    if type(value) is int:
        n = value
    elif type(value) is str and re.fullmatch("[0-9]{1,19}", value):
        n = int(value)
    else:
        raise D1ProbeDenied("MST_209_VOLUME_TYPE")
    if n < 0 or n > _SHARES_MAX:
        raise D1ProbeDenied("MST_209_VOLUME_OUT_OF_RANGE")
    return n


@dataclass(frozen=True)
class D1SourceObservation:
    source: D1ProbeSource
    symbol: str
    trading_day: date
    retrieved_at_utc: datetime
    state: D1ObservationState
    basis: PriceBasis
    ohlcv_vnd_shares: tuple[Decimal, Decimal, Decimal, Decimal, int] | None
    source_semantics: str
    vendor_first_known_verified: bool = False
    venue_close_verified: bool = False
    retention_rights_verified: bool = False
    source_independently_attested: bool = False
    action_eligible: bool = False

    def __post_init__(self) -> None:
        if (not isinstance(self.source, D1ProbeSource)
                or not isinstance(self.symbol, str)
                or not _SYMBOL.fullmatch(self.symbol)
                or type(self.trading_day) is not date
                or not isinstance(self.state, D1ObservationState)
                or not isinstance(self.basis, PriceBasis)
                or type(self.source_semantics) is not str
                or not self.source_semantics or len(self.source_semantics)>96
                or self.vendor_first_known_verified is not False
                or self.venue_close_verified is not False
                or self.retention_rights_verified is not False
                or self.source_independently_attested is not False
                or self.action_eligible is not False):
            raise D1ProbeDenied("MST_209_FAKE_SOURCE_AUTHORITY")
        require_utc(self.retrieved_at_utc)
        if self.state is not D1ObservationState.ROW_OBSERVED:
            if self.ohlcv_vnd_shares is not None:
                raise D1ProbeDenied("MST_209_MISSING_WITH_FAKE_PRICES")
        else:
            v=self.ohlcv_vnd_shares
            if (type(v) is not tuple or len(v)!=5
                    or any(type(p) is not Decimal or not p.is_finite()
                           or p<=0 or p>MAX_PRICE_VND for p in v[:4])
                    or type(v[4]) is not int or v[4]<0 or v[4]>_SHARES_MAX
                    or v[2]>min(v[0],v[3]) or v[1]<max(v[0],v[3],v[2])):
                raise D1ProbeDenied("MST_209_BAD_OHLCV")
        if self.source is D1ProbeSource.DNSE_DAY and self.basis is not PriceBasis.UNKNOWN:
            raise D1ProbeDenied("MST_209_DNSE_BASIS_CANNOT_BE_GUESSED")
        if self.source is D1ProbeSource.VCBS_RAW and self.basis is not PriceBasis.RAW:
            raise D1ProbeDenied("MST_209_VCBS_BASIS_NOT_RAW")


def inspect_d1_live_response(
    payload: Mapping[str, Any], *, source: D1ProbeSource,
    symbol: str, trading_day: date, retrieved_at_utc: datetime,
) -> D1SourceObservation:
    """Consume provider response DATA, not an authenticated source signature.

    SSI compact response: {"status":"ok","data":{"stocks":[...]}}.
    SSI detail is independent endpoint: may NOT contain today's target.
    DNSE DAY epoch represents 09:00 Vietnam SESSION LABEL, not bar close.
    VCBS raw response: {"row_basis":{...},"data":[...]}; board_supplement
    is an in-session/late board fallback, never independently final.
    """
    require_utc(retrieved_at_utc)
    if (not isinstance(payload, Mapping)
            or not isinstance(source, D1ProbeSource)
            or type(trading_day) is not date
            or type(symbol) is not str or not _SYMBOL.fullmatch(symbol)):
        raise D1ProbeDenied("MST_209_INPUT_SHAPE")
    state=D1ObservationState.ROW_OBSERVED
    reason=""
    basis=PriceBasis.UNKNOWN
    values=None
    if source in (D1ProbeSource.SSI_COMPACT,D1ProbeSource.SSI_DETAIL):
        if payload.get("status")!="ok":
            err=payload.get("error")
            if not isinstance(err,Mapping) or err.get("code")!="DOWNSTREAM_UNAVAILABLE":
                raise D1ProbeDenied("MST_209_SSI_UNCLASSIFIED_FAILURE")
            state=D1ObservationState.DOWNSTREAM_UNAVAILABLE
            reason="SSI_DOWNSTREAM_UNAVAILABLE"
        else:
            rows=payload.get("data",{}).get("stocks")
            if type(rows) is not list or len(rows)>MAX_ROWS:
                raise D1ProbeDenied("MST_209_SSI_STOCK_LIST_INVALID")
            label=trading_day.strftime("%d/%m/%Y")
            hits=[x for x in rows if type(x) is dict and x.get("trading_date")==label
                  and x.get("symbol")==symbol]
            if len(hits)>1:
                raise D1ProbeDenied("MST_209_DUPLICATE_SSI_SESSION")
            if not hits:
                state=D1ObservationState.TARGET_ABSENT
                reason="SSI_TARGET_NOT_RETURNED_NOT_ZERO_VOLUME"
            else:
                row=hits[0]
                if source is D1ProbeSource.SSI_DETAIL:
                    names=("open_raw","high_raw","low_raw","close_raw")
                    basis=PriceBasis.RAW
                    reason="SSI_DETAILED_RAW_FIELDS_ONLY_NO_ISSUER_FINALITY"
                else:
                    names=("open","high","low","close")
                    basis=PriceBasis.ADJUSTED
                    reason="SSI_COMPACT_ADJUSTED_REFERENCE_ONLY"
                values=(*(_decimal(row.get(k)) for k in names),
                        _volume(row.get("volume")))
    elif source is D1ProbeSource.DNSE_DAY:
        basis=PriceBasis.UNKNOWN
        data=payload.get("data")
        if not isinstance(data,Mapping) or not isinstance(data.get("t"),list):
            raise D1ProbeDenied("MST_209_DNSE_DATA_INVALID")
        ts=data["t"]
        if len(ts)>MAX_ROWS:
            raise D1ProbeDenied("MST_209_DNSE_HISTORY_OVERSIZED")
        cols=("o","h","l","c","v")
        if any(type(data.get(k)) is not list or len(data[k])!=len(ts)
               for k in cols):
            raise D1ProbeDenied("MST_209_DNSE_ARRAY_LENGTH_MISMATCH")
        hits=[]
        previous=None
        for i,t in enumerate(ts):
            if type(t) is not int or t<0 or t>253402300799:
                raise D1ProbeDenied("MST_209_DNSE_EPOCH_INVALID")
            if previous is not None and t<=previous:
                raise D1ProbeDenied("MST_209_DNSE_NONMONOTONE_SESSIONS")
            previous=t
            dt=datetime.fromtimestamp(t,tz=timezone.utc).astimezone(_VN)
            if (dt.hour,dt.minute,dt.second)!=(9,0,0):
                raise D1ProbeDenied("MST_209_DNSE_NOT_SESSION_09_LABEL")
            if dt.date()==trading_day:
                hits.append(i)
        if not hits:
            state=D1ObservationState.TARGET_ABSENT
            reason="DNSE_DAY_NOT_IN_SNAPSHOT"
        else:
            i=hits[0]
            values=(*(_decimal(data[k][i],factor=1000) for k in cols[:4]),
                    _volume(data["v"][i]))
            reason="DNSE_09_SESSION_LABEL_NOT_CLOSE_UNKNOWN_PRICE_BASIS"
    else:
        row_basis=payload.get("row_basis")
        rows=payload.get("data")
        if (not isinstance(row_basis,Mapping) or type(rows) is not list
                or len(rows)>MAX_ROWS):
            raise D1ProbeDenied("MST_209_VCBS_RESPONSE_SHAPE")
        if (row_basis.get("price_unit")!="VND"
                or row_basis.get("volume_scope")!="matched_only"
                or not isinstance(row_basis.get("field_basis"),Mapping)
                or row_basis["field_basis"].get("price")!="raw"):
            raise D1ProbeDenied("MST_209_VCBS_PRICE_OR_VOLUME_BASIS_INVALID")
        basis=PriceBasis.RAW
        hits=[x for x in rows if type(x) is dict
              and x.get("tradingDate")==trading_day.isoformat()]
        if len(hits)>1:
            raise D1ProbeDenied("MST_209_VCBS_DUPLICATE_SESSION")
        if not hits:
            state=D1ObservationState.TARGET_ABSENT
            reason="VCBS_TARGET_NOT_RETURNED"
        else:
            row=hits[0]
            values=(*(_decimal(row.get(k)) for k in
                       ("openPrice","highPrice","lowPrice","closePrice")),
                    _volume(row.get("volume")))
            if row.get("source")=="board_supplement":
                reason="VCBS_BOARD_SUPPLEMENT_NOT_ARCHIVED_FINAL"
            else:
                reason="VCBS_RAW_HISTORY_UNVERIFIED_PROVIDER_CLOSE"
    return D1SourceObservation(
        source,symbol,trading_day,retrieved_at_utc,state,basis,values,reason,
    )


@dataclass(frozen=True)
class D1ThreeSourceAudit:
    symbol: str
    trading_day: date
    state: D1ParityState
    present_sources: tuple[D1ProbeSource,...]
    absent_sources: tuple[D1ProbeSource,...]
    numeric_ohlcv_equal: bool | None
    reasons: tuple[str,...]
    provider_first_known_verified: bool = False
    venue_close_verified: bool = False
    retention_rights_verified: bool = False
    signal_eligible: bool = False
    action_eligible: bool = False

    def __post_init__(self) -> None:
        if (not isinstance(self.state,D1ParityState)
                or not isinstance(self.symbol,str) or not _SYMBOL.fullmatch(self.symbol)
                or type(self.trading_day) is not date
                or type(self.present_sources) is not tuple
                or type(self.absent_sources) is not tuple
                or type(self.reasons) is not tuple
                or any(type(x) is not str or not x for x in self.reasons)
                or self.provider_first_known_verified is not False
                or self.venue_close_verified is not False
                or self.retention_rights_verified is not False
                or self.signal_eligible is not False
                or self.action_eligible is not False):
            raise D1ProbeDenied("MST_209_AUDIT_FALSE_AUTHORITY")


def reconcile_d1_three_source_observations(
    observations: tuple[D1SourceObservation, ...], *,
    symbol: str, trading_day: date,
) -> D1ThreeSourceAudit:
    """Always NO-TRADE, even exact FPT-like numeric agreement.

    SSI compact vs SSI detailed remain separate endpoint records; the
    latter can be missing despite the former's data. A DNSE price-basis
    UNKNOWN or SSI adjusted vs VCBS raw means no cross-provider basis
    certification. Likewise equal volume is not proof of matched scope.
    """
    if (type(observations) is not tuple or len(observations)>4
            or type(trading_day) is not date or type(symbol) is not str
            or not _SYMBOL.fullmatch(symbol)):
        raise D1ProbeDenied("MST_209_AUDIT_INPUT_INVALID")
    used=set()
    for x in observations:
        if (type(x) is not D1SourceObservation
                or x.symbol!=symbol or x.trading_day!=trading_day
                or x.source in used):
            raise D1ProbeDenied("MST_209_MIXED_OR_DUPLICATE_SOURCE")
        used.add(x.source)
    present=tuple(x.source for x in observations
                  if x.state is D1ObservationState.ROW_OBSERVED)
    missing=tuple(x.source for x in observations
                  if x.state is not D1ObservationState.ROW_OBSERVED)
    core={D1ProbeSource.SSI_COMPACT,D1ProbeSource.DNSE_DAY,
          D1ProbeSource.VCBS_RAW}
    ready=core.issubset(set(present))
    if not ready:
        state=D1ParityState.INSUFFICIENT_SOURCES_UNVERIFIED
        match=None
    else:
        vals=[x.ohlcv_vnd_shares for x in observations
              if x.source in core]
        match=all(v==vals[0] for v in vals[1:])
        if not match:
            state=D1ParityState.SOURCE_VALUES_CONFLICT
        else:
            selected=[x for x in observations if x.source in core]
            bases={x.basis for x in selected}
            state=(D1ParityState.VALUES_EQUAL_BUT_UNATTESTED
                   if len(bases)==1 and PriceBasis.UNKNOWN not in bases
                   else D1ParityState.VALUES_EQUAL_BASIS_UNVERIFIED)
    reasons=tuple(sorted({
        "FIRST_KNOWN_NOT_PROVIDER_ATTESTED",
        "OFFICIAL_SESSION_CLOSE_NOT_INDEPENDENTLY_VERIFIED",
        "RETENTION_RIGHTS_AND_SOURCE_REVISION_NOT_PROVEN",
        "INTRADAY_M15_H1_NOT_QUALIFIED_BY_D1",
        *(x.source_semantics for x in observations
          if x.state is not D1ObservationState.ROW_OBSERVED
          or x.source in core),
    }))
    return D1ThreeSourceAudit(
        symbol,trading_day,state,present,missing,match,reasons,
    )
