# MST §244 — owner-private highwater GitHub Cloud GET-only probe

2026-11-20 ICT. **Read-only code import** from still-Draft PR #23. No private repository provisioned, no REST call to private repo executed and no GitHub Actions workflow or credential configured in this PR.

## Purpose

Reuses exact reviewed §203 source module `scripts/mst_highwater_owner_cloud_readonly_probe.py` and fictional unit QA `tests/test_mst_highwater_owner_cloud_readonly_probe.py`. The module can issue **GET only** to GitHub REST when an independent owner provides `MST_HIGHWATER_READ_TOKEN`, `MST_HIGHWATER_CUSTODY_REPO`, `MST_HIGHWATER_SERIES_ID` and mode (`repo-only` default or `inspect-ref`). On missing inputs it outputs fixed `NO_GO` codes without leaking repo names, token, branch SHA, raw response or private IDs.

- `repo-only` reads exact repo metadata and requires actually private, not public `ngluonghoa/MST`, with expected owner and non-archived status.
- `inspect-ref` is only for an **already owner-provisioned** `refs/heads/highwater/<series>`, reads the exact Git ref, effective branch rules, bounded ruleset inventory and active ruleset detail. Fail closed on missing ref, incomplete page, unparseable reply, unexpected shape or unknown branch control. Missing `bypass_actors` details are UNKNOWN, not proof of no bypass.
- HTTPS GET fixed `https://api.github.com`, redirects forbidden, 10-second timeout, bounded JSON and duplicate-key rejection. Error receipts sanitized.
- Audit/report flags `owner_key_or_tip_externally_authenticated=false`, `atomic_cas_proven=false`, `highwater_ref_write_authorized=false`, `production_cache_published=false`, `signals_eligible=false` remain FALSE regardless of success. No POST/PATCH/DELETE, Git ref updates, OAuth changes or source Cache writing.

## Owner-controlled prerequisites for real audit

1. Independently verify a suitable GitHub plan and ruleset policy for a **PRIVATE** highwater repo; never make market trust pins or private source metadata public to avoid billing.
2. Authorize a separate owner-controlled PRIVATE repository, not `ngluonghoa/MST`, with read-only access for an independent audit GitHub App/token scoped to Metadata/Contents read.
3. Keep signer public key, key epoch and externally anchored latest tip **outside** the mutable GitHub repo and MST writer's trust domain.
4. Run only `repo-only` before provisioning a ref; `inspect-ref` later only when the exact branch and effective ruleset already exist and can be read. Verify owner IAM/ruleset bypasses outside this probe; API visibility alone cannot certify append-only or CAS.
5. Never copy a private GitHub token into chat, public PR, Google Docs or CI log. This PR has no workflow dispatch and needs no sensitive GitHub secrets to pass CI.

GitHub REST `force=false` fast-forward is not a general independently signed CAS; administrative bypass and history rewinds require a distinct external monotone witness and signed checkpoint policy. The script is **NO-GO production evidence collection**, not a ledger. See prior `docs/MST_OWNER_PRIVATE_HIGHWATER_CLOUD_SETUP_AND_READONLY_PROBE_20261116.md` in broad Draft PR23 for the original review; importing it into main is not approval to merge that draft.

No source rights, SSI/DNSE hosted LIVE entitlement, venue closed candles, original 16 B/S zone predicates, complete 6TF/W1 history or OOS release gates were proven here. MST stays `UNVERIFIED/NO_TRADE`, 2026-11-22 remains conditional engineering RC.
