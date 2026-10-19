# WO-P1-683 - Sunday config-root alignment (offline only)

Identity schema: GITHUB_ISSUE_V1
Issue: #683
Status: GOVERNANCE_BOOTSTRAP - proposal awaiting integrator packet review; no SRM mutation admitted.
Risk: R0 DOCS bootstrap ONLY; intended source delivery R3 (installer, persisted configuration and foreign-state isolation).
Topology: CROSS_REPO - A-Wiki-Conductor (AWC) authority/governance; SunDayRemoteMCP (SRM) execution source/tests. Each future lane binds exactly one repository.
Parent: #630 CONFIG-PREP comment 6230245217; related #607 INSTALL-1 and #659 allowlist reconciliation.

## 1. Authority, ownership and exact pins

- User instruction 2026-10-19 authorizes agent-decidable OFFLINE engineering, not live activation. This bootstrap authorizes writing this WO only, not implementing its proposal.
- Driving issue: https://github.com/aase7en/A-Wiki-Conductor/issues/683.
- Root bootstrap claim: https://github.com/aase7en/A-Wiki-Conductor/issues/683#issuecomment-6271673854, CORRECTED/NARROWED by https://github.com/aase7en/A-Wiki-Conductor/issues/683#issuecomment-6271683230. The correction controls: EXACT tracked mutable scope is this file only.
- AWC bootstrap tuple: `A:\GitHub\_worktrees\AWC-wo683-config-root` -> `docs/wo683-config-root` -> base `9cd58c787a2acfbb290e380543eaac2e5ac6e2e8` -> root claim above -> this WO.
- Readiness compatibility set: AWC `9cd58c787a2acfbb290e380543eaac2e5ac6e2e8`; SRM `241160bb93945302b12a6497e5aebe0c85eb895d`. Re-pin after governance integration or any member drift, with focused delta review before source admission.
- Protected roots `A:\GitHub\A-Wiki-Conductor` (observed `d3f319a64fd4cef03a7fe5e23a676ba6db8d4b2b`) and `A:\GitHub\SunDayRemoteMCP` (observed `2f033cfb1f61b6dff9c2e55264cca6f2a9125e95`) are stale, not mutation destinations. Unknown/untracked work remains untouched.
- Alternate SRM reference `A:\GitHub\_worktrees\SunDayRemoteMCP-wo677-context` is clean at `546c05eb5e31480de9dfbd6c8108afa3d1ff0065`; source/test/scripts/package/lock/tsconfig paths match the SRM pin. Reference only, not an implementation claim.
- Historical evidence: #607 A-G source claims released; #630 slice-A claim released at comment 6126647821; #659 claim 6165983805 released at 6168010170; readiness API returned no open SRM PRs. These facts do NOT certify current path ownership. `SRM_SOURCE_CLAIM=UNKNOWN` pending fresh census and exact-path claim.
- Shared continuity fold is `BLOCKED:OWNERSHIP_UNRESOLVED`: independent recovery found #549 / PR #550 PARKED-WAITING_EXTERNAL reservation includes `CURRENT-WORK.md` and `handoff.md`; owner not proven released. Those files and `COLLAB.md` are forbidden writes. Do not create alternative continuity copies. Reuse this WO, driving issue and ignored `runs/WO-P1-683/` evidence until ownership is explicitly resolved.
- `runs/WO-P1-457/` belongs to a separate advisory reviewer and is forbidden to this lane.

`SAFE_TO_MUTATE_SRM=NO`: integrator must first adjudicate this packet, establish a fresh isolated SRM worktree/branch/HEAD/dirty-state/owner/scope tuple, acquire a non-overlapping claim within global WIP, and rerun the full startup/source gate. This document is not that claim. No commit/push/PR/merge permission is granted by the bootstrap.

## 2. Verified problem and reuse decision

Readiness used pinned `git show` / `git grep`, not stale working source. AWC entry/graph/AGENTS, FAST_EXECUTION_PROTOCOL, collaboration/routing policy, relevant architecture sections, CURRENT-WORK, WO630 and WO659 were read. SRM AGENTS/current-work/operator docs were read at its pin; SRM has no `00-AGENT-ENTRY.md` there and its CURRENT-WORK is historical. Current user authority, actual source and later GitHub evidence control.

SRM at `241160bb93945302b12a6497e5aebe0c85eb895d`:

