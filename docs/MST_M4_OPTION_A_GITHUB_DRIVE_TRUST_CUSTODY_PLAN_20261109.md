# MST M4 — Option A implementation blueprint (GitHub + Google Drive ONLY)

**Decision:** The user explicitly selected Option A ("Đồng ý phương án A") on 2026-11-09. **Selection scope:** architecture/platform choice **ONLY**, not a credential, signer enrollment, source license, branch-policy change, protected witness provisioning, live cache publication or release sign-off.  
**Status:** SELECTED_FOR_DESIGN / NOT PRODUCTION READY / OWNER CONTROL GATES OPEN.  
**Authoritative choice overlay:** `docs/MST_M4_OPTION_A_SCOPE_SELECTION_20261109.json`. Historical unselected ADR draft `docs/MST_M4_G01_G02_OWNER_DECISIONS_20261109.json` remains unchanged as a snapshot, not the current choice. See existing ADR `docs/MST_M4_ADR_G01_G02_TRUST_ROOT_MONOTONIC_FLOOR_20261109.md`.

## 1. Platform and source restrictions

**Allowed services only:** GitHub (repositories, read-only CI, protected refs/rulesets with owner approval, GitHub-native identities/automation) and Google Drive (canonical Docs/QA and, once licensed, immutable-by-convention content-addressed cache chunks and manifests). Do **not** provision GCP Cloud KMS, Firestore, Azure, AWS, other key vaults, databases, or independent external queue/storage services. "GitHub + Google Drive" means using **these services**, not relying on a Mac, MOCHI, developer laptop or local permanent state.

