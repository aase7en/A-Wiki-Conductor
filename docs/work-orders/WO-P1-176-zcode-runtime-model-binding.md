# WO-P1-176 — ZCode Authorized Runtime Model Materialization

Status: READY_FOR_GLM_CLAIM / R3 CRITICAL
Owner split: GPT-5.6 Sol integrator owns architecture, authority framing, acceptance, merge and release. GLM-5.3/ZCode is the preferred bounded implementation executor after a fresh non-overlap claim and worktree gate.
Parent: WO-P1-155 Zero-Relay Accelerator
Trigger evidence: Issue #213, especially independent audit comment `5620725176`; Wave-2 result in Issue #233 comment `5620813258`.
Bootstrap base used to author this packet: `main@1e2d193db2e7db7763d52cb337e9a3f130d0808e`.

## 1. Problem statement

A-Conductor already authorizes and hashes the intended provider/model selection, but the current supervised ZCode app-server turn does not prove that this authorized selection is materialized into the real ZCode session before the prompt is sent.

The independent GLM runtime audit reproduced the gap against installed ZCode 0.16.5. With an A-Conductor-shaped `session/create` that omitted model selection, the app-server used the ambient machine-default provider. Under the synthetic probe trust model, the synthetic credential was then sent to the ambient provider endpoint rather than the probe-authorized loopback endpoint. The same root defect is therefore treated as:

- P0: credential-delivery trust-boundary escape is possible when ambient default and authorized endpoint diverge;
- P1: durable/runtime evidence can attest provider/model A while execution actually selects ambient provider/model B.

No real credential may be used to reproduce this work. Do not read, copy, print or commit live credential values.

## 2. Required outcome

Before any user/task prompt reaches the ZCode model session, A-Conductor must deterministically prove that the running session is bound to the exact provider/model/endpoint authority already admitted upstream.

Required sequence:

`AUTHORIZED SELECTION -> MATERIALIZE EPHEMERAL RUNTIME PROVIDER/MODEL -> CREATE SESSION WITH EXACT MODEL REF -> VERIFY ACTUAL SESSION MODEL -> ONLY THEN SEND PROMPT`

If any required provider/model/base-URL/generation/credential-reference fact is missing, unsupported, ambiguous, ignored, mismatched or unverifiable, execution must fail closed before prompt send.

The repair must remove dependence on ambient machine defaults for an authorized Zero-Relay execution.

## 3. Reuse-before-build boundary

REUSE existing authorities and primitives. Do not create a second provider/model authority, provider store, policy store, scheduler, task store, retry engine or secret store.

Reuse at minimum:

- canonical provider snapshot/admission record and generation;
- `HarnessRuntimeBinding` / existing typed runtime binding configuration;
- existing selection authorization and digest/equality checks;
- `derive_zcode_runtime_identity` inputs and execution identity;
- existing explicit child-environment credential delivery path;
- existing `OwnedProcessSpec` environment allowlist and process ownership semantics;
- supported ZCode app-server protocol primitives discovered from the installed bundle, currently including create-time `model:{providerId,modelId}` and workspace/provider model registry operations.

A protocol feature observed in the installed bundle is capability evidence, not authority to invent new provider semantics.

## 4. Architecture decision for the repair

The acceptance target is the isolation-complete shape, not merely a cosmetic `model` field.

Preferred flow:

1. receive the already-authorized runtime binding from the production assembly/helper boundary;
2. carry only non-secret runtime metadata across the helper boundary: provider id, model id, authorized base URL, protocol metadata/generation, and the NAME of the credential environment key;
3. materialize an ephemeral provider/model entry using the ZCode workspace/provider registry operation supported by the installed protocol, with the API key sourced from the existing child environment by key reference rather than embedding the credential value in packet/protocol/log text;
4. call `session/create` with the exact authorized `{providerId, modelId}`;
5. obtain deterministic evidence of the actual selected session model/provider from the protocol response/state or another supported read-back mechanism;
6. compare actual vs authorized binding;
7. only after exact match, call `session/send`.

If a simpler implementation can prove the same isolation and exact-match properties without depending on ambient provider catalog state, it may be used. A create-time model ref that merely resolves against ambient config and therefore can still drift is insufficient by itself.

## 5. Mutable scope ceiling

After fresh re-pin, claim and dirty-state verification, GLM may use the smallest subset necessary from:

- `src/a_conductor/zcode_protocol.py`
- `src/a_conductor/zcode_supervised_helper.py`
- `src/a_conductor/zcode_runner.py`
- `src/a_conductor/zcode_production_assembly.py`
- `src/a_conductor/owned_process.py` only for one explicit non-secret ZCode runtime-model metadata environment key if required by the existing allowlist boundary
- minimum directly affected existing `tests/test_zcode*.py`
- minimum directly affected owned-process/supervised test if the allowlist changes
- this WO for checkpoint/evidence updates
- ignored `runs/WO-P1-176/**` for assurance evidence

Prefer a materially smaller actual edit set. Any new production file, provider schema/store, global continuity hotspot, dependency manifest, installed ZCode config, live DB, private Drive file, UI automation or unrelated runtime change requires a new GPT/integrator decision and claim.

## 6. Explicitly forbidden

