"""§369 source-locked phase input routing, not executable detector manifests.

Verbatim §24.4 clauses preserve non-timeframe requirements. Explicit frame
mentions are routing candidates only; slash choices need an explicit caller
choice, not an inferred OR predicate. Unspecified TFs, feature IDs, lookback,
warmup, right bars, parameters, freshness and event policies remain pending.
"""
from dataclasses import dataclass
from types import MappingProxyType

from .contracts import DecisionStatus, Strategy
from .market_data import Timeframe
from .private_multitf_readiness import BaselineResolvedInputs
from .zone_manifest_v03 import MANIFESTS, PHASES, inspect_phase

SOURCE_CLAUSES = MappingProxyType({
    "B1": (
        "R0 W1+D1 causal decline + confirmed bottom/range + valid market context",
        "R_C D1 support/two historically available tests or causally confirmed pivot",
        "R_E M15 verified CLOSED reclaim/failed-break OR BOS_UP tied to event_id",
        "R_F D1 CLOSED BOS_UP and confirmed HL + independent verified volume/market group; W1 confirmation required only when label=MAJOR_REVERSAL",
        "O M5 entry refinement; verified divergence as corroboration, never sole price trigger",
    ),
    "B2": (
        "R0 D1 uptrend+H1/D1 support and no verified critical break",
        "R_C pullback NEAR verified support and ATR valid",
        "R_E verified CLOSED M15 HL/reclaim event",
        "R_F H1/M15 CLOSED above causal micro pivot + D1 trend intact + risk pass",
        "O M5 when armed; low-volume RVOL as additional confidence, but if used as gate becomes R at corresponding phase",
    ),
    "B3": (
        "R0 D1 causal range with two confirmed upper/lower boundary touches + valid ATR",
        "R_C price NEAR lower range boundary",
        "R_E verified CLOSED false breakdown/reclaim OR M15 BOS_UP",
        "R_F H1/D1 CLOSED back above lower boundary and micro rejection/pivot, no price basis mismatch",
        "O RVOL/VSA context if not in selected confirmation variant; optional M5",
    ),
    "B4": (
        "R0 historical D1/H1 confirmed CHoCH/BOS_UP event_id after falling regime",
        "R_C initial post-event pullback with prior bottom invalidation",
        "R_E M15 verified CLOSED HL/reclaim",
        "R_F first causally confirmed HL + later CLOSED breakout over last known micro high, no right-bar lookahead",
        "O volume as warning only until selected confirmation variant specifies as R",
    ),
    "B5": (
        "R0 verified prior D1/H1 breakout event_id/pivot with timestamp and revision",
        "R_C retest of exact former pivot within versioned window, known ATR",
        "R_E M15 verified CLOSED reclaim/failed-break",
        "R_F H1/D1 verified CLOSED support hold + breakout of retest micro high + confirmed required volume/risk policy",
        "O M5 entry precision; low-volume pullback quality unless configured R",
    ),
    "B6": (
        "R0 W1/D1 rising trend or verified post-rise base + causal contraction pivots",
        "R_C >=2 contractions or approved compression predicate with source/ATR/volume valid",
        "R_E M15 verified CLOSED rise near upper pivot",
        "R_F D1/H1 CLOSED above upper pivot + approved volume confirmation + anti-chase/R:R",
        "O BB bandwidth only as feature input if configured; RVOL_TOD when legally sourced, never infer from missing minutes",
    ),
    "B7": (
        "R0 verified D1 downtrend + market/settlement/liquidity info for eligible SHORT strategy",
        "R_C causal support/ATR stretch + no long-trend reversal",
        "R_E M15 verified CLOSED reclaim/CHoCH_UP",
        "R_F H1/M15 CLOSED above causal micro high + D1 downtrend explicitly preserved + liquidity/settlement/risk pass",
        "O M5 when armed; RSI oversold is contextual only, not signal",
    ),
    "B8": (
        "R0 verified D1/H1 base and resistance pivot + aligned RS benchmark + ATR and price-limit rules",
        "R_C price NEAR pivot with confirmed candidate base",
        "R_E M15 verified CLOSED pivot cross/reclaim; if intraday RVOL_TOD invoked, it becomes R_E",
        "R_F H1/D1 CLOSED breakout with approved volume/RVOL and RS confirmation, max-extension and R:R pass",
        "O M5 preview/entry; industry benchmark may be optional only if index RS variant approved and explicitly labeled, never silently replace sector",
    ),
    "S1": (
        "R0 W1/D1 uptrend history + causal major resistance/pivots",
        "R_C verified distribution/exhaustion evidence beyond RSI",
        "R_E H1/M15 CLOSED failed breakout/CHoCH_DOWN",
        "R_F D1 CLOSED below structural HL/neckline, confirmed BOS_DOWN/CHoCH and independent volume/context group; W1 required only for MAJOR_CYCLE_TOP label",
        "O divergence/VWAP as corroboration, never RSI sole sell trigger",
    ),
    "S2": (
        "R0 D1 verified downtrend + H1 resistance/LH context",
        "R_C rally NEAR resistance and confirmed bearish structure",
        "R_E M15 verified CLOSED rejection/micro LH",
        "R_F H1/M15 CLOSED below micro swing low while D1 remains down; actionable sell requires verified holdings",
        "O RVOL supply-demand confirmation unless a selected variant makes it R; no naked short",
    ),
    "S3": (
        "R0 D1 verified uptrend + structural resistance or actual TP plan",
        "R_C price near structural target/extension",
        "R_E M15 verified CLOSED micro CHoCH or approved risk-plan TP event",
        "R_F CLOSED H1/M15 micro HL break OR objectively achieved pre-existing approved TP target; actionable sell/partial requires verified holdings and plan",
        "O momentum divergence and volume climax; do not invent user position",
    ),
    "S4": (
        "R0 verified D1 range with >=2 causal upper/lower boundary tests + ATR",
        "R_C near upper boundary with causal rejection/failed extension",
        "R_E M15/H1 verified CLOSED false breakout/BOS_DOWN",
        "R_F D1/H1 CLOSED back inside range and below confirmed micro low; sell action requires holdings",
        "O VSA/UTAD labeling only when causal event evidence exists",
    ),
    "S5": (
        "R0 prior D1/H1 uptrend + timestamped verified BOS_DOWN/CHoCH event",
        "R_C first post-event rally fails beneath previous structural high",
        "R_E M15 verified CLOSED LH/rejection",
        "R_F first causally confirmed LH + CLOSED breakdown of micro low, no future pivot bars; sell action requires holdings",
        "O volume confirmation if not part of approved variant; no short selling",
    ),
    "S6": (
        "R0 prior verified breakout event_id, time, pivot, revision",
        "R_C failure to hold pivot within approved event window",
        "R_E M15 verified CLOSED back under pivot",
        "R_F corresponding H1/D1 CLOSED below breakout pivot + micro-support failure/approved volume criteria, as-of event sequence verified; sell action requires holdings",
        "O AVWAP (if exact matched value verified), never mandatory silently",
    ),
    "S7": (
        "R0 previous verified D1/H1 breakdown event_id + old support level",
        "R_C retest from below within approved window",
        "R_E M15 verified CLOSED rejection/failed reclaim",
        "R_F H1/D1 CLOSED under former support and below micro low or verified continuation structure; sell action requires holdings",
        "O low-volume retracement unless selected variant demands it",
    ),
    "S8": (
        "R0 D1 causal return/ATR historical percentile distribution + volume comparables",
        "R_C approved acceleration/exhaustion predicate with event evidence (not RSI alone)",
        "R_E M15 verified CLOSED reversal below micro support (VWAP only if accurate)",
        "R_F H1/D1 CLOSED reversal under confirmed key low + verified exhaustion/volume context, no inferred major S1 top; sell action requires holdings",
        "O session VWAP and position context for warning only; position required if generating sell order/size",
    ),
})
# Direct explicit frame mentions, not a completed required-feature manifest.
# A slash group is unresolved until the caller selects a route candidate.
_FRAME_ROUTES = MappingProxyType({
    "B1": ((("W1", "D1"), ()), (("D1",), ()), (("M15",), ()), (("D1",), ())),
    "B2": ((("D1",), ("H1", "D1")), ((), ()), (("M15",), ()), (("D1",), ("H1", "M15"))),
    "B3": ((("D1",), ()), ((), ()), ((), ()), ((), ("H1", "D1"))),
    "B4": (((), ("D1", "H1")), ((), ()), (("M15",), ()), ((), ())),
    "B5": (((), ("D1", "H1")), ((), ()), (("M15",), ()), ((), ("H1", "D1"))),
    "B6": (((), ("W1", "D1")), ((), ()), (("M15",), ()), ((), ("D1", "H1"))),
    "B7": ((("D1",), ()), ((), ()), (("M15",), ()), (("D1",), ("H1", "M15"))),
    "B8": (((), ("D1", "H1")), ((), ()), (("M15",), ()), ((), ("H1", "D1"))),
    "S1": (((), ("W1", "D1")), ((), ()), ((), ("H1", "M15")), (("D1",), ())),
    "S2": ((("D1", "H1"), ()), ((), ()), (("M15",), ()), (("D1",), ("H1", "M15"))),
    "S3": ((("D1",), ()), ((), ()), ((), ()), ((), ())),
    "S4": ((("D1",), ()), ((), ()), ((), ("M15", "H1")), ((), ("D1", "H1"))),
    "S5": (((), ("D1", "H1")), ((), ()), (("M15",), ()), ((), ())),
    "S6": (((), ()), ((), ()), (("M15",), ()), ((), ("H1", "D1"))),
    "S7": (((), ("D1", "H1")), ((), ()), (("M15",), ()), ((), ("H1", "D1"))),
    "S8": ((("D1",), ()), ((), ()), (("M15",), ()), ((), ("H1", "D1"))),
})
_M5_OPTIONAL = frozenset(("B1", "B2", "B3", "B5", "B7", "B8"))
_PENDING = ("EXACT_FEATURE_IDS", "LOOKBACK_WARMUP_RIGHT_BARS",
            "SOURCE_FRESHNESS_CLOSURE_POLICY", "EVENT_AND_VARIANT_POLICY",
            "PARAMETER_AND_PREDICATE_APPROVAL", "INDEPENDENT_SOURCE_ADMISSION")


