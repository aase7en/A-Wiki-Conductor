# WO-P1-248 — SunDay Desktop bridge / owned RDC-equivalent MVP

Date: 2026-09-17
Status: ACTIVE / STAGE A REUSE+PROOF / PRODUCTION SOURCE HOLD
Owner: GPT-5.6 Sol integrator / SOL-B
Risk: R2 local compatibility + external-runtime proof; R3 before production cutover
Issue: #334
Base: `018779d0d2f5a7a7a21adb277e23a617692c36fd`
Strategy: `REUSE + WRAP + EXTEND`; do not clone proprietary hosted services.

## Goal

Replace routine dependence on Desktop Commander hosted Remote MCP with an A-Sunday-owned execution path as quickly as safely possible. Reuse the MIT DesktopCommanderMCP local stdio server for mature filesystem/search/process mechanics and expose it through the existing OpenAI `tunnel-client` / future SunDay Runtime substrate. A-Sunday Conductor remains the sole control plane.

This stage is deliberately not a second scheduler, task store, claim/lease system, provider registry, review system, completion state machine, or project-memory authority.

## Re-pinned evidence

- Desktop Commander public plan currently advertises Free = 10,000 remote tool calls/month and Pro = unlimited; local MCP remains free/open source.
- User dashboard screenshot on 2026-09-17 shows `15,990 of 10,000` and still-online devices. Public material does not establish whether the limit is a hard stop, delayed enforcement, or grace behavior.
- Local Desktop Commander package is `@wonderwhy-er/desktop-commander` v0.2.50, license MIT.
- Local September tool log contains 15,573 entries, close to the dashboard 15,990 count.
- 6,954 / 15,573 entries (44.65%) contain A-Wiki-Conductor path context; this is a lower-bound path-match estimate, not exact attribution.
- Largest tool-call classes: `start_process=7410`, `read_process_output=3422`, `read_file=1640`, `write_file=1223`. `start_process + read_process_output` alone is 10,832 / 15,573 (~69.6%).
- Two Desktop Commander `remote` process trees are concurrently established on the Windows device. A recent 15-call sample found one adjacent identical call within five seconds; duplicate execution is therefore not proven. Treat duplicate runtime as a reliability/safety risk, not as established quota root cause.
- `tunnel-client` v0.0.14 explicitly supports local/private stdio MCP -> OpenAI control plane and a `sample_mcp_stdio_local` profile.
- Existing SunDay Worker profiles already use that mechanism with `mcp.commands[].command`.
- `tunnel-client` admin profile `default` exists but references `env:OPENAI_ADMIN_KEY`; current process environment and approved A-Wiki secret source contain no `OPENAI_ADMIN_KEY`, `OPENAI_API_KEY`, or `OPENAI_RUNTIME_API_KEY`. New tunnel creation is therefore authorization-blocked.
- Fresh CoinTH quota preflight through the accepted A-Wiki secret resolver reached the endpoint but returned HTTP 403. Classify GLM material dispatch as `AUTH_REQUIRED / ENTITLEMENT_MISMATCH`, not `RATE_LIMITED`.

## Architecture decision

Fastest owned path:

```text
ChatGPT / MCP client
  -> OpenAI tunnel-client (existing trusted transport)
  -> SunDay Desktop lane / future Runtime Supervisor
  -> pinned DesktopCommanderMCP local stdio adapter
  -> typed/bounded filesystem, search, process and evidence operations
```

Do not build a clone of `mcp.desktopcommander.app`, its billing service, Supabase project, OAuth service, or other hosted/proprietary backend. The open-source remote client may be studied for interoperability, but hosted behavior is not copied.

Longer term, DesktopCommanderMCP is a pinned upstream dependency/adapter behind SunDay Runtime. A-Conductor owns admission, lane binding, claims, scope, review, acceptance, recovery and evidence.

## Stage A claim and scope

Tracked mutation allowed now:
- NEW `docs/work-orders/WO-P1-248-sunday-desktop-bridge.md` only.

