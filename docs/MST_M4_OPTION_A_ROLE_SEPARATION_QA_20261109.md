# MST M4 — Option A owner / signer / publisher duty-separation QA

**QA-ID:** MST-M4-OPTION-A-ROLE-001 · **Date:** 2026-11-09 Asia/Ho_Chi_Minh  
**VERDICT:** **ROLE DESIGN & BLOCKING TESTS PASS. OWNER IDENTITIES / SIGNER ROOT / PROTECTED FLOOR / REAL PUBLISHING NOT PROVISIONED OR AUTHORIZED.**  
**Scope:** user-selected Option A **GitHub + Google Drive ONLY**. No Mac, MOCHI, local project runtime, third-party Cloud service, trading or live licensed data.

## 1. Source lock and exact change

Pinned Swing Trading source `cd90c1babae8912db31490ad614fc2ad2f868042`; MST protected `main@4048f91beaaa3410116d97e35896c8b688384e19` with tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`. All 63 inherited V1 Python modules and pre-existing V2 modules are unchanged. New files ONLY on open **Draft PR #8**:

- `docs/MST_M4_OPTION_A_ROLE_SEPARATION_PROPOSAL_20261109.json`: eight **unassigned** role slots and their proposed/forbidden capabilities; 25 no-shared-principal pair constraints; eight unresolved owner decisions R01–R08; 9 owner-gated privileged actions.
- `scripts/m4_option_a_role_separation_preflight.py`: strict source-bound schema validator and role/permission guard. Returns `OPTION_A_DUTY_SEPARATION_DESIGNED_ALL_REAL_ROLES_UNASSIGNED`, **not** owner approval. Also offers a synthetic *alias-collision* analyzer, whose output NEVER authorizes data access, even with eight distinct dummy names.
- `tests/test_m4_option_a_role_separation_preflight.py`: **42 new tests** for role rights, forbidden privilege changes, missing owner fields, no self-enrollment, source/Main SHA drift, reviewer count and Drive role baseline, 25 no-alias pairs, 9 owner-only operations, same-account signer/policy/writers and fake PR CI owner privileges.
- `docs/MST_M4_OPTION_A_ROLE_SEPARATION_OWNER_REVIEW_20261109.md`: operational Option A RACI-like review, exact role boundaries, signer/key limitations, admin/root rollback threats, and owner decision packets R01–R08.
- `.github/workflows/m4-option-a-role-separation-review.yml`: same-repo **PR #8-only** GitHub-hosted read-only CI, `permissions: contents: read`, temporary review artifact. No protected branch, ruleset, keys, Google Drive sharing, actual cache or vendor access writes.

## 2. Why this specific design

Previously observed **actual GitHub/Drive** ACL metadata (separate [QA](docs/MST_M4_OPTION_A_LIVE_CUSTODY_GAP_QA_20261109.md)) shows main ruleset #26801439 active but `required_approving_review_count=0` and no `required_signatures` in the inspected main rule; M4 authoritative witness ref `refs/heads/mst/m4-witness/v1` is absent. Classic branch protection endpoint is 403 for integration and PR CI bypass list is not visible, while a separate GitHub connector token sees an empty bypass list. Five MST Google Drive folders display a single visible owner role each and no independent administrative attestation. These facts cannot be treated as proof of signer root, two-controller custody, floor or vendor rights.

Separate proposed role slots: `POLICY_CONTROLLER`, `SIGNER_ROOT_CUSTODIAN`, `REVOCATION_CONTROLLER`, `WITNESS_WRITER_A`, `WITNESS_WRITER_B`, `DRIVE_CHUNK_WRITER`, `READ_ONLY_VERIFIER`, `PULL_REQUEST_CI`. Every slot has `principal_binding=null`, `independent_identity_verified=false`. **25 separation constraints** prevent modeled policy/signer, signer/writer, writer A/writer B, revoker/custodian/writer, reader/publisher, PR token/privileged role overlaps. Pairwise distinct labels can be simulated but **cannot** prove distinct human or root control: additional independent remote owner evidence is required.

## 3. Real GitHub Actions and QA corrections

**Pre-report code/workflow HEAD:** `f74ea6f9a6e8b529b8d05c9932e0109ce53779c0`. [Foundation CI #42624084131](https://github.com/ngluonghoa/MST/actions/runs/42624084131) **SUCCESS 3/3**: Python 3.11 **1912/1912**, Python 3.12 **1912/1912**, engineering **63/63**, H2/H3 exact source boundary, lint and wheel PASS.

[Dedicated hosted role separation #42624083966](https://github.com/ngluonghoa/MST/actions/runs/42624083966) **SUCCESS**, output: `roles_proposed=8`, `roles_with_actual_principals=0`, `required_distinct_principal_pairs=25`, `role_owner_decisions_open=8`, `privileged_actions_blocked=9`, `independent_admin_custody_verified=false`, `external_monotonic_floor_verified=false`, `production_cache_read_authorized=false`, `production_cache_write_authorized=false`, `trading_authorized=false`. Temporary GitHub artifact [13677431970](https://github.com/ngluonghoa/MST/actions/runs/42624083966/artifacts/13677431970), 14-day retention, **NOT** owner trust root or monotonic floor. Other 6 workflows on the same code HEAD also successful.

**Transparent CI correction:** first code-HEAD Foundation run [#42623889452](https://github.com/ngluonghoa/MST/actions/runs/42623889452) failed exactly **one test on each Python version** because `test_missing_authority_field_is_not_false` expected `PermissionError`; the strict top-level schema correctly raised `ValueError: NONCANONICAL_ROLE_POLICY_FIELDS` before checking privilege flags. Corrected the *test expectation*, did NOT loosen authorization. Retest on `f74ea6f...` passed all 1912. Do not cite the failed interim run as a QA success.

**Final report-containing HEAD must be read back and CI validated separately** before calling the full checkpoint green.

## 4. No premature role grant — explicit signoff still OPEN

- R01: separate policy controller, full bypass/root/recovery graph.
- R02: root signer registry and independent revocation authority; key lifecycle and PR secret exclusion.
- R03: two actual separately authenticated witness writers with one-winner server CAS.
- R04: Drive writer and independent reader ACLs + physical immutable licensed chunk readback.
- R05: owner-approved exact witness ref/ruleset creation, effective protection and no unreviewed bypass.
- R06: owner decision on main review count 0, non-strict required checks and signature policy.
- R07: source vendor first-known/revision/correction/retention license, independent of infrastructure signer SHA.
- R08: protected monotonic floor + root/admin bypass adversarial rollback/revocation/recovery across accounts.

Selecting Option A does **not** give consent to create separate GitHub repository/ref, change `main` ruleset, enroll signing keys, share real Drive data/roles, add producer secrets, merge PR8 or authorize live trading. If only one human/root controls both domains or Option A cannot prove nonresettable floor under an admin attacker, **G01/G02 remain BLOCKED**. Do not silently substitute GitHub Actions cache or introduce Cloud KMS/Firestore.

**Project gates all OPEN:** [#16 G01–G08](https://github.com/ngluonghoa/MST/issues/16), [#15 witness](https://github.com/ngluonghoa/MST/issues/15), [#13 CAS](https://github.com/ngluonghoa/MST/issues/13), [#14 cross-service](https://github.com/ngluonghoa/MST/issues/14), [#10 actual Drive bytes](https://github.com/ngluonghoa/MST/issues/10), [#9 data rights](https://github.com/ngluonghoa/MST/issues/9), [#4 A02 module owner disposition](https://github.com/ngluonghoa/MST/issues/4), [#6 A03 ABI approval](https://github.com/ngluonghoa/MST/issues/6). Draft PR8 unmerged, `main` untouched, M5/M8 release/trading BLOCKED.

**Next safe work without new approval:** construct an exact **owner approval/change plan** for an isolated GitHub witness, including proposer/approver identities, ref/policy diffs, audit/recovery and default-branch review risk; compare against GitHub+Drive capability limits. Any real privilege changes must be explicitly approved before execution.
