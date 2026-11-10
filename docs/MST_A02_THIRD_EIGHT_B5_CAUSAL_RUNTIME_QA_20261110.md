# MST A02 — Third Distinct Eight Original V1 Runtime Modules: B5 Geometry, Causality and Backtest

QA ID: MST-A02-V1-B5-CAUSAL-THIRD-EIGHT-001
Date: 2026-11-10 (Asia/Ho_Chi_Minh)
Verdict: **40/40 newly added V1 actual-function tests PASS; 26/26 code-HEAD GitHub Actions SUCCESS; 0/63 owner module signoffs.**
Work: https://github.com/ngluonghoa/MST/pull/8 (Draft, unmerged).
Architecture: Option A GitHub + Google Drive ONLY, cloud-hosted tests using synthetic fixtures. NO real market feed, trade, broker, owner crypto root or real Drive licensed-cache operations.

## 1. Exact original-source and coverage boundary

Upstream Swing Trading 1.8 commit cd90c1babae8912db31490ad614fc2ad2f868042, protected MST main 4048f91beaaa3410116d97e35896c8b688384e19, original Git tree d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e. An existing independent live GitHub REST tree-lock workflow ran within the dedicated hosted job and verified all 63 inherited V1 package paths unchanged across original upstream/main/PR, and exactly eight already-known V2 opt-in sidecars. No original V1/V2 module was edited.

Third tranche invokes eight DIFFERENT original V1 modules (not among the earlier two tranches): b5_feature_pack, b5_phase_contract, b5_formula_geometry, b5_calibration_draft, b5_temporal_split_audit, causal_indicators, causal and backtest. This makes 24 DISTINCT V1 modules having selected synthetic executed behavior cases across three eight-module batches. **39 of 63 originals remain outside this grouped runtime review.** The H3/AST 63/63 inventory remains static, NOT executed behavioral certification. Even the tested 24 are not fully certified and none signed by a human owner.

The review-only orchestration imports pre-existing synthetic fixture constructors from the project's tests/ directory using PYTHONPATH=tests, while all B5/causal/indicator/Backtest domain functions actually invoked are the inherited source-locked V1 implementation; the fixtures are NOT authoritative market data or replacement implementations.

## 2. Cross-module B5 first-known, evidence and arithmetic boundaries

Six fake intraday timestamps have no provider origin. For both original Strategy.SHORT and Strategy.SWING and each B5/E_RECLAIM and B5/E_FAILED_BREAK variant (4 combinations), the real inherited B5 feature extractor returns DATA_UNVERIFIED before the M15 retest verification at synthetic minute 49, then EXTRACTED_UNCALIBRATED at minute 60. The real phase manifest inspector with complete synthetic receipts returns PRESENT_UNCALIBRATED; the real raw geometry engine with a causally available anchor returns RAW_GEOMETRY_UNCALIBRATED. Every variant stays non-actionable, detector_approved=false.

Removing RF_VOLUME from eight typed ingredients yields RECEIPTS_MISSING rather than a fabricated negative signal; duplicating a receipt yields RECEIPTS_UNVERIFIED. Failed-break geometry without its earlier independently closed anchor is ANCHOR_BLOCKED, not inferred. Cross-instrument and late-known pivot protection is exercised. No B5 entry, Stop Loss, Take Profit, confidence, threshold, signal or executable policy is inferred from Decimal arithmetic.

B5 calibration registers 24 unapproved parameter slots (2 strategies x 2 variants x 6 axes) and 4 unapproved validation protocols; all numeric candidate/calibrated values remain None; an injected numeric parameter fails closed. Inherited temporal split checker marks the supplied train/validation/holdout structure only STRUCTURALLY_SEPARATED_UNCERTIFIED, with zero actual official VN exchange calendar, licensed history or OOS performance proof. A training label overlapping validation returns BLOCKED with TRAIN_LABEL_LEAKS_INTO_VALIDATION; validation overlap with holdout, duplicate event IDs and missing embargo are separate safety requirements.

## 3. Indicator arithmetic and causal backtest review

