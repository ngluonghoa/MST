"""A03 test-only multi-segment M5 candidate over an exchange-like lunch break.

Structural QA ONLY. Official HOSE/HNX schedules are contextual requirements,
not issuer credentials, actual provider bar availability or live calendars.
No V1 or V2 source module is modified or imported as a new product API.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from swing_trading.session_calendar import SessionType
from scripts.m2_a03_v2_session_pit_screen_lab import (
    UntrustedSessionSlot, UntrustedVersionedBar, fixtures,
    screen, partition_from_scope, utc, FIVE,
)
from scripts.m2_a03_revision_tombstone_hypothesis_lab import (
    FixtureRevision, RevisionKind,
)
from scripts.m2_a03_v2_cache_consumer_contract import FixtureV2ConsumerScope
from swing_trading.incremental_cache import FixtureBar

SCHEMA = "mst.a03.multi-segment-m5-session-gap.untrusted-qa.v1"
STATUS = "MULTI_SEGMENT_SESSION_SCREENER_ONLY_NO_OFFICIAL_CALENDAR"
VN = ZoneInfo("Asia/Ho_Chi_Minh")
DENIED = (
    "exchange_calendar_issuer_authenticated",
    "official_auction_bar_aggregation_verified",
    "source_bar_first_known_and_revision_issuer_verified",
    "licensed_market_data_or_cache_rights",
    "complete_holiday_and_halt_handling_verified",
    "historical_vendor_correction_closure_verified",
    "original_v1_or_v2_changed",
    "market_data_or_production_cache_activated",
    "owner_a02_signed", "owner_a03_v2_signed",
    "owner_a03_gate_approved", "production_release_authorized",
    "trading_authorized",
)


def vn_utc(h: int, minute: int, *, day=9) -> datetime:
    return datetime(2026,11,day,h,minute,tzinfo=VN).astimezone(timezone.utc)


@dataclass(frozen=True)
class CandidateSegment:
    slot: UntrustedSessionSlot
    kind: SessionType
    venue: str
    label: str

    def __post_init__(self):
        if type(self.slot) is not UntrustedSessionSlot or type(self.kind) is not SessionType:
            raise TypeError("EXACT_TYPED_SESSION_SLOT_AND_PHASE_REQUIRED")
        if type(self.venue) is not str or self.venue not in ("HOSE","HNX","UPCOM"):
            raise ValueError("EXPLICIT_RECOGNIZED_EXCHANGE_REQUIRED")
        if type(self.label) is not str or re.fullmatch(r"[A-Z0-9_]{1,24}",self.label) is None:
            raise ValueError("EXPLICIT_SAFE_SEGMENT_ID_REQUIRED")


@dataclass(frozen=True)
class UntrustedMultiSegmentDay:
    scope: FixtureV2ConsumerScope
    trading_day_local: date
    segments: tuple[CandidateSegment, ...]
    calendar_source_issuer_authenticated: bool = False

    def __post_init__(self):
        if type(self.scope) is not FixtureV2ConsumerScope or type(self.trading_day_local) is not date:
            raise TypeError("EXPLICIT_V2_SCOPE_AND_TRADING_DATE_REQUIRED")
        if self.trading_day_local != self.scope.candidate.session_date_local:
            raise ValueError("SESSION_DATE_SCOPE_BINDING_MISMATCH")
        if type(self.segments) is not tuple or not (2 <= len(self.segments) <= 8):
            raise ValueError("EXACT_BOUNDED_MULTISEGMENT_TUPLE_REQUIRED")
        if self.calendar_source_issuer_authenticated is not False:
            raise PermissionError("PUBLIC_PAGE_OR_CALLER_FLAG_CANNOT_AUTHENTICATE_CALENDAR")
        seen=set()
        previous_end=None
        for seg in self.segments:
            if type(seg) is not CandidateSegment:
                raise TypeError("EXACT_CANDIDATE_SEGMENT_REQUIRED")
            if seg.slot.partition != self.scope.candidate:
                raise ValueError("SEGMENT_SOURCE_PARTITION_MISMATCH")
            if seg.venue != self.scope.legacy.exchange:
                raise ValueError("CROSS_EXCHANGE_SEGMENT_MISMATCH")
            if seg.label in seen:
                raise ValueError("DUPLICATE_CANDIDATE_SEGMENT_LABEL")
            seen.add(seg.label)
            start,end=seg.slot.starts_at_utc,seg.slot.ends_at_utc
            if (start.astimezone(VN).date() != self.trading_day_local or
                (end-timedelta(microseconds=1)).astimezone(VN).date()!=self.trading_day_local):
                raise ValueError("SEGMENT_CROSSES_WRONG_VN_LOCAL_DAY")
            if previous_end is not None and start < previous_end:
                raise ValueError("OVERLAPPING_OR_UNORDERED_SEGMENT_WINDOWS")
            previous_end=end


def candidate_screen(
    day: UntrustedMultiSegmentDay,
    rows: tuple[UntrustedVersionedBar, ...],
    *,
    claimed_segment: str,
    as_of_utc: datetime,
) -> dict:
    """A named *synthetic* phase is not a vendor-issued session credential."""
    if type(day) is not UntrustedMultiSegmentDay:
        raise TypeError("EXACT_MULTISEGMENT_ENVELOPE_REQUIRED")
    now=utc(as_of_utc)
    if type(claimed_segment) is not str:
        raise TypeError("EXPLICIT_SEGMENT_ID_REQUIRED")
    selected=next((s for s in day.segments if s.label==claimed_segment),None)
    if selected is None:
        raise ValueError("UNKNOWN_SEGMENT_NOT_ADMITTED")
    # Auction-close M5 candles are provider-aggregation-specific; public
    # trading hours DO NOT certify their candle derivation. Do not silently
    # interpret auction/after-hours as ordinary continuous M5 trades.
    if selected.kind is not SessionType.CONTINUOUS:
        raise PermissionError("NONCONTINUOUS_MARKET_PHASE_NEEDS_OWNER_POLICY")
    if type(rows) is not tuple or not rows or any(type(r) is not UntrustedVersionedBar for r in rows):
        raise TypeError("EXACT_RETAINED_BAR_HISTORY_REQUIRED")
    for r in rows:
        if not (selected.slot.starts_at_utc <= r.bar.start_utc and
                r.bar.end_utc <= selected.slot.ends_at_utc and
                r.bar.start_utc in selected.slot.permitted_bar_starts_utc):
            raise ValueError("CANDLE_OUTSIDE_CLAIMED_CONTINUOUS_SEGMENT")
    # Delegate all source partition, SHA/clock/revision chain and as-of
    # rules to the EXISTING strict test-only A03 screen.
    result=screen(day.scope,selected.slot,rows,as_of_utc=now)
    return {
        "schema":SCHEMA, "status":STATUS, "selected_segment":selected.label,
        "visible_revision_count":result["visible_revision_count"],
        "candidate_revision_id":result["candidate_revision_id"],
        "candidate_digest":result["candidate_fixture_digest"],
        "calendar_issuer_authenticated":False,
        "session_source_independently_verified":False,
        **{key:False for key in DENIED},
    }


def records_at(start: datetime, scope: FixtureV2ConsumerScope,
               *, event: str, rev: str = "r1",
               first_known: datetime | None = None,
               close=None, predecessor: str | None = None):
    _,_,prior,_,_=fixtures()
    orig=prior[0].bar
    known=start+FIVE if first_known is None else utc(first_known)
    changes={"start_utc":start,"end_utc":start+FIVE,
             "first_known_utc":known,"revision":rev}
    if close is not None:
        from decimal import Decimal
        changes["close"]=Decimal(str(close))
        changes["high"]=max(orig.high,Decimal(str(close))+Decimal("1"))
    b=replace(orig,**changes)
    sequence=1 if predecessor is None else 2
    r=FixtureRevision(
        partition_from_scope(scope),event,rev,sequence,
        RevisionKind.UPSERT,start,known,supersedes_revision_id=predecessor,
        payload_sha256=b.normalized_digest)
    return UntrustedVersionedBar(r,b,scope.candidate)


def fixtures_day():
    scope,_,_,_,_=fixtures()
    # A tiny fabricated pair of CONTINUOUS segments follows the published
    # HOSE lunch gap pattern but is NOT an official calendar publication.
    am=vn_utc(11,20)
    pm=vn_utc(13,0)
    def segment(label,begin,kind=SessionType.CONTINUOUS):
        slot=UntrustedSessionSlot(scope.candidate,begin,begin+2*FIVE,
            (begin,begin+FIVE))
        return CandidateSegment(slot,kind,"HOSE",label)
    day=UntrustedMultiSegmentDay(
        scope,date(2026,11,9),
        (segment("AM_LAST",am),segment("PM_FIRST",pm)),
    )
    morning=records_at(am,scope,event="MORNING_BAR")
    noon=records_at(pm,scope,event="AFTERNOON_BAR")
    late_at=vn_utc(9,5,day=10)
    late=records_at(am,scope,event="MORNING_BAR",rev="r2",close="250",
                    first_known=late_at,predecessor="r1")
    gap=records_at(vn_utc(12,0),scope,event="BREAK_CANDLE")
    crossing=records_at(vn_utc(11,25),scope,event="CROSSES_LUNCH")
    # The source event-time is the morning bar, although the new revision
    # becomes known on the FOLLOWING day.
    return day,morning,noon,late,gap,crossing,late_at


def build() -> dict:
    day,am,pm,late,gap,cross,known=fixtures_day()
    checks=[]
    def need(label,condition):
        if not condition:
            raise AssertionError("A03_MULTI_SEGMENT_NEGATIVE_CASE_DRIFT_"+label)
        checks.append(label)
    early=candidate_screen(day,(am,late),claimed_segment="AM_LAST",
        as_of_utc=known-timedelta(microseconds=1))
    current=candidate_screen(day,(am,late),claimed_segment="AM_LAST",
        as_of_utc=known)
    afternoon=candidate_screen(day,(pm,),claimed_segment="PM_FIRST",
        as_of_utc=pm.bar.first_known_utc)
    need("AM_R1_BEFORE_PUBLICATION",early["candidate_revision_id"]=="r1")
    need("AM_R2_AT_EXACT_FIRST_KNOWN",current["candidate_revision_id"]=="r2")
    need("PM_INDEPENDENT_EVENT_ACCEPTED",afternoon["candidate_revision_id"]=="r1")
    need("LATE_PUBLICATION_NOT_WRONG_EVENT_SESSION",
         late.bar.first_known_utc>day.segments[-1].slot.ends_at_utc)
    need("AM_PM_CANDIDATE_DIFFERENT_DIGESTS",
         current["candidate_digest"]!=afternoon["candidate_digest"])
    need("AM_PM_UNTRUSTED_ISSUER",not current["calendar_issuer_authenticated"])
    def reject(name,fn,expected):
        try:
            fn()
        except expected:
            checks.append(name)
        else:
            raise AssertionError("UNTRUSTED_SESSION_GAP_FAIL_OPEN_"+name)
    reject("LUNCH_GAP_CANDLE_DENIED",
        lambda:candidate_screen(day,(gap,),claimed_segment="AM_LAST",
            as_of_utc=gap.bar.first_known_utc),ValueError)
    reject("LUNCH_CROSSING_M5_CANDLE_DENIED",
        lambda:candidate_screen(day,(cross,),claimed_segment="AM_LAST",
            as_of_utc=cross.bar.first_known_utc),ValueError)
    reject("PM_BAR_MISCLAIMED_AS_AM_DENIED",
        lambda:candidate_screen(day,(pm,),claimed_segment="AM_LAST",
            as_of_utc=pm.bar.first_known_utc),ValueError)
    reject("AM_BAR_MISCLAIMED_AS_PM_DENIED",
        lambda:candidate_screen(day,(am,),claimed_segment="PM_FIRST",
            as_of_utc=am.bar.first_known_utc),ValueError)
    reject("UNKNOWN_PHASE_ID_DENIED",
        lambda:candidate_screen(day,(pm,),claimed_segment="NOT_A_SLOT",
            as_of_utc=pm.bar.first_known_utc),ValueError)
    auction=replace(day.segments[1],kind=SessionType.AUCTION)
    auction_day=replace(day,segments=(day.segments[0],auction))
    reject("AUCTION_BAR_UNPROVEN_DENIED",
        lambda:candidate_screen(auction_day,(pm,),claimed_segment="PM_FIRST",
            as_of_utc=pm.bar.first_known_utc),PermissionError)
    reject("CALENDAR_SELF_ATTESTATION_DENIED",
        lambda:replace(day,calendar_source_issuer_authenticated=True),PermissionError)
    reject("MISORDERED_SEGMENT_BOUNDS_DENIED",
        lambda:replace(day,segments=day.segments[::-1]),ValueError)
    reject("WRONG_VENUE_SEGMENT_DENIED",
        lambda:replace(day,segments=(day.segments[0],
            replace(day.segments[1],venue="HNX"))),ValueError)
    need("NO_PRODUCTION_AUTHORITY",not afternoon["trading_authorized"])
    if len(checks)!=16:
        raise AssertionError("EXPECTED_SIXTEEN_COMPOSED_SEGMENT_ASSERTIONS")
    out={
        "schema":SCHEMA,"status":STATUS,"checks":checks,"assertion_count":len(checks),
        "untrusted_segments":len(day.segments),
        "modeled_lunch_gap_minutes":int(
            (day.segments[1].slot.starts_at_utc-
             day.segments[0].slot.ends_at_utc).total_seconds()/60),
        "morning_early_revision":early["candidate_revision_id"],
        "morning_late_revision":current["candidate_revision_id"],
        "afternoon_independent_revision":afternoon["candidate_revision_id"],
        "break_candle_rejected_by_synthetic_slot":True,
        "auction_candle_unqualified_and_blocked":True,
        "public_exchange_trading_hours_are_context_not_issuer_proof":True,
        **{k:False for k in DENIED},
    }
    payload=json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    out["synthetic_sha256"]=sha256(payload.encode("ascii")).hexdigest()
    return out


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path)
    args=p.parse_args(argv)
    report=build()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="checks"},sort_keys=True))


if __name__=="__main__":
    main()