Keep inherited Swing Trading 1.8 pinned source commit `cd90c1babae8912db31490ad614fc2ad2f868042`, MST `main@4048f91beaaa3410116d97e35896c8b688384e19` with tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e` and 63 original V1 modules byte-identical. Draft PR #8 is the **only** test-candidate branch; no merge without owner parity and ABI acceptance. No live trading or vendor OHLCV ingestion without licensed G04 approval.

## 2. Option A custody topology — proposal, not provisioned

**Domain A — code & QA:** Existing `ngluonghoa/MST`, protected `main`, untrusted Draft PR #8 and `contents:read` PR-triggered GitHub Actions. No production signer secrets or Drive writer tokens may appear in an unreviewed PR. Runner artifacts and cache are temporary proof, **never** monotonic authority.

**Domain B — independent owner-controlled witness custody:** Proposed separately governed GitHub witness repository **or** an effectively isolated protected witness ref `refs/heads/mst/m4-witness/v1` with all bypass actors/administrator powers inventoried. Optionally separate owner-controlled signer registry from publisher workflow. Nothing has been created or enabled. Evaluate whether administrators of Domain A can bypass/replace the Domain B trust root; a separate repository owned by the **same unrestricted admin** may not add independent authority.

**Domain C — licensed physical data custody:** Existing owner-controlled Google Drive cache parent; each authorized vendor/partition/TF chunk is staged as a distinct content-addressed object, with exact Drive object ID, SHA256 computed from **read-back bytes**, legal provider contract/license and revision/as-of metadata. Drive file IDs and checksums alone cannot stop file deletion, unauthorized rewrite, contract expiry or privileged rollback. Readers must block on unavailable/corrupt/deleted chunks. No raw vendor bytes in GitHub Actions logs/artifacts.

**Independent observer and escalation:** A reader with a **different approved identity** obtains both the actual witness head and current independent registry/floor, verifies physical Drive bytes, and re-reads the witness after verification. Admin bypass, root reassignment or policy deletion requires independently reviewed alert/quarantine and owner signoff; unless that can be demonstrably enforced using only GitHub+Drive, G01/G02 must remain OPEN. Neither Cloud-only nor a signed Git commit by itself guarantees independence.

## 3. Canonical writer/read protocol (design contract)

1. **Bootstrap (owner gated):** Owner approves root signing key custody, admission of producer/verifier identities, partition normalization, source entitlements, witness ref ruleset, bypass inventory, floor genesis tied to verified prior source, and recovery authority. Do not initialize from Actions cache or caller-supplied G1 floor.
2. **Acquire trusted floor:** Writer obtains current protected registry digest/authorized signer epoch and **current** per-provider+symbol+TF+rights/adjustment policy `head_sha + generation + manifest_sha + source_revision_watermark`; namespace collisions and source license mismatch block.
3. **Stage physical Drive chunks:** Under licensed retention, write a new content-addressed object only once, re-fetch physical bytes, compare SHA256 and immutable manifest claims. Stage=PENDING, not visible to cache consumers. If Drive I/O unavailable, fail closed.
4. **Propose append:** Generate a canonical signed receipt with expected parent/head, monotonic generation, key epoch, rights policy digest, vendor source-first-known/revision (corrections treated according to contract, not naive clock), Drive ID/SHA, and idempotency key. Proposed Git commit parent must be exactly the observed protected head.
5. **Atomic witness transition:** After owner-reviewed writer enrollment, use an independently verified GitHub ref update with `force=false` and an authenticated expected head. A concurrent update must have at most one winning ref transition; the loser must read the actual new head and abort/rebase only under the independent policy. **GitHub FF by itself is not vendor authority nor an atomic Drive commit.**
6. **Read barrier:** Independent verifier checks owner signer registry and current floor, signed receipt, GitHub commit/tree/ref/head lineage, actual Google Drive bytes and rights, then re-reads GitHub ref/floor. Any mismatch, concurrent newer state, lost entitlement or revoked key = BLOCK/QUARANTINE.
7. **Recovery:** Drive-only orphan, Git-only orphan, ambiguous timeout, stale signed ref, admin-policy change, deleted Drive object or compromised key never means success. Resume from the idempotency journal and the **highest independently accepted prior floor**; do not lower generation on key rotation/restore.

**Unproven safety boundary:** A protected append-only GitHub branch can prevent ordinary force-updates and provide a linear ref when protection works. It is **not** an indestructible external clock or automatic two-service transaction, especially under privileged administrator or policy-bypass threat. M4 must either demonstrate sufficient independent detection/rollback refusal with the authorized GitHub+Drive principals, or remain BLOCKED. This selection does **not** relax SIGNED-G01/G02.

## 4. Concrete acceptance evidence required before any real provisioning

| Gate | Owner-controlled proof | Current |
| --- | --- | --- |
| A-CUSTODY-01 | Actual separate controller identities, GitHub admin/bypass policy scope, rule audit, and anti-secret-exfiltration workflow review | OPEN |
| A-CUSTODY-02 | Owner-approved signer key enrollment/revocation, protected public registry and two identities rejecting unknown/compromised key | OPEN |
| A-FLOOR-01 | Protected authoritative namespace floor survives separate GitHub-hosted runs, account switch, restore, and older signed G1 replay | OPEN |
| A-FLOOR-02 | Independent second account with permissible write scope: two simultaneous sibling writers produce one accepted head and one rejected actor | OPEN |
| A-FLOOR-03 | Owner/admin bypass and deletion/force-push detection: no silent history downgrade to readers; fail closed under unverifiable metadata | OPEN |
| A-SOURCE-01 | Licensed SSI/DNSE/VCBS rights and as-of correction/retention semantics, not inferred from SHA/signature | OPEN |
| A-DRIVE-01 | Actual Drive immutable chunk bytes read back by separate approved reader, verified ID/SHA and revocation/retention policy | OPEN |
| A-RECOVERY-01 | Fault-injected GitHub/Drive partial commit, idempotency, final-readback fencing and no-caller-floor reset | OPEN |
| A-GOV-01 | Owner approves 63 A02 dispositions, A03 ABI, M3/M4/M8 and no live-order policy | OPEN |

**Go/no-go:** 9/9 infrastructure acceptance rows remain OPEN; SIGNED-G01..G08 remain OPEN. A user selecting the architecture may approve further *read-only design/QA*, but does not automatically approve any GitHub admin settings, separate privileged repo, new writer identities, cryptographic signer material or real vendor transport.

## 5. Next executable steps without new approval

- Keep PR #8 Draft/unmerged and root source locks; add an **Option A selection-only** read-only CI guard validating source pins, exact permitted platforms, historic proposal snapshot, and all G01..G08 still OPEN.
- Read existing GitHub ruleset/ref metadata and current Drive project folder ACL metadata through connected APIs only; produce a **gap inventory**, not a trust attestation. Current read-only GitHub M4 witness preflight confirmed the proposed ref/ruleset absent.
- Develop standalone, adversarial **contract tests** for A-style witness/floor semantics (legacy signed siblings, caller reset, owner bypass, revoked signer, cross-GitHub/Drive crash). These are models and must stay UNATTESTED until two independent actual authenticated principals and physical licensed chunk readbacks exist.
- Generate exact owner approval packets for each privileged action, identifying intended actors, resources, protections, rollback, legal constraints and acceptance test. Request authorization only at the exact owner-gated step.
- Do not add Cloud KMS/Firestore back by inference. If Option A cannot satisfy strong G01/G02, record the demonstrated limitation and escalate an *explicit separate scope choice* to the user; do not silently weaken acceptance or use new cloud resources.

## 6. Status statement to carry forward

`OPTION_A_GITHUB_GOOGLE_DRIVE_SELECTED_FOR_ARCHITECTURE_SCOPE=true`; `APPROVED_PLATFORM_EXTENSION=false`; `PROTECTED_M4_WITNESS_PROVISIONED=false`; `OWNER_SIGNER_ENROLLED=false`; `G01/G02_INDEPENDENT_TRUST_VERIFIED=false`; `SIGNED_G01_G08_ALL_OPEN=true`; `LICENSED_REAL_CACHE_PUBLISH_AUTHORIZED=false`; `M5/M8_RELEASE_AND_TRADING=BLOCKED`.

The historical 2026-11-09 unselected decision proposal is retained for audit; the **new versioned selection overlay** is the current architecture-choice source of truth, and cannot be interpreted as privileged acceptance.
