"""§386 explicitly selected D1 pullback contraction geometry, not VCP approval."""
from dataclasses import dataclass
from decimal import Decimal

from .causal_structure_geometry import GeometryState, StructureSide, TiePolicy, inspect_causal_pivot
from .market_data import Timeframe
from .replay import require_utc
from .source_quality import ResolvedBarSnapshotV12


@dataclass(frozen=True)
class ContractionPlan386:
    swings: tuple[tuple[int, int], ...]
    left_count: int
    right_count: int
    tie_policy: TiePolicy


@dataclass(frozen=True)
class ContractionCandidate386:
    reason: str
    depths: tuple[Decimal, ...] = ()
    relations: tuple[str, ...] = ()
    low_relations: tuple[str, ...] = ()
    trailing_contractions: int = 0

    @property
    def action_eligible(self):
        return False

    @property
    def compression_verified(self):
        return False

    def safe_summary(self):
        return {
            "schema": "mst.private.b6_contraction_geometry.v0.1",
            "reason": self.reason, "relations": self.relations,
            "low_relations": self.low_relations,
            "trailing_contractions": self.trailing_contractions,
            "two_observed_contractions": self.trailing_contractions >= 2,
            "compression_verified": False, "source_qualified": False,
            "parameter_approved": False, "action_eligible": False,
        }


def _valid_pair386(pair):
    return (type(pair) is tuple and len(pair) == 2
            and all(type(i) is int and i >= 0 for i in pair))


def _check_plan386(plan):
    if type(plan) is not ContractionPlan386 or type(plan.swings) is not tuple:
        raise ValueError("MST_386_EXPLICIT_IMMUTABLE_SWING_PLAN")
    if len(plan.swings) > 40 or not all(_valid_pair386(p) for p in plan.swings):
        raise ValueError("MST_386_BOUNDED_INDEX_PAIRS")
    if (type(plan.left_count) is not int or not 1 <= plan.left_count <= 40
            or type(plan.right_count) is not int or not 1 <= plan.right_count <= 40
            or type(plan.tie_policy) is not TiePolicy):
        raise ValueError("MST_386_EXPLICIT_PIVOT_POLICY")


def _history_ok386(history):
    return (type(history) is tuple and 1 <= len(history) <= 512
            and all(type(r) is ResolvedBarSnapshotV12
                    and r.market_bar_key.timeframe is Timeframe.D1 for r in history))


def _ordered386(indices, count):
    return all(a < b for a,b in zip(indices,indices[1:])) and indices[-1] < count


def _pivots386(history, indices, plan, cutoff):
    return tuple(inspect_causal_pivot(
        history, candidate_index=i, left_count=plan.left_count,
        right_count=plan.right_count, tie_policy=plan.tie_policy,
        side=StructureSide.HIGH if j % 2 == 0 else StructureSide.LOW,
        as_of_utc=cutoff,
    ) for j,i in enumerate(indices))


def _known_before_next386(history, indices, pivots):
    return all(p.witness_known_at_utc <= history[i].market_bar_key.bar_start_utc
               for p,i in zip(pivots,indices[1:]))


def _relation386(previous, current):
    return "NARROWER" if current < previous else "WIDER" if current > previous else "EQUAL"


def _trailing386(relations):
    count = 0
    for relation in reversed(relations):
        if relation != "NARROWER":
            break
        count += 1
    return count


def _describe386(pivots):
    highs = tuple(p.pivot_price for p in pivots[::2])
    lows = tuple(p.pivot_price for p in pivots[1::2])
    if any(high <= low or low <= 0 for high,low in zip(highs,lows)):
        return ContractionCandidate386("NONPOSITIVE_PULLBACK_OR_PRICE")
    # Compare cross products, avoiding quotient rounding changing a tie.
    widths = tuple(h-l for h,l in zip(highs,lows))
    relations = tuple(_relation386(a*hb,b*ha)
                      for a,b,ha,hb in zip(widths,widths[1:],highs,highs[1:]))
    low_relations = tuple("HIGHER" if a < b else "LOWER" if a > b else "EQUAL"
                          for a,b in zip(lows,lows[1:]))
    depths = tuple(w/h for w,h in zip(widths,highs))
    return ContractionCandidate386("PULLBACK_DEPTH_GEOMETRY_ONLY", depths, relations,
                                   low_relations, _trailing386(relations))


def inspect_d1_contraction_candidate(history, *, plan, as_of_utc):
    """Strictly ordered high-to-low swings; two decreases need three swings.

    Candidate depth = (high-low)/high; comparison uses cross products.
    Prior local extremum must have been known before next candidate begins.
    This explicit geometry does not certify contiguous sessions, uptrend,
    volume dry-up, ATR compression, selected latest pivots or a B6 signal.
    """
    require_utc(as_of_utc)
    _check_plan386(plan)
    if not _history_ok386(history):
        return ContractionCandidate386("MISSING_OR_INVALID_D1_HISTORY")
    if len(plan.swings) < 3:
        return ContractionCandidate386("INSUFFICIENT_SWINGS_FOR_TWO_COMPARISONS")
    indices = tuple(i for pair in plan.swings for i in pair)
    if not _ordered386(indices,len(history)):
        return ContractionCandidate386("DUPLICATE_OR_UNORDERED_SWINGS")
    pivots = _pivots386(history,indices,plan,as_of_utc)
    if any(p.state is GeometryState.BLOCKED for p in pivots):
        return ContractionCandidate386("PIVOT_INPUT_BLOCKED")
    if any(p.geometric_extremum is not True for p in pivots):
        return ContractionCandidate386("SWING_NOT_LOCAL_EXTREMUM")
    if not _known_before_next386(history,indices,pivots):
        return ContractionCandidate386("EARLIER_EXTREMUM_NOT_KNOWN_BEFORE_NEXT")
    return _describe386(pivots)
