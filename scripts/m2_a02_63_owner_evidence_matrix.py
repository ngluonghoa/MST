"""MST A02 original 63-file evidence/owner-decision matrix (NO-GO).

Generate from REAL checked-in H3+AST V1 inventory and independently parse the
EIGHT original tranche scripts. All owner dispositions remain NOT_SIGNED.
The caller workflow MUST separately verify GitHub upstream/main/PR source bytes.
"""
from __future__ import annotations
import argparse
import ast
import csv
from io import StringIO
import json
from pathlib import Path
from scripts.m2_a02_legacy_63_interface_review import inventory, TARGET_COUNT, _digest

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="mst.a02.original-v1-63-owner-evidence-unapproved.v1"
PACKETS=(
    ("B01","m2_a02_eight_inherited_runtime_boundary_lab","m2-a02-eight-inherited-runtime-boundaries.yml",48),
    ("B02","m2_a02_source_custody_cache_eight_runtime_lab","m2-a02-source-custody-cache-eight-runtime.yml",42),
    ("B03","m2_a02_b5_causal_eight_runtime_lab","m2-a02-b5-causal-eight-runtime.yml",40),
    ("B04","m2_a02_fourth_eight_routing_calendar_runtime_lab","m2-a02-fourth-eight-routing-calendar-runtime.yml",40),
    ("B05","m2_a02_fifth_eight_source_semantics_runtime_lab","m2-a02-fifth-eight-source-semantics-runtime.yml",40),
    ("B06","m2_a02_sixth_eight_replay_evidence_migration_runtime_lab","m2-a02-sixth-eight-replay-evidence-migration-runtime.yml",40),
    ("B07","m2_a02_seventh_eight_engineering_custody_rollback_runtime_lab","m2-a02-seventh-eight-engineering-custody-rollback.yml",40),
    ("B08","m2_a02_final_seven_original_v1_runtime_lab","m2-a02-final-seven-original-v1-runtime.yml",40),
)
QA_DOCS=(
    "MST_A02_EIGHT_INHERITED_BEHAVIOR_QA_20261110.md",
    "MST_A02_SECOND_EIGHT_SOURCE_CUSTODY_RUNTIME_QA_20261110.md",
    "MST_A02_THIRD_EIGHT_B5_CAUSAL_RUNTIME_QA_20261110.md",
    "MST_A02_FOURTH_EIGHT_ROUTING_CALENDAR_QA_20261110.md",
    "MST_A02_FIFTH_EIGHT_SSI_DNSE_VCBS_QA_20261110.md",
    "MST_A02_SIXTH_EIGHT_REPLAY_EVIDENCE_MIGRATION_QA_20261110.md",
    "MST_A02_SEVENTH_EIGHT_ENGINEERING_CUSTODY_ROLLBACK_QA_20261110.md",
    "MST_A02_FINAL_SEVEN_ORIGINAL_V1_QA_20261110.md",
)
GAPS={
    "domain_and_reference":"official source/calendar, replay timing, complete decisions and out-of-sample behavior",
    "source_adapter_and_quality":"real licensed provider rights, retention, authenticated live endpoint data, freshness",
    "cache_and_persistence":"physical licensed Drive cache, external CAS/monotonic floor and cross-run recovery",
    "evidence_and_rights":"independent signer/custodian, lawful retention, witness/revocation freshness",
    "engineering_governance":"signed approved last-known-good, deployment authorization, rollback/settlement proof",
}
EXTRA={
    "replay":"V1 ReplayClock.as_of_utc public assignment permits rewind; V2 compatibility approval required",
    "contracts":"V1 Evidence.verified accepts nonboolean truthy values; V2 strictness approval required",
    "__init__":"package import/version/disclaimer ONLY, no domain behavior",
    "rvol_tod_contract":"20 prior same-local-slot sessions synthetic, no real official trading calendar/volume rights",
    "reference_checkpoint_signature":"caller-pinned Ed25519 fixture key is not enrolled external signer",
    "reference_checkpoint_mac":"self-held shared key is not independent custodian",
    "reference_offline_verified_archive":"offline metadata-only SQLite is not live WAL or production Drive cache",
    "cache_swap_preview":"two fake backends comparing equal does not authorize real migration",
    "vn_release_rollback":"T+2 settlement and independent LKG/restore approval not verified",
}
SIDECARS=(
 "strict_contract_v2","v2_cache_fencing_lab","v2_cache_partition_plan",
 "v2_cloud_publish_verify_lab","v2_cloud_ref_witness_plan",
 "v2_provider_readiness","v2_replay_port","v2_source_adapter",
)

