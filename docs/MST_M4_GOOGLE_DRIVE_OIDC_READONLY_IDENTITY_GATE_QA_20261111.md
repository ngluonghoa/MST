# MST M4 P0 — GitHub OIDC / Google Workload Identity Federation Metadata-Only Preflight

Date: 2026-11-11. Status: additively implemented on Draft PR #8, synthetic tests only; live Cloud identity verification NOT executed. Production Cache and trading NO-GO.

## Actual prior private Drive checkpoint

One-time user-authorized ChatGPT MCP→private Google Drive capture, FPT D1, SSI/DNSE/VCBS, 20 closed sessions/source, 60 real rows, 2026-10-14 to 2026-11-10. User-private Drive folder: https://drive.google.com/drive/folders/1F7mXwDXJW8KPCNSjFeKJ-2egkiobMaqz . Private source manifest: https://docs.google.com/document/d/1Ni8VN9rW0gaE9_CV8uyyaYbC4Heorsuc7gW2RQqHB3g/edit . Separate private numeric QA: https://docs.google.com/document/d/1OgiH-WNJgOztGadpF431pNuhZpnwvB9Z3KCJhUF0qYA/edit .

Google Drive file metadata previously returned not-shared, owner-only folder. A separate GitHub-runner Google service account is NOT the same principal as the connected ChatGPT Google Drive user; merely knowing folder or Docs IDs cannot establish its access. No repo variables, GCP WIF pool/provider, role binding or service account entitlement has been independently validated. Do not share folder to unknown principals or print private Docs contents to public GitHub logs.

## What this checkpoint adds

1. scripts/m4_drive_oidc_readonly_preflight.py: closed allowlist of ONE target private folder, ONE manifest and THREE exact per-source Google Docs. Uses Google Drive v3 files.get with fields=id,mimeType,parents,trashed and supportsAllDrives=true only. Never calls files.list, Docs body read, market API or Drive write. Enforces all objects non-trashed, three source docs and manifest have exact folder parent and Docs MIME, folder has folder MIME. Sanitizes HTTP/JSON errors so token/error bodies never enter workflow logs. All report fields omit IDs, source prices, JWTs, private URLs, headers or contents. Fail-closed if any object inaccessible, out of scope or invalid.
2. tests/test_m4_drive_oidc_readonly_preflight.py: 48 synthetic unit tests, using completely fictional folder IDs and fake responses, verify main-only event/repository branch, no PR secret execution, source membership and parent, no cross-provider substitution, no body-download or write flags, no authorization self-grant, error redaction, and exact metadata-only URL/fields. No real Google API or private quote values in GitHub CI.
3. .github/workflows/m2-a03-v2-manifest-full-policy-local-chain.yml: extends Draft PR #8's existing unprivileged read-only GitHub Actions testing with the 48 fake tests and a temporary synthetic NO-GO JSON receipt. No secret, OIDC id-token permission or user private Google Drive requests on pull_request.
4. .github/workflows/m4-drive-wif-metadata-only-manual.yml: a SEPARATE proposed manual main-only workflow. Requires GITHUB_REPOSITORY ngluonghoa/MST, github.ref refs/heads/main, workflow_dispatch, then an exact Google Workload Identity Federation configured provider + service account from GitHub Actions repository variables. Acquires Google credentials using google-github-actions/auth@v2 and github id-token:write solely in that main-only manual workflow. Python uses default Google WIF credentials with Drive METADATA.READONLY scope to verify five exact objects. No long-lived service-account JSON key is stored in code or requested for this design. No market data, no Google Docs contents, no data writes, no production Cache.
5. docs/MST_M4_GOOGLE_DRIVE_OIDC_READONLY_IDENTITY_GATE_QA_20261111.md (this report).

## Runtime configuration required for an actual **future** manual execution

This PR workflow file exists only on Draft PR #8, NOT protected main. Official GitHub Actions workflow_dispatch requires the workflow to exist on the default branch; therefore a real OIDC job cannot be executed from this branch alone. DO NOT merge PR8, change main or turn on a schedule without separately completing source parity/production governance and approval.

For an eventual controlled operator review, the separate GitHub workflow reads GitHub Actions repository variables (never quotes): MST_GCP_WIF_PROVIDER, MST_GCP_DRIVE_SA_EMAIL, MST_PILOT_FOLDER_ID, MST_PILOT_MANIFEST_ID, and MST_PILOT_SOURCE_DOC_IDS_JSON containing SSI,DNSE,VCBS document IDs. These variables are NOT declared configured/validated. Google-side trusted workload identity provider must bind exact GitHub repo, branch and workflow claims to a least-privilege viewer service account; the private Drive owner must permit THAT exact principal to view ONLY intended private folder/documents. The repo workflow must then be available on main and independently dispatched as a read-only test. This report does not claim any of those configuration or authentication steps have happened.

## Test and acceptance boundary

Previous accepted Draft PR #8 HEAD aca26ac20bb1b247fae2bdcfd01c0cac1e28a669: 47/47 GitHub PR workflows SUCCESS and 633 focused synthetic fixture test methods. Expected new count: 633+48=681 focused tests only IF the exact final HEAD and all 47 PR workflows successfully finish (not full repo test count). Verify exactly these five files changed from previous accepted HEAD (script, tests, two YAML workflow paths, this report), none of the original locked 63 V1 or eight pre-existing opt-in V2 source modules and protected main at 4048f91beaaa3410116d97e35896c8b688384e19 touched. Swing upstream source pin cd90c1babae8912db31490ad614fc2ad2f868042.

## Explicit production and licensing NO-GO

- Genuine GitHub Actions→Google WIF service account authentication and actual Drive files.get **not yet demonstrated**. Private Drive snapshot read/write through ChatGPT is demonstrated separately and does NOT imply GitHub runner entitlement.
- Google Drive readonly identity access, if eventually shown, would NOT authorize SSI/DNSE/VCBS vendor market-data transport, source licensed cloud retention, index/stock calendar first-known histories, or numerical source normalization. Published SSI FastConnect restrictions remain open.
- All production ABI ownership, independent signer and monotonic rollback floor, authenticated multiple-writer CAS, Cloud quote cache ingest/scheduled refresh, M5/M15/M30/H1/H4 real candle support, signals and trading are blocked.

M3 license/provider Issue: https://github.com/ngluonghoa/MST/issues/9
M4 Cloud Cache custody Issue: https://github.com/ngluonghoa/MST/issues/10
Draft PR: https://github.com/ngluonghoa/MST/pull/8

References: GitHub official workflow_dispatch default-branch behavior https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows ; Google Drive Python readonly scopes https://developers.google.com/workspace/drive/api/quickstart/python .
