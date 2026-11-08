# MST M2/A03 — Contract version and compatibility decision (candidate)

Status: TECHNICAL_REVIEW_READY / OWNER_ACCEPTANCE_PENDING.
Evidence: GitHub draft PR #7 https://github.com/ngluonghoa/MST/pull/7
Issue #6: https://github.com/ngluonghoa/MST/issues/6
Baseline main: 4048f91beaaa3410116d97e35896c8b688384e19
Baseline tree: d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e (exact pinned Swing 1.8).

## 1. Contract status and decision
Candidate strict MST Python-domain contract: v2.0.0 (PROPOSED, NOT RELEASED).
This intentionally changes runtime acceptance of previously tolerated, untyped inputs. It is therefore a potential behavioral breaking change, not merely a transparent bug fix. Public names, typed constructor signatures, ReplayClock.advance_to(), ReplayClock.known(), B1–B8/S1–S8 zone IDs, typed enums and valid typed decisions are preserved. Original main remains byte-identical to inherited Swing source until an approved merge.

Legacy Python behavior -> strict candidate behavior:
- Direct earlier ReplayClock.as_of_utc assignment: accepted -> ValueError, no clock change.
- Direct naive/non-UTC clock assignment: accepted -> ValueError, no clock change.
- SignalDecision strategy/status bare string: accepted -> TypeError; require Strategy/DecisionStatus enum values.
- Evidence.verified truthy string: accepted -> TypeError; require exact Python bool.
- SignalDecision evidence list or non-Evidence element: accepted or inadequately checked -> TypeError; require immutable tuple of Evidence instances.
- All unimplemented 16 zones continue to return UNVERIFIED, without any calibrated trading predicate.
- No provider rights or execution privileges are created by a verified=True claim.

## 2. Consumer evidence
A new AST test on all 63 src/swing_trading Python modules measured on GitHub Actions:
replay_module_importers=31; ReplayClock_calls=1; SignalDecision_calls=1; Evidence_calls=0; ReplayClock_direct_writes=1.
Importing replay.require_utc is not the same as constructing a ReplayClock. These are static call expressions, NOT a certification of reflection/dynamic loads or external applications. No static SignalDecision constructor was called with explicit string literal for strategy/status.
Existing 1,332 tests plus 27 A03 tests run on Python 3.11 and 3.12; include serial compatibility, dataclasses.replace, synthetic copy/pickle from trusted bytes, JSON typed conversion, all-zone UNVERIFIED golden and BacktestHarness causal replay. Do not unpickle untrusted data.

## 3. Versioned JSON and deprecation plan
The Python dataclasses are NOT themselves a JSON wire decoder. Enum values serialize as strings. Direct SignalDecision(**json.loads(...)) must be rejected by strict runtime boundaries.
Before exposing public v2 data, create a separately versioned wire schema discriminator (proposal: mst.signal_decision.v2), validated UTC timestamps and exact enum/bool/tuple fields, known required/optional field policy, unknown-version rejection and explicit adapter. A wire string such as SHORT may be mapped to Strategy.SHORT only after schema validation. No automatic VERIFIED/trade promotion.
Legacy v1 imported source and its source rights, cache namespaces, HMAC/signed-domain and historical records remain frozen. If real v1 serialized consumers exist, introduce an isolated v1 reader and migration with golden tests and rollback; never silently modify the 1:1 baseline.
Current draft package metadata remains inherited 0.0.1; this IS NOT an independently versioned v2 package release. G02 release/version manifest and consumer migration decisions must be resolved before a public version claim.

## 4. Trust and clock limits
Normal direct Python attribute assignments on ReplayClock now enforce monotonic UTC. Arbitrary same-process __dict__ manipulation, malicious unpickling, forged vendor timestamp, signed snapshot custody or hostile plugins are NOT prevented by this guard. Evidence.verified is a typed, caller-supplied engineering claim, never authenticated provider entitlement.
Cloud GitHub + Google Drive only. No Mac/MOCHI/local compute, real licensed OHLCV, source credentials or broker order rights.

## 5. Acceptance/rollback gate
Before any merge:
1) explicit owner acceptance of strict v2 input behavior, plus external-client impact and deprecation policy;
2) per-module scoped A02 technical disposition for replay.py and contracts.py, independent review, no implied 63-module final signoff;
3) protected PR all required check contexts green on actual HEAD with Python 3.11/3.12, H2/H3 regenerated matrix, 63 engineering tests, lint and wheel;
4) stable source baseline/branch tree SHAs, regression + negative + serialization tests, auditable release/schema version and N/N-1 rollback plan;
5) verified separate GitHub main CI after squash merge ONLY if merge is explicitly authorized.
If unapproved, KEEP PR #7 DRAFT, do not merge. Before merge rollback is simply close the PR. After an approved merge, rollback through a tested protected revert PR, never force-push main.
This is a CANDIDATE engineering policy and not a user approval or production deployment.