@dataclass(frozen=True)
class RoutedPhaseInputs:
    """Read-only scoped inputs; counts and clauses do not authorize a signal."""
    zone_id: str
    strategy: Strategy
    variant_id: str
    phase: str
    predicate_ref: str
    required_clause: str
    optional_clause: str
    fixed_frames: tuple[Timeframe, ...]
    choice_frames: tuple[Timeframe, ...]
    selected_frame: Timeframe | None
    buckets: tuple
    optional_m5: tuple | None
    unresolved: tuple[str, ...]

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def action_eligible(self):
        return False


def _frames(zone, variant, phase):
    fixed, choice = _FRAME_ROUTES[zone][PHASES.index(phase)]
    if phase == "R_F" and variant in (
            "B1/F_MAJOR_REVERSAL_PENDING", "S1/F_MAJOR_CYCLE_TOP_PENDING"):
        fixed = fixed + ("W1",)
    if zone == "B3" and phase == "R_E" and variant == "B3/E_BOS_UP":
        fixed = ("M15",)
    if zone == "S3" and phase == "R_E" and variant == "S3/E_MICRO_CHOCH":
        fixed = ("M15",)
    if zone == "S3" and phase == "R_F" and variant == "S3/F_MICRO_BREAK":
        choice = ("H1", "M15")
    return tuple(map(Timeframe, fixed)), tuple(map(Timeframe, choice))