| Surface | Verified divergence |
| --- | --- |
| `src/sunday/agent-entry.ts:41-43` | `sundayAgentConfigRoot()` hardcodes the foreign `~/.desktop-commander-device`. Preflight uses it at line 195. |
| `src/sunday/sunday-config-root.ts:51-60,86+` | Existing pure/injectable resolver defaults to `~/.sunday-device`; env override; lexical equality/descendant/ancestor foreign refusal. |
| `src/npm-scripts/sunday-install.ts:61,72,104,150,157` | CLI explicit root selects installer artifacts, but post-install pairing/agent-state reads independently use `sundayConfigRoot()`. |
| `src/npm-scripts/sunday-doctor.ts:22,77` | Sunday runtime root and installer root differ. Doctor does not currently parse `--config-root`, despite WO659 wording. |
| `src/sunday/installer.ts:145-151` | Library requires explicit nonempty string root; no foreign guard at this boundary. |
| `src/sunday/agent-lifecycle.ts:215-249,526` | Direct initializer writes without foreign-root guard; startup factory inherits foreign default. |
| Enroll / smoke CLIs | Enroll already uses Sunday resolver and remains refusal-only. Smoke inherits foreign helper default. |

REUSE/EXTEND the existing resolver, installer, doctor and state stores. No new schema, root manager, migration engine, authority store, scheduler, dependency or issuer.

## 3. Alternatives and minimal recommendation

| Approach | Benefit | Failure / disposition |
| --- | --- | --- |
| Change only the foreign default literal | Tiny diff | Leaves explicit-root bypass and first-run split-brain. Reject. |
| Extend existing pure resolver and align existing consumers | One root-selection contract; bounded source/test change | Recommended; validate at IO boundaries as well as CLI. |
| Discover/adopt/copy legacy state automatically | Apparent continuity | Expands credential/grant/destructive authority and violates clean start. Forbidden. |

Proposed precedence: explicit caller/CLI root -> `SUNDAY_CONFIG_ROOT` -> `~/.sunday-device`. Preserve the existing injectable environment API; do not break existing `sundayConfigRoot(env)` callers. `sundayAgentConfigRoot()` should delegate rather than retain a second default. Resolve once per invocation and use that selected root for ALL install config/marker, pairing and agent-state observations. Doctor should accept the same explicit-root flag; enroll keeps its existing environment-root contract, no live flow added. Smoke retains its explicit-root option but uses the shared validated fallback.

CLI present-but-empty, missing-value, or malformed root options must fail, not silently fall back. Validate the selected root before reads/writes/mkdir, upstream callbacks or PID operations; retain existing inert option extraction and typed failure envelopes. A rejected foreign target must expose `SUNDAY_CONFIG_ROOT_FOREIGN`-class evidence, never success or a default-root retry. Explicit safe roots remain supported; an explicit legacy FOREIGN root is NOT an opt-in escape hatch. Compatibility means preserving foreign tooling/files and existing state, not reading/adopting its tokens/grants.

## 4. Failure model and invariants

1. No true user home/config/credentials may be read or written in verification. All HOME/USERPROFILE, Sunday and foreign reference roots are synthetic, process-local temp fixtures; override inherited root/upstream variables explicitly.
2. Default new install selects Sunday-owned root; presence of legacy state never changes selection. No discovery, automatic migration/adoption, token/grant copy, cleanup, or foreign deletion.
3. Foreign equality, descendants, containing ancestors, case/separator variants and relocated foreign roots refuse before effects. Fix the known drive-root/trailing-separator containment edge; sibling-prefix paths are not descendants.
4. Existing resolver is lexical: symlink/junction/8.3 aliases are NOT proven isolated by `path.resolve`. Pure selection must stay IO-free. Physical alias cases must be adversarially tested at existing IO boundaries and either fail closed or remain a blocking finding for integrator adjudication; never silently accept an isolation waiver. If safe alias enforcement needs paths outside section 5, STOP for a scoped amendment before mutation.
5. Direct initializer/library/preflight/factory consumers cannot bypass the selected-root guard. Root refusal never reaches a caller probe, pairing store, config write or PID acquire/release. Preserve existing typed containment rather than throw an unhandled factory error.
6. One command cannot combine install evidence from one root with pairing/agent-state from another. Reject invalid selection; never merge evidence to manufacture READY.
7. Doctor remains read-only on absent, valid, corrupt and inaccessible fixtures. Missing/corrupt/unreadable evidence preserves fail-closed distinctions; UNKNOWN is never healthy.
8. Installer writes ONLY existing `config.json` and `install.json`; no issuance, pairing, PID claim, agent start, autostart execution, registry change or credentials. Persisted schema and strict-write/lenient-read allowlist contracts remain unchanged; standalone allowlist stays NON-CANONICAL and grants never merge.
9. Preserve `INSTALLED_READY` exit-0-only contract and first-run truth. No new trust from HTTP 200, token presence, RDC ONLINE or mock pairing.
10. Existing rollback library removes only config/install artifacts, preserving pairing/agent-state/allowlist/other files. Do not expand to the four-file deletion mentioned in old advisory preparation; do not wire rollback CLI or perform rollback on live state.
11. `src/remote-device/device.ts` still uses foreign device persistence/DC transport. Root alignment is not native transport readiness, enrollment consent, or permission to run `device:start`.
12. Denial/evidence output must not leak tokens or forge diagnostic rows through path/control-character content. No production issuer, key generation, listeners, network calls, LIVE canary, installed/global changes, registry or global hooks.

