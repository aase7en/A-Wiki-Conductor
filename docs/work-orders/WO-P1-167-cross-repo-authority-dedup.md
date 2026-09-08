# WO-P1-167 — Cross-repo authority dedup gate

Status: IN_PROGRESS / CONTRACT_GUARD_IMPLEMENTED
Risk: R3 architecture / authority boundary
Owner: GPT1 integrator
Issue: A-Conductor #233
Upstream issue: A-Wiki #58
Base: b2eb9ef275f41efb6aa5b567a508569cf2641f35
Branch: docs/wo-p1-167-cross-repo-authority-dedup
Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo167-dedup

## Trigger

User observed that A-Wiki and A-Conductor appear to repeat the same orchestration work.
Live audit confirmed both intentional overlap and one actual split-authority defect class.

## Goal

Make the sibling boundary executable enough that future roadmap work cannot silently
create OWNER/OWNER control planes. Preserve A-Wiki as brain/policy owner and
A-Conductor as live runtime/control-plane owner.

## Current lane scope

Allowed:
- docs/contracts/a-wiki-a-conductor-integration.md
- tests/test_awiki_a_conductor_authority_contract.py
- DEFECT_LESSONS.md
- this work order

Forbidden:
- active P0-B4 source/test/task packet
- P0-B5/B6/ZRA source
- A-Wiki source mutation
- shared runtime/job/lease/review implementation
## Confirmed audit findings

1. A-Wiki exposes conductor status/gate/verify/claim/models/plan/review.
2. A-Wiki a-flow persists pipeline state in .tmp/a-flow.json.
3. A-Wiki a-claim persists TTL lease state in .tmp/agent-claims.json.
4. A-Wiki conductor claim directly writes durable COLLAB.md rows.
5. A-Conductor independently owns durable job state, WorkerLease, runtime mutation
   admission, scheduler/dispatch, checkpoint/recovery, execution evidence and GoalCloseout.
6. A-Wiki ReviewBus is already the accepted review lifecycle owner; A-Conductor must adapt.
7. During P0-B4, concurrent integrator sessions published/reconciled multiple task hashes
   before exact-hash fencing converged; safety held, but coordination work was duplicated.

## Classification

P0-B1/B2/B3 are not rejected as duplicates: they are runtime safety EXTEND/WRAP work.
P0-B4 may continue only as projection-only ADAPTER work.
P0-B5/P0-B6/ZRA source mutation is held until the owner-map audit is reconciled.

The upstream A-Wiki dual-claim issue is tracked separately as #58; this lane does not
choose its migration implementation on A-Wiki's behalf.

## Executable prevention

The existing integration contract now contains one machine-checked operational
authority table rather than a new registry.

Invariant:
- exactly one OWNER per capability;
- allowed peer roles: CONSUMER / ADAPTER / COMPATIBILITY_FALLBACK;
- OWNER/OWNER is forbidden;
- compatibility fallback requires a sunset condition.
## TDD evidence

RED on base contract with new regression:
- tests/test_awiki_a_conductor_authority_contract.py
- 3 failed
- missing authority-map sentinel
- missing OWNER/OWNER invariant
- missing fallback sunset / downstream hold wording

GREEN after contract update:
- same focused file: 3 passed

## Remaining verification before freeze

- run related contract/integration tests;
- compileall tests where applicable;
- git diff --check;
- UTF-8/no U+FFFD;
- added-line secret scan;
- exact scope audit;
- independent exact-SHA architecture review.

## Downstream gate

P0-B5, P0-B6 and ZRA-2/3/4 source mutation must not open solely because P0-B4
finishes. First reconcile Issue #233 and upstream A-Wiki #58 into a reviewed
owner/adaptor migration decision.

## Next safe action

Finish deterministic verification of this lane, freeze one candidate SHA, publish
PR without merging, and request exact-SHA architecture review.