External/ignored proof scope allowed now:
- `runs/WO-P1-248/SOL-B/`;
- isolated temporary tunnel-client profiles with no existing tunnel id;
- read-only inspection of DesktopCommanderMCP v0.2.50 and historical North Star branch;
- bounded local stdio launch/handshake tests that do not alter repository files or existing Worker/RDC configuration.

Forbidden in Stage A:
- any production `src/` or test mutation;
- reuse/rebind of Worker1..5 tunnel ids or credentials;
- mutation of existing Desktop Commander device/account configuration;
- stopping existing RDC processes solely on suspicion;
- WO246 / WO205 / WO227 / Zero-Relay source or claims;
- WO247 frozen candidate;
- protected root mutation;
- new scheduler/claim/task/provider/review authority;
- merge/deploy/cutover.

## Stage A proof plan

1. Pin DesktopCommanderMCP exact version/license and inventory only the capabilities needed by SunDay Desktop.
2. Prove the local stdio command starts and answers MCP initialize/tools-list without Remote MCP.
3. Generate/validate a tunnel-client stdio profile shape using a placeholder/new tunnel identity only; never borrow an existing Worker tunnel.
4. Record exact independent-tunnel authorization required (`OPENAI_ADMIN_KEY` for tunnel create and a runtime API-key reference as required by tunnel-client).
5. Establish single-instance ownership: one supervisor process owns one DesktopCommander child; exact PID/process identity; duplicate start must fail closed or attach, never create a second uncontrolled child.
6. Define migration routing so routine shell/read/search work prefers SunDay Desktop/local execution; hosted RDC remains temporary recovery/remote-device fallback until parity is accepted.
7. Record usage baseline and a target reducing hosted RDC calls by at least 70% after cutover, with observed accounting rather than assumed savings.

## Production source gate

Production SunDay Runtime implementation remains behind the accepted dependency order from WO247:

`WO246 -> WO205/full ZRA-2 -> ZRA-3 -> SunDay Runtime single-device MVP -> two-lane isolation/recovery proof -> ZRA-4 recomposed acceptance -> thin SunDayMCP`.

Stage A may finish reuse archaeology, local compatibility, exact contracts and authorization preparation in parallel. It grants no authority to reorder or mutate the production Runtime before its dependency gate releases.

When the gate releases, a successor source claim must publish exact files, RED tests, mutation owner and independent exact-SHA review requirements before touching source.

## GLM offload

`GLM_OFFLOAD_ASSESSMENT=BENEFICIAL`: upstream capability audit, test-matrix drafting and mechanical compatibility review are good GLM-5.3 work.

Current disposition: `BLOCKED / AUTH_REQUIRED`. Fresh CoinTH quota preflight returned HTTP 403 through the accepted secret resolver. No material GLM dispatch is authorized until a fresh full five-hour quota tuple is available. Do not silently substitute another paid/provider route.

## Acceptance — Stage A

- [ ] exact worktree/branch/HEAD/claim binding recorded and clean;
- [ ] tracked scope is exactly this WO file;
- [ ] MIT upstream/version evidence recorded;
- [ ] local stdio MCP initialize/tools-list proof passes;
- [ ] tunnel-client profile validation/doctor reaches only the expected missing independent-tunnel authorization blocker;
- [ ] existing Worker1..5 tunnel ids untouched;
- [ ] existing Desktop Commander config/device state untouched;
- [ ] duplicate-runtime risk and single-instance rule captured;
- [ ] usage baseline + A-Conductor attribution method recorded;
- [ ] fresh GLM review performed if/when quota/auth gate becomes eligible;
- [ ] durable Issue #334 checkpoint names exact next action.

`SAFE_TO_MUTATE_STAGE_A_DOC=YES` in this isolated worktree.
`SAFE_TO_MUTATE_PRODUCTION_SOURCE=NO`.
`SAFE_TO_CREATE_NEW_TUNNEL=NO` until independent OpenAI tunnel authorization is available.