## 5. Exact proposed SRM mutation allowlist (NOT yet admitted)

Source:

- `src/sunday/sunday-config-root.ts`
- `src/sunday/agent-entry.ts`
- `src/sunday/agent-lifecycle.ts`
- `src/sunday/installer.ts`
- `src/npm-scripts/sunday-install.ts`
- `src/npm-scripts/sunday-doctor.ts`
- `src/npm-scripts/sunday-smoke.ts`

Tests:

- `test/test-sunday-config-root.js`
- `test/test-sunday-agent-entry.js`
- `test/test-sunday-agent-lifecycle.js`
- `test/test-sunday-agent-installer.js`
- `test/test-sunday-install-firstrun.js`
- `test/test-sunday-allowlist-recon.js`
- `test/test-sunday-first-run.js`

Existing operator documentation:

- `docs/sunday-local-first.md`

No new source/helper module is authorized. Reuse local test `tempDir`/`makeRoot`, `pairIt`, `runInstall`, fs pairing store, watchdogs and subprocess patterns. Replace recon/first-run foreign-root positive fixtures with selected-root positives plus foreign negative sentinels; replace install-firstrun's two-store seeding with single-selected-root assertions. Preserve grant-boundary regression assertions, not just snapshots.

Exclude all other paths: especially remote-device auth/channel, enroll/verifier/test-issuer contracts, package/lock/build/dependency files, installed/global config, AWC product/tests, PR550-owned source/tests, and shared continuity. Amendment + fresh overlap adjudication is mandatory before expansion.

## 6. Acceptance / RED-first fault matrix

| ID | Case | Required result |
| --- | --- | --- |
| R01 | No explicit/env override | All affected defaults select synthetic home `.sunday-device`, zero foreign discovery. |
| R02 | Safe explicit root with conflicting env | Explicit wins consistently for installer, first-run and doctor; no second-root evidence. |
| R03 | Safe environment root only | Installer, doctor and preflight agree. |
| R04 | Empty/missing/malformed CLI root | Typed/nonzero refusal; zero root effects or callbacks. |
| R05 | Foreign exact/child/ancestor/case/separator variants | Typed foreign refusal before any reads/writes/probes/PID effects. |
| R06 | Relocated foreign reference; drive/root separator edges | Same isolation; sibling-prefix safe root allowed. |
| R07 | Legacy fixture has plausible tokens/grants/config | No adoption or false READY; foreign bytes unchanged. No real credential fixture. |
| R08 | Absent selected root | Doctor creates nothing; explicit installer creates only its two artifacts. |
| R09 | Corrupt/unreadable config/marker/pairing/agent-state | Existing typed fail-closed truth, no fabricated READY. |
| R10 | Direct library/initializer/preflight/factory | Same foreign rejection; inert options/proxy/getter regressions retained. |
| R11 | Symlink/junction/8.3 alias to foreign tree | Prove fail-closed at IO boundary or mark blocking; do not certify lexical check as physical isolation. |
| R12 | Strict grants, conflicting standalone and legacy forms | Strict display/use posture retained; standalone noncanonical, never merged. |
| R13 | Re-run/idempotency and rollback regression | No foreign effects; existing bounded rollback scope unchanged. |
| R14 | CLI exit/first-run output | Existing exit code contract; coherent selected-root evidence and escaped diagnostic text. |

Capture new behavioral rows RED against pinned baseline before production edits. Existing pinned test `test-sunday-install-firstrun.js` row 2b starts a loopback listener: DO NOT run it unchanged under this no-listener authorization. Replace that test-only dependency with a child-scoped deterministic fetch stub (temporary fixture/preload controlled by the test, never production env bypass/global hook) before running the adapted suite; retain exit-0 proof. No test may contact a real upstream. Inspect other selected regressions for IO/network before execution.

## 7. Verification commands and environment readiness

Readiness observed Node `v24.15.0`, npm `11.12.1` on Windows. Alternate SRM reference lacks local TypeScript, shx, esbuild and compiled config-root output. `DEPENDENCY_READY=NO` for that reference; this is not a source failure. No install/build/test was run during research. Fresh source worktree dependency availability/cache/provenance must be verified separately; no implicit network install, lifecycle scripts, setup/global install or protected-reference build. Existing build invokes tsc + shx staging + esbuild UI bundling and writes dist. TypeScript may emit despite type errors: check process exit, not emitted files.

