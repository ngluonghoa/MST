"""MST A03 test-only candidate: session membership + retained-revision as-of screening.

Compose EXISTING inherited V1 source and opt-in V2 partition, consumer scope
and A03 untrusted revision resolver. This code is under scripts/ (QA ONLY),
NOT an imported/activated production module or authenticated provider API.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from swing_trading.incremental_cache import FixtureBar, SyntheticIncrementalStore
from swing_trading.v2_cache_partition_plan import FixturePartitionV2
from scripts.m2_a03_v2_cache_consumer_contract import (
    FixtureV2ConsumerScope, fixture_scope, preview_v2_consumer,
)
from scripts.m2_a03_revision_tombstone_hypothesis_lab import (
    FixturePartition, FixtureRevision, RevisionKind, resolve_untrusted_fixture,
)
from scripts.m2_a02_incremental_cache_oracle_lab import (
    bar as fabricated_bar, instant, _apply,
)

SCHEMA = "mst.a03.opt-in-session-pit-screening.untrusted-no-apply.v1"
STATUS = "SYNTHETIC_SESSION_AND_ASOF_SCREEN_ONLY_NO_SOURCE_AUTHORITY"
FIVE = timedelta(minutes=5)
DENIED = (
    "external_exchange_calendar_authenticated",
    "provider_session_membership_authenticated",
    "revision_ledger_completeness_authenticated",
    "source_first_known_issuer_authenticated",
    "licensed_historical_data_authorized",
    "real_google_drive_cache_implemented",
    "external_floor_or_cas_verified",
    "existing_v1_or_v2_module_modified",
    "owner_a02_63_approved", "owner_a03_v2_8_approved",
    "owner_a03_14_choices_approved",
    "production_release_authorized", "trading_authorized",
)


def utc(value: datetime) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or (
        value.utcoffset() != timedelta(0)
    ):
        raise ValueError("EXPLICIT_EXACT_UTC_INSTANT_REQUIRED")
    return value


@dataclass(frozen=True)
class UntrustedSessionSlot:
    """Caller-supplied synthetic candle grid; NOT a real VN trading calendar."""
    partition: FixturePartitionV2
    starts_at_utc: datetime
    ends_at_utc: datetime
    permitted_bar_starts_utc: tuple[datetime, ...]
    independently_calendar_verified: bool = False

    def __post_init__(self):
        if type(self.partition) is not FixturePartitionV2:
            raise TypeError("TYPED_V2_PARTITION_REQUIRED")
        if self.partition.timeframe != "M5":
            raise ValueError("THIS_SYNTHETIC_GRID_ONLY_MODELS_M5")
        start, end = utc(self.starts_at_utc), utc(self.ends_at_utc)
        if start >= end or end-start > timedelta(days=1):
            raise ValueError("POSITIVE_BOUNDED_FIXTURE_SESSION_REQUIRED")
        starts = self.permitted_bar_starts_utc
        if type(starts) is not tuple or not (1 <= len(starts) <= 64):
            raise ValueError("IMMUTABLE_NONEMPTY_SYNTHETIC_SESSION_GRID_REQUIRED")
        if any(type(x) is not datetime for x in starts):
            raise TypeError("TYPED_GRID_INSTANTS_REQUIRED")
        if any(utc(x) < start or x + FIVE > end for x in starts):
            raise ValueError("CANDLE_START_NOT_WITHIN_FIXTURE_SESSION")
        if tuple(sorted(set(starts))) != starts:
            raise ValueError("UNIQUE_SORTED_FIXTURE_GRID_REQUIRED")
        if self.independently_calendar_verified is not False:
            raise PermissionError("SELF_REPORTED_CALENDAR_AUTHORITY_NOT_ACCEPTED")


@dataclass(frozen=True)
class UntrustedVersionedBar:
    """Retained fake content plus original A03 strict revision-identity metadata."""
    revision: FixtureRevision
    bar: FixtureBar
    claimed_partition: FixturePartitionV2

    def __post_init__(self):
        if (type(self.revision) is not FixtureRevision or
            type(self.bar) is not FixtureBar or
            type(self.claimed_partition) is not FixturePartitionV2):
            raise TypeError("EXACT_UNTRUSTED_REVISION_BAR_AND_V2_SCOPE_REQUIRED")
        if (self.revision.kind is not RevisionKind.UPSERT or
            self.revision.revision_id != self.bar.revision or
            self.revision.event_time_utc != self.bar.start_utc or
            self.revision.first_known_utc != self.bar.first_known_utc or
            self.revision.payload_sha256 != self.bar.normalized_digest or
            not self.bar.closed):
            raise ValueError("REVISION_PAYLOAD_OR_FIRST_KNOWN_BINDING_MISMATCH")


def partition_from_scope(scope: FixtureV2ConsumerScope) -> FixturePartition:
    if type(scope) is not FixtureV2ConsumerScope:
        raise TypeError("EXPLICIT_V1_TO_V2_CONSUMER_BINDING_REQUIRED")
    c = scope.candidate
    return FixturePartition(c.provider_id,c.endpoint_id,c.symbol,c.timeframe,
                            c.price_basis,scope.legacy.session_id)


def screen(
    scope: FixtureV2ConsumerScope,
    slot: UntrustedSessionSlot,
    versions: tuple[UntrustedVersionedBar, ...],
    *,
    as_of_utc: datetime,
) -> dict:
    """Screen structure and event-known cutoffs; NEVER elevate to source truth."""
    if type(scope) is not FixtureV2ConsumerScope or type(slot) is not UntrustedSessionSlot:
        raise TypeError("EXACT_V2_SCOPE_AND_FIXTURE_SLOT_REQUIRED")
    at = utc(as_of_utc)
    if slot.partition != scope.candidate:
        raise ValueError("V2_SESSION_PARTITION_GRID_SCOPE_MISMATCH")
    if type(versions) is not tuple or not (1 <= len(versions) <= 32):
        raise ValueError("RETAINED_IMMUTABLE_REVISION_HISTORY_REQUIRED")
    if any(type(x) is not UntrustedVersionedBar for x in versions):
        raise TypeError("EXACT_TYPED_RETAINED_FIXTURE_VERSION_REQUIRED")
    expected = partition_from_scope(scope)
    root = versions[0].revision
    for item in versions:
        b, r = item.bar, item.revision
        if item.claimed_partition != scope.candidate or r.partition != expected:
            raise ValueError("SOURCE_SESSION_OR_POLICY_IDENTITY_MISMATCH")
        if (b.start_utc not in slot.permitted_bar_starts_utc or
            b.start_utc < slot.starts_at_utc or b.end_utc > slot.ends_at_utc or
            b.end_utc-b.start_utc != FIVE):
            raise ValueError("EXPLICIT_FIXTURE_CANDLE_SESSION_MEMBERSHIP_REJECTED")
        if r.event_id != root.event_id or r.event_time_utc != root.event_time_utc:
            raise ValueError("MIXED_CANDLE_EVENT_HISTORY_REJECTED")
    ledger = tuple(item.revision for item in versions)
    if [r.sequence for r in ledger] != list(range(1,len(ledger)+1)):
        raise ValueError("NO_MISSING_OR_UNORDERED_REVISION_PREFIX")
    # Validate the *whole supplied* fixture chain, including future-known
    # retained revisions, BEFORE deriving its narrower as-of candidate.
    closure_clock = max(at,*(r.first_known_utc for r in ledger))
    resolve_untrusted_fixture(expected,root.event_id,ledger,
                              as_of_utc=closure_clock)
    view = resolve_untrusted_fixture(expected,root.event_id,ledger,
                                     as_of_utc=at)
    visible = tuple(item for item in versions
                    if item.revision.revision_id in view.visible_revision_ids)
    selected = next((item for item in visible
                     if item.revision.revision_id==view.candidate_revision_id),None)
    if selected is not None and (
        selected.bar.first_known_utc > at or selected.bar.end_utc > at
    ):
        raise PermissionError("ASOF_CANNOT_CONSUME_UNCLOSED_OR_FUTURE_KNOWN_BAR")
    return {
        "schema":SCHEMA,
        "status":STATUS,
        "candidate_state":view.status,
        "candidate_revision_id":view.candidate_revision_id,
        "candidate_fixture_digest":selected.bar.normalized_digest if selected else None,
        "visible_revision_count":len(view.visible_revision_ids),
        "retained_revision_count":len(versions),
        "candidate_partition_digest":scope.candidate.digest,
        "legacy_full_policy_binding_digest":scope.binding_sha256,
        "as_of_utc":at.isoformat(),
        "source_truth_status":"UNVERIFIED_UNTRUSTED_FIXTURE_CANDIDATE_ONLY",
        **{k:False for k in DENIED},
    }


def fixtures():
    scope=fixture_scope()
    start=instant(0)
    slot=UntrustedSessionSlot(
        scope.candidate,start,instant(20),
        tuple(instant(k) for k in (0,5,10,15)),
    )
    original=fabricated_bar(0)
    late_at=instant(0)+timedelta(days=1,minutes=15)
    correction=replace(fabricated_bar(0,close=250,revision="r2"),
                       first_known_utc=late_at)
    partition=partition_from_scope(scope)
    first=FixtureRevision(partition,"BAR_A0","r1",1,RevisionKind.UPSERT,
        original.start_utc,original.first_known_utc,
        payload_sha256=original.normalized_digest)
    next_revision=FixtureRevision(
        partition,"BAR_A0","r2",2,RevisionKind.UPSERT,
        correction.start_utc,correction.first_known_utc,
        supersedes_revision_id="r1",payload_sha256=correction.normalized_digest)
    records=(UntrustedVersionedBar(first,original,scope.candidate),
             UntrustedVersionedBar(next_revision,correction,scope.candidate))
    wrong_start=start+timedelta(days=1)
    wrong_bar=replace(original,start_utc=wrong_start,
                      end_utc=wrong_start+FIVE,
                      first_known_utc=wrong_start+FIVE)
    wrong_revision=FixtureRevision(partition,"BAR_B0","b1",1,RevisionKind.UPSERT,
        wrong_start,wrong_start+FIVE,
        payload_sha256=wrong_bar.normalized_digest)
    wrong=UntrustedVersionedBar(
        wrong_revision,replace(wrong_bar,revision="b1"),
        scope.candidate)
    # For this deliberately wrong record, digest must bind its revised body.
    return scope,slot,records,late_at,wrong_bar


def build() -> dict:
    scope,slot,records,late_at,wrong_bar=fixtures()
    checks=[]
    def need(label,yes):
        if not yes:
            raise AssertionError("A03_V2_SESSION_PIT_QA_DRIFT_"+label)
        checks.append(label)
    before=screen(scope,slot,records,as_of_utc=late_at-timedelta(microseconds=1))
    after=screen(scope,slot,records,as_of_utc=late_at)
    early=screen(scope,slot,records,as_of_utc=instant(10))
    need("RETAINED_R1_VISIBLE_BEFORE_CORRECTION",before["candidate_revision_id"]=="r1")
    need("RETAINED_R2_VISIBLE_AT_EXACT_FIRST_KNOWN",after["candidate_revision_id"]=="r2")
    need("EARLY_ASOF_SAME_R1",early["candidate_revision_id"]=="r1")
    need("CORRECTION_FIRST_KNOWN_PAST_SESSION_END_ALLOWED",late_at>slot.ends_at_utc)
    need("OLDER_ASOF_NEVER_SEES_R2",before["candidate_fixture_digest"]==
         records[0].bar.normalized_digest)
    need("CORRECTION_CHANGES_CONTENT_DIGEST",after["candidate_fixture_digest"]!=
         before["candidate_fixture_digest"])
    need("FULL_POLICY_HASH_BOUND",after["legacy_full_policy_binding_digest"]==
         scope.binding_sha256)
    need("SESSION_SLOT_PARTITION_HASH_BOUND",after["candidate_partition_digest"]==
         scope.candidate.digest)
    need("NO_REAL_SOURCE_CLAIM",not after["source_first_known_issuer_authenticated"])
    with TemporaryDirectory(prefix="mst-github-v2-session-pit-") as root:
        store=SyntheticIncrementalStore(Path(root)/"synthetic.sqlite")
        store.initialize()
        start=instant(0)
        _apply(store,scope.legacy,(records[0].bar,),now=20,start=0,end=1,
               complete=False)
        _apply(store,scope.legacy,(records[1].bar,),
               now=24*12+4,start=0,end=1,complete=False)
        # Slightly later than the replacement's first-known time.
        latest=store.read_bars(scope.legacy)
        need("ORIGINAL_V1_CURRENT_ONLY_STORE_RETURNS_CORRECTED_R2",
             latest[0].revision=="r2")
        try:
            preview_v2_consumer(store,scope,as_of_utc=instant(20),proposed_head=None)
        except PermissionError as e:
            need("EXISTING_V2_READONLY_CONSUMER_DENIES_OLD_ASOF",
                 "HISTORICAL_MATERIALIZED" in str(e))
        else:
            raise AssertionError("V2_MATERIALIZED_HISTORICAL_FAIL_OPEN")
        # Existing V1 can accept cross-session data under caller's A key.
        cross=_apply(store,scope.legacy,(wrong_bar,),now=24*12+5,
                     start=24*12,end=24*12+1,complete=False)
        need("LEGACY_WRONG_SESSION_REPRODUCER_ACCEPTS",cross.inserted==1)
        # Reusing the CURRENT V2 preview does not itself enforce a bar-to-slot
        # calendar mapping; it is a read-only, untrusted preview.
        raw=preview_v2_consumer(
            store,scope,as_of_utc=instant(24*12+5),proposed_head=None)
        need("EXISTING_V2_PREVIEW_CONTAINS_MISLABELED_BAR",
             raw["bar_count"]==2)
        # New test-only screening is explicitly separate from the V2 module.
        wrong_revision=FixtureRevision(partition_from_scope(scope),
            "BAR_B0","b1",1,RevisionKind.UPSERT,wrong_bar.start_utc,
            wrong_bar.first_known_utc,payload_sha256=wrong_bar.normalized_digest)
        wrong_row=UntrustedVersionedBar(
            wrong_revision,replace(wrong_bar,revision="b1"),
            scope.candidate)
        try:
            screen(scope,slot,(wrong_row,),as_of_utc=instant(24*12+5))
        except ValueError as e:
            need("PROPOSED_SCREEN_BLOCKS_WRONG_SESSION",
                 "SESSION_MEMBERSHIP_REJECTED" in str(e))
        else:
            raise AssertionError("TEST_ONLY_SCREEN_DID_NOT_DENY_WRONG_SESSION")
    need("NO_GO_EVEN_WITH_CORRECT_ASOF",not after["trading_authorized"])
    need("CALENDAR_CANNOT_BE_SELF_ATTESTED",slot.independently_calendar_verified is False)
    if len(checks)!=16:
        raise AssertionError("EXACT_SIXTEEN_FIXTURE_ASSERTIONS_REQUIRED")
    report={
        "schema":SCHEMA,"status":STATUS,
        "assertion_count":len(checks),"assertion_names":checks,
        "before_correction_candidate":"r1",
        "at_exact_correction_first_known_candidate":"r2",
        "legacy_latest_only_replays_new_revision_at_old_asof":False,
        "legacy_raw_store_returns_late_revision_without_asof":True,
        "existing_v2_consumer_old_asof_denied":True,
        "existing_v2_preview_wrong_session_not_authenticated":True,
        "proposed_test_only_slot_screen_rejects_cross_session":True,
        "no_real_calendar_or_issuer_admitted":True,
        **{k:False for k in DENIED},
    }
    raw=json.dumps(report,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    report["synthetic_sha256"]=sha256(raw.encode("ascii")).hexdigest()
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args(argv)
    report=build()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="assertion_names"},
                     sort_keys=True))


if __name__=="__main__":
    main()