- no live provider credential values in task packets, Git history, logs, comments, fixtures or result artifacts;
- no mutation of `~/.zcode`, `%USERPROFILE%\.zcode`, installed ZCode bundle, live provider config or live Control Center DB;
- no broad recursive search of the live ZCode config tree while ZCode is running;
- no broad process kill/stop/restart; process actions require exact owned PID identity and are not part of this task unless separately authorized;
- no fallback to ambient workspace default when an authorized selection exists;
- no silent downgrade from exact verification to an assertion/boolean supplied by the caller;
- no second provider/model authority;
- no blind replay after ambiguous execution;
- no self-approval, merge or release by the implementation lane.

## 7. RED-first behavioral matrix

Create failing tests before production repair. At minimum prove RED for the currently missing behavior, then GREEN for:

1. session creation places the exact authorized provider/model on the wire;
2. missing runtime binding fails before `session/send`;
3. malformed or partial provider/model metadata fails before prompt send;
4. ambient machine/workspace default deliberately differs from the authorized binding, yet cannot become the selected execution route;
5. authorized provider registration/materialization uses the authorized base URL, not ambient provider endpoint state;
6. credential value remains only in the explicit child environment; protocol metadata carries only the credential env-key reference where supported;
7. unknown/unsupported model or provider returns a typed fail-closed outcome; no fallback to ambient default;
8. read-back/attestation mismatch between actual session model and authorized binding fails before prompt send;
9. result-side evidence cannot claim success under a provider/model identity different from the actual verified session;
10. unknown environment override keys remain rejected if `OwnedProcessSpec` allowlist is expanded;
11. redaction/log/result artifacts contain no synthetic secret marker;
12. existing same-packet/two-model execution identity and dedup behavior remains intact;
13. timeout/output-budget/process ownership behavior remains unchanged;
14. directly related provider admission/selection authorization tests remain green.

Use synthetic credentials and loopback/fake provider endpoints for adversarial proof. Do not rely on a real provider for correctness.

## 8. Failure vocabulary

Prefer existing typed errors where semantically correct. If a new typed failure is truly required, keep it narrow and stable. Distinguish at least:

- runtime binding missing/invalid;
- provider/model materialization rejected/unsupported;
- actual model/provider mismatch;
- runtime binding unverifiable;
- protocol/transport failure;
- prompt not sent.

Do not collapse an authority mismatch into a generic provider business error after the prompt has already escaped the gate.

## 9. Deterministic verification

During implementation use progressive verification from `FAST_EXECUTION_PROTOCOL.md`:

1. smallest RED reproducer;
2. targeted protocol/helper/assembly tests;
3. directly related ZCode + supervised/owned-process tests;
4. adversarial matrix with conflicting ambient default and synthetic-secret canary;
5. `git diff --check`;
6. strict UTF-8 check;
7. added-line secret scan;
8. relevant compile/static checks;
9. bounded regression appropriate to changed trust boundaries;
10. exact candidate SHA freeze.

Because this is R3, a frozen candidate also requires independent exact-SHA adversarial review, hosted exact-head CI, expected-SHA merge and post-main verification by the integrator. The implementation GLM lane must not count its own review as independent.

## 10. Assurance packet

For the frozen candidate, create a secret-safe packet under:

`runs/WO-P1-176/assurance/<candidate-sha>/`

Recommended contents:

- `manifest.json`
- `task-ref.txt`
- `repo-state.txt`
- `changed-files.txt`
- `diff-stat.txt`
- `verification.txt`
- `adversarial-findings.md`
- `review-request.md`
- `hashes.sha256`

Never include unrestricted environment dumps, live provider config, credentials, hidden model reasoning or unrelated chat history.

## 11. Implementation-lane stop condition

When implementation + deterministic/adversarial tests are green:

- freeze exact candidate SHA;
- push branch;
- open/update Draft PR;
- publish assurance summary to Issue #213 and coordination pointer to Issue #233;
- report `READY_FOR_INDEPENDENT_EXACT_SHA_R3_REVIEW`;
- do not merge;
- do not self-approve.

The GLM session does not need to stop being useful after the candidate freezes. It may continue only with the read-only successor stages in `docs/prompts/GLM-MARATHON-5H-WAVE3.md` while another lane reviews the frozen candidate.

## 12. Acceptance criteria

WO176 is not complete until GPT/integrator verifies all of the following on one exact reviewed candidate:

- runtime does not depend on ambient provider/model defaults for authorized execution;
- exact provider/model/endpoint binding is materialized before prompt send;
- actual selected session identity is deterministically checked against authorized identity;
- mismatch/unsupported/unverifiable state fails closed before prompt send;
- synthetic-secret adversarial proof shows no unauthorized endpoint receives the secret canary;
- no live credential/config mutation was required;
- no duplicate provider/model authority was introduced;
- all targeted/related/adversarial tests pass;
- secret/diff/UTF-8/static checks pass;
- independent R3 review returns no unresolved blocking finding;
- exact-head hosted CI passes;
- merge uses expected candidate SHA;
- post-main verification passes.

Only after this acceptance may Zero-Relay claim an honest authorized-model execution and proceed toward the live one-task ZRA-1 proof / ZRA-COMP-1 / ZRA-2 critical path according to current dependency evidence.

## 13. Resume contract

Every resume must re-read `00-AGENT-ENTRY.md`, `PROJECT-GRAPH.yaml`, `AGENTS.md`, actual Git/worktree/remote/branch/HEAD/dirty state, claim ownership, this WO, `DEFECT_LESSONS.md`, the Zero-Relay roadmap, and any newer Issue #213/#233 evidence.

If `main`, the task-packet branch, provider protocol evidence, ownership, or mutable scope has changed, reconcile before mutation. Do not rely on the bootstrap SHA above as current truth.
