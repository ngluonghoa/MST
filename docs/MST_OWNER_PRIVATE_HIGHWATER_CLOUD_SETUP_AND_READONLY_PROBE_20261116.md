# MST §203 — Owner-private highwater custody: Cloud-only setup & actual GET-only preflight

**Status:** DRAFT RUNBOOK / NO PROVISIONING / NO WRITES / NO-GO PRODUCTION  
**Scope:** Separate owner-controlled PRIVATE GitHub repository and authenticated read-only evidence for a prospective external highwater. This is **not** an approval to merge MST PR #23, write a ref, change IAM, activate a publisher, fetch licensed vendor data from GitHub Actions, schedule tasks or trade.

## 1. Verified current state — 2026-11-16 ICT

- Connected GitHub account `ngluonghoa` owner repository inventory and the accessible GitHub App installation's repository list both show the same seven **PUBLIC** repos: `swing-trading-1-8`, `forex-trading-1-0`, `MOCHIVNST`, `MOCHIFX`, `MST`, `MFX`, `ngluonghoa.github.io`. No separate private highwater repository is visible **within current connected access**. This does not establish global non-existence elsewhere.
- MST is **public** with default `main`. Development remains on Draft PR #23 `mst/cache-v21-real-staging-fakejson-manual-20261111`; protected `main` remains unchanged.
- GitHub's documentation states that **private-repository branch rulesets require GitHub Pro, Team or Enterprise**. Public rulesets on Free are not equivalent; do not create a PUBLIC highwater repository or publish private source pins merely to work around plan limitations. Verify actual owner's GitHub plan before provisioning. https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets
- GitHub REST `GET /repos/{owner}/{repo}/rulesets/{id}` can **omit** `bypass_actors` unless the caller can edit the ruleset. An omitted field is **UNKNOWN**, not an empty bypass list. https://docs.github.com/en/rest/repos/rules
- Existing owner permission to collect and retain real private connected-MCP research Cache is already granted; it must not be asked again. It does **not** establish license/retention entitlements for direct GitHub Actions-origin SSI/DNSE/VCBS APIs.

## 2. Owner setup checklist — requires separate owner action and authorization

