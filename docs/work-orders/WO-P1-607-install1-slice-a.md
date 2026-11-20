# WO-P1-607 — INSTALL-1 slice A: Windows-first read-only Device Agent install front door

Issue: #607
(Priority authority: #495 comment 6035553079 Track A — highest user-visible
priority. This WO is the governance bootstrap + contract freeze; source
mutation gated to a separate claim below.)
Class: CROSS_REPO — authority A-Wiki-Conductor / implementation SunDayRemoteMCP
Risk: R3 (local install surface, autostart, pairing security, allowlist)
Executor route: Windows ZCode + GLM-5.3 MAX primary
Worktree (bootstrap): `A:\GitHub\_worktrees\A-Wiki-Conductor-wo607-install1-bootstrap`
Branch: `docs/wo-p1-607-install1-slice-a`
Bootstrap base: `3c7534d762ca28ba54bccea35c5f683e9e0f152b` (= origin/main)

## Slice A scope (read-only first)

Per the reorder's INSTALL-1 target, bounded to the read-only path:
1. installer entry + packaging layout (Windows-first);
2. pairing/enrollment contract (device identity + per-device token, loopback
   or user-approved transport only; no broad network listener);
3. autostart/restart recovery skeleton (crash-safe re-enrollment, no
   duplicate processes);
4. folder allowlist model — fail-closed default, explicit user grant only,
   deny-by-default outside the allowlist, no glob escapes;
5. read-only Doctor/health/version (self-check: version, config validity,
   allowlist state, pairing state, upstream reachability);
6. deterministic read smoke: ping -> list -> read against an allowlisted
   folder;
7. uninstall/rollback that removes only components it owns, never foreign
   work.

Out of scope (later slices / other tracks): mutation smoke (temp
write/readback/cleanup), Mac parity, semantic features (#341), mutation
authority (#526/#495/ACT-1 consumption), Worker/Serena changes (G0 forbids
removal in this lane).

## REUSE archaeology — mandatory before source freeze

The source claim MUST inventory, in SunDayRemoteMCP current main, existing
surfaces for: install/packaging scripts, process supervision/autostart,
pairing/enrollment, allowlist/permission models, doctor/health endpoints,
smoke harnesses, connector/device routing; and classify each
REUSE/WRAP/EXTEND/NEW with exact symbols. No second scheduler, task DB,
claim/lease store, retry machine, or review/completion authority anywhere.

## Frozen failure floor (source claim, RED-first)

- fresh install on clean machine -> healthy read-only smoke PASS;
- deny-by-default: read outside allowlist -> typed deny, no data leak;
- pairing without user grant -> no enrollment, no listener;
- corrupt/partial install -> Doctor reports typed state, repair path safe;
- autostart double-boot -> exactly one agent process (idempotent start);
- uninstall -> removes owned components only; foreign files untouched;
- restart mid-smoke -> smoke reports INCOMPLETE, never fake success;
- secrets: pairing tokens never logged/echoed/committed;
- gateway/monitor failures cannot affect install truth;
- UNKNOWN never reported as healthy.

## Cross-repo binding rule

Any SRM mutation runs in an SRM-side isolated worktree/branch/claim, pinned
as an exact compatibility set `{A-Wiki-Conductor@SHA_AUTH,
SunDayRemoteMCP@SHA_EXEC}` frozen at source-claim time; either head drift
invalidates the set until re-pinned.

## Non-goals

No Worker 1-5 or Serena changes; no CUTOVER declaration (gates live in the
reorder comment); no CI/packaging overhaul beyond slice A needs.

## Acceptance criteria (bootstrap)

Docs-only: this WO merges with identity-fixture + CI green; contract frozen;
source work gated to the next claim with full cross-repo mutation gate.

## Claim

Bootstrap claim: `WO-P1-607-INSTALL1-BOOTSTRAP-WIN-001` (released on merge).
Source claim: `WO-P1-607-INSTALL1-SOURCE-WIN-001` (posted under #607 after
the mutation gate rerun).
