# MST §246 — signed highwater CAS INTENT, prepare-only and re-read only

2026-11-20 ICT. Isolated draft §197 algorithm adapted to the source-pin verifier already protected on main in §245. **NO remote updates, no signing key, no GitHub ref writes, no independent trust authorization, no Cache publication or trade.**

## What works offline

- Given an already verified full signed Ed25519 checkpoint chain, an externally *supplied* anchor with series/generation/tip/CHUNK head/revision, and the next signed checkpoint, the module `scripts/mst_highwater_cas_intent.py` rechecks all signatures, exact source scope and chain links before preparing a deterministic SHA256-bound **conditional-write intent**.
- An intent binds exact expected old generation/revision/CHUNK pin and signed tip to proposed generation +1, revision +1 and proposed signed CHUNK pin. It declares `external_atomic_cas_required=true`, `published=false`, `signals_eligible=false`. No actual CAS is executed.
- `verify_pre_submit_snapshot` recomputes the original pinned intent digest and compares a **second caller-supplied** anchor snapshot to reject stale/changed generation, revision, source head or tip.
- The private intent includes source CHUNK IDs and digests. **Never write intent/anchor/source records to public GitHub Actions logs**. The re-read report is only diagnostic, with `external_store_atomic_cas_executed=false` and `owner_trust_anchor_verified=false` even after valid signatures.

## Why still NO-GO for production

A caller can supply the same stale snapshot to two competing writers. A pre-submit read is **not an atomic compare-and-swap** and cannot stop races without a separate atomic storage operation and independent pin control. Owner private repository, effective rulesets, signer identity, key epoch, expected latest tip, actual CAS write principal and genuine forced/fast-forward fencing remain unproven. A GitHub `force=false` fast-forward alone is not authenticated independent durable monotonicity.

No live SSI/DNSE retention-rights read, Google Drive CHUNKS/MANIFESTS promotion, H4/W1 authoritative venue closure, original 16 source-locked detector predicates, OOS or UI Step08 is demonstrated. Continue UNVERIFIED/NO_TRADE and conditional 2026-11-22 engineering RC.

## QA

`tests/test_mst_highwater_cas_intent.py` builds ephemeral **fictional** signed checkpoints using the §245 test helper; tests exact initial prepare, reread, stale old tip, changed anchor, wrong signed proposal, signed run replay, invalid generations/revisions/fields, invalid request ID, altered intent despite resealing and two competing fake writers observing the same stale snapshot. CI uses Python 3.11/3.12 cryptography already declared as the custody extra. No network or private secrets.

Later separate owner-authorized development may add private remote Git branch fast-forward proposal/readback and sandbox race testing, but **must not** merge broad Draft PR23 or claim this module executes CAS.
