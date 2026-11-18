"""Source-isolated D1 ATR14 / RVOL20 *reference math* over private MCP Cache.

This diagnostic never creates an original engine ResolvedBarSnapshotV12:
venue close, official session coverage, issuer first-known, verified price
adjustments, comparison policy, corporate actions and source rights are
NOT proven by a well-formed OHLCV document. Therefore its numbers must
never be fed to a trade-eligible detector, backtest or publisher.

Math matches causal_indicators.py P0.9:
- Wilder ATR14: seed mean 14 TR using 15 prior chronological bars,
  smooth remaining TR as (13*previous_ATR + current_TR)/14.
- RVOL_TF N20: target volume / mean 20 preceding SAME-source D1 bars.
  No RVOL_TOD, inferred intra-session class or cross-provider blending.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from .market_data import PriceBasis
from .private_cache_source_bridge import (
    PrivateD1Reference, PrivateSourceDenied, inspect_private_d1_snapshot,
)
from .replay import require_utc

_RULE_ATR="WILDER_ATR14_SEED14_TR_V0_1"
_RULE_RVOL="RVOL_TF_N20_CANDIDATE_V0_1"


class ReferenceMathState(str, Enum):
    BLOCKED="BLOCKED"
    COMPUTED_UNCALIBRATED="COMPUTED_UNCALIBRATED"


@dataclass(frozen=True)
class PrivateD1Math:
    """Descriptive result only, nonactionable even if computed."""
    indicator_id: str
    rule_version: str
    state: ReferenceMathState
    reason: str
    value: Decimal | None
    used_bar_count: int
    source_provider: str
    source_symbol: str
    source_digest_sha256: str
    capture_day: date
    last_source_session: date | None
    price_basis: PriceBasis
    source_provisional_observed: bool
    first_known_attested: bool=False
    venue_close_attested: bool=False
    data_certified: bool=False
    history_complete_certified: bool=False
    comparator_policy_certified: bool=False
    parameter_approved: bool=False
    actionable: bool=False

    def __post_init__(self) -> None:
        if (self.indicator_id not in ("ATR14_D1","RVOL_TF20_D1")
                or self.rule_version not in (_RULE_ATR,_RULE_RVOL)
                or not isinstance(self.state,ReferenceMathState)
                or type(self.used_bar_count) is not int
                or not 0<=self.used_bar_count<=2048
                or not isinstance(self.price_basis,PriceBasis)
                or type(self.source_provisional_observed) is not bool):
            raise PrivateSourceDenied("MST_PRIVATE_MATH_INVALID_STATE")
        if (self.state is ReferenceMathState.COMPUTED_UNCALIBRATED
                and (not isinstance(self.value,Decimal)
                     or not self.value.is_finite() or self.value<0)):
            raise PrivateSourceDenied("MST_PRIVATE_MATH_BAD_COMPUTED")
        if (self.state is ReferenceMathState.BLOCKED
                and self.value is not None):
            raise PrivateSourceDenied("MST_PRIVATE_MATH_BLOCKED_HAS_VALUE")
        if (self.first_known_attested or self.venue_close_attested
                or self.data_certified or self.history_complete_certified
                or self.comparator_policy_certified or self.parameter_approved
                or self.actionable):
            raise PrivateSourceDenied("MST_PRIVATE_MATH_AUTHORITY_FORBIDDEN")


def compute_private_d1_math(
    snapshot: PrivateD1Reference, *, as_of_utc: datetime,
) -> tuple[PrivateD1Math, PrivateD1Math]:
    """Recompute from source-normalized private rows, never from another issuer.

    Only complete immutable reference identity is accepted. Caller must NOT
    use a future snapshot at a past cutoff: this rejects retrospective input.
    Snapshot chronology is not traded, regardless of measured math.
    """
    require_utc(as_of_utc)
    if (type(snapshot) is not PrivateD1Reference
            or snapshot.source_snapshot_day>as_of_utc.date()
            or snapshot.source_is_appowned_publisher
            or snapshot.venue_close_attested
            or snapshot.issuer_first_known_attested
            or snapshot.eligible_for_signals
            or snapshot.eligible_for_backtest):
        raise PrivateSourceDenied("MST_PRIVATE_MATH_REFERENCE_AUTHORITY_INVALID")
    bars=snapshot.bars
    if (not bars or len(bars)!=snapshot.source_rows_observed
            or len(bars)>2048
            or any(b.provider!=snapshot.provider or b.symbol!=snapshot.symbol
                   or b.trading_date>snapshot.source_snapshot_day
                   or b.eligible_for_signals for b in bars)
            or any(b.trading_date<=bars[i-1].trading_date
                   for i,b in enumerate(bars) if i>0)
            or len({b.reported_price_basis for b in bars})!=1):
        raise PrivateSourceDenied("MST_PRIVATE_MATH_SERIES_CONTEXT_INVALID")
    basis=bars[0].reported_price_basis
    last=bars[-1].trading_date
    provisional=any(b.provisional_source for b in bars)

    def result(indicator,rule,state,reason,value=None,count=0):
        return PrivateD1Math(
            indicator,rule,state,reason,value,count,
            snapshot.provider,snapshot.symbol,snapshot.raw_source_sha256,
            snapshot.source_snapshot_day,last,basis,provisional,
        )
    if len(bars)<15:
        atr=result("ATR14_D1",_RULE_ATR,ReferenceMathState.BLOCKED,
                   "REQUIRE_15_D1_SOURCE_BARS")
    else:
        ranges=[]
        for previous,current in zip(bars,bars[1:]):
            ranges.append(max(
                current.high_vnd-current.low_vnd,
                abs(current.high_vnd-previous.close_vnd),
                abs(current.low_vnd-previous.close_vnd),
            ))
        n=Decimal(14)
        value=sum(ranges[:14],Decimal(0))/n
        for tr in ranges[14:]:
            value=(Decimal(13)*value+tr)/n
        if value<=0:
            atr=result("ATR14_D1",_RULE_ATR,ReferenceMathState.BLOCKED,
                       "NONPOSITIVE_ATR14_NO_NORMALIZATION")
        else:
            atr=result("ATR14_D1",_RULE_ATR,
                       ReferenceMathState.COMPUTED_UNCALIBRATED,
                       "PRIVATE_SOURCE_MATH_ONLY_NO_VENUE_CLOSE_OR_ISSUER_CERTIFICATION",
                       value,len(bars))

    if len(bars)<21:
        rvol=result("RVOL_TF20_D1",_RULE_RVOL,ReferenceMathState.BLOCKED,
                    "REQUIRE_TARGET_AND_EXACTLY_20_PRIOR_D1_SOURCE_BARS")
    else:
        comparator=bars[-21:-1]
        total=sum((b.volume_shares for b in comparator),0)
        if total<=0:
            rvol=result("RVOL_TF20_D1",_RULE_RVOL,ReferenceMathState.BLOCKED,
                        "ZERO_PRIOR_20_VOLUME_DENOMINATOR")
        else:
            val=Decimal(bars[-1].volume_shares)*Decimal(20)/Decimal(total)
            rvol=result("RVOL_TF20_D1",_RULE_RVOL,
                        ReferenceMathState.COMPUTED_UNCALIBRATED,
                        "PRIVATE_SOURCE_MATH_ONLY_NO_VOLUME_COMPARABILITY_CERTIFICATION",
                        val,21)
    return atr,rvol


def inspect_and_compute_private_d1(
    document: dict, *, as_of_utc: datetime,
) -> tuple[PrivateD1Reference, tuple[PrivateD1Math,PrivateD1Math]]:
    """Single read-only entrypoint for captured PRIVATE D1 docs."""
    snapshot=inspect_private_d1_snapshot(document,as_of_utc=as_of_utc)
    return snapshot,compute_private_d1_math(snapshot,as_of_utc=as_of_utc)
