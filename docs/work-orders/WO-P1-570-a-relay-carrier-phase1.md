# WO-P1-570 — A-Relay Carrier Phase 1

Issue: #570
Parent: #568 / PR #569 (Phase 0 contract merged)
Topology: CONTROL_PLANE_ONLY
Risk: R3
Status: BOOTSTRAP / CLAIMED / SOURCE_MUTATION_PENDING_FULL_GATE

## Goal

Implement the smallest executable A-Relay carrier that makes the merged Phase 0
A-Sidecar/A-Relay contract usable without creating a second scheduler, task
store, claim/lease authority, retry engine, review authority, completion
authority, or SSoT.

A-Conductor remains canonical authority. The carrier stores and projects typed
receipt/evidence events only.

## Proven base

- origin/main base: `d15c55dc2b8e05f028357ddf2d7320cd3e456bd6`
- merged predecessor: #568 / PR #569
- read-only GLM-5.3 Flash shaping: `exec-munkk6ui-wd6lyxr0`
- shaping terminal: COMPLETED / verified exit 0 / harvested
- current bootstrap worktree:
  `/Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo570-sidecar-bootstrap`
- bootstrap branch: `docs/wo-p1-570-sidecar-relay-bootstrap`

## Reuse-before-build result

REUSE / WRAP patterns only:
- `src/a_conductor/control_events.py` — event-id + typed-error precedent only.
- `src/a_conductor/lifecycle_journal.py` — validate-before-append/journal precedent only.
- `docs/contracts/hook-contract-v1.md` — at-least-once/dedupe/bounds precedent.
- `docs/contracts/codex-nightshift-resume-adapter-v1.md` — receipt-not-command /
  forbidden sensitive fields / pointer-only precedent.
- `src/a_conductor/delegated_run_artifacts.py` and A-Faster durable-lane contract —
  evidence-pointer grammar; no new run store.
- `src/a_conductor/context_rollover_guard.py` — context-pressure vocabulary only.
- accepted CoinTH quota hook/probe — provider preflight remains outside the carrier.
- `src/a_conductor/zero_relay_review_execution.py` — execution identity/binding precedent only.

Do not modify any of those shared seams in this slice.

## Claim

claim_ref: `WO-P1-570-ARELAY-CARRIER-MAC-001`
owner/integrator: ChatGPT A-Sidecar
preferred author: Kilo / CoinTH GLM-5.3 MAX through `sunday_dispatch`
preferred reviewer: separate GLM-5.3 MAX read-only exact-SHA execution

## Exact mutable scope

NEW only:
- `src/a_conductor/sidecar_relay.py`
- `tests/test_sidecar_relay.py`
- `docs/work-orders/WO-P1-570-a-relay-carrier-phase1.md`

Everything else is READ ONLY.

Any required edit outside these paths is `SCOPE_EXPANSION_REQUIRED` and must stop
for integrator reconciliation.

## Explicit forbidden / collision scope

Do not modify:
- #498 / PRE_DISPATCH / hook hotspot:
  `src/a_conductor/pre_dispatch_guard.py`,
  `src/a_conductor/control_hook_adapter.py`, `CURRENT-WORK.md`, `handoff.md`.
- #549 / #550 A-Faster auto-refill surfaces.
- #551 / #552 claim-reader/task-binding surfaces.
- `.codex/hooks/**`.
- #547 reserved `hook_bus.py` / `hook_stm.py` surfaces.
- `control_events.py`, `lifecycle_journal.py`, `worker_lease.py`, provider/admission stores.
- `zero_relay*.py`.
- Phase 0 contract/skill files.
- A-Wiki or SunDayRemoteMCP.
- any live Codex SQLite/lock state.

## Required behavior

Implement a stdlib-only dumb carrier:
- immutable/frozen relay envelope representation;
- closed allowlist for the 11 Phase 0 event families;
- strict mandatory-field validation and exact when-applicable binding validation;
- append-only strict UTF-8 LF JSONL;
- bounded envelope size <= 65536 bytes;
- evidence refs <= 16 unique durable pointers;
- result receipt families require at least one evidence ref;
- dedupe-on-read by EVENT_ID;
- deterministic per-producer ordering;
- torn final line tolerated/skipped deterministically;
- no rewrite/delete semantics;
- no network/subprocess/provider calls;
- no scheduler/claim/task/review/merge/completion behavior;
- minimal module-local CLI: validate / emit / tail;
- cross-platform path values are opaque/device-tagged evidence, never cross-device resolved.

## Typed failures

At minimum:
- `RELAY_ENVELOPE_INVALID`
- `RELAY_EVIDENCE_MISSING`
- `RELAY_EVENT_TOO_LARGE`
- `RELAY_EVENT_DUPLICATE` where material
- `RELAY_IO_ERROR`

Malformed/unbound mutation-relevant events fail closed as evidence and never become commands.

## GLM durable evidence rule

`GLM_RESULT_RECEIPT` and `SIDECAR_RESULT_RECEIPT` require durable
`EVIDENCE_REFS`.

The carrier validates the pointer presence only. It never dereferences or
promotes a pointer to authority. Exact execution/claim/worktree binding is
verified by the consumer/integrator against existing durable execution and claim
authority.

## Risk / failure model

R3 because this adds durable receipt state and replay/idempotency behavior.

Loss/corruption of the relay carrier degrades observability only. Canonical task,
claim, Git and execution truth remain authoritative.

Duplicate delivery is expected and must be idempotent on EVENT_ID.
Out-of-order delivery is tolerated.
A torn final JSONL line must not corrupt earlier valid events.
Replay re-derives observations only; replay never grants authority.

## Tests

RED-first focused tests must cover:
1. all 11 families accepted; unknown family rejected;
2. required fields and mutation-relevant binding requirements;
3. event-id minting/validation;
4. append-only UTF-8/LF JSONL + 65536-byte cap;
5. torn final line;
6. dedupe-on-read and stable ordering;
7. result receipts require evidence refs;
8. sensitive/executable-content rejection;
9. typed CLI exit behavior;
10. stdlib-only / no network / no subprocess / no authority methods;
11. Windows/macOS path evidence remains opaque;
12. related `test_control_events.py` and `test_lifecycle_journal.py` remain green.

## Acceptance

- exact 3-path delta only;
- `git diff --check`;
- strict UTF-8/no CRLF/trailing whitespace checks;
- focused tests green;
- related tests green;
- work-order identity checks green;
- freeze exact candidate SHA;
- independent fresh-quota GLM-5.3 MAX read-only review on exact SHA;
- exact-head CI;
- integrator acceptance / merge / post-main verification.

## GLM offload

`GLM_OFFLOAD_ASSESSMENT=DISPATCHED`

Reason: bounded R3 implementation/test work is highly suitable for GLM-5.3 MAX.
GPT/ChatGPT remains authority/fan-in/acceptance only.
