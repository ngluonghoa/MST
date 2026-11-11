# MST — On-Demand Market Scanner, design and synthetic safety boundary

Date: 2026-11-11. Status: **OWNER APPROVED DESIGN; SYNTHETIC DRAFT ONLY; LIVE MARKET SCAN NO-GO**.

## Decision and invariant

One MST project with two independent operational domains:

| Dimension | Watchlist Engine | Market Scanner |
|---|---|---|
| Universe | Owner-maintained, dynamically editable list | Eligible HOSE/HNX/UPCoM universe from a source-issued point-in-time listing master |
| Trigger | Separate future incremental schedule (not activated) | **Manual request only**, never scheduled |
| Private Google Drive target (proposed, NOT created) | mst/watchlist/... | mst/scanner/... |
| Cache/manifest writer | Independent Watchlist identity and revisions | Independent scanner identity and revisions; cannot write Watchlist |
| Output | Followed-symbol cache/analysis | Candidate inbox with rank evidence and abstentions |
| Candidate enrollment | User edits or approves Watchlist revision | **Never automatically edits Watchlist** |

There is no additional standalone repository. No full-market automatic refresh is permitted. A scan may cover the whole *eligible authorized listed market*, not just the VN-Index's components. It must not silently expand from an unknown master or unavailable provider.

## Planned Cloud pipeline (NOT implemented here)

1. A user explicitly requests a scan. A manually gated workflow records authorized person, time, venue set, budget and mode. ChatGPT cannot be assumed to dispatch GitHub Actions until a separately authenticated integration exists.
2. Lock a signed/versioned point-in-time universe manifest with exchange, symbol, eligibility, listing/delisting and suspension flags; disallow ambiguous venue/symbol, duplicates, missing revision, stale evidence, wildcard and overflow.
3. First pass uses licensed, source-qualified D1 *closed* bars, not synthetic substitutes. Do the cheaper market-wide screening using thresholds explicitly governed by MST strategy specification, e.g. liquidity, trend, relative strength and volatility. Preserve the original Swing Trading parity; do not invent a production strategy in this lab.
4. Only bounded shortlist candidates receive optional M5/M15/M30/H1/H4/D1 follow-up (20–50 is a *configurable proposal*, not a required number). Each bar must pass proper market closure and adjusted/first-known issuer-source revision checks. If VCBS native bar completeness remains unverified, abstain rather than invent candles from ticks.
5. Write only an isolated candidate evidence manifest and Scanner cache, with independent immutable lineage, CAS, signers, freshness/TTL, quota and antirollback. Do not mutate Watchlist cache, refresh schedules or dynamic Watchlist.
6. Present candidate inbox with ranked evidence, watch reasons and uncertainty / insufficient-data flags. Only explicit owner selection can call Watchlist control-plane approval, which writes a new validated Watchlist revision.

## Safety gates before any production action

- Source-issued, complete and correctly PIT-snapshotted HOSE/HNX/UPCoM master and official calendars.
- Contracts allowing real GitHub runner vendor API use, historical data retention and price/volume adjustment; quotas and bounded costs.
- Independent Google WIF signed identity, dedicated Drive Scanner namespace/ACL and writer; never reuse a Watchlist writer identity.
- Authoritative SSI/DNSE/VCBS multi-timeframe closed-bar availability, corrections, first-known and unit/adjustment provenance.
- Snapshot/manifest key identity includes universe revision/as-of, source revision, strategy/policy, venue calendar, closed-bar proof and Cloud cache writer/floor.
- Fail-closed on master/permissions/source outage, duplicate/ambiguous securities, stale revision, scope overflow or concurrency conflict.
- End-to-end manual-only workflow proof, no cron, idempotence/cancellation and budget isolation from Watchlist.
- Explicit owner signoff for production promotion; no trading or auto-enrollment authority.

## Exactly what is implemented in this isolated draft

- scripts/mst_market_scanner_manual_contract_lab.py: stdlib-only synthetic-freeze plan, deterministic SHA-256 snapshot, invented eligible-listing data, injected fictional probe-score ranking, strictly fenced Scanner-only synthetic object keys, no external I/O, safe no-price receipt.
- tests/test_mst_market_scanner_manual_contract_lab.py: 63 intentionally synthetic functional/negative/static boundary tests, including missing/master overflow, as-of eligibility, wrong venues, duplicate symbols, manual-only workflow and zero Watchlist mutations.
- .github/workflows/mst-market-scanner-synthetic-manual.yml: a separate **manual-only** synthetic contract QA workflow, restricted to protected main, pinned GitHub actions, read-only repository token, no Google OIDC, secrets, vendor calls, live source data, persistent scanner cache or schedule.

These new files are strictly **additive** and do not replace Swing V1 sources, existing opt-in Cache V2 architecture, or the separate WIF manual-readiness PR #17. This new manual workflow is on a draft PR, not protected main; therefore it is NOT currently dispatchable there. Foundation CI on the draft may verify fictional code, not real market eligibility/licensing or Cloud data operations.

## Promotion separation

- Synthetic draft QA can be reviewed, amended, and eventually independently approved.
- Google WIF metadata-read readiness PR #17 remains a separate approval decision and does not authorize scanner Cloud operation.
- No Schedule or full-market collector is proposed until all production gates and a new explicit owner approval.
- Watchlist dynamic design (§125) and this on-demand scanner decision (§126) are independently maintained in MST canonical Handoff and Spec.
