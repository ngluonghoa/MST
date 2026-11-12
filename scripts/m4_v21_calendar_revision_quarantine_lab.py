"""MST M3/M4 P0: revised fictional session policy, as-of and six-TF quarantine.

All dates and venue-like phases in this module are MADE UP. No issuer/venue
calendar, trading halt, holidays, source license, actual provider OHLCV,
Google Drive cache, signature or protected CAS is authenticated here.
Never interpret a syntactically accepted fixture as production eligibility.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path

from scripts.m4_v21_daily_partition_checkpoint_chain_lab import daily_scope
from scripts.m4_v21_gap_v1_numeric_parity_lab import start_for, SOURCE_COUNT
from scripts.m4_v21_multiday_all_tf_atr14_oracle_lab import (
    FakeDay, FakeHistory, fabricated_history, FAKE_DAYS, TIMEFRAMES,
    KIND_PER_DAY, per_day_groups, METADATA_KNOWN,
)
from scripts.m4_v21_source_revision_asof_ledger_lab import (
    ToyAsOfLedger, fabricate_ledger, utc,
)

SCHEMA = "mst.m3.v21.calendar-revision-source-admission.synthetic.v1"
STATUS = "ASOF_TOY_CALENDAR_REVISIONS_QUARANTINE_NO_MARKET_AUTHORITY"
GENESIS = "0" * 64
FIVE = timedelta(minutes=5)
CALENDAR_KNOWN_1 = METADATA_KNOWN + timedelta(minutes=5)
CALENDAR_KNOWN_2 = METADATA_KNOWN + timedelta(minutes=10)
STATES = frozenset(("OPEN", "CLOSED", "UNKNOWN"))
PHASES = frozenset(("CONTINUOUS", "AUCTION", "AFTER_HOURS", "HALTED", "UNKNOWN"))
BASE_POLICY = "TOY.CALENDAR.V1"
REV_POLICY = "TOY.CALENDAR.REVISION.V2"


def digest(obj: object) -> str:
    return sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()


@dataclass(frozen=True)
class ToyPhase:
    name: str
    start_utc: datetime
    end_utc: datetime
    kind: str

    def __post_init__(self):
        if self.name not in ("AM", "PM"):
            raise ValueError("EXPLICIT_AM_PM_LABEL_REQUIRED")
        utc(self.start_utc)
        utc(self.end_utc)
        if type(self.kind) is not str or self.kind not in PHASES:
            raise ValueError("TYPED_UNTRUSTED_PHASE_KIND_REQUIRED")
        if self.end_utc-self.start_utc != SOURCE_COUNT//2*FIVE:
            raise ValueError("EXACT_FICTIONAL_TWO_HOUR_SEGMENT_REQUIRED")


@dataclass(frozen=True)
class ToyCalendarDay:
    day: FakeDay
    policy_version: str
    status: str
    phases: tuple[ToyPhase, ToyPhase]
    issuer_calendar_authenticated: bool = False
    official_holiday_or_halt_proven: bool = False

    def __post_init__(self):
        if type(self.day) is not FakeDay or type(self.policy_version) is not str or self.policy_version not in (
            BASE_POLICY, REV_POLICY
        ):
            raise ValueError("VERSIONED_TOY_CALENDAR_DAY_REQUIRED")
        if self.status not in STATES:
            raise ValueError("TYPED_OPEN_CLOSED_UNKNOWN_STATE_REQUIRED")
        if (self.issuer_calendar_authenticated is not False
                or self.official_holiday_or_halt_proven is not False):
            raise PermissionError("CALLER_CANNOT_SELF_ATTEST_OFFICIAL_VENUE_EVENT")
        if type(self.phases) is not tuple or len(self.phases) != 2 or any(
            type(p) is not ToyPhase for p in self.phases
        ):
            raise TypeError("EXACT_TWO_TYPED_PHASES_REQUIRED")
        if tuple(p.name for p in self.phases) != ("AM", "PM"):
            raise ValueError("ORDERED_AM_PM_REQUIRED")
        shift = timedelta(days=self.day.ordinal)
        if (self.phases[0].start_utc != start_for(0)+shift
                or self.phases[0].end_utc != start_for(24)+shift-timedelta(hours=2)
                or self.phases[1].start_utc != start_for(24)+shift
                or self.phases[1].end_utc != start_for(47)+shift+FIVE):
            raise ValueError("TOY_PHASE_BOUNDS_OR_LUNCH_GAP_DRIFT")
        if self.phases[1].start_utc - self.phases[0].end_utc != timedelta(hours=2):
            raise ValueError("LUNCH_GAP_MUST_NOT_BE_STITCHED_AS_CONTINUOUS")
        if self.status == "CLOSED" and any(p.kind == "CONTINUOUS" for p in self.phases):
            # A closed date may retain two candidate historic phases but must
            # not silently elevate any of them into open market bars.
            pass

    def eligible(self, m5_index: int) -> bool:
        if type(m5_index) is not int or not 0 <= m5_index < SOURCE_COUNT:
            raise ValueError("DECLARED_M5_SLOT_REQUIRED")
        if self.status != "OPEN":
            return False
        return self.phases[0 if m5_index < 24 else 1].kind == "CONTINUOUS"

    @property
    def scoped_policy_digest(self) -> str:
        scope = daily_scope("M5", self.day)
        return digest({
            "full_v1_v2_binding": scope.binding_sha256,
            "candidate_partition": scope.candidate.digest,
            "calendar_policy_version": self.policy_version,
            "date": scope.candidate.session_date_local.isoformat(),
            "status": self.status,
            "phase_kinds": [p.kind for p in self.phases],
        })


@dataclass(frozen=True)
class ToyCalendarEvent:
    calendar: ToyCalendarDay
    generation: int
    revision: str
    first_known_utc: datetime
    vendor_calendar_signature_verified: bool = False
    real_source_rights_verified: bool = False
    independent_protected_clock_verified: bool = False

    def __post_init__(self):
        if type(self.calendar) is not ToyCalendarDay:
            raise TypeError("EXACT_TOY_DAY_REQUIRED")
        if type(self.generation) is not int or self.generation < 1:
            raise ValueError("POSITIVE_VERSION_GENERATION_REQUIRED")
        if type(self.revision) is not str or self.revision not in ("r1", "r2", "r3"):
            raise ValueError("EXPLICIT_TOY_REVISION_REQUIRED")
        utc(self.first_known_utc)
        if self.first_known_utc < self.calendar.day.m5[0].start_utc-timedelta(minutes=1):
            raise PermissionError("CALENDAR_REVISION_KNOWN_BEFORE_DECLARED_TOY_FIRST_KNOWN")
        if any((self.vendor_calendar_signature_verified,
                self.real_source_rights_verified,
                self.independent_protected_clock_verified)):
            raise PermissionError("CALENDAR_EVENT_CANNOT_SELF_GRANT_EXTERNAL_PROOF")


@dataclass(frozen=True)
class ToyCalendarLink:
    event: ToyCalendarEvent
    parent_sha256: str
    sha256: str


def payload(event: ToyCalendarEvent) -> dict:
    cal = event.calendar
    return {
        "schema": SCHEMA,
        "date_ordinal": cal.day.ordinal,
        "policy_scope_sha256": cal.scoped_policy_digest,
        "generation": event.generation,
        "revision": event.revision,
        "first_known_utc": event.first_known_utc.isoformat(),
        "issuer_verified": event.vendor_calendar_signature_verified,
        "rights_verified": event.real_source_rights_verified,
        "protected_clock_verified": event.independent_protected_clock_verified,
    }


class ToyCalendarLedger:
    """Pure in-memory hypothetical calendar revisions, no external custody."""

    def __init__(self, history: FakeHistory):
        if type(history) is not FakeHistory:
            raise TypeError("EXACT_FAKE_HISTORY_REQUIRED")
        self.history = history
        self._links: list[ToyCalendarLink] = []
        self._versions: dict[int, list[ToyCalendarEvent]] = {}

    @property
    def links(self) -> tuple[ToyCalendarLink, ...]:
        return tuple(self._links)

    def append(self, event: ToyCalendarEvent) -> ToyCalendarLink:
        if type(event) is not ToyCalendarEvent:
            raise TypeError("TYPED_CALENDAR_EVENT_REQUIRED")
        day = event.calendar.day.ordinal
        if event.calendar.day != self.history.days[day]:
            raise PermissionError("FOREIGN_OR_MUTATED_TOY_DAY_SOURCE")
        if self._links and event.first_known_utc < self._links[-1].event.first_known_utc:
            raise PermissionError("GLOBAL_CALENDAR_FIRST_KNOWN_REWIND")
        previous = self._versions.get(day, [])
        if not previous:
            if (event.generation != 1 or event.revision != "r1"
                    or event.calendar.policy_version != BASE_POLICY):
                raise ValueError("TOY_CALENDAR_GENESIS_VERSION_REQUIRED")
        else:
            old = previous[-1]
            if event.generation != old.generation+1:
                raise ValueError("CALENDAR_REVISION_SEQUENCE_GAP_OR_REPLAY")
            if event.first_known_utc <= old.first_known_utc:
                raise PermissionError("CALENDAR_FIRST_KNOWN_MUST_ADVANCE")
            if event.revision == old.revision:
                raise ValueError("CALENDAR_REVISION_ID_REUSE")
            if event.calendar.scoped_policy_digest == old.calendar.scoped_policy_digest:
                raise ValueError("CALENDAR_REVISION_NO_POLICY_CHANGE")
            if event.calendar.policy_version == old.calendar.policy_version:
                raise ValueError("CALENDAR_CHANGE_REQUIRES_POLICY_VERSION_ROTATION")
        parent = self._links[-1].sha256 if self._links else GENESIS
        link = ToyCalendarLink(event, parent, digest({"parent": parent, "event": payload(event)}))
        self._links.append(link)
        self._versions.setdefault(day, []).append(event)
        return link

    def verify(self):
        parent = GENESIS
        for link in self._links:
            if (link.parent_sha256 != parent or
                    link.sha256 != digest({"parent": parent, "event": payload(link.event)})):
                raise PermissionError("LOCAL_TOY_CALENDAR_SHA_TAMPERING")
            parent = link.sha256

    def snapshot(self, as_of_utc: datetime) -> dict[int, ToyCalendarDay]:
        now = utc(as_of_utc)
        out = {}
        for day, entries in self._versions.items():
            visible = next((e for e in reversed(entries) if e.first_known_utc <= now), None)
            if visible is not None:
                out[day] = visible.calendar
        return out


def make_toy_day(day: FakeDay, *, status: str="OPEN", am: str="CONTINUOUS",
                 pm: str="CONTINUOUS", policy: str=BASE_POLICY) -> ToyCalendarDay:
    if type(day) is not FakeDay:
        raise TypeError("EXACT_DAY_FIXTURE_REQUIRED")
    shift = timedelta(days=day.ordinal)
    return ToyCalendarDay(
        day, policy, status, (
            ToyPhase("AM",start_for(0)+shift,start_for(23)+shift+FIVE,am),
            ToyPhase("PM",start_for(24)+shift,start_for(47)+shift+FIVE,pm),
        ),
    )


def fabricate_calendar_ledger(history: FakeHistory) -> ToyCalendarLedger:
    ledger = ToyCalendarLedger(history)
    for day in history.days:
        cal = make_toy_day(day)
        ledger.append(ToyCalendarEvent(
            cal,1,"r1",day.m5[0].start_utc-timedelta(minutes=1)))
    # Both events are MADE UP revisions known only after entire toy source
    # history. Do not infer that either is a real venue announcement.
    holiday = make_toy_day(history.days[3],status="CLOSED",policy=REV_POLICY)
    ledger.append(ToyCalendarEvent(holiday,2,"r2",CALENDAR_KNOWN_1))
    halt = make_toy_day(history.days[8],pm="HALTED",policy=REV_POLICY)
    ledger.append(ToyCalendarEvent(halt,2,"r2",CALENDAR_KNOWN_2))
    return ledger


def admission_preview(source: ToyAsOfLedger, calendar: ToyCalendarLedger,
                      *, as_of_utc: datetime) -> dict:
    """Structural six-TF quarantine *preview*: NEVER grants source reuse."""
    if type(source) is not ToyAsOfLedger or type(calendar) is not ToyCalendarLedger:
        raise TypeError("EXACT_TOY_SOURCE_AND_CALENDAR_LEDGER_REQUIRED")
    now = utc(as_of_utc)
    # Authentication and real source consent remain impossible in this lab.
    visible_source = source.snapshot(as_of_utc=now,require_complete=False)
    visible_cal = calendar.snapshot(now)
    if len(visible_cal) != FAKE_DAYS:
        raise PermissionError("MISSING_ASOF_DAY_CALENDAR_NO_PARTIAL_PROMOTION")
    if source.history != calendar.history:
        raise PermissionError("CROSS_HISTORY_SOURCE_CALENDAR_MIX_DENIED")
    admitted: dict[int,set[int]] = {}
    quarantined: dict[int,set[int]] = {}
    unknown: dict[int,set[int]] = {}
    policy_rotations=[]
    for day in source.history.days:
        index=day.ordinal
        cal=visible_cal[index]
        if cal.day != day:
            raise PermissionError("WRONG_ASOF_CALENDAR_DATE_SCOPE")
        if cal.policy_version != BASE_POLICY:
            policy_rotations.append(index)
        admitted[index]=set()
        quarantined[index]=set()
        unknown[index]=set()
        for idx in range(SOURCE_COUNT):
            if (index,idx) not in visible_source:
                unknown[index].add(idx)
            elif cal.eligible(idx):
                admitted[index].add(idx)
            else:
                quarantined[index].add(idx)
    impacted={}
    for tf in TIMEFRAMES:
        groups=per_day_groups(tf)
        impacted[tf] = sum(
            1 for day in source.history.days for group in groups
            if set(group.members) & (quarantined[day.ordinal] | unknown[day.ordinal])
        )
    quarantined_count=sum(map(len,quarantined.values()))
    unknown_count=sum(map(len,unknown.values()))
    return {
        "schema":SCHEMA,"status":STATUS,
        "as_of_utc":now.isoformat(),
        "source_observed_m5":len(visible_source),
        "source_unknown_m5":unknown_count,
        "structurally_admissible_m5":sum(map(len,admitted.values())),
        "quarantined_known_m5":quarantined_count,
        "quarantined_day_ordinals":sorted(i for i,v in quarantined.items() if v),
        "full_policy_rotation_day_ordinals":policy_rotations,
        "six_tf_affected_windows":impacted,
        "six_tf_affected_total":sum(impacted.values()),
        "candidate_calendar_policy_digests":{str(day):visible_cal[day].scoped_policy_digest for day in range(FAKE_DAYS)},
        "any_incomplete_or_quarantined":bool(quarantined_count or unknown_count),
        "calendar_claim_is_fictional":True,
        "real_calendar_issuer_verified":False,
        "real_holiday_or_halt_verified":False,
        "rights_for_live_market_data_or_cloud_cache":False,
        "old_calendar_policy_cache_reuse_authorized":False,
        "source_first_known_by_actual_issuer_verified":False,
        "real_gdrive_quote_cache_read_write":False,
        "protected_cloud_signer_floor_cas_verified":False,
        "production_release_or_trading_permitted":False,
    }


def run_lab() -> dict:
    source,original,_,_ = fabricate_ledger()
    calendar = fabricate_calendar_ledger(original)
    from scripts.m4_v21_multiday_all_tf_atr14_oracle_lab import COLD_AT
    baseline=admission_preview(source,calendar,as_of_utc=COLD_AT)
    holiday=admission_preview(source,calendar,as_of_utc=CALENDAR_KNOWN_1)
    revised=admission_preview(source,calendar,as_of_utc=CALENDAR_KNOWN_2)
    if (baseline["quarantined_known_m5"]!=0 or
        holiday["quarantined_known_m5"]!=48 or
        revised["quarantined_known_m5"]!=72 or
        revised["full_policy_rotation_day_ordinals"]!=[3,8] or
        revised["six_tf_affected_windows"]!={
            "M5":72,"M15":24,"M30":12,"H1":6,"H4":2,"D1":2
        } or
        revised["six_tf_affected_total"]!=118):
        raise AssertionError("TOY_CALENDAR_CAUSAL_QUARANTINE_COUNTS_DRIFT")
    if revised["candidate_calendar_policy_digests"]["3"]==baseline["candidate_calendar_policy_digests"]["3"]:
        raise AssertionError("CALENDAR_RIGHTS_SCOPE_DIGEST_MUST_ROTATE")
    return {
        "schema":SCHEMA,"status":STATUS,
        "initial_fabricated_calendar_days":FAKE_DAYS,
        "untrusted_calendar_events":len(calendar.links),
        "two_retroactive_calendar_corrections_at_different_known_times":True,
        "baseline_before_calendar_revisions":baseline,
        "after_fake_holiday_correction":holiday,
        "after_fake_halt_correction":revised,
        "six_tf_affected_windows_final":revised["six_tf_affected_windows"],
        "old_policy_reuse_for_changed_days_denied":True,
        "missing_external_issuer_rights_and_calendar_proof":True,
        "real_storage_trading_or_release_authorized":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path)
    args=p.parse_args(argv)
    report=run_lab()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":STATUS,"toy_calendar_events":report["untrusted_calendar_events"],
        "fake_quarantined_m5":report["after_fake_halt_correction"]["quarantined_known_m5"],
        "affected_toy_six_tf_windows":report["after_fake_halt_correction"]["six_tf_affected_total"],
        "real_source_and_trading_no_go":True,
    },sort_keys=True))


if __name__=="__main__":
    main()
