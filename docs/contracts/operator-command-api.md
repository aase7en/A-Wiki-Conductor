# Contract — Transport-Neutral Operator Command API

Status: binding for P1-039 protocol work
Version: `operator.v1`

## Purpose

Provide one small command vocabulary that can be transported by Telegram/Hermes, Discord, desktop UI, CLI, or future gateways without giving those transports direct SQL, filesystem, Git, subprocess, planner, or model-routing authority.

## Ownership boundary

- **A-Wiki / Hermes** own conversational interpretation, high-level goals, work-order creation, planning knowledge, skills, and routing policy.
- **A-Conductor** owns durable operational job state, authority enforcement, execution, checkpoint/recovery, verification, and evidence.
- **Operator transports** translate user/operator interactions into this bounded protocol and render responses. They do not invent another state machine.

A direct Telegram conversation such as “ตรวจ OCR bug แล้วแก้จน tests ผ่าน” should be interpreted by Hermes/A-Wiki first. A-Conductor receives a `work_order_ref` and bounded operational commands rather than storing that conversational prompt as durable job payload.

## Protocol envelope

Every request has:

- `protocol_version`: exactly `operator.v1`
- `action`: one of the bounded actions below
- action-specific identifier fields only

There is intentionally no `command`, `argv`, `shell`, `prompt`, `goal`, `transcript`, `script`, `sql`, or arbitrary payload field.

## Bounded actions

### Read-only

- `status`
- `job.get`
- `job.events`

### Durable job lifecycle

- `job.create`
  - `job_id`
  - `work_order_ref`
  - `project_id`
  - `max_attempts`
- `job.ready`
  - `job_id`
  - `expected_version`
- `job.claim`
  - `job_id`
  - `expected_version`
  - `worker_id`
- `job.gate`
  - `job_id`
  - `expected_version`
  - `worker_id`
- `job.checkpoint`
  - `job_id`
  - `expected_version`
  - `checkpoint_ref`
  - optional `evidence_ref`
- `job.execute`
  - `job_id`
  - `expected_version`
  - `worker_id`
  - `operation_ref`

`operation_ref` is an opaque identifier resolved only by A-Conductor's allowlisted native-operation registry. It is not shell text.

## Identifier policy

Identifiers and refs are compact opaque strings. Protocol v1 permits ASCII letters, digits, `.`, `_`, `-`, `/`, `:`, and `@`, with bounded length. Whitespace/control characters are forbidden.

`work_order_ref` may point to an A-Wiki work order or companion-project work-order identifier, but the protocol does not fetch or parse A-Wiki itself.

## Optimistic concurrency

Every mutating command after `job.create` carries `expected_version`. The transport must not auto-refresh and silently retry a version conflict. It should surface the latest durable job state so the operator/Hermes can reconcile intent first.

## Response shape

Transport-independent responses should expose only bounded operational metadata:

- `ok`
- `code`
- optional `job_id`
- optional `state`
- optional `version`
- optional `worker_id`
- optional `attempt_count`
- optional `max_attempts`
- optional tuple of evidence/checkpoint refs

Raw stdout/stderr, secrets, tokens, environment values, shell commands, and prompts are not protocol response fields.

## Safety principles

1. Transport authentication is separate from execution authority.
2. A Telegram/Discord user being authenticated does not bypass A-Conductor job/version/worker/project gates.
3. No transport can request arbitrary executable/argv/shell strings through v1.
4. No transport owns retry/recovery truth; durable A-Conductor state does.
5. An LLM or Hermes statement that work is “done” is evidence, not completion authority by itself.
