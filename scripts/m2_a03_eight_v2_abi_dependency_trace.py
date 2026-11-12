"""MST A03: explicit 8 V2 sidecar -> original 63 V1 ABI/dependency trace.

This is an evidence map plus the ALREADY EXISTING bounded 128-case real
V1/V2 UNVERIFIED replay differential, not full public ABI interchangeability
or owner signoff. Direct and transitive imports are syntactic AST edges only.
The two deliberately stricter V2 legacy boundaries are runtime-demonstrated
and held OPEN for owner transition approval, never automatically patched.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from scripts.m2_a02_63_owner_evidence_matrix import ROOT, SIDECARS, build as build_a02
from scripts.m2_a02_legacy_63_interface_review import module_static_api, _digest
from scripts.m2_a03_behavior_equivalence_lab import run_behavior_matrix
from swing_trading.contracts import Evidence
from swing_trading.replay import ReplayClock
from swing_trading.strict_contract_v2 import StrictReplayClockV2, StrictEvidenceV2

SCHEMA="mst.a03.eight-v2-source-abi-transitive-trace-unapproved.v1"
TIME=datetime(2026,11,9,tzinfo=timezone.utc)
DIVERGENCES=(
  {"v1":"replay.ReplayClock.as_of_utc","v2":"strict_contract_v2.StrictReplayClockV2.as_of_utc",
   "classification":"INTENTIONAL_STRICTER_NON_INTERCHANGEABLE",
   "migration_requirement":"explicit opt-in/fail-closed adapter, transitive callers and rollback tested; owner approval required"},
  {"v1":"contracts.Evidence.verified","v2":"strict_contract_v2.StrictEvidenceV2.verified",
   "classification":"INTENTIONAL_STRICTER_NON_INTERCHANGEABLE",
   "migration_requirement":"explicit nonbool legacy cleansing with no silent promotion; owner approval required"},
)

def package_graph(root=ROOT):
    folder=root/"src"/"swing_trading"
    names={p.stem for p in folder.glob("*.py")}
    if len(names)!=71:
        raise ValueError("A03_SOURCE_PACKAGE_NOT_63_V1_8_V2")
    graph={}
    for name in names:
        path=folder/(name+".py")
        tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
        imports=set()
        for n in ast.walk(tree):
            if isinstance(n,ast.ImportFrom) and n.level==1:
                candidates=[n.module.split(".")[0]] if n.module else [a.name.split(".")[0] for a in n.names]
                for target in candidates:
                    if target in names and target!=name:
                        imports.add(target)
        graph[name]=tuple(sorted(imports))
    return graph

def reachable(graph,start):
    done=set();stack=list(graph[start])
    while stack:
        item=stack.pop()
        if item==start or item in done:
            continue
        done.add(item)
        stack.extend(graph[item])
    return sorted(done)

def divergence_runtime():
    old=ReplayClock(TIME);v2=StrictReplayClockV2(TIME)
    prior=TIME-timedelta(minutes=5)
    old.as_of_utc=prior
    if old.as_of_utc != prior:
        raise AssertionError("V1_DIRECT_ASSIGNMENT_LEGACY_SEMANTICS_CHANGED")
    prevented=False
    try:
        v2.as_of_utc=prior
    except ValueError:
        prevented=True
    if not prevented or v2.as_of_utc!=TIME:
        raise AssertionError("V2_REPLAY_REWIND_FALSELY_ALLOWED")
    permissive=Evidence("synthetic.fixture",TIME,1)
    if permissive.verified != 1 or type(permissive.verified) is not int:
        raise AssertionError("V1_LEGACY_TRUTHY_FLAG_CHANGED")
    strict=False
    try:
        StrictEvidenceV2("synthetic.fixture",TIME,1)
    except TypeError:
        strict=True
    if not strict:
        raise AssertionError("V2_NONBOOL_EVIDENCE_BECAME_TRUSTED")
    return {
        "v1_direct_clock_rewind_allowed":True,
        "v2_direct_clock_rewind_denied":True,
        "v1_truthy_nonbool_evidence_accepted":True,
        "v2_nonbool_evidence_denied":True,
        "intentional_breaks_need_explicit_owner_adapter":True,
    }

def build(root=ROOT, *, run_safe_fixture=True):
    a02=build_a02(root)
    originals={r["module"]:r for r in a02["modules"]}
    if len(originals)!=63 or len(SIDECARS)!=8 or set(SIDECARS)&set(originals):
        raise ValueError("A03_63_V1_8_V2_SCOPE_INVALID")
    graph=package_graph(root)
    if set(graph)!=set(originals)|set(SIDECARS):
        raise ValueError("A03_GRAPH_MODULE_IDENTITY_DRIFT")
    rows=[]
    for name in SIDECARS:
        path=root/"src"/"swing_trading"/(name+".py")
        src=path.read_text(encoding="utf-8")
        static=module_static_api(src,module_name=name)
        direct=[x for x in graph[name] if x in originals]
        linked=reachable(graph,name)
        transitive=[x for x in linked if x in originals and x not in direct]
        v2dep=[x for x in linked if x in SIDECARS]
        if len(direct)+len(transitive)!=len(set(direct+transitive)):
            raise ValueError("A03_DEPENDENCY_DUPLICATE_"+name)
        evidence=[{
          "original_v1_module":item,
          "original_static_abi_sha256":originals[item]["static_abi_sha256"],
          "a02_batch":originals[item]["batch"],
          "a02_evidence_scope":originals[item]["coverage_scope"],
          "owner_disposition":originals[item]["human_owner_disposition"],
        } for item in sorted(set(direct+transitive))]
        rows.append({
          "v2_module":name,
          "v2_source_path":"src/swing_trading/"+name+".py",
          "v2_source_sha256":__import__("hashlib").sha256(path.read_bytes()).hexdigest(),
          "v2_static_public_abi_sha256":static["interface_sha256"],
          "v2_public_function_count":static["public_function_count"],
          "v2_public_class_count":static["public_class_count"],
          "direct_original_v1_imports":direct,
          "transitive_original_v1_imports":transitive,
          "v2_sidecars_reachable":v2dep,
          "original_abi_evidence_dependencies":evidence,
          "static_import_graph_is_complete_behavior_call_graph":False,
          "legacy_v1_abi_interchangeable":False,
          "full_original_to_v2_behavior_parity_proven":False,
          "owner_a03_approved":False,
          "owner_review_required":"ABI signatures/field types, transitive runtime consumers, negative cases, rollback, source/data rights and signed approval",
          "external_security_gates":"G01_G08_AND_OA01_OA06_OPEN",
          "production_or_trading_authorized":False,
        })
    diff=divergence_runtime()
    baseline=run_behavior_matrix() if run_safe_fixture else None
    if baseline is not None and not (
        baseline["decision_comparisons"]==128
        and baseline["as_of_snapshots_checked"]==4
        and baseline["zones_checked"]==16
        and baseline["strategies_checked"]==2
        and baseline["signal_decisions_all_unverified"]
        and not baseline["full_v2_abi_interchangeability_approved"]
    ):
        raise AssertionError("A03_SAFE_V1_V2_SUBSET_DRIFT_OR_FALSE_APPROVAL")
    return {
      "schema":SCHEMA,
      "status":"EIGHT_V2_SIDECARS_TRACE_MAPPED_128_UNVERIFIED_ONLY_TWO_KNOWN_ABI_BREAKS_OWNER_NO_GO",
      "source_upstream_sha":a02["upstream_pin"],
      "protected_main_sha":a02["protected_main_pin"],
      "source_tree_sha":a02["original_tree_pin"],
      "original_v1_module_count":len(originals),
      "opt_in_v2_sidecar_count":len(rows),
      "direct_plus_transitive_graph_is_static_only":True,
      "v1_original_static_abi_inventory_fingerprint":a02["static_abi_inventory_fingerprint"],
      "a02_owner_signed_module_dispositions":a02["owner_signed"],
      "a03_owner_signed_abi_behavior_approvals":0,
      "a03_full_abi_and_behavior_interchangeability_proven":False,
      "legacy_contract_divergences":list(DIVERGENCES),
      "runtime_divergence_observations":diff,
      "prior_safe_unverified_fixture_differential":(
          {"comparisons":baseline["decision_comparisons"],
           "snapshots":baseline["as_of_snapshots_checked"],
           "zones":baseline["zones_checked"],
           "strategies":baseline["strategies_checked"],
           "fixture_matrix_sha256":baseline["fixture_matrix_sha256"]}
          if baseline else None),
      "full_v2_detector_formula_parity_proven":False,
      "real_provider_market_data_or_licence_proven":False,
      "real_google_drive_market_cache_or_distributed_cas_proven":False,
      "all_g01_g08_independent_security_gates_closed":False,
      "production_release_authorized":False,
      "trading_authorized":False,
      "v2_abi_trace_fingerprint":_digest([
          [r["v2_module"],r["v2_static_public_abi_sha256"],
           r["direct_original_v1_imports"],r["transitive_original_v1_imports"]]
          for r in rows]),
      "v2_sidecars":rows,
    }

def as_markdown(r):
    lines=[
      "# MST A03 — Eight opt-in V2 sidecars: original V1 static ABI/consumer trace and intentionally incompatible contracts",
      "",
      "**Status: 8/8 V2 sidecars mapped, not approved. A02 owner 0/63; A03 owner approvals 0/8.**",
      "Source graph is AST IMPORT syntax only, not a complete transitive runtime call graph or substitution proof. All V1/V2 original source files unchanged.",
      "Existing original V1 ↔ V2 differential proves only 128 UNVERIFIED decisions at four synthetic as-of snapshots, not live signals, detector formulas, source rights or full ABI equivalence.",
      "",
      "Original V1 ABI fingerprint: "+r["v1_original_static_abi_inventory_fingerprint"]+".",
      "V2 static trace fingerprint: "+r["v2_abi_trace_fingerprint"]+".",
      "",
      "| Opt-in V2 sidecar | Public ABI SHA256 prefix | V1 imports direct | V1 imports transitive (AST) | V2 internal sidecars reachable | Approval |",
      "|---|---|---|---|---|---|",
    ]
    for row in r["v2_sidecars"]:
        lines.append("| "+row["v2_module"]+" | "+row["v2_static_public_abi_sha256"][:16]
          +" | "+(", ".join(row["direct_original_v1_imports"]) or "none")
          +" | "+(", ".join(row["transitive_original_v1_imports"]) or "none")
          +" | "+(", ".join(row["v2_sidecars_reachable"]) or "none")
          +" | **NO-GO** |")
    lines+=["","## Intentional V1/V2 compatibility differences (REQUIRES HUMAN DECISION)","",
      "1. V1 ReplayClock directly allows as_of_utc rewind (legacy public-field API); StrictReplayClockV2 denies reverse assignment. Neither code path was changed.",
      "2. V1 Evidence.verified accepts truthy nonboolean 1; StrictEvidenceV2 rejects 1 with TypeError. Never auto-coerce a legacy proof to verified.",
      "",
      "These are KNOWN NON-INTERCHANGEABLE contracts; an explicit migration adapter, tests of transitive consumers, and separate owner acceptance are required.",
      "",
      "**All owner decisions, G01–G08, OA01–OA06, provider entitlements, Google Drive licensed physical market cache, release and trades remain NO-GO.**",""]
    return "\n".join(lines)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--json",type=Path)
    p.add_argument("--markdown",type=Path)
    args=p.parse_args(argv)
    d=build(args.root)
    for path,data in ((args.json,json.dumps(d,indent=2,sort_keys=True)+"\n"),
                       (args.markdown,as_markdown(d))):
        if path:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(data,encoding="utf-8")
    print(json.dumps({k:v for k,v in d.items() if k!="v2_sidecars"},sort_keys=True))

if __name__=="__main__":
    main()
