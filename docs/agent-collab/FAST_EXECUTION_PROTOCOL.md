# Fast Execution / Risk-Tier Delivery Protocol

Status: BINDING DELIVERY POLICY
Owner: GPT integrator / A-Sunday Conductor coordination layer
Introduced by: `WO-P1-154`
Goal: increase effective delivery throughput without reducing final assurance.

## 1. Non-negotiable invariants

Fast mode removes repeated ceremony. It does not remove:
- exact repository/worktree/branch/HEAD identity before mutation;
- known dirty-state ownership and non-overlapping mutable scope;
- secrets/credential protection;
- destructive/high-impact approval gates;
- deterministic acceptance evidence;
- recovery/idempotency handling where replay may be unsafe;
- independent review, E2E, release verification, or post-merge proof when the task risk requires them.

If identity, ownership, authority, or replay safety is uncertain: `SAFE_TO_MUTATE = NO`.

## 2. Risk tiers

Choose the **lowest tier that truthfully covers blast radius**. Escalate immediately when actual scope crosses a higher-risk boundary.

| Tier | Typical work | Default assurance path |
|---|---|---|
| `R0 DOCS` | wording, roadmap capture, comments, non-binding operator docs, status-only metadata | gate -> edit batch -> diff/UTF-8/link/scope checks -> merge/closeout as required |
| `R1 LOW` | isolated helper, fixture, small UI behavior, mechanical refactor, deterministic tooling | gate -> implement batch -> targeted tests -> freeze candidate -> self/diff review -> CI only if branch policy requires it -> merge |
| `R2 NORMAL` | bounded feature, schema projection, adapter, persistence-neutral business logic, multi-file behavior | gate -> exact task contract -> implement -> targeted+related tests -> adversarial batch -> freeze SHA -> assurance packet -> independent review -> bounded repair -> exact-head CI -> merge |
| `R3 CRITICAL` | auth/authorization, secrets, process ownership, concurrency, durable state, retry/idempotency, provider admission, protocol/schema authority, installer/release, high-blast-radius shared state | full repo/ownership gate -> plan/claim -> RED/implementation -> targeted+related -> adversarial/fault injection -> frozen SHA -> independent review -> full regression/E2E as applicable -> exact-head CI -> merge -> post-main/release verification |

### Automatic escalation triggers

Escalate to at least `R2` when work changes a shared contract, serialized format, durable store semantics, cross-component integration, or multiple mutable hotspots.

Escalate to `R3` when work affects:
- authorization/security/trust boundaries;
- credentials/secrets or external-provider authority;
- process/PID ownership or destructive operations;
- concurrency, leases, retries, deduplication, idempotency or ambiguous outcomes;
- release/installer/update path;
- durable task/graph state or protocol authority;
- safety-critical fail-open/fail-closed behavior.

A task may not be downgraded merely because tests currently pass.

## 3. Core execution loops

### R0 — docs/admin loop

```text
RECOVER ACTUAL STATE
-> SCOPE/OVERLAP GATE
-> EDIT AS ONE BATCH
-> DIFF + UTF-8 + LINK/SCOPE CHECK
-> CHECKPOINT / MERGE
```

No independent model review is required unless the document changes binding architecture, security, release policy, or acceptance criteria; such work is R2/R3, not R0.

### R1 — low-risk implementation loop

```text
RECOVER + GATE
-> IMPLEMENT BATCH
-> TARGETED TESTS
-> FREEZE CANDIDATE
-> DIFF/SELF REVIEW
-> REQUIRED CI
-> MERGE/CLOSEOUT
```

Do not run full-repo tests after every micro-edit unless a failure indicates broad coupling.

### R2 — normal feature loop

```text
RECOVER + GATE
-> TASK CONTRACT
-> IMPLEMENT BATCH
-> TARGETED + RELATED TESTS
-> ADVERSARIAL BATCH
-> REPAIR ALL CONFIRMED FINDINGS ONCE
-> FREEZE CANDIDATE SHA
-> ASSURANCE PACKET
-> INDEPENDENT EXACT-SHA REVIEW
-> BOUNDED REPAIR/REREVIEW IF REQUIRED
-> EXACT-HEAD CI
-> MERGE + CHECKPOINT
```

