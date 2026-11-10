# MST A03 — Actual consumer divergence, source-cache guards and synthetic N/N−1 rollback

QA ID: MST-A03-DYNAMIC-CONSUMER-NMINUS1-20261110  
Date: 2026-11-10 Asia/Ho_Chi_Minh  
Status: **PENDING exact-head GitHub Actions** until readback verifies all runs. This is a targeted differential/falsification packet, not broad ABI parity certification.

## Baseline and scope

Original Swing Trading 1.8 commit: `cd90c1babae8912db31490ad614fc2ad2f868042`. MST protected `main` pin: `4048f91beaaa3410116d97e35896c8b688384e19` and original tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`. Preserve all 63 original V1 files and eight existing opt-in V2 sidecar Python files byte-for-byte. Work only on [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8), never merge without independent owner acceptance.

Earlier MST A03 §78/Handoff / §79 Spec checkpoint: 25 tests, 26 consumer cases and previous 128 UNVERIFIED synthetic replay decisions; only exact UNVERIFIED-empty-evidence upgrade/downgrade is permitted. Current packet adds **37 unittest methods** and **42 actual-original/V2 fixture cases** exercising two newly observed runtime differences, rule callback side effects, in-memory port/source semver rollback, and V2 cache-source observation policy.

## Two runtime differences requiring independent owner review

| New observation | Untouched V1 behavior | Existing opt-in V2 behavior | Consequence |
|---|---|---|---|
| One-pass generator returned by a causal market adapter | `BacktestHarness.visible_events` runs `any(... for e in events)` on the generator first, exhausting it; later visibility pass yields no events | `StrictReplayHarnessV2.visible_events` materializes a tuple first, then validates/filters; eligible event remains visible | **Not substitutable for iterator-returning ports.** Could affect replay evidence and historical as-of semantics. Must review upstream caller contract, cardinality and migration strategy; no V1 silent patch |
| Typed `CausalMarketEvent` subclass from adapter | `isinstance(event,CausalMarketEvent)` accepts subclasses | `type(event) is CausalMarketEvent` rejects subclasses | **Not substitutable for subclass-returning adapters.** Requires explicit versioned adapter/consumer acceptance, not an automatic source rewrite |

These are **additional observed compatibility differences**, not automatic owner-authorized fixes or evidence that V1 has ever produced trading outcomes in production. Earlier known intentional breaks remain: direct public clock rewind and truthy integer `Evidence.verified`.

## Actual consumer and rollback scenario coverage

- Replay: list inputs preserve four-time-scope source-locked causal evidence selection on a deterministic fixture; future-first-known events are hidden; source called once. Explicit one-pass generator and subclass negative differentials, untyped events rejected.
- Rule evaluation: only typed identity-matched `StrictSignalDecisionV2(status=UNVERIFIED,evidence=())` can pass; self-attested `DETECTED` and `NOT_DETECTED`, wrong zone/strategy, V1 result type and untyped caller inputs are denied; invalid inputs do not invoke the rule callback.
- Engineering `PortDescriptor` consumer pins: tested fake in-memory 2.0→2.1 replacement with old 2.0 consumer, downgrade 2.1→2.0 successful when no 2.1 consumer attached; downgrade rejected atomically while a 2.1 consumer is pinned; explicit unpin enables rollback; removal while consumer attached denied.
- Fixture source registry: SSI 2.0→2.1→2.0 path with identical endpoint, pin-aware rollback denial, cross-provider replacement denial, no impact to DNSE or VCBS fixtures, no vendor entitlement from a source adapter object.
- Fixture cache: RAW vs ADJUSTED and source revision namespace produce different partition identities; future untrusted head rejected; recent metadata never means trusted source freshness; stale metadata demands revalidation; `can_write_drive`, `can_fetch_market_data`, licensed cache read and `permission_to_trade` remain false.
- Prior 128 decisions over 16 B/S zones, two strategies and four as-of snapshots remain **UNVERIFIED** and nonactionable.

## Additive-only GitHub artifacts

- `scripts/m2_a03_dynamic_consumer_rollback_lab.py`: 42 named synthetic fixture checks, exact case SHA256, two unapproved runtime findings, no production permissions.
- `tests/test_m2_a03_dynamic_consumer_rollback_lab.py`: 37 unittest methods, including independently reproduced generator divergence, rule denial, atomic downgrade guard and cache freshness check.
- `.github/workflows/m2-a03-dynamic-consumer-rollback.yml`: GitHub-hosted Python3.12, PR #8 same-repo read-only token, independent LIVE upstream/main/PR source byte-tree proof before tests, 14-day nonauthorizing JSON artifact.
- `docs/MST_A03_DYNAMIC_CONSUMER_ROLLBACK_QA_20261110.md`: this review and evidence receipt.

Workflow: https://github.com/ngluonghoa/MST/actions/workflows/m2-a03-dynamic-consumer-rollback.yml

## What must not be claimed

This **does not** implement real N/N−1 signed release rollback, a durable switch, an approved legacy adapter, a fix in the original source, a calibrated detector, verified `DETECTED/NOT_DETECTED` trading decisions, authenticated SSI/DNSE/VCBS market source, licensed physical Drive cache, independent signer/witness floor, multi-principal server CAS, revocation or owner-signed production authority.

Human A02 full module approvals **0/63**, A03 V2 full owner approvals **0/8**. `G01–G08` and `OA01–OA06` stay OPEN, M3/M4/M5/M8 production and trading remain BLOCKED. GitHub+Google Drive **only**; no Mac/MOCHI/local/third Cloud, real market data, secrets, broker, privileged GitHub settings, merge or release.

## Evidence checklist (must be updated after exact-head CI readback)

- Dedicated dynamic-consumer workflow: PENDING as written.
- Foundation Python 3.11 and Python 3.12, engineering source/wheel: PENDING as written.
- Independent live upstream/main/PR source-lock: PENDING as written.
- All exact-current-head PR workflow runs: PENDING as written.
- Four MST canonical Docs updated only after QA is green; owner and production NO-GO must stay explicit.
