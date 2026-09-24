# Codex NightShift Resume Adapter v1

Status: DEX-3b transport contract
Issue: #531
Authority: A-Sunday Conductor Issue #215 automatic NEXT_READY continuation
Role: resume transport only

## 1. Purpose

This contract lets one already-authorized A-NightShift parent goal survive the
end of an individual Codex model turn. It does not select roadmap work. The
parent goal, A-Faster, A-FastTask, claims, reviews and Sol acceptance remain the
existing authorities.

The adapter consumes one bounded machine-readable parent turn receipt and may
resume the SAME persisted Codex thread only when every fail-closed admission
check passes.

## 2. Proven Codex capability

The bundled Codex CLI was exercised end-to-end on GPT-6 Luna / Medium:

1. a non-interactive seed turn returned a persisted thread id and
   RESUME_SEED_OK;
2. the first resume probe failed deterministically because the exec-resume
   subcommand does not accept -s or -C;
3. the supported form resumed the same thread and returned
   RESUME_CONTINUE_OK.

The automation-safe shape is:

    <CODEX_BIN> exec resume --json --ignore-user-config
      -m <model>
      -c model_reasoning_effort="<effort>"
      <thread_id>
      "<bounded wake pointer>"

The initial parent session MUST therefore be seeded with the required sandbox,
working directory and process-local MCP configuration. The adapter MUST NOT
invent unsupported resume flags. Capability is VERIFIED only for the exact
binary/version/profile that passed the probe.

## 3. Parent turn receipt

The parent writes one receipt under its existing ephemeral A-NightShift run
authority before a turn intentionally ends. The receipt conforms to
codex-nightshift-resume-adapter-v1.schema.json.

Required identity:
- run_id;
- thread_id;
- parent_exec_ref;
- model and effort;
- contract_ref and receipt_ref;
- authority_repo_ref and worktree_ref;
- capability_evidence_version;
- generation and generated_at.

Required transition:
- status = CONTINUE or TERMINAL;
- reason;
- stop_gate;
- outstanding_exec_refs;
- next_safe_action_ref.

The receipt is a projection/continuation pointer, not a new task state store.
Actual Git/GitHub/Sunday durable evidence outranks the receipt.

## 4. Resume admission

Resume is allowed only when ALL are true:

1. receipt schema validates and status=CONTINUE;
2. stop_gate=NONE;
3. exact CODEX_BIN/version resume capability is VERIFIED;
4. expected_generation equals receipt generation;
5. run_id/thread_id/parent_exec_ref and bounded refs are present;
6. Sunday/runtime recovery proves the previous parent process is terminal and
   no live parent process owns the same thread;
7. outstanding delegated executions were recovered before any duplicate
   dispatch decision;
8. the wake driver itself holds the one accepted execution/scope ownership for
   this run.

A CONTINUE receipt does not authorize any mutation. After resume, the parent
must start with RECOVER -> RECONCILE -> HARVEST and re-evaluate current
authority.

## 5. Fail-closed outcomes

Do not resume for:
- TERMINAL receipt;
- frozen human/action/authorization/safety/TRUE_NO_SAFE_NEXT_ACTION gate;
- stale or future generation;
- missing/malformed receipt;
- missing contract or thread identity;
- unverified/changed Codex capability;
- live parent ownership;
- ambiguous previous resume delivery;
- unknown durable execution truth.

Duplicate wake of the same generation is forbidden. An ambiguous resume
transport outcome is WAKE_DELIVERY_UNKNOWN and MUST NOT be blindly retried.
Recover durable thread/execution evidence first.

## 6. Wake payload

The wake message is pointer-only and bounded. Canonical shape:

    Read <contract_ref> and <receipt_ref>; continue the SAME A-NightShift
    parent goal from next_safe_action after fresh RECOVER.

The adapter MUST NOT reconstruct or embed roadmap state, prompts, credentials,
raw argv/env, logs, share URLs, model transcripts or Git operations.

Queue is only a live-thread convenience. codex queue MUST NOT be used as a resume substitute after the parent turn/process is terminal.

## 7. Generation and fencing

generation starts at 1 and increases exactly once per completed parent turn.
The wake driver binds expected_generation before invoking resume.

If expected_generation != receipt.generation, classify STALE_WAKE_GENERATION
and do nothing.

The driver is transport, not a retry engine. A successfully resumed next turn
must emit generation+1 before another wake is eligible. A second driver or
second wake for the same run/generation is a collision and fails closed under
existing Sunday/A-Conductor ownership rules.

## 8. Authority boundary

This adapter creates no:
- scheduler or roadmap owner;
- task database;
- claim or lease system;
- retry authority;
- review or merge authority;
- completion authority;
- model-routing authority;
- project memory.

Issue #215 remains NEXT_READY continuation authority. A-NightShift remains the
parent run supervisor. A-Faster remains router/binder. Sunday is durable
execution transport. Sol remains integration/acceptance authority.

## 9. Security and privacy

The schema is closed and bounded. Forbidden fields include prompt/messages,
token/api_key/secret/password/cookie/session_token/share_url, argv,
command_line/shell_command, Git operations and PID fields.

Refs reject URL schemes. Secret-bearing or executable payloads are not legal
resume receipts. Raw command lines are not durable evidence.

## 10. Terminal behavior

TERMINAL means the wake adapter performs no resume. A quota terminal is valid
only when the parent contract already classified fresh QUOTA_EXHAUSTED after
child reconciliation. The adapter does not calculate quota or choose stop
gates.

ChatGPT chat/session timeout has no semantic effect on this adapter. The parent
thread is resumed from durable run evidence, not from chat memory.
