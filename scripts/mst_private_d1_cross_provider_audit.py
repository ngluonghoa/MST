"""Strict same-session, cross-provider D1 arithmetic audit -- research only.

Never selects a winning provider, signs source provenance, verifies official
exchange close, confirms a price adjustment or issues a trading decision.
Comparing a source's LAST 21 native D1 rows (not a filtered intersection)
prevents missing dates from being silently concealed by an inner join.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from swing_trading.private_cache_source_bridge import (
    PrivateD1Reference, QuarantinedD1Bar, PrivateSourceDenied,
)
from swing_trading.replay import require_utc

PROVIDERS = ("SSI", "DNSE", "VCBS")
WINDOW = 21
DENIAL = "MST_CROSS_PROVIDER_PRIVATE_D1_NOT_COMPARABLE"


def _validate(s: PrivateD1Reference, *, as_of_utc: datetime) -> None:
    if (type(s) is not PrivateD1Reference
            or s.provider not in PROVIDERS
            or type(s.bars) is not tuple
            or len(s.bars) != s.source_rows_observed
            or len(s.bars) < WINDOW or len(s.bars) > 2048
            or s.source_snapshot_day > as_of_utc.date()
            or s.source_is_appowned_publisher
            or s.venue_close_attested or s.issuer_first_known_attested
            or s.eligible_for_signals or s.eligible_for_backtest
            or type(s.has_provisional_source) is not bool
            or any(type(b) is not QuarantinedD1Bar
                   or b.provider != s.provider or b.symbol != s.symbol
                   or b.trading_date > s.source_snapshot_day
                   or b.eligible_for_signals
                   or type(b.volume_shares) is not int
                   or b.volume_shares < 0
                   or not all(type(v) is Decimal and v.is_finite() and v > 0
                              for v in (b.open_vnd, b.high_vnd,
                                        b.low_vnd, b.close_vnd))
                   for b in s.bars)
            or any(s.bars[i-1].trading_date >= s.bars[i].trading_date
                   for i in range(1, len(s.bars)))):
        raise PrivateSourceDenied(DENIAL)
    if (len({b.reported_price_basis for b in s.bars}) != 1
            or any(b.low_vnd > min(b.open_vnd, b.close_vnd)
                   or b.high_vnd < max(b.open_vnd, b.close_vnd)
                   for b in s.bars)):
        raise PrivateSourceDenied(DENIAL)


def _math(rows: tuple[QuarantinedD1Bar, ...]) -> tuple[Decimal, Decimal | None]:
    """21 same-source bars; seed 14 TR then apply 6 Wilder updates."""
    ranges = [
        max(cur.high_vnd - cur.low_vnd,
            abs(cur.high_vnd - prev.close_vnd),
            abs(cur.low_vnd - prev.close_vnd))
        for prev, cur in zip(rows, rows[1:])
    ]
    atr = sum(ranges[:14], Decimal(0)) / Decimal(14)
    for tr in ranges[14:]:
        atr = (Decimal(13) * atr + tr) / Decimal(14)
    previous_volume = sum((bar.volume_shares for bar in rows[:-1]), 0)
    rvol = (Decimal(rows[-1].volume_shares) * Decimal(20) /
            Decimal(previous_volume)) if previous_volume else None
    return atr, rvol


def audit_common_tail(
    sources: tuple[PrivateD1Reference, ...], *,
    as_of_utc: datetime,
) -> dict[str, Any]:
    """Return provider-isolated numeric diagnostics; no price rows or authority.

    Refuse date gaps, detached captures, a different symbol, issuer status
    promotion, or any mismatch in the LAST 21 native date labels. Historical
    ATR differences from distinct 62/70/248-row seeds are intentionally not
    confused with the strictly aligned 21-row research comparison.
    """
    require_utc(as_of_utc)
    if (type(sources) is not tuple or len(sources) != 3
            or tuple(sorted(s.provider for s in sources
                            if type(s) is PrivateD1Reference)) != PROVIDERS
            or len({s.symbol for s in sources
                    if type(s) is PrivateD1Reference}) != 1):
        raise PrivateSourceDenied(DENIAL)
    for s in sources:
        _validate(s, as_of_utc=as_of_utc)
    selected = {s.provider: s for s in sources}
    window = {p: tuple(selected[p].bars[-WINDOW:]) for p in PROVIDERS}
    days = tuple(b.trading_date for b in window["SSI"])
    if any(tuple(b.trading_date for b in window[p]) != days
           for p in PROVIDERS[1:]):
        raise PrivateSourceDenied("MST_CROSS_PROVIDER_PRIVATE_D1_TAIL_NOT_ALIGNED")

    # Purely numeric, NOT source/adjustment equivalence.
    ohlcv_differences = 0
    close_differences = 0
    volume_differences = 0
    for rows in zip(*(window[p] for p in PROVIDERS)):
        shapes = [(
            b.open_vnd, b.high_vnd, b.low_vnd, b.close_vnd,
            b.volume_shares,
        ) for b in rows]
        ohlcv_differences += len(set(shapes)) > 1
        close_differences += len({b.close_vnd for b in rows}) > 1
        volume_differences += len({b.volume_shares for b in rows}) > 1
    computed = {p: _math(window[p]) for p in PROVIDERS}
    return {
        "schema": "mst.qa.private_d1_strict_21day_provider_audit.v0.1",
        "symbol": selected["SSI"].symbol,
        "providers": list(PROVIDERS),
        "timeframe": "D1",
        "native_tail_days_each": WINDOW,
        "aligned_first_day": days[0].isoformat(),
        "aligned_last_day": days[-1].isoformat(),
        "source_rows_by_provider": {
            p: selected[p].source_rows_observed for p in PROVIDERS
        },
        "source_digests_by_provider": {
            p: selected[p].raw_source_sha256 for p in PROVIDERS
        },
        "reported_price_basis_by_provider": {
            p: selected[p].bars[-1].reported_price_basis.value
            for p in PROVIDERS
        },
        "numerical_ohlcv_difference_days": int(ohlcv_differences),
        "numerical_close_difference_days": int(close_differences),
        "numerical_volume_difference_days": int(volume_differences),
        "aligned_seed21_atr14_reference": {
            p: str(computed[p][0]) for p in PROVIDERS
        },
        "aligned_prior20_rvol_reference": {
            p: None if computed[p][1] is None else str(computed[p][1])
            for p in PROVIDERS
        },
        "atr_references_numerically_equal": (
            len({computed[p][0] for p in PROVIDERS}) == 1
        ),
        "rvol_references_numerically_equal": (
            len({computed[p][1] for p in PROVIDERS}) == 1
        ),
        "source_licence_attested": False,
        "official_venue_close_attested": False,
        "issuer_first_known_attested": False,
        "adjustment_basis_comparability_attested": False,
        "calendar_completeness_attested": False,
        "provider_winner_selected": False,
        "eligible_for_signal_or_backtest": False,
        "cache_published": False,
        "trade_orders": 0,
        "status": "PRIVATE_REFERENCE_ONLY_NO_TRADE",
    }
