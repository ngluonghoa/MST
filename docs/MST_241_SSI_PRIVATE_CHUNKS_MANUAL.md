# MST §241 — SSI FastConnect native -> private unpublished app-owned Cloud CHUNK

**P0-C / manual owner-and-rights gated / NO_TRADE.** This is a *real-source capable but never automatically executed* workflow. Creating or testing this PR does not imply any live SSI or Google Drive market upload took place.

## Components

- .github/workflows/mst-private-source-chunks-manual.yml: workflow_dispatch only, exact repository ID/owner ID, protected main, confirm=STAGE_SOURCE_ONLY, one native timeframe, one symbol and bounded calendar dates. No push, PR, cron or background scheduler; contents: read; non-cancelling same-workflow group.
- scripts/mst_ssi_cloud_private_chunk241.py: fail-closed owner/retention/API/OAuth guard, discover exact private app-owned root MST_OAUTH_CACHE_V1 and child CHUNKS, read SSI FastConnect V3 marketdata via vetted adapter and serialize seven-field original source envelope without exposing provider HTTP responses or credentials.
- scripts/mst_private_chunk_readback240.py: exact-name Drive multipart upload, metadata owner/privacy/MD5, **two source-byte/media SHA-256 readbacks**, version and duplicate census. No MANIFESTS, update, overwrite, delete, highwater or publication.
- tests/test_mst_ssi_cloud_private_chunk241.py: mocked SSI, mocked Google Drive folder discovery and exact source-envelope restrictions. Full two-read fake HTTP tests remain in tests/test_mst_private_chunk_readback240.py.

## Necessary owner-supplied setup (never fake it)

Before **manual dispatch**, the repository owner must independently establish that the SSI FastConnect account/token is permitted to access and retain these specific native OHLCV observations in a private Drive copy. The connected ChatGPT MCP account is not a substitute for the app's GitHub Actions credentials or retention permissions.

Repo **Actions Secrets** (never put them in PRs, chat or logs):
- MST_SSI_API_KEY and MST_SSI_API_SECRET (market-data scoped only)
- MST_GDRIVE_OAUTH_CLIENT_ID, MST_GDRIVE_OAUTH_CLIENT_SECRET and MST_GDRIVE_OAUTH_REFRESH_TOKEN (existing Google OAuth drive.file scope)

Repo **Actions Variables** must explicitly be literal true **only if legitimately established**:
- MST_SSI_READONLY_OWNER_ACCEPTED
- MST_SSI_SOURCE_RIGHTS_CONFIRMED
- MST_SOURCE_RETENTION_RIGHTS_CONFIRMED
- MST_PRIVATE_CHUNKS_WRITE_ACCEPTED

The old MST_OAUTH_BOOTSTRAP_ACCEPTED variable must NOT equal true (folder-creation bootstrap must stay disabled). No service-account fallback, no GitHub PR/fork or rerun attempt allowed.

Workflow URL after protected-main merge:
https://github.com/ngluonghoa/MST/actions/workflows/mst-private-source-chunks-manual.yml

Dispatch confirm=STAGE_SOURCE_ONLY, native_tf D1/H1/M30/M15/M5, symbol FPT/HPG/DCM, from_date/to_date YYYY-MM-DD. Calendar bounds are enforced by the existing SSI native adapter; native H4/W1 and scanner scope are denied.

## Safety semantics

The owner/rights variables are asserted conditions; **they do not independently attest vendor rights, source timestamp first-known, price adjustment, exchange closure or complete historical coverage**. The final output is a count and boolean-only receipt. It never logs API bearer, source prices, raw vendor response, Drive file IDs or data SHA. A failed operation may leave an unpromoted orphan CHUNK and does not retry or delete.

Drive file naming is not atomic or unique. An exact list before/after and 2 readbacks increase detection of conflicts/corruption, but do not establish independent signed monotonic CAS or publication safety. A future separate P0-C change must bind chunks to validated versioned MANIFESTS and independent signed highwater under a separately reviewed transaction protocol. Until then **all B/S zones remain UNVERIFIED and NO_TRADE**. This workflow intentionally cannot write MANIFESTS, AUDIT, trade orders, alerts or a production Cache head.

## Source / release status

CI passing for this workflow verifies **fictional offline** transport and guard logic only. **Do not claim any successful live SSI upload until a main-branch manual workflow run demonstrably passes after rights and credentials are supplied.** Cache CHUNKS folder is still empty as last independently audited in §237. 2026-11-22 remains a conditional engineering RC goal, not production acceptance.
