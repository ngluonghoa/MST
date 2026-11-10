"""MST Cache V2.1 P0 toy six-TF M5 dependency and causal checkpoint planner.

All 96 M5 bars are wholly invented over ONE ARTIFICIAL eight-hour no-break
session. D1 here means the declared fixture session, never an official VN D1
calendar. M15/M30/H1/H4/D1 membership is explicitly validated in this toy
grid; do not infer exchange sessions, auction bars or provider aggregation
from wall-clock multiples. No real market data, cache write, source entitlement,
issuer first-known, Google Drive connection, signer, CAS or trade is permitted.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
import json
from pathlib import Path

from scripts.m2_a03_v2_cache_consumer_contract import _utc, fixture_scope
from scripts.m4_v21_layered_invalidation_lab import FullPolicyFixture

SCHEMA = "mst.m4.cache-v2-1-six-tf-causal-slices.synthetic.v1"
STATUS = "SIX_TF_M5_DEPENDENCY_AND_CAUSAL_SUFFIX_SYNTHETIC_NO_GO"
FAKE_M5 = 96
BAR = timedelta(minutes=5)
TIMEFRAMES = ("M5", "M15", "M30", "H1", "H4", "D1")
FAKE_MEMBERS_PER_WINDOW = {
    "M5": 1, "M15": 3, "M30": 6, "H1": 12, "H4": 48, "D1": 96
}
# D1 = entire fabricated 8h session; NEVER a source-verified VN trading day.


class ChangeKind(str, Enum):
    PRICE_VOLUME_REVISION = "PRICE_VOLUME_REVISION"
    LINEAGE_ONLY = "LINEAGE_ONLY"
    UNQUALIFIED_SOURCE = "UNQUALIFIED_SOURCE"
    UNCHANGED = "UNCHANGED"


@dataclass(frozen=True)
class FixtureWindow:
    tf: str
    ordinal: int
    source_m5: tuple[int, ...]
    start_utc: datetime
    end_utc: datetime
    binding: str
    closed: bool = True
    scope_complete: bool = True

    def __post_init__(self):
        if type(self.tf) is not str or self.tf not in TIMEFRAMES:
            raise ValueError("EXACT_SUPPORTED_TF_REQUIRED")
        if type(self.ordinal) is not int or self.ordinal < 0:
            raise ValueError("NONNEGATIVE_EXACT_WINDOW_ORDINAL_REQUIRED")
        if type(self.source_m5) is not tuple or any(type(i) is not int for i in self.source_m5):
            raise TypeError("EXPLICIT_INTEGER_M5_CONSTITUENTS_REQUIRED")
        if not self.source_m5 or len(set(self.source_m5)) != len(self.source_m5):
            raise ValueError("NONEMPTY_UNIQUE_M5_MEMBERS_REQUIRED")
        _utc(self.start_utc)
        _utc(self.end_utc)
        if self.start_utc >= self.end_utc:
            raise ValueError("WINDOW_END_AFTER_START_REQUIRED")
        if type(self.binding) is not str or len(self.binding) != 64 or any(c not in "0123456789abcdef" for c in self.binding):
            raise ValueError("FULL_V1_POLICY_BINDING_SHA256_REQUIRED")
        if type(self.closed) is not bool or type(self.scope_complete) is not bool:
            raise TypeError("EXPLICIT_CLOSED_AND_COMPLETENESS_FLAGS_REQUIRED")
        if not self.closed or not self.scope_complete:
            raise PermissionError("OPEN_OR_INCOMPLETE_SOURCE_WINDOW_DENIED")


@dataclass(frozen=True)
class FixtureSixTFGrid:
    scope: FullPolicyFixture
    artificial_session_start_utc: datetime
    artificial_session_end_utc: datetime
    windows: tuple[FixtureWindow, ...]
    fixture_vendor_calendar_verified: bool = False

    def __post_init__(self):
        if type(self.scope) is not FullPolicyFixture:
            raise TypeError("FULL_V1_POLICY_TYPED_SCOPE_REQUIRED")
        start = _utc(self.artificial_session_start_utc)
        end = _utc(self.artificial_session_end_utc)
        if end - start != FAKE_M5 * BAR:
            raise ValueError("ONLY_EXPLICIT_ARTIFICIAL_EIGHT_HOUR_SESSION_ALLOWED")
        if type(self.fixture_vendor_calendar_verified) is not bool or self.fixture_vendor_calendar_verified:
            raise PermissionError("VENDOR_SESSION_CALENDAR_NOT_ATTESTED")
        if type(self.windows) is not tuple or any(type(w) is not FixtureWindow for w in self.windows):
            raise TypeError("ALL_SIX_TF_TYPED_WINDOWS_REQUIRED")
        found = {}
        for w in self.windows:
            if w.binding != self.scope.binding:
                raise PermissionError("FOREIGN_RIGHTS_CALENDAR_OR_INDICATOR_BINDING_DENIED")
            key=(w.tf,w.ordinal)
            if key in found:
                raise ValueError("DUPLICATE_TIMEFRAME_WINDOW_DENIED")
            found[key]=w
            ratio=FAKE_MEMBERS_PER_WINDOW[w.tf]
            expected=tuple(range(w.ordinal*ratio,(w.ordinal+1)*ratio))
            if w.source_m5 != expected:
                raise ValueError("MISSING_OVERLAPPING_OR_MISALIGNED_M5_MEMBERS_DENIED")
            if w.start_utc != start + w.ordinal*ratio*BAR or w.end_utc != start + (w.ordinal+1)*ratio*BAR:
                raise ValueError("WINDOW_START_END_BOUNDARY_MISMATCH")
        expected_keys={(tf,i) for tf in TIMEFRAMES for i in range(FAKE_M5//FAKE_MEMBERS_PER_WINDOW[tf])}
        if set(found) != expected_keys:
            raise ValueError("INCOMPLETE_SIX_TF_CLOSED_GRID_DENIED")

    @property
    def count_by_tf(self):
        return {tf:FAKE_M5//FAKE_MEMBERS_PER_WINDOW[tf] for tf in TIMEFRAMES}


@dataclass(frozen=True)
class FixtureSourceChange:
    kind: ChangeKind
    m5_indices: tuple[int, ...]
    full_policy_binding: str
    prior_as_of_utc: datetime
    first_known_utc: datetime
    as_of_utc: datetime

    def __post_init__(self):
        if type(self.kind) is not ChangeKind:
            raise TypeError("EXPLICIT_SOURCE_CHANGE_ENUM_REQUIRED")
        if type(self.m5_indices) is not tuple or any(type(i) is not int for i in self.m5_indices):
            raise TypeError("TYPED_EXPLICIT_M5_CHANGE_SET_REQUIRED")
        if len(self.m5_indices) != len(set(self.m5_indices)):
            raise ValueError("DUPLICATE_CHANGED_SOURCE_BAR_DENIED")
        if any(i < 0 or i >= FAKE_M5 for i in self.m5_indices):
            raise ValueError("OUT_OF_ARTIFICIAL_SESSION_M5_INDEX_DENIED")
        if self.kind in (ChangeKind.PRICE_VOLUME_REVISION,ChangeKind.LINEAGE_ONLY) and not self.m5_indices:
            raise ValueError("EXPLICIT_CHANGED_M5_REQUIRED_FOR_REVISION")
        if self.kind is ChangeKind.UNCHANGED and self.m5_indices:
            raise ValueError("UNCHANGED_CANNOT_ASSERT_A_CHANGED_CANDLE")
        if type(self.full_policy_binding) is not str or len(self.full_policy_binding)!=64:
            raise ValueError("COMPLETE_POLICY_CHANGE_BINDING_REQUIRED")
        prior,known,now=(_utc(v) for v in (self.prior_as_of_utc,self.first_known_utc,self.as_of_utc))
        if not (prior < known <= now):
            raise ValueError("CAUSAL_FIRST_KNOWN_AFTER_PRIOR_AS_OF_REQUIRED")


def plan_six_tf(grid: FixtureSixTFGrid, event: FixtureSourceChange) -> dict:
    """Preview only. No indicator calculations or physical cache mutations."""
    if type(grid) is not FixtureSixTFGrid or type(event) is not FixtureSourceChange:
        raise TypeError("TYPED_QUALIFIED_FIXTURE_AND_EVENT_REQUIRED")
    if grid.scope.binding != event.full_policy_binding:
        raise PermissionError("CROSS_RIGHTS_OR_POLICY_SCOPE_EVENT_DENIED")
    if event.prior_as_of_utc < grid.artificial_session_end_utc:
        raise PermissionError("CHANGE_EARLIER_THAN_DECLARED_CLOSED_SESSION_DENIED")
    count=grid.count_by_tf
    detail={}
    affected=set(event.m5_indices)
    for tf in TIMEFRAMES:
        ratio=FAKE_MEMBERS_PER_WINDOW[tf]
        n=count[tf]
        if event.kind is ChangeKind.UNQUALIFIED_SOURCE:
            dirty=()
            tail=()
            quarantine=tuple(range(n))
        elif event.kind is ChangeKind.PRICE_VOLUME_REVISION:
            dirty=tuple(i for i in range(n) if any((i*ratio<=x<(i+1)*ratio) for x in affected))
            tail=tuple(range(min(dirty),n)) if dirty else ()
            quarantine=()
        else:
            dirty=tail=quarantine=()
        detail[tf]={
            "fixture_window_total":n,
            "numerical_bar_windows_recompute":list(dirty),
            "causal_indicator_checkpoints_recompute":list(tail),
            "quarantined_window_ordinals":list(quarantine),
            "independent_earlier_indicator_checkpoints_reusable_count":(n-len(tail) if not quarantine else 0),
            "unmodified_aggregated_windows_reusable_count":(n-len(dirty) if not quarantine else 0),
            "official_exchange_tf_finality_verified":False,
        }
    return {
        "schema":SCHEMA,
        "status":STATUS,
        "mode":event.kind.value,
        "full_v1_policy_binding_sha256":grid.scope.binding,
        "bare_v2_partition_hash_not_sufficient":True,
        "explicit_timeframes":list(TIMEFRAMES),
        "artificial_no_break_session_m5_count":FAKE_M5,
        "artificial_day_is_not_official_vn_d1":True,
        "source_m5_modified_indices":list(sorted(affected)),
        "metadata_lineage_changed_indices":(list(sorted(affected)) if event.kind is ChangeKind.LINEAGE_ONLY else []),
        "lineage_audit_update_required":event.kind in (ChangeKind.LINEAGE_ONLY,ChangeKind.PRICE_VOLUME_REVISION),
        "timeframes":detail,
        "numeric_indicators_actually_recomputed":False,
        "provider_published_first_known_verified":False,
        "official_vn_calendar_and_auction_finality_verified":False,
        "authorized_real_higher_tf_source_data":False,
        "real_drive_cache_read_write_performed":False,
        "remote_multiwriter_cas_or_protected_floor_verified":False,
        "production_reuse_or_trading_allowed":False,
    }


def fabricate_grid() -> FixtureSixTFGrid:
    scope=FullPolicyFixture(fixture_scope())
    start=datetime(2020,1,1,0,0,tzinfo=timezone.utc)
    windows=[]
    for tf in TIMEFRAMES:
        ratio=FAKE_MEMBERS_PER_WINDOW[tf]
        for i in range(FAKE_M5//ratio):
            windows.append(FixtureWindow(
                tf,i,tuple(range(i*ratio,(i+1)*ratio)),
                start+i*ratio*BAR,start+(i+1)*ratio*BAR,scope.binding,
            ))
    return FixtureSixTFGrid(scope,start,start+FAKE_M5*BAR,tuple(windows))


def fixture_change(grid: FixtureSixTFGrid,
                   kind: ChangeKind=ChangeKind.PRICE_VOLUME_REVISION,
                   indices: tuple[int,...]=(15,)) -> FixtureSourceChange:
    prior=grid.artificial_session_end_utc
    return FixtureSourceChange(kind,indices,grid.scope.binding,
                               prior,prior+timedelta(minutes=1),prior+timedelta(minutes=2))


def build_receipt():
    grid=fabricate_grid()
    value=plan_six_tf(grid,fixture_change(grid))
    metadata=plan_six_tf(grid,fixture_change(grid,ChangeKind.LINEAGE_ONLY))
    unknown=plan_six_tf(grid,fixture_change(grid,ChangeKind.UNQUALIFIED_SOURCE))
    unchanged=plan_six_tf(grid,fixture_change(grid,ChangeKind.UNCHANGED,()))
    assert {tf:value["timeframes"][tf]["numerical_bar_windows_recompute"] for tf in TIMEFRAMES} == {
        "M5":[15],"M15":[5],"M30":[2],"H1":[1],"H4":[0],"D1":[0]
    }
    assert sum(len(x["causal_indicator_checkpoints_recompute"]) for x in value["timeframes"].values())==132
    assert not any(x["numerical_bar_windows_recompute"] or x["causal_indicator_checkpoints_recompute"] for x in metadata["timeframes"].values())
    assert sum(len(x["quarantined_window_ordinals"]) for x in unknown["timeframes"].values())==155
    assert not any(x["numerical_bar_windows_recompute"] for x in unchanged["timeframes"].values())
    return {
        "schema":SCHEMA,"status":STATUS,
        "six_tf_total_artificial_closed_windows":155,
        "value_revision":value,
        "metadata_revision":metadata,
        "unqualified_provider_change":unknown,
        "unchanged_fixture":unchanged,
        "numeric_indicator_values_not_computed":True,
        "official_session_calendar_not_attested":True,
        "no_real_google_drive_or_vendor_market_calls":True,
        "release_and_trading_no_go":True,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args(argv)
    receipt=build_receipt()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "schema":SCHEMA,"status":STATUS,
        "six_tf_total_artificial_closed_windows":155,
        "price_revision_causal_checkpoints_recompute":
            sum(len(x["causal_indicator_checkpoints_recompute"]) for x in receipt["value_revision"]["timeframes"].values()),
        "unknown_source_quarantined_windows":
            sum(len(x["quarantined_window_ordinals"]) for x in receipt["unqualified_provider_change"]["timeframes"].values()),
        "all_real_data_permissions_false":True,
    },sort_keys=True))


if __name__=="__main__":
    main()
