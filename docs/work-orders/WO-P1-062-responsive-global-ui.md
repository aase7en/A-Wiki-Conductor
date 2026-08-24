# WO-P1-062 — Responsive Global UI + Multilingual Guidance

Created: 2026-08-24 · Owner: GPT-5.6 Sol + SunDay-Worker 1 · Status: COMPLETE / ABSORBED INTO v0.5.0 BASELINE
Depends on: WO-P1-061 GPU Sunday Family particle portrait integration

## Goal

Refine the A-Sunday Conductor desktop UI so it uses available screen space intelligently,
keeps primary actions obvious and globally readable, and moves localized teaching/help
into tooltips/guidance rather than translating button labels.

This work begins only after this plan is recorded in repo SSoT. Implementation follows the
project loop: grill-with-docs/upstream freshness -> brainstorm/reuse gate -> deep plan ->
implement -> review -> debug -> tests/E2E -> report -> defect memory -> PR -> CI/CD ->
fetch/merge.

## User requirements — 2026-08-24

1. Responsive controls:
   - narrow window: controls compact/wrap into fewer-width rows;
   - wide/maximized window: controls expand into a horizontal action flow;
   - avoid narrow stacked controls wasting space on large windows.

2. Primary button language:
   - all user-facing action button labels are English globally;
   - button labels do not change when language preference changes.

3. Guidance language:
   - language selector supports Thai (`th`), Simplified Chinese (`zh-CN`), English (`en`);
   - selected language changes tooltips, hover help, teaching text, explanatory/status prose;
   - action labels remain canonical English.

4. Product vocabulary:
   - remove user-facing `Serena` wording from normal Active/hover/help copy when the user
     is interacting with A-Conductor concepts;
   - use canonical product terms such as `Conductor`, `Worker`, `Runtime`, `Connector`;
   - keep `Serena` only where the underlying Serena runtime/diagnostic identity is
     technically necessary.

5. Action order:
   - controls should follow operator sequence left-to-right where space permits;
   - initial canonical flow:
     `Add Project -> Assign -> Add Worker -> Start -> Stop/Restart -> Open/Logs/Advanced`;
   - destructive/secondary operations remain visually separated.

6. Donate:
   - add `Donate` at the lower-right beside `Check Update`.

7. Brain + teaching header:
   - move `Add Brain` to the upper-left near the application name;
   - reclaim header space made available by the Sunday Family particle portrait;
   - replace persistent Step 1/2/3 instruction blocks with a compact typewriter teaching
     line: type -> cursor -> pause -> erase -> next instruction;
   - animation must be stoppable with app shutdown and must not spawn subprocesses.

8. Main lower workspace:
   - MONITOR and ACTIVITY LOG use a horizontal ~50/50 split on normal/wide windows;
   - narrow-window fallback may stack them vertically if needed for minimum usable width.

9. Accessibility/usability:
   - keyboard focus order should follow action order;
   - no control should become unreachable at the supported minimum window size;
   - avoid animation that steals focus or causes layout movement;
   - typewriter respects a future reduced-motion preference seam.

10. Particle visual contract (shared with WO-P1-061):
    - Sunday Family uses only white/gray particles on black;
    - no cyan, amber, orange, or other accent colors in the family portrait;
    - points should be very small/fine and retain maximum recognizable fidelity to
      `assets/sunday-family-particle.png`;
    - eye tracking changes geometry/position, not color.

11. Copyable diagnostics:
    - MONITOR and ACTIVITY / LOG text must support normal text selection and copy;
    - provide an explicit `Copy` / `Copy All` interaction where practical so bug reports can
      be copied without fighting disabled-widget state;
    - copy support must not make logs editable by accident.

12. Assign replacement UX:
    - when a project is selected and Assign targets a Worker that already has another project/path,
      do not silently fail or require a manual Release first;
    - show a confirmation popup naming the old assignment and the new project;
    - on confirmation, replace the Worker's assignment safely in one user flow;
    - on cancel, leave the current assignment unchanged;
    - preserve existing control-center safety/invariant checks rather than bypassing them.

13. Connector discoverability / ownership:
    - explain in-product what the Worker `Connector` column means: the runtime/tunnel connector
      available for that Worker/project, not a second Worker identity;
    - verify whether connector creation is already supported from the desktop UI and make the path
      discoverable if so; do not imply that GPT/Agent is required unless the repo/runtime really
      requires an agent-only setup step;
    - if creation is blocked by a real prerequisite (for example credentials/tunnel ID/reference
      template), surface that prerequisite in localized help instead of leaving the user guessing.

