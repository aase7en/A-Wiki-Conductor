# WO-P1-182 — GLM Wave 5 / 320 Nested Goal Units

Status: PACKET_AUTHORING / DOCS-ONLY / NO PRODUCT MUTATION AUTHORITY
Date: 2026-09-11
Owner: GPT-5.6 Sol integrator for task framing, SSoT reconciliation, acceptance, merge, release
Preferred execution engine: GLM-5.3 / ZCode long-horizon `/goal` mode when current gates permit
Repository: `aase7en/A-Wiki-Conductor`
Bootstrap main: `680566d25e105630b321127c1a9b3e9e61af4bd4`
Coordination authority: Issue #233
Zero-Relay authority: Issue #213 + Issues #214/#215/#216 + WO-P1-155
Wave-4 predecessor: PR #252 / WO-P1-180 (consumed execution evidence; not current task authority)

## 1. User outcome

Exploit ZCode/GLM's long-horizon nested `/goal` capability so one human pointer can launch a large, resumable engineering program that continues through many useful dependent and independent tasks without repeated `continue` messages.

The target is not token consumption for its own sake. The target is accepted engineering evidence and throughput while consuming as much available GLM capacity as useful.

Wave 5 is deliberately much larger than Wave 4:

- Wave 4: 16 Level-1 goals (`G0..G15`).
- Wave 5: 32 goal families.
- Every family executes the standard ten-child protocol `A..J`.
- Base work units = `32 × 10 = 320`, exactly 20 times the 16 top-level goal count used by Wave 4.
- Proven findings may spawn bounded recursive sub-goals, so useful executed units may exceed 320.

This count measures planned analytical/engineering units, not lines of prompt text and not an obligation to repeat settled work.

## 2. Binding startup

Before any Wave-5 work:

1. `00-AGENT-ENTRY.md`
2. `PROJECT-GRAPH.yaml`
3. `AGENTS.md`
4. actual Git/worktree/remote/branch/HEAD/dirty/process/claim state
5. `CURRENT-WORK.md` as a continuity input, but reconcile its known staleness against live GitHub/claims
6. active WO for any mutable child
7. selected nodes from `PROJECT-GRAPH.yaml`
8. `DEFECT_LESSONS.md` before any `src/a_conductor/**` mutation
9. `docs/agent-collab/FAST_EXECUTION_PROTOCOL.md`
10. `docs/agent-collab/CAPABILITY_MATRIX.md`
11. `docs/plans/2026-09-04-zero-relay-accelerator-roadmap.md` for Zero-Relay work
12. Issue #233 and task-specific Issues #213/#214/#215/#216 as live durable coordination evidence

Actual repository/runtime evidence overrides stale task-state prose. It does not override safety, user authority or binding repository policy.

## 3. Authority / non-duplication

This WO and its prompt are a **goal-program transport contract**, not a new scheduler, job store, claim/lease system, review lifecycle, model-policy authority, retry engine, memory system or SSoT.

Mandatory reuse order:

`REUSE -> WRAP -> EXTEND -> BUILD`

Before proposing BUILD, prove why existing accepted primitives cannot satisfy the capability.

A-Wiki remains brain/policy/knowledge/memory-promotion authority where mapped by the cross-repo owner contract. A-Conductor remains runtime execution/lease/admission/recovery/provider-enforcement authority where mapped. No OWNER/OWNER duplication.

## 4. Mutable-child rule

The Wave-5 packet itself grants **zero production mutation authority**.

Every mutable child must independently prove:

- exact repo/worktree/remote/base/current branch/HEAD;
- dirty/untracked state known and owned;
- live WO/task and owner/claim;
- allowed and forbidden scope;
- no overlap with other active claims/worktrees/PRs;
- risk tier R0/R1/R2/R3;
- `SAFE_TO_MUTATE=YES` for that exact child.

If not proven, that child remains READ_ONLY and the Wave continues elsewhere.

Do not edit, reset, clean, stash, rebase, switch, overwrite or inspect sensitive contents of another active lane.

## 5. Current critical-path observation at bootstrap

At the bootstrap observation:

