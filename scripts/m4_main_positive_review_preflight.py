"""MST M4: READ-ONLY owner proposal for mandatory positive main PR review.

Checks public proposal, previously OPEN M4 E01/E02/E03/E06/E10/E12/E14,
current main ruleset and PR8 metadata. Counts/views are NOT independent
attestation. Never modifies rulesets, reviews, CODEOWNERS, refs, or rights.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

REPO = "ngluonghoa/MST"
SCHEMA = "mst.m4.main-positive-review.owner-unapproved.v1"
PIN = "4048f91beaaa3410116d97e35896c8b688384e19"
UPSTREAM = "cd90c1babae8912db31490ad614fc2ad2f868042"
TREE = "d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e"
RULE_ID = 26801439
CONTEXTS = ["unittest (3.11)", "unittest (3.12)",
            "Contract, source-boundary and wheel checks"]
EVIDENCE = (("E01","OA01","G01"),("E02","OA02","G02"),
            ("E03","OA01","G01"),("E06","OA03","G07"),
            ("E10","OA05","G01"),("E12","OA06","G08"),
            ("E14","OA05","G07"))
CODEOWNERS = (".github/CODEOWNERS","CODEOWNERS","docs/CODEOWNERS")
PROPOSAL = Path("docs/MST_M4_MAIN_POSITIVE_REVIEW_OWNER_PROPOSAL_20261110.json")
M4 = Path("docs/MST_M4_OPTION_A_PRIVATE_OWNER_EVIDENCE_INTAKE_20261110.json")
_BASELINE = dict(required_approvals=0,codeowner_review=False,
    dismiss_stale_reviews=False,last_push_approval=False,
    thread_resolution=False,required_ci=CONTEXTS,
    main_delete_guard=True,main_force_push_guard=True)
_TARGET = dict(minimum_approvals=1,codeowner_review=True,
    dismiss_stale_reviews=True,last_push_approval=True,
    thread_resolution=True,preserve_existing_ci=True,
    preserve_non_fast_forward=True,preserve_no_delete=True)
_FLAGS = ("independent_reviewer_verified","owner_approved",
    "private_evidence_channel_approved","policy_applied",
    "codeowners_applied","main_updated","pr_merged",
    "production_authorized","trading_authorized")
_PRIVACY = ("no_private_ids","no_keys_or_tokens",
            "no_real_vendor_data","no_local_or_third_cloud")


def _same(actual,expected,err):
    if type(actual) is not type(expected) or actual!=expected:
        raise ValueError(err)


def validate(proposal,m4):
    if type(proposal) is not dict or set(proposal)!={
        "schema","repo","source_main","source_upstream","source_tree",
        "ruleset_id","option","status","baseline","proposal",
        "owner_conditions","permissions","privacy","next"}:
        raise ValueError("OWNER_POLICY_PROPOSAL_UNREVIEWED_FIELDS")
    for key,val in (("schema",SCHEMA),("repo",REPO),("source_main",PIN),
        ("source_upstream",UPSTREAM),("source_tree",TREE),
        ("ruleset_id",RULE_ID),("option","GITHUB_GOOGLE_DRIVE_ONLY"),
        ("status","OWNER_DECISION_REQUIRED_NO_POLICY_APPLY"),
        ("next","OWNER_APPROVE_PRIVATE_EFFECTIVE_ROLE_AND_MAIN_RULESET_REVIEW_NO_APPLY")):
        _same(proposal[key],val,"OWNER_POLICY_SCOPE_DRIFT_"+key)
    _same(proposal["baseline"],_BASELINE,"OWNER_BASELINE_REWRITTEN")
    _same(proposal["proposal"],_TARGET,"UNAPPROVED_REVIEW_POLICY_TARGET_CHANGED")
    if type(proposal["permissions"]) is not dict or set(proposal["permissions"])!=set(_FLAGS):
        raise ValueError("ALL_DENIAL_FLAGS_REQUIRED")
    for k in _FLAGS:
        if proposal["permissions"][k] is not False:
            raise PermissionError("PR_POLICY_SELF_APPROVAL_"+k)
    if type(proposal["privacy"]) is not dict or set(proposal["privacy"])!=set(_PRIVACY):
        raise ValueError("PRIVATE_OWNER_DATA_HANDLING_REQUIRED")
    for k in _PRIVACY:
        if proposal["privacy"][k] is not True:
            raise PermissionError("PRIVATE_OWNER_POLICY_WEAKENED_"+k)
    if type(m4) is not dict or type(m4.get("evidence_requirements")) is not list:
        raise ValueError("M4_EXISTING_OWNER_INTAKE_REQUIRED")
    index={x["id"]:x for x in m4["evidence_requirements"] if type(x) is dict and "id" in x}
    if set(index)!={f"E{i:02d}" for i in range(1,15)}:
        raise ValueError("M4_14_OWNER_EVIDENCE_CLASSES_MISSING")
    rows=proposal["owner_conditions"]
    if type(rows) is not list or len(rows)!=len(EVIDENCE):
        raise ValueError("EXACT_SEVEN_OWNER_PRECONDITIONS")
    for row,(proof,choice,gate) in zip(rows,EVIDENCE):
        if type(row) is not dict or set(row)!={"proof","decision","gate","state"}:
            raise ValueError("PROOF_CROSSWALK_FIELDS_CHANGED")
        _same(row,{"proof":proof,"decision":choice,"gate":gate,
                    "state":"NOT_RECEIVED"},"REQUIRED_OWNER_CROSSWALK_DRIFT")
        previous=index[proof]
        if (previous.get("state")!="NOT_RECEIVED" or
            previous.get("owner_reviewed") is not False or
            previous.get("independently_verified") is not False):
            raise PermissionError("INDEPENDENT_M4_OWNER_EVIDENCE_NOT_AVAILABLE")
        for key in ("private_evidence_uri","principal_binding","signer_fingerprint",
                    "verifier_attestation_uri"):
            if previous.get(key) is not None:
                raise PermissionError("PUBLIC_OWNER_EVIDENCE_IDENTITY_LEAK")


def observe(proposal,m4,rule,main,pr,reviews,codeowners,head):
    validate(proposal,m4)
    if any(type(x) is not dict for x in (rule,main,pr)):
        raise TypeError("LIVE_GITHUB_OBJECT_REQUIRED")
    if type(reviews) is not list or any(type(x) is not dict for x in reviews):
        raise TypeError("PR_REVIEW_EVENTS_REQUIRED")
    if type(codeowners) is not dict or set(codeowners)!=set(CODEOWNERS):
        raise ValueError("ALL_THREE_CODEOWNERS_SCOPES_REQUIRED")
    if any(v not in ("MISSING_404","UNKNOWN_403","VISIBLE") for v in codeowners.values()):
        raise ValueError("CODEOWNERS_EVIDENCE_SCOPE_INVALID")
    if any((rule.get("id")!=RULE_ID,rule.get("name")!="MST - Protect Main",
        rule.get("source")!=REPO,rule.get("target")!="branch",
        rule.get("enforcement")!="active",
        rule.get("conditions",{}).get("ref_name")!={"include":["~DEFAULT_BRANCH"],"exclude":[]})):
        raise ValueError("MAIN_RULESET_SCOPE_OR_AUTHORITY_CHANGED")
    rows=rule.get("rules")
    if type(rows) is not list or any(type(x) is not dict for x in rows):
        raise ValueError("RULESET_RULES_NOT_READABLE")
    kinds={x.get("type"):x for x in rows}
    if not {"deletion","non_fast_forward","pull_request",
            "required_status_checks"}.issubset(kinds):
        raise ValueError("MAIN_SOURCE_POLICY_GUARDS_MISSING")
    params=kinds["pull_request"].get("parameters")
    checks=kinds["required_status_checks"].get("parameters")
    if type(params) is not dict or type(checks) is not dict:
        raise ValueError("MAIN_PR_APPROVAL_POLICY_NOT_READABLE")
    for k,val in (("required_approving_review_count",0),
        ("require_code_owner_review",False),
        ("dismiss_stale_reviews_on_push",False),
        ("require_last_push_approval",False),
        ("required_review_thread_resolution",False)):
        _same(params.get(k),val,"MAIN_REVIEW_BASELINE_DRIFT_"+k)
    actual=checks.get("required_status_checks")
    if type(actual) is not list or any(type(x) is not dict for x in actual):
        raise ValueError("MAIN_REQUIRED_CI_UNAVAILABLE")
    if len(actual)!=3 or {x.get("context") for x in actual}!=set(CONTEXTS):
        raise ValueError("MAIN_FOUNDATION_CI_CHANGED")
    if (main.get("name")!="main" or main.get("protected") is not True or
        main.get("commit",{}).get("sha")!=PIN):
        raise ValueError("MAIN_SOURCE_SHA_OR_PROTECTION_CHANGED")
    if (pr.get("number")!=8 or pr.get("state")!="open" or
        pr.get("draft") is not True or pr.get("merged") is not False or
        pr.get("base",{}).get("sha")!=PIN or
        pr.get("base",{}).get("ref")!="main" or
        pr.get("head",{}).get("repo",{}).get("full_name")!=REPO or
        type(head) is not str or len(head)!=40 or
        pr.get("head",{}).get("sha")!=head):
        raise ValueError("DRAFT_PR8_HEAD_OR_BASE_CHANGED")
    return dict(schema="mst.m4.main-positive-review.live-readonly.no-go.v1",
        status="NO_MANDATORY_POSITIVE_HUMAN_REVIEW_OWNER_DECISION_REQUIRED",
        main_pin=PIN,pr8_head_matches_event=True,
        rule_id=RULE_ID,three_foundation_ci_required=True,
        current_positive_reviews_required=0,
        current_codeowner_review_required=False,
        pr8_review_events_seen=len(reviews),
        codeowners_scope_states=codeowners,
        visible_bypass_list_for_current_token=(type(rule.get("bypass_actors")) is list),
        effective_admin_bypass_independently_verified=False,
        reviewer_identity_independently_verified=False,
        proposal_approved=False,policy_applied=False,
        main_or_permissions_changed=False,pr_merged=False,
        production_authorized=False,trading_authorized=False)


def _get(path,token,allow_missing=False):
    req=Request("https://api.github.com/repos/"+REPO+path,headers={
        "Authorization":"Bearer "+token,"Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28",
        "User-Agent":"MST-M4-ReadOnly-Owner-Review-20261110"},method="GET")
    try:
        with urlopen(req,timeout=20) as res:
            return json.load(res),"VISIBLE"
    except HTTPError as exc:
        if allow_missing and exc.code in (403,404):
            return None,("MISSING_404" if exc.code==404 else "UNKNOWN_403")
        raise


def main_cli():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    if (os.getenv("GITHUB_ACTIONS")!="true" or
        os.getenv("GITHUB_REPOSITORY")!=REPO or
        os.getenv("GITHUB_EVENT_NAME")!="pull_request"):
        raise PermissionError("SAME_REPO_ACTIONS_PR_ONLY")
    token=os.getenv("GITHUB_TOKEN")
    head=os.getenv("GITHUB_HEAD_SHA")
    if not token or not head:
        raise PermissionError("READ_ONLY_TOKEN_AND_PR_HEAD_REQUIRED")
    get=lambda u:_get(u,token)[0]
    states={}
    for path in CODEOWNERS:
        _,states[path]=_get("/contents/"+path+"?ref=main",token,allow_missing=True)
    receipt=observe(json.loads(PROPOSAL.read_text()),
        json.loads(M4.read_text()),get("/rulesets/"+str(RULE_ID)),
        get("/branches/main"),get("/pulls/8"),
        get("/pulls/8/reviews?per_page=100"),states,head)
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print(json.dumps(receipt,sort_keys=True))


if __name__=="__main__":
    main_cli()
