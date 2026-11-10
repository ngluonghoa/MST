"""MST A02: static, owner-ready V1 module ABI and dependency review inventory.

Read-only AST analysis of ALL 63 exact inherited V1 Python modules. V2 opt-in
sidecars are excluded. This is evidence for a future HUMAN owner disposition
of each module, not 63 signed approvals or a full behavior-parity certificate.

Real upstream/main/head Git blob parity is checked INDEPENDENTLY by the
existing mst_remote_legacy_tree_lock.py in the same GitHub-hosted job.
No import/execute of target modules, market data, keys, Drive writes, local
user runtime, remote trade, or production authorization.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

from scripts.mst_remote_legacy_tree_lock import (
    _ALLOWED_V2_PATHS, _MAIN_COMMIT, _SOURCE_COMMIT, _TREE,
)

DEFAULT_PACKAGE = Path("src/swing_trading")
DEFAULT_H3 = Path("docs/H3_MODULE_DISPOSITION_PROVISIONAL.md")
SCHEMA = "mst.a02.legacy-63.static-api-dependency-owner-review.unapproved.v1"
H3_DISPOSITIONS = {"KEEP", "IMPROVE", "REPLACE", "REMOVE"}
TARGET_COUNT = 63
V2_COUNT = 8
EXPECTED_ALL_COUNT = TARGET_COUNT + V2_COUNT
HIGH_IMPACT = (
    "contracts", "engine", "replay", "market_data", "source_quality",
    "incremental_cache", "cache_fetch_planner", "vn_backtest_execution_fixture",
)


def _canonical(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _digest(payload: object) -> str:
    return hashlib.sha256(_canonical(payload).encode("ascii")).hexdigest()


def parse_provisional_h3(h3_markdown: str) -> dict:
    """Independent crosswalk against EXISTING H3 static proposals, not owner votes."""
    result = {}
    for line in h3_markdown.splitlines():
        if not line.startswith("| "):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) != 8 or parts[6] not in H3_DISPOSITIONS:
            continue
        name, group, loc, branch, longest, consumers, proposed, flags = parts
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError("H3_INVALID_MODULE_IDENTIFIER")
        if name in result:
            raise ValueError("H3_DUPLICATED_MODULE")
        if not group or not all(p.isdigit() for p in (loc, branch, longest, consumers)):
            raise ValueError("H3_INVALID_STATIC_REVIEW_METADATA")
        result[name] = {
            "group": group,
            "loc": int(loc),
            "max_branch": int(branch),
            "longest_function": int(longest),
            "historical_consumer_count": int(consumers),
            "provisional_disposition": proposed,
            "flags": flags,
        }
    if len(result) != EXPECTED_ALL_COUNT:
        raise ValueError("H3_NOT_EXACTLY_71_PROVISIONAL_MODULES")
    return result


def _api_item(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict:
    """Do not serialize default values. Hash exact AST arguments for drift."""
    args = node.args
    pos = [a.arg for a in (*args.posonlyargs, *args.args)]
    kw = [a.arg for a in args.kwonlyargs]
    return {
        "name": node.name,
        "async": isinstance(node, ast.AsyncFunctionDef),
        "positional": pos,
        "positional_only_count": len(args.posonlyargs),
        "keyword_only": kw,
        "has_vararg": args.vararg is not None,
        "has_kwarg": args.kwarg is not None,
        "defaults_count": len(args.defaults),
        "keyword_defaults_count": sum(v is not None for v in args.kw_defaults),
        "declaration_ast_sha256": hashlib.sha256(
            (ast.dump(args, include_attributes=False)
             + ast.dump(node.returns, include_attributes=False)).encode("utf-8")
        ).hexdigest(),
    }


def module_static_api(source: str, *, module_name: str) -> dict:
    """Inspect real Python syntax WITHOUT importing or executing it."""
    tree = ast.parse(source, filename=module_name + ".py", type_comments=True)
    functions = []
    classes = []
    direct_imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1:
            if node.module:
                direct_imports.add(node.module.split(".")[0])
            else:
                direct_imports.update(alias.name.split(".")[0] for alias in node.names)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                functions.append(_api_item(node))
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            methods = [
                _api_item(method) for method in node.body
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
                and (not method.name.startswith("_")
                     or method.name in ("__init__", "__post_init__", "__call__",
                                        "__iter__", "__enter__", "__exit__",
                                        "__aenter__", "__aexit__"))
            ]
            fields = [
                sub.target.id for sub in node.body if isinstance(sub, ast.AnnAssign)
                and isinstance(sub.target, ast.Name)
                and not sub.target.id.startswith("_")
            ]
            classes.append({
                "name": node.name,
                "methods": methods,
                "public_annotated_fields": fields,
                "decorator_syntax_sha256": _digest([
                    ast.dump(dec, include_attributes=False) for dec in node.decorator_list
                ]),
                "base_syntax_sha256": _digest([
                    ast.dump(base, include_attributes=False) for base in node.bases
                ]),
            })
    surface = {"functions": functions, "classes": classes}
    return {
        "module": module_name,
        "public_function_count": len(functions),
        "public_class_count": len(classes),
        "direct_package_imports": sorted(direct_imports),
        "interface_sha256": _digest(surface),
        "interface": surface,
    }


def inventory(package_path: Path = DEFAULT_PACKAGE,
              h3_path: Path = DEFAULT_H3) -> dict:
    """Build crosswalk of current hosted checkout plus existing H3 rows."""
    h3 = parse_provisional_h3(h3_path.read_text(encoding="utf-8"))
    v2_names = {
        Path(path).stem for path in _ALLOWED_V2_PATHS
    }
    if len(v2_names) != V2_COUNT:
        raise ValueError("V2_SIDE_CAR_ALLOWLIST_NOT_EXACTLY_EIGHT")
    present = list(package_path.glob("*.py"))
    if len(present) != EXPECTED_ALL_COUNT:
        raise ValueError("SOURCE_PACKAGE_NOT_EXACTLY_63_V1_8_V2")
    names = {p.stem for p in present}
    if len(names) != len(present) or names != set(h3):
        raise ValueError("SOURCE_AND_EXISTING_H3_MODULE_INVENTORY_DRIFT")
    if not v2_names <= names:
        raise ValueError("KNOWN_OPT_IN_V2_MODULE_MISSING")
    originals = sorted(names - v2_names)
    if len(originals) != TARGET_COUNT:
        raise ValueError("ORIGINAL_V1_MODULE_COUNT_NOT_63")
    summaries = []
    for name in originals:
        path = package_path / (name + ".py")
        source_bytes = path.read_bytes()
        source = source_bytes.decode("utf-8")
        static = module_static_api(source, module_name=name)
        for dep in static["direct_package_imports"]:
            if dep not in names:
                raise ValueError("UNKNOWN_DIRECT_INTERNAL_IMPORT_" + name)
        summaries.append({
            "module": name,
            "source_path": "src/swing_trading/" + name + ".py",
            "checkout_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "interface_sha256": static["interface_sha256"],
            "public_function_count": static["public_function_count"],
            "public_class_count": static["public_class_count"],
            "direct_package_imports": static["direct_package_imports"],
            "provisional_h3_group": h3[name]["group"],
            "provisional_h3_disposition": h3[name]["provisional_disposition"],
            "provisional_h3_flags": h3[name]["flags"],
            "owner_decision": "NOT_SIGNED",
            "owner_abi_approved": False,
            "owner_behavior_parity_approved": False,
        })
    reverse = {name: 0 for name in originals}
    for row in summaries:
        for dependency in row["direct_package_imports"]:
            if dependency in reverse:
                reverse[dependency] += 1
    for row in summaries:
        row["direct_internal_consumer_modules"] = reverse[row["module"]]
    if any(row["owner_decision"] != "NOT_SIGNED" for row in summaries):
        raise PermissionError("UNAUTHORIZED_OWNER_MODULE_DISPOSITION")
    return {
        "schema": SCHEMA,
        "status": "V1_63_MODULE_AST_API_DEPENDENCY_PACKET_COMPLETE_OWNER_NOT_SIGNED",
        "source_upstream_sha": _SOURCE_COMMIT,
        "mst_protected_main_sha": _MAIN_COMMIT,
        "mst_original_source_tree_sha": _TREE,
        "source_tree_remote_readback_in_this_function": False,
        "remote_source_lock_requires_separate_live_github_api_check": True,
        "original_module_count": len(summaries),
        "existing_v2_sidecar_count_excluded": len(v2_names),
        "provisional_h3_total_modules": len(h3),
        "high_impact_modules_to_review_first": list(HIGH_IMPACT),
        "high_impact_module_count": len(HIGH_IMPACT),
        "package_interface_fingerprint": _digest([
            [r["source_path"], r["interface_sha256"]] for r in summaries
        ]),
        "module_owner_dispositions_received": 0,
        "module_owner_abi_approvals_received": 0,
        "module_owner_behavior_approvals_received": 0,
        "independent_real_market_provider_rights_verified": False,
        "v1_v2_full_behavior_parity_claimed": False,
        "production_release_authorized": False,
        "trading_authorized": False,
        "modules": summaries,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--h3", type=Path, default=DEFAULT_H3)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    result = inventory(args.package, args.h3)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    print(json.dumps({
        k: v for k, v in result.items() if k != "modules"
    }, sort_keys=True))


if __name__ == "__main__":
    main()
