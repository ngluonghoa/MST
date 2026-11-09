# MST M4 — machine-readable owner acceptance dossier, strictly non-authorizing

**QA ID:** MST-M4-OWNER-EVIDENCE-001 · **Date:** 2026-11-09 Asia/Ho_Chi_Minh  
**Disposition:** **PASS: OWNER_DECISION_PACKET_ONLY_PRODUCTION_BLOCKED.** This is a usable owner-review dossier, NOT a signer enrollment, verified floor, authorized cache reader, actual Drive publisher or production release.

## 1. Source lock and bounded scope

- Swing Trading source pin `cd90c1babae8912db31490ad614fc2ad2f868042`; MST protected `main@4048f91beaaa3410116d97e35896c8b688384e19`, tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`.
- All 63 original inherited v1 source modules, previously existing V2 modules, `pyproject.toml`, main rulesets and proposed but unprovisioned M4 witness ref remain unchanged. Work only on [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8), no merge.
- New `scripts/m4_owner_gate_dossier.py` and `tests/test_m4_owner_gate_dossier.py` (26 tests); scoped update to `.github/workflows/m4-reader-readiness-block-gate.yml` to save the existing real GitHub REST read-only readiness JSON plus generated review-only dossier as GitHub Actions artifact.
- No credential/key generation, signer enrollment, actual vendor data/entitlement, real Google Drive market cache writes, local/Mac/MOCHI execution, protected branch policy edit, authorized publisher or broker trade.

## 2. Evidence taxonomy and validator

The dossier constructor consumes ONLY `mst.m4.reader-readiness.blocking-audit.v1` with exact `M4_READER_AND_PUBLISHER_BLOCKED_PENDING_EXTERNAL_OWNER_GATES`, pinned main source SHA, expected witness name `refs/heads/mst/m4-witness/v1`, all eight SIGNED gates open and all production rights explicitly **false**. It rejects malformed/missing boolean GitHub fields, false claimed witness-ref SHA, inconsistent ruleset scope, changed main HEAD, maliciously asserted owner approval, source rights, external monotonic floor, distributed CAS or cache/trading access.

All proposed output gates have `OPEN_OWNER_EVIDENCE_REQUIRED` and `externally_attested=false`. The checksum of the raw audit JSON is explicitly named `readiness_audit_sha256_untrusted`: it is NOT an independent signature, owner approval, immutable witness or durable floor.

The review package includes per-gate independent evidence required:

1. **G01** owner-approved authenticated signer root, identity/role/provenance and key enrollment.
2. **G02** externally durable, protected per-provider+partition+rights monotonic registry and signed receipt floor, including cross-run/crash/no-rollback checks.
3. **G03** two independently authenticated publishers attempting a single GitHub/witness head, exactly one wins under server atomic CAS; loser recovery.
4. **G04** SSI/DNSE/VCBS licensed source entitlement, first-known revisions/corrections/tombstones and legal Google Drive retention.
5. **G05** real immutable Google Drive object bytes/SHA, protected Git commit/tree/ref readback and injected two-service crash recovery.
6. **G06** globally enforced signer/key-epoch and vendor-right revocation, across separately authenticated accounts and readers.
7. **G07** independently verifiable provenance and trust tiers with no self-attested promotions.
8. **G08** owner final per-module A02 dispositions (63), A03 ABI compatibility, M3/M4/M8 signoff before release.

**No Gxx is marked closed by this checkpoint.** All evidence requests remain external-owner-gated.

## 3. Real GitHub-hosted execution evidence

Code + workflow HEAD `2bd3ad4cf0e972f85ca110c5410653989ebbdb79`:

- [Read-only owner-gate CI #42611931503](https://github.com/ngluonghoa/MST/actions/runs/42611931503) **SUCCESS**, produced `OWNER_DECISION_PACKET_ONLY_PRODUCTION_BLOCKED`, `owner_gates_open=8`, `readiness_checksum_untrusted=8ffe6266ed2a299e84762f1fef2080f6559324171b51e99c8eda66ac4c5d7912`. Both `cache_read_authorized` and `trading_authorized` remained FALSE. The runner uploaded [GitHub artifact 13670049798](https://github.com/ngluonghoa/MST/actions/runs/42611931503/artifacts/13670049798), name `mst-m4-owner-gates-blocked-only`, containing `m4-readiness-unattested.json` and `m4-owner-gate-dossier-unattested.json`. Artifact retention 14 days; it is NOT immutable durable custody.
- [Foundation CI #42611931450](https://github.com/ngluonghoa/MST/actions/runs/42611931450) **SUCCESS 3/3**, Python3.11 **1768/1768**, Python3.12 **1768/1768**, engineering contracts **63/63**, H2 63-module boundary audit/H3 exact matrix, lint and wheel build/install PASS.
- [Read-only GitHub remote ref audit #42611931463](https://github.com/ngluonghoa/MST/actions/runs/42611931463), [untrusted cross-run registry cache #42611931547](https://github.com/ngluonghoa/MST/actions/runs/42611931547), and [untrusted cross-run journal #42611931487](https://github.com/ngluonghoa/MST/actions/runs/42611931487) all SUCCESS.
- Exact final documentation-containing HEAD must have its OWN workflow result checked before representing it as green.

## 4. Negative cases and known limits

The 26 new tests cover fixed eight-gate taxonomy; deterministic checksum for identical read-only input; different audit state changes checksum without changing rights; hypothetical witness and apparently matching ruleset still not owner authority; forged production-ready status; fake owner/root/floor/CAS/source/Drive/trading claims; dropped/reordered gates; moved source SHA; incorrect witness ref name or SHA/presence; impossible ruleset metadata; malformed boolean flags, candidate HEAD, run IDs; untyped input; and strict failure for absent required flags.

A real GitHub 404 for `mst/m4-witness/v1` remains a blocked preflight. If that ref appears later, the dossier will remain **blocked** until separate owner-approved trust-root, protected floor, rights, physical Drive and multi-principal verification are established outside this review-only protocol. **No code in this change promotes the dossier to a production receipt.**

## 5. Owner decisions / dependency path

A suggested *review sequence*, not an authorization: establish owner-approved key and rights-governance authority **G01/G04**, design protected external floors **G02**, demonstrate distinct-writer CAS and global revoke **G03/G06**, verify real Drive/GitHub crash recovery **G05**, then independently certify trust tiers **G07** and close source parity/ABI/M3/M4/M8 release governance **G08**.

Open issues: [#16 signer and signed floor](https://github.com/ngluonghoa/MST/issues/16), [#15 protected witness ruleset](https://github.com/ngluonghoa/MST/issues/15), [#13 multiwriter](https://github.com/ngluonghoa/MST/issues/13), [#14 cross-service read barrier](https://github.com/ngluonghoa/MST/issues/14), [#10 real Google Drive cache](https://github.com/ngluonghoa/MST/issues/10), [#9 vendor rights](https://github.com/ngluonghoa/MST/issues/9), [#4 owner A02 dispositions](https://github.com/ngluonghoa/MST/issues/4), [#6 owner A03 ABI](https://github.com/ngluonghoa/MST/issues/6). Keep PR #8 Draft/unmerged and M5/M8 release/trading BLOCKED.

**Next source-safe work:** review G01/G02 independent root and monotonic store architecture as an owner decision record, not synthetic CI success; require explicit approval before provisioning a witness, signer or vendor transport.
