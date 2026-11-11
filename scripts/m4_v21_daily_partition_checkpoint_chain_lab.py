"""Synthetic P0 per-date V2 partition chain with causal V1 checkpoint carry.

This is a review-only adapter. Each invented day is a *separate* typed V2
candidate partition, linked to a full-policy V1 identity for that SAME date.
No physical V2 cache, authenticated issuer, official market calendar, signed
first-known custody, Google Drive I/O, CAS, trading or release is implemented.
The existing single-date V1->V2 guard is reused, never bypassed.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path

from swing_trading.incremental_cache import (
    FixtureBar, IndicatorCheckpoint, advance_checkpoint, full_recompute,
)
from swing_trading.v2_cache_partition_plan import FixturePartitionV2
from scripts.m2_a02_incremental_cache_oracle_lab import independent_ema_atr_oracle
from scripts.m2_a03_v2_cache_consumer_contract import FixtureV2ConsumerScope
from scripts.m4_v21_gap_v1_numeric_parity_lab import aggregate
from scripts.m4_v21_multiday_all_tf_atr14_oracle_lab import (
    FAKE_DAYS, TIMEFRAMES, EXPECTED_TOTAL, EXPECTED_SUFFIX, KIND_PER_DAY,
    CHANGE_DAY, CHANGE_M5_IN_DAY, META_DAY, META_M5_IN_DAY,
    COLD_AT, CORRECTION_KNOWN, METADATA_KNOWN,
    FakeDay, FakeHistory, multi_key, per_day_groups,
    fabricated_history, materialize_history, changed, changed_group,
)

SCHEMA = "mst.m4.v21.per-session-partition-carry.synthetic.v1"
STATUS = "SINGLE_DATE_V2_SCOPE_CHAIN_SYNTHETIC_ONLY_ALL_LIVE_GATES_NO_GO"


def digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()


def checkpoint_payload(state: IndicatorCheckpoint | None):
    if state is None:
        return None
    if type(state) is not IndicatorCheckpoint:
        raise TypeError("TYPED_V1_INDICATOR_CHECKPOINT_REQUIRED")
    return {
        "start": state.start_utc.isoformat(),
        "ema20": str(state.ema20),
        "atr14": None if state.atr14 is None else str(state.atr14),
        "atr_seen": state.atr_seen,
        "atr_seed_sum": str(state.atr_seed_sum),
        "last_close": str(state.last_close),
    }


def state_digest(state: IndicatorCheckpoint | None) -> str:
    return digest({"checkpoint": checkpoint_payload(state)})


def bar_digest(bars: tuple[FixtureBar, ...]) -> str:
    return digest([b.normalized_digest for b in bars])


def provenance_digest(bars: tuple[FixtureBar, ...]) -> str:
    return digest([
        (b.start_utc.isoformat(), b.normalized_digest, b.revision,
         b.first_known_utc.isoformat()) for b in bars
    ])


def daily_scope(tf: str, day: FakeDay) -> FixtureV2ConsumerScope:
    """Explicitly reconstruct one V1 session identity and one V2 DATE."""
    if tf not in TIMEFRAMES or type(day) is not FakeDay:
        raise TypeError("TYPED_SIX_TF_AND_FABRICATED_DAY_REQUIRED")
    # Artificial morning 09:00 VN; UTC date happens to be the same calendar date.
    declared = day.m5[0].start_utc.date()
    old = replace(multi_key(tf), session_id="SYNTHETIC." + declared.strftime("%Y%m%d"))
    candidate = FixturePartitionV2(
        old.provider.value, old.endpoint_id, "FAKE001", tf,
        declared, old.price_basis, old.adjustment_revision,
    )
    return FixtureV2ConsumerScope(old, candidate, old.instrument_id, "FAKE001")


def daily_bars(day: FakeDay, tf: str) -> tuple[FixtureBar, ...]:
    if type(day) is not FakeDay or tf not in TIMEFRAMES:
        raise TypeError("EXACT_SYNTHETIC_DAY_AND_TIMEFRAME_REQUIRED")
    return tuple(aggregate(g, day.m5) for g in per_day_groups(tf))


def link_digest(link_values: dict) -> str:
    return digest({"schema": SCHEMA, **link_values})


@dataclass(frozen=True)
class DayLink:
    """Unpublished, untrusted in-memory checkpoint link; never a Drive manifest."""
    tf: str
    ordinal: int
    scope: FixtureV2ConsumerScope
    bars: tuple[FixtureBar, ...]
    checkpoints: tuple[IndicatorCheckpoint, ...]
    parent_link_sha256: str | None
    incoming_checkpoint_sha256: str
    outgoing_checkpoint_sha256: str
    normalized_bars_sha256: str
    source_revision_lineage_sha256: str
    self_sha256: str

    def values(self) -> dict:
        return {
            "timeframe": self.tf,
            "day_ordinal": self.ordinal,
            "candidate_partition": self.scope.candidate.digest,
            "full_v1_v2_policy_binding": self.scope.binding_sha256,
            "legacy_daily_identity": self.scope.legacy.fingerprint,
            "parent_link": self.parent_link_sha256,
            "checkpoint_in": self.incoming_checkpoint_sha256,
            "checkpoint_out": self.outgoing_checkpoint_sha256,
            "normalized_bars": self.normalized_bars_sha256,
            "source_revision_lineage": self.source_revision_lineage_sha256,
        }


def make_link(tf: str, day: FakeDay, prior: DayLink | None,
              *, as_of_utc: datetime, old: DayLink | None = None,
              numeric_start_index: int | None = None,
              lineage_only: bool = False) -> tuple[DayLink, int]:
    if type(day) is not FakeDay or tf not in TIMEFRAMES:
        raise TypeError("EXACT_DAY_TF_REQUIRED")
    if type(as_of_utc) is not datetime or as_of_utc.utcoffset() is None or as_of_utc.utcoffset().total_seconds() != 0:
        raise TypeError("EXPLICIT_UTC_ASOF_REQUIRED")
    if prior is None:
        if day.ordinal != 0:
            raise ValueError("MISSING_GENESIS_DAY_LINK")
    elif type(prior) is not DayLink or prior.tf != tf or prior.ordinal + 1 != day.ordinal:
        raise ValueError("WRONG_TF_OR_NONCONSECUTIVE_PREDECESSOR")
    scope = daily_scope(tf, day)
    bars = daily_bars(day, tf)
    if len(bars) != KIND_PER_DAY[tf] or any(
        not b.closed or b.end_utc > as_of_utc or b.first_known_utc > as_of_utc
        for b in bars
    ):
        raise PermissionError("CLOSED_KNOWN_COMPLETE_DAILY_SOURCE_REQUIRED")
    if any(x.start_utc >= y.start_utc for x, y in zip(bars, bars[1:])):
        raise ValueError("DUPLICATE_OR_UNORDERED_DAILY_GROUPS")
    state_in = None if prior is None else prior.checkpoints[-1]
    in_sha = state_digest(state_in)
    if old is not None:
        if (type(old) is not DayLink or old.tf != tf or old.ordinal != day.ordinal
                or old.scope.binding_sha256 != scope.binding_sha256
                or old.scope.candidate.digest != scope.candidate.digest):
            raise PermissionError("CROSS_DATE_SOURCE_OR_FULL_POLICY_REUSE_DENIED")
    if lineage_only:
        if old is None or numeric_start_index is not None:
            raise ValueError("LINEAGE_RELINK_NEEDS_OLD_LINK_AND_NO_NUMERIC_REPLAY")
        if (old.incoming_checkpoint_sha256 != in_sha
                or tuple(x.normalized_digest for x in old.bars)
                   != tuple(x.normalized_digest for x in bars)):
            raise PermissionError("NUMERIC_OR_CARRY_DRIFT_CANNOT_USE_LINEAGE_ONLY")
        checkpoints = old.checkpoints
        computed = 0
    elif numeric_start_index is not None:
        if old is None or type(numeric_start_index) is not int or not 0 <= numeric_start_index < len(bars):
            raise ValueError("TYPED_BOUNDED_CAUSAL_REPLAY_OFFSET_REQUIRED")
        if (old.incoming_checkpoint_sha256 != in_sha
                or tuple(x.normalized_digest for x in old.bars[:numeric_start_index])
                   != tuple(x.normalized_digest for x in bars[:numeric_start_index])):
            raise PermissionError("UNPROVEN_CAUSAL_PREFIX_OR_CARRY_REUSE")
        checkpoints = list(old.checkpoints[:numeric_start_index])
        state = checkpoints[-1] if checkpoints else state_in
        for bar in bars[numeric_start_index:]:
            state = advance_checkpoint(bar, state)
            checkpoints.append(state)
        checkpoints = tuple(checkpoints)
        computed = len(bars) - numeric_start_index
    else:
        checkpoints_list = []
        state = state_in
        for bar in bars:
            state = advance_checkpoint(bar, state)
            checkpoints_list.append(state)
        checkpoints = tuple(checkpoints_list)
        computed = len(bars)
    if len(checkpoints) != len(bars) or any(
        cp.start_utc != b.start_utc for cp, b in zip(checkpoints, bars)
    ):
        raise AssertionError("INCOMPLETE_DAY_CHECKPOINTS")
    record = DayLink(
        tf, day.ordinal, scope, bars, checkpoints,
        None if prior is None else prior.self_sha256,
        in_sha, state_digest(checkpoints[-1]), bar_digest(bars),
        provenance_digest(bars), "",
    )
    record = replace(record, self_sha256=link_digest(record.values()))
    return record, computed


def build_chain(history: FakeHistory, tf: str, *, as_of_utc: datetime,
                previous: tuple[DayLink, ...] | None = None,
                dirty_day: int = 0,
                kind: str = "COLD",
                dirty_group_index: int | None = None) -> tuple[tuple[DayLink, ...], int]:
    if type(history) is not FakeHistory or tf not in TIMEFRAMES:
        raise TypeError("EXACT_SYNTHETIC_HISTORY_TF_REQUIRED")
    if kind not in ("COLD", "PRICE", "METADATA"):
        raise ValueError("EXPLICIT_REPLAY_EVENT_REQUIRED")
    if kind == "COLD":
        if previous is not None or dirty_day != 0 or dirty_group_index is not None:
            raise ValueError("COLD_CHAIN_MUST_START_AT_GENESIS")
        prefix: tuple[DayLink, ...] = ()
    else:
        if (type(previous) is not tuple or len(previous) != FAKE_DAYS
                or type(dirty_day) is not int or not 0 <= dirty_day < FAKE_DAYS):
            raise ValueError("COMPLETE_PRIOR_CHAIN_AND_DIRTY_DAY_REQUIRED")
        verify_chain(history=None, tf=tf, chain=previous, as_of_utc=as_of_utc,
                     content_only=False)  # verify structure, not new history
        prefix = previous[:dirty_day]
    result = list(prefix)
    computed = 0
    for day in history.days[len(prefix):]:
        prior = result[-1] if result else None
        old = None if previous is None else previous[day.ordinal]
        if kind == "METADATA":
            link, count = make_link(tf, day, prior, as_of_utc=as_of_utc,
                                    old=old, lineage_only=True)
        elif kind == "PRICE" and day.ordinal == dirty_day:
            link, count = make_link(tf, day, prior, as_of_utc=as_of_utc,
                                    old=old, numeric_start_index=dirty_group_index)
        else:
            link, count = make_link(tf, day, prior, as_of_utc=as_of_utc)
        result.append(link)
        computed += count
    chain = tuple(result)
    verify_chain(history, tf, chain, as_of_utc=as_of_utc)
    return chain, computed


def verify_chain(history: FakeHistory | None, tf: str, chain: tuple[DayLink, ...],
                 *, as_of_utc: datetime, content_only: bool = True) -> None:
    """Independent structural + source + mathematical validation of every link."""
    if tf not in TIMEFRAMES or type(chain) is not tuple or len(chain) != FAKE_DAYS:
        raise ValueError("COMPLETE_TYPED_SIXTEEN_DAY_LINK_CHAIN_REQUIRED")
    if history is not None and type(history) is not FakeHistory:
        raise TypeError("SYNTHETIC_HISTORY_OR_NONE_REQUIRED")
    prior = None
    for index, item in enumerate(chain):
        if type(item) is not DayLink or item.tf != tf or item.ordinal != index:
            raise ValueError("CROSS_TF_OR_NONCONSECUTIVE_LINK")
        if item.scope.legacy.session_id != "SYNTHETIC." + item.scope.candidate.session_date_local.strftime("%Y%m%d"):
            raise PermissionError("SINGLE_DAY_V1_V2_SCOPE_REQUIRED")
        if item.parent_link_sha256 != (None if prior is None else prior.self_sha256):
            raise PermissionError("PARENT_LINK_MISMATCH_OR_REWIND")
        if item.incoming_checkpoint_sha256 != state_digest(None if prior is None else prior.checkpoints[-1]):
            raise PermissionError("INCOMING_CARRY_HASH_OR_POLICY_DRIFT")
        if history is not None and item.scope.binding_sha256 != daily_scope(
            tf, history.days[index]
        ).binding_sha256:
            # No real provenance can be derived from a caller claiming V2 rights.
            raise PermissionError("FULL_LEGACY_POLICY_SCOPE_DRIFT")
        if (item.normalized_bars_sha256 != bar_digest(item.bars)
                or item.source_revision_lineage_sha256 != provenance_digest(item.bars)
                or item.outgoing_checkpoint_sha256 != state_digest(item.checkpoints[-1])
                or item.self_sha256 != link_digest(item.values())):
            raise PermissionError("CONTENT_LINEAGE_OR_CHECKPOINT_LINK_TAMPER")
        if history is not None:
            expected = daily_bars(history.days[index], tf)
            if item.bars != expected:
                raise PermissionError("WRONG_DATE_SOURCE_CONTENT_OR_REVISION")
        if content_only and (
            any(b.first_known_utc > as_of_utc or b.end_utc > as_of_utc or not b.closed for b in item.bars)
        ):
            raise PermissionError("FUTURE_FIRST_KNOWN_OR_OPEN_REPLAY_DENIED")
        # Critical: do not equate link hashes with numeric correctness.
        state = None if prior is None else prior.checkpoints[-1]
        expected_cp = []
        for b in item.bars:
            state = advance_checkpoint(b, state)
            expected_cp.append(state)
        if item.checkpoints != tuple(expected_cp):
            raise ValueError("NONCAUSAL_OR_TAMPERED_INDICATOR_CARRY")
        prior = item


def run_lab() -> dict:
    original = fabricated_history()
    corrected = changed(original, "PRICE", CHANGE_DAY, CHANGE_M5_IN_DAY)
    revised = changed(corrected, "METADATA", META_DAY, META_M5_IN_DAY)
    per_tf = {}
    total_price = total_meta = 0
    for tf in TIMEFRAMES:
        initial, cold_count = build_chain(original, tf, as_of_utc=COLD_AT)
        dirty = changed_group(tf, CHANGE_DAY, CHANGE_M5_IN_DAY) - CHANGE_DAY * KIND_PER_DAY[tf]
        altered, price_count = build_chain(
            corrected, tf, as_of_utc=CORRECTION_KNOWN,
            previous=initial, dirty_day=CHANGE_DAY, kind="PRICE", dirty_group_index=dirty,
        )
        lineage, meta_count = build_chain(
            revised, tf, as_of_utc=METADATA_KNOWN,
            previous=altered, dirty_day=META_DAY, kind="METADATA",
        )
        final = tuple(cp for link in lineage for cp in link.checkpoints)
        oracle = independent_ema_atr_oracle(materialize_history(revised, tf))
        if (final != full_recompute(materialize_history(revised, tf))
                or final != oracle or price_count != EXPECTED_SUFFIX[tf]
                or cold_count != EXPECTED_TOTAL[tf] or meta_count != 0
                or initial[:CHANGE_DAY] != altered[:CHANGE_DAY]
                or altered[:META_DAY] != lineage[:META_DAY]):
            raise AssertionError("PER_DATE_CARRY_NOT_EQUAL_INHERITED_V1_OR_DECIMAL_ORACLE_" + tf)
        if altered[CHANGE_DAY].self_sha256 == initial[CHANGE_DAY].self_sha256:
            raise AssertionError("PRICE_RELINK_DID_NOT_CHANGE_AFFECTED_DATE")
        if lineage[META_DAY].source_revision_lineage_sha256 == altered[META_DAY].source_revision_lineage_sha256:
            raise AssertionError("METADATA_EVENT_NOT_AUDITED")
        if lineage[META_DAY].normalized_bars_sha256 != altered[META_DAY].normalized_bars_sha256:
            raise AssertionError("METADATA_EVENT_MUST_NOT_CHANGE_NUMERIC_BAR_CONTENT")
        if lineage[META_DAY+1].parent_link_sha256 == altered[META_DAY+1].parent_link_sha256:
            raise AssertionError("LINEAGE_CHAIN_NOT_RELINKED_FORWARD")
        total_price += price_count
        total_meta += meta_count
        per_tf[tf] = {
            "partitions": len(lineage),
            "cold_checkpoints_computed": cold_count,
            "price_revision_checkpoints_recomputed": price_count,
            "metadata_only_checkpoints_recomputed": meta_count,
            "first_atr14_index": 13,
            "cross_session_indicator_carry_equal_original_v1_and_decimal_oracle": True,
            "single_date_typed_scope_bound_each_day": True,
            "lineage_only_relinks_audit_digest_without_numeric_changes": True,
        }
    if total_price != 204 or total_meta != 0:
        raise AssertionError("SIX_TF_CAUSAL_CARRY_COUNT_DRIFT")
    return {
        "schema": SCHEMA, "status": STATUS,
        "fake_days": FAKE_DAYS,
        "candidate_single_date_partition_links": FAKE_DAYS * len(TIMEFRAMES),
        "timeframes": list(TIMEFRAMES),
        "total_cold_checkpoints": sum(EXPECTED_TOTAL.values()),
        "actual_price_replayed_checkpoint_positions": total_price,
        "metadata_only_replayed_checkpoint_positions": total_meta,
        "per_tf": per_tf,
        "cross_date_carry_numerically_equal_original_v1": True,
        "full_policy_and_source_revision_linked": True,
        "one_day_v1_v2_guard_unmodified": True,
        "multi_day_composite_v2_scope_allowed": False,
        "official_exchange_calendar_authenticated": False,
        "provider_issued_first_known_revision_authenticated": False,
        "market_data_or_cloud_retention_licensed": False,
        "physical_google_drive_market_cache_read_write": False,
        "protected_external_monotonic_floor_or_two_writer_cas": False,
        "production_release_or_trading_authorized": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    result = run_lab()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8")
    print(json.dumps({
        "status": STATUS,
        "single_date_links": result["candidate_single_date_partition_links"],
        "cross_session_ema_atr_numeric_oracle": True,
        "price_recomputed": result["actual_price_replayed_checkpoint_positions"],
        "metadata_numeric_recomputed": result["metadata_only_replayed_checkpoint_positions"],
        "real_market_cache_or_trade": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
