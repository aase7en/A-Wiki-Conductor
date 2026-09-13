# WO-P1-170 — Custom Provider Settings Roadmap Capture

Date: 2026-09-10
Owner: GPT-5.6 Sol integrator
Status: ROADMAP_CAPTURED / DRAFT_PR_243 / CLAIM_RELEASED / DEFERRED_AFTER_ZRA-4
Priority: P2 DEFERRED / POST-ZRA-4
Risk: R1 docs-only
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo170-provider-settings-roadmap`
Branch: `docs/wo-p1-170-provider-settings-roadmap`
Base: `origin/main@577d9483720c857a89a5d2c9ea9359f9c0aa50b5`
Classification: `REUSE + EXTEND`

## User outcome

Capture a future Settings/Advanced experience where an operator can configure model providers with the familiarity of modern agent tools while preserving A-Sunday Conductor's existing provider, secret, authorization, admission, and routing authorities.

Target operator flow:

`Add Provider -> Base URL -> API format -> credential input -> model list -> Test -> Enable -> eligible routing`

The UI should be easy for a non-developer to use, but must not make configuration equivalent to runtime readiness or authorization.

## Priority decision

This roadmap item is intentionally deferred. The current P0 remains `WO-P1-155` / Zero-Relay Accelerator.

Do not consume a mutable implementation lane for this feature until at least `ZRA-4` bounded-parallel no-human-relay execution is accepted, unless a later explicit user decision changes the dependency order.

Primary success metric before this feature starts remains:

`human relay actions per accepted external-agent task = 0`

The user must not have to relay prompts/results among GPT, GLM, Astra/Codex, or other accepted agents for each micro-task.

## Reuse-before-build decision

Reuse and extend the existing accepted AHA provider fabric:

- AHA-1 provider/harness contracts;
- AHA-2 secure provider configuration;
- AHA-6A/AHA-6A.1 runtime assembly and provider admission;
- AHA-7A truthful provider operator read model;
- AHA-7B Models & Agents display/read service;
- WO-P1-127 Edit / Disable / Enable / Test actions;
- existing `Models & Agents` Settings surface;
- existing A-Wiki private secret-reference resolution.

Do **not** create a second provider registry, router, secret store, readiness authority, quota authority, or scheduler.

## Future product slice — AHA-7C Custom Provider Settings Console

The Settings/Advanced `MODELS & AGENTS` surface should eventually support:

1. **Add Provider** with operator-defined display name and stable provider identity.
2. **Base URL** entry with validation and explicit transport/security policy.
3. **API format / protocol family** selection, initially from supported adapters rather than arbitrary unvalidated strings. Candidate families include Anthropic Messages and OpenAI-compatible APIs; Gemini/local adapters are added only when their contracts exist.
4. **API credential entry** through a masked/transient input. The entered secret must be moved into the approved private secret boundary and provider metadata must retain only a credential reference. Never persist plaintext credentials in Git, public project files, logs, task packets, evidence, or ordinary UI state.
5. **Model list management**: add/edit/remove model IDs and friendly names, with optional capabilities/metadata such as vision support, context limits, reasoning/effort class, and provider-specific model reference where supported.
6. **Enable / Disable** without deleting configuration.
7. **Test Connection** through the accepted background provider observation path; no direct network calls from the UI thread.
8. **Truthful status** distinguishing at least `CONFIGURED`, `READY`, `AUTHORIZED`, `ADMITTED`, `DISABLED`, and typed failure/blocker states.
9. **Selection visibility** showing why a provider/model was chosen or rejected for a task.
10. **Safe editing** with generation/CAS and in-use fencing so active executions cannot be silently rebound to changed provider identity.
11. **Provider templates plus Custom** so common providers are easy to configure without making any vendor an architectural dependency.
12. **Restart durability**: safe provider metadata survives restart while secrets remain in the approved private secret boundary.

## UX direction

Use the existing Sunday Family visual language and existing Settings window. Do not copy another vendor UI pixel-for-pixel and do not create a second dashboard.

Recommended layout:

```text
MODELS & AGENTS

Providers
  [Z.ai]
  [GLM / CoinTH]
  [OpenRouter]
  [Google]
  [Local]
  [+ Add Provider]

Selected Provider
  Name              [................]
  Base URL          [................]
  API format        [Anthropic Messages v]
  API credential    [••••••••••••••••] [Replace]
  Status            CONFIGURED / READY / AUTHORIZED / ...
  [Test] [Enable/Disable]