def literal_module_tuple(path:Path,name:str):
    tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
    values=[]
    for stmt in tree.body:
        if isinstance(stmt,(ast.Assign,ast.AnnAssign)):
            targets=stmt.targets if isinstance(stmt,ast.Assign) else [stmt.target]
            if any(isinstance(x,ast.Name) and x.id==name for x in targets):
                values.append(ast.literal_eval(stmt.value))
    if len(values)!=1 or type(values[0]) is not tuple or any(type(x) is not str for x in values[0]):
        raise ValueError("TRANCHE_DECLARATION_INVALID_"+name)
    return values[0]

def checked_in_test_count(path):
    tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
    return sum(1 for cls in tree.body if isinstance(cls,ast.ClassDef)
               for node in cls.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))
               and node.name.startswith("test_"))

def read_evidence_packets(root=ROOT):
    mapping={};evidence=[]
    for i,(batch,stem,workflow,minimum) in enumerate(PACKETS):
        lab=root/"scripts"/(stem+".py")
        test=root/"tests"/("test_"+stem+".py")
        wf=root/".github"/"workflows"/workflow
        qa=root/"docs"/QA_DOCS[i]
        if not all(p.is_file() for p in (lab,test,wf,qa)):
            raise ValueError("EVIDENCE_FILE_MISSING_"+batch)
        members=literal_module_tuple(lab,"FILES" if i==7 else "EIGHT")
        if len(members)!=(7 if i==7 else 8) or len(set(members))!=len(members):
            raise ValueError("EVIDENCE_PACKET_DUPLICATE_OR_BAD_COUNT_"+batch)
        count=checked_in_test_count(test)
        if count<minimum:
            raise ValueError("EVIDENCE_PACKET_TEST_COUNT_TOO_LOW_"+batch)
        y=wf.read_text(encoding="utf-8")
        if any(k not in y for k in ("contents: read","mst_remote_legacy_tree_lock","unittest discover","pull_request")):
            raise ValueError("EVIDENCE_PACKET_REMOTE_SOURCE_LOCK_MISSING_"+batch)
        for member in members:
            if member in mapping:
                raise ValueError("SAME_ORIGINAL_IN_TWO_QA_BATCHES_"+member)
            mapping[member]={
                "batch":batch,
                "source_lab":"scripts/"+stem+".py",
                "tests":"tests/test_"+stem+".py",
                "workflow":".github/workflows/"+workflow,
                "qa_report":"docs/"+QA_DOCS[i],
                "packet_test_method_count_not_per_module":count,
                "coverage_scope":"PACKAGE_IMPORT_METADATA_ONLY" if member=="__init__"
                    else "SELECTED_SYNTHETIC_ACTUAL_V1_FUNCTION_CALLS",
            }
        evidence.append({"batch":batch,"members":list(members),"tests":count,
                         "lab":"scripts/"+stem+".py","workflow":".github/workflows/"+workflow,
                         "qa_report":"docs/"+QA_DOCS[i]})
    if len(mapping)!=63 or mapping["__init__"]["coverage_scope"]!="PACKAGE_IMPORT_METADATA_ONLY":
        raise ValueError("63_PATH_COVERAGE_NOT_EXACT_OR_INIT_MISCLASSIFIED")
    return mapping,evidence

def direct_sidecar_consumers(root,original_names):
    result={m:[] for m in original_names}
    for v2 in SIDECARS:
        path=root/"src"/"swing_trading"/(v2+".py")
        t=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
        for n in ast.walk(t):
            if isinstance(n,ast.ImportFrom) and n.level==1:
                deps=[n.module.split(".")[0]] if n.module else [a.name.split(".")[0] for a in n.names]
                for dep in deps:
                    if dep in result and v2 not in result[dep]:
                        result[dep].append(v2)
    return result

