"""A03 source-document reconciler: DNSE live vs closed WS and SSI REST-v3 M30.

This is additive test-only evidence. The documented WebSocket/REST surfaces
are NOT connected ChatGPT MCPs and caller-supplied channel labels cannot attest
an issuer or its licensed real bar data.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from hashlib import sha256
import argparse
import json
from pathlib import Path
from collections.abc import Mapping

from swing_trading.incremental_cache import Provider
from scripts.m2_a03_three_source_vcbs_capability_lab import one, TF

SCHEMA = "mst.a03.public-doc-transport-native-m5-closed-vs-forming.v1"
NO_GO = "DOCUMENTED_SOURCE_TRANSPORT_IS_NOT_CONNECTED_OR_LICENSED_NO_GO"

class DocumentedTransport(str, Enum):
    SSI_REST_V3 = "SSI_PUBLIC_REST_V3_DATA_OHLC"
    DNSE_WS_FORMING = "DNSE_PUBLIC_WS_OHLC_FORMING"
    DNSE_WS_CLOSED = "DNSE_PUBLIC_WS_OHLC_CLOSED"

DOCUMENTED_SOURCE_URLS = {
    DocumentedTransport.SSI_REST_V3:
        "https://developers.ssi.com.vn/en/docs/api-reference/data-ohlc",
    DocumentedTransport.DNSE_WS_FORMING:
        "https://developers.dnse.com.vn/docs/guide/market-data/connect/",
    DocumentedTransport.DNSE_WS_CLOSED:
        "https://developers.dnse.com.vn/docs/guide/market-data/connect/",
}

DENIED = (
    "connected_mcp_exposes_this_native_ws_stream",
    "connected_mcp_exposes_rest_v3_30m",
    "vendor_channel_origin_authenticated",
    "provider_entitlement_and_retention_authorized",
    "signed_source_first_known_history_verified",
    "official_exchange_calendar_and_auction_verified",
    "native_bar_feed_closed_and_complete_independently_verified",
    "real_historical_revision_ledger_verified",
    "real_market_data_cached_on_google_drive",
    "original_v1_or_v2_source_changed",
    "a02_owner_63_approved", "a03_v2_owner_8_approved",
    "a03_owner_14_approved", "production_release_authorized",
    "trading_authorized",
)

@dataclass(frozen=True)
class UntrustedDocumentedDNSEBar:
    transport: DocumentedTransport
    time: int
    resolution: str
    lastUpdated: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    source_verified: bool = False

    def __post_init__(self):
        if type(self.transport) is not DocumentedTransport or self.transport not in (
            DocumentedTransport.DNSE_WS_FORMING, DocumentedTransport.DNSE_WS_CLOSED
        ):
            raise TypeError("TYPED_DOCUMENTED_DNSE_WS_CHANNEL_REQUIRED")
        if type(self.resolution) is not str or self.resolution != "5":
            raise ValueError("EXPLICIT_DOCUMENTED_FIVE_MINUTE_SCOPE_REQUIRED")
        for x in (self.time, self.lastUpdated):
            if type(x) is not int or not (1_000_000_000 <= x <= 4_000_000_000):
                raise ValueError("UNIX_SECONDS_REQUIRED_NOT_BOOL_OR_MILLISECONDS")
        if self.lastUpdated < self.time:
            raise ValueError("UPDATE_BEFORE_BAR_START")
        if self.time % 300:
            raise ValueError("SYNTHETIC_M5_GRID_UNALIGNED")
        for p in (self.open, self.high, self.low, self.close):
            if type(p) is not Decimal or not p.is_finite() or p <= 0:
                raise ValueError("POSITIVE_FINITE_DECIMAL_PRICE_REQUIRED")
        if self.low > min(self.open,self.close) or self.high < max(self.open,self.close):
            raise ValueError("INCONSISTENT_OHLC_GEOMETRY")
        if self.low > self.high:
            raise ValueError("HIGH_LOW_INVERSION")
        if type(self.volume) is not int or self.volume < 0:
            raise ValueError("NONNEGATIVE_INTEGER_VOLUME_REQUIRED")
        if self.source_verified is not False:
            raise PermissionError("PUBLIC_CHANNEL_STRING_CANNOT_SELF_ATTEST_ISSUER")

def documented_channel_observation(w: UntrustedDocumentedDNSEBar,
                                   *, observed_at_utc: datetime):
    if type(w) is not UntrustedDocumentedDNSEBar:
        raise TypeError("EXACT_TYPED_UNTRUSTED_WEBSOCKET_BAR_REQUIRED")
    if (type(observed_at_utc) is not datetime or
            observed_at_utc.tzinfo is None or
            observed_at_utc.utcoffset()!=timedelta(0)):
        raise ValueError("AWARE_UTC_OBSERVER_CLOCK_REQUIRED")
    if w.lastUpdated > int(observed_at_utc.timestamp()):
        raise ValueError("LAST_UPDATED_AFTER_OBSERVER_CLOCK")
    end = w.time + 300
    closed_claim = w.transport is DocumentedTransport.DNSE_WS_CLOSED
    if closed_claim and w.lastUpdated < end:
        raise ValueError("CLOSED_CHANNEL_EVENT_BEFORE_NOMINAL_INTERVAL_END")
    return {
        "schema": SCHEMA, "status": NO_GO,
        "declared_documented_transport": w.transport.value,
        "documented_start_label_seconds": w.time,
        "nominal_end_seconds": end,
        "source_payload_self_declares_closed_channel": closed_claim,
        "source_payload_self_declares_forming_channel": not closed_claim,
        "claimed_closed_channel_shape_after_end": closed_claim,
        "clock_consistent_under_synthetic_assumptions": True,
        "exchange_calendar_and_phase_accepted": False,
        "source_channel_authenticated": False,
        "source_first_known_authenticated": False,
        "real_closed_native_m5_qualified": False,
        "can_emit_signal": False,
    }

def fabricated(kind=DocumentedTransport.DNSE_WS_CLOSED, *,
               update_after_start_seconds=301):
    start = int(datetime(2026, 11, 9, 2, 15, tzinfo=timezone.utc).timestamp())
    assert start % 300 == 0
    return UntrustedDocumentedDNSEBar(
        transport=kind, time=start, resolution="5",
        lastUpdated=start+update_after_start_seconds,
        open=Decimal("100"), high=Decimal("102"),
        low=Decimal("99"), close=Decimal("101"), volume=50
    )

def documented_m30_ssi_status():
    row=one(Provider.SSI, "M30")
    if not row.public_native_api_documented_unconnected:
        raise AssertionError("SSI_REST_V3_30M_PUBLIC_DOCUMENT_CAPABILITY_OMITTED")
    if row.qualified_native_ohlcv or row.signal_eligible or row.entitlement:
        raise AssertionError("SSI_PUBLIC_REST_30M_FALSELY_PROMOTED_TO_CONNECTED")
    return {
        "source": "SSI", "timeframe": "M30",
        "transport": DocumentedTransport.SSI_REST_V3.value,
        "rest_v3_public_timeFrame_30m": True,
        "sdk_tutorial_30m_independently_proven": False,
        "current_connected_mcp_supports_rest_v3_30m": False,
        "signed_provider_retention_and_correction_rights": False,
        "eligible_for_live_ohlcv_or_signals": False,
    }

def build():
    closed=fabricated()
    forming=fabricated(DocumentedTransport.DNSE_WS_FORMING,
                       update_after_start_seconds=350)
    obs=datetime.fromtimestamp(closed.lastUpdated+10, tz=timezone.utc)
    a=documented_channel_observation(closed,observed_at_utc=obs)
    b=documented_channel_observation(forming,observed_at_utc=obs)
    if not a["claimed_closed_channel_shape_after_end"]:
        raise AssertionError("CLOSED_CHANNEL_SHAPE_WAS_NOT_RECOGNIZED")
    if b["source_payload_self_declares_closed_channel"]:
        raise AssertionError("FORMING_CHANNEL_FALSELY_TREATED_AS_CLOSED")
    if a["can_emit_signal"] or b["can_emit_signal"]:
        raise AssertionError("UNTRUSTED_DOCUMENTATION_PROMOTED_TO_TRADING")
    r={
        "schema":SCHEMA, "status":NO_GO,
        "source_urls":{k.value:v for k,v in DOCUMENTED_SOURCE_URLS.items()},
        "ssi_public_rest_v3_m30":documented_m30_ssi_status(),
        "dnse_public_ws_start_label_documented": True,
        "dnse_public_ws_ohlc_forming_channel_documented": True,
        "dnse_public_ws_ohlc_closed_channel_documented": True,
        "dnse_connected_mcp_is_d1_history_not_live_ws": True,
        "dnse_closed_event_is_not_a_source_revision_ledger": True,
        "dnse_qualified_closed_M5_signal": False,
        "ssi_rest_v3_m30_qualified_source": False,
        "fabricated_channel_observations": [
            {k:v for k,v in a.items() if k not in ("documented_start_label_seconds","nominal_end_seconds")},
            {k:v for k,v in b.items() if k not in ("documented_start_label_seconds","nominal_end_seconds")}
        ],
        **{k:False for k in DENIED},
    }
    blob=json.dumps(r,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    r["synthetic_receipt_sha256"]=sha256(blob.encode("ascii")).hexdigest()
    return r

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path)
    args=p.parse_args(argv)
    r=build()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in r.items() if k!="fabricated_channel_observations"},sort_keys=True))

if __name__=="__main__":
    main()