### R3 — critical loop

```text
RECOVER SSoT + ACTUAL RUNTIME/GIT
-> FULL AUTHORITY/OWNERSHIP/REPLAY-SAFETY GATE
-> PLAN + CLAIM + FAILURE MODEL
-> RED / IMPLEMENTATION
-> TARGETED + RELATED REGRESSION
-> ADVERSARIAL / RACE / FAULT / REALISTIC E2E AS APPLICABLE
-> FREEZE CANDIDATE SHA
-> ASSURANCE PACKET
-> STRONGEST-INDEPENDENT REVIEW
-> REPAIR + EXACT-SHA REREVIEW
-> FULL/RELEASE REGRESSION AS APPLICABLE
-> EXACT-HEAD HOSTED CI
-> MERGE EXPECTED SHA
-> POST-MAIN / LIVE / RELEASE VERIFICATION
-> CLEANUP + SSoT CLOSEOUT
```

## 4. Frozen Candidate rule

Independent reviewers review a stable candidate, not a stream of intermediate commits.

A candidate becomes `FROZEN` when:
- planned implementation is complete;
- targeted/relevant tests are green;
- known adversarial findings have been batched and repaired;
- scope/secret/diff checks are clean;
- exact candidate SHA is recorded.

Any production-code repair after review creates a new candidate SHA. Re-review should be **focused on changed trust/behavior boundaries plus prior blocking findings**, expanding to full rereview only when the repair has broad blast radius.

Reviewer independence is real, not nominal: the candidate author/integrator cannot be the sole independent reviewer. Prefer a separate model/provider/session/lane with read-only scope and exact-SHA evidence. If no independent reviewer is currently available for an R2/R3 gate, record `REVIEW_BLOCKED` rather than silently self-approving.

## 5. Assurance packet / optional ZIP

For R2/R3, generate one bounded evidence packet per frozen candidate under the existing ignored runtime surface, e.g.:

```text
runs/<task-id>/assurance/<sha>/
  manifest.json
  task-ref.txt
  repo-state.txt
  changed-files.txt
  diff-stat.txt
  verification.txt
  adversarial-findings.md
  review-request.md
  hashes.sha256
```

Optional transport bundle:

`assurance-<task-id>-<shortsha>.zip`

Rules:
- packet/ZIP is transport evidence, not a second SSoT;
- never include secrets, unrestricted environment dumps, hidden reasoning, or unrelated chat history;
- bind every review result to task ID + repository + branch + exact SHA + packet hash;
- reuse the same packet for multiple read-only reviewers when they are reviewing the same candidate;
- do not rerun deterministic checks merely because another reviewer needs the already-produced evidence unless independence specifically requires a rerun.

## 6. Adversarial batch rule

Before external independent review, collect plausible boundary cases into one RED/adversarial wave when they share the same candidate:
- malformed/extreme input;
- semantic-neighbor ambiguity;
- time/ordering/duplicate edges;
- provider/readiness/authorization edges;
- platform/path/encoding edges;
- race/retry/transport ambiguity where relevant.

Prefer one local/isolated adversarial branch or test file set. Do not open a separate PR for every discovered defect unless remote collaboration/CI genuinely requires it.

## 7. Verification economy

Use progressive verification:

1. **during edits:** smallest targeted reproducer/test;
2. **after implementation batch:** targeted + directly related tests;
3. **before freeze:** adversarial batch + scope/diff/secret/static checks;
4. **frozen candidate:** risk-tier-required independent review and hosted CI;
5. **release:** only release-relevant full regression/E2E/live proof.

Broad/full suites may run earlier when the changed boundary is known to have broad coupling or when a targeted failure suggests systemic impact.

## 8. Parallelism and WIP limit

