"""A02 evidence sufficiency matrix regression: NOT human/module approvals."""
import csv
from io import StringIO
import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import m2_a02_63_owner_evidence_matrix as m


class OriginalV1OwnerEvidenceMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=m.build()
        cls.rows=cls.report["modules"]
        cls.by_name={r["module"]:r for r in cls.rows}

    def test_01_schema_is_explicit_no_owner_signoff(self):
        self.assertEqual(self.report["schema"],m.SCHEMA)
        self.assertIn("NOT_SIGNED",self.report["status"])

    def test_02_exactly_63_original_rows(self):
        self.assertEqual(len(self.rows),63)

    def test_03_unique_and_sorted_names(self):
        names=[x["module"] for x in self.rows]
        self.assertEqual(len(names),len(set(names)))
        self.assertEqual(names,sorted(names))

    def test_04_all_originals_in_eight_checked_in_QA_packets(self):
        self.assertEqual(len(self.report["packets"]),8)
        self.assertEqual(sum(len(x["members"]) for x in self.report["packets"]),63)
        self.assertEqual([len(x["members"]) for x in self.report["packets"]],
                         [8,8,8,8,8,8,8,7])

    def test_05_one_unique_packet_per_original_file(self):
        member_to_batch={}
        for p in self.report["packets"]:
            for module in p["members"]:
                self.assertNotIn(module,member_to_batch)
                member_to_batch[module]=p["batch"]
        self.assertEqual(set(member_to_batch),set(self.by_name))
        for name,row in self.by_name.items():
            self.assertEqual(row["batch"],member_to_batch[name])

    def test_06_exact_zero_owner_signatures(self):
        self.assertEqual(self.report["owner_signed"],0)
        self.assertTrue(all(r["human_owner_disposition"]=="NOT_SIGNED" for r in self.rows))

    def test_07_no_module_full_behavior_certification(self):
        self.assertEqual(self.report["full_behavior_acceptances"],0)
        self.assertTrue(all(not r["complete_behavior_certified"] for r in self.rows))

    def test_08_zero_owner_ABI_or_behavior_acceptance(self):
        self.assertTrue(all(not r["owner_abi_approved"] and not r["owner_behavior_approved"]
                            for r in self.rows))
        self.assertFalse(self.report["a03_full_v1_v2_behavior_certified"])

    def test_09_full_original_sha256_and_static_ABI_hash(self):
        for row in self.rows:
            with self.subTest(module=row["module"]):
                self.assertRegex(row["source_sha256"],r"^[0-9a-f]{64}$")
                self.assertRegex(row["static_abi_sha256"],r"^[0-9a-f]{64}$")

    def test_10_provisional_keep_improve_not_owner_vote(self):
        self.assertEqual({x["h3_proposal_NOT_owner_decision"] for x in self.rows},
                         {"KEEP","IMPROVE"})
        self.assertTrue(all(x["human_owner_disposition"]=="NOT_SIGNED" for x in self.rows))

    def test_11_init_only_import_and_metadata(self):
        row=self.by_name["__init__"]
        self.assertEqual(row["coverage_scope"],"PACKAGE_IMPORT_METADATA_ONLY")
        self.assertEqual(row["batch"],"B08")
        self.assertEqual(self.report["init_only_import_metadata_paths"],1)

    def test_12_all_other_62_have_selected_original_synthetic_calls(self):
        self.assertEqual(self.report["original_domain_file_paths_with_selected_tests"],62)
        self.assertTrue(all(r["coverage_scope"]=="SELECTED_SYNTHETIC_ACTUAL_V1_FUNCTION_CALLS"
                            for r in self.rows if r["module"]!="__init__"))

    def test_13_all_evidence_files_exist(self):
        for r in self.rows:
            with self.subTest(module=r["module"]):
                for k in ("source_path","source_lab","tests","qa_report","workflow"):
                    self.assertTrue((m.ROOT/r[k]).is_file(),(k,r["module"]))

    def test_14_40_or_more_test_methods_is_batch_total_not_per_module(self):
        for r in self.rows:
            self.assertGreaterEqual(r["packet_test_method_count_not_per_module"],40)

    def test_15_all_outside_security_and_release_gates_open(self):
        self.assertTrue(all(r["outside_gates"]=="OA01-OA06_OPEN_AND_G01-G08_OPEN"
                            and not r["production_authorized"] and not r["trading_authorized"]
                            for r in self.rows))

    def test_16_external_authorities_never_claimed(self):
        for key in ("real_vendor_licence_verified","physical_google_drive_market_cache_certified",
                    "security_g01_g08_independently_closed","production_authorized",
                    "trading_authorized"):
            self.assertIs(self.report[key],False)

    def test_17_immutable_original_source_pin_is_present(self):
        self.assertEqual(self.report["upstream_pin"],
                         "cd90c1babae8912db31490ad614fc2ad2f868042")
        self.assertEqual(self.report["protected_main_pin"],
                         "4048f91beaaa3410116d97e35896c8b688384e19")

    def test_18_live_source_byte_lock_is_separate_from_static_builder(self):
        self.assertTrue(self.report["real_remote_upstream_main_pr_git_tree_lock_runs_separately"])

    def test_19_real_v2_direct_import_mapping_is_syntactic_not_parity(self):
        for r in self.rows:
            self.assertIsInstance(r["direct_v2_importers"],list)
            self.assertTrue(all(s in m.SIDECARS for s in r["direct_v2_importers"]))
            self.assertIn(r["v2_mapping_status"],(
                "DIRECT_STATIC_IMPORT_REQUIRES_FULL_ABI_BEHAVIOR_TEST",
                "NO_DIRECT_IMPORT_FOUND_TRANSITIVE_MAPPING_NOT_PROVEN"))

    def test_20_specific_replay_and_contract_legacy_gaps_retained(self):
        self.assertIn("ReplayClock.as_of_utc",self.by_name["replay"]["unresolved_evidence"])
        self.assertIn("Evidence.verified",self.by_name["contracts"]["unresolved_evidence"])

    def test_21_missing_rvol_real_calendar_and_volume_claims(self):
        x=self.by_name["rvol_tod_contract"]["unresolved_evidence"]
        self.assertIn("20 prior same-local-slot",x)
        self.assertIn("official trading calendar",x)

    def test_22_63_markdown_rows_preserve_NOT_SIGNED_and_qa_links(self):
        text=m.markdown(self.report)
        rows=[x for x in text.splitlines() if x.rstrip().endswith("| NOT_SIGNED |")]
        self.assertEqual(len(rows),63)
        self.assertIn("IMPORT/METADATA ONLY",text)
        self.assertIn("[QA](",text)

    def test_23_csv_is_63_rows_with_explicit_no_go_fields(self):
        records=list(csv.DictReader(StringIO(m.csv_text(self.report))))
        self.assertEqual(len(records),63)
        self.assertTrue(all(x["human_owner_disposition"]=="NOT_SIGNED" for x in records))

    def test_24_deterministic_evidence_matrix_sha(self):
        again=m.build()
        self.assertEqual(again["module_evidence_fingerprint"],
                         self.report["module_evidence_fingerprint"])
        self.assertEqual(again["static_abi_inventory_fingerprint"],
                         self.report["static_abi_inventory_fingerprint"])

    def test_25_duplicate_original_in_two_tranches_denied(self):
        packets=list(m.PACKETS)
        packets[1]=(packets[1][0],packets[0][1],packets[1][2],packets[1][3])
        with patch.object(m,"PACKETS",tuple(packets)):
            with self.assertRaisesRegex(ValueError,"SAME_ORIGINAL_IN_TWO_QA_BATCHES"):
                m.read_evidence_packets()

    def test_26_missing_QA_document_is_denied(self):
        documents=list(m.QA_DOCS)
        documents[7]="DOES_NOT_EXIST_QA.md"
        with patch.object(m,"QA_DOCS",tuple(documents)):
            with self.assertRaisesRegex(ValueError,"EVIDENCE_FILE_MISSING"):
                m.read_evidence_packets()

    def test_27_zero_real_test_methods_denied(self):
        with patch.object(m,"checked_in_test_count",return_value=0):
            with self.assertRaisesRegex(ValueError,"TEST_COUNT_TOO_LOW"):
                m.read_evidence_packets()

    def test_28_tranche_invalid_constant_or_duplicate_detected(self):
        with TemporaryDirectory() as tmp:
            f=Path(tmp)/"lab.py"
            f.write_text("EIGHT=('replay','replay')\n",encoding="utf-8")
            self.assertEqual(m.literal_module_tuple(f,"EIGHT"),
                             ("replay","replay"))
            with self.assertRaisesRegex(ValueError,"TRANCHE_DECLARATION_INVALID"):
                m.literal_module_tuple(f,"FILES")

    def test_29_generated_reviewer_matrix_is_JSON_serializable(self):
        data=json.dumps(self.report,sort_keys=True)
        self.assertEqual(len(json.loads(data)["modules"]),63)

    def test_30_one_checkout_contains_63_V1_plus_eight_opt_in_V2(self):
        self.assertEqual(self.report["h3_ast_modules"],63)
        files={p.stem for p in (m.ROOT/"src"/"swing_trading").glob("*.py")}
        self.assertEqual(len(files),71)
        self.assertEqual(len(files-set(m.SIDECARS)),63)


    def test_31_published_63_row_review_index_exists(self):
        p=m.ROOT/"docs"/"MST_A02_63_ORIGINAL_V1_OWNER_EVIDENCE_MATRIX_20261110.md"
        self.assertTrue(p.is_file())

    def test_32_published_index_contains_exact_63_unsigned_module_rows(self):
        src=(m.ROOT/"docs"/"MST_A02_63_ORIGINAL_V1_OWNER_EVIDENCE_MATRIX_20261110.md").read_text()
        index=[line for line in src.splitlines() if re.match(r"^\| \d+ \|",line)]
        self.assertEqual(len(index),63)
        self.assertTrue(all(line.endswith("| **NOT_SIGNED** |") for line in index))

    def test_33_published_index_module_membership_matches_AST(self):
        src=(m.ROOT/"docs"/"MST_A02_63_ORIGINAL_V1_OWNER_EVIDENCE_MATRIX_20261110.md").read_text()
        index=[line for line in src.splitlines() if re.match(r"^\| \d+ \|",line)]
        for r in self.rows:
            with self.subTest(module=r["module"]):
                path="src/swing_trading/"+r["module"]+".py"
                self.assertEqual(sum("("+("../"+path)+")" in line for line in index),1)

    def test_34_published_index_fingerprints_match_generated_inventory(self):
        src=(m.ROOT/"docs"/"MST_A02_63_ORIGINAL_V1_OWNER_EVIDENCE_MATRIX_20261110.md").read_text()
        self.assertIn(self.report["module_evidence_fingerprint"],src)
        self.assertIn(self.report["static_abi_inventory_fingerprint"],src)

    def test_35_published_evidence_does_not_approve_owner_or_trade(self):
        src=(m.ROOT/"docs"/"MST_A02_63_ORIGINAL_V1_OWNER_EVIDENCE_MATRIX_20261110.md").read_text()
        self.assertIn("A02 owner closure 0/63",src)
        self.assertIn("G01–G08 OPEN",src)
        self.assertIn("IMPORT/METADATA ONLY",src)
        self.assertNotIn("OWNER APPROVED 63/63",src)

if __name__=="__main__":
    unittest.main()
