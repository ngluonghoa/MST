"""MST Cache V2.1 P0-2: fixture-only full-policy layered invalidation preview.

Uses inherited V1 CacheIdentity via existing V1->V2 typed scope. This is not
a market feed, authenticated source identity, approved Google Drive cache,
CAS publisher, persistent revision ledger or trading signal.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
from enum import Enum, IntEnum
from hashlib import sha256
import json
from pathlib import Path
import re

from scripts.m2_a03_v2_cache_consumer_contract import (
    FixtureV2ConsumerScope, fixture_scope, _hash,
)

SCHEMA = "mst.m4.cache-v2-1-layered-invalidation.synthetic.v1"
STATUS = "FULL_POLICY_LAYER_INVALIDATION_PREVIEW_SOURCE_AND_DRIVE_NO_GO"
_NAME = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_HEX = re.compile(r"^[0-9a-f]{64}$")


class Layer(IntEnum):
    RAW = 0
    NORMALIZED = 1
    AGGREGATED = 2
    INDICATORS = 3
    ANALYSIS = 4
    AUDIT = 5


class DependencyKind(str, Enum):
    DATA = "DATA"
    LINEAGE = "LINEAGE"


class SourceEvent(str, Enum):
    PRICE_OR_VOLUME_CHANGE = "PRICE_OR_VOLUME_CHANGE"
    METADATA_LINEAGE_ONLY = "METADATA_LINEAGE_ONLY"
    UNQUALIFIED_SOURCE_CHANGE = "UNQUALIFIED_SOURCE_CHANGE"


@dataclass(frozen=True)
class FullPolicyFixture:
    """Untrusted but complete legacy V1 policy binding, not vendor authority."""
    scope: FixtureV2ConsumerScope

    def __post_init__(self):
        if type(self.scope) is not FixtureV2ConsumerScope:
            raise TypeError("EXACT_V1_TO_V2_TYPED_SCOPE_REQUIRED")
        if type(self.scope.binding_sha256) is not str or not _HEX.fullmatch(self.scope.binding_sha256):
            raise ValueError("COMPLETE_V1_POLICY_SCOPE_BINDING_REQUIRED")
        if self.scope.binding_sha256 == self.scope.candidate.digest:
            raise ValueError("STANDALONE_V2_PARTITION_NOT_COMPLETE_POLICY")

    @property
    def binding(self) -> str:
        return self.scope.binding_sha256

    @property
    def policy_fields(self) -> tuple[tuple[str, str], ...]:
        k = self.scope.legacy
        return tuple(sorted((
            ("rights", k.source_rights_policy_version),
            ("resolution", k.source_resolution_policy_version),
            ("quality", k.quality_policy_version),
            ("adjustment", k.adjustment_revision),
            ("calendar", k.calendar_version),
            ("aggregation", k.aggregation_policy_version),
            ("indicator", k.indicator_version),
            ("indicator_parameters", k.indicator_parameter_version),
        )))

    @property
    def fingerprint(self) -> str:
        return _hash({
            "schema": SCHEMA,
            "full_v1_policy_scope": self.binding,
            "legacy_identity": self.scope.legacy.fingerprint,
            "candidate_partition": self.scope.candidate.digest,
            "eight_policy_dimensions": dict(self.policy_fields),
        })


@dataclass(frozen=True)
class Depend:
    node_id: str
    channel: DependencyKind

    def __post_init__(self):
        if type(self.node_id) is not str or not _NAME.fullmatch(self.node_id):
            raise ValueError("VALID_PARENT_NODE_ID_REQUIRED")
        if type(self.channel) is not DependencyKind:
            raise TypeError("EXPLICIT_DEPENDENCY_CHANNEL_REQUIRED")


@dataclass(frozen=True)
class LayerNode:
    node_id: str
    layer: Layer
    full_policy_binding: str
    dependencies: tuple[Depend, ...] = ()

    def __post_init__(self):
        if type(self.node_id) is not str or not _NAME.fullmatch(self.node_id):
            raise ValueError("VALID_LAYER_NODE_ID_REQUIRED")
        if type(self.layer) is not Layer:
            raise TypeError("EXPLICIT_CACHE_LAYER_REQUIRED")
        if type(self.full_policy_binding) is not str or not _HEX.fullmatch(self.full_policy_binding):
            raise ValueError("FULL_POLICY_SHA256_REQUIRED_NOT_BARE_PARTITION")
        if type(self.dependencies) is not tuple or any(type(d) is not Depend for d in self.dependencies):
            raise TypeError("TYPED_IMMUTABLE_DEPENDENCIES_REQUIRED")
        if len(set(d.node_id for d in self.dependencies)) != len(self.dependencies):
            raise ValueError("DUPLICATE_NODE_DEPENDENCY_DENIED")
        if self.layer is Layer.RAW and self.dependencies:
            raise ValueError("RAW_SOURCE_ROOT_CANNOT_DEPEND_ON_DERIVATIVES")


def plan_invalidation(
    scope: FullPolicyFixture,
    nodes: tuple[LayerNode, ...],
    *,
    changed_raw_node: str,
    event: SourceEvent,
) -> dict:
    """Conservative synthetic dependency impact; never actually invalidates cache."""
    if type(scope) is not FullPolicyFixture:
        raise TypeError("EXACT_FULL_POLICY_TEST_SCOPE_REQUIRED")
    if type(nodes) is not tuple or not nodes or any(type(n) is not LayerNode for n in nodes):
        raise TypeError("NONEMPTY_TYPED_DAG_REQUIRED")
    if type(event) is not SourceEvent:
        raise TypeError("TYPED_SOURCE_EVENT_REQUIRED")
    if type(changed_raw_node) is not str or not _NAME.fullmatch(changed_raw_node):
        raise ValueError("EXACT_CHANGED_NODE_REQUIRED")
    by_id = {n.node_id: n for n in nodes}
    if len(by_id) != len(nodes):
        raise ValueError("DUPLICATE_LAYER_NODE_DENIED")
    if any(n.full_policy_binding != scope.binding for n in nodes):
        raise PermissionError("V1_RIGHTS_OR_POLICY_SCOPE_MISMATCH_DENIED")
    for n in nodes:
        if n.layer is not Layer.RAW and not n.dependencies:
            raise ValueError("ORPHAN_DERIVED_LAYER_NOT_QUALIFIED")
        for d in n.dependencies:
            source = by_id.get(d.node_id)
            if source is None:
                raise ValueError("MISSING_DECLARED_DEPENDENCY_DENIED")
            if source.layer >= n.layer:
                raise ValueError("CYCLE_OR_REVERSE_CACHE_DEPENDENCY_DENIED")
    if changed_raw_node not in by_id or by_id[changed_raw_node].layer is not Layer.RAW:
        raise ValueError("SOURCE_EVENT_MUST_TARGET_EXISTING_RAW_ROOT")
    order = sorted(nodes, key=lambda n: (n.layer.value, n.node_id))
    effects = {n.node_id: set() for n in order}
    if event is SourceEvent.UNQUALIFIED_SOURCE_CHANGE:
        # Unknown provenance/closure cannot safely reuse *any* node of the
        # explicitly bound full-policy scope. Even another root is quarantined.
        for n in order:
            effects[n.node_id].add("QUARANTINE")
    else:
        effects[changed_raw_node] = (
            {"DATA", "LINEAGE"} if event is SourceEvent.PRICE_OR_VOLUME_CHANGE
            else {"LINEAGE"}
        )
        for n in order:
            for edge in n.dependencies:
                p = effects[edge.node_id]
                if edge.channel is DependencyKind.DATA and "DATA" in p:
                    effects[n.node_id].update(("DATA", "LINEAGE"))
                elif edge.channel is DependencyKind.LINEAGE and ("LINEAGE" in p or "DATA" in p):
                    effects[n.node_id].add("LINEAGE")
    affected = tuple(sorted(k for k, v in effects.items() if v))
    reusable = tuple(sorted(k for k, v in effects.items() if not v))
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "source_event": event.value,
        "scope_fingerprint_sha256": scope.fingerprint,
        "full_legacy_policy_binding_sha256": scope.binding,
        "bare_v2_partition_sha256_not_sufficient": True,
        "policy_field_count": len(scope.policy_fields),
        "dependency_nodes": len(nodes),
        "impacted_nodes": list(affected),
        "unimpacted_fixture_nodes": list(reusable),
        "impacts": {k: sorted(effects[k]) for k in sorted(effects) if effects[k]},
        "read_or_write_licensed_market_cache": False,
        "real_data_reuse_authorized": False,
        "source_revision_first_known_verified": False,
        "google_drive_io_performed": False,
        "independent_cas_or_protected_floor_verified": False,
        "trading_or_release_authorized": False,
    }


def fabricated_dag(scope: FullPolicyFixture) -> tuple[LayerNode, ...]:
    """Two independent fictitious source roots with one lineage audit."""
    b = scope.binding
    def n(k: str, layer: Layer, *edges: Depend):
        return LayerNode(k, layer, b, tuple(edges))
    def data(k): return Depend(k, DependencyKind.DATA)
    def lineage(k): return Depend(k, DependencyKind.LINEAGE)
    return (
        n("a_raw", Layer.RAW),
        n("a_normalized", Layer.NORMALIZED, data("a_raw")),
        n("a_aggregate", Layer.AGGREGATED, data("a_normalized")),
        n("a_indicators", Layer.INDICATORS, data("a_aggregate")),
        n("a_analysis", Layer.ANALYSIS, data("a_indicators")),
        n("a_revision_audit", Layer.AUDIT, lineage("a_raw")),
        n("b_raw", Layer.RAW),
        n("b_normalized", Layer.NORMALIZED, data("b_raw")),
        n("b_indicators", Layer.INDICATORS, data("b_normalized")),
    )


def build_report() -> dict:
    scope = FullPolicyFixture(fixture_scope())
    nodes = fabricated_dag(scope)
    value = plan_invalidation(scope, nodes, changed_raw_node="a_raw", event=SourceEvent.PRICE_OR_VOLUME_CHANGE)
    lineage = plan_invalidation(scope, nodes, changed_raw_node="a_raw", event=SourceEvent.METADATA_LINEAGE_ONLY)
    unknown = plan_invalidation(scope, nodes, changed_raw_node="a_raw", event=SourceEvent.UNQUALIFIED_SOURCE_CHANGE)
    assert len(value["impacted_nodes"]) == 6 and len(value["unimpacted_fixture_nodes"]) == 3
    assert lineage["impacted_nodes"] == ["a_raw", "a_revision_audit"]
    assert len(unknown["impacted_nodes"]) == len(nodes)
    return {
        "schema": SCHEMA, "status": STATUS,
        "adopted_candidate": "CACHE_V2_1_P0_LAYERED_RECOMPUTE_PLAN",
        "v1_original_source_modified": False,
        "opt_in_eight_v2_source_modified": False,
        "fixture_value_correction": value,
        "fixture_metadata_revision": lineage,
        "unqualified_change_quarantine": unknown,
        "provider_market_source_verified": False,
        "actual_drive_cache_published": False,
        "governance_p0_owner_release_approved": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    result = build_report()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": SCHEMA, "status": STATUS,
        "price_impacted_count": len(result["fixture_value_correction"]["impacted_nodes"]),
        "lineage_impacted_count": len(result["fixture_metadata_revision"]["impacted_nodes"]),
        "unknown_quarantine_count": len(result["unqualified_change_quarantine"]["impacted_nodes"]),
        "real_cache_enabled": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
