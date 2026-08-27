# Desktop Commander Runtime — bounded execution-hand contract

Status: North Star contract / WO-P1-077

## Role

Desktop Commander is an optional **execution integration / hand** for A-Sunday Conductor. It is not the planner, task authority, scheduler, durable state owner, verifier, or brain.

```text
A-Wiki                 = brain / policy / durable knowledge
A-Sunday Conductor     = control plane / router / safety / recovery / evidence
Desktop Commander      = optional local or remote execution hand
Serena / Native / etc. = peer execution hands
```

## Upstream facts adopted

Desktop Commander exposes filesystem/search, terminal and interactive process management, long-running sessions, bounded output pagination, document/data tooling, audit logging, and a Remote Device bridge. Remote Device forwards tool calls through a secure remote channel to the local MCP server.

Its upstream security policy says directory allowlists, command blocklists, and symlink protections are guardrails rather than a sandbox. OS/container isolation is the security boundary for untrusted workloads.

## Reuse boundary

A-Conductor MUST reuse its existing durable execution stack: job control, execution records, duplicate protection, supervision/reconciliation, output backpressure, repo/ownership gates, verification evidence, and opaque operation references.

Desktop Commander MUST NOT introduce:
- a second task/job state machine;
- a second scheduler/retry authority;
- a generic model-facing `run(command)` surface;
- a raw shell/argv field in operator.v1;
- an A-Conductor MCP multiplexer/proxy;
- a background polling loop just to discover runtime state.

## Routing capabilities

Base profile: `filesystem.read`, `filesystem.search`, `filesystem.write`, `process.execute`, `process.interactive`, `process.long-running`, `output.pagination`, `repo.tools`, `document.read`, `data.analysis`.

Remote mode adds only `remote.device`; it does not imply broader task authority.

Execution-surface traits are long-running, resumable, background-capable and repo-tool capable, with `max_safe_transaction_scope = bounded-project-operation`.

## Future transport adapter gate

A later transport slice may call Desktop Commander only after all of these exist:
1. fixed/opaque operation mapping owned by A-Conductor;
2. project/device identity and authorization gate;
3. mutation intent and allowed-scope validation;
4. bounded timeout/output contract;
5. durable execution ID before side effect;
6. duplicate/retry/recovery classification;
7. evidence capture and verification-required result state;
8. security review proving no direct operator/raw-shell bypass.

Preferred first remote operations are read-only inspection and deterministic verification. Interactive mutation is last, not first.

## Performance invariant

The profile module is pure metadata and adds no process, network, filesystem I/O, dependency, thread, timer, or polling cost at runtime. Future transports must be event-driven/on-demand and lazy-loaded.

## ADR compatibility

ADR-0001 remains in force: this integration does not reopen or implement an A-Conductor MCP gateway. A Desktop Commander Remote Device is an upstream execution transport, not a new Conductor orchestration universe.