- main = `680566d25e105630b321127c1a9b3e9e61af4bd4` after WO178 / PR #251.
- WO178 ZRA-COMP-1 is merge/post-main verified.
- WO179 ZRA-1 real authorized proof attempt 1 ended non-positive; later evidence classified transient/child-context DNS failure.
- WO181 has an active GPT-5.6 Sol R3 source claim for the Windows child-environment boundary (`SYSTEMROOT`-class repair), with no remote branch visible at the docs-bootstrap checkpoint.
- No WO179 retry may leap ahead of WO181 merge/post-main verification.

These are bootstrap observations only. Wave 5 must re-pin before using them.

## 6. GLM execution topology

One ZCode MASTER `/goal` owns the Wave-5 program.

Under it, create 32 Level-1 goal families `F00..F31`.

Each family executes child goals:

- `A — RECOVER`: live state, dependency, owner, SHA, claims, process truth.
- `B — REUSE MAP`: exact existing owners/primitives/contracts; classify REUSE/WRAP/EXTEND/BUILD.
- `C — TRACE`: source symbols/call paths/tests/commits/issues; no assumption-only conclusions.
- `D — EVIDENCE MAP`: what is proven, unproven, stale, contradictory; exact deterministic evidence.
- `E — FALSIFY`: at least three plausible counterexamples/failure hypotheses when meaningful.
- `F — PROBE`: execute bounded deterministic/adversarial probes when safe; otherwise specify executable probes.
- `G — DELIVER`: implement only if a live mutable WO/claim grants authority; otherwise shape the smallest future packet.
- `H — VERIFY`: targeted + related + negative/positive controls appropriate to risk; distinguish author evidence from independent evidence.
- `I — CHECKPOINT`: persist durable result to the declared Issue/PR/WO surface without creating a shadow SSoT.
- `J — ROUTE`: mark DONE/BLOCKED/PARTIAL; enqueue prerequisites or next independent family; never ask the human to type `continue` merely to proceed.

Thus 32 families × 10 children = 320 base work units.

## 7. Recursive finding rule

When `E` or `F` proves a new material finding:

- allocate child id `<family>.R<n>`;
- root-cause first;
- classify severity and owner;
- prove whether an existing WO already owns it;
- if no mutation authority, create only a future bounded packet recommendation;
- if mutation authority exists, follow its risk-tier loop;
- after freeze, author cannot count itself as independent reviewer;
- return to the parent family after durable checkpoint.

Maximum automatic recursive depth: 4. Depth limits prevent unbounded speculative branching, not useful evidence gathering. Multiple independent findings may each have their own branch.

## 8. Preemption

A higher-value exact-SHA review or critical-path candidate may preempt a lower-value read-only family.

Preemption sequence:

`CHECKPOINT CURRENT CHILD -> RE-PIN PREEMPT TARGET -> REVIEW/EXECUTE UNDER ITS AUTHORITY -> CHECKPOINT -> RETURN TO GOAL QUEUE`

Never lose parent-goal state when preempting.

## 9. Independence rule

A GLM session that authored a frozen R2/R3 candidate may not count its own review as the required independent review.

If the same session authored a candidate, it must:

1. freeze/push exact SHA + assurance evidence;
2. checkpoint `REVIEW_REQUIRED`;
3. continue independent read-only Wave-5 work;
4. leave review for a genuinely independent lane/session/model as required by policy.

If Wave 5 did not author the candidate, it may perform independent exact-SHA review when explicitly eligible.

## 10. Secret/provider/live-runtime rule

Never print, copy, hash for display, commit or paste real credential values.

Use canonical secret references only. Synthetic credentials may be used for controlled probes.

No live ZCode user-config mutation unless a task-specific explicit WO/claim authorizes it. No broad recursive scan over ZCode state while ZCode is running. No broad process kill. Exact PID+identity only when process work is explicitly authorized.

A live external-provider attempt is not authorized merely because this Wave exists. It requires its task-specific live proof gate.

## 11. 32 family queue

The full family contracts live in `docs/prompts/GLM-MARATHON-WAVE5-320-NESTED-GOALS.md`.

High-level groups:

- `F00-F03` actual-state recovery, Wave-4 reconciliation, WO181/WO179 critical path.
- `F04-F09` ZRA-1 live proof and ZRA-2/3/4/5 composition readiness.
- `F10-F15` evaluator corpus, injection/exfiltration, provider/runtime hardening advisories.
- `F16-F19` Windows/process-environment, recovery/replay, credential/provenance, compatibility.
- `F20-F23` A-Wiki cross-repo authority/memory/defect/evidence reconciliation.
- `F24-F27` SSoT/claims/PR hygiene, observability/privacy, cold-start continuity.
- `F28-F31` efficiency/test-economy, failure forecasting, next-WO shaping, final synthesis.

