#!/usr/bin/env python3
"""MST Dynamic Watchlist contract: pure, fictional, nonproduction control plane.

This file does NOT contact Google Sheets, Drive, GitHub, SSI, DNSE, VCBS, or
the market; it cannot schedule jobs, write cache, authorize a candidate
promotion, or grant an actor Cloud permissions. The caller must independently
authenticate a stable version of a private Sheet before passing rows here.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Sequence

WATCHLIST_NAMESPACE = "mst/watchlist"
SCANNER_NAMESPACE = "mst/scanner"
SHEET_HEADERS = ("Symbol", "Exchange", "Enabled")
ALLOWED_VENUES = frozenset(("HOSE", "HNX", "UPCOM"))
MAX_WATCHLIST_ROWS = 1000
_SYMBOL_RE = re.compile(r"[A-Z][A-Z0-9]{0,7}\Z")
_REVISION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{2,127}\Z")


class WatchlistContractError(ValueError):
    """Invalid or untrusted configuration: refuse all refresh planning."""


@dataclass(frozen=True, order=True)
class WatchSecurity:
    venue: str
    symbol: str


@dataclass(frozen=True)
class FrozenWatchlist:
    """Immutable, fully validated snapshot to use for ONE collector run."""

    generation: int
    source_revision: str
    membership_digest: str
    snapshot_digest: str
    enabled: tuple[WatchSecurity, ...]
    paused: tuple[WatchSecurity, ...]
    namespace: str = WATCHLIST_NAMESPACE

    def public_safety_receipt(self) -> dict[str, object]:
        """Only aggregated fake-safe metadata; no private ticker values."""
        return {
            "mode": "synthetic_watchlist_contract_only",
            "membership_digest": self.membership_digest,
            "enabled_count": len(self.enabled),
            "paused_count": len(self.paused),
            "provider_requests": 0,
            "drive_reads": 0,
            "drive_writes": 0,
            "scanner_cache_writes": 0,
            "production_ready": False,
        }


@dataclass(frozen=True)
class RefreshPlan:
    """Desired changes only; NO network operations or data deletion."""

    to_start: tuple[WatchSecurity, ...]
    to_continue: tuple[WatchSecurity, ...]
    to_stop: tuple[WatchSecurity, ...]
    stopped_by_pause: tuple[WatchSecurity, ...]
    stopped_by_removal: tuple[WatchSecurity, ...]
    previous_digest: str | None
    current_digest: str

    def safe_counts(self) -> dict[str, int]:
        return {
            "start": len(self.to_start),
            "continue": len(self.to_continue),
            "stop": len(self.to_stop),
            "paused": len(self.stopped_by_pause),
            "removed": len(self.stopped_by_removal),
        }


def _normalize_symbol(value: object) -> str:
    if not isinstance(value, str):
        raise WatchlistContractError("symbol must be text")
    symbol = value.strip().upper()
    if not _SYMBOL_RE.fullmatch(symbol):
        raise WatchlistContractError("invalid symbol; wildcards forbidden")
    return symbol


def _normalize_venue(value: object) -> str:
    if not isinstance(value, str):
        raise WatchlistContractError("exchange must be text")
    venue = value.strip().upper()
    if venue not in ALLOWED_VENUES:
        raise WatchlistContractError("unsupported exchange; no venue inference")
    return venue


def _normalize_enabled(value: object) -> bool:
    if not isinstance(value, str):
        raise WatchlistContractError("enabled must be explicit TRUE/FALSE text")
    enabled = value.strip().upper()
    if enabled not in {"TRUE", "FALSE"}:
        raise WatchlistContractError("enabled must be explicit TRUE or FALSE")
    return enabled == "TRUE"


def freeze_sheet_values(
    *,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    source_revision: str,
    generation: int,
    max_rows: int = MAX_WATCHLIST_ROWS,
) -> FrozenWatchlist:
    """Validate one caller-supplied consistent Google Sheet values snapshot.

    'generation' MUST be attested and monotonic by a separately authorized
    external signer/floor; this lab cannot establish the authenticity of a
    Google Drive revision or prevent remote rollback by itself.
    """
    if not isinstance(headers, (list, tuple)) or tuple(headers) != SHEET_HEADERS:
        raise WatchlistContractError("invalid Sheet header/schema")
    if not isinstance(source_revision, str) or not _REVISION_RE.fullmatch(source_revision):
        raise WatchlistContractError("missing/invalid stable source revision")
    if type(generation) is not int or generation < 1:
        raise WatchlistContractError("invalid trusted generation")
    if type(max_rows) is not int or not (1 <= max_rows <= MAX_WATCHLIST_ROWS):
        raise WatchlistContractError("invalid row budget")
    if not isinstance(rows, (list, tuple)) or len(rows) > max_rows:
        raise WatchlistContractError("invalid or oversized Sheet rows")

    values: dict[WatchSecurity, bool] = {}
    seen_symbols: set[str] = set()
    for row in rows:
        if not isinstance(row, (list, tuple)):
            raise WatchlistContractError("invalid Sheet row container")
        # Allow completely blank spreadsheet rows, but NOT partial rows.
        if len(row) == 3 and all(isinstance(v, str) and not v.strip() for v in row):
            continue
        if len(row) != 3:
            raise WatchlistContractError("incomplete or extended Sheet row")
        symbol = _normalize_symbol(row[0])
        venue = _normalize_venue(row[1])
        enabled = _normalize_enabled(row[2])
        if symbol in seen_symbols:
            raise WatchlistContractError("duplicate/cross-venue ambiguous symbol")
        seen_symbols.add(symbol)
        values[WatchSecurity(venue, symbol)] = enabled

    active = tuple(sorted(security for security, on in values.items() if on))
    inactive = tuple(sorted(security for security, on in values.items() if not on))
    # Membership identity ignores harmless input row order and casing.
    members = [
        {"venue": security.venue, "symbol": security.symbol, "enabled": flag}
        for security, flag in sorted(values.items())
    ]
    members_json = json.dumps(members, sort_keys=True, separators=(",", ":"))
    membership_digest = hashlib.sha256(members_json.encode("utf-8")).hexdigest()
    revision_json = json.dumps({
        "schema": "mst.watchlist.sheet.v1",
        "source_revision": source_revision,
        "generation": generation,
        "membership_digest": membership_digest,
        "namespace": WATCHLIST_NAMESPACE,
    }, sort_keys=True, separators=(",", ":"))
    snapshot_digest = hashlib.sha256(revision_json.encode("utf-8")).hexdigest()
    return FrozenWatchlist(
        generation=generation,
        source_revision=source_revision,
        membership_digest=membership_digest,
        snapshot_digest=snapshot_digest,
        enabled=active,
        paused=inactive,
    )


def plan_incremental_refresh(
    *,
    prior: FrozenWatchlist | None,
    current: FrozenWatchlist,
) -> RefreshPlan:
    """Compute an immutable one-run symbol delta, never provider/Drive I/O.

    Stops are scheduling decisions only: NEVER delete old Cache. Content
    changes at an unchanged externally trusted generation are denied.
    """
    if not isinstance(current, FrozenWatchlist):
        raise WatchlistContractError("current snapshot required")
    if current.namespace != WATCHLIST_NAMESPACE:
        raise WatchlistContractError("watchlist namespace mismatch")
    if prior is not None:
        if not isinstance(prior, FrozenWatchlist) or prior.namespace != WATCHLIST_NAMESPACE:
            raise WatchlistContractError("invalid previous snapshot")
        if current.generation < prior.generation:
            raise WatchlistContractError("rollback generation refused")
        if current.generation == prior.generation and (
            current.snapshot_digest != prior.snapshot_digest
        ):
            raise WatchlistContractError("torn/same-generation edit refused")

    before = set(prior.enabled) if prior is not None else set()
    now = set(current.enabled)
    paused = set(current.paused)
    to_start = tuple(sorted(now - before))
    to_continue = tuple(sorted(now & before))
    to_stop = tuple(sorted(before - now))
    stopped_pause = tuple(sorted(set(to_stop) & paused))
    stopped_removed = tuple(sorted(set(to_stop) - paused))
    return RefreshPlan(
        to_start=to_start,
        to_continue=to_continue,
        to_stop=to_stop,
        stopped_by_pause=stopped_pause,
        stopped_by_removal=stopped_removed,
        previous_digest=prior.snapshot_digest if prior else None,
        current_digest=current.snapshot_digest,
    )


def synthetic_example() -> dict[str, object]:
    """Not owner Watchlist; invented fake securities and zero side effects."""
    old = freeze_sheet_values(
        headers=SHEET_HEADERS,
        rows=[["MOCKA", "HOSE", "TRUE"], ["MOCKB", "HNX", "TRUE"]],
        source_revision="fake-revision-one",
        generation=1,
    )
    new = freeze_sheet_values(
        headers=SHEET_HEADERS,
        rows=[["MOCKA", "HOSE", "FALSE"], ["MOCKB", "HNX", "TRUE"],
              ["MOCKC", "UPCOM", "TRUE"]],
        source_revision="fake-revision-two",
        generation=2,
    )
    result = new.public_safety_receipt()
    result["plan_counts"] = plan_incremental_refresh(prior=old, current=new).safe_counts()
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic-self-test", action="store_true", required=True)
    parser.parse_args()
    print(json.dumps(synthetic_example(), sort_keys=True))
