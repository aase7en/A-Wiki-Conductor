# WO-P1-181 — ZCode Windows child environment DNS boundary

Status: READY_FOR_EXACT_SHA_REVIEW / R3 CORRECTIVE REPAIR
Date: 2026-09-11
Owner: GPT-5.6 Sol integrator/implementer; independent GLM/ZCode exact-SHA review required before acceptance
Repository: aase7en/A-Wiki-Conductor
Branch: fix/wo-p1-181-zcode-windows-child-env
Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo181-zcode-child-env
Base: 680566d25e105630b321127c1a9b3e9e61af4bd4
Parent authority: Issue #213 ZRA-1 + Issue #233 continuity; triggered by WO179 live attempts 1 and 2.

## Defect

The specialized ZCode helper constructs the app-server child environment as exactly `ELECTRON_RUN_AS_NODE=1` plus the accepted ephemeral credential. On Windows this omits `SYSTEMROOT`, and exact installed `ZCode.exe` / Node DNS resolution fails with `getaddrinfo EAI_FAIL cointh.com` even while host DNS and TCP/443 are healthy.

Deterministic synthetic reproducer on the same Windows host and exact installed ZCode bundle:

- explicit child env (`ELECTRON_RUN_AS_NODE` only) -> `EAI_FAIL`;
- add only inherited non-secret `SYSTEMROOT` -> `DNS_OK`;
- `WINDIR`, `SYSTEMDRIVE`, `TEMP`, or `USERPROFILE` alone do not fix the failure.

Two authorized WO179 live attempts failed with the same redacted provider error `EAI_FAIL cointh.com`. Attempt 2 proved canonical recovery composition separately and ended execution `RECOVERY_REQUIRED` / job `BLOCKED`, with admission + lease released and no orphan.

## Risk / failure model

R3 because this code is the credential-bearing provider child-process boundary. The repair must restore required Windows OS runtime state without reopening ambient provider/auth/config inheritance.

Security invariants:

1. The child environment remains explicit and allowlisted.
2. No arbitrary parent environment is inherited.
3. No legacy credential variables (`ANTHROPIC_AUTH_TOKEN`, `CLAUDE_API_KEY`, `OPENAI_API_KEY`, `ZCODE_API_KEY`) may enter the child.
4. The accepted credential still appears only under the canonical delivery key (`ANTHROPIC_API_KEY` for this route).
5. On Windows, `SYSTEMROOT` is inherited from the helper process as the minimum proven non-secret OS dependency.
6. Missing/blank/NUL-containing Windows `SYSTEMROOT` fails closed before child spawn; do not silently fall back to ambient environment.
7. Non-Windows behavior remains unchanged except where deterministic tests require explicit proof.

## Scope

Mutable:
- `src/a_conductor/zcode_supervised_helper.py`
- `tests/test_zcode_real_helper_e2e.py`
- this work-order document

May add one narrowly-scoped helper test file only if existing tests cannot express the fail-closed environment contract without duplication; checkpoint scope expansion first.

Forbidden:
- provider config/store/router changes;
- credential-ref semantics changes;
- ZCode user config edits;
- private Drive secret edits;
- installed application/live DB mutation;
- retry-policy changes;
- broad environment inheritance;
- merge/self-acceptance without independent exact-SHA review.

## RED / acceptance

RED-first requirements on Windows:

1. real-helper E2E must require child env keys exactly `{ELECTRON_RUN_AS_NODE, SYSTEMROOT, ANTHROPIC_API_KEY}` and prove prompt/secret confinement remains intact;
2. child environment builder must fail closed when Windows `SYSTEMROOT` is absent/blank/invalid;
3. exact installed `ZCode.exe` synthetic DNS probe with the repaired minimal child environment must return `DNS_OK` without any real credential;
4. existing ZCode/helper/supervised/provider regression suites remain green;
5. secret scan, diff check, UTF-8 and changed-scope audit pass;
6. freeze exact SHA, independent GLM/ZCode review reports P0=0/P1=0/P2=0, exact-head hosted CI passes, then GPT/integrator acceptance/expected-head merge/post-main verification.

## Implementation / verification checkpoint

R3 repair implemented on Windows with the narrowest proven environment change:

- RED: `test_real_helper_happy_path_e2e` failed because the actual child environment contained only `ELECTRON_RUN_AS_NODE` + `ANTHROPIC_API_KEY`; required `SYSTEMROOT` was absent.
- Repair: `_build_child_environment()` now copies only non-secret `SYSTEMROOT` from the helper environment on Windows; missing/blank/NUL-containing value fails typed `CHILD_ENV_SYSTEMROOT_INVALID` before child spawn. Ambient environment inheritance remains closed.
- Positive exact-key E2E: child environment is exactly `{ELECTRON_RUN_AS_NODE, SYSTEMROOT, ANTHROPIC_API_KEY}`.
- Exact installed `ZCode.exe` synthetic DNS proof: repaired environment returns `DNS_OK`; no real provider call and no real credential used.
- Targeted fail-closed + real-helper tests: 2 passed.
- All `test_zcode*.py`: 194 passed.
- Broader ZCode/owned-process/Windows-observer/supervised/provider boundary battery: 527 passed.
- `compileall`, `git diff --check`, strict UTF-8: PASS.
- Added-line secret heuristic found only the explicitly synthetic test literal `synthetic-secret-not-real`; no real credential value is present in the candidate.

Remaining before acceptance: exact staged-scope audit -> frozen SHA -> independent GLM/ZCode exact-SHA review with P0=P1=P2=0 -> exact-head hosted CI -> GPT/integrator fenced merge -> post-main verification.

## Retry boundary

WO179 live Attempt 3 is forbidden until WO181 is accepted/merged/post-main verified. After that, WO179 may create a fresh task/session/batch/execution identity and perform at most one additional bounded live attempt under a separately checkpointed gate. Attempt 1/2 identities are never replayed.
