# MST M4 — Option A owner / signer / writer / reader duty-separation review

**Status:** PROPOSED ONLY — ZERO REAL IDENTITIES ENROLLED, ZERO PRIVILEGED RIGHTS APPROVED  
**Scope:** User-selected **Option A: GitHub + Google Drive only**. No Cloud KMS, Firestore, other external compute/storage, Mac, MOCHI or local dependencies. Draft [PR #8](https://github.com/ngluonghoa/MST/pull/8), not main.  
**Pinned baseline:** Swing Trading 1.8 `cd90c1babae8912db31490ad614fc2ad2f868042`; MST protected `main@4048f91beaaa3410116d97e35896c8b688384e19`; 63 original V1 modules unchanged.  
**Record:** `docs/MST_M4_OPTION_A_ROLE_SEPARATION_PROPOSAL_20261109.json`, checked by `scripts/m4_option_a_role_separation_preflight.py` (test-only, **not** an IAM enforcement service).

## 1. Why a separate custodian matters

Actual prior read-only API observations [live ACL QA](docs/MST_M4_OPTION_A_LIVE_CUSTODY_GAP_QA_20261109.md):

- GitHub `MST - Protect Main` active ruleset #26801439 protects `main` against non-FF/delete, requires PR and three foundation CI contexts, but has **zero required approving reviews**, strict up-to-date CI disabled, and does not include a signed-commit requirement. This is a **source-main** rule, **not** a separately authenticated M4 trust root.
- M4 authoritative witness `refs/heads/mst/m4-witness/v1` does not exist. Classic main protection GET 403 for integration; the GitHub Actions token could not view bypass list, while another connected GitHub identity saw it empty. This is a visibility boundary, not independently certified administrator isolation.
- Google Drive metadata on five MST project folders: `shared=false` and one visible `owner` role per folder. This is NOT a proof of separate human owner, not proof of a nonerasable Drive object, and not proof of SSI/DNSE/VCBS rights. Do not post owner emails or access credentials in a public repo.
- An attacker controlling one administrator who can replace both GitHub rulesets/trust registry and Drive bytes may forge an apparently continuous history. **Two different role *names* or GitHub logins do not prove independent owner custody**, because they may share a human, admin recovery, app installation or billing/root control.

## 2. Concrete proposed zero-assignment RACI-like topology

Every role below is a **slot awaiting specific owner approval**, not a provisioned account, secret or permission grant.

| Role | Proposed authority boundary | Forbidden until proven |
| --- | --- | --- |
| `POLICY_CONTROLLER` | Owner-governed GitHub witness policy/ruleset, inspect bypass | Publish market cache; enroll signing key; self-certify policy |
| `SIGNER_ROOT_CUSTODIAN` | Separate owner-approved signer registry/key-enrollment approval | Modify witness rules; write data; self-authorize key |
| `REVOCATION_CONTROLLER` | Independent emergency key/rights revocation and recovery review | Sign/approve own emergency revocation, write cache, bypass policy |
| `WITNESS_WRITER_A` | Restricted authenticated GitHub append-candidate writer | Change rules, delete/force-push, reset genesis floor |
| `WITNESS_WRITER_B` | Second separately authenticated append writer for race test | Same; must not equal A, root custodian or policy admin |
| `DRIVE_CHUNK_WRITER` | Future provider-licensed Google Drive chunk staging only | Change witness policy, enroll signer, delete accepted cache |
| `READ_ONLY_VERIFIER` | Independent current witness/registry/Drive physical bytes reader | Write Git/Drive, grant own data admission, sign as publisher |
| `PULL_REQUEST_CI` | `contents:read` only and synthetic QA | Any production writer, root signer secret, vendor token, owner approval |

Proposed **25 pairwise no-shared-principal constraints** are encoded verbatim in the JSON. The most critical: policy vs signer; policy vs both writers; signer vs both writers; writer A vs B; both writers vs verifier; revocation controller vs signer/policy/writers/reader; Drive writer vs verifier; PR CI vs every privileged domain. Distinctness must ultimately be proven against real GitHub and Drive principals and their common control roots, **not inferred from the names entered into this JSON**.

## 3. Governance for GitHub-only trust and signer key lifecycle

Option A may use separate owner-governed GitHub witness repository or an isolated protected witness ref, but neither is **created** by this work. Exact choice and policy creation require owner permission. Separate repository is preferred for isolation **only after** proving the real owner/admin/recovery graph differs from the PR source repository; moving to a second repository controlled by the same unrestricted administrator does not create an independent root.

A proposed signing workflow could use tightly restricted GitHub owner-controlled environments with manual approval and branch/ref/workflow restrictions, but **never put signer private keys or vendor credentials into a pull_request workflow**. GitHub-hosted environment secrets are not equivalent to non-exportable hardware-backed keys; a privileged workflow or owner administrator might exfiltrate/reset secrets. Any actual key generation, environment secret upload, separate repo or app authorization is a **future explicit owner-gated change**. Do not imply that existing Actions runs already sign trusted receipts.

For protected witness writes, two independently authenticated low-privilege writers must present receipts with the **same expected parent**. A GitHub non-force ref update and FF ruleset must be tested under owner-approved accounts, including race/retry/ambiguous response. GitHub's ref status alone does **not** atomically commit Drive data; independent reader must fetch current protected head, rights/revocation and real Drive bytes, and recheck the head after bytes. A root administrator's ability to replace history, alter protection or restore old floor must be independently detected; otherwise G02 remains BLOCKED.

**Explicit scope limitation:** If the only existing person/account can override both sides, or GitHub + Google Drive cannot meet the owner-approved adversarial floor test, report it as an unresolved architectural limitation. Do not weaken G01/G02, pass a self-hash as signer authentication or silently add Cloud KMS/Firestore.

## 4. Owner decisions still required — all OPEN

| ID | Separate approval packet | Evidence prerequisite |
| --- | --- | --- |
| R01 | Witness policy controller and effective bypass/admin inventory | Real GitHub admin access graph including bypass and recovery paths, separately witnessed |
| R02 | Independent signer registry custody and emergency revoker | Verifiable key issuance/epoch/revoke flow with separate approver; no PR secrets |
| R03 | Two GitHub writer identities / protected head concurrency | Different authenticated principals with exactly one winner under server CAS and fault recovery |
| R04 | Independent Drive content writer/verifier permission scope | Actual physical Drive object readback, restricted sharing/deletion, separate read identity |
| R05 | Owner-approved witness ref + ruleset creation | Exact ref scope, force/delete prevention, signed-commit plan, owner rollback |
| R06 | Owner decision on main's zero-review count, non-strict status policy and code-signature policy | Explicit configuration review; **do not auto-change main** |
| R07 | Licensed SSI/DNSE/VCBS first-known/revisions, source corrections and Drive retention | Provider permission and retention boundaries, not publisher's SHA |
| R08 | High-water floor, global revocation, shared administrator reset and disaster recovery | Independent adversarial root/admin rollback alert + quarantine, approved recovery without lowering floor |

All are `OPEN`, every `principal_binding` is `null`, `independent_identity_verified=false`. Neither assigning dummy names nor green synthetic CI can close any row. All SIGNED-G01..G08, A02 63 module owner dispositions, A03 opt-in ABI, M3/M4/M8 release remain OPEN.

## 5. Proposed acceptance sequence, never automatic authorization

1. Review with owner what distinct human/admin accounts actually exist for GitHub policy, signer root, Drive and revocation. Determine shared root/bypass risk; no public username/email in QA.
2. Approve *specific* witness design (separate repo vs scoped ref), list exact roles, repo IDs, workflow references and reason for each privilege. If unable to isolate root, mark security gap OPEN.
3. Only after separate approval, provision the witness protection and perform live **read-only** independent readback plus signed-root enrollment, then two-account single-winner CAS. No PR-triggered privileged secrets.
4. Only after vendor legal and source time semantics are approved, verify real physical immutable-by-policy Drive chunks and two-service crash recovery; do not confuse Google Drive content SHA with official vendor signatures.
5. Final acceptance requires separately signed owner approval and red-team proof against attacker controlling a PR, ordinary writer, signer, and privileged admin. Partial/unknown/403 must BLOCK rather than authorize.

## 6. Machine-enforced draft-only boundaries

`scripts/m4_option_a_role_separation_preflight.py` freezes 8 slots, 25 no-alias pairs, 8 OPEN owner decisions, 9 protected actions. A hypothetical-alias function rejects role collisions but **always returns independent-owner verified=false and production authorized=false**, including when all eight synthetic aliases differ. CI is `contents:read` on exact same-repo Draft PR #8; resulting temporary JSON artifact is an unauthenticated review packet, not a global floor, signer receipt or legal vendor data source.

**Next permitted Cloud-only work:** owner IAM/bypass review checklist, static threat modeling, independent GitHub + Drive visibility inventory and exact approval form. Protected ruleset/ref writes, new credentials, real market cache ingestion, main policy changes and PR merge require additional explicit owner approval.
