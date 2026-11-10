"""A03 test-only DNSE documented REST M5 history nextTime/backfill candidate.

PUBLIC API documentation is not an authorized connection, source-issuer
attestation, historical first-known ledger, or provider-approved retention.
Only manufactured OHLC values are used; no network, credentials or market cache.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path

from scripts.m2_a03_documented_ohlc_transport_boundary_lab import (
    UntrustedDocumentedDNSEBar, DocumentedTransport, fabricated,
)

SCHEMA = "mst.a03.dnse-rest-m5-nexttime-untrusted.v1"
NO_GO = "PUBLIC_DNSE_M5_REST_BACKFILL_SHAPE_NOT_ISSUER_AUTHORITY_NO_GO"
PUBLIC_DOC = "https://developers.dnse.com.vn/docs/dnse/get-ohlc-history/"
FIELDS = ("t", "o", "h", "l", "c", "v")
MAX_FIXTURE_PAGES = 8

@dataclass(frozen=True)
class UntrustedRequest:
    symbol: str
    from_seconds: int
    to_seconds: int
    resolution: str = "5"
    def __post_init__(self):
        if type(self.symbol) is not str or not self.symbol.isascii() or not self.symbol.isupper() or not self.symbol.isalnum():
            raise ValueError("EXPLICIT_UPPERCASE_ASCII_STOCK_SYMBOL_REQUIRED")
        if type(self.from_seconds) is not int or type(self.to_seconds) is not int:
            raise TypeError("UNIX_SECONDS_WINDOW_NOT_BOOL_REQUIRED")
        if not (1_000_000_000 <= self.from_seconds < self.to_seconds <= 4_000_000_000):
            raise ValueError("STRICT_BOUNDED_UNIX_SECONDS_WINDOW_REQUIRED")
        if self.resolution != "5" or type(self.resolution) is not str:
            raise ValueError("DOCUMENTED_REST_M5_RESOLUTION_REQUIRED")

@dataclass(frozen=True)
class FakePage:
    requested_from: int
    payload: dict
    def __post_init__(self):
        if type(self.requested_from) is not int or type(self.payload) is not dict:
            raise TypeError("EXPLICIT_FAKE_PAGE_REQUEST_AND_OBJECT_REQUIRED")

def price_decimal(value):
    if type(value) not in (int, float, Decimal):
        raise TypeError("NUMERIC_OHLC_NOT_BOOL_OR_STRING_REQUIRED")
    try:
        d = Decimal(str(value))
    except (ValueError, InvalidOperation):
        raise ValueError("VALID_DECIMAL_PRICE_REQUIRED") from None
    if not d.is_finite() or d <= 0:
        raise ValueError("FINITE_POSITIVE_PRICE_REQUIRED")
    return d

def decode_page(payload: dict, request: UntrustedRequest):
    if type(request) is not UntrustedRequest or type(payload) is not dict:
        raise TypeError("UNTRUSTED_TYPED_REQUEST_AND_RESPONSE_REQUIRED")
    if set(payload) != set(FIELDS) | {"nextTime"}:
        raise ValueError("EXACT_DOCUMENTED_OHLC_ARRAY_FIELDS_REQUIRED")
    arrays = tuple(payload[k] for k in FIELDS)
    if any(type(a) is not list for a in arrays):
        raise TypeError("SIX_PARALLEL_ARRAYS_REQUIRED")
    count = len(arrays[0])
    if any(len(a) != count for a in arrays):
        raise ValueError("PARALLEL_ARRAY_LENGTH_MISMATCH")
    if count > 500:
        raise ValueError("SYNTHETIC_RECEIPT_ROW_LIMIT_REQUIRED")
    cursor = payload["nextTime"]
    if type(cursor) is not int or cursor < 0 or cursor > 4_000_000_000:
        raise ValueError("NEXTTIME_EXACT_UNIX_SECONDS_OR_ZERO_REQUIRED")
    rows = []
    prev = None
    for t, o, h, l, c, v in zip(*arrays):
        if type(t) is not int or not (request.from_seconds <= t <= request.to_seconds):
            raise ValueError("UNIX_SECOND_TIMESTAMP_IN_REQUEST_WINDOW_REQUIRED")
        if prev is not None and t <= prev:
            raise ValueError("STRICTLY_INCREASING_UNTRUSTED_PAGE_TIMES_REQUIRED")
        prev = t
        if type(v) is not int or v < 0:
            raise ValueError("NONNEGATIVE_LOSSLESS_VOLUME_REQUIRED")
        po,ph,pl,pc = (price_decimal(x) for x in (o,h,l,c))
        if ph < max(po,pc) or pl > min(po,pc) or pl > ph:
            raise ValueError("CANDLE_PRICE_GEOMETRY_INVALID")
        rows.append((t,po,ph,pl,pc,v))
    return tuple(rows),cursor

def inspect_fake_pages(req: UntrustedRequest, pages: tuple[FakePage, ...]):
    """No REST requests: test only hypothetical pagination progress and shape."""
    if type(req) is not UntrustedRequest:
        raise TypeError("EXACT_REST_REQUEST_REQUIRED")
    if type(pages) is not tuple or not pages or len(pages)>MAX_FIXTURE_PAGES:
        raise ValueError("NONEMPTY_BOUNDED_FAKE_PAGE_SEQUENCE_REQUIRED")
    cursor=req.from_seconds
    last_bar=None
    rows=0
    ended=False
    next_outside=False
    for i,page in enumerate(pages):
        if type(page) is not FakePage or page.requested_from != cursor:
            raise ValueError("NEXT_PAGE_MUST_USE_EXPLICIT_DOCUMENTED_CURSOR")
        sub_req=UntrustedRequest(req.symbol,cursor,req.to_seconds)
        bars,next_time=decode_page(page.payload,sub_req)
        if bars and last_bar is not None and bars[0][0] <= last_bar:
            raise ValueError("CROSS_PAGE_DUPLICATE_OR_NONMONOTONE_TIME")
        if bars:
            last_bar=bars[-1][0]
        rows+=len(bars)
        if next_time==0:
            if i!=len(pages)-1:
                raise ValueError("NO_NEXTTIME_BUT_ADDITIONAL_FAKE_PAGE")
            ended=True
        else:
            if next_time <= cursor or (last_bar is not None and next_time <= last_bar):
                raise ValueError("STUCK_OR_ROLLBACK_NEXTTIME_DENIED")
            if next_time >= req.to_seconds:
                next_outside=True
                if i!=len(pages)-1:
                    raise ValueError("OUT_OF_WINDOW_CURSOR_NOT_AUTO_FETCHABLE")
            else:
                cursor=next_time
    return {
        "schema":SCHEMA, "status":NO_GO,
        "synthetic_pages_observed":len(pages),
        "synthetic_rows_observed":rows,
        "nexttime_zero_claimed_at_end":ended,
        "nexttime_outside_window_requires_vendor_semantics":next_outside,
        "remaining_cursor_is_untrusted":None if ended or next_outside else cursor,
        "connected_mcp_supports_m5_history":False,
        "rest_api_called":False,
        "api_key_or_signature_used":False,
        "publisher_first_known_history_verified":False,
        "official_market_calendar_verified":False,
        "source_bar_start_end_label_verified":False,
        "closed_candle_completeness_verified":False,
        "historical_correction_and_retention_rights_verified":False,
        "physical_google_drive_market_cache_enabled":False,
        "signal_or_order_allowed":False,
    }

def compare_fake_ws_closed_and_rest(rest_payload:dict, req:UntrustedRequest, bar:UntrustedDocumentedDNSEBar):
    """Numerical overlap only, NOT publisher-source chronological equivalence."""
    if type(bar) is not UntrustedDocumentedDNSEBar or bar.transport is not DocumentedTransport.DNSE_WS_CLOSED:
        raise TypeError("DOCUMENTED_FAKE_CLOSED_BAR_ONLY")
    rows,_=decode_page(rest_payload,req)
    candidates=[r for r in rows if r[0]==bar.time]
    if not candidates:
        status="NO_EQUAL_NUMERIC_TIMESTAMP_SHAPE"
    elif (candidates[0][1:] == (bar.open,bar.high,bar.low,bar.close,bar.volume)):
        status="IDENTICAL_NUMERIC_SHAPE_NOT_SOURCE_PROOF"
    else:
        status="CONFLICTING_NUMERIC_SHAPE_QUARANTINE"
    return {"status":status,"closed_m5_issuer_authenticated":False,
            "historical_bar_same_identity_proven":False,
            "rest_timestamp_start_semantics_verified":False,
            "first_known_or_revision_evidence_verified":False,
            "can_emit_signal":False}

def fake_fixture():
    start=fabricated().time
    req=UntrustedRequest("FPT",start,start+900)
    def page(stamps,next_time):
        return {"t":list(stamps),"o":[100]*len(stamps),
                "h":[102]*len(stamps),"l":[99]*len(stamps),
                "c":[101]*len(stamps),"v":[50]*len(stamps),
                "nextTime":next_time}
    pages=(FakePage(start,page((start,start+300),start+600)),
           FakePage(start+600,page((start+600,),0)))
    return req,pages,page((start,),0)

def build():
    req,pages,single=fake_fixture()
    receipt=inspect_fake_pages(req,pages)
    comparison=compare_fake_ws_closed_and_rest(single,req,fabricated())
    assert receipt["synthetic_pages_observed"]==2 and receipt["synthetic_rows_observed"]==3
    assert receipt["nexttime_zero_claimed_at_end"] is True
    assert comparison["status"]=="IDENTICAL_NUMERIC_SHAPE_NOT_SOURCE_PROOF"
    out={"schema":SCHEMA,"status":NO_GO,
         "documentation":{"rest_path":"/price/ohlc",
                          "resolution":"5",
                          "historical_response_fields":list(FIELDS)+["nextTime"],
                          "nexttime_zero_documented_no_more_data":True,
                          "authenticated_headers_documented_but_not_used":True,
                          "public_url":PUBLIC_DOC},
         "fake_pagination":receipt,
         "fake_closed_vs_rest":comparison,
         "source_lawful_entitlement_verified":False,
         "issuer_first_known_or_revision_ledger_verified":False,
         "official_exchange_calendar_verified":False,
         "real_history_saved":False,
         "real_drive_market_cache_enabled":False,
         "production_or_trading_allowed":False}
    raw=json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    out["synthetic_receipt_sha256"]=sha256(raw.encode("ascii")).hexdigest()
    return out

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path)
    args=p.parse_args(argv)
    out=build()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in out.items() if k!="fake_pagination"},sort_keys=True))

if __name__=="__main__":
    main()
