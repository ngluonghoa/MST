"""§204 Cloud-only SIX timeframe Cache→Signal readiness, unpublished only.

This is a bounded consistency/coverage view over CALLER-supplied immutable
CanonicalCandle candidates, not actual licensed SSI/DNSE/VCBS ingestion or
a backtest/qualified 16-zone strategy. H4 is DERIVED-ONLY after separately
reviewed venue-session/calendar closure and will NEVER be inferred as
a native SSI/DNSE feed. All market qualification and Signal/UI/trade gates
stay false even if every synthetic CanonicalCandle passes local checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Any

from .market_data import CanonicalCandle, PriceBasis, Timeframe
from .replay import require_utc
from .source_quality import LifecycleState, ResolvedBarSnapshotV12

TF_ORDER = (Timeframe.M5, Timeframe.M15, Timeframe.M30,
            Timeframe.H1, Timeframe.H4, Timeframe.D1)
TF_NAMES = tuple(x.value for x in TF_ORDER)
ID = re.compile(r"STOCK:(HOSE|HNX|UPCOM):[A-Z0-9]{3,15}:[A-Za-z0-9_-]{3,80}\Z")
EXCHANGE = re.compile(r"(HOSE|HNX|UPCOM)\Z")
MAX_BARS_PER_TF = 512


class PrivateMultiTfDenied(ValueError):
    """Fixed errors, never return source prices/secret/row identity."""


@dataclass(frozen=True)
class PrivateMultiTfReadiness:
    summary: dict[str, Any]
    reference_sha256: str
    qualified_for_signals: bool = False
    qualified_for_backtest: bool = False
    eligible_for_trades: bool = False

    def __post_init__(self) -> None:
        if (type(self.summary) is not dict
                or self.summary.get("schema") != "mst.private.six_tf_readiness.v0.1"
                or self.summary.get("pipeline_state") != "UNVERIFIED"
                or self.summary.get("source_released") is not False
                or self.summary.get("signal_engine_parity_verified") is not False
                or self.summary.get("ui_step08_approved") is not False
                or self.summary.get("trades_eligible") is not False
                or self.qualified_for_signals is not False
                or self.qualified_for_backtest is not False
                or self.eligible_for_trades is not False):
            raise PrivateMultiTfDenied("MST_SIX_TF_RELEASE_CLAIM_FORBIDDEN")
        rows = self.summary.get("timeframes")
        if (type(rows) is not list or len(rows) != 6
                or [r.get("timeframe") for r in rows if type(r) is dict]
                   != list(TF_NAMES)
                or any(type(r) is not dict
                       or r.get("verified_for_signals") is not False
                       or r.get("source_finality_attested") is not False
                       or r.get("price_basis_officially_attested") is not False
                       or r.get("status") not in (
                           "MISSING", "CANDIDATE_ONLY_UNVERIFIED")
                       or type(r.get("observed_candles")) is not int
                       or not 0 <= r["observed_candles"] <= MAX_BARS_PER_TF
                       or type(r.get("local_necessary_checks_count")) is not int
                       or not 0 <= r["local_necessary_checks_count"] <= r["observed_candles"]
                       or (r["status"] == "MISSING") != (r["observed_candles"] == 0)
                       for r in rows)):
            raise PrivateMultiTfDenied("MST_SIX_TF_STRUCTURE_INVALID")
        if (self.summary.get("h4_native_provider_supported") is not False
                or self.summary.get("w1_context_verified") is not False
                or self.summary.get("highwater_independent_cas_verified") is not False
                or self.summary.get("venue_calendar_verified") is not False):
            raise PrivateMultiTfDenied("MST_SIX_TF_FABRICATED_H4_OR_W1")
        try:
            raw = json.dumps(
                self.summary, sort_keys=True, separators=(",", ":"),
                allow_nan=False, ensure_ascii=True,
            ).encode()
        except (ValueError, TypeError, OverflowError):
            raise PrivateMultiTfDenied("MST_SIX_TF_SUMMARY_JSON_INVALID") from None
        if sha256(raw).hexdigest() != self.reference_sha256:
            raise PrivateMultiTfDenied("MST_SIX_TF_SUMMARY_DIGEST_CHANGED")


def inspect_six_tf_candidate_coverage(
    candles_by_tf: Any, *, instrument_id: str, exchange: str,
    as_of_utc: datetime,
) -> PrivateMultiTfReadiness:
    """Inspect a homogeneous source partition and 6 explicit TF buckets.

    Even VERIFIED+CLOSED synthetic CanonicalCandle inputs only prove
    *necessary local checks*, not venue/provider attestation or eligibility.
    Missing TF is not "NO SIGNAL", nor may source corrections be erased.
    """
    require_utc(as_of_utc)
    if (type(instrument_id) is not str
            or ID.fullmatch(instrument_id) is None
            or instrument_id.split(":")[1] != exchange
            or type(exchange) is not str
            or EXCHANGE.fullmatch(exchange) is None
            or type(candles_by_tf) is not dict
            or set(candles_by_tf) != set(TF_ORDER)):
        raise PrivateMultiTfDenied("MST_SIX_TF_INPUT_SCOPE_INVALID")
    rows = []
    provider_seen: str | None = None
    basis_seen: PriceBasis | None = None
    for timeframe in TF_ORDER:
        candles = candles_by_tf[timeframe]
        if (type(candles) not in (list, tuple)
                or len(candles) > MAX_BARS_PER_TF):
            raise PrivateMultiTfDenied("MST_SIX_TF_COUNT_OR_TYPE_INVALID")
        previous = None
        local_provider: str | None = None
        local_basis: PriceBasis | None = None
        necessary = 0
        for candle in candles:
            if type(candle) is not CanonicalCandle:
                raise PrivateMultiTfDenied("MST_SIX_TF_NON_CANONICAL_CANDLE")
            key = candle.market_bar_key
            if (key.timeframe is not timeframe
                    or key.instrument_id != instrument_id
                    or key.exchange != exchange
                    or key.instrument_class.value != "STOCK"
                    or candle.revision.first_known_time_utc > as_of_utc
                    or candle.revision.retrieved_at_utc > as_of_utc
                    or candle.bar_end_utc > as_of_utc
                    or key.bar_start_utc > as_of_utc):
                raise PrivateMultiTfDenied("MST_SIX_TF_LOOKAHEAD_OR_IDENTITY")
            if previous is not None and key.bar_start_utc <= previous:
                raise PrivateMultiTfDenied("MST_SIX_TF_DUPLICATE_OR_REORDERED")
            previous = key.bar_start_utc
            p = candle.observation_key.provider_id
            basis = key.price_basis
            if (type(p) is not str or not p
                    or local_provider is not None and p != local_provider
                    or local_basis is not None and basis is not local_basis
                    or provider_seen is not None and provider_seen != p
                    or basis_seen is not None and basis is not basis_seen):
                raise PrivateMultiTfDenied("MST_SIX_TF_MIXED_PROVIDER_OR_BASIS")
            provider_seen = local_provider = p
            basis_seen = local_basis = basis
            necessary += int(candle.eligible_for_confirmed_signals(as_of_utc))
        rows.append({
            "timeframe": timeframe.value,
            "observed_candles": len(candles),
            "local_necessary_checks_count": necessary,
            "status": ("CANDIDATE_ONLY_UNVERIFIED" if candles else "MISSING"),
            "source_finality_attested": False,
            "price_basis_officially_attested": False,
            "verified_for_signals": False,
            "derived_h4_venue_policy_proven": False if timeframe is Timeframe.H4 else None,
        })
    report = {
        "schema": "mst.private.six_tf_readiness.v0.1",
        "instrument_id": instrument_id, "exchange": exchange,
        "source_provider": provider_seen,
        "as_of_utc": as_of_utc.isoformat(),
        "timeframes": rows,
        "required_timeframes": list(TF_NAMES),
        "candidate_timeframes_present": sum(
            row["observed_candles"] > 0 for row in rows
        ),
        "h4_native_provider_supported": False,
        "w1_context_verified": False,
        "venue_calendar_verified": False,
        "source_released": False,
        "highwater_independent_cas_verified": False,
        "signal_engine_parity_verified": False,
        "ui_step08_approved": False,
        "pipeline_state": "UNVERIFIED",
        "trades_eligible": False,
    }
    wire = json.dumps(report, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode()
    return PrivateMultiTfReadiness(report, sha256(wire).hexdigest())


# Owner-approved original analysis scope, separate from §204 engineering inventory.
BASELINE_CORE_TF = (Timeframe.W1, Timeframe.D1, Timeframe.H1,
                    Timeframe.M30, Timeframe.M15)


def _baseline_key_check(key, *, tf, instrument, exchange, cutoff):
    if (key.timeframe is not tf or key.instrument_id != instrument
            or key.exchange != exchange or key.instrument_class.value != "STOCK"
            or key.bar_start_utc > cutoff):
        raise PrivateMultiTfDenied("MST_368_KEY_IDENTITY_OR_LOOKAHEAD")


def _baseline_selected_scope(row, cutoff):
    rev = row.observation_revision
    if (rev.first_known_time_utc > cutoff or row.retrieved_at_utc > cutoff
            or row.verified_at_utc is not None and row.verified_at_utc > cutoff
            or row.lifecycle_state is LifecycleState.CLOSED and row.bar_end_utc > cutoff):
        raise PrivateMultiTfDenied("MST_368_SELECTED_REVISION_LOOKAHEAD")
    obs = row.observation_key
    return (obs.project_id, obs.provider_id, rev.adjustment_revision)


def _baseline_bucket(tf, snapshots, *, instrument, exchange, cutoff):
    if type(snapshots) is not tuple or len(snapshots) > MAX_BARS_PER_TF:
        raise PrivateMultiTfDenied("MST_368_IMMUTABLE_BOUNDED_BUCKET")
    previous_start = previous_end = common_key = selected_scope = stream = None
    for snap in snapshots:
        if type(snap) is not ResolvedBarSnapshotV12:
            raise PrivateMultiTfDenied("MST_368_REQUIRE_RESOLVED_V12")
        key = snap.market_bar_key
        _baseline_key_check(key, tf=tf, instrument=instrument, exchange=exchange, cutoff=cutoff)
        if (previous_start is not None and key.bar_start_utc <= previous_start
                or previous_end is not None and key.bar_start_utc < previous_end):
            raise PrivateMultiTfDenied("MST_368_DUPLICATE_OVERLAP_OR_ORDER")
        previous_start = key.bar_start_utc
        this_key = (key.price_basis, key.calendar_version, key.aggregation_policy_version)
        if common_key is not None and this_key != common_key:
            raise PrivateMultiTfDenied("MST_368_MIXED_BUCKET_KEY_POLICY")
        common_key = this_key
        row = snap.selected
        if row is None:
            continue
        previous_end = row.bar_end_utc
        this_scope = _baseline_selected_scope(row, cutoff)
        this_stream = (row.observation_key.origin, row.observation_key.source_stream_id)
        if (selected_scope is not None and this_scope != selected_scope
                or stream is not None and this_stream != stream):
            raise PrivateMultiTfDenied("MST_368_MIXED_BUCKET_SOURCE_REVISION")
        selected_scope, stream = this_scope, this_stream
    return (common_key[:2] if common_key is not None else None), selected_scope


def _baseline_report_row(tf, snapshots, cutoff):
    selected = tuple(s for s in snapshots if s.selected is not None)
    return {
        "timeframe": tf.value,
        "requested_snapshots": len(snapshots),
        "single_visible": len(selected),
        "no_visible_revision": sum(s.reason == "NO_VISIBLE_REVISION" for s in snapshots),
        "conflicting_revision": sum(s.reason == "SOURCE_OR_REVISION_CONFLICT" for s in snapshots),
        "local_prerequisites_only": sum(s.confirmation_prerequisites(cutoff) for s in selected),
        "status": "CANDIDATE_ONLY_UNVERIFIED" if snapshots else "MISSING",
        "source_qualified": False,
    }


@dataclass(frozen=True)
class BaselineResolvedInputs:
    """Original analysis input boundary, not a detector or source admission.

    Each rule must still check its own versioned required/optional feature
    manifest. An empty independent bucket does not determine another rule.
    H4/M1 engineering/source inventory is deliberately not the core input.
    """
    instrument_id: str
    exchange: str
    as_of_utc: datetime
    m5_armed: bool
    buckets: tuple[tuple[Timeframe, tuple[ResolvedBarSnapshotV12, ...]], ...]

    def __post_init__(self):
        require_utc(self.as_of_utc)
        if (type(self.instrument_id) is not str
                or re.fullmatch(r"[A-Za-z0-9_:-]{3,128}", self.instrument_id) is None
                or type(self.exchange) is not str or EXCHANGE.fullmatch(self.exchange) is None
                or type(self.m5_armed) is not bool or type(self.buckets) is not tuple):
            raise PrivateMultiTfDenied("MST_368_BASELINE_SCOPE")
        expected = BASELINE_CORE_TF + ((Timeframe.M5,) if self.m5_armed else ())
        if (len(self.buckets) != len(expected)
                or any(type(pair) is not tuple or len(pair) != 2 for pair in self.buckets)
                or any(pair[0] is not tf for pair, tf in zip(self.buckets, expected))):
            raise PrivateMultiTfDenied("MST_368_EXACT_BASELINE_TF_ORDER")
        basis_calendar = selected_scope = None
        for tf, snapshots in self.buckets:
            key_scope, source_scope = _baseline_bucket(
                tf, snapshots, instrument=self.instrument_id,
                exchange=self.exchange, cutoff=self.as_of_utc,
            )
            if key_scope is not None:
                if basis_calendar is not None and key_scope != basis_calendar:
                    raise PrivateMultiTfDenied("MST_368_MIXED_CROSS_TF_BASIS_CALENDAR")
                basis_calendar = key_scope
            if source_scope is not None:
                if selected_scope is not None and source_scope != selected_scope:
                    raise PrivateMultiTfDenied("MST_368_MIXED_CROSS_TF_SOURCE_REVISION")
                selected_scope = source_scope

    def snapshots_for(self, tf: Timeframe):
        """Explicitly route exact, immutable as-of inputs; no best-source fallback."""
        for key, snapshots in self.buckets:
            if tf is key:
                return snapshots
        raise PrivateMultiTfDenied("MST_368_TIMEFRAME_NOT_IN_ANALYSIS_SCOPE")

    def safe_readiness(self):
        rows = [_baseline_report_row(tf, snaps, self.as_of_utc)
                for tf, snaps in self.buckets]
        if not self.m5_armed:
            rows.append({"timeframe": "M5", "status": "NOT_ARMED",
                         "source_qualified": False})
        return {
            "schema": "mst.private.original_baseline_resolved_inputs.v0.1",
            "timeframes": rows, "m5_armed": self.m5_armed,
            "h4_core_required": False, "m1_core_required": False,
            "global_rule_decision_inferred": False,
            "source_released": False, "signal_engine_parity_verified": False,
            "publication_state": "INCOMPLETE_REPORT", "decision": "NO_TRADE",
        }
