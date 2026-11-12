"""MST Cache V2.1 synthetic 6-TF source-window and causal suffix regression tests."""
from dataclasses import replace
from datetime import timedelta, datetime
import unittest

from scripts.m4_v21_six_tf_causal_slices import (
    SCHEMA,STATUS,FAKE_M5,TIMEFRAMES,FAKE_MEMBERS_PER_WINDOW,BAR,
    ChangeKind,FixtureWindow,FixtureSixTFGrid,FixtureSourceChange,
    plan_six_tf,fabricate_grid,fixture_change,build_receipt,
)
from scripts.m4_v21_layered_invalidation_lab import FullPolicyFixture
from scripts.m2_a03_v2_cache_consumer_contract import fixture_scope


class SixTimeframeCausalWindowTests(unittest.TestCase):
    def setUp(self):
        self.grid=fabricate_grid()
        self.event=fixture_change(self.grid)
    def grid_with(self,windows=None,**kw):
        return replace(self.grid,windows=self.grid.windows if windows is None else windows,**kw)
    def plan(self,kind=ChangeKind.PRICE_VOLUME_REVISION,indices=(15,),**eventkw):
        return plan_six_tf(self.grid,replace(fixture_change(self.grid,kind,indices),**eventkw))
    def mutated_window(self,index,**kwargs):
        return self.grid.windows[:index]+(replace(self.grid.windows[index],**kwargs),)+self.grid.windows[index+1:]
    def test_01_declares_exactly_six_fixtures(self):
        self.assertEqual(TIMEFRAMES,("M5","M15","M30","H1","H4","D1"))
    def test_02_explicit_m5_membership(self):
        self.assertEqual(self.grid.count_by_tf["M5"],96)
    def test_03_explicit_m15_membership(self):
        self.assertEqual(self.grid.count_by_tf["M15"],32)
    def test_04_explicit_m30_membership(self):
        self.assertEqual(self.grid.count_by_tf["M30"],16)
    def test_05_explicit_h1_membership(self):
        self.assertEqual(self.grid.count_by_tf["H1"],8)
    def test_06_explicit_h4_membership(self):
        self.assertEqual(self.grid.count_by_tf["H4"],2)
    def test_07_artificial_d1_one_session(self):
        self.assertEqual(self.grid.count_by_tf["D1"],1)
        self.assertEqual(self.grid.artificial_session_end_utc-self.grid.artificial_session_start_utc,timedelta(hours=8))
        self.assertFalse(self.grid.fixture_vendor_calendar_verified)
    def test_08_all_window_count_155(self):
        self.assertEqual(len(self.grid.windows),155)
    def test_09_specific_m5_value_only_corresponding_bar_groups(self):
        x=self.plan()
        expected={"M5":[15],"M15":[5],"M30":[2],"H1":[1],"H4":[0],"D1":[0]}
        self.assertEqual({t:x["timeframes"][t]["numerical_bar_windows_recompute"] for t in TIMEFRAMES},expected)
    def test_10_causal_suffix_recomputes_132_checkpoints(self):
        x=self.plan()
        self.assertEqual({t:len(x["timeframes"][t]["causal_indicator_checkpoints_recompute"]) for t in TIMEFRAMES},{"M5":81,"M15":27,"M30":14,"H1":7,"H4":2,"D1":1})
    def test_11_earlier_checkpoints_not_recomputed(self):
        x=self.plan()
        for tf,earlier in {"M5":15,"M15":5,"M30":2,"H1":1,"H4":0,"D1":0}.items():
            self.assertEqual(x["timeframes"][tf]["independent_earlier_indicator_checkpoints_reusable_count"],earlier)
    def test_12_last_m5_revision_only_one_per_tf(self):
        x=self.plan(indices=(95,))
        self.assertEqual({t:x["timeframes"][t]["numerical_bar_windows_recompute"] for t in TIMEFRAMES},{"M5":[95],"M15":[31],"M30":[15],"H1":[7],"H4":[1],"D1":[0]})
        self.assertEqual(sum(len(v["causal_indicator_checkpoints_recompute"]) for v in x["timeframes"].values()),6)
    def test_13_two_revisions_order_independent(self):
        a=self.plan(indices=(15,95))
        b=self.plan(indices=(95,15))
        self.assertEqual(a["timeframes"],b["timeframes"])
    def test_14_two_revisions_in_same_m15_bucket(self):
        x=self.plan(indices=(15,16))
        self.assertEqual(x["timeframes"]["M15"]["numerical_bar_windows_recompute"],[5])
        self.assertEqual(x["timeframes"]["M5"]["numerical_bar_windows_recompute"],[15,16])
    def test_15_metadata_does_not_recompute_price_or_ema_atr(self):
        x=self.plan(ChangeKind.LINEAGE_ONLY)
        for tf in TIMEFRAMES:
            self.assertEqual(x["timeframes"][tf]["numerical_bar_windows_recompute"],[])
            self.assertEqual(x["timeframes"][tf]["causal_indicator_checkpoints_recompute"],[])
        self.assertEqual(x["metadata_lineage_changed_indices"],[15])
        self.assertTrue(x["lineage_audit_update_required"])
    def test_16_unknown_source_quarantines_all_155_windows(self):
        x=self.plan(ChangeKind.UNQUALIFIED_SOURCE)
        self.assertEqual(sum(len(v["quarantined_window_ordinals"]) for v in x["timeframes"].values()),155)
        self.assertTrue(all(v["independent_earlier_indicator_checkpoints_reusable_count"]==0 for v in x["timeframes"].values()))
    def test_17_unchanged_no_numeric_work_or_history_revision(self):
        x=self.plan(ChangeKind.UNCHANGED,())
        self.assertFalse(x["lineage_audit_update_required"])
        self.assertFalse(any(v["numerical_bar_windows_recompute"] for v in x["timeframes"].values()))
    def test_18_live_market_never_authorized(self):
        x=self.plan()
        for field in ("numeric_indicators_actually_recomputed","provider_published_first_known_verified",
                      "official_vn_calendar_and_auction_finality_verified","authorized_real_higher_tf_source_data",
                      "real_drive_cache_read_write_performed","remote_multiwriter_cas_or_protected_floor_verified",
                      "production_reuse_or_trading_allowed"):
            self.assertFalse(x[field],field)
    def test_19_changed_policy_binding_denied(self):
        with self.assertRaisesRegex(PermissionError,"CROSS_RIGHTS_OR_POLICY"):
            self.plan(full_policy_binding="f"*64)
    def test_20_changed_calendar_fingerprint_denied(self):
        old=self.grid.scope.scope.legacy
        newer=replace(old,calendar_version="FAKE.NEW.CALENDAR")
        with self.assertRaisesRegex(PermissionError,"FOREIGN_RIGHTS"):
            self.grid_with(scope=FullPolicyFixture(fixture_scope(newer)))
    def test_21_changed_rights_fingerprint_denied(self):
        old=self.grid.scope.scope.legacy
        newer=replace(old,source_rights_policy_version="RIGHTS.REVOKED")
        with self.assertRaisesRegex(PermissionError,"FOREIGN_RIGHTS"):
            self.grid_with(scope=FullPolicyFixture(fixture_scope(newer)))
    def test_22_missing_tf_window_denied(self):
        with self.assertRaisesRegex(ValueError,"INCOMPLETE_SIX_TF"):
            self.grid_with(windows=self.grid.windows[:-1])
    def test_23_duplicate_window_denied(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE_TIMEFRAME"):
            self.grid_with(windows=self.grid.windows+(self.grid.windows[0],))
    def test_24_changed_m5_membership_denied(self):
        with self.assertRaisesRegex(ValueError,"MISSING_OVERLAPPING"):
            self.grid_with(windows=self.mutated_window(98,source_m5=(0,1,2)))
    def test_25_m5_member_outside_fake_day_denied(self):
        with self.assertRaisesRegex(ValueError,"MISSING_OVERLAPPING"):
            self.grid_with(windows=self.mutated_window(0,source_m5=(96,)))
    def test_26_wrong_time_window_start_denied(self):
        with self.assertRaisesRegex(ValueError,"WINDOW_START_END"):
            self.grid_with(windows=self.mutated_window(0,start_utc=self.grid.windows[0].start_utc+timedelta(minutes=1)))
    def test_27_wrong_time_window_end_denied(self):
        with self.assertRaisesRegex(ValueError,"WINDOW_START_END"):
            self.grid_with(windows=self.mutated_window(0,end_utc=self.grid.windows[0].end_utc+timedelta(minutes=1)))
    def test_28_open_bar_denied(self):
        with self.assertRaisesRegex(PermissionError,"OPEN_OR_INCOMPLETE"):
            replace(self.grid.windows[0],closed=False)
    def test_29_incomplete_bar_denied(self):
        with self.assertRaisesRegex(PermissionError,"OPEN_OR_INCOMPLETE"):
            replace(self.grid.windows[0],scope_complete=False)
    def test_30_unofficial_calendar_cannot_be_marked_official(self):
        with self.assertRaisesRegex(PermissionError,"VENDOR_SESSION_CALENDAR"):
            self.grid_with(fixture_vendor_calendar_verified=True)
    def test_31_non_eight_hour_fake_day_denied(self):
        with self.assertRaisesRegex(ValueError,"ONLY_EXPLICIT_ARTIFICIAL"):
            self.grid_with(artificial_session_end_utc=self.grid.artificial_session_end_utc-timedelta(minutes=5))
    def test_32_source_change_before_declared_close_denied(self):
        prior=self.grid.artificial_session_end_utc-timedelta(minutes=1)
        with self.assertRaisesRegex(PermissionError,"CHANGE_EARLIER"):
            self.plan(prior_as_of_utc=prior,first_known_utc=prior+timedelta(seconds=1),as_of_utc=prior+timedelta(seconds=2))
    def test_33_future_first_known_denied(self):
        ev=self.event
        with self.assertRaisesRegex(ValueError,"CAUSAL_FIRST_KNOWN"):
            replace(ev,first_known_utc=ev.as_of_utc+timedelta(minutes=1))
    def test_34_source_early_first_known_denied(self):
        ev=self.event
        with self.assertRaisesRegex(ValueError,"CAUSAL_FIRST_KNOWN"):
            replace(ev,first_known_utc=ev.prior_as_of_utc)
    def test_35_source_duplicate_indices_denied(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE_CHANGED"):
            self.plan(indices=(15,15))
    def test_36_bool_source_index_denied(self):
        with self.assertRaisesRegex(TypeError,"TYPED_EXPLICIT_M5"):
            self.plan(indices=(True,))
    def test_37_negative_source_index_denied(self):
        with self.assertRaisesRegex(ValueError,"OUT_OF_ARTIFICIAL"):
            self.plan(indices=(-1,))
    def test_38_large_source_index_denied(self):
        with self.assertRaisesRegex(ValueError,"OUT_OF_ARTIFICIAL"):
            self.plan(indices=(96,))
    def test_39_price_revision_without_changed_source_denied(self):
        with self.assertRaisesRegex(ValueError,"EXPLICIT_CHANGED"):
            self.plan(indices=())
    def test_40_unchanged_but_changed_source_denied(self):
        with self.assertRaisesRegex(ValueError,"UNCHANGED_CANNOT"):
            self.plan(ChangeKind.UNCHANGED,indices=(15,))
    def test_41_untyped_kind_denied(self):
        with self.assertRaisesRegex(TypeError,"EXPLICIT_SOURCE_CHANGE"):
            replace(self.event,kind="PRICE_VOLUME_REVISION")
    def test_42_naive_clock_denied(self):
        with self.assertRaises((TypeError,ValueError)):
            self.plan(as_of_utc=datetime(2020,1,1))
    def test_43_m5_aggregate_fixtures_are_not_vendor_source_bars(self):
        x=self.plan()
        self.assertTrue(x["artificial_day_is_not_official_vn_d1"])
        self.assertFalse(x["official_vn_calendar_and_auction_finality_verified"])
        self.assertEqual(FAKE_MEMBERS_PER_WINDOW["D1"],96)
    def test_44_repeatable_receipt_four_scenarios(self):
        self.assertEqual(build_receipt(),build_receipt())
        receipt=build_receipt()
        self.assertEqual(receipt["schema"],SCHEMA)
        self.assertEqual(receipt["status"],STATUS)
        self.assertEqual(receipt["six_tf_total_artificial_closed_windows"],155)
        self.assertTrue(receipt["release_and_trading_no_go"])
