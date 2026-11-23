"""PRIVATE connected-MCP D1 source -> original engine diagnostic boundary.

This module has no network, storage, credentials, order or scheduler access.
It is intentionally not a source qualification/publisher. Native provider
data stay in separate reference-only partitions; do not infer venue close,
issuer first-known, historical adjusted basis or trade-ready signals.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from .contracts import SignalDecision, Strategy
from .engine import evaluate_unimplemented_zones
from .market_data import PriceBasis
from .replay import require_utc

PROVIDERS = ("SSI", "DNSE", "VCBS")
SCHEMA = "mst.private_connector_d1_cache_capture.v1"
MAX_SOURCE_ROWS = 2048
MAX_EPOCH = 253402300799
MAX_PRICE_VND = Decimal("1000000000")
_SSI_DAY = re.compile(r"[0-9]{2}/[0-9]{2}/[0-9]{4}\Z")
_VCBS_DAY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_SYMBOL = re.compile(r"[A-Z]{3}\Z")


class PrivateSourceDenied(ValueError):
    """Fixed failure codes only. Never place source rows in error messages."""


@dataclass(frozen=True)
class QuarantinedD1Bar:
    provider: str
    symbol: str
    trading_date: date
    open_vnd: Decimal
    high_vnd: Decimal
    low_vnd: Decimal
    close_vnd: Decimal
    volume_shares: int
    reported_price_basis: PriceBasis
    provisional_source: bool = False

    def __post_init__(self) -> None:
        # §256: callers can construct dataclasses without going through _bar().
        # Enforce the same numeric, source-identity and authority invariants at
        # the typed-object boundary. Never leak caller supplied raw values.
        if (type(self.provider) is not str or self.provider not in PROVIDERS
                or type(self.symbol) is not str
                or _SYMBOL.fullmatch(self.symbol) is None
                or type(self.trading_date) is not date
                or type(self.reported_price_basis) is not PriceBasis
                or type(self.provisional_source) is not bool):
            raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_BAD_IDENTITY")
        prices = (
            self.open_vnd, self.high_vnd, self.low_vnd, self.close_vnd,
        )
        if any(type(x) is not Decimal or not x.is_finite()
               or not Decimal(0) < x <= MAX_PRICE_VND for x in prices):
            raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_TYPED_PRICE_INVALID")
        if (self.low_vnd > min(self.open_vnd, self.close_vnd)
                or self.high_vnd < max(
                    self.open_vnd, self.low_vnd, self.close_vnd)):
            raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_OHLC_BAD_ORDER")
        if type(self.volume_shares) is not int:
            raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_VOLUME_TYPE")
        if not 0 <= self.volume_shares <= (1 << 63) - 1:
            raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_VOLUME_RANGE")

    @property
    def eligible_for_signals(self) -> bool:
        return False


@dataclass(frozen=True)
class PrivateD1Reference:
    provider: str
    symbol: str
    source_snapshot_day: date
    raw_source_sha256: str
    source_rows_observed: int
    bars: tuple[QuarantinedD1Bar, ...]
    has_provisional_source: bool
    source_is_appowned_publisher: bool = False
    venue_close_attested: bool = False
    issuer_first_known_attested: bool = False
    eligible_for_signals: bool = False
    eligible_for_backtest: bool = False

    def __post_init__(self) -> None:
        if (type(self.provider) is not str or self.provider not in PROVIDERS
                or type(self.symbol) is not str
                or _SYMBOL.fullmatch(self.symbol) is None
                or type(self.source_snapshot_day) is not date
                or type(self.raw_source_sha256) is not str
                or _SHA.fullmatch(self.raw_source_sha256) is None
                or type(self.source_rows_observed) is not int
                or type(self.bars) is not tuple
                or not 1 <= self.source_rows_observed <= MAX_SOURCE_ROWS
                or len(self.bars) != self.source_rows_observed
                or type(self.has_provisional_source) is not bool):
            raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_DIGEST_OR_ROWS_INVALID")
        if any(type(b) is not QuarantinedD1Bar
               or b.provider != self.provider or b.symbol != self.symbol
               or b.trading_date > self.source_snapshot_day
               for b in self.bars):
            raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_SOURCE_PARTITION_DRIFT")
        days = tuple(b.trading_date for b in self.bars)
        if tuple(sorted(set(days))) != days:
            raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_DUPLICATE_OR_UNSORTED")
        if self.has_provisional_source is not any(
            b.provisional_source for b in self.bars
        ):
            raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_PROVISIONAL_DRIFT")
        if (self.source_is_appowned_publisher is not False
                or self.venue_close_attested is not False
                or self.issuer_first_known_attested is not False
                or self.eligible_for_signals is not False
                or self.eligible_for_backtest is not False):
            raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_AUTHORITY_FORGED")


@dataclass(frozen=True)
class PrivateD1Diagnostic:
    source: PrivateD1Reference
    strategy: Strategy
    as_of_utc: datetime
    decisions: tuple[SignalDecision, ...]
    eligible_for_signals: bool = False
    trading_or_broker_calls: int = 0

    def __post_init__(self) -> None:
        require_utc(self.as_of_utc)
        if type(self.strategy) is not Strategy:
            raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_BAD_STRATEGY")
        if type(self.source) is not PrivateD1Reference:
            raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_DIAGNOSTIC_SOURCE_INVALID")
        if self.source.source_snapshot_day > self.as_of_utc.date():
            raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_RETROSPECTIVE_LOOKAHEAD")
        if (self.eligible_for_signals is not False
                or type(self.trading_or_broker_calls) is not int
                or self.trading_or_broker_calls != 0):
            raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_DIAGNOSTIC_AUTHORITY_FORGED")
        # The report boundary independently checks 16 zone verdict contents;
        # a caller-mutated tuple must not be silently turned into a signal.


def _bounded_num(value: Any) -> Decimal:
    if type(value) not in (int, float, str):
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_PRICE_TYPE")
    raw = str(value)
    if not 1 <= len(raw) <= 50:
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_PRICE_WIDTH")
    try:
        number = Decimal(raw)
    except InvalidOperation:
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_PRICE_INVALID") from None
    if not number.is_finite() or not 0 < number <= MAX_PRICE_VND:
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_PRICE_RANGE")
    return number


def _shares(value: Any) -> int:
    if type(value) is int:
        n = value
    elif type(value) is str and re.fullmatch(r"[0-9]{1,19}", value):
        n = int(value)
    else:
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_VOLUME_TYPE")
    if not 0 <= n <= (1 << 63) - 1:
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_VOLUME_RANGE")
    return n


def _day(label: Any, provider: str) -> date:
    if type(label) is not str:
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_DATE_TYPE")
    try:
        if provider == "SSI" and _SSI_DAY.fullmatch(label):
            result = datetime.strptime(label, "%d/%m/%Y").date()
        elif provider == "VCBS" and _VCBS_DAY.fullmatch(label):
            result = date.fromisoformat(label)
        else:
            raise ValueError("bad source date format")
    except ValueError:
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_DATE_INVALID") from None
    if result.strftime("%d/%m/%Y" if provider=="SSI" else "%Y-%m-%d") != label:
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_DATE_NOT_CANONICAL")
    return result


def _bar(provider: str, symbol: str, day: date, values: list[Any],
         price_basis: PriceBasis, provisional: bool = False,
         multiplier: int = 1) -> QuarantinedD1Bar:
    if len(values) != 5:
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_MISSING_FIELDS")
    o,h,l,c = (_bounded_num(x)*multiplier for x in values[:4])
    vol = _shares(values[4])
    if max(o,h,l,c)>MAX_PRICE_VND:
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_PRICE_RANGE")
    return QuarantinedD1Bar(
        provider,symbol,day,o,h,l,c,vol,price_basis,provisional,
    )


def _ssi(data: Any, symbol: str) -> list[QuarantinedD1Bar]:
    if type(data) is not list:
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_SSI_DATA_TYPE")
    result=[]
    for row in data:
        if type(row) is not dict or row.get("symbol") != symbol:
            raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_SSI_SYMBOL_DRIFT")
        day=_day(row.get("trading_date"),"SSI")
        # SSI MCP returns VND, reported adjusted history; actual venue and
        # issuer adjustment chain are NOT independently attested.
        result.append(_bar("SSI",symbol,day,
                           [row.get(x) for x in ("open","high","low","close","volume")],
                           PriceBasis.UNKNOWN))
    return result


def _dnse(data: Any, symbol: str) -> list[QuarantinedD1Bar]:
    fields=("t","o","h","l","c","v")
    if (type(data) is not dict
            or type(data.get("nextTime")) is not int
            or data["nextTime"]!=0
            or any(type(data.get(k)) is not list for k in fields)):
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_DNSE_INCOMPLETE")
    n=len(data["t"])
    if not 1 <= n <= MAX_SOURCE_ROWS or any(len(data[k])!=n for k in fields):
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_DNSE_ARRAY_LENGTH")
    result=[]
    previous=0
    for i,stamp in enumerate(data["t"]):
        if (type(stamp) is not int or not 0<stamp<=MAX_EPOCH
                or stamp<=previous):
            raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_DNSE_TIMESTAMP")
        label=datetime.fromtimestamp(stamp,timezone.utc)
        if (label.hour,label.minute,label.second)!=(2,0,0):
            # SOURCE D1 time labels are 09:00 in Viet Nam, not a bar close.
            raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_DNSE_LABEL_NOT_NATIVE_D1")
        previous=stamp
        result.append(_bar("DNSE",symbol,label.date(),
                           [data[k][i] for k in ("o","h","l","c","v")],
                           PriceBasis.UNKNOWN,multiplier=1000))
    return result


def _vcbs(data: Any, symbol: str) -> list[QuarantinedD1Bar]:
    if (type(data) is not dict or data.get("symbol")!=symbol
            or type(data.get("data")) is not list
            or type(data.get("row_basis")) is not dict
            or data["row_basis"].get("price_unit")!="VND"
            or data["row_basis"].get("volume_scope")!="matched_only"
            or type(data["row_basis"].get("field_basis")) is not dict
            or data["row_basis"]["field_basis"].get("price")!="raw"):
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_VCBS_BASIS_INVALID")
    result=[]
    for row in data["data"]:
        if type(row) is not dict:
            raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_VCBS_ROW_INVALID")
        day=_day(row.get("tradingDate"),"VCBS")
        source=row.get("source")
        if source not in (None,"board_supplement"):
            raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_VCBS_UNKNOWN_SUPPLEMENT")
        result.append(_bar("VCBS",symbol,day,
                           [row.get(k) for k in
                            ("openPrice","highPrice","lowPrice","closePrice","volume")],
                           PriceBasis.RAW,source=="board_supplement"))
    return result


def inspect_private_d1_snapshot(
    document: Mapping[str,Any], *, as_of_utc: datetime,
) -> PrivateD1Reference:
    """Read-only reference; forbids retrospective lookahead and signal claims.

    Dates from a private snapshot are NOT reconstructed into a fake vendor
    first-known or official venue-close timestamp. The private document may
    be inspected, never directly converted into a qualified CanonicalCandle.
    """
    require_utc(as_of_utc)
    if type(document) is not dict:
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_DOCUMENT_TYPE")
    provider,symbol=document.get("provider"),document.get("symbol")
    if (document.get("schema")!=SCHEMA
            or document.get("project")!="MST"
            or provider not in PROVIDERS
            or type(symbol) is not str or not _SYMBOL.fullmatch(symbol)
            or document.get("timeframe")!="D1"
            or document.get("source_origin")!="ChatGPT_MCP_CONNECTOR_PRIVATE_DRIVE"
            or document.get("not_appowned_github_cache_publisher") is not True
            or document.get("issuer_closed_bar_attested") is not False
            or document.get("signal_eligible") is not False
            or type(document.get("trade_orders")) is not int
            or document["trade_orders"]!=0):
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_SOURCE_AUTHORITY_INVALID")
    try:
        snapshot_day=date.fromisoformat(document["snapshot_day"])
        if snapshot_day.isoformat()!=document["snapshot_day"]:
            raise ValueError("noncanonical")
    except (KeyError,ValueError,TypeError):
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_CAPTURE_DATE_INVALID") from None
    if snapshot_day>as_of_utc.date():
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_RETROSPECTIVE_LOOKAHEAD")
    raw=document.get("native_source_data")
    if provider=="SSI":
        bars=_ssi(raw,symbol)
    elif provider=="DNSE":
        bars=_dnse(raw,symbol)
    else:
        bars=_vcbs(raw,symbol)
    expected=document.get("source_rows_observed")
    if (type(expected) is not int or not 1<=expected<=MAX_SOURCE_ROWS
            or len(bars)!=expected):
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_ROW_COUNT_INVALID")
    days=[bar.trading_date for bar in bars]
    if len(set(days))!=len(days):
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_DUPLICATE_SESSION")
    if max(days)>snapshot_day:
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_SOURCE_FUTURE_SESSION")
    if type(raw) not in (list,dict):
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_NATIVE_TYPE_INVALID")
    try:
        canon=json.dumps(raw,sort_keys=True,ensure_ascii=False,
                         separators=(",",":"),allow_nan=False).encode("utf-8")
    except (ValueError,TypeError):
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_NATIVE_DIGEST_INVALID") from None
    if len(canon)>1_500_000:
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_NATIVE_BYTES_BOUNDED")
    digest=sha256(canon).hexdigest()
    sorted_bars=tuple(sorted(bars,key=lambda x:x.trading_date))
    return PrivateD1Reference(
        provider,symbol,snapshot_day,digest,len(sorted_bars),sorted_bars,
        any(x.provisional_source for x in sorted_bars),
    )


def diagnose_private_d1_without_signals(
    document: Mapping[str,Any], *, strategy: Strategy, as_of_utc: datetime,
) -> PrivateD1Diagnostic:
    """Connect REAL private-source SHAPES to original 16-zone engine fail-closed.

    Never use this entrypoint as a sell/buy decision, backtest or publisher.
    """
    if not isinstance(strategy,Strategy):
        raise PrivateSourceDenied("MST_PRIVATE_BRIDGE_STRATEGY_INVALID")
    inspection=inspect_private_d1_snapshot(document,as_of_utc=as_of_utc)
    decisions=evaluate_unimplemented_zones(strategy,as_of_utc)
    return PrivateD1Diagnostic(inspection,strategy,as_of_utc,decisions)
