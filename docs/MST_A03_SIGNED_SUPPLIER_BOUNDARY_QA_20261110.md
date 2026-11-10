# MST A03 — Conditional Ed25519 signature vs source closure and legal authority

QA ID: MST-A03-SIGNED-SUPPLIER-CROSS-BOUNDARY-20261110
Date: 2026-11-10 Asia/Ho_Chi_Minh
Status: PENDING exact GitHub final HEAD CI. All owner approvals and production/trading explicitly NO-GO.

## Existing source-lock and why this packet is nonredundant

Swing Trading 1.8 is pinned upstream commit cd90c1babae8912db31490ad614fc2ad2f868042; protected MST main is 4048f91beaaa3410116d97e35896c8b688384e19; inherited Git tree d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e. All 63 existing V1 source modules and eight opt-in V2 sidecars remain byte-identical on Draft PR #8.

Existing V1 source already includes verifier-only provider_signed_event_chain, reference_checkpoint_signature, provider_head_custody; existing M4 script m4_signed_floor_fixture.py conditionally verifies Ed25519 under a CALLER-PINNED TEST public key, with a CALLER-LOCAL fake floor. It explicitly does NOT trust vendor authority, rights, cross-run monotonicity or globally shared CAS. A03 previously added an untrusted source/viewer ledger closure hypothesis with 44 tests/44 cases, which demonstrated that self-reported two-party IDs and content digests are not independent custody.

This packet **reuses** the existing M4 signature fixture, not a second production cryptography implementation. A03 now binds a signed receipt's provider, partition digest, ledger digest and source first-known as-of timestamp to an exact A03 untrusted revision closure. It proves only structural and conditional Ed25519 integrity for GitHub-hosted ephemeral test keys. It DOES NOT authenticate SSI/DNSE/VCBS, vendor-signed history, licensed market-data entitlement, independent root, durable floor, CAS, Google Drive cache or trading.

## Negative controls and signed counterexamples

- Positive fixture: fresh in-run Ed25519 key (memory only, private key never printed/persisted), a fixture source/viewer closure over r1→r2, source/price-basis/partition/as-of-bound receipt, the existing M4 conditional verifier and local generation-one floor. The result explicitly reads CONDITIONAL_FIXTURE_ED25519_AND_SELF_CLAIMS_ONLY_NO_GO.
- Signed wrong ledger digest, source, price-basis partition or as-of time is rejected before promoting anything. Tampered envelope after signing, invalid signature, wrong public key, wrong epoch, unreviewed approval field, wrong parent or generation jump are rejected. The fake signature verifies only bytes under the caller-selected key.
- **Counterexample A — caller-controlled signer replacement**: a freshly generated second test key signs the same receipt with its own caller-replaced anchor and local floor. The cryptography passes, demonstrating that key substitution plus self-claim does not prove actual vendor-issued identity.
- **Counterexample B — valid signature forks / floor reset**: two different test receipts at generation one each verify independently against the same unshared in-memory floor. Old signed receipt re-verifies after caller resets that floor. A signature is not a distributed two-writer CAS, witness, or nonresettable cross-run rollback barrier.
- **Counterexample C — fully resigned tamper**: modify an older synthetic r1 payload digest, regenerate both untrusted SOURCE and VIEWER closure claims, sign the new closure with the valid fixture key and reset the local floor. Cryptographic integrity **passes** while historic source truth remains unproven. Signed consistency is not independent provider completeness or licensed market data.

This packet does not automatically convert any of these observed attack paths into authorized repairs. No V1 or V2 original or pre-existing modules changed. No private key material leaves GitHub's ephemeral runner, no real signer/credentials are provisioned, no vendor API called.

## Existing owner-proof crosswalk (do not create duplicate approvals)

| A03 unsigned owner gate | Related preexisting M4 private evidence requirements | Required independent proof |
|---|---|---|
| A03-OWNER-SOURCE-HEAD-CLOSURE-11 | E11, E14 | Vendor-authenticated revision head, canonical correction/tombstone semantics, source-as-of closure and independent readback |
| A03-OWNER-INDEPENDENT-CUSTODY-12 | E03, E14 | Actual signer/viewer enrollment, independent controllers/ACL, public-key ownership and revocation issuer |
| A03-OWNER-DURABLE-FLOOR-13 | E08, E13 | Real cross-run monotonic external floor and independent two-writer CAS/witness consistency |
| A03-OWNER-LICENSED-REPLAY-14 | E11, E12 | Contractual SSI/DNSE/VCBS licensing, retention, historical replay, legal cache on Drive and explicit owner authorization |

The public GitHub repository contains only requirement IDs E03/E08/E11/E12/E13/E14 and NO private evidence, signer fingerprints, license grants, access tokens or personal identities. Existing M4 owner-private evidence intake plan is explicitly NOT_RECEIVED. These six IDs are a crosswalk, NOT an owner attestation. A03 choices 01–14 still all UNSIGNED. A02 original modules owner signoff 0/63; A03 full V2 ABI/behavior owner signoff 0/8.

## New Draft PR #8 additive files

- scripts/m2_a03_signed_supplier_boundary_lab.py: invokes existing M4 verifier; ephemeral in-memory test keys; 31 named fixture cases, original A03 conditional closure metadata, SHA256 of case names/status only; no external payload or credentials.
- tests/test_m2_a03_signed_supplier_boundary_lab.py: 35 independent unittest methods, including standalone signature mismatch, resigned historical tampering and floor reset checks.
- .github/workflows/m2-a03-signed-supplier-boundary.yml: same-repository PR #8 GitHub-hosted Python 3.12 with optional existing custody cryptography dependency; live Swing/main/PR 63 V1+eight existing V2 Git byte-lock before tests; 14-day nonauthorizing JSON artifact, contents:read only.
- docs/MST_A03_SIGNED_SUPPLIER_BOUNDARY_QA_20261110.md: this QA/owner review, mirrored to Google Drive MST 02_QA_RELEASE_EVIDENCE.

Workflow https://github.com/ngluonghoa/MST/actions/workflows/m2-a03-signed-supplier-boundary.yml

## Hard gates, source rights and release denial

The conditional fixture verifier must NOT be represented as a real vendor source qualification. No authenticated vendor root/ledger closure, no independent key custody/revocation, no durable nonresettable cross-run floor, no authenticated two-writer CAS, no legitimate SSI/DNSE/VCBS market data licence, no physical licensed Google Drive market cache and no official VN exchange correction/calendar proof are demonstrated. All engineering decisions remain source-unverified, never DETECTED or NOT_DETECTED qualified. M3/M4/M5/M8 production and trading NO-GO; G01–G08 and OA01–OA06 remain OPEN. PR8 remains Draft/unmerged, protected main not modified. Option A GitHub + Google Drive only, no Mac/MOCHI/local/third Cloud, privileged GitHub settings or broker operations.

Do not claim exact-current-head PASS until independent GitHub Actions 35 tests/31 cases, Foundation Python3.11+3.12/source/H2/H3/lint/wheel, original-tree source byte-lock, and ALL workflows at final report-containing commit have completed SUCCESS.
