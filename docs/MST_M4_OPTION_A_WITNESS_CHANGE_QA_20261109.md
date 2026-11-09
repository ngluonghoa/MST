# MST M4 — Option A exact witness owner-change packet / no-apply QA

**QA:** MST-M4-OPTION-A-WITNESS-CHANGE-001 · **Date:** 2026-11-09 (Asia/Ho_Chi_Minh)  
**VERDICT:** **PROPOSED CHANGE PACKET + NO-ACTION CONTRACT TESTS PASS**; G01/G02/G03/G05 infrastructure admission **NOT VERIFIED**. Nothing provisioned, configured or released.

## 1. Source-locked scope and actual user selection

User-selected **Option A = GitHub + Google Drive only**, no additional Cloud KMS/Firestore/third-party storage and no Mac/MOCHI/local project execution. Original Swing Trading 1.8 pin `cd90c1babae8912db31490ad614fc2ad2f868042`; MST protected `main@4048f91beaaa3410116d97e35896c8b688384e19` tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`; 63 inherited V1 modules, existing candidate V2 and main GitHub rule untouched. All code/work executed on [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8), unmerged.

**Current real remote evidence from preceding QA:** main GitHub active ruleset `MST - Protect Main` #26801439, default-branch target, PR required + 3 CI checks but **required approving reviews=0**, strict CI freshness=false and no `required_signatures` rule; M4 proposed witness ref HTTP404 absent; main classic protection endpoint 403 to integration; PR CI bypass list not visible, separate connector token saw empty list. Google Drive metadata for 5 project folders showed one visible owner role per folder and `shared=false`; not independently authenticated custody or real licensed market bytes.

## 2. New reviewed change artifacts

- `docs/MST_M4_OPTION_A_WITNESS_OWNER_CHANGE_PACKET_20261109.json` (schema `mst.m4.option-a.witness-change-packet.unapproved.v1`) pins exact proposed ref `refs/heads/mst/m4-witness/v1`, original/main source and rule ID. It details **8 owner review decisions C01..C08 OPEN**, **10 ordered operations S00..S09 NOT_EXECUTED**, **8 of the later operations require independent owner approval**, proposed rules `deletion`, `non_fast_forward`, `required_signatures`, no bypass actor, and explicit writer-lockout caveat for `creation`/`update`.
- `docs/MST_M4_OPTION_A_WITNESS_OWNER_CHANGE_PLAN_20261109.md` gives the concrete proposed GitHub ref/ruleset change, exact controls, account/root-administrator separation, genesis-before-enforcement, readback, two-writer CAS, physical licensed Drive bytes, quarantine and owner recovery. It does NOT claim GitHub ruleset alone prevents privileged owner/admin policy changes.
- `scripts/m4_option_a_witness_change_preflight.py` joins and validates **four already locked contracts**: Option A scope choice, prior exact witness ruleset proposal, prior 8-role/25-pair duty separation and new owner packet. The validator fails closed on changed main/ref/scope, unapproved bypass, introduced ref lockout rules, changed protected rules, missing owner decisions, fake owner signatures, step reordering/authorization, role drift and any claim of actual production activity.
- `tests/test_m4_option_a_witness_change_preflight.py`: **44 regression cases**, positive only for *unapproved*, negative for forged approval/secret, fallback to B, main protection edit, owner ref scope widening, missing signatures, reordering initial bootstrap, permission confusion, witness claimed provisioned, malformed rights and root-admin reset.
- `.github/workflows/m4-option-a-witness-change-review.yml`: same-repo PR #8 only, GitHub Actions `contents:read`, **no protected ref/ruleset API mutation**, no production keys, no vendor token or real Google Drive candle data. Outputs a temporary `NO-APPLY` review artifact.

## 3. Verified real hosted execution (code head)

**Source+workflow+runbook HEAD before report commit:** `ce8ea51de56edbd6e52ef1483c41520a1a1db457`.

- [Foundation CI #42628249668](https://github.com/ngluonghoa/MST/actions/runs/42628249668) **SUCCESS 3/3**: Python 3.11 **1956/1956**, Python 3.12 **1956/1956**, engineering contracts **63/63**, H2/H3 exact source-boundary, lint/wheel checks PASS.
- [Owner-change packet review #42628249892](https://github.com/ngluonghoa/MST/actions/runs/42628249892) **SUCCESS**, outputs `WITNESS_OWNER_CHANGE_PACKET_COMPLETE_NOT_APPROVED_NOT_EXECUTED` with `owner_approval_gates_open=8`, `change_steps_not_executed=10`, `privileged_change_steps_require_owner=8`, `witness_ref_provisioned=false`, `real_signer_enrolled=false`, `real_writer_credentials_provisioned=false`, `external_nonresettable_floor_verified=false`, `cache_read_authorized=false`, `cache_write_authorized=false`, `trading_authorized=false`.
- Temporary GitHub [artifact #13679451702](https://github.com/ngluonghoa/MST/actions/runs/42628249892/artifacts/13679451702), name `mst-m4-option-a-witness-owner-change-NO-APPLY`, retention 14 days, **NOT** an immutable independent owner signature or rollback floor.
- Other exact-code-head GitHub workflows: role separation #42628249858, Option A scope #42628249759, GitHub remote readback #42628249837, live permission inventory #42628249799, readiness denial #42628249638, untrusted synthetic cross-run journal #42628249705, untrusted registry #42628249810 — **all SUCCESS**. Nine workflows total on this commit including Foundation, owner packet.
- **Final documentation-containing HEAD requires its own exact-HEAD check** before reporting the entire release candidate as CI green.

## 4. Honest owner/custody decisions still unresolved

C01 independent GitHub policy-admin + root/bypass inventory; C02 separate/isolated witness ref controller and namespace; C03 genesis/first trustworthy floor; C04 explicit ruleset install plus authenticated readback; C05 two writers, signer and independent reader enrollment; C06 actual concurrent CAS/rollback/root-admin adversarial tests; C07 licensed SSI/DNSE/VCBS as-of/Drive retention/physical bytes and key revocation; C08 original 63 A02 modules owner disposition, A03 opt-in V2 ABI, M3/M4/M8 approval and no unauthorized trading.

**Critical:** If one actual administrator can rewrite both GitHub root and Drive history, then even two distinct account aliases, GitHub verified signatures and an empty visible bypass list do NOT establish a globally non-resettable floor. Option A was selected as a *platform restriction*, not consent to lower the G01/G02 bar. Keep [#16](https://github.com/ngluonghoa/MST/issues/16) SIGNED-G01..G08, [#15](https://github.com/ngluonghoa/MST/issues/15) witness, [#13](https://github.com/ngluonghoa/MST/issues/13) multiwriter CAS, [#14](https://github.com/ngluonghoa/MST/issues/14) cross-service, [#10](https://github.com/ngluonghoa/MST/issues/10) Drive, [#9](https://github.com/ngluonghoa/MST/issues/9) vendor legal source, [#4](https://github.com/ngluonghoa/MST/issues/4) A02 and [#6](https://github.com/ngluonghoa/MST/issues/6) A03 **OPEN**.

**No privileged change done or approved here:** no new witness ref, no ruleset POST/PATCH/DELETE, no main ruleset modifications, no key enrollment, no new writer credential, no Drive ACL edit, no licensed source/real market-cache write, no merge and no trade. Production cache reader/publisher and M5/M8 release stay **BLOCKED**.

**Next safe step:** continue read-only owner decision packet review and verify technical feasibility of independent root custody under existing GitHub+Drive roles; ask for explicit approval ONLY before exact privileged change and never silently add cloud providers.
