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
- Legacy `BacktestHarness.from_contracts` intentionally checks `isinstance(clock, ReplayClock)`; it **must not** silently accept `StrictReplayClockV2` as a v1 versioned port. A **separate synthetic-only v2 port consumer** now exists in `v2_replay_port.py`; it is not a production backtesting implementation or a replacement for the original harness.
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

## 6. Scoped versioned v2 replay port — synthetic fixture only
- NEW `swing_trading.v2_replay_port.StrictReplayHarnessV2` uses explicit `PortDescriptor("replay.causal_events", "2.0.0", "SYNTHETIC_TEST_ONLY", ("available_events",))` and `PortDescriptor("rules.zone_registry", "2.0.0", "SYNTHETIC_TEST_ONLY", ("evaluate",))`. Existing `engineering_contracts.py` is reused **without modifying its original source blob**.
- `StrictReplayHarnessV2.from_contracts` requires an exact `StrictReplayClockV2`. The immutable/frozen harness also validates both mandatory descriptors in `__post_init__`, so **direct construction cannot bypass v2 port-version checks** or replace a wiring field afterward. Structural checks precede provider/rule invocation; no automatic v1 substitution, provider fallback or live rights. The legacy `BacktestHarness.from_contracts` continues to reject the strict clock.
- `visible_events` accepts typed `CausalMarketEvent` fixtures only, gates by both event time and first-known time, and sorts deterministically. It does NOT prove source publisher truth or a real market calendar.
- `evaluate_unverified` accepts only exactly matched zone/strategy and a typed `StrictSignalDecisionV2(status=UNVERIFIED, evidence=())`. Callbacks asserting `DETECTED`, `NOT_DETECTED`, fake evidence or mixed identities fail closed; 16 zones and both strategies remain uncalibrated.
- The existing **in-memory** `EngineeringPortRegistry` demonstrates v2 add/resolve/replace/rollback; test fixtures pin a v2 consumer and prove an incompatible downgrade/replacement is rejected without corrupting the previous pointer. Rollback to a lower minor is permitted only when *all pinned consumers* allow it. No distributed Cloud service, atomic Google Drive manifest, independent signing or hot-swap operational authority follows from this fixture.
- New `tests/test_m2_a03_v2_replay_port.py` supplies **25** explicit v2 port, consumer, fail-closed, deterministic replay and rollback tests, including direct-construction bypass and immutable wiring guards. `tests/test_m2_a03_legacy_blob_parity.py` adds 3 independent Git blob SHA checks covering ALL 63 inherited source Python modules and pinned package metadata. PR #8 therefore contains **55** new opt-in/parity tests overall (27 earlier + 25 v2 ports + 3 blob lock), alongside the 1,332 legacy tests = **1,387** tests per Python version. H3 inventories 65 source Python modules (63 pinned originals + strict_contract_v2 + v2_replay_port), without altering any of the 63 legacy source files.
- The additional v2 module updates H3 source importer numbers: `replay` consumer count remains 32 from the earlier v2 module, `contracts` importer rises 8→9, and `strict_contract_v2` consumer count becomes 1. These are static import counts, not runtime consumer approval.
- Both the v2 sidecar and this versioned port are **draft engineering artifacts, not a released v2 package**. Continue to require user-owner compatibility/version signoff, all protected CI, licensed provider authorization and formal rollback before any merge/release. Never combine the closed in-place PR #7 with opt-in PR #8.

## 7. Evidence snapshot: v1 exact Git-tree custody and scoped v2 CI
- Locked source identity: `MST/main@4048f91beaaa3410116d97e35896c8b688384e19`, tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`, pinned Swing original source `cd90c1babae8912db31490ad614fc2ad2f868042`.
- CI test `tests/test_m2_a03_legacy_blob_parity.py` independently computes canonical Git blob SHA-1 with `blob <bytes>\\0<payload>` for each of the 63 pinned v1 source files; asserts no unexpected extra Python modules beyond the two explicitly scoped v2 modules; separately locks `pyproject.toml` to original SHA. This is stronger than assuming a total test-count PASS proves byte-for-byte legacy parity.
- Current PR #8 head before this documentation sync: `c5679e0c3620593513d179ac1cd08db9e427e0ea`; GitHub PR CI `42508469127` and push CI `42508463593` both completed SUCCESS: Python 3.11 and 3.12 `1387/1387`, engineering contracts `63/63`, H2/H3/lint/wheel and isolated package install PASS. Later documentation-only commit must be revalidated on its own HEAD before considering this exact PR SHA green.
- A structurally compatible v2 port remains only a synthetic engineering contract. It cannot authenticate a provider, certify broker permissions, attest live data, confer deployment authority or prove semantic parity of a future third-party v2 implementation without independent golden/negative tests.
- **Final acceptance not implied:** A02 63 manually signed module dispositions OPEN; v2 public ABI/schema/package version and owner approval OPEN; Draft PR #8 unmerged; no live source execution or deployed v2 backtest.