def _bucket_status(frame, rows, cutoff):
    if not rows:
        return ("MISSING_" + frame.value,)
    if any(r.selected is None for r in rows):
        return ("UNRESOLVED_REVISION_" + frame.value,)
    if not all(r.confirmation_prerequisites(cutoff) for r in rows):
        return ("LOCAL_PREREQUISITES_INCOMPLETE_" + frame.value,)
    return ()


def route_phase_inputs(inputs, *, zone_id, strategy, variant_id, phase,
                       selected_frame=None):
    """Route exact requested phase inputs, without inheriting a global failure.

    A supplied frame choice is not approval of a slash policy or a branch.
    No previous-phase pass or feature value is inferred from this report.
    """
    if type(inputs) is not BaselineResolvedInputs:
        raise TypeError("MST_369_BASELINE_INPUT_REQUIRED")
    manifest = inspect_phase(zone_id, strategy=strategy, variant_id=variant_id,
                             phase=phase)
    fixed, choice = _frames(zone_id, variant_id, phase)
    if selected_frame is not None and (
            type(selected_frame) is not Timeframe or selected_frame not in choice):
        raise ValueError("MST_369_EXPLICIT_FRAME_CHOICE_INVALID")
    frames = fixed
    if selected_frame is not None and selected_frame not in fixed:
        frames += (selected_frame,)
    buckets = tuple((tf, inputs.snapshots_for(tf)) for tf in frames)
    pending = list(_PENDING)
    if choice and selected_frame is None:
        pending.append("EXPLICIT_FRAME_CHOICE_PENDING")
    if not fixed and not choice:
        pending.append("EXACT_FEATURE_TIMEFRAME_PENDING")
    for tf, snapshots in buckets:
        pending.extend(_bucket_status(tf, snapshots, inputs.as_of_utc))
    m5 = None
    if inputs.m5_armed and zone_id in _M5_OPTIONAL:
        m5 = inputs.snapshots_for(Timeframe.M5)
    if variant_id == "B8/INTRADAY_RVOL_TOD_PENDING" and phase == "R_E":
        pending.append("REQUIRED_RVOL_TOD_UNVERIFIED")
    return RoutedPhaseInputs(
        zone_id, strategy, variant_id, phase, manifest.predicate_ref,
        SOURCE_CLAUSES[zone_id][PHASES.index(phase)], SOURCE_CLAUSES[zone_id][4],
        fixed, choice, selected_frame, buckets, m5, tuple(pending),
    )
