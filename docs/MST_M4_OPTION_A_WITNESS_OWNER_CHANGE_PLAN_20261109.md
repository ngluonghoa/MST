# MST M4 — Option A witness protection owner change plan (review only)

**Decision status:** GitHub + Google Drive **selected for MST scope**; **M4 witness provisioning NOT authorized**.  
**Draft:** [MST PR #8](https://github.com/ngluonghoa/MST/pull/8), unmerged.  
**Owner change packet:** `docs/MST_M4_OPTION_A_WITNESS_OWNER_CHANGE_PACKET_20261109.json`.  
**Witness ref proposed:** `refs/heads/mst/m4-witness/v1`, **currently absent**; do not confuse earlier `mst/m4-witness-test-only/*` references with authority.  
**Main:** existing `main@4048f91beaaa3410116d97e35896c8b688384e19` is protected and MUST NOT change during this work. No 63 inherited V1 source modules changed.

## 1. What must be approved — and what this plan does not approve

This packet is an **exact proposed change sequence**, not a GitHub Admin API request or implicit delegation to ChatGPT. It does NOT create GitHub repos/refs, update a ruleset, change the main review count, grant an app permission, generate signer keys, add secrets, add Google Drive sharing, ingest SSI/DNSE/VCBS data, publish cache, merge PR8 or trade.

The user selected **Option A (GitHub + Google Drive only)**. That allows design and read-only testing without another cloud vendor; it does **NOT** resolve whether the real owner can meet G01 independent signer custody and G02 non-resettable rollback floor using only these products. Root/admin-level rollback or policy replacement remains the central unresolved threat. If this cannot be demonstrated with distinct independently controlled owners/watchers, **do not relax G01/G02 to get a green report**.

**Before any new privileged operation** obtain separate owner approval identifying exact target repository/ref, controller principal(s), permissions, expected new metadata, independent verifier, rollback/recovery and an explicit go/no-go. No action in this document is a prior blanket authorization.

## 2. Exact read-only current baseline

| Evidence | Actual observation | Caveat |
| --- | --- | --- |
| Main GitHub ruleset | `MST - Protect Main`, ID `26801439`, `~DEFAULT_BRANCH`, active | Protects main, not the M4 witness |
| Main required rules | `deletion`, `non_fast_forward`, `pull_request`, `required_status_checks` (3 foundation CI contexts) | Exact main rules not changed here |
| Main approving reviews | `required_approving_review_count=0` | A PR does **not** require an approving review under this particular rule |
| Main signatures | no `required_signatures` in inspected rule | Not equivalent to M4 signer enrollment |
| Main CI freshness | `strict_required_status_checks_policy=false` | Owner decision needed before any policy update |
| Witness `mst/m4-witness/v1` | HTTP 404, absent | All `test-only` refs remain untrusted |
| GitHub classic protection endpoint | 403 for integration token | A permission gap, **not** evidence main is unprotected |
| Bypass actors | GitHub connector token saw `[]`; PR Actions token did not see list | Token visibility differs; no independent admin-bypass proof |
| Google Drive MST five folders | `shared=false`, one visible `owner` per folder | Does not prove two independent controllers or physical licensed cache bytes |

The current main/Drive observations are **snapshots from specific tokens**, not a universal real-time administrator/root attestation. Only the GitHub branch/ref/ruleset observations are live inside the GitHub-hosted preflight. Google Drive metadata was read separately through the connected Drive API.

## 3. Exact *proposed* witness ruleset (DO NOT APPLY)

Existing validated source: `docs/MST_M4_WITNESS_RULESET_PROPOSAL_20261109.json`. For the **specific witness ref only**, proposed:

| Property | Proposed value | Reason |
| --- | --- | --- |
| Target | `branch` | Scope only Git refs |
| Ref include | `refs/heads/mst/m4-witness/v1` | Never affect main, PR8 or synthetic branches |
| Ref exclude | `[]` | No hidden exclusions |
| Enforcement after bootstrap | `active` | Must independently confirm application |
| Deletion | prohibited | Prevent ordinary ref deletion |
| Non-fast-forward | prohibited | Prevent ordinary forced rewrites |
| Required signatures | enabled | Require Git verified commits, **not** vendor attestation |
| Bypass actors | proposed `[]` | Actual effective rights/bypass must be read back by an independent administrator |
| `creation` rule | **not proposed** | Could prevent genesis bootstrap without approved bypass |
| `update` rule | **not proposed** | Could lock out future legitimate append writers |
| PR requirement on witness | **not proposed** | Current candidate flow models protected append. Enforcing PR flow would need distinct owner-approved writer/publisher design |

GitHub rulesets can be layered with other protections. Creating an exactly scoped ruleset must be verified by effective policy readback, not merely by name or screenshot. A new enforced `required_signatures` rule may prevent legitimate automation from writing unless its key and workflow are signed/enrolled correctly. No repository-admin role is automatically equivalent to an independent signer root.

**Separate main change:** main PR approval count=0 and CI strict flag=false have been observed but are **NOT IN SCOPE for an automatic change**. Review them as owner decision C01/C08 and issue #15 before submitting a separate concrete main policy diff. This packet MUST NOT mutate `main`.

## 4. Ordered execution with stop/rollback semantics

These **ten steps S00–S09 are recorded as NOT_EXECUTED**. S00/S01 are review/read-only steps; S02–S09 demand separate independent owner approval, even when the step would primarily collect evidence.

| Step | Proposed action | Required condition | STOP condition |
| --- | --- | --- | --- |
| S00 | Read GitHub main/ruleset/ref and Drive folder ACL metadata | Connector read-only | Missing or 401/403/429 => UNKNOWN/BLOCK, not absent |
| S01 | Inventory actual policy root, signer root, revoker, 2 writers, Drive writer and independent reader | Confidential owner review | Shared control root or hidden bypass => BLOCK |
| S02 | Approve exact ref and genesis lineage/head/rights namespace | Owner signed permission and independent floor provenance | Genesis based on Actions cache or caller-provided floor => BLOCK |
| S03 | Bootstrap proposed branch/ref with verified genesis before restrictive rule | Explicit separate owner approval, verified actor, ref readback | Unknown response => quarantine, never blindly retry |
| S04 | Apply exact witness-only deletion/non-FF/signed-commit rules | Explicit separate owner approval, no broadened ref or unreviewed bypass | Mismatch, admin bypass or lockout => BLOCK; quarantine while reverting only via owner recovery |
| S05 | Independently re-read ref/head/commit/tree and effective protection | Different verified read principal; full bypass visibility | 403/partial metadata or drift => BLOCK |
| S06 | Owner-enroll signer registry, 2 independent low-privilege writers, reader | Privileges restricted to exact operations/refs; no PR secret | Role overlap or same controlling admin => BLOCK |
| S07 | Real sibling writer CAS, stale signed receipt and administrator rollback test | 2 real authenticated principals, verified protected floor | Two winners, G1 replay, administrator reset undetected => BLOCK |
| S08 | Licensed Google Drive physical chunk SHA, rights/revisions/retention and two-service crash test | G04 vendor rights/retention cleared, physical byte readback | Deleted/mutated Drive chunk, lost Git ref, ambiguous receipt => BLOCK |
| S09 | Final owner G01–G08 + A02/A03/M3/M4/M8 go/no-go | Independent approval chain and release evidence | Any open gate => NO RELEASE/NO TRADE |

**Recovery is not reset:** If a ref is rewritten, a ruleset disabled, key compromised, Drive object lost or an admin can bypass, do not create a new genesis `G1` over an accepted `G2` and call the history fixed. Freeze writers/readers, quarantine damaged data, re-fetch a previously externally anchored monotonic floor, independently attest the unchanged accepted history and pursue a documented owner-authorized forward-only recovery. If the protected floor itself is resettable, this Option A acceptance test is **not satisfied**.

## 5. Owner approval checklist C01–C08 (all OPEN)

- **C01 — controllers:** separate policy/admin/root & bypass inventory; user/root-sharing risk, hidden installation/admin rights, recovery controls.
- **C02 — custody decision:** this exact witness ref under MST vs a separately owned GitHub witness repository; explicitly show which administrator can change each.
- **C03 — genesis:** independently verified first accepted floor/lineage and bootstrap approval **before** enabling restrictive rule.
- **C04 — ruleset:** explicit GitHub changes approval with exact ref/rule JSON and independent post-change readback.
- **C05 — identity:** two distinct real writer credentials, signer key custody, independent reader and source rights owners.
- **C06 — adversarial proof:** real CAS one winner/one loser, stale receipt rejection, admin bypass/reset detection, quarantine.
- **C07 — Drive/vendor/recovery:** licensed SSI/DNSE/VCBS rights and source revisions, physical Drive chunks and two-service recovery, global revoke.
- **C08 — release governance:** source parity owner signoff 63, ABI owner approval, M3/M4/M8, no trading until release.

**No approver principal, proof URI or acceptance signature has been entered.** This is intentional: a PR-controlled field cannot itself establish owner identity, even if it contains a legitimate-looking link.

## 6. Feasibility risk: the strongest unresolved condition

GitHub signed commits verify eligible Git signatures, not vendor data origin; GitHub branch rulesets enforce ordinary ref operations but privileged administrators may change repository settings. Google Drive content bytes or an item labelled "immutable" may be deleted or replaced by sufficiently privileged actors. If one real controller can change both GitHub and Drive, the pair is not a trustworthy independent witness even when it has two account names.

Under strict GitHub+Drive-only scope, a high-security, independently non-resettable rollback floor **may not be demonstrable** with current ownership/custody. Therefore this plan deliberately supports a **NO-GO** disposition rather than false positive G01/G02 closure. There is no automatic fallback to Cloud KMS/Firestore or any other unapproved platform.

## 7. Verification source and next safely executable work

- Existing current GitHub owner/witness proposal: `docs/MST_M4_WITNESS_RULESET_PROPOSAL_20261109.json`; signed-floors issue [#16](https://github.com/ngluonghoa/MST/issues/16) and witness governance issue [#15](https://github.com/ngluonghoa/MST/issues/15).
- Option A role separation: `docs/MST_M4_OPTION_A_ROLE_SEPARATION_PROPOSAL_20261109.json`.
- Machine-readable change packet: `docs/MST_M4_OPTION_A_WITNESS_OWNER_CHANGE_PACKET_20261109.json`.
- CI-only fail-closed packet check: `scripts/m4_option_a_witness_change_preflight.py` + `tests/test_m4_option_a_witness_change_preflight.py` + `.github/workflows/m4-option-a-witness-change-review.yml`.
- Current public GitHub documentation for ruleset layering, bypass actors, signed commits and branch creation nuances: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets and https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets

**Outcome:** A reviewed change plan can be prepared without touching privileged infrastructure. No production read/write/trading authorization exists; PR8 stays Draft and protected main/source parity stays intact.