The prompt defines the detailed objective, dependency and completion boundary for every family.

## 12. Result destinations

Default durable coordination/result surface: A-Wiki-Conductor Issue #233.

Task-specific findings also belong in their existing task Issue/PR where one exists (e.g. #213/#214/#215/#216). Do not duplicate the same full report across many surfaces; post a concise cross-pointer when necessary.

Ignored local evidence may use `runs/<WO-or-wave-id>/**` where repository policy permits. It is evidence, not a second SSoT.

## 13. Checkpoint format

At every meaningful family boundary persist:

```text
WAVE=GLM-WAVE5-320
FAMILY=Fxx
CHILDREN=A..J status
REPO/REF/SHA=
MODE=READ_ONLY|MUTATION_AUTHORIZED_BY_<WO>
OWNER/CLAIM=
PROVEN=
FALSIFIED=
FINDINGS=
BLOCKERS=
DEPENDENCIES=
NEXT_QUEUE=
```

Do not store hidden chain-of-thought. Store observable evidence, hypotheses tested, commands/tests/probes and verdicts.

## 14. Session-limit continuity

When the current ZCode context/session approaches a practical limit:

- stop opening new mutation;
- finish/checkpoint the current bounded child;
- publish `STATUS=PARTIAL_LIMIT_CHECKPOINT`;
- record exact completed family/child ids;
- record current repos/SHAs/claims/blocked dependencies;
- record resume queue in deterministic order;
- record exactly one `NEXT_SAFE_ACTION`;
- a new GLM session resumes from that checkpoint and **must not rerun DONE children** without a stated falsification reason.

The 320-unit Wave is intentionally allowed to span multiple ZCode sessions.

## 15. Completion

Wave 5 completes when every family is one of:

- `DONE_PROVEN`
- `DONE_NO_GAP`
- `BLOCKED_WITH_OWNER_AND_DEPENDENCY`
- `DEFERRED_BY_AUTHORITY`

A family may not be called DONE merely because notes were written.

Final post on Issue #233:

`## GLM-MARATHON-WAVE5-320 RESULT`

Must contain:

1. exact repos/SHAs and state transitions observed;
2. completed/blocked family matrix F00..F31;
3. material defects with severity + owner + evidence;
4. Zero-Relay current maturity and exact gating chain;
5. REUSE/WRAP/EXTEND/BUILD decisions;
6. security/evaluator/provenance results;
7. cross-platform/runtime results;
8. stale-SSoT/claim/PR findings;
9. accepted-run efficiency evidence;
10. ranked future work, maximum 12 micro-WOs;
11. blockers requiring human/authorization action, if any;
12. exactly one `NEXT_SAFE_ACTION`.

## 16. Stop conditions

Stop the whole Wave only for:

- `HUMAN_DECISION_REQUIRED`
- `HUMAN_ACTION_REQUIRED`
- `AUTHORIZATION_REQUIRED`
- `SAFETY_BLOCK`
- `OWNERSHIP_CONFLICT`
- `NO_SAFE_NEXT_ACTION`
- useful goal tree exhausted/completed
- session/context limit after durable checkpoint

A single blocked family is not a whole-Wave stop when other safe families remain.

## 17. Explicit non-goals

Wave 5 does not authorize:

- burning tokens by restating settled evidence;
- creating duplicate scheduler/task/claim/review/provider/memory authorities;
- broad source refactors not tied to a proved gap;
- weakening tests/security/privacy/authorization for speed;
- live credential exposure;
- same-agent self-approval;
- branch/worktree cleanup owned by someone else;
- merges or releases by the GLM execution lane unless separately assigned.

## 18. Bootstrap mutation scope

This docs bootstrap may change only:

- `docs/work-orders/WO-P1-182-glm-wave5-320-goals.md`
- `docs/prompts/GLM-MARATHON-WAVE5-320-NESTED-GOALS.md`

No global continuity/hotspot/source/test/runtime/private/config/DB changes are part of WO182 authoring.