## A-Think + brainstorming design review — 2026-08-24

**Real problem:** make the installed Windows desktop control center responsive, globally readable,
self-explanatory, and easy to debug without weakening Worker/assignment/runtime safety invariants.

**Done criteria:**
- compact/wide/maximized layouts use available width appropriately;
- all action buttons stay English while help can switch Thai / Simplified Chinese / English;
- diagnostics are copyable but remain read-only;
- replacing an occupied Worker assignment is confirmed and cannot silently lose the old assignment;
- Connector meaning and creation prerequisites are discoverable without requiring GPT;
- deterministic tests + real resize/language/copy/assign/connector E2E pass before PR/merge.

### Approaches

| Approach | Complexity | Main failure mode | Reversible? | Decision |
|---|---:|---|---|---|
| A. UI-only patches | low | Release→Assign can lose old assignment if second step fails | two-way | reject |
| B. Bounded domain + UI extension | medium | small cross-layer change requires careful tests | two-way | **recommended, pending user approval** |
| C. Rewrite desktop UI into new components/framework | high | broad regression/scope explosion | one-way-ish | reject |

**Recommended B:** keep the existing Tk desktop shell and current responsive/i18n work; add a small
validated assignment-replacement primitive below the UI, read-only copy helpers, and localized
Connector discovery help. No framework rewrite and no duplicate orchestration system.

### Decomposition (A-Loop phase 1 mapped to this repo's existing WO/claim SSoT)

1. `UI-062-A` — finish + verify responsive workflow/header/footer/language behavior already partially implemented.
2. `UI-062-B` — copyable MONITOR/ACTIVITY with selection + Copy All while read-only.
3. `UI-062-C` — confirmed replacement assignment with prevalidation and STOPPED safety gate.
4. `UI-062-D` — Connector column/help + Add Connector prerequisite discoverability.
5. `UI-062-E` — deep review/debug + resize/language/copy/assign/connector E2E + report/defect memory/PR/CI/merge.

### Pre-mortem / disproof targets

- rapid resize causes Tk Configure reflow loops or inaccessible buttons;
- language switching changes button labels or leaves stale tooltip snapshots;
- replacing a RUNNING Worker changes project under an active process;
- release-then-assign loses the old assignment on validation/save failure;
- copy support accidentally makes log Text widgets editable;
- Connector `-` remains unexplained or Add Connector fails because no validated reference exists;
- local ESET `.ps1`/fresh-PE locks are mistaken for product regressions instead of CI/environment evidence.

### Verified Connector behavior from current code

- WORKERS `Connector` shows the connector instance whose project path matches that Worker's assigned project.
- `-` means no matching connector. `Start` can still use the configured lifecycle runtime when ready;
  otherwise the Worker is blocked with `SETUP_REQUIRED`.
- `Add Connector` already exists in the desktop UI; GPT/Agent is **not required** for connector creation.
- creation clones a validated existing connector reference (scripts/templates/config), auto-selects the next
  health port, and accepts an optional Tunnel ID that may be set later. With no valid reference, creation
  can fail with `REFERENCE_MISSING` / reference-artifact errors; the UI should explain this prerequisite.

### Brainstorming hard gate

The user explicitly invoked the brainstorming skill. New production implementation for requirements
11–13 pauses at this design review until the user approves the recommended Approach B. Existing dirty
implementation for requirements 1–10 is preserved and must not be rewritten independently.

## Responsive design contract

Use breakpoint behavior based on actual available width, not OS display resolution.

Suggested initial states (tune by real E2E evidence):
- COMPACT: content width < 900 px — wrapped action rows, reduced gaps, MONITOR/ACTIVITY may stack.
- STANDARD: 900–1279 px — horizontal primary action flow with compact secondary group.
- WIDE: >= 1280 px — single-row primary actions where practical; MONITOR/ACTIVITY 50/50.

Do not hard-code one visual arrangement only for 1080×680.

## Internationalization contract

Separate two concepts:
- `action_label(key)` -> canonical English only.
- `localized_help(key, language)` -> `th`, `zh-CN`, or `en`.

Existing i18n infrastructure should be extended/reused rather than replaced.

## Model/agent routing contract

Research snapshot: `docs/research/model-routing-2026-08-24.md`.

