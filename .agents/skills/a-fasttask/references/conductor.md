# A-FastTask reference — conductor roles, WIP capacity, executor fallbacks

Pointer file only (WO-P1-245, extended by WO-P1-249). Authority lives in the
referenced files; this reference adds none. On any conflict,
`00-AGENT-ENTRY.md`, `AGENTS.md`, `PROJECT-GRAPH.yaml`,
`docs/agent-collab/CAPABILITY_MATRIX.md`,
`docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`, and the private Project
Protocol win.

## Role binding (routing preferences, never authority)

| Role | Default route | Boundary |
|---|---|---|
| GPT-5.6 Sol (integrator) | planning, task packets, authority/failure framing, integration, adjudication, continuity, acceptance, authorized merge/release | current claim and risk-tier evidence govern |
| GLM-5.3 via accepted Kilo CLI / Claude Code CLI | bounded implementation, fixtures, targeted tests, mechanical edits, repair batches | exact scope/result destination; no autonomous merge, policy change, or claim transfer |
| SundayWorker / Serena | local semantic navigation, bounded repository tools | Worker output is a claim until reconciled with Git/durable evidence |
| GPT-6 Astra / Codex (exceptional specialist) | narrow decision/review after one recorded Sol escalation | return implementation to Sol/GLM; not a routine worker or mandatory gate |
| RDC / GitHub / deterministic native tools | filesystem/shell/process evidence, remote truth, exact SHAs, CI, hashes, tests, builds | no mutation or acceptance authority by themselves |

No model or provider name is an authority. Routing identity never transfers
claim, mutation, or acceptance authority.

## CoinTH GLM secret + quota resolution

For every material CoinTH GLM dispatch, run the existing quota preflight in
`docs/runbooks/cointh-glm-quota.md` before dispatch.

Canonical key name: `COINTH_GLM_AUTH_TOKEN`.

Resolver rules:

1. Use the approved private Project Protocol / existing A-Wiki environment
   resolver boundary. The private protocol may contain a machine-specific
   source path; that path is configuration, not a repository secret.
2. Resolve only the named key. Do **not** recursively search disks, Google
   Drive, repositories, logs, shell history, environment dumps, or unrelated
   `.env` files to discover a credential.
3. The repository's existing resolver implementation is the reusable boundary
   (`resolve_awiki_drive_root` + `AWikiDriveEnvironmentSource`); A-FastTask
   must not create a second secret store/resolver.
4. Never echo, print, serialize, screenshot, commit, or attach the resolved
   token to task/result/evidence artifacts. Pass it only in memory to the
   authorized quota/provider call.
5. Approved resolver/source unavailable => fail closed with a typed secret or
   auth blocker. Do not guess a new path and do not ask the human to reconstruct
   a location already present in the private Project Protocol.
6. A 401/403 from a client whose compatibility is not proven is
   `CLIENT_COMPATIBILITY_UNVERIFIED`, not immediate proof of a bad credential.
   Recheck once with the proven PowerShell `Invoke-RestMethod` path before
   classifying `AUTH_REQUIRED / ENTITLEMENT_MISMATCH`.

Changing where the user stores the secret later should require only private
resolver configuration/Project Protocol changes. A-FastTask should continue to
use this same resolver contract.

## WIP behavior

`PROJECT-GRAPH.yaml` `rules.default_wip` is the capacity authority: up to 3
mutable implementation lanes and 1 independent read-only review lane, with
spare capacity kept for recovery/blocker diagnosis.

- A free mutable lane is filled by claiming non-overlapping scope through the
  existing claim/lease authority — never by creating a parallel task list.
- WIP full => NO new mutable lane. The routing decision returns the typed
  blocker, the live-lane inventory, and the exact next safe action (wait,
  recycle a finished lane via closeout, or split scope only after Sol
  adjudication).
- Review traffic never occupies the mutable-lane budget; review lanes read
  frozen exact SHAs only.

## Executor fallback (failure → next route)

Classify the failure with the codes in
`docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md` section 8, then degrade
without widening scope:

1. SundayWorker `PLUGIN_NOT_EXPOSED_TO_CHAT`, `WORKER_BUSY`, or
   `WORKER_STATE_UNKNOWN` => fall back to the next eligible existing route for
   the same bounded task (GLM bounded lane or deterministic native tools); Sol
   retains integration. Never wait on an unexposed Worker; never spin up a
   second scheduler or queue to work around it.
2. GLM route `RATE_LIMITED`, `TRANSPORT_FAILURE`, or unverified route =>
   `ROUTE_UNVERIFIED`; use an explicitly eligible fallback or checkpoint the
   lane for Sol; never silently substitute a different model.
3. Unclassifiable failure => `UNKNOWN_FAILURE`: checkpoint through the lane's
   declared result/evidence destination at a material boundary (coordination
   SSoT — WO checkpoint, `CURRENT-WORK.md`, `handoff.md` — is folded by
   Sol/integrator or an executor explicitly assigned those exact coordination
   paths) and report the typed blocker.

A failed tool blocks only the dependent step; other safe independent work may
continue.