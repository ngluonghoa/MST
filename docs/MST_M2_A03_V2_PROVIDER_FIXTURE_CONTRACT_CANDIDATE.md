# MST M2/A03 — Synthetic provider adapter v2 compatibility gate (candidate)

**Status: TEST_FIXTURE_ONLY / OWNER_APPROVAL_PENDING / NO_LIVE_MCP / DO_NOT_MERGE**
**Scope:** Draft PR #8 https://github.com/ngluonghoa/MST/pull/8, independent opt-in v2_source_adapter.py; original pinned Swing Trading v1 remains byte-identical.
**Architecture:** ADR-002 forward-compatible provider N registration is a design and in-memory fixture, not an approved production connector.

## 1. Provider names are NOT source connections

FixtureSourceRegistryV2 explicitly registers three immutable metadata-only fixture identities:

| Namespace | Synthetic fixture endpoint | Scope |
| --- | --- | --- |
| SSI | fixture.ssi.d1 | metadata test only |
| DNSE | fixture.dnse.d1 | metadata test only |
| VCBS | fixture.vcbs.d1 | metadata test only |

These are invented fixture identifiers, NOT real MCP endpoint names, capability or permission grants. This module does not import a connector client, expose credentials, invoke callbacks, retain licensed OHLCV, infer first-known market timestamps, or contact any provider. A fourth future namespace such as FOURTH can be registered only explicitly; NO implicit fallback or SSI/DNSE/VCBS data mixing exists. Actual provider-4 onboarding requires separate authenticated transport, licensing, capability, quality, rate limits and rollback evidence under M3.

## 2. Explicit typed contract

- FixtureSourceIdentityV2(provider_id, endpoint_id, version=2.0.0) constrains provider and fixture endpoint name and validates strict versioned identity.
- FixtureProbeRequestV2 has only exact provider, fixture endpoint, normalized symbol, allowed timeframe, and UTC as_of_utc; no source data payload or credentials.
- FixtureProbeReceiptV2 has state=UNVERIFIED only. Source/retention/trading authority flags are permanently false; caller attempts to set true or verified/detected states fail closed. It is NOT an authentic signed provider receipt.
- FixtureSourceAdapterV2.probe is deterministic and pure, checks exact provider/endpoint, and cannot call a live MCP connector.
- FixtureSourceRegistryV2 has explicit register/bind/resolve/replace/remove keyed by provider. Structural H2 PortDescriptor(source.fixture_probe, 2.0.0, provider, probe) validates exact contract ID, version, scope and callable method.
- In-memory rollback 2.1.0→2.0.0 is permitted only if no attached consumer demands 2.1.0. Invalid provider/endpoint or version changes preserve previous registry state; attached consumers block removal. This is NOT a Cloud distributed swap, CAS, signed recovery or LKG witness.

## 3. Trust-boundary separation

The fixture adapter MUST NOT be used as a market-events adapter for StrictReplayHarnessV2. Its port ID differs from replay.causal_events and FixtureProbeReceiptV2 is not typed CausalMarketEvent. Negative tests prove both boundaries. Metadata UNVERIFIED does not attest a market event, licensed retention, exchange truth, or a trusted first-known timestamp.

Not implemented: actual MCP authorization, source freshness, source quality, validated candles, corporate actions, provider-isolated Google Drive chunk persistence, secure provider credentials, external revocation/permission verification, operational Cloud failover, trading or data rights. These belong to M3/M4 independent gates.

## 4. CI, source parity and release gates

Tests/test_m2_a03_v2_source_adapter.py contains 29 synthetic unittest cases covering SSI/DNSE/VCBS isolation, explicit fourth provider registration, false-rights enforcement, bad timestamp/timeframe/symbol, endpoint/scope/contract/version mismatch, fail-closed data-type handling, safe explicit replacement/rollback with consumer pins, and forbidden coupling to replay market-events. These are never real API tests.

The existing tests/test_m2_a03_legacy_blob_parity.py locks all 63 original Swing Trading source Python Git blobs and original pyproject.toml. It now explicitly allows exactly three new opt-in source modules: strict_contract_v2.py, v2_replay_port.py, v2_source_adapter.py (66 source modules in candidate branch). Protected main remains 63 original modules.

Expected candidate total, pending final CI: 1,416 unittest cases on each Python 3.11 and 3.12 (1,332 legacy + 27 strict domain + 25 replay port + 3 legacy blob + 29 provider fixture), plus engineering 63 tests, H2/H3 source matrix/lint/wheel. Passing engineering tests cannot grant production rights, trade authority, release or a functioning source adapter.

Keep PR #8 DRAFT and UNMERGED until user-owner approval of v2 API/version/schema, future authenticated provider onboarding, source rights and rollback. Original locked baseline is main commit 4048f91beaaa3410116d97e35896c8b688384e19, tree d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e; old in-place PR #7 was closed unmerged. Issue #4 https://github.com/ngluonghoa/MST/issues/4 and issue #6 https://github.com/ngluonghoa/MST/issues/6 remain open.
