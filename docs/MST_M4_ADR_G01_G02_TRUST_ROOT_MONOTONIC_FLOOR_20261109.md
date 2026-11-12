# MST ADR-M4-001 — Independent signer root and monotonic rollback floor (G01/G02)

**Status:** OPTION A (GitHub + Google Drive only) SELECTED FOR ARCHITECTURE SCOPE on 2026-11-09; G01/G02 authority and provisioning STILL NOT APPROVED / NO DEPLOY  
**Date:** 2026-11-09 (Asia/Ho_Chi_Minh)  
**Scope:** architecture and acceptance only. **Source baseline:** Swing Trading 1.8 `cd90c1babae8912db31490ad614fc2ad2f868042`, protected MST `main@4048f91beaaa3410116d97e35896c8b688384e19` (tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`); 63 inherited V1 modules unchanged. Work only on Draft PR #8, not main. Cloud-only, never Mac/MOCHI/local. Existing real market OHLCV, licensed cache retention, trading and production keys **NOT AUTHORIZED**.

## Decision amendment — explicit user selection after the draft

The user has explicitly responded **"Đồng ý phương án A"**. This confirms **GitHub + Google Drive only** as the present MST architecture/platform scope. It does NOT authenticate an independent signing key, close any SIGNED-G01..G08 security gate, authorize admin provisioning, new GitHub witness rules, production credentials, licensed OHLCV ingestion, Google Drive cache write or PR merge. Any additional Cloud KMS/Firestore service is explicitly **not selected** and needs a new user decision.

The original unselected decision JSON (`docs/MST_M4_G01_G02_OWNER_DECISIONS_20261109.json`) is intentionally kept as the **historical draft snapshot** for audit. Current architecture selection is recorded in the later **versioned overlay** `docs/MST_M4_OPTION_A_SCOPE_SELECTION_20261109.json`, which takes precedence *only on selected platform scope*, while all owner security/admin/release decisions D01–D08 stay OPEN. Operational Option A blueprint: `docs/MST_M4_OPTION_A_GITHUB_DRIVE_TRUST_CUSTODY_PLAN_20261109.md`. This chat approval is not an independent cryptographic owner attestation and must never be used to close signer/floor release gates.

## 1. Decision to make

MST's M4 signed receipt laboratory is NOT a trust service. It accepts a caller-pinned Ed25519 public key and a caller-provided floor; a caller may substitute both or replay a prior snapshot. GitHub Actions cache can transfer bytes across runs but is neither an authoritative monotonic store nor durable custody. Main's existing ruleset protects `main` only; the proposed witness ref `refs/heads/mst/m4-witness/v1` does not exist, and no owner-approved witness ruleset has been installed.

**G01** needs a key-enrollment trust root independent of data writers/readers: owner governance, signer identities, issuer, roles, key versions, expiry/revocation and secure private-key custody. **G02** needs an externally protected high-water mark per canonical (provider, symbol, timeframe, interval/as-of partition, rights-policy version) across GitHub runs, accounts, crashes and key rotations. Neither property follows from a valid signature or stable-looking Git commit.

**Historical pre-choice draft state: NONE SELECTED at initial ADR creation.** The subsequent user message explicitly selected A for architecture scope, with all implementation/privileged approvals still OPEN. This ADR does not grant credentials or create a new cloud provider.

## 2. Non-negotiable safety invariants

- The **source data provider** (SSI/DNSE/VCBS) and its licensed first-known/revision/correction rights are distinct from MST's infrastructure signer. Source-rights evidence is a separately required G04 gate. Never treat a publisher's signature as vendor-origin truth.
- Partition ID is immutable and binds provider ID, market, symbol, TF, adjusted/raw bar policy, source contract/entitlement version, calendar and rights-policy SHA; cross-partition transplant is forbidden. Canonicalization must be version-pinned; a split in canonicalization version requires an owner-approved new namespace and continuity proof.
- An acceptance record must bind `namespace_digest`, `signer_key_id`, `signer_epoch`, `registry_digest`, `parent_head_digest`, `generation`, `manifest_sha256`, `Drive_object_id`, `Drive_blob_sha256`, `source_first_known/revision`, `observed_utc`, `commit/ref/tree`, `rights_policy_digest`, and `idempotency_key`. **Do not automatically require first-known timestamps to be strictly increasing across backfills or corrections**: vendor-authorized revision semantics must be defined at G04. Also pin a revision/lineage watermark rather than using clock alone.
- A protected acceptance transaction has **one authoritative expected head** and compares it atomically with the actual current head; one of two siblings may commit, the other must fail and reconcile. Enforce monotonic generation/epoch/policy and nonzero monotonic counter; an old signed head may never be silently re-adopted after a later accepted head.
- Reader admission requires independent trust-root authentication, a fresh authoritative floor, signed registry and data receipt, provider rights, actual Google Drive bytes digest, protected Git commit/tree/ref and stable final readback after the Drive check. If the trust root, floor, source entitlement or Drive bytes cannot be verified: **BLOCK / UNVERIFIED**, never fall back to a saved cache, locally seeded floor or 'last known good' without a separate approved recovery.
- Key compromise/revocation: global revoke must fence readers AND writers, including previously issued tokens, old key epochs, source rights and offline cache; fail closed until independently verified new epoch and migration proof. A key-rotation "new G1" must not reset previous high-water marks.
- A root administrator may bypass or destroy an ordinary GitHub or database policy; document who can do so, whether tampering is independently detectable and how independent watchers react. "Non-erasable" must be **verified against the actual configured principals and root-admin threat**, not claimed from the service name.
- Never put owner signing private keys, cloud service account keys, real vendor tokens, protected production writer credential or actual licensed market payloads into a PR-triggered workflow or artifact.

## 3. Alternatives and constraints

### A — Only existing GitHub + Google Drive (IN-SCOPE TO DESIGN; NOT PROVEN SUFFICIENT)

**Concept:** Owner-controlled **separate** private GitHub witness-policy repository or protected ref with distinct administration and writer credentials; owner-signed trust registry; verification through GitHub remote API, protected ref/commit/tree readback, no force-push/delete, explicit bypass audit, second independent owner-controlled read-only watcher or archival checkpoint. Real cache chunks continue in Google Drive, if separately licensed. No Google Cloud resource required.

**Benefits:** Preserves the user's GitHub+Drive-only constraint and existing CI/Docs/Drive architecture, supports SHA/commit parent/FF references and external review, minimal new service footprint.

**Critical unresolved points:** Two GitHub accounts in a repo do not prove independence if both share admin/bypass rights; signed commits verify key signatures, not owner enrollment or data provenance; a fast-forward can publish old manifest contents with a *new* commit; Git branch state is not a non-resettable floor if privileged actors can rewrite/delete or replace policy. A GitHub ref-FF race can allow one winner at one ref but **does not atomically commit Google Drive objects or guarantee cross-account source authority**. Protected repo/ref and signer root must be separated from the PR actor and verified against root/admin bypass and recovery; no implementation claim until independent red-team acceptance.

**Disposition:** **SELECTED FOR ARCHITECTURE SCOPE ONLY** by the user, still conditionally viable and subject to independent proofs. **Not enough to close G01/G02 on present evidence.** Cannot automatically release production.

### B — Owner-separated managed key service + transactional floor (REQUIRES EXPLICIT SCOPE EXPANSION)

**Concept:** Owner-controlled external Cloud KMS asymmetric signer (e.g. Ed25519 where the chosen key protection tier actually supports it), with non-exportable key material; a separately governed Firestore transaction record per namespace for `{current_head, generation, approved_epoch, signed_registry_digest, rights-policy_digest, revocation_floor, last_first_known/revision}`, and dedicated trusted verifier service. Use workload identity federation with tightly bound GitHub OIDC identity (repository/ref/workflow/subject/audience), not static service-account JSON secrets. GitHub remains source/CI/witness, Google Drive stays the *requested cache medium*. The auxiliary cloud services hold **only trust authority/floor**, not a replacement for the Drive candle cache.

**Benefits:** Cloud KMS central key versions, externally managed access policy; Firestore transactions provide serializable conflict control and atomic same-record check/update. Separate resource/project IAM and admin custody can reduce single-PR actor control.

**Critical unresolved points:** Firestore transaction consistency is not immutable/admin-proof custody: project admins can still change IAM, delete/reset databases or disable retention; independent organization audit, backup, alerting and WORM/secondary witnesses may be necessary. A Firestore transaction does not atomically commit GitHub ref and Drive bytes; explicit prepare/commit/read barrier and crash-recovery protocol still needed. KMS signer authorization, key algorithm/protection tier, actual product entitlement, quotas/cost, region, identity setup, audit retention and owner-managed emergency revoke require validation. No external service may be provisioned without owner explicitly expanding the project scope beyond GitHub + Google Drive.

**Disposition:** ALTERNATIVE ON HOLD; user chose Option A, so Cloud KMS/Firestore are **out of current approved scope**. Must obtain a new explicit platform decision before any such service could be considered. Not selected or deployed.

### C — GitHub Actions cache / Google Drive files as the sole trust root and mutable floor (REJECT)

**Reason:** Evictable/mutable cache, caller-resettable local floor, self-hashed metadata, missing independent signer custody, no external two-writer server transaction, no guarantee latest head, and no admin-proof revocation. `G01=FALSE`, `G02=FALSE`; never reclassify an existing green synthetic CI run as a production proof.

## 4. Suggested service-neutral protocol (not a deployment plan)

**Phase 0 — Independent bootstrap:** Two authorized owner principals approve policy version, stable namespace canonicalization, rightsholder terms (G04), privileged actor inventory, supported signature algorithm/key IDs, effective protected witness rules, and initial external floor from a fully verified source snapshot. Require a second authorized witness/readback and immutable decision receipt. No bootstrap from an untrusted GitHub Actions cache.

**Phase 1 — Prepare:** Writer authenticates to a separate gate, fetches root/registry+floor (not from its PR-controlled environment), validates rights and source first-known/revisions; stages immutable content bytes in Drive under legal retention contract and computes authenticated SHA256 by reading the object bytes back. Produce a PENDING manifest with idempotency key; do not expose to readers.

**Phase 2 — Candidate:** Verify signed canonical receipt, approved key epoch, rights-policy SHA, partition and current head; create GitHub commit/tree with exactly one expected parent if authorized, but do not call it committed simply because GitHub returns 2xx or a commit object exists.

**Phase 3 — Atomic admission:** An owner-governed authority atomically compares `expected_head` to the protected floor and conditionally sets the next generation/head/epoch/source revision watermark. Conflict returns `CONFLICT_BLOCKED` with no success receipt. Where using Git-only candidate, protection/FF and other service barrier must still be reconciled; a transaction in Firestore alone does not make Drive+Git atomic.

**Phase 4 — Confirm:** An independent reader fetches current root/registry/revocation and protected floor, then actual Drive bytes and protected Git commit/ref/tree. Final witness/readback must match after Drive verification; if any pair diverges, return `PARTIALLY_COMMITTED_BLOCKED` or `UNKNOWN_BLOCKED`, never grant access.

**Phase 5 — Recovery:** Unknown HTTP response, stale reader, partial Drive stage, ref loss, suspect key, provenance correction, disabled provider license, or reset admin permissions must enter quarantine/journal. Re-run deterministic readback using the same idempotency key; owner-approved recovery always links old accepted floor, NEVER lowers it. A backup restore is not authorization to rewind the floor.

## 5. Threat/test matrix — owner acceptance requires independent evidence

| Test ID | Attack/fault | Required result |
| --- | --- | --- |
| G01-T01 | PR author substitutes signing public key+matching SHA | No trusted enrollment; BLOCK |
| G01-T02 | Revoked key/old token across two accounts | Both reader and writer reject, no stale privilege |
| G01-T03 | Git verified commit signed by *unapproved* actor | Reject; signature shape alone insufficient |
| G02-T01 | Restore old signed registry after newer generation | Reject from external floor |
| G02-T02 | Two independently authenticated sibling writers | Exactly one atomic winner; loser BLOCK and readback |
| G02-T03 | Restart/new runner/new service account, then replay G1 | Reject without trusting caller floor |
| G02-T04 | Unauthorized admin force-push, delete or policy bypass | Remote enforcement rejects OR independent tamper alarm + quarantine; never silently accept |
| G02-T05 | Cross-provider, symbol, TF or rights-policy transplant | Reject |
| G02-T06 | Key rotation/revoke then bootstrap at generation 1 | Reject unless owner-approved continuity to protected floor |
| G02-T07 | Valid vendor correction/backfill with earlier source time | Enforce licensed revision/as-of policy; not blindly block by clock |
| M4-T08 | Crash after Drive upload but before Git ref/floor | No successful read; idempotent recovery/garbage collection |
| M4-T09 | Crash after head advance but before receipt confirmation | Stable independently attested readback; no double-publish |
| M4-T10 | Expired/revoked provider entitlement | Block reader/write despite valid old SHA/signature |

All tests need **actual authenticated, independently controlled principals and physical remote readbacks** for an M4 production claim. Offline/fixture outputs remain UNATTESTED.

## 6. Required owner decision record — NO default authorization

| Decision | Options and impact | State |
| --- | --- | --- |
| D01 custody boundary | A GitHub+Drive-only architecture explicitly selected; controller identities, independent trust and privileges still unresolved | SCOPE CHOSEN A / CUSTODY APPROVAL OPEN |
| D02 root signer/controller | Named owner role, emergency revoker, distinct publisher/verifier admin, explicit bypass inventory | OPEN |
| D03 durable floor | Exact authority, namespace scope, CAS semantics, retention, backups, external tamper monitor | OPEN |
| D04 publisher/reader identity | Two actual independent principals; OIDC binding/ref restrictions and short-lived credentials | OPEN |
| D05 vendor G04 scope | Separate SSI/DNSE/VCBS rights, first-known corrections, legal Drive retention, broker restrictions | OPEN |
| D06 disaster/recovery | Unknown response, compromise, global revoke, provider changes, immutable recovery/rollforward | OPEN |
| D07 costs/operations | Extra cloud allowed? provider budget/IAM, owner pager, failure modes, data residency | OPEN |
| D08 acceptance | Owner G01–G08, A02/A03, M3/M4/M8 signoff and no self-attested promotion | OPEN |

**Current next action:** implement/read-only-test the Option A GitHub+Drive custody design. Owner still needs to approve concrete signer/controller identities, effective protections, witness creation, licensed data and real-custody testing. If Option A demonstrably cannot satisfy G01/G02, report the gap to the user for a *new explicit platform-scope decision*; never silently activate Cloud KMS/Firestore. This ADR selection is architecture-only.

## 7. External reference facts (read-only research; verify again at deployment)

- GitHub rulesets can restrict deletion/force-push and require signed commits, and include bypass actors; signature verification checks Git commits, not vendor data or owner key entitlement. https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets
- Firestore transactions are serializable by commit time; contention and retries occur, and this does not protect against privileged administrative reset. https://firebase.google.com/docs/firestore/transaction-data-contention
- Workload Identity Federation supports GitHub OIDC without static service account key files; IAM claim binding must be restrictive. https://docs.cloud.google.com/iam/docs/workload-identity-federation
- Cloud KMS supports asymmetric signing including Ed25519 at certain protection levels; select exact protection tier before relying on it. https://docs.cloud.google.com/kms/docs/algorithms

**Dossier verdict:** `M4_OPTION_A_SCOPE_SELECTED_G01_G02_SECURITY_AND_PRODUCTION_BLOCKED`. Every operational gate stays OPEN, `cache_read_authorized=false`, `cache_write_authorized=false`, `trading_authorized=false`. Signed reader receipt, licensed cache, live deployment and trading remain blocked.
