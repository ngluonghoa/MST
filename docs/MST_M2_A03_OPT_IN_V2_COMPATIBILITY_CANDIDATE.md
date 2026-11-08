# MST M2/A03 — Opt-in v2 sidecar compatibility contract (candidate)

**Status:** TECHNICAL_CI_EVIDENCE / OWNER_APPROVAL_PENDING / DO_NOT_MERGE.  
**Repository:** `ngluonghoa/MST`, Draft PR #8.  
**Original pinned main:** `4048f91beaaa3410116d97e35896c8b688384e19`; Git tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`.  
**Source:** Swing Trading 1.8 `cd90c1babae8912db31490ad614fc2ad2f868042`.

## 1. Explicit compatibility boundary
- `swing_trading.replay.ReplayClock`, `swing_trading.contracts.Evidence` and `swing_trading.contracts.SignalDecision` remain byte-identical **v1 legacy** implementations. Their historical permissive runtime constructor/assignment behavior is intentionally preserved for legacy callers, not certified secure.
- Opt-in module `swing_trading.strict_contract_v2` adds `StrictReplayClockV2`, `StrictEvidenceV2`, `StrictSignalDecisionV2`. Callers must import v2 explicitly. No original public module exports are redirected.
- `StrictReplayClockV2` rejects ordinary direct UTC clock rewinds and invalid types/timezones. It is **not** a trusted source-clock or tamperproof hostile-process clock.
- `StrictEvidenceV2` requires a real Python bool and typed UTC datetime, `StrictSignalDecisionV2` requires exact Strategy/DecisionStatus enum types and a tuple of StrictEvidenceV2. These are **typed caller claims only**, not licensed/provider-signed source evidence or rights.
- `legacy_to_v2_unverified` and `v2_to_legacy_unverified` explicitly migrate only evidence-free UNVERIFIED synthetic records with valid Strategy enum. Neither performs automatic permissive-v1 coercion or promotes a trading state.

## 2. Versioned wire boundary
- Proposed JSON discriminator: `mst.signal_decision.v2`.
- `decode_untrusted_v2_json` accepts **only** canonical exact-key JSON with a known zone and Strategy and `UNVERIFIED` with empty evidence; rejects unknown/missing/extra fields, unknown versions, duplicate JSON keys, oversized/nonfinite/badly typed input and any `DETECTED` or `NOT_DETECTED` claim.
- `encode_unverified_v2_json` emits stable sorted compact JSON for strictly typed UNVERIFIED/no-evidence records only.
- This is an **engineering-only conservative adapter**. It is not the full public v2 wire contract for authenticated evidence or real actionable detections. A future v2 source-attested decoder must be scoped separately, require provider authorization and remain fail-closed.
- No external data rights, signed provider provenance, real market data, cache persistence or brokerage execution rights are created.

## 3. Legacy consumer and port interaction
- Legacy `BacktestHarness.from_contracts` intentionally checks `isinstance(clock, ReplayClock)`; it **must not** silently accept `StrictReplayClockV2` as a v1 versioned port. An explicit v2 PortDescriptor/adapter and separate consumer golden tests are required for a production-quality v2 backtest harness.
- Other v1 clients can continue on the original v1 classes without mandatory migration. App-level wiring to v2 is *opt-in*, explicit and not yet approved in MST.
- Do not conflate equal names or behaviors with ABI compatibility: distinct v2 class identities are deliberately separate. No legacy serializer or v1 signed-domain/cache fingerprint is modified.

## 4. Test and inventory acceptance
- Original legacy ReplayClock and contracts Git blobs must stay exactly `38c2b0a6c0cdf531e5b3ade6d68950d1cbeed97a` and `4cec604057ab9909a5af3971f3693ae9563e9d3f` respectively.
- CI must pass inherited 1,332 tests, plus opt-in v2 negative/golden tests on Python 3.11/3.12, 63 engineering contract tests, H2/H3 matrix generated from **64** source files, lint/wheel/isolated install and dependency checks.
- Generated H3 change is strictly a new `strict_contract_v2` module row plus legacy `contracts` and `replay` consumers rising from 7→8 and 31→32. Their LOC, control flow and blob hashes must NOT change.
- Any passing tests are engineering fixtures, not actual live market/source/corporate-action verification or 16 calibrated detectors.

## 5. Choice / gate / rollback
- **Preferred design under uncertainty about external v1 clients:** opt-in v2 sidecar rather than the in-place breaking candidate draft PR #7. The PR #7 experiment stays available in GitHub history, but must never be merged in addition to this alternative.
- Before PR #8 merge: obtain owner approval of the v2 namespace, public version/schema plan, explicit consumer migration, security boundary, signed provenance and N/N−1 rollback; complete scoped A02 independent acceptance for the impacted interfaces. 63/63 manual final signoffs remain a separate open task.
- The inherited Python package metadata stays `swing-trading-1-8==0.0.1` on draft; **this is not an approved v2 package release**. Decide explicit versioning and packaging before any release.
- Before merge, rollback is close PR #8, leaving pinned main unchanged; after separately authorized merge, use a reviewed protected revert PR and new CI, never force-push main.
- All development, CI, docs and release are **GitHub + Google Drive Cloud-only**; no Mac, MOCHI, or other local project runtime.

**Decision state:** PROPOSED/TESTED, NOT OWNER-APPROVED. Do not automatically authorize merge, release or trade.
