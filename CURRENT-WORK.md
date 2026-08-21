# A-Conductor — Current Work

Last updated: 2026-08-22 (GLM 5.3 resume checkpoint)

## Current phase

**Phase 1 delivered. WO-P1-056 implementation is verified and PR #27 is CI-green but not merged yet. Merge #27 first, then start WO-P1-057.**

## Source-of-truth rule

Do **not** reconstruct task state from chat memory.

For resume, use in this order:
1. actual repository / GitHub state,
2. `CURRENT-WORK.md`,
3. `handoff.md`,
4. active `docs/work-orders/WO-*.md`,
5. `PROJECT-PLAN.md` + binding contracts/ADRs.

## Verified completed work

- WO-P1-052 — Second Brain Phase 1 shipped (Index+Pull brain profile, materialize-on-start).
- WO-P1-053 — usability overhaul shipped.
- WO-P1-054 — onboarding / Tunnel ID / AI connection guide shipped.
- WO-P1-055 — ONLINE pulse + themed Thai teaching errors shipped via PR #26; merged main at `2d345eb`.
- WO-P1-056 — Serena Activation Prompt Helper implementation verified locally:
  - focused TDD: 4 RED -> 4 passed,
  - desktop UI: 40 passed,
  - full suite: 812 passed,
  - no automatic Serena activation, no target-repo mutation.

## Current verified repository / PR state

Verified 2026-08-22 before this documentation checkpoint:

- Repo: `A:\GitHub\A-Wiki-Conductor`
- Branch: `chunk/p1-056-activation-prompt-helper`
- HEAD: `8571dbde8a13e34e3b8eadf29032c7a6655181ff`
- Working tree: clean before this SSoT doc update
- PR #27: `OPEN`
- Merge state: `CLEAN`
- CI `test`: `SUCCESS`

Because this file/handoff are being updated after that check, preserve any doc-only dirty changes you see and do not reset/clean/stash them blindly.

## GLM 5.3 — exact next work

### Step 1 — close WO-P1-056 safely

1. Run identity gate:
   - `git status --short`
   - `git branch --show-current`
   - `git rev-parse HEAD`
2. Check current GitHub truth:
   - `gh pr view 27`
   - `gh pr checks 27`
3. If PR #27 remains green + mergeable:
   - preserve/commit this SSoT documentation checkpoint if needed,
   - ensure PR #27 contains the intended docs/state,
   - merge PR #27,
   - switch/sync `main`,
   - verify clean state.
4. Mark WO-P1-056 `COMPLETE` only after merge evidence exists.

### Step 2 — start WO-P1-057

Create a bounded work order for **Serena Onboarding / Memory Presence Warning**.

Approved scope:
- selected project only,
- read-only detection of `.serena/memories/` presence / usable memory,
- explain that Serena onboarding triggers when no memories exist,
- show a `start new conversation` nudge after onboarding,
- reuse current project registry/path + existing UI,
- no new memory store,
- no mutation of target project,
- TDD + targeted/full regression + PR/CI.

Grounding: `docs/references/serena-fulldoc-implications.md`.

## Mandatory boundaries

- A-Wiki remains brain/policy/memory authority; do not duplicate its memory/work-order/claim/orchestration systems.
- MCP gateway hard enforcement remains **`DECISION_REQUIRED`** — do not implement it yet.
- CONNECTORS project rebind remains deferred behind its user-gated decision.
- Do not restart workers/tunnels merely to fix test environment.
- Keep work in resumable micro-steps and checkpoint `CURRENT-WORK.md` + `handoff.md` + active WO.

## Escalation rule

GLM 5.3 should do normal implementation/review itself.

Only if a genuinely hard, cross-cutting bug or architecture ambiguity prevents a safe bounded decision, STOP that micro-step, preserve repo state, and write a focused escalation prompt for **GPT-5.6 Sol UltraHigh**. Do not escalate routine coding/tests/UI work.
