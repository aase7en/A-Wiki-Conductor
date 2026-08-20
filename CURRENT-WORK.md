# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Native Execution Foundation — Work-class execution plane**

## Active work order

None.

Most recently completed:
- `WO-P1-031 — Native Execution Core`
- `WO-P1-030 — Runtime Setup Service + Desktop Dialog`
- `WO-P1-028R1 — Lifecycle Assembly Contract Regression Repair`

## Completed foundation

- [x] Phase 1 local Multi-Serena Control Center MVP.
- [x] Runtime lifecycle/setup/readiness safety stack.
- [x] A-Wiki ↔ A-Conductor sibling-repo responsibility contract.
- [x] Native execution core classified `EXTEND` against A-Wiki.
- [x] Project-root-confined bounded text read/list/write.
- [x] Atomic write with mutation authority and SHA-256 overwrite precondition.
- [x] Authorized argv subprocess primitive with `shell=False`, executable allowlist, cwd confinement, timeout, conservative environment, bounded output and digests.
- [x] P1-031 verification: 16 targeted + 439 full-suite tests, compileall, diff check, static safety scan.
- [x] Active Conductor listener preserved at PID 25396.

## External / deferred gate

- `DR-P1-003`: live Worker 3 Stage B remains `BLOCKED_EXTERNAL` until a unique transport binding is explicitly provisioned/authorized. Do not reuse Conductor/Phase6 transport.
- A-Wiki companion registration payload remains prepared at `docs/contracts/a-wiki-companion-registration-payload.md` and awaits an authorized A-Wiki execution surface.

## Repository state

- Branch: `main`
- Git remote: none

## Next safe action

Open a bounded fixed-method adapter work order over the Native Execution Core. Preferred next slice: safe Git read/write families plus test/build execution with known command shapes. Do not expose raw `NativeSubprocessRunner` directly to an LLM and do not add destructive Git families without a separate decision/authority design.