Models
  GLM-5.3           [Edit] [Remove]
  GLM-5.3-Flash     [Edit] [Remove]
  [+ Add Model]
```

The normal main command-center screen stays uncluttered; detailed configuration belongs in Settings/Advanced.

## Security / authority invariants

- `API key entered` does not mean `AUTHORIZED`.
- `Provider configured` does not mean `READY`.
- `Test passed` does not bypass task trust/egress policy, admission, quota, or ownership gates.
- never reveal an existing full secret back into the UI;
- secret replacement must be explicit and separately authorized where required;
- endpoint/protocol/model edits must invalidate or generation-fence stale observations/admissions;
- unknown protocol/provider capability fails closed;
- no UI action may bypass Zero-Relay execution authority or the existing scheduler/lease model.

## Dependency gate

Implementation status is `DEFERRED` until:

1. WO-P1-168 corrective Claude-harness gate is accepted/merged/closed;
2. Zero-Relay production path is accepted through ZRA-1/2/3;
3. ZRA-4 bounded parallel lanes are accepted, proving the user no longer acts as GPT↔GLM/GPT reviewer message bus;
4. the current AHA-7/provider contracts are re-pinned from actual main before implementation.

After those gates, split AHA-7C into bounded implementation work orders rather than one broad UI rewrite.

## Likely implementation slices after dependency release

- AHA-7C.1: protocol-family/API-format contract and safe provider create/update facade;
- AHA-7C.2: secure credential replacement/persistence boundary;
- AHA-7C.3: model-list CRUD and capability metadata;
- AHA-7C.4: Settings UI composition and accessibility/i18n;
- AHA-7C.5: connection test/readiness display plus restart/adversarial verification.

Exact slicing must be re-evaluated against future main; these names are planning placeholders, not claims.

## Acceptance criteria for this roadmap capture

1. `PROJECT-PLAN.md` records AHA-7C as a future provider-neutral Settings feature.
2. The AHA accelerator roadmap records the concrete ZCode/Hermes/OpenCode-class configuration UX semantics without weakening secret/provider authority.
3. Both documents explicitly defer implementation until after ZRA-4 unless the user reprioritizes.
4. No product source, provider store, runtime, secret, or global continuity projection is modified by this WO.
5. Diff contains no credential values or private data.

## Mutable scope

- `docs/work-orders/WO-P1-170-provider-settings-roadmap.md`
- `PROJECT-PLAN.md`
- `docs/plans/2026-08-28-sunday-family-agent-harness-accelerator.md`

## Forbidden scope

- all `src/` and `tests/` files;
- private Drive/secrets;
- `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`, `AGENT_TASKS.md`;
- WO-P1-168/169 branches/files;
- Zero-Relay production source or active R4 candidate;
- merge/release operations for PR #242.

## Verification

- exact scope audit;
- `git diff --check`;
- UTF-8/readability check;
- sensitive-token/pattern scan on changed docs;
- remote/open-PR overlap recheck before push;
- independent review is not mandatory for this R1 docs-only capture unless the final diff expands into security/architecture authority rather than documenting existing constraints.

## Verification checkpoint — 2026-09-10 Windows

- isolated worktree is on `docs/wo-p1-170-provider-settings-roadmap@577d9483720c857a89a5d2c9ea9359f9c0aa50b5` from current `origin/main`;
- open-PR overlap check found no active PR touching either roadmap target;
- changed scope is exactly this WO plus `PROJECT-PLAN.md` and the AHA accelerator roadmap;
- `git diff --check` = PASS;
- strict UTF-8 read = PASS;
- changed-doc sensitive-token/value pattern scan = PASS / no secret values found;
- no `src/`, `tests/`, private Drive, active WO168/169, or global continuity projection mutation;
- roadmap now records AHA-7C as deferred behind ZRA-4 so it cannot silently displace the user's P0 Zero-Relay goal;
- first captured commit `011f11660649c2d1b6cab28fe5473829c53433e0` was pushed and Draft PR #243 opened against `main`;
- PR #243 is intentionally non-blocking and not merge-authorized while WO-P1-168 R4 / PR #242 remains frozen at its independent-review gate;
- this docs-only mutable claim is released after this checkpoint; future edits require a fresh mutation gate.

## Next safe action

Commit/push this docs-only roadmap capture and preserve it as a non-blocking draft PR without moving `main` ahead of the frozen WO-P1-168 R4 base. Release this docs claim, then return execution focus to WO-P1-168 / Zero-Relay and its independent-review gate.