def build(root=ROOT):
    old=inventory(root/"src"/"swing_trading",root/"docs"/"H3_MODULE_DISPOSITION_PROVISIONAL.md")
    by_name={r["module"]:r for r in old["modules"]}
    found,batches=read_evidence_packets(root)
    if set(found)!=set(by_name):
        raise ValueError("H3_AST_RUNTIME_PACKET_SET_MISMATCH:"+str(sorted(set(by_name)^set(found))))
    v2=direct_sidecar_consumers(root,set(by_name))
    rows=[]
    for name in sorted(by_name):
        a=by_name[name];p=found[name]
        group=a["provisional_h3_group"]
        if group not in GAPS:
            raise ValueError("UNKNOWN_H3_GROUP_"+group)
        gap=GAPS[group]
        if name in EXTRA:
            gap+="; "+EXTRA[name]
        if a["provisional_h3_disposition"]=="IMPROVE":
            gap+="; H3 IMPROVE is unapproved, requires owner review"
        if a["provisional_h3_flags"]!="none":
            gap+="; AST flags "+a["provisional_h3_flags"]
        rows.append({
            "module":name,"source_path":a["source_path"],
            "source_sha256":a["checkout_sha256"],
            "static_abi_sha256":a["interface_sha256"],
            "public_functions":a["public_function_count"],
            "public_classes":a["public_class_count"],
            "direct_v1_dependencies":a["direct_package_imports"],
            "direct_v1_consumer_count":a["direct_internal_consumer_modules"],
            "h3_group":group,
            "h3_proposal_NOT_owner_decision":a["provisional_h3_disposition"],
            "h3_static_flags":a["provisional_h3_flags"],
            **p,
            "direct_v2_importers":v2[name],
            "v2_mapping_status":"DIRECT_STATIC_IMPORT_REQUIRES_FULL_ABI_BEHAVIOR_TEST"
                 if v2[name] else "NO_DIRECT_IMPORT_FOUND_TRANSITIVE_MAPPING_NOT_PROVEN",
            "unresolved_evidence":gap,
            "owner_required_review":"source+ABI, consumer effects, real trust/gates, behavior branches, rollback and V2 parity",
            "human_owner_disposition":"NOT_SIGNED",
            "complete_behavior_certified":False,
            "owner_abi_approved":False,"owner_behavior_approved":False,
            "outside_gates":"OA01-OA06_OPEN_AND_G01-G08_OPEN",
            "production_authorized":False,"trading_authorized":False,
        })
    if len(rows)!=TARGET_COUNT or any(r["human_owner_disposition"]!="NOT_SIGNED"
        or r["complete_behavior_certified"] or r["owner_abi_approved"]
        or r["owner_behavior_approved"] or r["production_authorized"]
        or r["trading_authorized"] for r in rows):
        raise PermissionError("CI_CANNOT_APPROVE_MODULE_OR_PRODUCTION")
    return {
        "schema":SCHEMA,
        "status":"63_SCOPED_ORIGINAL_V1_OWNER_EVIDENCE_ROWS_READY_FOR_HUMAN_NOT_SIGNED",
        "upstream_pin":old["source_upstream_sha"],
        "protected_main_pin":old["mst_protected_main_sha"],
        "original_tree_pin":old["mst_original_source_tree_sha"],
        "real_remote_upstream_main_pr_git_tree_lock_runs_separately":True,
        "h3_ast_modules":len(rows),
        "v1_paths_with_scoped_synthetic_or_import":len(rows),
        "original_domain_file_paths_with_selected_tests":len(rows)-1,
        "init_only_import_metadata_paths":1,
        "full_behavior_acceptances":0,"owner_signed":0,
        "a03_full_v1_v2_behavior_certified":False,
        "real_vendor_licence_verified":False,
        "physical_google_drive_market_cache_certified":False,
        "security_g01_g08_independently_closed":False,
        "production_authorized":False,"trading_authorized":False,
        "static_abi_inventory_fingerprint":old["package_interface_fingerprint"],
        "module_evidence_fingerprint":_digest([[r["module"],r["source_sha256"],r["static_abi_sha256"],r["batch"],r["human_owner_disposition"]] for r in rows]),
        "packets":batches,"modules":rows,
    }

