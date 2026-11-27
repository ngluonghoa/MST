"""§427 explicit hypothetical post-signal settlement timing, not a fill."""
from dataclasses import dataclass
from datetime import datetime

from .contracts import Strategy
from .market_data import InstrumentClass
from .replay import require_utc
from .session_calendar import TradingSession, SessionType


@dataclass(frozen=True)
class B8SettlementPlan427:
    instrument_id: str
    strategy: Strategy
    policy_version: str
    known_at_utc: datetime
    entry_session: TradingSession
    release_session: TradingSession
    hypothetical_entry_utc: datetime
    externally_supplied_release_utc: datetime
    required_exit_from_utc: datetime


@dataclass(frozen=True)
class B8SettlementResult427:
    state: str
    reason: str
    candidate_match: bool | None = None

    @property
    def action_eligible(self):
        return False


def validate_settlement427(p):
    if type(p) is not B8SettlementPlan427 or type(p.strategy) is not Strategy:
        raise ValueError("MST_427_EXPLICIT_STRATEGY_SETTLEMENT")
    if not all(type(x) is str and x.strip() for x in (p.instrument_id,p.policy_version)):
        raise ValueError("MST_427_EXPLICIT_INSTRUMENT_POLICY")
    for t in (p.known_at_utc,p.hypothetical_entry_utc,p.externally_supplied_release_utc,
              p.required_exit_from_utc):
        require_utc(t)
    if any(type(x) is not TradingSession for x in (p.entry_session,p.release_session)):
        raise ValueError("MST_427_EXPLICIT_SESSION_WITNESSES")
    if not (p.hypothetical_entry_utc<=p.externally_supplied_release_utc
            and p.hypothetical_entry_utc<p.required_exit_from_utc):
        raise ValueError("MST_427_INVALID_CLOCK_ORDER")


def _session427(session,t,key):
    return (session.verified and session.session_type is SessionType.CONTINUOUS
            and session.exchange==key.exchange
            and session.calendar_version==key.calendar_version
            and session.start_utc<=t<session.end_utc)


def _scope427(target,p,strategy):
    key=target.market_bar_key
    return (key.instrument_class is InstrumentClass.STOCK
            and key.instrument_id==p.instrument_id and p.strategy is strategy
            and p.known_at_utc<=target.verified_at_utc
            and p.hypothetical_entry_utc>target.verified_at_utc)


def inspect_settlement427(target,p,*,strategy):
    validate_settlement427(p)
    if not _scope427(target,p,strategy):
        return B8SettlementResult427("BLOCKED","SETTLEMENT_SCOPE_OR_CLOCK_MISMATCH")
    key=target.market_bar_key
    if not (_session427(p.entry_session,p.hypothetical_entry_utc,key)
            and _session427(p.release_session,p.externally_supplied_release_utc,key)):
        return B8SettlementResult427("BLOCKED","SESSION_WITNESS_MISMATCH")
    match=p.externally_supplied_release_utc<=p.required_exit_from_utc
    return B8SettlementResult427("COMPUTED_UNCALIBRATED",
        "SUPPLIED_RELEASE_BEFORE_REQUIRED_EXIT" if match else "REQUIRED_EXIT_BEFORE_RELEASE",match)
