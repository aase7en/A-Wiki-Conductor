# Desktop Commander Bounded Transport — provider operation contract

Status: North Star N3 binding contract / WO-P1-080
Schema: `schemas/desktop-commander-operation.schema.json` (`urn:a-conductor:schema:desktop-commander-operation:1.0.0`)
Parent contract: `docs/contracts/desktop-commander-runtime.md` (DC = optional execution hand, never authority)

## Role

This contract defines the **internal, pre-authorized, provider-specific operation definition** that a future bounded Desktop Commander transport adapter may resolve **after** A-Conductor has already accepted an operator `job.execute` command carrying only an opaque `operation_ref` (`docs/contracts/operator-command-api.md`).

It is `REUSE + WRAP/EXTEND`, not a new orchestration surface:

- it **reuses** the existing `operator.v1` `job.execute` → opaque `operation_ref` authority and the allowlisted fixed-operation pattern of `docs/contracts/native-operation-registry.md`;
- it **does not create a second registry** and **does not create a second `operation_ref` namespace**: provider definitions are resolved through the same A-Conductor operation authority as native operations, with no second scheduler, job state machine, or retry authority of their own;
- per **ADR-0001** there is **no MCP gateway** and no general MCP proxy in A-Conductor; a Desktop Commander Remote Device is an upstream execution transport, not a new orchestration universe.

The schema describes an internal definition shape only. It is **not** a model/operator free-form payload: there is intentionally no `command`, `argv`, `shell`, `executable`, `env`, `prompt`, `goal`, `transcript`, `script`, `sql`, or arbitrary payload field, mirroring the prohibitions already binding in `operator.v1` and the native operation registry.

## Definition shape

Every definition is closed (`additionalProperties: false`) and bounded by four independent clamps — project identity, mutation intent, timeout, and output budget:

| Field | Bound |
|---|---|
| `operation_ref` | opaque identifier, same semantics/charset as operator.v1 refs |
| `tool_family` | fixed closed enum (below) |
| `project_id` | authoritative A-Conductor project identity |
| `mutation_intent` | `READ_ONLY` or `PROJECT_MUTATION`, explicit |
| `timeout_seconds` | integer 1..3600 |
| `max_output_bytes` | positive integer ≤ **8,388,608** (8 MiB hard maximum) |
| `device_id` | optional; only for remote-device definitions |

Output beyond the budget must be **paginated** / tail-read by a future adapter; raw output is never injected wholesale into model context, matching the existing output-backpressure discipline.

## Fixed tool families

```text
PROJECT_FILE_READ      PROJECT_FILE_SEARCH
PROCESS_START          PROCESS_INSPECT
PROCESS_READ_OUTPUT    PROCESS_INTERACT
DOCUMENT_READ          DATA_ANALYZE
```

The enum is closed: adding a family requires a contract change. There is deliberately **no raw-shell family** — remote execution is a target device identity (`device_id`), not a `REMOTE_SHELL`-style escape hatch.

## Remote-device semantics

- `device_id` refers to an **explicitly registered device identity**; it is never discovered dynamically — there is **no discovery or polling** behavior of any kind in this slice or its successors' idle state.
- A missing, stale, or unknown device identity **fails closed**; it never falls back to "any device" or to local execution by guess.
- Per the runtime profile contract, remote mode is metadata until a separately gated bounded transport adapter exists.

## Capability ordering

**Read-only inspection is the recommended first remote capability.** Interactive or mutating families (`PROCESS_INTERACT`, `PROCESS_START` with `PROJECT_MUTATION`) remain later-gated behind the transport adapter gate below and the N6 security audit; they are last, not first.

## Security boundary

Desktop Commander's allowed-directory/blocklist protections are **defense-in-depth** guardrails and are **not A-Conductor's authorization boundary**. Authorization is owned by A-Conductor's project identity, mutation intent, operation allowlist, and durable job gates. OS/container isolation remains the boundary for untrusted workloads (upstream DC security policy, adopted in the runtime profile contract).

## Durable execution and recovery

- A **durable execution ID** (existing durable job/execution identity) must exist **before any side effect** is dispatched through a future adapter.
- **Transport loss is not execution failure.** Disconnect/retry/recovery classification reuses the existing resilient execution supervisor contracts (`docs/contracts/resilient-execution-supervisor.md`); this contract adds no second recovery authority.
- Duplicate dispatch protection, output backpressure, evidence capture, and VERIFYING/REVIEW result flow all reuse the existing durable stack; a runtime reporting "done" is evidence, not completion authority.

## Transport adapter gate (unchanged from the runtime contract)

A live transport adapter may call Desktop Commander only after: fixed/opaque operation mapping; project/device identity and authorization gate; mutation intent and allowed-scope validation; bounded timeout/output contract; durable execution ID before side effect; duplicate/retry/recovery classification; evidence capture with verification-required results; and a security review proving no direct operator/raw-shell bypass.

## This slice adds no transport

No MCP client, network call, process launch, background thread/timer, scheduler/dispatch, persistence, UI, or remote discovery is implemented or implied by this contract. N4 remains BLOCKED until GE-005A, GE-6, and the GE-7 dispatch seam are independently proven ready on current main.