Default split:
- GPT-5.6 Sol MAX: architecture, cross-cutting decisions, visual/UX judgment, multimodal
  asset fidelity, difficult debugging, final review/integration/E2E acceptance.
- GLM-5.3 MAX: bounded implementation tickets, repetitive/refactor-heavy code, test
  generation, CLI/repo work, lower-cost bulk execution, first-pass bug fixing.
- Deterministic tools/tests: always preferred when no model judgment is required.

Anti-duplication:
- one WO/ticket has one active owner;
- GLM implementation and GPT review are sequential roles unless file scopes are disjoint;
- no two agents implement the same intent independently;
- actual repo + CURRENT-WORK + handoff + WO is authoritative.

## Reuse-before-build classification

- Responsive layout: EXTEND existing Tk layout.
- English action labels + localized help: EXTEND existing `i18n.py`; do not build a second i18n system.
- Typewriter teacher: NEW bounded UI helper, no new event loop.
- Model routing policy: REUSE/EXTEND A-Wiki work-order/claim/routing principles; A-Conductor
  records execution-surface fit and evidence but does not duplicate A-Wiki orchestration brain.
- MONITOR/ACTIVITY split: EXTEND existing PanedWindow/layout primitives.

## Design approval — 2026-08-24

User explicitly approved **Approach B — bounded domain + UI extension** and authorized execution through completion. The current installed app screenshot still shows the older UI (Thai action labels and no visible `Add Connector`), so final acceptance now includes rebuild/install/relaunch verification that the shipped desktop binary visibly contains the new controls.

## Acceptance criteria

- [ ] Window resizing is tested at minimum, 900-ish, 1280+, and maximized widths.
- [ ] Wide window uses horizontal action flow and does not retain unnecessary stacked buttons.
- [ ] Compact window keeps all primary controls reachable.
- [ ] Every action button label is English.
- [ ] Thai/Chinese/English selection changes help/tooltips/guidance without changing action labels.
- [ ] Normal user-facing Active help no longer presents Serena as the product identity.
- [ ] Primary controls follow the documented action order.
- [ ] Donate appears beside Check Update at lower-right.
- [ ] Add Brain appears upper-left near product name.
- [ ] Typewriter instruction cycles safely without subprocesses or focus/layout jitter.
- [ ] MONITOR and ACTIVITY LOG render 50/50 horizontally on standard/wide windows.
- [ ] Sunday Family portrait remains grayscale-only and recognizably matches source asset.
- [ ] MONITOR and ACTIVITY / LOG support selection/copy plus an explicit copy-all path while remaining read-only.
- [ ] Assigning to an occupied Worker requires confirmation and safely replaces the previous project when confirmed.
- [ ] Worker Connector meaning and connector-creation path/prerequisites are discoverable in localized help.
- [ ] Unit/UI tests + realistic resize/language/action-flow E2E pass.
- [ ] Deep bug hunt includes resize while animation runs, language switching, app close,
      GPU failure fallback, and persisted language preference.
- [ ] PR CI green before merge.
- [ ] Fresh installed/relaunched Windows build visibly shows `Add Connector` and the new English/responsive UI (prevents source-vs-installed-version drift).

## Execution order

A. Finish/reconcile WO-P1-061 grayscale GPU/fallback correctness.
B. Inventory existing layout + i18n + footer/header seams.
C. Add failing tests for action-label invariant, language-help switching, layout mode logic.
D. Implement responsive action bar and lower 50/50 split.
E. Implement canonical English buttons + `zh-CN` guidance extension.
F. Move Add Brain + typewriter guidance.
G. Footer Donate beside Check Update.
H. Add read-only copyable MONITOR/ACTIVITY diagnostics + Copy All.
I. Add guarded Assign replacement confirmation flow.
J. Clarify Connector column/creation prerequisites and expose localized help.
K. Review/debug/realistic E2E resize/language/assign/copy matrix.
L. Defect memory, report, PR, CI/CD, fetch/merge.

## Checkpoint

2026-08-24: requirements captured from user before implementation. No WO-P1-062 production
code should be changed until this planning checkpoint and the linked routing research note are
present in repo SSoT.

## Closure — v0.5.0 baseline

The responsive/global-language/copy-log/assignment/connector capabilities from this WO are present on `main` at the WO-P1-063 start gate. Further visual restructuring is owned by WO-P1-063 and `DESIGN.md`; do not reopen this WO to implement the same intent twice.
