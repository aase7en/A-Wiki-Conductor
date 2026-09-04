# Parallel 4-Lane Coordination — 2026-09-04

Status: ACTIVE
Repository: `A:\GitHub\A-Wiki-Conductor`
Base authority at lane creation: `origin/main@68079e3d00047ca9432f0aefe3ad667f892614d0`
Purpose: accelerate the frozen Fast Roadmap with 2 GPT chats + 2 GLM/ZCode chats without mutable-scope overlap.

## Global invariants

- Durable repository/project state is SSoT; chat memory is not authority.
- Every lane must re-read `00-AGENT-ENTRY.md`, `PROJECT-GRAPH.yaml`, repo-local `AGENTS.md`, relevant work order, `COLLAB.md`, `CURRENT-WORK.md`, and `handoff.md` before mutation.
- No lane may take a dirty/claimed worktree or overwrite another lane's scope.
- Max mutable lanes: 3; read-only review lane is separate.
- GPT-A is final integration/architecture/acceptance/merge authority for this coordination window.
- GLM/ZCode output is evidence/claim until reconciled against exact repo state and deterministic verification.
- No broad-kill Python/Node/ZCode/Serena/tunnel-client. Exact PID + process identity only.
- No live DB mutation until exact candidate migration gate passes.
- No global ESET disable.
- No blind replay after ambiguous execution.
- Frozen roadmap order remains authoritative; parallel preparation must not reorder merge/release gates.

## Lane GPT-A — Integrator / architecture / review / merge gates

Owner: primary GPT chat
Mutation surface: coordination/review evidence only unless a dedicated safe repair lane is explicitly claimed.
Current responsibilities:

1. reconcile all external lane outputs against actual HEAD/diff/tests;
2. maintain this coordination SSoT;
3. review WO156 R3 architecture and accept/reject exact GLM candidate;
4. own clean build / migration / installed-chaos acceptance planning;
5. own PR #208 exact-SHA final decision after qualifying independent review;
6. enforce frozen roadmap merge order;
7. after PR208 merge, release next ZRA implementation slice to GLM-B.

Forbidden:
- do not edit GPT-B PR #209 branch while GPT-B owns it;
- do not mutate GLM-A WO156 source worktree;
- do not mutate PR208 candidate during independent review;
- do not claim installed E2E from direct coordinator harness.

Current GPT-A evidence:
- WO156 candidate `55de87f04dde7b0682026ef2c45ce17096de66db`: 145/145 required regression PASS, compileall PASS, diff-check PASS; duplicate durable recovery authorities removed.
- Blocking finding: `worker_resilience.py` policy has no production caller outside itself/tests; direct `chaos_w1.py` uses `_MemStore` + direct coordinator invocation, so it is CORE_PROCESS_PROOF, not installed E2E.
- Blocking semantic finding: transient OWNERSHIP_BLOCKED/TASK_AMBIGUOUS must not call durable manual-stop `ConnectorRecoveryCoordinator.suppress()`.
- Clean `origin/main@68079e3` isolated build:
  - Portable SHA-256 `26817C8EB8F2BF8AA8C5898C5640C033CBC5CE4809D9E276FF05251028CE4526`
  - Setup SHA-256 `261A9D87F0B34ECC046981867788D2003504E3333CE2CD84B45D4694ACC509D2`
  - Portable smoke exit 0 on isolated DB
  - archive contains `a_conductor.connector_recovery`, `serena_config_store`, `desktop_control`, `local_instances`.

## Lane GPT-B — Live tunnel-client canary / PR #209 operational evidence

Owner: second GPT chat
Branch: `docs/wo-p1-156-worker-tunnel-incident`
PR: #209
Allowed mutable scope:
- PR #209 documentation/incident/continuity evidence;
- W1-only operational canary config, with exact backup/rollback and fresh ownership checks.

Forbidden:
- do not edit WO156 source worktree;
- do not edit PR208 candidate;
- do not touch W2/W3/W5 tunnel paths/processes;
- do not replace shared 0.0.11 binary while fleet workers use it;
- do not globally disable ESET.

Current observed state:
- latest remote PR #209 commit observed by GPT-A: `c730ea7d9de3e22b8f5a19358e897b8295270ece` at the time of canary verification; later commits may exist and must be re-fetched.
- W1-only canary path:
  `C:\AI\dwb-serena-tunnel-starter\canary\0.0.14\tunnel-client\tunnel-client.exe`
