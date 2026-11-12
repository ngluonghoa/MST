# MST A03 — Dual Reader / Dual Writer Interleavings, Forks and Reset Falsification

**Evidence:** MST-A03-DUAL-READER-WRITER-001  
**Date:** 2026-11-10 (Asia/Ho_Chi_Minh)  
**Verdict:** **PASS — deterministic synthetic negative controls. PRODUCTION NO-GO.**  
**Work surface:** [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8), opt-in additive-only, unmerged.

## 1. Immutable parity and architecture boundaries

- Pinned Swing source: cd90c1babae8912db31490ad614fc2ad2f868042. Protected MST main: 4048f91beaaa3410116d97e35896c8b688384e19. Original Git tree d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e is identical. All 63 original V1 modules and 8 previous opt-in V2 source modules remain unchanged.
- Only Option A is authorized: GitHub + Google Drive. This experiment executes on GitHub Actions ephemeral runners using real inherited V1 temporary SQLite and independent Decimal EMA20/Wilder ATR14 over manufactured M5 candles. It never reads/writes actual Google Drive market cache or extra cloud services, never uses Mac/MOCHI/local, licensed SSI/DNSE/VCBS credentials/data, production secrets, signer, witness ref/ruleset edits, releases or trades.
- Previous A03 reader-barrier evidence introduced PREPARED / COMMITTED / READER-VISIBLE with 39 tests and no external trust. This task extends it as a separate additive research layer; no existing guards are weakened.

## 2. New implemented source/test/CI

- scripts/m2_a03_dual_reader_writer_interleaving_lab.py: synthetic in-process SingleMemorySequencer and typed WriterClaim, fake actor labels, observed-head generation and SHA, exact candidate SHA; original tombstone/backfill full-scope chain retained. It exercises ordered schedules (not actual parallel distributed transactions) with two independently created readers and two writer candidates. Schema mst.a03.dual-reader-writer-race.synthetic.v1.
- tests/test_m2_a03_dual_reader_writer_interleaving_lab.py: 48 targeted regression tests, including invalid typed claims, stale observed head, competing pending write, owner-label mismatch, unmaterialized/tampered payload, precommit and committed-invisible reads, rights drift, forged visible observations, local reader floor and explicit-generation checks, split-brain replicas, caller-resettable floor, fork detection and crash interleavings.
- .github/workflows/m2-a03-dual-reader-writer-race-lab.yml: same-repository PR #8, GitHub-hosted Python 3.12, contents:read only, 48 tests + deterministic executable negative-replay JSON artifact retained temporarily for 14 days. It does not provide independent custody.

## 3. Positive invariants that were *actually* observed

Two contenders inspect the same G1 source head and propose different valid G2 manifests: identical parent and exact full rights/source scope, different self-hashed as-of timestamps (G2 @minute30 vs @minute31). In ONE shared Python memory image, writer A claims the generation and B is denied while A is active. PREPARED, materialized, and COMMITTED-but-not-visible states cannot be read as G2. After explicit reader visibility, writer B's stale head observation is denied. Writer ownership enforcement is merely equality of caller-provided string labels; it is NOT authentication.

Reader A advances to G2 and thereafter rejects an older G1 snapshot, and rejects a same-generation conflicting G2 frame due to its own frame-SHA session anchor. Reader B can still consume G1 if it has not learned that G2 exists, unless the caller supplies a required generation of G2. After B learns G2, its own in-memory floor rejects the old snapshot. Thus read barriers work for those local preconditions only.

The source history cannot silently attach the original G3 BACKFILL (which references the canonical G2 SHA) under the rival G2; parent mismatch fails closed. The inherited V1 SQLite/oracle COLD20 → TOMBSTONE19 → BACKFILL20 → WARM20 chain is exercised, not mocked.

## 4. Crucial falsifications / independently insufficient controls

**Separate-process split brain:** Two entirely separate in-memory sequencer instances, each with the same pinned genesis, each accept a different local G2 as their only writer. Both locally valid hashes and receipts coexist and there is no remotely shared compare-and-swap authority to choose which is canonical. This is a synthetic counterexample to treating local writer exclusivity as G03 remote CAS.

**Reader restart/rollback:** A fresh reader reusing the pinned genesis but carrying no externally protected floor will accept a formerly valid G1 even after another session observed G2. A newly created reader also accepts a different, self-attested G2 fork. Older readers with a locally remembered SHA detect the fork, but a reset discards that protection. This is a synthetic counterexample to treating in-memory reader floors as an independent G02 durable monotonic floor.

**Self-attestation:** Hash consistency by itself never authenticates an independently authorized origin, vendor timestamps or a GitHub/Drive reader's custody. Actor labels are strings and do not establish two authenticated principals; in-memory serialization is not a server-enforced CAS, and multiple published candidates cannot be disambiguated with only caller-supplied receipts. G01 signer, G02 floor and G03 real server CAS remain OPEN.

**Crash boundaries:** In-process crash after prepared payload but before commit discards intent and does not publish; after commit but before visibility the model quarantines and does not auto-promote. Not a process-kill/restart, durable journal, actual GitHub/Drive snapshot, corruption recovery or true distributed network schedule.

## 5. GitHub hosted proof — actual code HEAD

**Code/workflow HEAD:** 6e04a2be1ac8a9c3c1928492e20df1b4ce3b9eee

- [Dedicated A03 dual-reader-writer workflow #42754258125](https://github.com/ngluonghoa/MST/actions/runs/42754258125): **SUCCESS**, **48/48 tests PASS** plus deterministic real-V1-fixture synthetic model.
- [Foundation CI #42754258069](https://github.com/ngluonghoa/MST/actions/runs/42754258069): **SUCCESS 3/3 jobs**, Python **3.11 2277/2277**, Python **3.12 2277/2277**, engineering 63/63 with source H2/H3 boundaries, lint and wheel checks. No original code edits.
- **18/18 workflow runs for this exact code HEAD completed SUCCESS.** These are review-only and synthetic checks, not independent security attestations.
- This file is written in a subsequent documentation commit; the *report-containing head* must be independently rechecked before claiming same-head evidence.

## 6. Open blockers and next safe work

A02: 63/63 preliminary source coverage, 0/63 signed owner module dispositions. A03: full V2 ABI/replay/real Drive migration semantics unsigned. G01 external independent signer, G02 nonresettable per-namespace floor, G03 authenticated server-side multi-writer CAS, G04 licensed source rights/first-known, G05 real Drive physical bytes and custody, G06 revocation, G07 independent evidence, G08 owner release remain OPEN. M3/M4/M5/M8 release/trading BLOCKED.

Next safe checkpoint is an owner-facing **Option A security/custody decision packet** that separates tested in-process behavior from requirements impossible to establish without different trust principals or independently controlled permissions. Evidence must be read-only and explicitly fail-closed; do not provision external secrets, protected refs, user permissions, real market cache or deploy. Keep PR #8 Draft and main source locked.
