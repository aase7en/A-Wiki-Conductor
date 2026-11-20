# Session rollover checkpoint — A-Sunday Conductor

Status: CHECKPOINT / CHAT ROLLOVER READY
Date: 2026-09-15 20:30 ICT
Issue: #325 / WO-P1-244

## Authority rule for next session

Do not use this checkpoint as project authority if repo/GitHub/runtime can be recovered. It is an index and starting map only.

Authority order:

`actual runtime/Git/GitHub/durable task state -> claims/checkpoints/evidence -> CURRENT-WORK/active WO/handoff/COLLAB -> chat/checkpoint summary`

Start every substantial session with:

`00-AGENT-ENTRY.md -> PROJECT-GRAPH.yaml -> AGENTS.md -> actual repo/worktree/branch/HEAD/dirty/claim -> CURRENT-WORK.md -> active WO -> handoff.md when needed -> task-relevant files`

## Current critical path at rollover

1. WO223 / PR #319 is still the top source critical path.
   - Frozen candidate: `779fcf5975e21d6891f63b94ad79893745776675`
   - PR #319 has not been fast-forwarded/merged in this session.
   - Required next gate: independent exact-SHA R3 review, then hosted exact-head CI, then expected-head merge/post-main if green.

2. WO242 / Issue #322 / PR #324 fixes SQLite job-store initialization race.
   - Frozen candidate: `bcf44f3be7b8323ef467999993b45c5d1588e761`
   - Draft PR: #324
   - Local evidence: deterministic race RED->GREEN, exact CI reproducer stress, job-store/control/dispatch/execution related tests.
   - Required next gate: hosted CI result + independent review.

3. WO243 / PR #323 records CoinTH GLM quota preflight.
   - Current head: `bcaf7aa2d8ad50e151556446d8b7f75dc6975b93`
   - Live quota endpoint attempts returned HTTP 403 with current discovered credentials, so endpoint method remains blocked by `AUTH_REQUIRED / ENTITLEMENT_MISMATCH` until a correct API key/entitlement is provided.

4. WO240 Browser Wake/Sunday-Family roadmap exists as planning work, but source implementation remains blocked until WO223 -> Phase-D/WO205 -> WO227/ZRA-3 releases the next-ready continuation semantics.

5. WO244 / Issue #325 records the Kilo vs Claude CLI harness decision.
   - Decision: Kilo is current proven GLM transport; Claude Code is promising but local GLM route unverified; A-Conductor must stay executor-neutral.

## Runtime observations

- Windows execution surface: `DESKTOP-7IB57R4`.
- Mac may be online but is not the default execution surface unless necessary.
- Root checkout `A:\GitHub\A-Wiki-Conductor` has historically been stale/dirty/protected. Prefer fresh isolated worktrees from `origin/main` or exact candidate SHAs.
- Kilo executable path used successfully: `kilocode.kilo-code-7.6.2-win32-x64\bin\kilo.exe`.
- Kilo model route used for GLM labor: `cointh-glm/glm-5.3`.
- `kilo roll-call` reported CoinTH GLM 5-hour rate limit with reset at `2026-09-15 19:26:26` during this session. Re-check current quota/health before launching more GLM lanes.
- Claude Code direct GLM route was not proven; do not use for production lanes until smoke returns structured result and model/credential route proof.

## Operating pattern to preserve

- GPT-5.6 Sol = integrator, authority reconciliation, diff/test verification, acceptance, merge/post-main decisions.
- GLM-5.3 MAX = high-token labor for implementation/review/adversarial lanes.
- Astra/premium models = reserve only for hard R3 architecture conflicts.
- Use one mutable writer per bounded source scope.
- Use many detached read-only GLM lanes for archaeology, adversarial review, test matrix, downstream prep.
- Agent `DONE` is a claim only. Accept only after exact SHA + scope + tests + review + CI as required.
- All long-running lanes must write status/results under ignored `runs/**` or durable GitHub comments so a new chat can recover without old chat history.

## Next-session immediate plan

1. Re-pin repo/GitHub/runtime.
2. Poll PR #323/#324 CI and PR #319 status.
3. Check Kilo/GLM readiness with `kilo roll-call` or accepted quota preflight if a valid quota API key exists.
4. Launch WO223 exact-SHA R3 review for `779fcf5...` if GLM route is ready; otherwise use GPT/Sol local review or another approved reviewer route.
5. Launch WO242 independent review if GLM route is ready.
6. Do not start Browser Wake/Sunday-Family source implementation until WO223 and downstream ZRA gates release it.
7. Keep checkpoints in repo/GitHub, not chat.

## New chat prompt

The user requested a copyable prompt in the assistant response. Use the prompt in the chat response, not this file, as the user-facing handoff text. The next session must still re-read actual authority before mutation.