- candidate SHA-256:
  `FCC85A69EC0AD82518E4F8964F60C45E31787957782A0FC9C1B0C44E82D61B9B`
- W1 process observed after switch:
  tunnel PID 11956 -> Serena child; remote MCP recovered.
- W2/W3/W5 remain on shared 0.0.11.
- This is compatibility/stability evidence, not proof that 0.0.11 is the sole initiating cause.

GPT-B next safe action:
- monitor bounded canary stability and collect exact exit/reconnect evidence;
- do not expand to fleet until GPT-A approves after WO156/source/deployment gates.

## Lane GLM-A — WO156 production wiring repair

Owner: GLM/ZCode chat A
Worktree:
`A:\GitHub\_worktrees\A-Wiki-Conductor-wo156-worker-resilience`
Branch:
`fix/wo-p1-156-worker-resilience`
Expected base for next repair:
`55de87f04dde7b0682026ef2c45ce17096de66db`

Allowed mutable scope:
- `src/a_conductor/worker_resilience.py`
- minimum existing production integration seam if justified, especially `desktop_control.py`
- focused WO156/recovery/provider tests
- WO156 work-order checkpoint
- no other roadmap hotspot.

Goal:
- wire only justified policy into existing production health/recovery path;
- remove dead policy with no production consumer;
- preserve ONE recovery authority;
- temporary safety holds must not persist manual-stop suppression;
- 429/404/remote-session state must remain at the correct provider/session authority layer;
- real SQLite + production-path tests, not direct coordinator-only harness.

Acceptance:
- exact new SHA;
- production call graph;
- no duplicate authority;
- deterministic tests;
- direct chaos correctly labeled CORE_PROCESS_PROOF unless installed app path is actually exercised;
- stop at frozen candidate, no merge/main push.

## Lane GLM-B — PR #208 independent exact-SHA review

Owner: GLM/ZCode chat B
Mode: READ-ONLY REVIEW
Candidate worktree:
`A:\GitHub\_worktrees\A-Wiki-Conductor-wo154-fast-workflow`
Base:
`68079e3d00047ca9432f0aefe3ad667f892614d0`
Candidate:
`0fd540c622d4539a2e809b8a441661896179f2ad`
PR: #208
CI: green on exact candidate in last GPT verification.

Allowed:
- read exact candidate/base/diff;
- run non-mutating deterministic checks if needed;
- write review result only to ignored/scratch review artifact outside candidate-tracked files.

Forbidden:
- no tracked file edits;
- no commit/rebase/merge;
- no PR mutation;
- no self-approval language beyond review verdict;
- no chain-of-thought output.

Review focus:
- Fast Execution risk tiers R0-R3;
- repo/ownership/secret/destructive gates;
- exact-SHA independent review semantics;
- bounded repair and CI/release gates;
- WIP/parallel lane limits;
- SSoT truthfulness;
- no self-approval/model-name authority loopholes;
- Zero-Relay frozen priority and ordering;
- WO155 dependency on PR208 acceptance/merge.

Output:
- exact base/head/diff identity;
- PASS or BLOCKED;
- P0/P1/P2 counts;
- only blocking findings with file/section/evidence and minimal repair;
- no stylistic/nit findings unless they create policy ambiguity.

After qualifying PASS:
- GPT-A independently reconciles result;
- PR208 may proceed through merge gate.
After PR208 merge:
- GLM-B may be reassigned to WO155/ZRA R3 repair on a freshly reconciled branch.

## Frozen merge / execution order

`PR #208 -> WO156 reliability close gate as required for stable execution -> ZRA-0..4 -> WO152/#204 -> ODP-1..8 -> ZRA-5 -> ODP-9 -> WO096 -> v0.7 stable -> cleanup/SSoT`

Reliability work may run in parallel because it protects the execution substrate, but it must not silently reorder product-roadmap acceptance.

## Cross-lane handoff protocol

Every lane result must report:

- Lane ID
- Task/work order
- repo/worktree/branch
- BASE SHA
- NEW/FROZEN SHA or READ-ONLY candidate SHA
- dirty state
- changed files
- tests/checks
- blockers
- ownership/overlap statement
- next safe action

Before changing lane ownership:
- persist checkpoint;
- prove no uncheckpointed mutation;
- release claim explicitly.
