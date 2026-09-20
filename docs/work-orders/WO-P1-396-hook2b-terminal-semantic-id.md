# WO-P1-396 — HOOK-2b canonical terminal semantic identity

Status: CLAIMED / READY_FOR_IMPLEMENTATION
Issue: #396
Identity schema: GITHUB_ISSUE_V1
Risk: R3 — concurrency / idempotency / durable execution evidence
Topology: CROSS_REPO

## Binding

- authority repo: `A:\GitHub\A-Wiki-Conductor`
- execution repo: `A:\GitHub\SunDayRemoteMCP`
- authority base: `61315b71d510ce8ba88498018bb6c1d76dab144d`
- accepted HOOK-2a authority SHA: `9afe16cd6b07a1175be47e70855734b86bc3afa8`
- accepted HOOK-2a SRM SHA: `587d281eac8182ce878dc4a87b810a81abd92432`
- claim: `WO-P1-396-HOOK2B-TERMINAL-SEMANTIC-ID-001`
- SRM remote: NONE / DEFERRED; do not create or publish one

Accepted Hook Contract blobs:
- prose: `941f9731f9665fe109451a14cdc2b737555be99a`
- schema: `d176fd5e6393af6f5619fad372ad59aa858391ee`

## Problem

HOOK-2a intentionally left `terminal-evidence-seen -> process.terminal`
unsupported. Multiple independently attached/recovered Supervisor sessions can
observe the same durable terminal outcome and each append its own native
observation row with a distinct row-level `hookEventId`.

Mapping those row identities would create multiple normalized terminal event
identities for one semantic process terminal.

## Settled design

EXTEND existing per-execution evidence only. Do not add an event store.

Add one small per-execution semantic identity anchor:

`terminal-hook-identity.json`

It contains only:
- `hookEventId`: true `hk-<uuid4hex>`;
- `occurredAt`: one finite epoch-millisecond timestamp chosen when terminal
  truth is first accepted for Hook observation.

This file is execution evidence/identity metadata, not task/project authority,
not a terminal outcome store, and not a Hook Bus. Existing `exit.json`,
`dispatch-failure.json`, and `interrupt-observed.json` remain the terminal
truth sources.

The anchor MUST be created only after current Supervisor logic has already
accepted one of those terminal truth paths and all existing liveness guards
have passed.

## Cross-process convergence

The current generic `writeOnce()` helper uses exists + rename and is not a
sufficient cross-process identity claim for this purpose.

Do NOT silently change generic `writeOnce()` semantics in this Work Order.

Implement a dedicated bounded helper on EvidenceStore using an OS-exclusive
create (`open(..., "wx")`) for the terminal Hook identity anchor:

1. read and validate an existing anchor if present;
2. otherwise generate one UUIDv4 Hook id and one finite timestamp;
3. attempt exclusive target creation;
4. winner writes/syncs/closes the small anchor;
5. an EEXIST loser reads and validates the winner's anchor;
6. malformed/corrupt anchor fails the Hook identity path closed.

A crash-created malformed anchor may degrade Hook observability; it MUST NOT
prevent execution terminalization or alter terminal truth.

## Native observation row

Whenever existing logic is about to append `terminal-evidence-seen` after
accepting terminal truth:

- best-effort obtain the canonical terminal anchor;
- if successful, append the observation row with:
  - its normal row-level `hookEventId` (unchanged append semantics);
  - `terminalHookEventId` = anchor hookEventId;
  - `terminalOccurredAt` = anchor occurredAt;
- if anchor acquisition fails, still append/finalize as existing execution
  behavior permits, but without inventing a fallback semantic identity.

Identity/observability failure MUST NOT block `finalizeRuntime()`.

Repeated observers may append repeated native observation rows, but all rows
for the same execution terminal MUST carry the same terminal semantic identity
and terminal occurrence timestamp once an anchor exists.

## Normalizer

Enable exactly:

`terminal-evidence-seen -> process.terminal`

For this mapping ONLY:
- normalized `event_id` MUST come from validated `terminalHookEventId`, not
  from the native observation row's own `hookEventId`;
- normalized `occurred_at` MUST come from validated
  `terminalOccurredAt`, not the observer row `t`;
- missing/malformed terminal semantic identity or timestamp fails typed and
  fail-closed;
- no session/pid/command/scope/raw terminal payload is emitted.

Existing mappings remain unchanged:
- `shim-spawned -> process.spawned`
- `recovered-attached -> execution.recovery`.

## Backward compatibility

- legacy native rows remain readable;
- old `terminal-evidence-seen` rows without semantic identity remain
  unnormalizable and fail typed;
- an execution with pre-existing durable terminal truth but no terminal Hook
  anchor MAY acquire the new anchor on a later safe observation/recovery,
  because this adds observability identity without rewriting terminal outcome;
- never rewrite `exit.json`, `dispatch-failure.json`, or
  `interrupt-observed.json`.

## SRM mutable scope ONLY

- `src/sunday/supervisor-evidence.ts`
- `src/sunday/supervisor.ts`
- `src/sunday/supervisor-hook-normalizer.ts`
- `test/test-sunday-supervisor.js`
- `test/test-sunday-supervisor-hook-normalizer.js`

Authority Work Order mutation is separate in A-Wiki.

## Forbidden

- generic `writeOnce()` behavior change
- terminal truth precedence/liveness policy change
- exit/dispatch-failure/interrupt schema rewrite
- known output-tail / ESRCH timing-race repair
- Hook Bus / STM / Monitor
- task / scheduler / claim / lease / retry / review / completion authority
- A-Wiki production filesystem dependency in SRM
- package/lockfile/tsconfig changes
- SRM remote creation/push
- reset/clean/stash/rebase/force-push

## RED-first acceptance

Prove before implementation:
1. two attached sessions observing one terminal outcome currently persist
   distinct row Hook identities and cannot normalize to one terminal identity;
2. no canonical terminal Hook anchor exists;
3. terminal normalization is currently typed unsupported.

Then add regressions proving:
1. exclusive concurrent anchor acquisition converges on exactly one UUIDv4
   `hookEventId` and one `occurredAt`;
2. two attached/recovered observers of one terminal outcome carry the same
   `terminalHookEventId` and `terminalOccurredAt`;
3. their normalized `process.terminal` envelopes have the same event_id and
   occurred_at;
4. observer row hook ids remain distinct;
5. separate executions get distinct terminal semantic identities;
6. malformed/missing anchor fields fail typed;
7. identity-anchor I/O failure does not block terminal execution/finalization;
8. legacy rows stay readable but fail terminal normalization typed;
9. the two previously enabled mappings are byte-for-byte semantically
   unchanged.

## Verification

- `npm run build`
- focused terminal identity/concurrency tests
- full hook normalizer suite
- relevant supervisor recovery/terminal tests, baseline-flake aware
- exact scope / `git diff --check`
- strict UTF-8 / no U+FFFD
- added-line fake-secret scan
- external Draft 2020-12 validation against exact accepted A-Wiki schema blob
- independent exact-SHA R3 review
- freeze exact authority + SRM SHA pair

No merge/publication of SRM is authorized. Authority closeout may merge only
after the exact local SRM candidate is accepted and post-fan-in compatibility
is proven.

## Replay safety

Recover durable pointer/process/result/Git before redispatch. RUNNING is never
duplicated. Unknown concurrent side effects fail closed.
