"""§435 explicit cumulative candidate evidence gate, never rule approval."""
from dataclasses import replace


def _proof435(code,result):
    return (code,result is not None,None if result is None else result.candidate_match)


def _r0435(plan,g):
    return (("R0_ADJUSTED_STOCK_STREAM",plan.rs_stock is not None,True),
            _proof435("R0_RS",g.rs),
            ("R0_RAW_BAND",g.band is not None,
             g.band is not None and g.band.state=="COMPUTED_UNCALIBRATED"))


def _rf435(g):
    return (("RF_RVOL",g.rvol is not None,g.rvol_candidate_match),
            _proof435("RF_RS",g.rs),
            ("RF_EXTENSION",g.extension_atr is not None,g.extension_candidate_match),
            _proof435("RF_NET_RR",g.risk),
            ("RF_MAX_ENTRY",g.risk is not None and g.risk.max_entry is not None,True),
            _proof435("RF_RAW_GRID",g.band),
            _proof435("RF_SETTLEMENT",g.settlement),
            _proof435("RF_LIQUIDITY",g.liquidity),
            _proof435("RF_PORTFOLIO_SCENARIO",g.portfolio))


def _requirements435(plan,phase,g,variant):
    if phase=="R0":
        return _r0435(plan,g)
    if phase=="R_E" and variant=="B8/INTRADAY_RVOL_TOD_PENDING":
        return (("RE_TOD",g.rvol is not None,g.tod_candidate_match),)
    if phase=="R_F":
        return _rf435(g)
    return ()


def _classify435(g,requirements,states):
    missing=tuple(code for code,present,_ in requirements if not present)
    unknown=tuple(code for code,present,match in requirements if present and match is None)
    rejected=tuple(code for code,present,match in requirements if present and match is False)
    if rejected:
        return replace(g,state=states.NONMATCH,reason="MANDATORY_CANDIDATE_NONMATCH",
                       candidate_evidence_complete=False,mandatory_gaps=rejected)
    if missing:
        return replace(g,state=states.MISSING,reason="MANDATORY_CANDIDATE_INPUT_MISSING",
                       candidate_evidence_complete=False,mandatory_gaps=missing+unknown)
    if unknown:
        return replace(g,state=states.DISTANCE,reason="MANDATORY_CANDIDATE_UNCALIBRATED",
                       candidate_evidence_complete=False,mandatory_gaps=unknown)
    return replace(g,candidate_evidence_complete=True)


def apply_phase435(plan,phase,g,variant,*,states):
    if not plan.strict_candidate_evidence:
        return g
    if g.state is not states.MATCH:
        return replace(g,candidate_evidence_complete=False)
    return _classify435(g,_requirements435(plan,phase,g,variant),states)
