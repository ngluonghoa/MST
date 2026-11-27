"""§445 explicit hypothetical settled long-holdings feasibility, no sell authority."""
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from .contracts import Strategy
from .replay import require_utc


@dataclass(frozen=True)
class S1HoldingsPlan445:
    instrument_id: str
    strategy: Strategy
    policy_version: str
    known_at_utc: datetime
    max_age_seconds: int
    open_shares: int
    settled_shares: int
    reserved_shares: int
    sell_shares: int


@dataclass(frozen=True)
class S1HoldingsResult445:
    available_shares: int
    requested_shares: int
    candidate_match: bool

    @property
    def action_eligible(self):
        return False


def validate_holdings445(p):
    if type(p) is not S1HoldingsPlan445 or type(p.strategy) is not Strategy:
        raise ValueError("MST_445_EXPLICIT_HOLDINGS")
    if any(type(s) is not str or not s.strip() for s in (p.instrument_id,p.policy_version)):
        raise ValueError("MST_445_EXPLICIT_SCOPE_POLICY")
    if type(p.known_at_utc) is not datetime:
        raise ValueError("MST_445_EXPLICIT_KNOWN_TIME")
    require_utc(p.known_at_utc)
    counts=(p.open_shares,p.settled_shares,p.reserved_shares,p.sell_shares,p.max_age_seconds)
    if any(type(v) is not int or v<0 for v in counts):
        raise ValueError("MST_445_EXACT_NONNEGATIVE_COUNTS")
    if not 0<=p.reserved_shares<=p.settled_shares<=p.open_shares or p.sell_shares==0:
        raise ValueError("MST_445_IMPOSSIBLE_BALANCE_OR_SIZE")
    if not 1<=p.max_age_seconds<=86400:
        raise ValueError("MST_445_BOUNDED_SNAPSHOT_AGE")


def inspect_holdings445(target,p,proof,*,strategy,states):
    if p is None or proof.state is not states.MATCH:
        return proof
    if proof.rvol is None:
        return replace(proof,state=states.MISSING,reason="RF_INDEPENDENT_VOLUME_REQUIRED")
    if p.instrument_id!=target.market_bar_key.instrument_id or p.strategy is not strategy:
        return replace(proof,state=states.BLOCKED,reason="SELL_HOLDINGS_SCOPE_MISMATCH")
    age=target.verified_at_utc-p.known_at_utc
    if not timedelta(0)<=age<=timedelta(seconds=p.max_age_seconds):
        return replace(proof,state=states.BLOCKED,reason="SELL_HOLDINGS_NOT_CAUSAL_OR_FRESH")
    available=p.settled_shares-p.reserved_shares
    match=p.sell_shares<=available
    result=S1HoldingsResult445(available,p.sell_shares,match)
    return replace(proof,state=states.MATCH if match else states.NONMATCH,
                   reason="HYPOTHETICAL_SETTLED_HOLDINGS_ONLY",holdings=result)
