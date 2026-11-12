"""A02 real dynamic V1 execution footprint across eight inherited test suites.

This is coverage *evidence*, not 1:1 behavioral parity or owner approval.
Eight existing synthetic A02 unittest suites execute in isolated GitHub-hosted
child processes; sys.settrace records Python calls and executed distinct lines
for the ORIGINAL 63 inherited V1 modules. Not a new trading code path.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import redirect_stdout, redirect_stderr
from hashlib import sha256
from io import StringIO
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import unittest

from scripts.m2_a02_63_owner_evidence_matrix import PACKETS
from scripts.mst_remote_legacy_tree_lock import _ALLOWED_V2_PATHS

SCHEMA = "mst.a02.v1-63.dynamic-trace-scope.synthetic-readonly.v1"
ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "swing_trading"
PATH_PREFIX = "src/swing_trading/"
BATCHES = tuple(x[0] for x in PACKETS)
NO_GO = (
    "full_behavioral_parity_certified", "owner_63_dispositions_approved",
    "real_vendor_source_or_license_verified", "production_drive_cache_verified",
    "external_witness_and_nonresettable_floor_verified",
    "production_release_authorized", "trading_authorized",
)


def original_paths() -> tuple[str, ...]:
    all_python = {
        PATH_PREFIX + x.name for x in PACKAGE.glob("*.py") if x.is_file()
    }
    files = tuple(sorted(all_python - _ALLOWED_V2_PATHS))
    if len(all_python) != 71 or len(files) != 63 or len(all_python & _ALLOWED_V2_PATHS) != 8:
        raise ValueError("ORIGINAL_63_PLUS_8_V2_SOURCE_SET_DRIFT")
    if PATH_PREFIX + "__init__.py" not in files:
        raise ValueError("ORIGINAL_PACKAGE_IMPORT_METADATA_MISSING")
    return files


def _synthetic_no_network():
    """No network may be initiated by these selected fixture suites."""
    def blocked(*args, **kwargs):
        raise PermissionError("A02_DYNAMIC_AUDIT_NETWORK_DENIED")
    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
    socket.create_connection = blocked


def run_child(batch: str) -> dict:
    packet = next((x for x in PACKETS if x[0] == batch), None)
    if packet is None:
        raise ValueError("UNKNOWN_A02_ORIGINAL_BATCH")
    pattern = "test_" + packet[1] + ".py"
    files = original_paths()
    by_abs = {str((ROOT / x).resolve()): x for x in files}
    seen = set()
    invoked = defaultdict(set)
    executed = defaultdict(set)
    calls = Counter()

    def trace(frame, event, arg):
        path = by_abs.get(frame.f_code.co_filename)
        if path:
            seen.add(path)
            if event == "call" and frame.f_code.co_name != "<module>":
                invoked[path].add(frame.f_code.co_name)
                calls[path] += 1
            if event == "line":
                executed[path].add(frame.f_lineno)
        return trace

    _synthetic_no_network()
    buff = StringIO()
    old = sys.gettrace()
    try:
        sys.settrace(trace)
        with redirect_stdout(buff), redirect_stderr(buff):
            suite = unittest.defaultTestLoader.discover(
                start_dir=str(ROOT / "tests"), pattern=pattern,
                top_level_dir=str(ROOT / "tests"))
            result = unittest.TextTestRunner(stream=buff, verbosity=0).run(suite)
    finally:
        sys.settrace(old)
    if (result.testsRun < packet[3] or result.failures or result.errors
        or result.skipped or result.expectedFailures or result.unexpectedSuccesses):
        # Tests/fixtures are CI inputs; print no raw logs or test output.
        raise AssertionError("A02_BATCH_TESTS_FAILED_OR_MINIMUM_DRIFT_" + batch)
    return {
        "batch": batch,
        "tests_passed": result.testsRun,
        "module_import_or_line_events": sorted(seen),
        "v1_module_call_counts": {p: calls[p] for p in sorted(invoked)},
        "v1_function_name_counts": {p: len(invoked[p]) for p in sorted(invoked)},
        "v1_executed_distinct_line_counts": {p: len(executed[p]) for p in sorted(executed)},
        "source_or_owner_authority": False,
    }


def audit(rows: list[dict], files: tuple[str, ...]) -> dict:
    """Checks complete 8-suite, 63 V1 report. No module claims full parity."""
    if type(rows) is not list or len(rows) != len(PACKETS):
        raise ValueError("EXACT_EIGHT_A02_SUITE_RECEIPTS_REQUIRED")
    if type(files) is not tuple or len(files) != 63 or len(set(files)) != 63:
        raise ValueError("EXACT_63_ORIGINAL_PATHS_REQUIRED")
    if any(type(x) is not str or not x.startswith(PATH_PREFIX)
           or x in _ALLOWED_V2_PATHS for x in files):
        raise ValueError("NON_ORIGINAL_V1_PATH_ATTEMPT")
    counter = Counter()
    unique_functions = Counter()
    positive_line_modules = set()
    observed_modules = set()
    per_batch = []
    for row, (batch, _, _, minimum) in zip(rows, PACKETS):
        if type(row) is not dict or set(row) != {
            "batch", "tests_passed", "module_import_or_line_events",
            "v1_module_call_counts", "v1_function_name_counts",
            "v1_executed_distinct_line_counts", "source_or_owner_authority",
        } or row["batch"] != batch:
            raise ValueError("A02_EXECUTION_BATCH_OR_FIELDS_DRIFT")
        if type(row["tests_passed"]) is not int or row["tests_passed"] < minimum:
            raise ValueError("A02_UNIT_SUITE_SUCCESS_REQUIRED")
        if row["source_or_owner_authority"] is not False:
            raise PermissionError("NO_SOURCE_OR_OWNER_AUTHORITY_FROM_TEST")
        for k in ("v1_module_call_counts", "v1_function_name_counts",
                  "v1_executed_distinct_line_counts"):
            obj = row[k]
            if type(obj) is not dict or not set(obj).issubset(files):
                raise ValueError("A02_EXECUTION_COUNTS_UNKNOWN_V1_FILE")
            if any(type(v) is not int or v < 1 for v in obj.values()):
                raise ValueError("A02_EXECUTION_COUNTS_MUST_BE_POSITIVE_INTS")
        if type(row["module_import_or_line_events"]) is not list or any(
                f not in files for f in row["module_import_or_line_events"]):
            raise ValueError("A02_IMPORTED_PATH_OUT_OF_BOUND")
        if not set(row["v1_module_call_counts"]).issubset(
                row["v1_executed_distinct_line_counts"]):
            raise ValueError("V1_FUNCTION_CALLS_WITHOUT_EXECUTED_LINES")
        observed_modules.update(row["module_import_or_line_events"])
        positive_line_modules.update(row["v1_executed_distinct_line_counts"])
        counter.update(row["v1_module_call_counts"])
        unique_functions.update(row["v1_function_name_counts"])
        per_batch.append({
            "batch":batch, "tests_passed":row["tests_passed"],
            "original_v1_paths_with_function_calls":
                len(row["v1_module_call_counts"]),
            "original_v1_paths_with_execution_lines":
                len(row["v1_executed_distinct_line_counts"]),
            "owner_signed":False,
        })
    fn_paths = set(counter)
    metadata = PATH_PREFIX + "__init__.py"
    module_status = []
    for path in files:
        state = ("FUNCTION_CALLED_IN_SELECTED_EIGHT_SUITES" if path in fn_paths
                 else "IMPORT_OR_MODULE_LEVEL_ONLY" if path in observed_modules
                 else "NOT_OBSERVED_IN_SELECTED_SUITES")
        if path == metadata:
            state = "PACKAGE_INIT_METADATA_ONLY_NO_DOMAIN_CLAIM"
        module_status.append({
            "path":path, "classification":state,
            "function_call_events":counter[path],
            "distinct_function_name_count_sum_across_batches":
                unique_functions[path],
            "source_byte_parity_checked_separately":True,
            "full_behavioral_certification":False,
            "owner_signed":False,
        })
    receipt = {
        "schema": SCHEMA,
        "status":"SCOPED_DYNAMIC_PYTHON_EXECUTION_ONLY_NO_PARITY_OR_OWNER_AUTHORITY",
        "original_v1_count":len(files),
        "v2_excluded_count":len(_ALLOWED_V2_PATHS),
        "selected_a02_batches":len(PACKETS),
        "selected_a02_unit_tests_passed":sum(x["tests_passed"] for x in per_batch),
        "v1_modules_with_python_function_call":len(fn_paths),
        "v1_modules_with_any_import_or_line_event":len(observed_modules),
        "v1_modules_with_executed_source_lines":len(positive_line_modules),
        "v1_modules_without_traceable_calls":len(set(files)-fn_paths),
        "v1_modules_not_seen_under_selected_suites":len(set(files)-observed_modules),
        "per_batch":per_batch,
        "original_modules":module_status,
        "limits":[
            "CPython sys.settrace observed this exact synthetic eight-suite process only",
            "Call events and lines do not measure all branches, async tasks, all possible runtime behaviors, or independent expected results",
            "Imported module code and helper-only functions are not full 1-to-1 behavior parity",
            "CPython C extensions and untraced external processes excluded",
            "Network disabled for fixture subprocess, no vendor feed or real data",
        ],
        **{k:False for k in NO_GO},
    }
    payload=json.dumps(receipt,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    receipt["synthetic_trace_report_sha256"]=sha256(payload.encode("ascii")).hexdigest()
    return receipt


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--batch", choices=BATCHES)
    parser.add_argument("--out", type=Path)
    args=parser.parse_args(argv)
    if args.child:
        if not args.batch:
            raise ValueError("CHILD_BATCH_REQUIRED")
        print(json.dumps(run_child(args.batch),sort_keys=True))
        return
    originals=original_paths()
    observations=[]
    for batch in BATCHES:
        env=dict(os.environ)
        env["PYTHONPATH"]=str(ROOT/"tests")+os.pathsep+env.get("PYTHONPATH","")
        result=subprocess.run([sys.executable, "-m",
            "scripts.m2_a02_dynamic_execution_footprint_audit",
            "--child","--batch",batch],cwd=ROOT,env=env,
            capture_output=True,text=True,timeout=180,check=False)
        if result.returncode != 0:
            raise AssertionError("A02_ORIGINAL_TEST_BATCH_NOT_PASSED_"+batch)
        try:
            observations.append(json.loads(result.stdout.strip()))
        except (json.JSONDecodeError,TypeError) as ex:
            raise ValueError("A02_CHILD_RECEIPT_INVALID_"+batch) from ex
    receipt=audit(observations,originals)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",
                            encoding="utf-8")
    print(json.dumps({k:v for k,v in receipt.items()
        if k not in ("original_modules","per_batch")},sort_keys=True))


if __name__=="__main__":
    main()
