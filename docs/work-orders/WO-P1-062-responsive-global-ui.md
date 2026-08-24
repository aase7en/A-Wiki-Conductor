# WO-P1-062 — Responsive Global UI + Multilingual Guidance

Created: 2026-08-24 · Owner: GPT-5.6 Sol + available SunDay Worker · Status: PLANNED
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
- [ ] Unit/UI tests + realistic resize/language/action-flow E2E pass.
- [ ] Deep bug hunt includes resize while animation runs, language switching, app close,
      GPU failure fallback, and persisted language preference.
- [ ] PR CI green before merge.

## Execution order

A. Finish/reconcile WO-P1-061 grayscale GPU/fallback correctness.
B. Inventory existing layout + i18n + footer/header seams.
C. Add failing tests for action-label invariant, language-help switching, layout mode logic.
D. Implement responsive action bar and lower 50/50 split.
E. Implement canonical English buttons + `zh-CN` guidance extension.
F. Move Add Brain + typewriter guidance.
G. Footer Donate beside Check Update.
H. Review/debug/realistic E2E resize matrix.
I. Defect memory, report, PR, CI/CD, fetch/merge.

## Checkpoint

2026-08-24: requirements captured from user before implementation. No WO-P1-062 production
code should be changed until this planning checkpoint and the linked routing research note are
present in repo SSoT.
