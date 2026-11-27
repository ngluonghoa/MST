"""DNSE documented OHLC vs OHLC Closed envelope guard; synthetic metadata only.

Strictly separates channels, timeframe identity, candle-start labels,
lastUpdated and client observation. A documented channel-shaped message is
NOT authenticated market data, independent issuer first-known, licensed
retention, or an authorized cache candle. No HTTP, WebSocket or payload prices.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import re

_CHANNEL = re.compile(r"^(ohlc|ohlc_closed)\.(1|3|5|15|30|1H|1D|1W)\.(json|msgpack)$")
_INTERVAL_SECONDS = {"1": 60, "3": 180, "5": 300, "15": 900,
                     "30": 1800, "1H": 3600}
_TO_MST_TIMEFRAME = {"5": "M5", "15": "M15", "30": "M30",
                     "1H": "H1", "1D": "D1"}
_MIN_EPOCH = 946684800         # 2000-01-01 UTC, structural lower bound only
_MAX_EPOCH = 4102444800        # 2100-01-01 UTC, structural upper bound only


class DnseChannelKind(str, Enum):
    FORMING = "ohlc"
    CLOSED = "ohlc_closed"


@dataclass(frozen=True)
class UntrustedDnseWsMetadata:
    channel: str
    payload_resolution: str
    payload_type: str
    bar_time_seconds: int
    last_updated_seconds: int
    observed_at_utc: datetime
    authenticated_vendor_connection: bool = False
    authorized_for_retention: bool = False
    independently_verified_first_known: bool = False

    def __post_init__(self):
        if type(self.channel) is not str:
            raise TypeError("EXPLICIT_DNSE_CHANNEL_REQUIRED")
        match = _CHANNEL.fullmatch(self.channel)
        if match is None:
            raise ValueError("UNKNOWN_OR_UNSUPPORTED_DNSE_OHLC_CHANNEL")
        if type(self.payload_resolution) is not str or match.group(2) != self.payload_resolution:
            raise ValueError("CHANNEL_AND_PAYLOAD_RESOLUTION_MISMATCH")
        if self.payload_type != "STOCK" or type(self.payload_type) is not str:
            raise ValueError("EXPLICIT_STOCK_PRODUCT_ONLY")
        if (type(self.bar_time_seconds) is not int or
                type(self.last_updated_seconds) is not int or
                not _MIN_EPOCH <= self.bar_time_seconds < _MAX_EPOCH or
                not _MIN_EPOCH <= self.last_updated_seconds < _MAX_EPOCH or
                self.last_updated_seconds < self.bar_time_seconds):
            raise ValueError("INVALID_UNIX_SECOND_EVENT_TIME_ORDER")
        if (type(self.observed_at_utc) is not datetime or
                self.observed_at_utc.tzinfo is None or
                self.observed_at_utc.utcoffset() != timezone.utc.utcoffset(self.observed_at_utc)):
            raise ValueError("EXPLICIT_AWARE_UTC_OBSERVATION_REQUIRED")
        if (self.authenticated_vendor_connection is not False or
                self.authorized_for_retention is not False or
                self.independently_verified_first_known is not False):
            raise PermissionError("CALLER_SELF_ATTESTED_VENDOR_RIGHTS_OR_FIRST_KNOWN_DENIED")

    @property
    def kind(self) -> DnseChannelKind:
        return DnseChannelKind(_CHANNEL.fullmatch(self.channel).group(1))

    @property
    def encoding(self) -> str:
        return _CHANNEL.fullmatch(self.channel).group(3)


def examine(message: UntrustedDnseWsMetadata) -> dict[str, object]:
    if type(message) is not UntrustedDnseWsMetadata:
        raise TypeError("TYPED_DOCUMENTED_DNSE_WS_METADATA_REQUIRED")
    resolution = message.payload_resolution
    theoretical_end = (message.bar_time_seconds + _INTERVAL_SECONDS[resolution]
                       if resolution in _INTERVAL_SECONDS else None)
    return {
        "source_product": "DNSE_WEBSOCKET_DOCUMENTATION_ONLY_NOT_CONNECTED_MCP",
        "kind": message.kind.value,
        "encoding": message.encoding,
        "resolution": resolution,
        "candidate_mst_timeframe": _TO_MST_TIMEFRAME.get(resolution),
        "native_h4_documented": False,
        "listed_six_timeframes_all_native": False,
        "timestamp_field_semantics": "CANDLE_START_UNIX_SECONDS",
        "last_updated_field_semantics": "LAST_SOURCE_UPDATE_NOT_FIRST_KNOWN",
        "fixed_intraday_end_candidate_seconds": theoretical_end,
        "clock_order_warning": int(message.observed_at_utc.timestamp()) < message.last_updated_seconds,
        "structural_status": (
            "DOCUMENTED_CLOSED_CHANNEL_ENVELOPE_UNTRUSTED"
            if message.kind is DnseChannelKind.CLOSED
            else "FORMING_CHANNEL_NOT_CLOSED"
        ),
        "equivalent_to_connected_dnse_day_mcp": False,
        "first_known_issuer_authenticated": False,
        "real_websocket_entitlement_verified": False,
        "source_native_closed_event_verified": False,
        "official_exchange_calendar_verified": False,
        "licensed_cache_retention": False,
        "cache_publish_authorized": False,
        "backtest_authorized": False,
        "signal_eligible": False,
        "production_authorized": False,
    }


def require_authorized_closed_bar(message: UntrustedDnseWsMetadata) -> None:
    examine(message)
    raise PermissionError("DNSE_DOCUMENTED_CLOSED_ENVELOPE_NOT_AUTHORIZED_VENDOR_EVIDENCE")
