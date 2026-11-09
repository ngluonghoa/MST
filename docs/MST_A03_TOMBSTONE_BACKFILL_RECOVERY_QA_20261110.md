# MST A03 — Tombstone, Backfill & Fail-Closed Recovery (Cloud-Only Synthetic QA)

**QA ID:** MST-A03-TOMBSTONE-RECOVERY-001  
**Date:** 2026-11-10 (Asia/Ho_Chi_Minh)  
**Verdict:** **PASS** — real inherited V1 SQLite synthetic deletion/backfill + distinct first-known events + in-process fail-closed recovery rules. **NO-GO** — independently authenticated history, durable crash recovery, physical Google Drive market cache or production.

## 1. Context and immutable source boundary

The source-locked upstream `ngluonghoa/swing-trading-1-8@cd90c1babae8912db31490ad614fc2ad2f868042` and protected MST `main@4048f91beaaa3410116d97e35896c8b688384e19` share the same Git tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e` (216 entries, 208 blobs). All **63 inherited V1 Python source modules and 8 pre-existing V2 opt-in source modules remain unchanged**. Work is additive only on unmerged Draft [PR #8](https://github.com/ngluonghoa/MST/pull/8). GitHub + Google Drive Option A remains the sole permitted cloud platform; no Mac, MOCHI, local execution, external cloud service, live market feed, broker, market cache Drive writes, signer, witness ref/ruleset edit or production deployment.

Previous [full-policy manifest QA](https://github.com/ngluonghoa/MST/blob/mst/m2-a03-opt-in-v2-sidecar-20261109/docs/MST_A03_V2_FULL_POLICY_MANIFEST_CHAIN_QA_20261109.md) intentionally **rejected unversioned historical deletions**. This checkpoint introduces a *new synthetic-only* event protocol rather than weakening the previous manifest schema or changing original V1 source logic.

## 2. Additive source, test and CI changes

- `scripts/m2_a03_tombstone_backfill_recovery_lab.py`: typed `SyntheticRevisionEvent`, `SyntheticMaterializedFrame`, full local `verify_local_event_chain`, and `LocalCrashReviewJournal` **in-process only**. The new schema is `mst.a03.tombstone-backfill-recovery.synthetic.v1`.
- `tests/test_m2_a03_tombstone_backfill_recovery_lab.py`: **48 regression tests**, including source event chronology, strict revision-to-tombstone binding, missing event, policy/rights drift, duplicate/incorrect bar SHA, indicator invalidation, local recovery and quarantine.
- `.github/workflows/m2-a03-tombstone-backfill-recovery-lab.yml`: GitHub-hosted same-repository PR #8, `contents:read` only; executes inherited V1 fixtures on GitHub ephemeral SQLite, saves an unattested JSON review artifact with 14-day retention.
- This report, Drive QA, Handoff/Spec/Charter/Gap documentation. No inherited V1 or existing V2 Python file was edited.

The event model requires `action` = `TOMBSTONE` or `BACKFILL`, exact bar start, *first-known UTC* and SHA256 of the previously materialized content. BACKFILL additionally requires exact new payload SHA256 and revision ID. Event time must be later than the preceding snapshot's as-of; a BACKFILL must follow a recorded TOMBSTONE for the **same bar** and prior content digest, with a strictly later first-known time. It cannot rewrite a bar that never disappeared or alter unrelated bars under a deletion event.

Every versioned materialization binds the **complete legacy V1 rights/resolution/quality/adjustment/calendar/aggregation/indicator-parameter scope**, source identity, original V2 partition mapping and full current revision set. Separate digest of materialized bars and EMA20/ATR14 checkpoints must be consistent with actual inherited V1 SQLite and the independent Decimal oracle. Generation/parent SHA256, monotonic as-of, sorted closed bars, first-known timestamps and exact one-bar event transitions are checked. An unchanged WARM stage cannot change bars or indicators.

**Security boundary:** Synthetic event timestamps and SHA256 are caller-provided, **not** an authenticated licensed provider revision feed. The locally self-hashed chain is not an independent G01 signer, non-resettable G02 floor or genuine G03 two-auth CAS.

## 3. Real inherited V1 SQLite scenario

Actual inherited `SyntheticIncrementalStore.apply_fixture_window` is executed on a temporary SQLite file **on GitHub Actions**, not a mock database:

| Generation | Synthetic V1 transaction | Expected and observed |
| --- | --- | --- |
| G1 COLD @ minute 20 | Load 20 closed manufactured M5 bars | 20 materialized rows, original + independent EMA20/ATR14 references equal |
| G2 TOMBSTONE @ minute 30 | Mark a complete bounded source window and omit bar #11 | Exactly 1 bar removed, **8** affected checkpoint rows recomputed; event references prior bar content SHA |
| G3 BACKFILL @ minute 40 | Restore same bar start with new fabricated close, revision r2 and first-known = minute 40 | Exactly 1 bar inserted, **9** affected checkpoint rows recomputed; new SHA and revision linked to prior tombstone |
| G4 WARM @ minute 41 | Re-use unchanged materialization | 20 bars and indicator checkpoint digest unchanged |

The previous G1 view retains bar #11. G2 deletion cannot be claimed as known before minute 30. G3 restoration cannot be claimed as known before minute 40. This is a **local four-generation history of synthetic snapshots**; it does not authenticate external market corrections or prove general historical reconstruction from Google Drive.

## 4. Crash/recovery behavior — deliberately limited

The volatile `LocalCrashReviewJournal` distinguishes a committed local frame from an uncommitted prepared candidate:
- **Crash after SQLite changed, before local manifest commit:** the current SQLite materialization disagrees with the last committed local frame. A review-only recovery check raises `UNCOMMITTED_SQLITE_MATERIALIZATION_QUARANTINED`; it does **not** silently adopt, repair or publish the candidate.
- **Crash after preparing an unchanged WARM candidate, before SQLite changed:** the current materialization equals the last committed local frame. The uncommitted candidate can be discarded, and the last committed local head remains unchanged.
- `commit` checks current materialized data/indicator digests, full rights binding and complete parent chain against the pending candidate. A changed checkpoint fails verification. Only one pending candidate is accepted.

These are **in-process deterministic failure simulations**; no process kill/restart, GitHub remote CAS, separately authenticated writers, durable journal recovery, independent external receipt or actual Google Drive byte-level restore was demonstrated. Even a successful local recovery does **not** certify persistence after process loss or admin rollback.

## 5. Hosted QA evidence and transparent failed test fixtures

**Code-only HEAD after correcting isolated negative fixtures:** `9bb7697df2a14caa080f3275c75a3717615edd23`.

- [Tombstone + Backfill hosted audit #42669196251](https://github.com/ngluonghoa/MST/actions/runs/42669196251) **SUCCESS**; four-stage fixture, exactly 1 delete / 8 indicator checkpoints and 1 backfill / 9 checkpoints, dirty uncommitted SQLite quarantine and clean-prepared intent discarded. Review-only [artifact #13698455614](https://github.com/ngluonghoa/MST/actions/runs/42669196251/artifacts/13698455614), retention 14 days, not protected custody.
- [Foundation #42669196504](https://github.com/ngluonghoa/MST/actions/runs/42669196504) **SUCCESS 3/3**: Python 3.11 **2190/2190**, Python 3.12 **2190/2190**, engineering **63/63**, H2/H3 source-boundary, lint and wheel PASS.
- Source-locked upstream/main/candidate audit and 13 other read-only/synthetic workflows also succeeded: **16/16 workflows SUCCESS on the same code HEAD**.
- Earlier [Foundation #42668953060](https://github.com/ngluonghoa/MST/actions/runs/42668953060) failed **two test-fixture expectations**. One invalid time-rewind manifest was rejected earlier by the first-known/as-of guard; another missing-tombstone case was rejected earlier as an unversioned existing bar rewrite. The test fixtures alone were repaired to independently reach the intended specific guards. No source production behavior, V1 module or existing V2 guard was relaxed. Dedicated new workflow was already SUCCESS.
- **This report creates a new commit**; final report-containing HEAD workflows must be checked separately.

## 6. Required work before production or calling this 1:1

1. The local complete-scope deletion assertion is **not** an independently verified SSI/DNSE/VCBS deletion receipt. A source event needs licensed, authenticated event identity, vendor first-known semantics, retention and correction authorization (G04).
2. Recovery requires durable independently protected high-water and signer, actual physical Drive market bytes, verified Git ref admin/bypass controls, true distinct authenticated writers/server CAS and global revocation (G01–G07), not local SHA hashes or volatile memory.
3. Owner approval of A02's 63 source-module dispositions, A03 V2 strict ABI/data schema migration, and release gating G08 remains OPEN.
4. This evidence does not implement V2 Google Drive cache publishing, remote read barriers, durable recovery, production signals or trading; M5/M8 stay BLOCKED.

**Next safe engineering task:** model separately committed and reader-visible states in a *synthetic* Google Drive manifest protocol, test interleaved/crash checkpoints and stale-reader rejection, while waiting for owner-approved independent custody, service identities and licensed data rights. **Do not** call that model physical Google Drive CAS.
