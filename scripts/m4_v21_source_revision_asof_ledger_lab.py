"""MST M3/M4 P0: bitemporal revision custody for wholly synthetic M5 source.

An append-only fixture observation ledger distinguishes bar valid time from
first-known/observed time, supports historical-as-of views, metadata-only
revisions, price corrections and tombstones. Its SHA links are local evidence,
NOT issuer signatures, trusted chronology, real market rights or Drive custody.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path

from swing_trading.incremental_cache import FixtureBar, full_recompute
from scripts.m2_a02_incremental_cache_oracle_lab import independent_ema_atr_oracle
from scripts.m2_a03_v2_cache_consumer_contract import FixtureV2ConsumerScope
from scripts.m4_v21_daily_partition_checkpoint_chain_lab import daily_scope
from scripts.m4_v21_gap_v1_numeric_parity_lab import SOURCE_COUNT, start_for
from scripts.m4_v21_multiday_all_tf_atr14_oracle_lab import (
    FakeDay, FakeHistory, fabricated_history, changed, materialize_history,
    FAKE_DAYS, TIMEFRAMES, CHANGE_DAY, CHANGE_M5_IN_DAY,
    META_DAY, META_M5_IN_DAY, COLD_AT, CORRECTION_KNOWN, METADATA_KNOWN,
)

SCHEMA = "mst.m3.v21.synthetic-first-known-asof-ledger.v1"
STATUS = "SOURCE_REVISION_ASOF_CUSTODY_FIXTURE_ONLY_ALL_LIVE_GATES_NO_GO"
EVENT_KINDS = frozenset(("INITIAL", "PRICE", "METADATA", "TOMBSTONE"))
GENESIS = "0" * 64
FIVE = timedelta(minutes=5)


def utc(value: datetime) -> datetime:
    if type(value) is not datetime or value.utcoffset() is None or value.utcoffset().total_seconds() != 0:
        raise TypeError("EXPLICIT_ZERO_OFFSET_UTC_REQUIRED")
    return value


def digest(obj: object) -> str:
    return sha256(json.dumps(obj, ensure_ascii=True, allow_nan=False,
                             separators=(",", ":"), sort_keys=True).encode("ascii")).hexdigest()


def canonical_bar(b: FixtureBar | None) -> dict | None:
    if b is None:
        return None
    if type(b) is not FixtureBar:
        raise TypeError("TYPED_CLOSED_FIXTURE_BAR_ONLY")
    return {
        "from": b.start_utc.isoformat(), "to": b.end_utc.isoformat(),
        "value_sha256": b.normalized_digest, "revision": b.revision,
        "first_known": b.first_known_utc.isoformat(), "closed": b.closed,
    }


@dataclass(frozen=True)
class ToySourceObservation:
    scope: FixtureV2ConsumerScope
    day_ordinal: int
    m5_ordinal: int
    generation: int
    event_kind: str
    first_known_utc: datetime
    revision: str
    bar: FixtureBar | None
    official_calendar_attested: bool = False
    vendor_license_attested: bool = False
    issuer_signature_verified: bool = False

    def __post_init__(self):
        if type(self.day_ordinal) is not int or not 0 <= self.day_ordinal < FAKE_DAYS:
            raise ValueError("EXPLICIT_FABRICATED_DAY_REQUIRED")
        if type(self.m5_ordinal) is not int or not 0 <= self.m5_ordinal < SOURCE_COUNT:
            raise ValueError("DECLARED_CONTINUOUS_M5_SLOT_REQUIRED")
        if type(self.generation) is not int or self.generation < 1:
            raise ValueError("POSITIVE_PER_SLOT_GENERATION_REQUIRED")
        if self.event_kind not in EVENT_KINDS:
            raise ValueError("EXPLICIT_SOURCE_REVISION_EVENT_REQUIRED")
        utc(self.first_known_utc)
        if type(self.scope) is not FixtureV2ConsumerScope or self.scope.candidate.timeframe != "M5":
            raise TypeError("EXACT_M5_DAILY_TYPED_V1_V2_SCOPE_REQUIRED")
        if any((self.official_calendar_attested, self.vendor_license_attested,
                self.issuer_signature_verified)):
            raise PermissionError("CALLER_CANNOT_SELF_ATTEST_REAL_ISSUER_OR_RIGHTS")
        if type(self.revision) is not str or not self.revision.startswith("r") or not self.revision[1:].isdigit():
            raise ValueError("EXPLICIT_TOY_REVISION_LABEL_REQUIRED")
        expected = start_for(self.m5_ordinal) + timedelta(days=self.day_ordinal)
        if self.scope.legacy.session_id != "SYNTHETIC." + expected.strftime("%Y%m%d"):
            raise PermissionError("TOY_CALENDAR_DATE_NOT_MATCHING_ONE_DATE_POLICY")
        if self.scope.candidate.session_date_local != expected.date():
            raise PermissionError("V2_DAY_PARTITION_DATE_DRIFT")
        if self.event_kind == "TOMBSTONE":
            if self.bar is not None or self.first_known_utc < expected + FIVE:
                raise PermissionError("TOMBSTONE_MUST_HAVE_NO_BAR_AFTER_SLOT_CLOSE")
        else:
            if type(self.bar) is not FixtureBar:
                raise TypeError("EXACT_TYPED_BAR_FOR_SOURCE_REVISION_REQUIRED")
            if (self.bar.start_utc != expected or self.bar.end_utc != expected + FIVE
                    or not self.bar.closed or self.bar.first_known_utc != self.first_known_utc
                    or self.bar.revision != self.revision
                    or self.first_known_utc < self.bar.end_utc):
                raise PermissionError("M5_WINDOW_CLOSE_FIRST_KNOWN_OR_REVISION_DRIFT")


@dataclass(frozen=True)
class LinkedToyObservation:
    observation: ToySourceObservation
    previous_sha256: str
    sha256: str


def event_payload(obs: ToySourceObservation) -> dict:
    return {
        "schema": SCHEMA, "day": obs.day_ordinal, "ordinal": obs.m5_ordinal,
        "generation": obs.generation, "event": obs.event_kind,
        "revision": obs.revision, "first_known": obs.first_known_utc.isoformat(),
        "candidate_partition_sha256": obs.scope.candidate.digest,
        "full_v1_policy_binding_sha256": obs.scope.binding_sha256,
        "value": canonical_bar(obs.bar),
        "claimed_official_calendar": obs.official_calendar_attested,
        "claimed_vendor_license": obs.vendor_license_attested,
        "claimed_issuer_signature": obs.issuer_signature_verified,
    }


class ToyAsOfLedger:
    """In-memory untrusted SHA chain, not tamper-proof archival storage."""

    def __init__(self, history: FakeHistory):
        if type(history) is not FakeHistory:
            raise TypeError("EXACT_FAKE_HISTORY_REQUIRED")
        self.history = history
        self._links: list[LinkedToyObservation] = []
        self._latest: dict[tuple[int, int], ToySourceObservation] = {}
        self._history: dict[tuple[int, int], list[ToySourceObservation]] = {}

    @property
    def links(self) -> tuple[LinkedToyObservation, ...]:
        return tuple(self._links)

    def append(self, obs: ToySourceObservation) -> LinkedToyObservation:
        if type(obs) is not ToySourceObservation:
            raise TypeError("TYPED_TOY_EVENT_REQUIRED")
        expected = daily_scope("M5", self.history.days[obs.day_ordinal])
        if (obs.scope.binding_sha256 != expected.binding_sha256
                or obs.scope.candidate.digest != expected.candidate.digest):
            raise PermissionError("CROSS_SOURCE_RIGHTS_CALENDAR_OR_PROVIDER_SCOPE_DENIED")
        slot = (obs.day_ordinal, obs.m5_ordinal)
        prev = self._latest.get(slot)
        if self._links and obs.first_known_utc < self._links[-1].observation.first_known_utc:
            raise PermissionError("APPEND_ONLY_FIRST_KNOWN_LEDGER_CLOCK_REWIND")
        if prev is None:
            if obs.generation != 1 or obs.event_kind != "INITIAL":
                raise ValueError("FIRST_SEEN_SLOT_MUST_BE_INITIAL_GENERATION_ONE")
        else:
            if obs.generation != prev.generation + 1:
                raise ValueError("SOURCE_SEQUENCE_REPLAY_OR_GAP_DENIED")
            if obs.first_known_utc <= prev.first_known_utc:
                raise PermissionError("SOURCE_REVISION_FIRST_KNOWN_MUST_ADVANCE")
            if obs.revision == prev.revision:
                raise ValueError("SOURCE_REVISION_ID_MUST_ADVANCE")
            if prev.bar is None and obs.event_kind != "PRICE":
                raise ValueError("TOMBSTONE_REINTRODUCTION_REQUIRES_EXPLICIT_PRICE_EVENT")
            if obs.event_kind == "INITIAL":
                raise ValueError("EXISTING_SOURCE_SLOT_CANNOT_BE_INITIAL_AGAIN")
            if obs.event_kind == "METADATA" and (
                prev.bar is None or obs.bar is None
                or prev.bar.normalized_digest != obs.bar.normalized_digest
            ):
                raise PermissionError("METADATA_REVISION_CANNOT_CHANGE_NUMERIC_OHLCV")
            if obs.event_kind == "PRICE" and (obs.bar is None or
                (prev.bar is not None and prev.bar.normalized_digest == obs.bar.normalized_digest)):
                raise PermissionError("PRICE_REVISION_MUST_CHANGE_NUMERIC_OHLCV")
        prior_hash = self._links[-1].sha256 if self._links else GENESIS
        sha = digest({"prior": prior_hash, "event": event_payload(obs)})
        link = LinkedToyObservation(obs, prior_hash, sha)
        # Mutate only after all constraints pass.
        self._links.append(link)
        self._latest[slot] = obs
        self._history.setdefault(slot, []).append(obs)
        return link

    def verify(self) -> None:
        prior = GENESIS
        for link in self._links:
            if (link.previous_sha256 != prior or link.sha256 !=
                    digest({"prior": prior, "event": event_payload(link.observation)})):
                raise PermissionError("UNTRUSTED_LOCAL_SHA_CHAIN_CORRUPTED")
            prior = link.sha256
        # Hash continuity cannot establish real issuer, protected floor or rights.

    def snapshot(self, *, as_of_utc: datetime, require_complete: bool = True) -> FakeHistory | dict:
        clock = utc(as_of_utc)
        rows = {}
        for key, versions in self._history.items():
            selected = next((v for v in reversed(versions) if v.first_known_utc <= clock), None)
            if selected is not None and selected.bar is not None:
                rows[key] = selected.bar
        if not require_complete:
            return rows
        if len(rows) != SOURCE_COUNT * FAKE_DAYS:
            raise PermissionError("MISSING_UNKNOWN_OR_RETRACTED_ASOF_SOURCE_BAR")
        days = tuple(FakeDay(day, tuple(rows[(day, i)] for i in range(SOURCE_COUNT)))
                     for day in range(FAKE_DAYS))
        return FakeHistory(days)

    def source_proof(self) -> dict:
        self.verify()
        return {
            "local_sha_chain_only": self._links[-1].sha256 if self._links else GENESIS,
            "total_untrusted_events": len(self._links),
            "issuer_signature_authenticated": False,
            "official_market_calendar_attested": False,
            "authorized_real_source_retention": False,
            "independent_protected_rollback_floor": False,
            "external_concurrent_writer_cas": False,
            "read_write_real_google_drive_quotes": False,
            "production_or_trading_permitted": False,
        }


def fabricate_ledger() -> tuple[ToyAsOfLedger, FakeHistory, FakeHistory, FakeHistory]:
    original = fabricated_history()
    after_price = changed(original, "PRICE", CHANGE_DAY, CHANGE_M5_IN_DAY)
    after_meta = changed(after_price, "METADATA", META_DAY, META_M5_IN_DAY)
    ledger = ToyAsOfLedger(original)
    for day in original.days:
        scope = daily_scope("M5", day)
        for idx, bar in enumerate(day.m5):
            ledger.append(ToySourceObservation(
                scope, day.ordinal, idx, 1, "INITIAL", bar.first_known_utc,
                bar.revision, bar))
    p = after_price.days[CHANGE_DAY].m5[CHANGE_M5_IN_DAY]
    ledger.append(ToySourceObservation(
        daily_scope("M5", original.days[CHANGE_DAY]), CHANGE_DAY,
        CHANGE_M5_IN_DAY, 2, "PRICE", p.first_known_utc, p.revision, p))
    m = after_meta.days[META_DAY].m5[META_M5_IN_DAY]
    ledger.append(ToySourceObservation(
        daily_scope("M5", original.days[META_DAY]), META_DAY,
        META_M5_IN_DAY, 2, "METADATA", m.first_known_utc, m.revision, m))
    return ledger, original, after_price, after_meta


def run_lab() -> dict:
    ledger, original, after_price, after_meta = fabricate_ledger()
    cold = ledger.snapshot(as_of_utc=COLD_AT)
    price = ledger.snapshot(as_of_utc=CORRECTION_KNOWN)
    meta = ledger.snapshot(as_of_utc=METADATA_KNOWN)
    if (cold != original or price != after_price or meta != after_meta):
        raise AssertionError("ASOF_VIEW_CROSS_TIME_REVISION_LEAKAGE")
    by_tf = {}
    for tf in TIMEFRAMES:
        before = materialize_history(cold, tf)
        revised = materialize_history(price, tf)
        final = materialize_history(meta, tf)
        cp_before = full_recompute(before)
        cp_after = full_recompute(revised)
        cp_meta = full_recompute(final)
        if (cp_before != independent_ema_atr_oracle(before)
                or cp_after != independent_ema_atr_oracle(revised)
                or cp_meta != cp_after):
            raise AssertionError("ASOF_REVISIONS_DISAGREE_WITH_INHERITED_V1_" + tf)
        by_tf[tf] = {
            "fixture_windows": len(before),
            "asof_before_price_has_original_values": True,
            "asof_after_price_matches_independent_v1_numeric_oracle": True,
            "metadata_only_keeps_same_indicators": True,
        }
    out = {
        "schema": SCHEMA, "status": STATUS,
        "two_valid_time_vs_first_known_dimensions_checked": True,
        "untrusted_ledger_events": len(ledger.links),
        "declared_synthetic_m5_source_rows": FAKE_DAYS * SOURCE_COUNT,
        "revision_history_asof_snapshots": 3,
        "value_revision_invisible_before_known": True,
        "metadata_only_zero_numeric_recompute": True,
        "six_tf_asof_numeric_oracle_verified": True,
        "per_tf": by_tf,
        "source_proof": ledger.source_proof(),
    }
    if len(ledger.links) != 770 or len(by_tf) != 6:
        raise AssertionError("EXPECTED_FAKE_SOURCE_VERSION_COUNT_DRIFT")
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    report = run_lab()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    print(json.dumps({
        "status": STATUS, "source_events": report["untrusted_ledger_events"],
        "six_tf_asof_oracle": True, "real_source_or_storage_approved": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
