# MST M4 — Option A Private Owner Evidence Intake (Public Requirements Only)

QA ID: MST-M4-OWNER-PRIVATE-EVIDENCE-INTAKE-001
Date: 2026-11-10 (Asia/Ho_Chi_Minh)
Verdict: PASS for 47/47 fail-closed privacy/security unit checks and 21/21 code-HEAD GitHub workflows. All 14 independent owner evidence classes NOT RECEIVED. Production and trading NO-GO.
Work surface: https://github.com/ngluonghoa/MST/pull/8 (Draft, unmerged).

## 1. Scope and immutable original source

This is owner evidence intake PLANNING, not a new trust root or owner signoff. User selected Option A GitHub + Google Drive ONLY. Pinned upstream Swing cd90c1babae8912db31490ad614fc2ad2f868042; protected MST main@4048f91beaaa3410116d97e35896c8b688384e19, original Git tree d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e, all original 63 V1 + 8 previous opt-in V2 modules unchanged.

No Mac/MOCHI/local, third Cloud, licensed real vendor market data, broker, real physical Drive cache, signer key/token, owner identity binding, GitHub ruleset/ACL/witness ref changes, PR merge, production release or trading.

## 2. Current metadata / independent-root limitations

- Connected GitHub repository metadata returns admin permission for the authenticated user, and an explicit owner collaborator permission check returns admin. This is a viewer-scoped observation, NOT the effective graph of all root admin/bypass/recovery privileges and not two independently controlled principals.
- Live GitHub Actions read-only token can see active default-branch ruleset 26801439, three Foundation checks, zero required positive approving reviews; proposed protected refs/heads/mst/m4-witness/v1 is absent; bypass actor inventory not visible. Unknown never means empty or safe.
- Connected Google Drive metadata again showed the MST project root and QA folder each with one visible owner role, consistent with the earlier 5-folder snapshot. Drive owner metadata alone does not prove independent signer control, physical-byte retention or immutable custody. GitHub Actions is NOT reading live Google Drive ACL; its Drive snapshot is historical connector metadata.
- Existing 8 roles / 25 distinct-principal constraints have 0 authenticated real bindings, six OA01–OA06 owner choices OPEN, 12 T01–T12 root threats OPEN. A03 demonstrated synthetic reset-reader and isolated split-brain counterexamples to remote CAS and nonresettable floor.

## 3. Fourteen owner evidence classes (requirements, NOT proof)

| ID | Independently required owner evidence | Gates |
| --- | --- | --- |
| E01 | Effective GitHub admin, bypass and recovery actor graph from separate viewers | G01 |
| E02 | Owner-approved protected witness ref/ruleset effectiveness | G02 |
| E03 | Independent signer-root custody and unauthorized signer denial | G01 |
| E04 | Key epoch, revocation and admin restore antirollback | G02/G06 |
| E05 | Two separate nonadmin authenticated writer identities and independent verifier | G03 |
| E06 | PR CI isolation from signer, writer and vendor credentials | G01/G07 |
| E07 | Effective Drive owner ACL, rights, physical-byte retention and readback | G05 |
| E08 | Fresh reader highest independently accepted floor after restart | G02 |
| E09 | Real GitHub + Drive two-service read barrier and crash quarantine | G03/G05 |
| E10 | Owner-signed shared-root risk disposition under Option A | G01/G02/G08 |
| E11 | Licensed vendor first-known correction and retention rights | G04 |
| E12 | Formal A02 63 dispositions, A03 V2 ABI and release approvals | G08 |
| E13 | True two-authenticated-principal remote one-winner/loser CAS test | G03 |
| E14 | Cross-viewer evidence provenance and permission-scope reconciliation | G07 |

Public GitHub JSON records only requirements. Each proof state NOT_RECEIVED; private evidence URI, subject identity, signer fingerprint, attestation URI NULL; independently_verified and owner_reviewed FALSE. No private evidence store or independent root has been approved/provisioned simply by possessing the current Drive folder. Future real proof must use separately authorized private owner access controls and verifier trust; PR CI cannot approve it.

Mapping covers 14/14 categories, all eight G01–G08, six OA01–OA06, twelve T01–T12. Coverage is NOT receipt or acceptance.

## 4. Implemented additive changes

- docs/MST_M4_OPTION_A_PRIVATE_OWNER_EVIDENCE_INTAKE_20261110.json: requirement ledger, zero received, privacy NO-GO policy.
- scripts/m4_option_a_private_owner_evidence_intake_preflight.py: reuses canonical owner bridge, role matrix, threat register, historical Drive snapshot and actual GitHub token-limited custody/readiness readbacks. Refuses extra/public private owner identifiers, emails, private URLs or signer fingerprints, acceptance-text credential assignments, missing gates, forged self-approval, fake private store or any production authorization.
- tests/test_m4_option_a_private_owner_evidence_intake_preflight.py: 47 unit tests, including private URI/email/key injections, forged independent signer/custodian, wrong witness status, omitted requirements and Cloud/source drift. Mocked unit API-shaped receipts are NOT actual GitHub evidence; hosted workflow separately reads GitHub token-limited REST.
- .github/workflows/m4-option-a-private-owner-evidence-intake-readonly.yml: GitHub-hosted same-repository PR #8, contents:read only. Runs unit tests, separately refreshes actual GitHub custody/readiness, reconciles ledger and uploads 14-day nonauthoritative review artifact. No real Drive market bytes, owner identity or secret.

## 5. GitHub-hosted code/workflow proof

Exact code/workflow HEAD 3f01a5bfab3e95269eaa22b225213dbd7d8c9601.

- Dedicated owner evidence intake run https://github.com/ngluonghoa/MST/actions/runs/42758620799: SUCCESS, 47/47 tests, returns FOURTEEN_PRIVATE_OWNER_REQUIREMENTS_RECONCILED_ALL_UNRECEIVED_NO_GO. All production signer, floor, CAS, read/write and trading flags remain FALSE.
- Foundation https://github.com/ngluonghoa/MST/actions/runs/42758620896: SUCCESS, Python3.11 2401/2401 and Python3.12 2401/2401 tests, original source boundary 63/63, H2/H3/lint/wheel PASS.
- All 21/21 workflows SUCCESS on exact code/workflow HEAD. Subsequent QA-report-containing HEAD must be read back separately before claiming same-head success.

## 6. Owner and privacy guardrails

Production NO-GO remains: OA01–OA06 unsigned, A02 0/63 formal module owner dispositions, A03 full V2 ABI OPEN, G01–G08 and M3/M4/M5/M8 release/trading BLOCKED.

No passwords, provider tokens, actual owner identities, private evidence links, owner account screenshots or signing keys may be inserted into the public repository or nonauthoritative CI artifacts. Passing green means the public plan remains empty and no unauthorized permissions were inferred, not that evidence has arrived.

Next safe owner action: privately authorize the evidence intake custody and independently controlled viewer identities for E01/E03/E05/E07/E14; separately review actual admin/bypass, signer, Drive ACL and common platform root risk. No keys or private data in PR Actions. If Option A cannot satisfy approved trust model, retain NO-GO rather than weakening requirements.
