# WO-P1-475 — Multi-Session Provenance & Collision Hardening

Status: DESIGN / ROADMAP
Issue: #475
Topology: CONTROL_PLANE_ONLY for this governance slice; later MSP-1 may become CROSS_REPO when the ChatGPT-facing MCP ingress is proven to live in SunDayRemoteMCP.
Risk: R3 architecture / concurrency / authority
Base: `2867797ca991e249c97999b6f0cebff4d12143a5`
Claim: `WO-P1-475-MSP-ROADMAP-WINDOWS-001`

## 1. Goal

Make the user's normal 2–4 ChatGPT-session A-Faster workflow first-class and collision-resistant without creating a second task, claim, scheduler, session-lock, or completion authority.

The human may open multiple ChatGPT sessions and issue the same high-level instruction such as "continue the roadmap with A-Faster" or introduce a new idea in a fresh session. The system must recover actual durable state and choose ATTACH / OBSERVE / CLAIM NEW LANE / READ-ONLY RESEARCH instead of blindly dispatching duplicate writers.

## 2. Existing authorities to preserve

- A-Wiki Work Order / `repo_coordination_claim` remains project mutation authority.
- A-Faster `LANE_REF`, `DELEGATED_RUN_ID`, binding digest, durable pointer and replay recovery remain delegated-execution identity.
- A-Conductor mutation gate / accepted lease mechanics remain the execution fencing substrate where applicable.
- Hook Contract v1 `correlation_id`, `causation_id`, and `command_ref` remain operation correlation.
- Global WIP remains one project-wide budget: max 3 mutable + 1 independent review unless an accepted WO overrides it.
- `NEW SESSION != NEW TASK`.
- `1 MUTABLE HOTSPOT = 1 MUTATION OWNER`.

Chat/session identity is provenance only. It never grants mutation, merge, review or completion authority.

## 3. Proven gaps

### MSP-0 — Collision-proof delegated-run artifact identity

Current logical run identity is already strong because `DELEGATED_RUN_ID` contains a random component, but physical artifacts still use `attempt-NNNN/`. Independent ChatGPT sessions can choose the same ordinal and overwrite `task.md`, `runner-config.json`, `execution-pointer.json`, result or log artifacts.

Target:
- physical attempt path includes an immutable unique suffix derived from the delegated run identity;
- attempt ordinal remains human-readable/recoverable but is not uniqueness authority;
- recovery enumerates attempts deterministically and can map each directory back to one immutable delegated run identity;
- old `attempt-NNNN/` paths remain readable for migration/recovery;
- two sessions cannot overwrite each other's task/config/pointer even if collision admission fails.

Candidate shape:

`runs/<WO>/<lane>/attempt-0001-<run-suffix>/`

Exact naming must be frozen by the implementation WO; this roadmap does not make the suffix format protocol authority.

### MSP-1 — Chat-origin provenance

Add privacy-preserving non-authoritative origin metadata to existing hook/execution evidence.

Candidate fields:
- `origin_surface`
- `origin_chat_session_ref`
- `origin_command_ref`

Rules:
- use a derived/HMAC/reference form where a platform exposes a session/conversation identifier;
- do not persist raw platform IDs unless an accepted privacy contract explicitly allows it;
- chat alias/title is display metadata only;
- origin fields are excluded from task/claim mutation authority and must not make a legitimate takeover from another chat fail binding;
- hook `command_ref` / causation should be reused rather than inventing a parallel command ID namespace when the existing contract is sufficient.

### MSP-2 — Atomic multi-session hotspot admission

Close the observe -> dispatch race across multiple ChatGPT integrators.

Required behavior:
- reuse accepted A-Wiki claim identity plus existing A-Conductor mutation/lease/fencing mechanics;
- no `session-lock.db`, browser lock, Extension lock, or new shadow claim store;
- one transactional/fenced admission winner per mutable hotspot;
- loser receives typed `CLAIM_CONFLICT` / `ATTACH_EXISTING` / equivalent accepted outcome and performs no material writer launch;
- release/recovery permits a different chat session to take over after actual authority is released;
- unknown or ambiguous admission state fails closed.

### MSP-3 — Session/Lane observability

