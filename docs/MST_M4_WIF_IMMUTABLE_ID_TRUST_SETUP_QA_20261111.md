# MST M4 P0 — Immutable GitHub ID / Google WIF Trust: Cloud Setup & QA

Date: 2026-11-11 (Asia/Ho_Chi_Minh). Scope: Draft PR #8 additive Cloud-only candidate security policy, NOT an applied Google Cloud IAM configuration.

## Actual immutable GitHub owner/repo identifiers

The GitHub repository metadata connector was queried directly for ngluonghoa/MST:
- GitHub repository ID: 1450356304.
- GitHub owner ID: 353049266.
- Full name: ngluonghoa/MST.
- Default branch: main.
- Proposed workflow ref: ngluonghoa/MST/.github/workflows/m4-drive-wif-metadata-only-manual.yml@refs/heads/main.

Google Cloud IAM documentation recommends immutable GitHub numeric IDs to limit renamed/reclaimed-name identity attacks. The GitHub workload OIDC provider is multi-tenant; trusting solely issuer URI, repository text name, or a broad pool principalSet is insufficient.

Primary sources:
- https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines
- https://docs.cloud.google.com/iam/docs/best-practices-for-using-workload-identity-federation
- https://docs.github.com/en/actions/reference/security/oidc
- https://github.com/google-github-actions/auth

## Minimal deny-by-default trust policy design

New scripts/m4_wif_immutable_trust_policy_lab.py produces this exact CANDIDATE Google STS WIF OIDC provider attribute condition:

    assertion.repository_id=='1450356304' &&
    assertion.repository_owner_id=='353049266' &&
    assertion.repository=='ngluonghoa/MST' &&
    assertion.repository_owner=='ngluonghoa' &&
    assertion.ref=='refs/heads/main' &&
    assertion.event_name=='workflow_dispatch' &&
    assertion.workflow_ref=='ngluonghoa/MST/.github/workflows/m4-drive-wif-metadata-only-manual.yml@refs/heads/main'

Identity attribute mapping (a static proposal, not installed):

    google.subject=assertion.sub
    attribute.repository_id=assertion.repository_id
    attribute.repository_owner_id=assertion.repository_owner_id
    attribute.workflow_ref=assertion.workflow_ref

OIDC issuer must be https://token.actions.githubusercontent.com . The default allowed audience must be the COMPLETE WIF provider resource name, not a client-selected broad audience. All condition claims require proper external signed issuer JWT verification at Google STS; script fixture claim comparisons do not perform cryptographic authentication.

A dedicated WIF pool, containing a single GitHub provider restricted by this condition, helps avoid another provider in a shared pool granting the same principalSet. Protect privilege to edit provider attribute mappings or disable provider condition, and enforce a short-lived service account impersonation path. Do not give blanket project Owner, Editor, Drive write, Google Workspace domain-wide delegation or broad IAM permissions.

## Cloud-only execution steps (future operator setup; NOT executed by ChatGPT)

The following commands are reference templates only. Values are **not available**, and NO GCP project, pool, provider or IAM binding has been created or altered. They must be carried out in a trusted authorized Cloud Shell or infrastructure pipeline after owners choose the GCP project and exact service account.

Inputs needed from Google Cloud: PROJECT_NUMBER (numeric, not project ID), dedicated WIF POOL_ID, PROVIDER_ID, SERVICE_ACCOUNT_EMAIL; approved permission to configure pool and account. Create dedicated WIF pool and GitHub provider using issuer above, exact attribute mapping and the full immutable ID + event/ref/workflow condition printed by the Python script. IAM service account policy should bind only:

    principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_ID/attribute.repository_id/1450356304

with roles/iam.workloadIdentityUser on the dedicated readonly service account, not on an entire Google project. The condition must also be verified on the provider to restrict source workflow. Attribute mapping and audience must be independently inspected after creation. Project number, provider ID and email MUST be genuine, not invented defaults.