Wilder ATR14 on fabricated fully closed D1 candles produces Decimal 4 using 15 D1 inputs; 13 D1 bars do not qualify and return BLOCKED. RVOL_TF20 on fabricated same-timeframe history produces Decimal 1 from 20 strictly comparable prior bars plus target (the result's used_bar_count correctly reports 21); dropping one comparator returns BLOCKED. Even successful indicator math stays COMPUTED_UNCALIBRATED and data_certified/parameter_approved/actionable false; RVOL_TF20 is explicitly not session-time normalized RVOL_TOD.

The original CausalMarketEvent and BacktestHarness accept typed event revisions only, with a fabricated event r2 discovered at T+10 invisible at T0 while r1 is visible; advancing the replay clock exposes r1,r2. An event first-known before its event-time, an untyped replay source or a manifest without source_snapshot_id fails closed. This harness is NOT a real backtest, trained model or P&L evaluator and has no live trading activation.

## 4. Additive PR8 files and cloud-only CI

- scripts/m2_a02_b5_causal_eight_runtime_lab.py: invokes eight actual original V1 modules, synthetic fixture-based 4 strategy-variant B5 progressions, calibration/temporal-split, ATR/RVOL and causal replay. Emits an aggregate 13-case boolean safety receipt; all production approval flags FALSE.
- tests/test_m2_a02_b5_causal_eight_runtime_lab.py: **40 actual-source tests** covering B5 late-known/cross-identity/missing-duplicated evidence, geometry anchor, frozen grid, temporal overlap, indicator warmup/comparator, future event, missing source pin, and no owner/trading.
- .github/workflows/m2-a02-b5-causal-eight-runtime.yml: GitHub-hosted same-repo Draft PR8 only, permissions contents:read; first fetches remote upstream/main/PR original Git tree lock, then 40 tests and runtime receipt. Review-only JSON uploaded to GitHub Actions for 14 days; no keys, real Drive market data, source provider API, secrets, broker, ACL/ref/ruleset/witness update or merge.
- docs/MST_A02_THIRD_EIGHT_B5_CAUSAL_RUNTIME_QA_20261110.md: this detailed QA, mirrored to Google Drive.

During the first run the new review harness had a syntax error in one comment, then an incorrect test expectation that RVOL consumed only its 20 comparators. Both were corrected **in the added harness only**, not the original V1 code. Final successful CI reran the full tests and proved the original RVOL interface consumes 21 total bars, including the target. Failed intermediate runs must not be represented as success.

## 5. Verified GitHub Actions results

Exact successful code/workflow HEAD: 7628096537125debeb94c2b88dac9df24e35bdcb.
Dedicated third tranche: https://github.com/ngluonghoa/MST/actions/runs/42768318823 — **SUCCESS 40/40 new tests**, 13 checked business/safety statements all true; remote upstream/main/PR tree source lock PASS; B5 and backtest never actionable. Receipt status THIRD_EIGHT_REAL_V1_B5_CAUSAL_RUNTIME_CASES_PASS_OWNER_AND_PRODUCTION_NO_GO.
Foundation: https://github.com/ngluonghoa/MST/actions/runs/42768318784 — **SUCCESS 3/3 jobs**, Python3.11 2625/2625, Python3.12 2625/2625, original engineering source63/63 and H2/H3/lint/wheel PASS.
Exact code/workflow HEAD **26/26 GitHub workflows SUCCESS**.

Once this Markdown QA report is committed, its own final report-containing commit must be read back separately before claiming 26/26 on that new HEAD.

## 6. Owner and release NO-GO

A02 formal owner module dispositions: **0/63**. A03 full V2 ABI and behavior parity not signed. Owner decisions OA01–OA06 all OPEN; independent G01 signer/root, G02 externally monotonic floor, G03 two independently authenticated writers/server CAS, G04 vendor licensed source, G05 real Google Drive physical cache and ACL, G06 revocation, G07 independent provenance, G08 release all OPEN. M3/M4/M5/M8 production and trading BLOCKED. Previous V1 legacy compatibility gaps ReplayClock direct public-field rewind and Evidence.verified truthy non-boolean acceptance remain unchanged and pending owner-reviewed strict V2 decisions.

Next safe A02 work: expand meaningful executed inherited V1 fixtures among remaining 39 original modules; prioritize input source routing, trading calendar, causality, migration/retention boundaries. No owner approval, protected source patch, production trade or release from synthetic CI.
