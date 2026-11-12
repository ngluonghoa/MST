#!/usr/bin/env python3
"""MST Market Scanner manual-only, synthetic-only safety contract.

This module makes NO external requests, reads NO private Google Drive data, writes
NO persistent cache, contains NO production market scanner/strategy implementation,
and grants NO permission to mutate the separate Watchlist control plane.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import math
import re
from typing import Mapping, Sequence

VENUES = frozenset({"HOSE", "HNX", "UPCOM"})
SCANNER_NAMESPACE = "mst/scanner/synthetic"
WATCHLIST_NAMESPACE = "mst/watchlist"
MAX_UNIVERSE_ROWS = 5000
MAX_SHORTLIST = 50
_SYMBOL = re.compile(r"[A-Z][A-Z0-9]{0,7}\Z")
_REVISION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{2,127}\Z")


class ScannerContractError(ValueError):
    """No external scan/cache action is permitted after a contract failure."""


@dataclass(frozen=True, order=True)
class Security:
    venue: str
    symbol: str


@dataclass(frozen=True)
class FrozenScan:
    scan_id: str
    source_revision: str
    as_of: str
    venues: tuple[str, ...]
    eligible: tuple[Security, ...]
    ignored_count: int
    candidate_limit: int
    scanner_cache_namespace: str = SCANNER_NAMESPACE

    def receipt(self) -> dict[str, object]:
        """Safe for public synthetic CI: counts and digest, not market prices."""
        return {
            "mode": "manual_synthetic_only",
            "scan_id": self.scan_id,
            "eligible_count": len(self.eligible),
            "excluded_count": self.ignored_count,
            "candidate_limit": self.candidate_limit,
            "cloud_access": False,
            "vendor_fetches": 0,
            "drive_writes": 0,
            "watchlist_writes": 0,
            "production_ready": False,
        }


def _as_of_date(value: str) -> date:
    if not isinstance(value, str):
        raise ScannerContractError("as_of must be an ISO date")
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise ScannerContractError("invalid as_of date") from exc
    if result.isoformat() != value:
        raise ScannerContractError("as_of must use YYYY-MM-DD exactly")
    return result


def _listing_date(value: object, field: str) -> date | None:
    if value is None and field == "delisted":
        return None
    if not isinstance(value, str):
        raise ScannerContractError("invalid listing date")
    parsed = _as_of_date(value)
    return parsed


def _bounded_positive_int(value: object, maximum: int, name: str) -> int:
    if type(value) is not int or not (1 <= value <= maximum):
        raise ScannerContractError(f"invalid {name}")
    return value


def freeze_manual_universe(
    *,
    trigger: str,
    source_revision: str,
    as_of: str,
    exchanges: Sequence[str],
    listings: Sequence[Mapping[str, object]],
    max_rows: int = MAX_UNIVERSE_ROWS,
    candidate_limit: int = 30,
) -> FrozenScan:
    """Freeze an explicit, bounded PIT universe; never discover wildcard symbols.

    This does not call a listing master, market provider or Google Drive. The
    caller supplies invented records for a synthetic contract demonstration.
    A real source-of-truth master, licenses and as-of revisions are NOT verified.
    """
    if trigger != "manual":
        raise ScannerContractError("only explicit manual trigger permitted")
    if not isinstance(source_revision, str) or not _REVISION.fullmatch(source_revision):
        raise ScannerContractError("missing or invalid source master revision")
    asof = _as_of_date(as_of)
    if isinstance(exchanges, (str, bytes)) or not isinstance(exchanges, (list, tuple)):
        raise ScannerContractError("exchanges must be an explicit list")
    if not exchanges or any(x not in VENUES for x in exchanges):
        raise ScannerContractError("invalid or empty exchange scope")
    if len(set(exchanges)) != len(exchanges):
        raise ScannerContractError("duplicate exchange scope")
    selected_venues = tuple(sorted(exchanges))
    maximum = _bounded_positive_int(max_rows, MAX_UNIVERSE_ROWS, "max_rows")
    count = _bounded_positive_int(candidate_limit, MAX_SHORTLIST, "candidate_limit")
    if isinstance(listings, (str, bytes)) or not isinstance(listings, (list, tuple)):
        raise ScannerContractError("listings must be an explicit bounded list")
    if not listings or len(listings) > maximum:
        raise ScannerContractError("empty or oversized listing master")
    eligible: list[Security] = []
    seen: set[tuple[str, str]] = set()
    seen_symbols: set[str] = set()
    for row in listings:
        if not isinstance(row, Mapping) or set(row) != {
            "venue", "symbol", "first_listed", "delisted", "suspended"
        }:
            raise ScannerContractError("invalid listing schema")
        venue, symbol = row["venue"], row["symbol"]
        if not isinstance(venue, str) or venue not in VENUES:
            raise ScannerContractError("unknown security venue")
        if not isinstance(symbol, str) or not _SYMBOL.fullmatch(symbol):
            raise ScannerContractError("invalid security symbol")
        if (venue, symbol) in seen or symbol in seen_symbols:
            raise ScannerContractError("duplicate or cross-venue ambiguous security")
        seen.add((venue, symbol))
        seen_symbols.add(symbol)
        if type(row["suspended"]) is not bool:
            raise ScannerContractError("invalid suspension status")
        first = _listing_date(row["first_listed"], "first_listed")
        last = _listing_date(row["delisted"], "delisted")
        if first is None or (last is not None and last < first):
            raise ScannerContractError("invalid listing lifecycle")
        if venue not in selected_venues:
            continue
        if first <= asof and (last is None or last > asof) and not row["suspended"]:
            eligible.append(Security(venue, symbol))
    if not eligible:
        raise ScannerContractError("no eligible securities; fail closed")
    frozen = tuple(sorted(eligible))
    canonical = {
        "domain": SCANNER_NAMESPACE,
        "trigger": trigger,
        "revision": source_revision,
        "as_of": asof.isoformat(),
        "venues": selected_venues,
        "eligible": [(r.venue, r.symbol) for r in frozen],
        "candidate_limit": count,
    }
    digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return FrozenScan(
        scan_id=digest,
        source_revision=source_revision,
        as_of=asof.isoformat(),
        venues=selected_venues,
        eligible=frozen,
        ignored_count=len(listings) - len(frozen),
        candidate_limit=count,
    )


def rank_fictional_probe_scores(
    frozen: FrozenScan, scores: Mapping[tuple[str, str], float]
) -> tuple[dict[str, object], ...]:
    """Sort INJECTED FICTIONAL scores only. NOT Swing parity/trading analysis."""
    if not isinstance(frozen, FrozenScan) or not isinstance(scores, Mapping):
        raise ScannerContractError("invalid synthetic screening inputs")
    allowed = {(security.venue, security.symbol) for security in frozen.eligible}
    if any(key not in allowed for key in scores):
        raise ScannerContractError("non-universe symbol supplied; refuse expansion")
    ranked: list[tuple[float, str, str]] = []
    for (venue, symbol), score in scores.items():
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ScannerContractError("non-numeric synthetic probe score")
        if not math.isfinite(score) or not 0 <= score <= 100:
            raise ScannerContractError("out-of-range synthetic probe score")
        ranked.append((float(score), venue, symbol))
    ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
    return tuple(
        {
            "venue": venue,
            "symbol": symbol,
            "synthetic_probe_score": score,
            "status": "FICTIONAL_REVIEW_ONLY_NOT_A_TRADE_SIGNAL",
        }
        for score, venue, symbol in ranked[:frozen.candidate_limit]
    )



def synthetic_scanner_cache_key(frozen: FrozenScan, kind: str) -> str:
    """Derive a synthetic Scanner-only key. Does NOT read/write Drive."""
    if not isinstance(frozen, FrozenScan):
        raise ScannerContractError("invalid immutable scan descriptor")
    if not isinstance(kind, str) or kind not in {"universe", "candidates", "audit"}:
        raise ScannerContractError("invalid scanner artifact kind")
    if not re.fullmatch(r"[0-9a-f]{64}", frozen.scan_id):
        raise ScannerContractError("invalid snapshot digest")
    if frozen.scanner_cache_namespace != SCANNER_NAMESPACE:
        raise ScannerContractError("cache namespace tampering denied")
    return f"{SCANNER_NAMESPACE}/{frozen.scan_id}/{kind}.json"



def synthetic_demo() -> dict[str, object]:
    """No arbitrary CLI symbols or live endpoints: wholly invented fixture."""
    listings = [
        {"venue": "HOSE", "symbol": "MOCKA", "first_listed": "2024-01-01",
         "delisted": None, "suspended": False},
        {"venue": "HNX", "symbol": "MOCKB", "first_listed": "2024-01-01",
         "delisted": None, "suspended": False},
        {"venue": "UPCOM", "symbol": "MOCKC", "first_listed": "2024-01-01",
         "delisted": None, "suspended": True},
    ]
    frozen = freeze_manual_universe(
        trigger="manual", source_revision="synthetic-v1",
        as_of="2026-11-11", exchanges=["HOSE", "HNX", "UPCOM"],
        listings=listings, candidate_limit=2,
    )
    ranked = rank_fictional_probe_scores(frozen, {
        ("HOSE", "MOCKA"): 87.0, ("HNX", "MOCKB"): 61.0,
    })
    receipt = frozen.receipt()
    receipt["fictional_candidate_count"] = len(ranked)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic-self-test", action="store_true", required=True)
    args = parser.parse_args()
    print(json.dumps(synthetic_demo(), sort_keys=True))
