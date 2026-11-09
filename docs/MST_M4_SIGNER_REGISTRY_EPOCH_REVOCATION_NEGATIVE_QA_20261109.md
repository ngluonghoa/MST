# MST M4 — Signer registry epoch, revocation and stale-runner falsification (synthetic only)

**QA ID:** MST-M4-SIGNER-REGISTRY-NEG-001  
**Date:** 2026-11-09 (Asia/Ho_Chi_Minh)  
**Scope:** GitHub-hosted Cloud-only fixture/negative contracts on Draft PR #8, without production permissions.  
**Verdict:** LOCAL STRUCTURE AND SIGNATURE NEGATIVE TESTS PASS. GLOBAL SIGNER AUTHORITY, REVOCATION, DURABLE FLOOR, SERVER CAS, LICENSED DATA AND REAL DRIVE CACHE REMAIN OPEN.

## 1. Source and scope invariants

- Original Swing Trading 1.8 pinned source `cd90c1babae8912db31490ad614fc2ad2f868042`; MST protected main `4048f91beaaa3410116d97e35896c8b688384e19`, tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`.
- Existing 63 inherited `src/swing_trading/*.py` modules, all existing V2 modules, `pyproject.toml`, main ruleset and GitHub witness refs are UNCHANGED by this step. Draft PR #8 stays OPEN/DRAFT/UNMERGED.
- Created only `scripts/m4_signer_registry_fixture.py` (Git blob `654843e9b0cbe8500620cdb4d266b2de2d447895`) and `tests/test_m4_signer_registry_fixture.py` (Git blob `27a7311a60c228585fe16eae2fe8c83bba4f1fff`).
- Test-only Ed25519 private keys are generated in memory by unittest. No real owner/custody signer, GitHub privileged write, external network, vendor OHLCV, Google Drive market-cache files, Mac, MOCHI, personal workstation or real trading is used.

## 2. Fixture registry contract — what is actually tested

`FixtureSignerRegistry` is a frozen typed record for a *caller-supplied* provider (SSI/DNSE/VCBS), partition SHA, rights-policy SHA, revision, prior registry digest, signer ID, key epoch, Ed25519 public key, revoked flag and strict UTC observation. Its canonical SHA256 digest is SELF-COMPUTED; it proves neither owner endorsement nor durable/public ledger custody. A caller can replace the record and recompute its matching claimed pin.

`local_registry_transition(previous, proposed)` checks same provider/partition/rights/signer, strictly consecutive registry revision, exact previous digest, clock order and epoch/key consistency. For safety, local revoked signers cannot be re-enabled or rotated, and same-step revoke+rotate is blocked pending owner decision. This rule is a lab guard, not a substitute for governed key-recovery policy.

`verify_with_caller_registry(receipt, signature, registry, floor, caller_pinned_registry_digest)` rejects mismatched claimed pins and revoked local signer snapshots, then delegates to actual Ed25519 validation against the *same caller's* key and ephemeral `FixtureFloor` from the previous signed-receipt lab. Successful result is `FIXTURE_CALLER_REGISTRY_AND_SIGNATURE_CONSISTENT_UNATTESTED`; no new privileges are granted.

## 3. New 26 test cases

Tests cover local signature consistency and all-false authority flags; wrong/malformed/missing registry SHA pin; local revoked-key denial; sequential registry revision; skipped/replayed/boolean registry revision; wrong parent digest; observation-clock regression; wrong source/partition/rights namespace; unauthorized signer substitution; replacement key without epoch increment; epoch increment without a different key; skipped/regressed/untyped epoch; disallowed simultaneous rotation and revocation; revoked signer re-enrollment; mutation of revoked signer key; two distinct signed-key registry siblings from the SAME prior head; runner with old active registry accepting a receipt after another runner locally marks it revoked; resetting registry and floor accepting an older signed generation after G2; old-epoch rejection under a newly pinned local registry; new-epoch bootstrap at G1 **without evidence of historical continuity**; attacker selecting a different registry/public key, recomputing the pin and self-signing a valid but unauthenticated receipt; signed receipt mutation rejection; untyped object rejection; malformed registry constructors; direct explicit null pin rejection.

Crucial production-blocking counterexamples:

1. **Registry fork:** Two different new public keys at `key_epoch=2` can each form locally valid revision-2 children from the same revision-1 registry. Without an independently protected, server-arbitrated registry root, both verifiers can accept distinct successor heads. A canonical SHA alone is not global single-winner CAS.
2. **Revocation propagation failure:** Runner A's old active snapshot continues accepting a valid G1 signature while runner B's successor snapshot locally rejects the same signer. This is NOT global revocation or credential kill-switch.
3. **Registry+floor rollback:** Replacing the active registry with its earlier snapshot and recreating the ephemeral floor accepts signed G1 even after G2 was seen in a different local history; no protected monotonic store exists.
4. **Key rotation continuity gap:** New key+epoch bootstrap can validate a signed G1 using a new, locally seeded floor, but cannot attest continuity to the old key epoch's source revisions and accepted generation. Explicit external authenticated migration is required.
5. **Attacker-selected trust root:** A forged public-key registry and caller-supplied matching pin accept an attacker-signed fixture cryptographically. A self-hash cannot establish independent authorized signer enrollment.

## 4. Exact GitHub CI proof

**Code-and-tests HEAD:** `363b86583596497d81fbf0973484d16425b31e37`.

- [Foundation CI #42600849045](https://github.com/ngluonghoa/MST/actions/runs/42600849045): **SUCCESS 3/3**, Python 3.11 **1701/1701 PASS**, Python 3.12 **1701/1701 PASS**, engineering contracts **63/63 PASS**, H2 full source boundary/H3 generated matrix/lint/package wheel and isolated installation PASS.
- [M4 GitHub real-ref readback #42600849064](https://github.com/ngluonghoa/MST/actions/runs/42600849064): **SUCCESS**, read-only TEST-ONLY proof; NOT independent authenticated cache writer or protected witness.
- [M4 synthetic cross-run cache proof #42600849112](https://github.com/ngluonghoa/MST/actions/runs/42600849112): **SUCCESS**, UNTRUSTED fixture transfer; NOT authenticated Drive retention, source rights or protected monotonic floor.
- Earlier initial CI #42600727533 was RED only because a unit-test convenience helper treated `pin=None` as "default valid pin" rather than forwarding explicit null; the production-facing lab verifier was already strict. A follow-up dedicated direct-null test plus corrected helper negative inputs resolved that test defect. Exact later code HEAD above is green. No baseline/V2 source fix was required.
- This report is a separate documentation-only commit after the verified code/test HEAD and must be checked against its OWN final exact HEAD CI before being called the latest green snapshot.

## 5. External authority gates — all OPEN

| Owner gate | Current tested evidence | Production disposition |
| --- | --- | --- |
| SIGNED-G01: independently governed root/key enrollment | Caller-supplied key/pin can be swapped | OPEN |
| SIGNED-G02: protected external monotonic registry AND receipt floor | Snapshot and floor reset can replay G1 | OPEN |
| SIGNED-G03: two authenticated writers/server CAS single-winner | Both locally valid registry siblings accepted | OPEN |
| SIGNED-G04: vendor source license/first-known/corrections/retention | No vendor connection/bytes/rights | OPEN |
| SIGNED-G05: real GitHub ref+commit/tree AND physical Drive SHA/2-service crash saga | Synthetic fixtures only | OPEN |
| SIGNED-G06: rotation/revocation globally fenced across accounts/runners | Stale runner accepts after another revokes | OPEN |
| SIGNED-G07: machine-readable honest trust tiers | UNATTESTED/false flags only | OPEN |
| SIGNED-G08: A02/A03/M3/M4/M8 release/signoff | PR #8 Draft/unmerged, 63 original modules untouched | OPEN |

**Do not interpret green CI or valid fixture cryptography as an authorization to publish, persist or backtest real market data, or place orders.** The next independent Cloud-only phase must acquire explicit owner approval for signer custody and protected witness policy first, then prove external registry pin/floor and revocation across distinct authenticated principals with fault-injected readback; no production provisioning in this checkpoint.

**Tracking:** [Issue #16 signer authority](https://github.com/ngluonghoa/MST/issues/16), [#15 witness policy](https://github.com/ngluonghoa/MST/issues/15), [#13 multiwriter](https://github.com/ngluonghoa/MST/issues/13), [#14 cross-service floor](https://github.com/ngluonghoa/MST/issues/14), [#10 Drive cache](https://github.com/ngluonghoa/MST/issues/10), [#9 vendor rights](https://github.com/ngluonghoa/MST/issues/9), [#4 A02 owner 63-module signoff](https://github.com/ngluonghoa/MST/issues/4), [#6 A03 ABI acceptance](https://github.com/ngluonghoa/MST/issues/6).
