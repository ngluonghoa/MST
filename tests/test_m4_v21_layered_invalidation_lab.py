"""Cache V2.1 P0 pure full-policy dependency invalidation tests (synthetic only)."""
from dataclasses import replace
import unittest

from scripts.m4_v21_layered_invalidation_lab import (
    SCHEMA, STATUS, Layer, DependencyKind, SourceEvent, Depend, LayerNode,
    FullPolicyFixture, plan_invalidation, fabricated_dag, build_report,
)
from scripts.m2_a03_v2_cache_consumer_contract import fixture_scope


class CacheV21LayeredTests(unittest.TestCase):
    def setUp(self):
        self.scope = FullPolicyFixture(fixture_scope())
        self.nodes = fabricated_dag(self.scope)
    def plan(self, event, raw="a_raw", nodes=None, scope=None):
        return plan_invalidation(scope or self.scope, self.nodes if nodes is None else nodes,
                                 changed_raw_node=raw, event=event)
    def test_01_value_correction_only_connected_six(self):
        x=self.plan(SourceEvent.PRICE_OR_VOLUME_CHANGE)
        self.assertEqual(x["dependency_nodes"],9)
        self.assertEqual(len(x["impacted_nodes"]),6)
        self.assertEqual(len(x["unimpacted_fixture_nodes"]),3)
    def test_02_metadata_only_keeps_numeric_derived_cache(self):
        x=self.plan(SourceEvent.METADATA_LINEAGE_ONLY)
        self.assertEqual(x["impacted_nodes"],["a_raw","a_revision_audit"])
        self.assertIn("a_indicators",x["unimpacted_fixture_nodes"])
    def test_03_unqualified_source_change_fails_closed_whole_scope(self):
        x=self.plan(SourceEvent.UNQUALIFIED_SOURCE_CHANGE)
        self.assertEqual(len(x["impacted_nodes"]),9)
        self.assertEqual(x["unimpacted_fixture_nodes"],[])
        self.assertEqual(x["impacts"]["b_raw"],["QUARANTINE"])
    def test_04_branch_b_correction_ignores_branch_a(self):
        x=self.plan(SourceEvent.PRICE_OR_VOLUME_CHANGE,raw="b_raw")
        self.assertEqual(x["impacted_nodes"],["b_indicators","b_normalized","b_raw"])
    def test_05_raw_target_not_present_denied(self):
        with self.assertRaisesRegex(ValueError,"RAW_ROOT"):
            self.plan(SourceEvent.PRICE_OR_VOLUME_CHANGE,raw="missing")
    def test_06_non_raw_target_denied(self):
        with self.assertRaisesRegex(ValueError,"RAW_ROOT"):
            self.plan(SourceEvent.PRICE_OR_VOLUME_CHANGE,raw="a_indicators")
    def test_07_duplicate_nodes_denied(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE_LAYER"):
            self.plan(SourceEvent.PRICE_OR_VOLUME_CHANGE,nodes=self.nodes+(self.nodes[0],))
    def test_08_missing_dependency_denied(self):
        bad=replace(self.nodes[2],dependencies=(Depend("not_there",DependencyKind.DATA),))
        with self.assertRaisesRegex(ValueError,"MISSING_DECLARED"):
            self.plan(SourceEvent.PRICE_OR_VOLUME_CHANGE,nodes=self.nodes[:2]+(bad,)+self.nodes[3:])
    def test_09_reverse_edge_denied(self):
        bad=replace(self.nodes[1],dependencies=(Depend("a_indicators",DependencyKind.DATA),))
        with self.assertRaisesRegex(ValueError,"REVERSE_CACHE"):
            self.plan(SourceEvent.PRICE_OR_VOLUME_CHANGE,nodes=self.nodes[:1]+(bad,)+self.nodes[2:])
    def test_10_self_reference_denied(self):
        bad=replace(self.nodes[1],dependencies=(Depend("a_normalized",DependencyKind.DATA),))
        with self.assertRaisesRegex(ValueError,"REVERSE_CACHE"):
            self.plan(SourceEvent.PRICE_OR_VOLUME_CHANGE,nodes=self.nodes[:1]+(bad,)+self.nodes[2:])
    def test_11_raw_node_with_derived_dependency_denied(self):
        with self.assertRaisesRegex(ValueError,"RAW_SOURCE_ROOT"):
            replace(self.nodes[0],dependencies=(Depend("b_raw",DependencyKind.DATA),))
    def test_12_wrong_full_policy_binding_denied(self):
        bad=replace(self.nodes[1],full_policy_binding="0"*64)
        with self.assertRaisesRegex(PermissionError,"POLICY_SCOPE"):
            self.plan(SourceEvent.PRICE_OR_VOLUME_CHANGE,nodes=self.nodes[:1]+(bad,)+self.nodes[2:])
    def test_13_bare_v2_partition_digest_denied(self):
        bad=replace(self.nodes[0],full_policy_binding=self.scope.scope.candidate.digest)
        with self.assertRaisesRegex(PermissionError,"POLICY_SCOPE"):
            self.plan(SourceEvent.PRICE_OR_VOLUME_CHANGE,nodes=(bad,)+self.nodes[1:])
    def test_14_rights_epoch_changes_full_binding(self):
        legacy=replace(self.scope.scope.legacy,source_rights_policy_version="RIGHTS.REVOKED")
        other=FullPolicyFixture(fixture_scope(legacy))
        self.assertEqual(other.scope.candidate.digest,self.scope.scope.candidate.digest)
        self.assertNotEqual(other.binding,self.scope.binding)
        with self.assertRaisesRegex(PermissionError,"POLICY_SCOPE"):
            self.plan(SourceEvent.PRICE_OR_VOLUME_CHANGE,scope=other)
    def test_15_calendar_epoch_changes_full_binding(self):
        legacy=replace(self.scope.scope.legacy,calendar_version="CALENDAR.REVISED")
        other=FullPolicyFixture(fixture_scope(legacy))
        self.assertNotEqual(other.binding,self.scope.binding)
        self.assertEqual(other.scope.candidate.digest,self.scope.scope.candidate.digest)
    def test_16_indicator_parameter_version_changes_scope(self):
        legacy=replace(self.scope.scope.legacy,indicator_parameter_version="EMA20.ATR14.R2")
        other=FullPolicyFixture(fixture_scope(legacy))
        self.assertNotEqual(other.fingerprint,self.scope.fingerprint)
        self.assertEqual(other.scope.candidate.digest,self.scope.scope.candidate.digest)
    def test_17_quality_policy_changes_scope(self):
        legacy=replace(self.scope.scope.legacy,quality_policy_version="QUALITY.R2")
        other=FullPolicyFixture(fixture_scope(legacy))
        self.assertNotEqual(other.binding,self.scope.binding)
    def test_18_synthetic_scope_has_all_eight_policies(self):
        self.assertEqual(len(self.scope.policy_fields),8)
        self.assertEqual({k for k,_ in self.scope.policy_fields},{"rights","resolution","quality","adjustment","calendar","aggregation","indicator","indicator_parameters"})
    def test_19_unknown_event_type_denied(self):
        with self.assertRaisesRegex(TypeError,"TYPED_SOURCE_EVENT"):
            self.plan("PRICE_OR_VOLUME_CHANGE")
    def test_20_duplicate_dependency_denied(self):
        d=Depend("a_raw",DependencyKind.DATA)
        with self.assertRaisesRegex(ValueError,"DUPLICATE_NODE_DEPENDENCY"):
            replace(self.nodes[1],dependencies=(d,d))
    def test_21_empty_graph_denied(self):
        with self.assertRaisesRegex(TypeError,"NONEMPTY_TYPED_DAG"):
            self.plan(SourceEvent.PRICE_OR_VOLUME_CHANGE,nodes=())
    def test_22_illegal_node_name_denied(self):
        with self.assertRaisesRegex(ValueError,"VALID_LAYER_NODE"):
            replace(self.nodes[0],node_id="../cache")
    def test_23_invalid_policy_binding_sha_denied(self):
        with self.assertRaisesRegex(ValueError,"FULL_POLICY_SHA"):
            replace(self.nodes[0],full_policy_binding="bad")
    def test_24_repeatable_no_go_report(self):
        a=build_report()
        b=build_report()
        self.assertEqual(a,b)
        self.assertEqual(a["status"],STATUS)
        self.assertEqual(a["schema"],SCHEMA)
        self.assertFalse(a["actual_drive_cache_published"])
        self.assertFalse(a["governance_p0_owner_release_approved"])
    def test_25_permission_fields_never_granted(self):
        d=self.plan(SourceEvent.PRICE_OR_VOLUME_CHANGE)
        for k in ("read_or_write_licensed_market_cache","real_data_reuse_authorized",
                  "source_revision_first_known_verified","google_drive_io_performed",
                  "independent_cas_or_protected_floor_verified","trading_or_release_authorized"):
            self.assertIs(d[k],False)
    def test_26_orphan_derived_node_denied(self):
        bad=replace(self.nodes[1],dependencies=())
        with self.assertRaisesRegex(ValueError,"ORPHAN_DERIVED_LAYER"):
            self.plan(SourceEvent.PRICE_OR_VOLUME_CHANGE,nodes=self.nodes[:1]+(bad,)+self.nodes[2:])
    def test_27_wrong_dependency_kind_denied(self):
        with self.assertRaisesRegex(TypeError,"EXPLICIT_DEPENDENCY_CHANNEL"):
            Depend("a_raw","DATA")
    def test_28_wrong_layer_kind_denied(self):
        with self.assertRaisesRegex(TypeError,"EXPLICIT_CACHE_LAYER"):
            replace(self.nodes[0],layer=0)
