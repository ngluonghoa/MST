# MST M4 — Cloud-only atomic Cache authority: verified API feasibility and go/no-go matrix

**Date:** 2026-11-12 (Asia/Ho_Chi_Minh)  
**Status:** DRAFT / DESIGN AND READ-ONLY PLATFORM VERIFICATION / NO PRODUCTION AUTHORITY  
**Scope:** One small isolated documentation PR branching from `main@e4b162c57f10a47de62809188389bdc35d1261f5`. No credentials, new service, cloud billing, real Drive write, market data, GitHub policy or ref mutation. The hourly MST automation stays **disabled**.

## 1. Why this decision is needed

The canonical Master Handoff **§152** audited overlap and locked the division of work:
- [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8): prior M4 signed-receipt, independent floor, source-rights, GitHub-ref publish/read-barrier and rollback research. **337 files**, old PR base. Reuse, do not bulk merge.
- [Draft PR #22](https://github.com/ngluonghoa/MST/pull/22): fully **offline fictional** JSON SHA256, two-read and toy CAS acceptance. **3 files**.
- [Draft PR #23](https://github.com/ngluonghoa/MST/pull/23): **future owner-approved** OAuth `drive.file` one-file fictional STAGING_ONLY workflow, default metadata-only probe, and fake race/fencing failure demonstrations. **6 files**. No live upload.
This ADR does **not** reimplement the test models, is **not** a fourth candidate writer, and makes no CAS-success claim. It answers which **actual platform operations** exist, what they guarantee, and what owner approvals are missing.

## 2. Independent observations of MST's existing cloud control plane

As of this review, using only authenticated **read-only GitHub and Google Drive inspection**:

| Evidence | Observed state | What this does NOT prove |
|---|---|---|
| `ngluonghoa/MST` public repo | `main@e4b162c57f10a47de62809188389bdc35d1261f5` | Does not give a private trusted Cache authority |
| GitHub rulesets list | Active `MST - Protect Main` ruleset ID `26801439` | Not a blanket protection for future control refs |
| Exact ruleset conditions | `ref_name.include = ["~DEFAULT_BRANCH"]`; `deletion`, `non_fast_forward`, `pull_request`, three required CI status checks, `bypass_actors=[]` | Applies to default branch only; **not** to `refs/heads/mst/m4-ref-cas-lab-20261109` or an uncreated Cache-head ref |
| Historical M4 GitHub ref lab | Existing `refs/heads/mst/m4-ref-cas-lab-20261109@869b64d348b88ceb272408d1a1dabd668ba720d6` was readable | Existing lab is **not** protected witness, independently signed store or licensed publisher |
| OAuth Drive root | App-owned `MST_OAUTH_CACHE_V1`, private `STAGING_ONLY`, `CHUNKS`, `MANIFESTS`, `AUDIT` folders; each **empty** at the prior review | No actual Cache bytes, multiwriter transaction, external latest floor or true OHLCV |
| Current MST automation | Disabled after explicit user request | No recurring work or approval inferred |

The GitHub connector's branch-protection endpoint returned **403 Resource not accessible by integration**, but the **repository ruleset API was readable** and gave the exact default-branch rule details. Do not infer additional hidden rules or per-actor enforcement from this limited observation. Re-read before making any authorization decision.

## 3. Verified provider/API semantics — one property at a time

| Candidate | Documented capability | Applicable use | Unproven / forbidden inference | Gate |
|---|---|---|---|---|
| **Drive v3 `files.generateIds` then `files.create(id=...)`** | API accepts `drive.file` scope for `generateIds`; pre-generated IDs may be supplied to **non-Workspace file** create/copy; after successful create, retrying **same ID** returns **409 Conflict**. | Makes an **already reserved raw immutable-ish artifact ID** idempotent for retry after lost response, subject to exact ID/content/hash/parent verification. | It does **not** allocate the same ID for two separate new dispatches automatically, enforce uniqueness by file **name**, elect a winner, enforce a fencing epoch or atomically advance logical manifest/highwater. A 409 is **not** proof that content is correct. | Needs approved live API experiment; persist reservation under independent authenticated idempotency control *before* upload. |
| **Drive `files.list` and metadata `version`** | Enumerate app-visible objects; get object metadata/version and media. | Best-effort private staging preflight and post-read drift detection (PR23). | **No documented server-atomic compare-if-head-equals-X on a separate logical Cache record.** OAuth `drive.file` may not show objects created outside app access. | No authority claim. |
| **GitHub Actions `concurrency`** | A concurrency group allows one running; default `queue: single` retains at most one pending and replaces prior pending. Since May 2026 `queue: max` may retain up to **100 pending**, without dispatch-order guarantees. | Prevent overlapping jobs in a cooperative workflow; an operational defense in depth if later approved. | Does not fence a direct external writer or guarantee all dispatches survive queue saturation; no antirollback, independent signer or server-side Cache publish guard. | May improve a future workflow only after design review; don't modify current disabled automation or manual workflows. |
| **GitHub Git References update `PATCH .../git/refs/<ref>`, `force:false`** | Documented **fast-forward** update, 200/409/422 responses, requires **Contents:write** for updates. | Potential serialized **control-head ref** if all publishers authenticate independently and submit a unique child commit of the verified current head, and readers validate actual ref + full commit ancestry. | Endpoint does **not** expose an explicit `expected_old_sha` field; must not claim a generic multi-resource CAS or full Google Drive transaction. `force:false` is not an independent irreversible latest floor if admins/other writers can mutate/bypass/ref-delete, nor does a GitHub PR pass prove external writer identity. | OWNER decision on a **private** control repo/ref, app-specific write permission, ruleset targeting exact ref, no-bypass proof, independent witness and two-writer live test. Do not write or create ref now. |
| **Existing MST main ruleset** | Verified active default-branch delete/non-FF/PR/CI guards, with empty bypass array in observed ruleset. | Keeps existing project source review controlled. | **Cannot** be reused as authorization for a new unprotected control ref, and public `main` is not a privacy boundary for licensed market cache manifest. | Separate exact-ref ruleset and ACL/trust review needed. |
| **Third-party managed transactional store** | Potential to provide server-enforced transaction/conditional head and durable highwater. | Alternative architecture if owner changes permitted Cloud-only service boundary. | No authorized provider, account, pricing, service role, security assessment or proof exists. | **OUT OF CURRENT SCOPE** until explicit approval; do not provision. |

### Official API documentation read at review

- Google Drive file creation and **pre-generated ID / 409** semantics: https://developers.google.com/workspace/drive/api/guides/create-file
- Google Drive v3 `files.generateIds` **`drive.file`** OAuth scope: https://developers.google.com/workspace/drive/api/reference/rest/v3/files/generateIds
- GitHub Git References API `force:false`, status and `Contents:write`: https://docs.github.com/en/rest/git/refs
- GitHub Actions pending queue `single` vs `max` and non-guaranteed dispatch order: https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency
- GitHub rulesets: deletion/non-fast-forward and bypass behavior: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets
- Prior existing MST [M4 publish/read-barrier ADR](https://github.com/ngluonghoa/MST/blob/mst/m2-a03-optin-v2-contracts-20261109/docs/MST_M4_CLOUD_PUBLISH_READ_BARRIER_ADR_CANDIDATE.md) and [signed-receipt negative proof](https://github.com/ngluonghoa/MST/pull/8). These are prior research, not runtime GO evidence.

## 4. Minimal authority protocol IF an independently trusted control service is authorized

This is a **specification**, not executable authorization:

1. **Admit licensed source**: provider/account/right-to-retain/right-to-derive/TF/exchange/session/calendar and historical as-of first-known must be independently verified. Never ingest from pilot quarantine just because a blob hash matches.
2. **Reserve idempotency key & artifact ID**: canonical cache key + generation + exact approved run/attempt/source clock; authority creates durable reservation. If a Drive pre-generated ID is used, future retries recover **the same reserved ID** from this durable record, not another `generateIds` call.
3. **Stage bytes only**: upload bounded immutable candidate chunk to an app-authorized private Drive folder. Verify exact ID, parent, content hash and two independent server media reads. A staging artifact has **zero reader authority**.
4. **Publish only by authoritative commit**: authenticated owner/epoch/expected prior head + expected source fingerprint + immutable artifact hash, under **server-atomic** conditional current-head advance with durable receipt/highwater. If multiple services cannot commit an external signed latest floor and head under a compatible trusted transaction/recovery boundary, treat outcome as **NO-GO**.
5. **Read barrier**: check strongly consistent current authorized head and independently trusted nonrollbackable latest floor; verify signed chain/signer epoch, source rights, exact Drive bytes/lineage. Fail closed if authority, freshness, source proofs or entitlement unavailable.
6. **Recover ambiguities**: after upload-but-before-commit, raw Drive bytes are quarantined orphans; after committed-but-ACK-lost, query exact idempotency receipt and strong head, never mint a fresh generation blindly. No automatic overwrite/delete in an uncertain state.
7. **Retain audit**: distinguish `UNTRUSTED_RAW_STAGED`, `CONFLICT`, `UNKNOWN`, `COMMITTED_CURRENT`, `REVOKED`, `ROLLED_BACK`; report exact evidence and do not convert “CI green” into “production allowed”.

### Acceptance gates that MUST be observed in real authorized services

| Gate | Required observation | Current outcome |
|---|---|---|
| AUTH-01 Identity & ruleset | Separate authenticated writer; exact control-ref protections, no bypass, unauthorized update and delete denied | **OPEN** |
| AUTH-02 Atomic single-winner | Two independent concurrent writers with the **same expected head**: exactly one publish; verify independent ref and receipt | **OPEN** |
| AUTH-03 Lease & fencing | Expired stale writer physically uploads bytes but is **not** able to publish or have readers serve them | **OPEN** |
| AUTH-04 Crash/ACK | Crash after raw write, before commit, after commit but before ACK; recover same ID and receipt, no blind retry | **OPEN** |
| AUTH-05 Nonrollbackable trusted floor | Tamper both old Drive bytes and signed metadata; verify current external trust root detects old-but-valid signature | **OPEN** |
| AUTH-06 Causal licensed data | Provider rights + source corrections, genuine closed bars at M5/M15/M30/H1/H4/D1, source-first-known | **OPEN** |
| AUTH-07 Reader custody | Read-only reader has no power to rewrite head, signer, highwater or amend older receipts | **OPEN** |
| AUTH-08 Real Drive idempotence | Explicitly approved **fictional** staging file using reserved ID and same-ID duplicate 409/readback, verify no market bytes | **OPEN / different approval from production** |
| AUTH-09 Production & rollback | Review/merge/rollout owner decision + independent operator-safe rollback without old signed snapshot acceptance | **OPEN** |

## 5. Recommendation and strict next steps

**Decision today: NO-GO for any real Cache publisher or production ingestion.** All currently authorized GitHub+Drive operations suffice for **design, read-only investigation and synthetic/cloud CI**, not authenticated distributed atomic publication with an independently durable antirollback anchor. A GitHub-protected *private* control-head ref is the **first candidate to cost/security-review**, not a proven solution. Google Drive pre-generated IDs are useful for **artifact idempotency only** and must be placed under an authoritative reservation.

**Next safe engineering step**, after owner reviews this isolated ADR:
1. Assess whether the owner permits a **private, independently protected** GitHub control repository/ref and independent trust anchor, and which actor owns app auth/ruleset; otherwise mark AUTH-01/05 impossible with current constraints.
2. Write one **read-only preflight** that checks live control-ref/ruleset/auth scope and outputs deterministic `NO_GO` when missing. Reuse PR8's existing read-only GitHub witness/ruleset lab rather than copy its mocks.
3. After a **separate, narrow** user approval, run exactly one sacrificial no-market two-writer ref experiment with distinct principals and explicit audit. **Never** use `main` or existing lab ref for a new write without owner consent.
4. If the actual controls cannot enforce externally trusted monotonic head/floor, select a different **owner-approved** authority architecture or keep market Cache disabled. Only thereafter consider the separately approved PR23 real Drive fictional JSON experiment.

**Invariants:** no new service, no secret/variable/branch-protection change, no merge of PR8/22/23/this ADR, no Drive upload, no real market Cache/Watchlist/production action, and no restarting the MST automation. Green CI only validates the code/docs at its exact commit, not AUTH-01..09.
