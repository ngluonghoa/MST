# MST §249 — GitHub Actions owner source configuration presence preflight (NO HTTP)

Date: 2026-11-21 ICT. Main baseline `a98a037987876c1732b4bf831e9d8c310d0e987b`. This is an **actual protected-main manual GitHub Actions workflow**, but it is inert until a human manually dispatches it. It checks *only whether GitHub Actions passes owner-variable declarations and required secret strings to the runner*, never whether external SSI/DNSE/Google credentials work or whether the owner actually has data-retention rights.

## Live blocker evidence at design time

Authenticated GitHub Actions list at `/repos/ngluonghoa/MST/actions/runs?event=workflow_dispatch` returned seven manual runs, all OAuth/bootstrap/census/canary, none native SSI, DNSE or SSI unpublished CHUNK. Cloud Google OAuth app-owned folder bootstrap and fictional private canary DID run successfully 2026-11-18. Do **not** redo OAuth bootstrap unless independently necessary. GitHub connector listed only seven accessible owner repositories, all `visibility=public`, **no independently held private highwater repository available through this connector**. Do not mistake code from §244–247 for an operational private signer/CAS.

The new workflow does not disclose real provider/Google keys, live provider rows, refresh tokens or GitHub repo IDs into logs. Each missing category is summarized with safe fixed codes. It does not store data, re-run OAuth, call brokerage APIs, use an external REST token, touch private highwater or attempt a market Cache publication.

## Manual workflow and how to read the diagnostic

Workflow: https://github.com/ngluonghoa/MST/actions/workflows/mst-source-owner-config-preflight-manual.yml

Select **Run workflow**, branch **main**, input `confirm=CHECK_ONLY`, and inspect the `owner-source-readiness` job output. Defaults to `NO`, requiring an explicit selection. Main/repo identity/owner IDs, `workflow_dispatch`, exact workflow ref, first run attempt and numeric `GITHUB_RUN_ID` must match **before the script emits any diagnostic**. No cron/push/PR, no install dependencies and no other I/O.

Output includes four independent branches:
- `ssi_native_readonly` needs `MST_SSI_READONLY_OWNER_ACCEPTED=true`, `MST_SSI_SOURCE_RIGHTS_CONFIRMED=true` and the separately provisioned `MST_SSI_API_KEY` + `MST_SSI_API_SECRET`.
- `dnse_native_readonly` likewise `MST_DNSE_READONLY_OWNER_ACCEPTED=true`, `MST_DNSE_SOURCE_RIGHTS_CONFIRMED=true` and both `MST_DNSE_API_KEY` + `MST_DNSE_API_SECRET`.
- `ssi_private_chunk_stage` additionally requires the SSI read declarations and credentials, `MST_PRIVATE_CHUNKS_WRITE_ACCEPTED=true`, `MST_SOURCE_RETENTION_RIGHTS_CONFIRMED=true`, the existing Google OAuth client/secret/refresh credential trio, and `MST_OAUTH_BOOTSTRAP_ACCEPTED != true` (disable the one-time bootstrap mode after initial setup).
- `ssi_private_unpublished_manifest_stage` requires everything needed for private CHUNK plus separate `MST_PRIVATE_MANIFEST_WRITE_ACCEPTED=true`. **It never grants market Cache or publish permissions.**

`configuration_status=DECLARED_ONLY_UNVERIFIED` means only that required strings are present and literal owner variables have the declared value; it does NOT mean the vendor accepts credentials, that retention permissions are lawful, that Google OAuth refresh succeeds now, or that any source row is real/final. Missing configuration yields `HOLD` plus codes such as `OWNER_DECLARATION_NOT_TRUE`, `SECRET_GROUP_NOT_PROVISIONED` or `STANDALONE_OAUTH_BOOTSTRAP_FLAG_MUST_BE_DISABLED`. No actual secret values, secret names or private repo name appear in the printed receipt; the script does not attempt to validate such values.

## Next owner operational step

If SSI branch is `DECLARED_ONLY_UNVERIFIED` and owner has independently confirmed credentials and API read rights, then separately dispatch https://github.com/ngluonghoa/MST/actions/workflows/mst-ssi-native-readonly-manual.yml on **main**, `confirm=READ_SSI_ONLY`, `symbol=FPT`, `native_tf=D1`, `from_date=2026-11-19`, `to_date=2026-11-20`. **No Google Drive write** occurs in the read-only probe. If SSI auth fails, inspect only its fixed-denial code; do not paste credentials, bearer tokens or full vendor error payloads into public GitHub issues or ChatGPT.

If the owner also has verified vendor API retention/storage rights, only then consider the *separately owner-gated* `mst-private-source-chunks-manual.yml` with `CHUNK_ONLY` default. Never set storage-rights variables to `true` simply to make checks pass. The user permitting Cache storage is not an external vendor data licence.

This preflight is **not a bypass** for independent SSI/DNSE terms, complete native M5/M15/M30/H1/D1 + derived H4/W1 first-known/close/adjustment evidence, private highwater repo/signer/public-key latest tip and atomic CAS, 16 source-locked B/S regions, OOS or release QA. 2026-11-22 remains conditional engineering RC; all 16 zones `UNVERIFIED/NO_TRADE`.
