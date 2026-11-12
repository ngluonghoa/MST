"""A03 negative proof: a public validator + its own fixtures are not independent trust.

Demonstrates a SAME-CONTROLLER REBASE of the reviewed acceptance text, case-to-gate
mapping or M4 evidence kind. Each pair passes its jointly changed validator,
even though the original unmodified verifier rejects each unilateral tamper.
No vendor, account, credential, actual Drive cache or private evidence is used.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from unittest.mock import patch

from scripts import m2_a03_supplier_owner_proof_packet as m

SCHEMA = "mst.a03.public-self-anchor-circumvention.negative-fixture-only.v1"
CASES = ("TEXT_AND_REVIEW_LITERAL_BOTH_MUTATED",
         "RISK_GATE_AND_REVIEW_MAP_BOTH_MUTATED",
         "M4_KIND_AND_REVIEW_MAP_BOTH_MUTATED")
STATUS = "COUNTEREXAMPLE_SELF_CONSISTENT_PUBLIC_FIXTURE_IS_NOT_INDEPENDENT_AUTHORITY"


def _no_authority(result: dict) -> bool:
    return (result.get("a03_owner_choices_approved") == 0
            and result.get("a02_original_module_owner_approved") == 0
            and result.get("a03_v2_owner_approved") == 0
            and all(result.get(k) is False for k in (
                "externally_authenticated_supplier",
                "independently_proven_custody",
                "nonresettable_floor_and_real_cas",
                "licensed_google_drive_cache",
                "real_source_qualified_signal",
                "production_release", "trading")))


def _expects_refusal(packet: dict, m4: dict) -> bool:
    try:
        m.validate_packet(packet, m4)
    except (ValueError, PermissionError, TypeError):
        return True
    return False


def build(packet: dict, m4: dict) -> dict:
    baseline = m.validate_packet(packet, m4)
    assert _no_authority(baseline)
    cases = []

    # 1. The checked text AND public code's "reviewed" text are controlled
    # by one actor. This passes after re-basing the local fixture constant.
    altered = deepcopy(packet)
    gate = altered["requirements"][0]["gate"]
    statement = ("A joint actor can substitute this unrelated lengthy public "
                 "text for provider enrollment and rewrite the accompanying "
                 "reviewed fixture so structural unit tests still go green.")
    altered["requirements"][0]["acceptance_checks"][0] = statement
    original_would_block = _expects_refusal(altered, m4)
    reviewed = deepcopy(m.REVIEWED_ACCEPTANCE_CHECKS[gate])
    reviewed[0] = statement
    with patch.dict(m.REVIEWED_ACCEPTANCE_CHECKS, {gate: reviewed}):
        accepted = m.validate_packet(altered, m4)
    cases.append((CASES[0], original_would_block, accepted))

    # 2. Reassign missing provider revision proof to a *valid but wrong*
    # owner gate, and rewrite the local expected risk mapping as well.
    altered = deepcopy(packet)
    original_case = altered["untrusted_claim_scenarios"][4]
    case_id = original_case["id"]
    original_case["gate"] = "A03-OWNER-DURABLE-FLOOR-13"
    original_would_block = _expects_refusal(altered, m4)
    with patch.dict(m.REVIEWED_SCENARIO_GATE_REASON,
                    {case_id: [original_case["gate"],
                               original_case["missing_independent_proof"]]}):
        accepted = m.validate_packet(altered, m4)
    cases.append((CASES[1], original_would_block, accepted))

    # 3. Relabel existing PRIVATE M4 evidence category in both
    # checklist metadata and verifier-side reviewed constants.
    altered_m4 = deepcopy(m4)
    item = next(x for x in altered_m4["evidence_requirements"]
                if x["id"] == "E11")
    item["kind"] = "UNRELATED_REBASED_REVIEW_KIND"
    original_would_block = _expects_refusal(packet, altered_m4)
    with patch.dict(m.REVIEWED_M4_EVIDENCE_KINDS, {"E11": item["kind"]}):
        accepted = m.validate_packet(packet, altered_m4)
    cases.append((CASES[2], original_would_block, accepted))

    output = []
    for name, refused, accepted in cases:
        assert refused, "ORIGINAL_VALIDATOR_WAS_NOT_FAIL_CLOSED"
        assert _no_authority(accepted), "UNTRUSTED_INPUT_PRODUCTION_PROMOTION"
        assert accepted["public_requirement_index_sha256"] == baseline[
            "public_requirement_index_sha256"], "COARSE_INDEX_CHANGED_UNEXPECTEDLY"
        assert accepted["reviewed_semantic_contract_sha256"] != baseline[
            "reviewed_semantic_contract_sha256"], "REBASED_SEMANTICS_NOT_VISIBLE"
        output.append({
            "case": name,
            "unmodified_validator_rejects": True,
            "co_modified_public_validator_accepts": True,
            "legacy_coarse_index_still_matches": True,
            "recomputed_semantic_index_differs": True,
            "independent_root_or_owner_authority_proven": False,
            "production_or_trading_authorized": False,
        })
    canonical = json.dumps(output, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True, allow_nan=False)
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "case_count": len(output),
        "cases": output,
        "case_only_digest_sha256": sha256(canonical.encode()).hexdigest(),
        "reviewer_reference_index_sha256":
            baseline["reviewed_semantic_contract_sha256"],
        "independent_protected_commit_or_signer_attestation": False,
        "public_github_repo_review_required_proven": False,
        "provider_entitlement_or_issuer_proven": False,
        "real_independent_actor_control_proven": False,
        "owner_gates_approved": 0,
        "a02_63_owner_signed": 0,
        "a03_v2_8_owner_signed": 0,
        "licensed_drive_market_cache_authorized": False,
        "trading_authorized": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--packet", type=Path, default=m.PACKET_PATH)
    p.add_argument("--existing-m4", type=Path, default=m.M4_PATH)
    p.add_argument("--out", type=Path)
    a = p.parse_args(argv)
    report = build(json.loads(a.packet.read_text(encoding="utf-8")),
                   json.loads(a.existing_m4.read_text(encoding="utf-8")))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                         encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
