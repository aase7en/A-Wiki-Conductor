# Incident — Windows host unavailable; Zero-Relay continuation moved to macOS

Date: 2026-09-10 (Asia/Bangkok)
Status: ACTIVE / MITIGATED FOR SOURCE WORK / LIVE ZERO-RELAY NOT YET PROVEN
Related: Issue #233, WO-P1-168, WO-P1-169

## Summary

The primary Windows workstation that normally runs A-Sunday Conductor became offline and
unreachable. Development therefore moved to the user's home Apple Silicon Mac.

The migration does not block repository development or the highest-priority Zero-Relay
MVP, but it exposes two independent macOS readiness gaps:
1. the current Claude Code invocation contract uses a flag not accepted by the installed
   Mac Claude CLI;
2. the canonical production supervised native adapter assembly is still Windows-specific.

These are environment/portability gaps, not evidence that the Zero-Relay architecture is
invalid.

## Recovered continuity

The prior shared ChatGPT conversation was decoded and reconciled against current Git/GitHub
state. Durable checkpoints were added to Issue #233 rather than relying on chat memory.

Recovered intended route:

```text
GPT integrator
  -> A-Sunday Conductor durable task/provider authority
  -> existing Claude Code supervised harness
  -> Cointh Anthropic-compatible endpoint
  -> GLM-5.3
  -> canonical result/evidence
  -> GPT review
```

ZCode is not on this critical path.

## Host facts — Mac

Fresh verified facts:
- repo: /Users/aase7en/Desktop/A-Wiki-Conductor
- base main at migration checkpoint: 77e7b0f8e9460f78fa2ef4a1ddaad62131c2c7f2
- Claude Code: 2.1.152
- Serena: not installed
- Sunday Worker fleet: not installed
- A-Conductor desktop/runtime: not installed
- ZCode: not required for the chosen Claude/Cointh path
- private A-Wiki-Data layer is present on Google Drive
- secrets/global.env exists with mode 0600
- required secret key name COINTH_GLM_AUTH_TOKEN is present; its value was not read/logged

The physical private Drive path is host-specific and must never be hard-coded into public
product code. Product code must continue resolving the private layer through the accepted
A-Wiki drive/environment contract.

## Problems already solved or mitigated

### 1. Chat-only continuity risk — MITIGATED

Problem:
important Zero-Relay/Claude/Cointh facts existed only in an old ChatGPT transcript.

Mitigation:
- recovered transcript as discovery evidence;
- reconciled against actual Git/GitHub;
- Issue #233 comments 5606720902 and 5606878598 now preserve the non-secret contract;
- private host-specific facts were checkpointed in A-Wiki-Data session memory.

### 2. Mac repository continuity — SOLVED

The Mac clone was fetched and verified clean/equal to origin/main before new lanes were
created. Work now uses isolated worktrees instead of mutating root main.

### 3. Cointh network reachability — PROVEN AT UNAUTHENTICATED BOUNDARY

From the Mac:
`https://cointh.com/glm/anthropic` returned HTTP 401 with
`x-cointh-reason: missing_key`.

This proves DNS/TLS/service reachability only. It does not prove authenticated model use.

### 4. Historical credential exposure — MITIGATED

A Cointh credential was exposed in the old chat. That historical value is treated as
compromised. The system must use only a rotated private secret through
`secret-ref:awiki-env/COINTH_GLM_AUTH_TOKEN` mapped at execution time to
`ANTHROPIC_AUTH_TOKEN`.

Never store the value in Git, Issues, PRs, argv, prompts, task packets, result files, or logs.

### 5. Unsafe probe cleanup — SOLVED

Temporary Claude probes created during Mac diagnosis were stopped only after exact PID and
command-identity verification. No broad process kill was used.

## Open problem A — Claude CLI compatibility

Current main generates a Claude invocation containing `--safe-mode`.

Real Mac reproduction on Claude Code 2.1.152:
```text
claude --print ... --safe-mode ...
-> error: unknown option '--safe-mode'
-> exit 1
```

WO-P1-168 / GPT-6 Astra owns the repair.

Astra's current checkpoint reports upstream evidence that `--safe-mode` was introduced
after the installed CLI version and proposes a uniform explicit confinement profile using
`--bare`, disabled slash commands, strict empty MCP configuration, and empty setting
sources while retaining plan/read-only tools, task binding, supervised execution, and
secret confinement.

Important: this design is PROPOSED / UNACCEPTED until WO168 freezes a candidate and the
integrator independently reviews the exact SHA and CI/evidence.

## Open problem B — macOS production supervised-process assembly

Fresh current-main source audit shows:
- `SupervisedClaudeCodeRunner` itself accepts an injected `NativeCommandRunner`;
- generic `NativeSubprocessRunner` exists and has cross-platform tests;
- however `build_supervised_claude_code_runner()` uses `SupervisedCommandRunner`;
- the canonical `build_supervised_native_adapter_resolver()` imports and constructs
  `WindowsOwnedProcessController`, `WindowsRuntimeObserver`, and
  `StrictPowerShellInspectionRunner`;
- real supervised Claude integration tests are currently marked Windows-only.

Therefore:
`CLAUDE_INVOCATION_COMPATIBILITY` and
`PRODUCTION_SUPERVISED_PROCESS_PORTABILITY` are separate gates.

Fixing WO168 alone must not be interpreted as proving the full A-Conductor supervised
Zero-Relay path on macOS.

## Open problem C — authenticated GLM turn

No real authenticated GLM-5.3 model turn through the accepted A-Conductor supervised path
has yet been proven on this Mac.

A raw 401, parser success, loopback fake provider, or direct unsupervised Claude response
must not be labeled Zero-Relay success.

## Tooling constraint observed in this ChatGPT/RDC lane

The ChatGPT tool safety layer blocked attempts that would read a private token and directly
send it to an external endpoint. Do not bypass that control.

Authenticated proof must use an authorized local execution path that keeps the secret
inside the execution boundary and exposes only sanitized evidence.

This is an operator/tool boundary, not a product runtime defect.

## Correct milestone labels

Current:
- MAC_REPO_CONTINUITY = READY
- COINTH_NETWORK_REACHABILITY = PROVEN_UNAUTHENTICATED
- ROTATED_SECRET_REFERENCE = PRESENT
- CLAUDE_MAC_INVOCATION = BLOCKED_BY_WO168
- MAC_PRODUCTION_SUPERVISION = NOT_YET_READY
- AUTHENTICATED_GLM_TURN = NOT_PROVEN
- GPT_GLM_ZERO_RELAY_ONE_SHOT = NOT_PROVEN

Do not collapse these states into a single READY flag.

## Next dependency order

```text
WO168 Claude invocation compatibility
  -> exact-SHA independent review / CI
  -> synthetic loopback confinement proof
  -> decide/implement POSIX supervised-process assembly if required for production path
  -> isolated authenticated Cointh -> GLM-5.3 one-shot
  -> canonical result ingestion
  -> GPT exact-result verification
  -> only then declare Zero-Relay one-shot proven
```