Extend the accepted Monitor read model so the operator can trace:

`Chat origin -> command -> WO/claim -> lane -> delegated run -> model/harness session -> device/PID/SHA`

The UI may show a friendly chat alias, but alias/session provenance never owns the lane.

## 4. Dependency order

1. **MSP-0 first** — remove physical artifact overwrite independently of origin metadata.
2. **MSP-1 second** — bind origin provenance through existing Hook/harness/MCP surfaces.
3. **MSP-2 third** — R3 atomic admission using existing claim authority; race/fault tests mandatory.
4. **MSP-3 fourth** — expose the accepted read model through MON/UI.
5. Goal-runner / Chrome Extension / Tampermonkey surfaces may consume accepted MSP contracts but may not create independent scheduler/claim/lock authority.

MSP-0 and MSP-2 are blockers for intentionally scaling same-project ChatGPT control sessions beyond the current recovery-based coordination model.

## 5. Goal-runner relationship

The desired operator experience is a one-goal / continue-without-watching workflow:

1. human states a durable goal once;
2. session recovers actual roadmap/claims/runs;
3. accepted control plane selects the next READY bounded action;
4. A-Faster attaches to existing work or claims a disjoint lane under WIP;
5. delegated execution runs/harvests/verifies;
6. accepted completion advances to the next READY node;
7. session surfaces only real blockers/decisions/completion.

A Chrome Extension, Web UI, desktop UI, or Tampermonkey userscript is an operator surface only. It may submit a typed goal/continue command through the accepted Command Gateway when that gateway exists. It must not click-loop ChatGPT as a hidden scheduler, invent task state, bypass WIP/claim gates, or treat browser-tab state as execution truth.

Before ACT-1 acceptance, any browser helper remains a thin command/presentation adapter to existing accepted goal/task pointers.

## 6. Mandatory adversarial acceptance

At minimum:

### Same-hotspot race
Two independent ChatGPT sessions observe the same READY mutable hotspot concurrently.
- exactly one becomes mutation owner;
- exactly one material writer is launched;
- loser gets typed attach/conflict;
- no shared run artifact is overwritten.

### Disjoint-lane parallelism
Two sessions claim non-overlapping READY hotspots.
- both may run within the global WIP budget;
- origin provenance remains distinct;
- fan-in uses accepted project authority.

### Chat loss / takeover
- writer continues after chat loss if execution is still live;
- fresh chat recovers/attaches instead of redispatching;
- after valid release, a different chat may acquire the lane;
- origin change does not invalidate task binding.

### Attempt identity
- same attempt ordinal from two sessions produces distinct immutable artifact paths;
- recovery maps each path to exactly one delegated run;
- stale/partial pointer from one run cannot overwrite or masquerade as another.

### Privacy
- raw platform session/token values do not leak to normal durable logs/issues;
- monitor shows only accepted derived references/aliases.

### Failure
- ambiguous claim/lease state => no writer;
- stale WIP/read model => no writer until authoritative recheck;
- browser/Extension disconnect does not imply execution failure;
- monitor/STM loss cannot change mutation authority.

## 7. Roadmap integration

This WO extends:
- `docs/plans/2026-09-19-a-faster-hook-stm-observability-roadmap.md`
- `docs/plans/2026-09-04-zero-relay-accelerator-roadmap.md`

It does not create a third roadmap.

Implementation is split into separate bounded WOs after roadmap acceptance:
- MSP-0 run-artifact identity;
- MSP-1 chat-origin provenance;
- MSP-2 atomic hotspot admission;
- MSP-3 monitor projection/UI;
- goal-runner operator surface only after the required MSP/ACT contracts are ready.

## 8. Current roadmap-slice acceptance

This governance slice is accepted only when:
- both existing roadmaps record the dependency and authority boundaries consistently;
- diff is limited to this WO + the two roadmaps;
- strict UTF-8/no-BOM and `git diff --check` pass;
- work-order identity test passes;
- independent read-only architecture challenge finds no P0/P1/P2 blocker;
- exact candidate is merged before opening source implementation WOs.

Until then:

`SAFE_TO_MUTATE_MSP_SOURCE = NO`
