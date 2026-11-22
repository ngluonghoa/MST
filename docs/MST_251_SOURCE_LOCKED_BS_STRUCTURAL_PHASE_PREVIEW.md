# MST §251 — Source-locked B/S structural phase evidence (UNVERIFIED / NO_TRADE)

**Scope:** Atomic extraction of four pre-existing, source-locked modules/tests from open Draft PR #23 pinned at `a3cca901f37f3dedd4d7a3ec49771b553b54c70d` into protected `main`. The extraction is **unchanged** from the reviewed draft. The preexisting dependent modules `causal_structure_geometry.py` and `zone_manifest_v03.py` have identical source blob IDs on `main` and in the pinned draft. Pinned master baseline remains Swing Trading 1.8 commit `cd90c1babae8912db31490ad614fc2ad2f868042`; relevant normative specification is original `01_MASTER_SPEC_v1.0_DRAFT` §24.4/§24.5/§24.10.

## Why this matters

The 16-zone manifest describes B1–B8/S1–S8 across phases R0/R_C/R_E/R_F, but **not all source formulas/calibration parameters are approved or implemented**. Current `engine.evaluate_unimplemented_zones` properly refuses to emit `DETECTED` or `NOT_DETECTED` without authoritative full-zone predicates. §251 adds bounded deterministic, causality-aware, actual Python **structural geometry ingredients** while preserving that hard stop.

- §207: four source-traced R_E closed BOS/pivot routes: B1, B3, B8 bullish and S4 bearish.
- §213: 14 additional **R_F component routes** across applicable B/S zones. These show that a closed price crossed a causally-known structural pivot at the required allowed TF(s), **not** that a complete zone is confirmed. The 18 routes are explicitly versioned and checked against the 16-zone source manifest/variant references. Other phase and OR/TP alternatives are not invented or silently selected.
- §214: B2/S2 causal near-support/resistance `R_C` **geometry-only evidence** with locked direction/TF, causal ATR/pivot and synthetic edge-case tests. A near threshold or unverified source clock cannot become a trading signal.

## Integrity gates and negative tests

All fixtures are synthetic. Tests cover positive & negative pivot crossings and projections for SHORT and SWING, immutable evidence fingerprints across repeat replay, temporal/first-known ordering, source/provider/price-basis/calendar/adjustment drift, corrected bar revisions, inappropriate TF, lookahead, out-of-scope zone/phase/variant, near/pivot invalid arithmetic, and **no trading**.

No network, broker, wallet, external provider API or Google Drive write is introduced. The module does not claim market source rights, venue close/first-known, calibrated lookback/epsilon/ATR or all 64 full phase predicates. Tests only certify implementation behavior for these **partial structural** ingredients, not equivalence of source-defined full detectors or real market profitability. The legacy engine and current 16-zone execution gates are **unchanged**.

## Release status

This is a meaningful P0-A **engineering increment**, NOT P0-A zone detector completion. Even if Foundation CI is green, all 16 B1–B8/S1–S8 remain `UNVERIFIED/NO_TRADE`; no source-validation authority, Cloud cache production, owner-private signer/CAS or release approval follows. Private app-owned `CHUNKS` and `MANIFESTS` remain empty until actual authenticated provider rights, read-only GitHub source verification, and separate retention permission are established.

On 2026-11-22 the last authenticated GitHub owner preflight run 45041453411 finished as a GitHub job but all SSI/DNSE source paths were `HOLD` (`OWNER_DECLARATION_NOT_TRUE`, `SECRET_GROUP_NOT_PROVISIONED`), so §251 does not pretend to unblock live source ingestion. PR #23 remains draft; only this four-file audited extraction plus this new standalone contract are in scope.
