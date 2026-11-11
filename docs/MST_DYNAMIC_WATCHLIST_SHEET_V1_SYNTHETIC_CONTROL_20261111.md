# MST Dynamic Watchlist — Cloud Control Plane Contract, Synthetic QA

Date: 2026-11-11. Owner-approved design under canonical Master Handoff §§125/128. **No production use.**

## Why this is the next safe milestone

Watchlist is **not hard-coded in Python nor GitHub YAML**. Owner edits a private Google Drive-hosted **Google Sheet**; an authorized GitHub Actions collector would (later) read a consistent snapshot **once per run** and only update enabled symbols. The Sheet is not created/deployed by this PR. The initial real ticker list has NOT been provided and must not be inferred from past synthetic/provider QA symbols.

Market Scanner remains separate and **manual-only**. No Scanner candidate is automatically inserted into Watchlist, even if it scores highly. On-demand unknown symbols must use separate explicit requests, not sneak into a scheduled scope.

## Proposed owner-facing Sheet v1

| Symbol | Exchange | Enabled |
|---|---|---|
| FAKEA | HOSE | TRUE |
| FAKEB | HNX | FALSE |
| FAKEC | UPCOM | TRUE |

**These are invented sample symbols, not a configured market watchlist.** Exactly three fields, strict header Symbol, Exchange, Enabled. Enabled uses TRUE or FALSE, not a free-form interpretation. The validator trims/canonicalizes lower-case ticker/venue entries for ergonomics, rejects duplicates and cross-venue ambiguity, rejects wildcards and malformed symbols/exchanges, requires explicit enablement, and accepts empty watchlists as a deliberate *no-refresh* state. Config budget default 1,000 source rows, independently configurable downward.

A read-only connector shall obtain an authenticated Google revision token and a separate **trusted, monotonic generation attestation**. That generation MUST come from the Cloud signer/monotonic floor or equivalent independently authenticated publisher, not blindly from an owner-editable Sheet cell. This draft cannot provide authentication or rollback protection by itself. Google read adapter must protect against torn reads by fetching a consistent snapshot (e.g. compare strong revision before/after, with bounded retries), lock one revision for a run, validate it, and fail closed on torn/stale/unreadable/invalid input.

## Required future collector semantics

1. At authorized run start, read exactly one owner-private Sheet revision. Validate schema, symbol/venue and enabled flags, frozen manifest digest, and monotonic revision. **Do not query a wildcard stock universe** on any error. A current run never switches list mid-run.
2. Plan set difference between the previous valid frozen list and the current frozen list. Newly enabled → authorized initial incremental backfill when source rights permit; unchanged enabled → incremental refresh; paused/removed → **stop scheduled refresh and never silently delete existing Cache**.
3. Google Drive Cache V2.1 persists per-source+TF provenance, revision, PIT/first-known, issuer-native units and official closed-bar calendars, independent true CAS/highwater signer, immutable chunks and causal DAG. Watchlist membership may change without replaying unaffected symbol data or changing previously valid cache ABI.
4. VN-Index index context is separately identified and is not a permission to crawl all its component stocks. No assumed automatic full HOSE/HNX/UPCoM scan: only Market Scanner manual user-initiated workflow has a separately authorized eligible-market universe.
5. User-approved Scanner candidate promotion must use an audited Watchlist revision operation. Private Sheet ACLs and exact writer permissions are owner-controlled: Scanner never writes the Watchlist directly.
6. No real API calls, GitHub schedule, Google Cloud identity, private Drive writes or trading actions are part of this PR. Real production operations require new owner-scoped approval and signed GitHub WIF/Drive authorization separately from current metadata-only PR17.

## Safe draft implementation

- scripts/mst_dynamic_watchlist_contract_lab.py — stdlib-only function freeze_sheet_values, immutable normalized membership and SHA256 digests, plan_incremental_refresh for add/pause/remove/resume and stale/same-generation denial, aggregate no-price safety receipt, wholly invented CLI demo. It never connects to a Sheet or Cloud resource.
- tests/test_mst_dynamic_watchlist_contract_lab.py — 55 deterministic fictional positive and negative QA cases: schema, duplicate symbols, invalid inputs, empty state, snapshot order invariance, toggles, no destructive delete, no cross-namespace mutation, rollback denial, source imports and fake receipt.
- This design document is the third additive file. **No workflow** is enabled or added: existing protected-main Foundation CI is sufficient to run the synthetic tests on PR, and no collector is dispatchable.

## Open external gates; no premature implementation claims

- Real private Google Sheet creation, auth/ACL and error-checked consistent values.get adapter, signed trusted revision and verified rollback floor.
- Owner's initial enabled/paused symbols; only owner may choose them.
- Explicit owner-selected cadence (example 5m is not yet locked), valid HOSE/HNX/UPCoM calendar, eligible closed M5–D1 sources, SSI/DNSE/VCBS license and GitHub runner permissions, source-native units and corrections.
- Actual Google OIDC → GCP WIF → service-account Drive metadata and content-read scope; PR17 still draft and not deployed. Least-privilege separate Cache write identity and authenticated multiwriter CAS.
- Safe incremental provider adapter with source-specific budgets and no crossover into the Scanner's own cache/workflow.

Existing broad PR8, isolated WIF PR17 and Market Scanner synthetic PR18 remain independent drafts. This document is not a release, live watchlist, production trading, Google Sheet, Cloud ACL or a license for market API reuse.
