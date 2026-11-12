"""A02 dynamic executed footprint: aggregation integrity and untrusted receipt guard."""
from copy import deepcopy
import unittest

from scripts import m2_a02_dynamic_execution_footprint_audit as a


class DynamicA02ExecutionFootprintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files=a.original_paths()
        cls.first=cls.files[0]
        cls.second=cls.files[1]
        cls.rows=[]
        for batch,_,_,minimum in a.PACKETS:
            cls.rows.append({
                "batch":batch, "tests_passed":minimum,
                "module_import_or_line_events":[cls.first,cls.second],
                "v1_module_call_counts":{cls.second:3},
                "v1_function_name_counts":{cls.second:2},
                "v1_executed_distinct_line_counts":{cls.second:5},
                "source_or_owner_authority":False,
            })
        cls.ok=a.audit(cls.rows,cls.files)

    def _alter(self,func,errors=(ValueError,PermissionError,TypeError)):
        rows=deepcopy(self.rows)
        func(rows)
        with self.assertRaises(errors):
            a.audit(rows,self.files)

    def test_01_exact_v1_count(self):
        self.assertEqual(len(self.files),63)

    def test_02_exact_v2_excluded(self):
        self.assertEqual(self.ok["v2_excluded_count"],8)

    def test_03_eight_test_groups(self):
        self.assertEqual(self.ok["selected_a02_batches"],8)

    def test_04_direct_counter_does_not_imply_full_parity(self):
        self.assertFalse(self.ok["full_behavioral_parity_certified"])

    def test_05_owner_status_unapproved(self):
        self.assertFalse(self.ok["owner_63_dispositions_approved"])

    def test_06_no_trading(self):
        self.assertFalse(self.ok["trading_authorized"])

    def test_07_synthetic_no_vendor_license(self):
        self.assertFalse(self.ok["real_vendor_source_or_license_verified"])

    def test_08_exact_eight_source_counter(self):
        self.assertEqual(self.ok["v1_modules_with_python_function_call"],1)

    def test_09_original_other_modules_not_implied_runtime(self):
        self.assertEqual(self.ok["v1_modules_without_traceable_calls"],62)

    def test_10_report_63_rows(self):
        self.assertEqual(len(self.ok["original_modules"]),63)

    def test_11_all_modules_not_owner_signed(self):
        self.assertTrue(all(not x["owner_signed"] for x in self.ok["original_modules"]))

    def test_12_missing_batch_denied(self):
        with self.assertRaises(ValueError):
            a.audit(self.rows[:-1],self.files)

    def test_13_swapped_batches_denied(self):
        self._alter(lambda x:x.reverse())

    def test_14_below_minimum_test_count_denied(self):
        self._alter(lambda x:x[0].__setitem__("tests_passed",1))

    def test_15_fake_source_or_owner_authority_denied(self):
        self._alter(lambda x:x[0].__setitem__("source_or_owner_authority",True))

    def test_16_missing_count_fields_denied(self):
        self._alter(lambda x:x[0].pop("v1_module_call_counts"))

    def test_17_unknown_python_file_path_denied(self):
        self._alter(lambda x:x[0]["v1_module_call_counts"].__setitem__(
            "src/swing_trading/this_is_not_original.py",1))

    def test_18_zero_function_count_denied(self):
        self._alter(lambda x:x[0]["v1_module_call_counts"].__setitem__(
            self.second,0))

    def test_19_boolean_count_denied(self):
        self._alter(lambda x:x[0]["v1_module_call_counts"].__setitem__(
            self.second,True))

    def test_20_function_without_line_coverage_denied(self):
        self._alter(lambda x:x[0]["v1_executed_distinct_line_counts"].clear())

    def test_21_v2_path_in_original_set_denied(self):
        x=(*self.files[:-1],"src/swing_trading/v2_cache_partition_plan.py")
        with self.assertRaises(ValueError):
            a.audit(self.rows,x)

    def test_22_duplicate_original_path_denied(self):
        x=self.files[:-1]+(self.files[0],)
        with self.assertRaises(ValueError):
            a.audit(self.rows,x)

    def test_23_import_event_not_called_remains_distinct(self):
        item=next(x for x in self.ok["original_modules"] if x["path"]==self.first)
        if self.first!="src/swing_trading/__init__.py":
            self.assertEqual(item["classification"],"IMPORT_OR_MODULE_LEVEL_ONLY")

    def test_24_sha_index_is_metadata_only(self):
        self.assertEqual(len(self.ok["synthetic_trace_report_sha256"]),64)
        self.assertFalse(self.ok["external_witness_and_nonresettable_floor_verified"])
