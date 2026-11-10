# MST A03 — Independently inspectable supplier and owner proof acceptance (public NO-GO)

QA ID: MST-A03-SUPPLIER-OWNER-PROOF-ACCEPTANCE-20261110
Date: 2026-11-10 (Asia/Ho_Chi_Minh)
Status: DRAFT PR #8 / UNAPPROVED OWNER ACCEPTANCE CONTRACT. Exact-final-head CI **PENDING**.
Provenance: Swing Trading 1.8 pin cd90c1babae8912db31490ad614fc2ad2f868042;
MST protected main 4048f91beaaa3410116d97e35896c8b688384e19;
original source tree d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e.

## Why this is the next step after conditional Ed25519
Prior A03 signed fixture verification (35 tests / 31 cases, at HEAD c450453c) demonstrated
that correct signatures and matching digest chains DO NOT prove the issuer is SSI/DNSE/VCBS,
the historical source head is complete, the custodians are independently controlled, the
cross-run rollback floor cannot reset, or the source license allows physical Google Drive caching.
Three decisive unresolved examples: caller-selected key substitution; separately valid sibling
signatures without server CAS; older altered revision rehashed and re-signed by colluding claims.

This packet is a **requirements-only acceptance checklist** to make the *missing external evidence*
specific and reviewable, not a fake independent attestation or a new runtime validator.
It reuses existing M4 private owner proof requirements **E03, E08, E11, E12, E13, E14**,
without duplicating the 14 M4 evidence records, owner grants, or privileged evidence collection.
No raw signatures, fingerprints, provider IDs from personal accounts, owner identities, secrets,
access tokens, private evidence URLs or licensed data are stored in this public repository.

## Four still-unsigned A03 owner gates, 12 inspectable checks

| Unsigned gate | Existing M4 requirements | Minimum independent owner evidence |
| --- | --- | --- |
| A03-SOURCE-HEAD-CLOSURE-11 | E11, E14 | Provider-issued root enrollment, vendor canonical revision/tombstone head, sequence completeness, source-as-of and official VN session proof |
| A03-INDEPENDENT-CUSTODY-12 | E03, E14 | Separate actual signer/viewer roles and effective permissions; externally anchored key and revocation; independently obtained readbacks |
| A03-DURABLE-FLOOR-13 | E08, E13 | Durable nonresettable floor tested after process restart or restore; two independently credentialed writers competing on protected server ref, one CAS winner and independently witnessed loser |
| A03-LICENSED-REPLAY-14 | E11, E12 | Contractual feed/retention/replay/Drive use rights and approval; only afterward authorized Google Drive physical byte/readback/expiry testing |

The JSON contains three detailed acceptance checks per gate, 16 named negative
untrusted-claim scenarios, and all production, cache and trading permissions FALSE.
A caller can assert that every vendor, witness and owner condition is true:
the preflight **still returns NO-GO** because only independently controlled private
evidence and separate owner review could prove any of these claims.

## New additive-only assets on Draft PR8
- docs/MST_A03_SUPPLIER_OWNER_PROOF_PACKET_UNAPPROVED_20261110.json — public exact four-gate packet, zero proof received.
- scripts/m2_a03_supplier_owner_proof_packet.py — fail-closed strict public contract and adversarial self-claim classification; reads existing M4 requirement index but does not ingest real proof.
- tests/test_m2_a03_supplier_owner_proof_packet.py — 26 targeted negative and integrity methods, no market data.
- .github/workflows/m2-a03-supplier-owner-proof-intake.yml — read-only same-repo PR8 GitHub-hosted tests, before-run live original 63 V1 and 8 V2 byte-lock, 14-day public metadata-only evidence.
- docs/MST_A03_SUPPLIER_OWNER_PROOF_ACCEPTANCE_QA_20261110.md — durable QA/reviewer note.

This cannot authorize signed-source market signals, merge, production, trades, privileged
GitHub changes, a new third Cloud, Mac/MOCHI/local processing, private owner evidence
exposure, actual SSI/DNSE/VCBS calls or licensed market-cache writes.
G01–G08 and OA01–OA06 remain OPEN. A02 owner 0/63; A03 V2 ABI 0/8;
A03 choices 0/14. M3/M4/M5/M8 production and all trading NO-GO.

## Owner-only next actions — NOT performed
An authorized owner must first choose an approved controlled PRIVATE evidence-intake
channel and independent verifier roles under Option A, ensure issuer and legal rights
evidence can be inspected without public disclosure, and determine feasibility of
externally durable floor and real two-writer CAS. Existing E03/E08/E11/E12/E13/E14
are existing criteria, not proof of availability. After source/license/role proof,
a separate gated execution plan must be reviewed; no current approval.
