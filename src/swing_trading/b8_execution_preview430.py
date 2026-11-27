"""§430 isolated RF execution-candidate chain; exact §424–429 behavior."""
from dataclasses import replace

from .market_data import Timeframe
from .b8_risk_geometry424 import inspect_b8_risk424, validate_risk424
from .b8_price_band426 import inspect_band426, validate_band426
from .b8_settlement427 import inspect_settlement427, validate_settlement427
from .b8_liquidity428 import inspect_liquidity428, validate_liquidity428
from .b8_portfolio429 import inspect_portfolio429, validate_portfolio429


def _rf_risk424(inputs, p, base, geometry, states):
    plan=p.rf.risk
    if plan is None:
        return geometry
    validate_risk424(plan)
    if geometry.state is not states.MATCH and geometry.extension_candidate_match is not False:
        return geometry
    target=inputs.snapshots_for(p.rf.timeframe)[p.rf.breakout_index].selected
    rows=inputs.snapshots_for(p.timeframe)[p.base_start:p.base_stop]
    result=inspect_b8_risk424(rows,target=target,resistance=base.private_resistance,
                             atr=base.private_atr,plan=plan,
                             extension_k=p.rf.extension.candidate_max_extension_atr if p.rf.extension else None)
    return _rf_risk_result424(geometry,result,states)


def _rf_risk_result424(geometry,result):
    if geometry.extension_candidate_match is False:
        return replace(geometry,risk=result)
    if result.state=="BLOCKED":
        return replace(geometry,state=states.BLOCKED,reason=result.reason,risk=result)
    if result.state=="NONMATCH" or result.candidate_match is False:
        return replace(geometry,state=states.NONMATCH,reason="RF_NET_RR_NONMATCH",risk=result)
    if result.candidate_match is None:
        return replace(geometry,state=states.DISTANCE,reason="RF_NET_RR_UNCALIBRATED",risk=result)
    return replace(geometry,reason="RF_MEASURED_BASE_NET_RR_CANDIDATE_ONLY",risk=result)


def _rf_band426(inputs,p,geometry,states):
    if p.rf.band is None:
        return geometry
    validate_band426(p.rf.band)
    if geometry.state not in (states.MATCH,states.NONMATCH):
        return geometry
    if geometry.risk is None and geometry.state is states.NONMATCH:
        return geometry
    target=inputs.snapshots_for(p.rf.timeframe)[p.rf.breakout_index].selected
    result=inspect_band426(target,p.rf.band,
                          max_entry=geometry.risk.max_entry if geometry.risk else None)
    if result.state=="BLOCKED":
        return replace(geometry,state=states.BLOCKED,reason=result.reason,band=result)
    if result.state=="NONMATCH" or result.candidate_match is False:
        return replace(geometry,state=states.NONMATCH,reason="RF_RAW_GRID_NONMATCH",band=result)
    return replace(geometry,band=result)


def _rf_settlement427(inputs,p,geometry,strategy,states):
    plan=p.rf.settlement
    if plan is None:
        return geometry
    validate_settlement427(plan)
    if geometry.state is not states.MATCH:
        return geometry
    target=inputs.snapshots_for(p.rf.timeframe)[p.rf.breakout_index].selected
    result=inspect_settlement427(target,plan,strategy=strategy)
    if result.state=="BLOCKED":
        return replace(geometry,state=states.BLOCKED,reason=result.reason,settlement=result)
    if result.candidate_match is False:
        return replace(geometry,state=states.NONMATCH,reason=result.reason,settlement=result)
    return replace(geometry,settlement=result)


def _rf_liquidity428(inputs,p,geometry,strategy,states):
    plan=p.rf.liquidity
    if plan is None:
        return geometry
    validate_liquidity428(plan)
    if geometry.state is not states.MATCH:
        return geometry
    target=inputs.snapshots_for(p.rf.timeframe)[p.rf.breakout_index].selected
    result=inspect_liquidity428(inputs.snapshots_for(Timeframe.D1),target,plan,strategy=strategy)
    state=geometry.state
    if result.state=="BLOCKED":
        state=states.BLOCKED
    elif result.state=="MISSING_INPUT":
        state=states.MISSING
    elif result.candidate_match is False:
        state=states.NONMATCH
    elif result.candidate_match is None:
        state=states.DISTANCE
    return replace(geometry,state=state,reason=result.reason,liquidity=result)


def _rf_portfolio429(inputs,p,geometry,strategy,states):
    plan=p.rf.portfolio
    if plan is None:
        return geometry
    validate_portfolio429(plan)
    if geometry.state is not states.MATCH:
        return geometry
    target=inputs.snapshots_for(p.rf.timeframe)[p.rf.breakout_index].selected
    result=inspect_portfolio429(target,plan,strategy=strategy,
        shares=p.rf.liquidity.order_shares if geometry.liquidity else None,
        net_risk=geometry.risk.net_risk if geometry.risk else None,
        buy_fee_rate=p.rf.risk.buy_fee_rate if geometry.risk else None)
    state=geometry.state
    if result.state=="BLOCKED":
        state=states.BLOCKED
    elif result.state=="MISSING_INPUT":
        state=states.MISSING
    elif result.candidate_match is False:
        state=states.NONMATCH
    return replace(geometry,state=state,reason=result.reason,portfolio=result)


def inspect_b8_execution430(inputs,p,base,geometry,strategy,*,states):
    """Preserve original enum and immutable ingredient identities without cycle."""
    risk=_rf_risk424(inputs,p,base,geometry,states)
    band=_rf_band426(inputs,p,risk,states)
    settlement=_rf_settlement427(inputs,p,band,strategy,states)
    liquidity=_rf_liquidity428(inputs,p,settlement,strategy,states)
    return _rf_portfolio429(inputs,p,liquidity,strategy,states)