def markdown(result):
    b=chr(96)
    lines=[
        "# MST A02 — 63 original V1 modules: formal evidence sufficiency / owner disposition matrix",
        "",
        "**63/63 files have scoped synthetic execution or import checks; owner signed 0/63; fully behavior-certified 0/63.**",
        "H3 KEEP/IMPROVE are provisional STATIC labels, never owner approvals. Direct V2 imports are only syntactic hints, NOT an exhaustive call graph or full V1→V2 ABI mapping.",
        "Every source, timestamp, provider right, real physical Drive market cache, owner independent signing key, real distributed two-writer CAS, G01–G08 and production/trading remains NO-GO.",
        "",
        "Pinned upstream "+b+result["upstream_pin"]+b+", protected main "+b+result["protected_main_pin"]+b+".",
        "Static ABI inventory SHA "+b+result["static_abi_inventory_fingerprint"]+b+".",
        "Matrix evidence SHA "+b+result["module_evidence_fingerprint"]+b+".",
        "",
        "| V1 module (source SHA/ABI SHA prefixes) | Static H3 proposal | Scoped executed QA lab / tests | Direct V2 importers (static only) | Missing evidence / reason not signed | Owner |",
        "|---|---|---|---|---|---|",
    ]
    for r in result["modules"]:
        name=r["module"]
        prop=r["h3_proposal_NOT_owner_decision"]
        if r["h3_static_flags"]!="none":
            prop+=" ("+r["h3_static_flags"].replace("|","/")+")"
        field=(b+name+b+" / "+r["source_sha256"][:10]+"/"+r["static_abi_sha256"][:10])
        labs=r["batch"]+" [lab]("+r["source_lab"]+") [tests]("+r["tests"]+") [QA]("+r["qa_report"]+")"
        if name=="__init__":
            labs+=" (IMPORT/METADATA ONLY)"
        deps=", ".join(r["direct_v2_importers"]) or "none directly observed"
        lines.append("| "+" | ".join((field,prop,labs,deps,
             r["unresolved_evidence"].replace("|","/"),"NOT_SIGNED"))+" |")
    lines+=["","## Mandatory follow-up before owner may decide","",
        "Verify actual full ABI/behavior and V2 parity per module (including transitive consumers), independent market rights, official session data, full replay/exit conditions, signed witness and real Drive CAS as applicable.",
        "Only an authorized independent human owner may formally accept KEEP/IMPROVE/REPLACE/REMOVE. CI cannot auto-close A02 or A03. Preserve the Git source byte lock and rollback route.",
        "**OA01–OA06, G01–G08, A03, production and real trading: NO-GO.**",""]
    return "\n".join(lines)

def csv_text(result):
    keys=("module","h3_group","h3_proposal_NOT_owner_decision","h3_static_flags",
          "batch","coverage_scope","source_path","source_sha256","static_abi_sha256",
          "direct_v1_consumer_count","direct_v2_importers","v2_mapping_status",
          "unresolved_evidence","human_owner_disposition","complete_behavior_certified",
          "outside_gates","production_authorized","trading_authorized")
    out=StringIO();w=csv.DictWriter(out,fieldnames=keys);w.writeheader()
    for r in result["modules"]:
        x={k:r[k] for k in keys};x["direct_v2_importers"]=";".join(x["direct_v2_importers"])
        w.writerow(x)
    return out.getvalue()

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--json",type=Path)
    p.add_argument("--markdown",type=Path)
    p.add_argument("--csv",type=Path)
    args=p.parse_args(argv)
    result=build(args.root)
    for where,blob in ((args.json,json.dumps(result,indent=2,sort_keys=True)+"\n"),
                       (args.markdown,markdown(result)),(args.csv,csv_text(result))):
        if where:
            where.parent.mkdir(parents=True,exist_ok=True)
            where.write_text(blob,encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k not in ("modules","packets")},sort_keys=True))

if __name__=="__main__":
    main()
