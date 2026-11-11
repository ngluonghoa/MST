# MST M4 — Real private 180-row D1 source audit, dual-schema metadata drift, no silent unit alias resolution

Date: 2026-11-11 Asia/Ho_Chi_Minh. Status: **real owner-private Google Drive read-only observation plus separately synthetic-only GitHub source adapter**. This is neither GitHub Actions authenticated real Drive reading nor approved production Cache. Master Handoff §120 and current canonical Spec/Gap read before this work. Six locked MST market frames remain M5/M15/M30/H1/H4/D1.

## Real Cloud source audit — 9 private Google Docs, 2 native manifest Docs

Using the currently user-connected **Google Drive/Docs cloud connector** (not a GitHub Actions service account), independently read ALL nine pre-existing real D1 source-partition documents and BOTH corresponding manifest documents. Each document contains one text heading line then JSON; it is not a bare JSON-only Google Docs body. The FPT triplet and DCM/HPG sextet use *different physical snapshot, manifest and governance field schemas*. The old public `m4_v21_private_pilot_d1_validation_lab.py` only accepts the initial FPT JSON shape and uses an outdated governance-key set compared with the actual private pilot; passing its synthetic tests is not proof it validated real Docs. There is a genuine compatibility gap.

Read-only, transient, in-cloud observation:
- Three symbols FPT/DCM/HPG, three providers SSI/DNSE/VCBS, 20 source D1 session rows each, dates 2026-10-14..2026-11-10. 180/180 rows passed numeric finite/Open-High-Low-Close envelope/volume and chronological distinct ISO-date checks in the independent cloud orchestration audit. All 60 source-day triples (20 common dates per symbol) present. All nine snapshots have their declared scope, source row counts and exact private file identifiers represented in manifests. Google Drive metadata confirmed **9/9 unshared private** and **9/9 have only their correct parent private folder**.
- SSI vs VCBS native observed OHLC: 0 mismatched dates in the three 20-session samples; native three-way share volume: 0 mismatched dates; SSI vs DNSE **hypothetical comparison only** using ×1000: 0 mismatched OHLC dates. None authenticates DNSE source unit, adjustment basis or entitlement to perform conversion in trading/cache.
- The two manifests contain **three exact DNSE price-unit label discrepancies**, one per instrument; all other inspected basis/date/count/last-close representations aligned. These are **unit provenance metadata conflicts**, not a detected numerical quote difference. They must not be silently normalized into a canonical price unit.

| Symbol | Provider | Snapshot's native price-unit metadata | Manifest's price-unit metadata | Disposition |
|---|---|---|---|---|
| FPT | DNSE | `source_native_DNSE_units_unverified` | `source_native_units_unverified` | Explicit unresolved alias; quarantine |
| DCM | DNSE | `source_native_scale_unverified` | `native_scale_unverified` | Explicit unresolved alias; quarantine |
| HPG | DNSE | `source_native_scale_unverified` | `native_scale_unverified` | Explicit unresolved alias; quarantine |

Additional strict historical schema differences:
- FPT pilot snapshots `mst.chatgpt_mcp_source_snapshot.quarantine.v0.1`, three physical rows/docs plus FPT single-symbol manifest `mst.chatgpt_mcp_private_drive_cache_manifest.v0.1`; named source unit/basis inside nested `scope`, governance keys in original seven-key set, VCBS per-row `provisional=false`.
- DCM/HPG snapshots `mst.private_chatgpt_mcp_multi_symbol_daily_snapshot.v0.1` and multi-symbol manifest `mst.private_connected_mcp_multiple_symbols_daily_manifest.v0.1`; top-level provider/symbol/basis/unit with DIFFERENT eight-key governance set; VCBS `provisional_source_flag=null` means unknown issuer provenance and MUST NOT be treated as `provisional=false`. The batch's VCBS per-day `adjFactor` is per-row, never a global corporate-action rescale.
- FPT and DCM/HPG SSI rows preserve **source-native numeric strings**; DNSE keeps its own native numeric scale with `source_unix_time` field and unapproved basis; VCBS adjusted price unit VND, matched-volume flags and raw close remain separate. No direct cross-provider numeric conversion is approved.
- Both file kinds carry all governance deny flags=false. The initial pilot manifest additionally records `user_directed_one_time_capture=true`—permission for THAT one-time readback, not permission for a scheduled licensed publisher.

## Public Draft PR8 additive compatibility/audit code — NO real market rows

New `scripts/m4_private_d1_dual_schema_manifest_quarantine_lab.py` has a **strict bounded one-heading-or-JSON parser**, explicit schema-specific scope/row/governance requirements, exact manifest identity/date/row/count/last close consistency checks, and an opt-in **known unverified DNSE token discrepancy observer**. It reports only symbolic status, counts, which metadata fields conflict and aggregate source parity counts. It preserves every original source unit label; any unknown alias, self-granted rights, unexpected schema or inconsistent raw OHLC is denied. The exact three known DNSE aliases remain **QUARANTINED** and never become authorized for production Cache or trades. No code reaches Google Drive, provider accounts, GitHub secrets, network, production source adapters or automatic publisher.

`tests/test_m4_private_d1_dual_schema_manifest_quarantine_lab.py` includes wholly fabricated three-symbol × three-provider × 20-row fixture groups, two fake manifests, and 50 negative/positive tests exercising the discovered real shape mismatch and safety constraints. The existing unprivileged `.github/workflows/m2-a03-v2-manifest-full-policy-local-chain.yml` is the only workflow touched; its tests and sanitized synthetic receipt are no substitute for actual Google Drive runner entitlement.

**Critical evidence distinction:** 180 REAL source rows were read and numerically audited by the current authenticated user-connected cloud tools in this turn, in private memory. The new public Python lab CI runs only fabricated source data; it did **not** itself ingest those nine real Docs via GitHub Actions. No source numeric quote arrays or source hashes that could reconstruct private quote data enter public GitHub. No existing private original snapshot/manifest has been mutated.

## Remaining work / release NO-GO

1. Source-of-truth correction for the **three DNSE manifest-vs-snapshot unit labels** must be explicitly adjudicated and versioned before using any derived data in actual indicators or cross-provider Cache. Do not edit the original evidence in place.
2. A real scoped GitHub Actions OIDC/WIF→Google Drive service account must independently read exact private doc IDs and execute the same schema validation in Cloud on source data **after** a rights/retention review. The current connected ChatGPT tools are not transferable identities.
3. Licensed source rights, source-native DNSE unit+basis issuer proof, native SSI/DNSE minute closed bars, VCBS intraday point-only gap, official VN trading calendar, independent publisher-first-known/corrections and signed anti-rollback/CAS floor remain OPEN. No PR merge, automatic production Cache/refresh or trades.

Preceding exact green Draft PR8 head `f0d98e44a04ef04179be653791e81a02df40f272` was 47/47 GitHub Actions PASS, 881 cumulative focused fake tests. Credit new tests and update head only after independently verifying new CI.
