# MST M4 — Read-only GitHub reader-readiness blocking audit

**QA-ID:** MST-M4-READINESS-001 · **Date:** 2026-11-09 Asia/Ho_Chi_Minh  
**Disposition:** READ_ONLY_GATE_PASSED_BLOCKING; M4_SOURCE_CUSTODY_AND_READER_AUTHORIZATION_BLOCKED.

## Source locks / implementation

- Swing Trading source pin: `cd90c1babae8912db31490ad614fc2ad2f868042`; MST protected main: `4048f91beaaa3410116d97e35896c8b688384e19`, original tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`.
- Draft PR #8 only, source v1 63 modules and existing V2 files unchanged.
- New `scripts/m4_reader_readiness_preflight.py` reads the REAL GitHub remote baseline main branch/rulesets/witness ref through token-limited read-only GitHub Actions. Returns owner gates `SIGNED-G01..G08` and explicit FALSE producer/reader/trader authorizations. It does NOT validate or enroll an external signer.
- New `tests/test_m4_reader_readiness_preflight.py`: 26 tests including absent/present witness, apparently matching ruleset still blocked, owner/bypass unknown/unsafe, protected main SHA mismatch, malformed ref and SHA, wrong GitHub ruleset owner/ref, duplicate rulesets, untrusted proposal owner approvals, exact REST HTTP 404 versus 401/403/429/500 error propagation, never upgrading self-reported root/source rights.
- New `.github/workflows/m4-reader-readiness-block-gate.yml`: PR #8 same-repo only, GitHub-hosted runner, `permissions: contents: read`; no write privilege, secrets, market data, Drive or local/Mac/MOCHI.

## Exact observed GitHub Actions code checkpoint

**Code/workflow HEAD:** `dc682090d9800e021ac270e5478fa43e31192e64`.

[Read-only M4 readiness workflow #42610697466](https://github.com/ngluonghoa/MST/actions/runs/42610697466) SUCCESS: live GitHub REST reported:
- main source SHA `4048f91beaaa3410116d97e35896c8b688384e19`; `main_baseline_verified_for_this_read=true`.
- `witness_ref_exists_for_this_read=false` (real HTTP 404 for `refs/heads/mst/m4-witness/v1`).
- `witness_ruleset_visible_for_this_token=false`; `witness_bypass_list_visible_for_this_token=false` (unknown, NOT independently verified empty).
- `witness_actual_owner_authorization=false`; `witness_active_protection_effective_end_to_end_verified=false`.
- `cache_read_authorized=false`, `cache_write_authorized=false`, `trading_authorized=false`.
- `status=M4_READER_AND_PUBLISHER_BLOCKED_PENDING_EXTERNAL_OWNER_GATES`.

[Foundation CI #42610697263](https://github.com/ngluonghoa/MST/actions/runs/42610697263) SUCCESS 3/3: Python 3.11 **1742/1742**, Python 3.12 **1742/1742**, engineering **63/63**, source H2/H3/lint/wheel checks PASS. [Remote GitHub readback #42610697445](https://github.com/ngluonghoa/MST/actions/runs/42610697445), [synthetic registry cross-run #42610697372](https://github.com/ngluonghoa/MST/actions/runs/42610697372), [synthetic journal cross-run #42610697577](https://github.com/ngluonghoa/MST/actions/runs/42610697577) all SUCCESS.

**Important:** Final report-commit HEAD must have its *own* exact-head workflow status verified, separately from the code checkpoint.

## Security interpretation

GREEN means the read-only audit correctly refuses M4 authority; it is NOT proof of signed vendor receipts or production-ready data custody. A GitHub main-branch ruleset does not protect a non-existent M4 witness branch. Even a future GitHub witness ref + apparently matching ruleset does not establish owner signer key provenance, separate authenticated writer admission, durable monotonic external floor, global key revocation, vendor first-known rights, legal retention or actual Google Drive blob integrity.

All **SIGNED-G01..G08 are open**: G01 independent owner signer; G02 protected external registry/receipt floor; G03 true server-side two-account CAS; G04 licensed SSI/DNSE/VCBS provenance/corrections/retention; G05 physical Google Drive chunk SHA + protected GitHub ref/tree and two-service crash recovery; G06 global key/right revocation; G07 independent evidence-tier receipt; G08 A02/A03/M3/M4/M8 owner signoffs. Issues: [#16](https://github.com/ngluonghoa/MST/issues/16), [#15](https://github.com/ngluonghoa/MST/issues/15), [#13](https://github.com/ngluonghoa/MST/issues/13), [#14](https://github.com/ngluonghoa/MST/issues/14), [#10](https://github.com/ngluonghoa/MST/issues/10), [#9](https://github.com/ngluonghoa/MST/issues/9), [#4](https://github.com/ngluonghoa/MST/issues/4) and [#6](https://github.com/ngluonghoa/MST/issues/6).

No protected witness provisioning, real key enrollment, source ingestion, Drive cache writes, PR merge or trading. Cloud-only and original v1 lock retained.
