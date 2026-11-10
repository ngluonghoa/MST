# MST A03 — PREPARED / COMMITTED / READER-VISIBLE Read-Barrier (Synthetic QA)

QA ID: MST-A03-READER-BARRIER-001
Date: 2026-11-10 (Asia/Ho_Chi_Minh)
Verdict: PASS for opt-in synthetic protocol only; PRODUCTION NO-GO.
Work surface: existing open DRAFT PR #8 (https://github.com/ngluonghoa/MST/pull/8), never merged.

## 1. Immutable scope, source lock and predecessor

- Upstream Swing pinned at cd90c1babae8912db31490ad614fc2ad2f868042; protected MST main pinned at 4048f91beaaa3410116d97e35896c8b688384e19, identical original source tree d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e.
- No source modification to 63 original V1 Python modules, any existing 8 opt-in V2 modules, or original package metadata. This checkpoint adds only a script, test, GitHub Actions workflow and review report.
- User chose architecture Option A: GitHub + Google Drive ONLY. This checkpoint uses GitHub-hosted ephemeral execution and in-memory fake objects; NO Mac, MOCHI, local machine, third cloud, Google Drive market bytes, licensed SSI/DNSE/VCBS feed, signer/secret, protected ref/ruleset mutation, PR merge, release or trade.
- Predecessor: MST_A03_TOMBSTONE_BACKFILL_RECOVERY_QA_20261110.md proved a typed source event local chain over actual inherited V1 SQLite and independent Decimal EMA20/Wilder ATR14, while explicitly leaving remote recovery/custody unproven.

## 2. Additive implementation

- scripts/m2_a03_reader_visibility_barrier_lab.py (schema mst.a03.reader-visibility-barrier.synthetic.v1): separate PREPARED candidate, materialized object, COMMITTED review receipt and READER-VISIBLE marker.
- tests/test_m2_a03_reader_visibility_barrier_lab.py: 39 negative/positive regression tests using the four real original V1 SQLite synthetic stages.
- .github/workflows/m2-a03-reader-visibility-barrier-lab.yml: GitHub Actions same-repository PR #8 only; contents:read, Python 3.12, standalone 39 tests, four-state inherited V1 fixture replay, an explicitly untrusted JSON review artifact retained 14 days. No application privileges.
- Review-only separate publication phases are modeled, not a real Google Drive transaction, not an independently authenticated signer or non-resettable external high-water witness.

## 3. Admission invariants actually exercised

Reader requires all of: an observed visible marker, entire G1..Gn frame chain, matching COMMITTED receipt per generation, exact manifest/payload SHA256 binding, right source/policy scope, pinned local genesis, exact last committed marker and continuity of the reader's in-process session floor. An explicit required generation also blocks treating an older visible head as a newly published generation.

Adversarial tests deny: PREPARED-only data, object materialized but not committed, COMMITTED without VISIBLE, visible pointer ahead of complete receipts or payloads, missing/corrupt receipts, forged pointer SHA, rights-scope substitution, wrong genesis or parent, skipped generation, altered lineage, duplicate prepare, commit without object, visibility without commit or readback, stale observed snapshots below the session floor and invalid required generation.

Crash interleavings:
1. After PREPARE and synthetic materialization, before COMMIT: simulated in-process crash discards volatile intent. Any leftover object is NOT reader-visible. Review-only re-prepare is possible; NO automatic publication.
2. After COMMIT, before visibility: crash marks an unresolved committed-but-invisible state, denies later automatic publication/prepare, leaves old visible head. Recovery requires separate owner-controlled protocol NOT implemented.
3. After successfully becoming visible: simulation of crash does not regress current in-memory visibility. This does NOT prove cross-run durability, external monotonicity or actual two-service read consistency.

Original V1 real temporary SQLite is exercised with 20 closed manufactured M5 bars: COLD@20 -> TOMBSTONE@30 deletes bar #11 and recomputes 8 indicator checkpoints -> BACKFILL@40 restores new synthetic r2 close and recomputes 9 rows -> WARM@41 preserves materialization. Each frame is validated against inherited V1 and independent Decimal EMA20/ATR14 from the prior A03 modules. No real provider event timestamps are authenticated.

## 4. Hosted GitHub CI proof (code HEAD)

Code + workflow HEAD: 5b442a476891b18d01731026b964bdd7af9329db

- Dedicated A03 reader barrier workflow https://github.com/ngluonghoa/MST/actions/runs/42753026161 SUCCESS, 39/39 unittest on GitHub Actions plus deterministic four-stage fixture and review-only artifact.
- Foundation CI https://github.com/ngluonghoa/MST/actions/runs/42753025544 SUCCESS 3/3 jobs: Python 3.11 2229/2229, Python 3.12 2229/2229, original engineering 63/63, source boundary / H2-H3 / lint / package-wheel gates PASS.
- All 17/17 exact code-HEAD workflows SUCCESS. Synthetic review/protection checks, not production acceptance.
- This report is a subsequent documentation commit. New report-containing HEAD needs independent CI recheck; never cite the code-only HEAD as the final documentation-HEAD check.

## 5. Honest trust/correctness boundaries

SyntheticReader.floor_generation is in process and caller-resettable. The negative suite deliberately demonstrates that constructing a fresh reader can accept an older snapshot. In-memory Committed and Visible hashes are self-asserted and derive no independent authenticity. An all-powerful caller can rewrite/fabricate the entire chain, and an untrusted data plane can replay a consistent snapshot to a fresh reader. A passing test DOES NOT solve G01 independent signer, G02 independently durable non-resettable namespace floor or G03 real distinct-writer server-side CAS.

No actual Google Drive physical objects, ETag/version preconditions, atomic cross-system snapshot, Drive ACL propagation, GitHub administrator bypass protections, network partitions, durable crash/restart, separate principals, provider licensed data or production permission have been tested. No broker orders, positions or generated trade signals.

A02: 63/63 module initial coverage, 0/63 formal owner dispositions signed. A03: full versioned ABI and production Drive/cache compatibility not accepted. G01..G08 remain OPEN. M3/M4/M5/M8 production gates remain BLOCKED.

## 6. Next safe step

Conduct synthetic two-reader/two-writer interleaving and reset-falsification review that explicitly classifies: (a) locally fenced stale reads, (b) external evidence gaps not solvable by in-memory hashes, and (c) owner decisions/privileged GitHub + Drive ACL work needed under Option A. Keep PR #8 DRAFT, preserve main, and require owner review before any actual Drive market cache I/O or witness/ref/ruleset changes.