1. Confirm a plan with enforceable rulesets on **private** GitHub repositories (GitHub Pro/Team/Enterprise; do not assume the account's plan).
2. Choose/create a **separate PRIVATE** repo under independently controlled owner custody, with no real OHLCV/source data, keys or production highwater initially. Do not repurpose public `ngluonghoa/MST` or any other public source repo. Existing ChatGPT GitHub App access must be explicitly scoped/connected if later used for review.
3. Create a GitHub **read-only audit credential** scoped to this one repo: **Metadata read** for repository/rulesets and **Contents read** for Git ref. Do not give this audit credential Administration or write permissions. Prefer an owner-controlled GitHub App installation token; it is short-lived and scoped to installed repos/permissions, never save the token in docs or public GitHub. https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation
4. Separately define a **future write principal** (not the read-only auditor, not the PR automation token). Only after further authorization: separate GitHub App, minimal **Contents write** on that sole private repo, no Administration, secret rotation/revocation plan and auditable permission changes. `GITHUB_TOKEN` from the public MST repository is not a substitute for private-repo authorization.
5. On the prospective `refs/heads/highwater/<SERIES_ID>`, review an active **branch** ruleset. For initial isolated proof, exact branch inclusion with no exclusions; effective rules include `deletion`, `non_fast_forward`, `required_linear_history`. Check every overlapping ruleset and actual bypass/admin paths. Branch rulesets are mutable by privileged owners: they do **not** create an immutable external ledger.
6. Confirm whether a rule prevents any normal nonforced successor update; do not make the only permitted future writer depend on an unrestricted bypass. The owner must review a legal, actually executable rule/permission configuration and rollback/recovery policy.
7. Keep **independent owner signer public-key fingerprints, key epochs, latest ref and signed checkpoint tip** outside the development PR, runtime write credentials and proposed private repo's mutable trust domain. An external durable, monotone witness remains a separate backend choice; no GitHub rule can independently guarantee it.
8. Do **not** create the first highwater branch/ref or perform a sibling-writer race in production as part of this read-only procedure. Such mutations require independent owner authorization for an isolated sandbox only.

## 3. Safe Cloud read-only probe — code already in Draft PR #23

File: `scripts/mst_highwater_owner_cloud_readonly_probe.py`.

**Not wired to GitHub Actions, not scheduled and not executed against any private repo.** It requires explicit environment inputs in an owner-controlled Cloud job, with a GitHub App installation token supplied privately (not on a command line, in PR logs, screenshots or Google Docs).

- `MST_HIGHWATER_CUSTODY_REPO` — `OWNER/PRIVATE-REPO` of the separate private repo, never `ngluonghoa/MST`.
- `MST_HIGHWATER_SERIES_ID` — allowlisted symbol/series, 8–80 letters/digits/`_`/`-`.
- `MST_HIGHWATER_PROBE_MODE` — `repo-only` for initial private metadata check; `inspect-ref` **only after** a specific highwater branch is already provisioned by separately authorized owner action.
- `MST_HIGHWATER_READ_TOKEN` — short-lived, repository-restricted audit credential held by the owner Cloud secret store. Never paste into the repository or assistant conversation.

Launch in an authorized Cloud runtime via `python -m scripts.mst_highwater_owner_cloud_readonly_probe` after securely providing those variables. Importing the file alone does **not** send traffic. The process uses **GET only**, fixed `https://api.github.com`, no redirect, one timeout-bound response per request, bounded bytes, sanitized error codes, no private URLs/SHAs/secrets in stdout.

`repo-only`: GET repo metadata and validate that it is actually private and not the MST source repo. No branch creation or ref write.

`inspect-ref`: additionally GET the exact existing Git head, active effective branch rules, first page of repository rulesets (up to 100; fail on boundary ambiguity), and active ruleset details (max 16). Missing/hidden bypass data is surfaced as incomplete observability. All resulting claims about trusted owner roots, actual authority, durable monotonicity, atomic CAS, approved storage and trading remain **FALSE**.

Required REST permissions: `Metadata: read` for branch rules/rulesets; `Contents: read` for Git references. Links: https://docs.github.com/en/rest/repos/rules and https://docs.github.com/en/rest/git/refs .

### Failure handling

If the repository does not exist or the audit app lacks rights, API may return 404; the probe fails with sanitized `MST_203_HTTP_READ_FAILED`. **Do not** respond by enabling public visibility or changing permission scopes broadly. Obtain exact owner access approval separately.

If rulesets are unavailable on the owner's current GitHub plan, stop and resolve plan/provider architecture before any private source highwater work. A **PASS** of structural ruleset readback is still only inventory, **never** a production release gate.

The read-only observer cannot verify whether privileged administrators can bypass/disable those controls. Owner must independently review GitHub Settings → Rules → Rulesets (effective enforcement and bypass privileges), preserve sanitized audit evidence privately, and attest revocation/rotation independently. Do not grant ruleset write access solely to expose bypass metadata in this probe.

## 4. Release decisions / gates

**READY FOR AUDIT READ** only after repo owner and plan verified, a separate private repo visible to the authorized audit principal, Metadata/Contents read credentials active, no token leakage, no mutating probe, and the owner confirms acceptable cost/security. This still does **not** imply permission to create/ref-update.

**READY FOR SYNTHETIC REMOTE REF TEST** requires distinct explicit owner sandbox authorization, branch/ruleset/IAM and bypass readback, independent trust witness and rollback/revoke procedure; only fake data, separate private repo, no production reference.

**PRODUCTION NO-GO** until independently anchored signer/monotone latest tip, genuinely verified atomic ref succession and full readback, license-authorized GitHub-origin SSI/DNSE/VCBS → private Google Drive app-owned CHUNKS, source finality/first-known/raw-adjusted corporate action evidence, executable original B1–B8/S1–S8 parity, UI1.0 Step08/browser goldens, backtesting and G01–G08 release gates. No main merge or scheduler/trade approval inferred.

## 5. Architecture risk notes

GitHub API's `force=false` is a **nonforced fast-forward** condition, not a general compare-and-swap against an independently supplied expected old SHA, and it does not prevent a privileged repository administrator from rewinding or changing rules. A same-parent competing writer is blocked **only while** both alternatives remain siblings of the same old head and provider rules are actually enforced. A privileged force/reset or disabled rule can invalidate that guarantee. https://docs.github.com/en/rest/git/refs

The owner trust root must be outside both public MST PR and the GitHub write principal. Repo rulesets are one defense, not an immutable ledger.

## 6. Next step

§204 once owner infrastructure or vendor source permissions are available: use the opt-in Cloud probe with a short-lived, constrained read token, independently review owner rule/pin evidence, and record actual authenticated provider readbacks in private QA. If no new owner-access evidence exists, prioritize real vendor-origin data entitlement/source transport rather than accumulating self-signed mock attestations. Never auto-enable any existing workflow. 
