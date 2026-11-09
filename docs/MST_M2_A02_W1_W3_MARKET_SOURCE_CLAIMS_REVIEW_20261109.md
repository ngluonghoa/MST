# MST M2/A02 W1/W3 — Market-data lineage, source claims and five-minute planner review

**Date:** 2026-11-09  
**Scope:** Three original 1:1 source modules, six new tests only; NO changes to any inherited v1 module.  
**Status:** scoped engineering investigation, NOT final per-module owner signoff / not M3 production source acceptance.  
**GitHub:** [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8), main pinned `4048f91beaaa3410116d97e35896c8b688384e19` with unchanged source tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`.

## Source identity and manual review scope

| Module and SHA-1 Git blob | Reviewed boundary | Proposed disposition |
| --- | --- | --- |
| `market_data.py` — `4640b6aae7bcb7593436a964464dfc5d959a0c2a` | `ObservationRevision` / `CanonicalCandle.eligible_for_confirmed_signals` and identity/closure checks | Preserve exact v1 behavior; external source timestamp attestation required |
| `source_quality.py` — `92fcb45745303fab4d1a39edd3af6ad85517a7ff` | `SourceEvidence`, canonical revision, independent quality axes and `resolve_as_known` | Preserve exact v1; add independently authenticated source custody before consumer authorization |
| `cache_fetch_planner.py` — `ce7b239ee750162f84f5680c9ad9b87ff9ad6767` | `SourceCapability`, mutable local cursor, periodic correction/full session and claimed immutable final head | Preserve exact v1; external calendar/head/capability attestation must precede real adapter |

Test/consumer audit includes `tests/test_market_data.py`, `tests/test_source_quality.py`, `tests/test_cache_fetch_planner.py`, `v2_source_adapter.py` and `v2_replay_port.py` boundaries; the complete graph/owner disposition remains pending A02 final 63-module review.

## Six new synthetic negative/boundary controls

1. **First-known is only a caller claim**: a v1 `ObservationRevision` can claim `first_known_time_utc` at T while `retrieved_at_utc` lies after a target as-of; `eligible_for_confirmed_signals` returns true on the first-known claim. This is not necessarily a time-travel defect if a real source was already public at T; it is a counterexample to *independent evidence of publication*, which v1 does not provide. A future verified source-clock custodian must bind the two meanings and producer timestamp.
2. **Provenance endpoint lacks authenticated binding**: two `CanonicalCandleV12` records with the same source observation identity but different caller-supplied `SourceEvidence.endpoint` and snapshot ID can both have true conditional `confirmation_prerequisites`. The Boolean fields are self-claims; real licensed source identity must be checked by an authenticated adapter and cannot be granted from these fields.
3. **Revision visibility is separate from confirmation**: a revision whose source `first_known` is T+15 but which is fetched at T+20 and verified at T+25 is visible to `resolve_as_known` at T+16; confirmation prerequisites are false until after the check time. No trade/signal permission is gained.
4. **Exact correction-known boundary is fail-closed**: a future revision becomes a second visible candidate at its exact `first_known_time_utc`, causing `SOURCE_OR_REVISION_CONFLICT` rather than silently replacing an earlier provider/version. A separately approved resolution/correction policy is required for production.
5. **Local claimed finality can preempt a due full correction scan**: even when `last_full_reconciled_utc` is old, caller flags `session_ended_verified=True` and `immutable_source_head_verified=True` cause `REUSE_CLOSED`; in every result `certified_source_freshness=False` and `data_authorized=False`. Never treat this local optimization as verified immutable provider finality without independent head attestations.
6. **Unknown provider capability is always blocked**: even with the same claimed finality flags, `SourceCapability.UNKNOWN` yields `BLOCKED`. Do not invent incremental endpoint support for SSI/DNSE/VCBS.

New tests:
- `test_legacy_first_known_is_a_claim_not_an_authenticated_source_timestamp`
- `test_provenance_endpoint_is_only_a_claim_not_authenticated_binding`
- `test_revision_visible_before_retrieval_is_not_eligible_before_verification`
- `test_future_correction_visibility_starts_at_exact_first_known_boundary`
- `test_caller_claimed_finality_preempts_due_reconciliation_but_never_certifies`
- `test_unknown_capability_stays_blocked_despite_finality_claims`

## Boundary / owner-decision checklist

- Untrusted booleans `entitlement_verified`, `timestamp_semantics_verified`, `coverage_policy_verified`, `session_ended_verified` and `immutable_source_head_verified` are NOT crypto receipts.
- `eligible_for_confirmed_signals` and `confirmation_prerequisites` are **necessary, never sufficient**, for any actual trading action. The source files themselves say so.
- Source-specific first-known/arrival semantics, session calendar closure and complete revision/revocation streams require independent producer evidence. Do not silently substitute SSI→DNSE→VCBS or change instrument/timeframe/price basis.
- For a real Cloud-only M3/M4 implementation, require separately verified data contract/right-to-cache-on-Drive, signed or independently fetched identity/provenance, external rollback floor and an authenticated protected control-ref witness. Test source late corrections, 1→5→20 symbols and full-scope reconcile against licensed staging only after entitlement approval.
- No edits to source modules, no market truth certification, no GitHub main merge and no local Mac/MOCHI runtime.
- **A02 FINAL_OWNER_APPROVAL still OPEN** for all 63 modules. A scoped review and tests do not approve 63/63 or change the versioned MST v2 API.

## QA and rollback

Six new tests added to the previous 1,541 suite. **GitHub Actions PR run #42568823644** ([view](https://github.com/ngluonghoa/MST/actions/runs/42568823644)) completed **SUCCESS 3/3** on code+report commit `a8f68a3753a67b3e68ec0c4f86f3a0f1267957c3`: **1,547/1,547** Python 3.11, **1,547/1,547** Python 3.12, engineering **63/63**, H2/H3/lint/isolated wheel checks PASS. Following this documentation-only update, verify the final exact PR HEAD CI again. No source-module or Python-package inventory change is expected (63 legacy + eight opt-in v2 modules). Review CI before updating the canonical Google Docs or claiming PASS. If any test legitimately contradicts pinned legacy behavior, change the test or revert its addition; never rewrite old source to make the test pass by default.
