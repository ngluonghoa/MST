# MST §245 — Ed25519 signed highwater checkpoint candidate chain, READ ONLY

2026-11-20 ICT. Isolated engineering code, independent from broad Draft PR23 §196 source-chain stack. **Does not sign, publish, execute Git CAS or authenticate signer ownership**.

## Scope

`scripts/mst_signed_highwater_diagnostic.py` validates a bounded 1–128-record proposed genesis→tip Ed25519 checkpoint chain with exact source-locked §196 checkpoint schema and six-field source CHUNK pin. Only SSI or DNSE are in this subset; VCBS remains separate source qualification. Native M5/M15/M30/H1/D1 only; H4/W1 are not native.

Every checkpoint contains: exact project repository and series, increasing sequence, previous checkpoint SHA256 and exact previous head pin, new source pin with provider/symbol/native_tf/file_id/run_id/content digest; **all source-finality, publisher-CAS, licensed-retention and signal/trade flags are FALSE**. This verifier refuses malformed/wrong key IDs, noncanonical base64 signature, invalid field sets, unauthorized provider/TF, malformed file IDs, wrong public key, tampered signed body, signature mismatch, missing/reordered link, changed series/TF/provider, non-increasing GitHub run ID, duplicate file ID, unchanged source hash or supplied tip mismatch.

The full body is signed as sorted compact canonical JSON using Ed25519. The complete envelope SHA256 includes the signature. A public report exposes only counts, provider/native TF and false-authority flags, never private chunk IDs/hash, signer key bytes, signatures, OAuth or source values.

Tests use ephemeral fictional Ed25519PrivateKey generated in CI only, `cryptography>=43,<50` already installed by `.[custody]`; no private key is committed, logged or read from a Cloud secret.

## Critical limitations

A user-supplied public key plus a matching user-supplied digest from the **same mutable GitHub/Drive writer** proves nothing about authentic owner custody: anyone can sign their own chain. Real approval requires independent owner-managed public-key fingerprint and epoch plus **out-of-band anchored monotone latest tip**, authenticated private repo/ref/ruleset, uncontested CAS update/write principal, atomic succession and post-write two independent reads. The GET-only §244 highwater private repo probe can collect metadata evidence but does not create that authority.

This module does not validate real Google Drive CHUNKS/MANIFESTS against every checkpoint, does not authorize vendor SSI/DNSE storage, and does not turn provider intraday bars into first-known venue-closed, corporate-action-adjusted source truth. It deliberately does NOT import the broad Draft PR23's private chain/manifest code or enable any signer/remote ref write.

## Release boundary

All 16 B/S zones remain UNVERIFIED/NO_TRADE, native 6TF+W1 source and Step08 UI/OOS incomplete, 2026-11-22 engineering RC target conditional only. Next scoped P0-C: independently authenticated public key/tip and private GitHub ref audit plus a **prepare-only** signed CAS intent check, followed by owner-authorized sandbox race tests before any production publisher.