Future commands ONLY in the admitted fresh SRM lane with isolated child HOME/config/upstream environment, local dependencies available and listener-free test adaptation complete:

```powershell
npm run build
node test/test-sunday-config-root.js
node test/test-sunday-agent-entry.js
node test/test-sunday-agent-lifecycle.js
node test/test-sunday-agent-installer.js
node test/test-sunday-install-firstrun.js
node test/test-sunday-allowlist-recon.js
node test/test-sunday-first-run.js
```

After scoped IO audit, related unchanged regression commands:

```powershell
node test/test-sunday-agent-gate.js
node test/test-sunday-device-gate.js
node test/test-sunday-pairing-state.js
node test/test-sunday-agent-state-store.js
node test/test-sunday-allowlist-config.js
node test/test-sunday-read-canary.js
git diff --check
```

Every command exit must be checked; do not hide prior failure with a later command's success. `npm test` builds then its runner builds again and discovers broad test files: NOT authorized blindly here; audit and isolate full-regression side effects first. Existing hosted codespell workflow alone is not build/test evidence. R3 freeze requires targeted+related/adversarial evidence, independent exact-SHA review, exact-head CI and GPT acceptance; no LIVE test can be substituted for missing offline proof. Integration/post-main steps require their own authority and exact reviewed-head gate.

Bootstrap verification: strict UTF-8 decode/no U+FFFD; `git diff --check` plus added-file whitespace check; exact tracked/untracked nonignored scope; focused `tests/test_work_order_identity.py` with new untracked WO included by the existing collector. Disable bytecode and pytest cache or direct them to the approved temp/ignored surface. No source/tests edited to make bootstrap verification pass.

## 8. Routing, stops and next safe action

- Routing fact: installed Windows Kilo 7.8.12 exposes configured `cointh-glm/glm-5.3` and `cointh-glm/glm-5.3-flash`. Both authorized RDC process environments lack already-bound `COINTH_GLM_AUTH_TOKEN`.
- Latest binding runbook is env-only and forbids searching secret files/env files/keychains. `GLM_OFFLOAD=BLOCKED:SECRET_SOURCE_UNAVAILABLE`; proxy quota `UNKNOWN`, NOT exhausted. No provider requests or secret searches occurred. Do not probe quota without the approved bound credential or infer upstream rate-limit.
- Eligible GPT/Sol fallback may execute after governance/source admission; independent R3 reviewer must remain separate from the author. Model availability never grants ownership, mutation, spend or merge authority.
- Stop for unknown ownership, pin/context drift, required scope expansion, nonisolated test IO, unresolved physical foreign alias, unintended grant/trust/schema changes, dependency acquisition requiring unauthorized network/global changes, or an actual LIVE boundary. Record a typed blocker; no blind retries or renamed bypass lane.
- No genuine human-only decision blocks this offline design. Production keys/custody, real issuance/enrollment, runtime activation and LIVE acceptance remain separate human gates; no domain/hosting purchase is required for the local-first pilot.
- NEXT_SAFE_ACTION: root integrator reviews alternatives, exact allowlist, precedence, foreign/physical-path failure model and no-listener test plan; adjudicates amendments; then separately admits a fresh SRM source tuple/claim and re-pins. Until then `SAFE_TO_MUTATE_SRM=NO`. Shared-doc fold remains ownership-blocked, not silently completed.

## 9. Checkpoint log (append-only)

- 2026-10-19: Bootstrap drafted in the clean isolated AWC tuple, limited to this WO under narrowed claim 6271683230. Source/test implementation, credentials, true home/config access, provider requests, listeners/network/LIVE actions and installed/global changes not performed. Verification results are reported back to the integrator; evidence may live only under ignored `runs/WO-P1-683/` or approved temp paths. No commit/push/PR/merge performed by this lane.
- 2026-10-19: Bootstrap verification PASS: `git diff --check`; strict UTF-8/no replacement character; exactly one issue identity; added-file whitespace and exact sole-file scope. `python -B -m pytest tests/test_work_order_identity.py -q -p no:cacheprovider --basetemp C:\Users\aase7en\AppData\Local\Temp\kilo\wo683-identity-20261019-1616` returned 33 passed (1.00s), with `PYTHONDONTWRITEBYTECODE=1`. Existing collector includes the new untracked WO. No workspace cache/bytecode or other nonignored file created. These are bootstrap checks, not SRM behavior/build evidence.