Repo variables eventually required by the separate main-only workflow:
- MST_GCP_WIF_PROVIDER: projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_ID/providers/PROVIDER_ID.
- MST_GCP_DRIVE_SA_EMAIL: exact dedicated service account email.
- MST_PILOT_FOLDER_ID: ID of the existing owner-private FPT/D1 pilot folder.
- MST_PILOT_MANIFEST_ID: exact pilot Google Docs manifest ID.
- MST_PILOT_SOURCE_DOC_IDS_JSON: private source-document ID map with SSI, DNSE and VCBS keys.

Note: variables are just configuration inputs, not proof of the WIF condition or external authorization. No actual variables have been checked for existence with this ChatGPT GitHub connector; do not mark configured.

The Drive folder owner must grant viewer permission specifically to the verified service account IF allowed by the Drive sharing policy. Prior Drive metadata reported owner-only/non-shared. This report does not modify sharing. No request to make the folder public, share it to an unrelated account or expose source Doc IDs in public artifacts.

## Workflow deployment gate

m4-drive-wif-metadata-only-manual.yml is ONLY on Draft PR #8. GitHub workflow_dispatch will not run it from the protected repository until the workflow exists on the default branch. MST main is locked at 4048f91beaaa3410116d97e35896c8b688384e19. Do NOT merge all of PR #8 merely to test authentication, do NOT silently edit protected main, and do NOT set a scheduled pipeline.

When a separate owner-approved minimal code-only promotion is allowed, use the workflow's main-only manual dispatch once. Read only Google Drive API files.get metadata fields id,mimeType,parents,trashed for exact owner-private folder, manifest and three per-provider Docs. Require five matching objects; capture sanitized no-price, no-token receipt. Confirm service-account identity and Google STS grants from independent Google Cloud IAM audit evidence, not workflow green test alone.

A real successful Drive metadata preflight would still not grant SSI/DNSE/VCBS source authorization, long-term off-platform Cloud retention, guaranteed timestamp/adjustment semantics, authentic source revision first-known, independently protected CAS/anti-rollback, automatic refresh, production cache or trading.

## QA: new additive source and tests

- scripts/m4_wif_immutable_trust_policy_lab.py: deterministic exact CEL attribute-condition generator with immutable repo+owner IDs, workflow/ref/event restrictions, example principalSet validator, locally simulated claim matches/denials, and static audit of manual workflow permissions/events.
- tests/test_m4_wif_immutable_trust_policy_lab.py: 50 completely fabricated tests rejecting altered numeric IDs, names, forks, tags, PR, pull_request_target, schedule, wrong workflow/ref, missing or malformed claims, over-broad IAM principalSet formats, and unsafe workflow modifications.
- Existing .github/workflows/m2-a03-v2-manifest-full-policy-local-chain.yml executes only fake tests and exports temporary **synthetic no-go** receipt. No real OAuth JWT, project ID, source prices or Drive contents in GitHub CI.
- This report docs/MST_M4_WIF_IMMUTABLE_ID_TRUST_SETUP_QA_20261111.md.

Previous exact PR8 green checkpoint: d7d8fc1aacdb7415c6f9171ec2cac09774c51006, 47/47 GitHub Actions PASS, 681 cumulative targeted synthetic methods. Only after new exact final SHA verifies 50 new tests and all 47 Actions success can 681+50=731 focused tests be reported (not full repo count). Compare commits should affect exactly script/test/new doc/existing CI workflow; original source locked 63 V1 and eight opt-in V2 source modules and protected main remain byte-identical.

## Gating / acceptance

Current **confirmed**: GitHub numeric repo/owner IDs; safe draft policy design; prior private one-time Google Drive real FPT D1 60-row readback.

Current **NOT confirmed**: existence of any GCP project/pool/provider or WIF condition; exact IAM service-account workloadIdentityUser grant; GitHub Actions repo variables and permissions; Drive viewer ACL for that service account; a manual main workflow run; live GitHub Google Drive access; provider data/Cloud retention rights; production Cache. Therefore M3 https://github.com/ngluonghoa/MST/issues/9 and M4 https://github.com/ngluonghoa/MST/issues/10 remain OPEN, and production/live market ingestion/trading NO-GO.

PR: https://github.com/ngluonghoa/MST/pull/8