Default maximum:
- **3 mutable implementation lanes**;
- **1 independent read-only review lane**;
- keep additional worker capacity free for recovery, blocker diagnosis, or urgent release work.

Parallelize only independent READY nodes from the dependency graph. Every mutable lane needs its own worktree/branch/claim and non-overlapping scope.

Do not maximize worker count merely because workers exist. Throughput is measured at accepted merge/release, not active-lane count.

## 9. GPT / GLM / deterministic-tool role split

Routing is capability-first; model names are implementation choices, not authority.

### GPT MAX / integrator default ownership
- product/architecture decomposition;
- trust/security/authorization boundary decisions;
- dependency graph and mutable-scope partitioning;
- conflict/claim adjudication;
- final independent judgment for high-risk work when GPT did not author the candidate;
- SSoT fold-back, PR/merge/release acceptance.

### GLM-5.3 / ZCode preferred execution classes when currently available
- repository archaeology and call-path tracing;
- bounded feature implementation from an exact task contract;
- multi-file mechanical refactor;
- regression/adversarial test generation;
- debugging and root-cause reproduction;
- batched defect repair;
- read-only exact-SHA code review/hardening.

### Deterministic/native tools
- grep/symbol/reference lookup where sufficient;
- formatting/static checks;
- targeted/full tests;
- manifest/hash/diff generation;
- schema validation;
- CI/build/package/E2E automation.

Do not spend premium reasoning on repetitive deterministic work that tools or a suitable bounded coding agent can complete safely.

## 10. ZCode execution-mode guidance

Current official ZCode documentation describes GLM-5.3/ZCode as optimized for long-horizon coding with stable long context, workspace/file/terminal/Git continuity, implementation, debugging, testing and review. Use that strength for sustained bounded implementation lanes.

Risk-aligned operator guidance:
- R0/R1 clear bounded work: lower-interruption execution modes may be used after the repository/scope gate;
- R2: plan/task contract first, then bounded autonomous implementation;
- R3: plan/confirm-before-change style for critical mutation boundaries, with deterministic gates outside the model.

Do not encode a provider-specific UI mode or thought-level label into task semantics; those product options may change.

## 11. Repair/no-progress loop

Default repair budget:
- R1: 1 bounded repair cycle;
- R2: 2 bounded repair cycles;
- R3: explicit task budget, normally no more than 2 repair cycles before adjudication/root-cause reset.

If the same material failure repeats twice without new evidence:

`STOP BLIND RETRY -> ROOT-CAUSE MODE -> RECLASSIFY / REPLAN / DECISION_REQUIRED`

Transport failure with ambiguous execution state is `RECOVERY_REQUIRED`, never automatic replay.

## 12. SSoT checkpoint economy

Checkpoint canonical SSoT at meaningful boundaries:
- claim/ownership acquisition or transfer;
- material blocker/decision;
- frozen candidate;
- merge/release acceptance;
- pause/handoff/session rollover.

Do not rewrite `CURRENT-WORK.md`/`handoff.md` after every trivial edit or test invocation. The active work order and `runs/<task-id>/` evidence hold intra-lane detail until a meaningful checkpoint.

## 13. PR/worktree policy

Default: **one logical feature PR per WO**.

Use additional remote PRs only when they provide real value: independent remote review, hosted CI unavailable locally, stacked dependency, or separate ownership. Otherwise keep RED/adversarial/repair experiments local and bounded.

After accepted merge, clean obsolete worktrees/branches only after proving clean state, ancestry/merge inclusion, and no active ownership. Never broad-clean unknown worktrees.

## 14. Throughput metric

Track accepted outcomes, not activity:
- median lead time from `READY_FOR_CLAIM` to accepted merge;
- number of review rounds per WO;
- full-suite/hosted-CI runs per accepted WO;
- active mutable WIP;
- reopened defects within the next accepted integration/release window.

Target for the fast workflow: **2–3x improvement in accepted-roadmap throughput** while keeping blocking-defect escape rate and safety incidents no worse than the prior baseline.

If speed improves only by moving defects downstream, the protocol has failed.
