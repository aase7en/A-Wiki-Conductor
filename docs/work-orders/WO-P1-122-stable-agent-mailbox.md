# WO-P1-122 — Stable External-Agent Mailbox

Date: 2026-09-01
Owner: GPT-5.6 Sol integrator
Status: ACTIVE / IMPLEMENTATION
Repository: `aase7en/A-Wiki-Conductor`
Branch: `feat/wo-p1-122-stable-agent-mailbox`
Priority: P1 ergonomics; disjoint from WO120/WO118B safety source

## Goal

Remove changing human relay prompts without creating a second task lifecycle. Extend the accepted AHA-5 task/result bridge with one stable machine-local mailbox path per external agent. GPT/Conductor may replace the mailbox contents for each assignment; the exact immutable task packet, lease, HEAD/hash preconditions, result destination, work order and repository SSoT remain authority.

## Reuse classification

`EXTEND` existing `agent_change_packets.py` + `docs/agent-collab/COLLAB_PROTOCOL.md`.

Do not create another scheduler, provider registry, task store, retry loop, roadmap, handoff, memory system, or tracked per-agent state tree.

## Allowed scope

- `src/a_conductor/agent_change_packets.py`
- `tests/test_agent_change_packets.py`
- `docs/agent-collab/COLLAB_PROTOCOL.md`
- `docs/research/model-routing-2026-08-24.md`
- this work order
## Mailbox contract

Default root is machine-local, outside the repository: `%LOCALAPPDATA%\A-Conductor\agent-bridge\` on Windows, with an explicit environment override and a user-state fallback on other systems.

Each agent receives one stable path such as `glm/task.md` or `ultra/task.md`. The stable file is only a pointer envelope containing task/provider/model/role identity, exact worktree/branch/base HEAD, exact task packet path + SHA-256, and exact result destination.

Publishing must re-read and hash the exact task packet before replacing the stable mailbox file. Replacement is atomic. A stale result remains rejectable by the existing task/provider/model/base-HEAD checks.

## Acceptance

1. Same agent + same root always resolves to the same mailbox task path across task IDs/worktrees.
2. Agent IDs are bounded slugs; traversal/absolute/path-separator input fails closed.
3. Environment override, Windows LOCALAPPDATA and cross-platform fallback are deterministic.
4. Publishing validates absolute task/result references and exact task-packet SHA before any mailbox replacement.
5. Publishing atomically overwrites the same `task.md`; no assignment-numbered mailbox files are created.
6. Human prompt is unchanged across assignments for one agent/root and names only the stable mailbox path.
7. Mailbox content points to exact task/result authority; it never embeds credentials or substitutes for the task packet.
8. Existing AHA-5 `build_human_bridge_prompt`, result reader and change-applier behavior remains compatible.
9. External agents still do not edit tracked coordination SSoT unless an explicit lane assigns it.
10. Accepted results are folded into canonical WO + `CURRENT-WORK.md` + `handoff.md`; reusable defects into `DEFECT_LESSONS.md`.
11. Automatic provider dispatch is not claimed complete by this WO.
12. Focused bridge tests + related lease/native tests + compile/diff/UTF-8/secret audit pass.


## Implementation checkpoint — 2026-09-01

RED first: focused bridge collection failed because stable-mailbox APIs did not exist. Initial GREEN exposed a Windows newline fixture mistake; the fixture was corrected to hash actual task bytes rather than assumed text bytes.

Adversarial self-review then found a prompt-injection boundary: mailbox metadata accepted newline/backtick content that could escape Markdown fields. A new RED reproduced it. Repair adds mailbox-specific scalar validation without changing the generic packet `_text()` contract. Missing result-parent and stale task-hash failures are verified not to replace the current mailbox.

Verification: `tests/test_agent_change_packets.py` = `24 passed`; related agent/native/lease/supervised suite = `137 passed`; compileall, `git diff --check`, UTF-8 and added-line credential-pattern scan PASS.

Operational proof: the current WO120 Ultra exact-head review packet was regenerated against latest docs-only main and re-read/hash-verified. Stable mailbox publication wrote `%LOCALAPPDATA%\A-Conductor\agent-bridge\ultra\task.md`, pointing to `wo120-ultra-rereview-003`, exact WO120 head `899d002...`, exact task SHA `f5cf07e6...`, and its declared result destination. Mailbox SHA after atomic publication: `566d9ee9...`.

No automatic provider execution is claimed. This removes changing human-visible task pointers while preserving exact per-task evidence authority. A reusable `DEFECT_LESSONS` entry for mailbox prompt metadata should be folded only after WO120 releases the shared lesson file, avoiding a manufactured conflict on PR #162.

Status: **IMPLEMENTED / SELF-REVIEWED / PR+INDEPENDENT-REVIEW PENDING.**

## Current-main reconciliation checkpoint ? 2026-09-01

The implementation was cleanly rebased from historical base `ba177341...` onto accepted main `b1024b354a6fc45faad618a055a55aef3d9954f5` after WO123 release. Scope remains exactly five declared files; no conflict and no additional authority/store/router was introduced.

Current-main verification: agent bridge + native/supervised/lease regression `207 passed`; `python -m compileall -q src/a_conductor` PASS; `git diff --check` PASS.

Machine-local realistic proof used the rebased mailbox API to publish the active WO118B GLM rereview pointer to the stable path `%LOCALAPPDATA%\A-Conductor\agent-bridge\glm\task.md`. The mailbox re-hashed the exact task packet before atomic replacement and points to exact review HEAD `cb758520...`, task SHA `d26b3af6...`, and the declared result destination. Human-visible GLM prompt is now stable across future assignments; only the pointer envelope changes. No credential or tracked SSoT was written to the mailbox.

Status: **CURRENT_MAIN_RECONCILED / EXACT_HEAD_INDEPENDENT_REVIEW_PENDING**.


## Deep-audit repair checkpoint ? 2026-09-01

GPT adversarial review found a real Markdown prompt-injection gap after the current-main rebase: `AgentMailboxAssignment.task_id`, `provider_id`, and `model_id` were embedded inside mailbox backticks but still used generic `_text()` validation, so newline/backtick content could escape the envelope. The existing test covered only role/branch/task_ref and did not pin these three fields.

RED-first repair extends the existing mailbox-injection test across all six Markdown-bearing metadata fields and changes only the three assignment identity fields to `_mailbox_text()`. The generic packet validator remains unchanged; no task lifecycle, router, result reader, or mailbox location semantics changed.

Post-repair evidence on current main base: `tests/test_agent_change_packets.py` = 24 passed; related agent/native/supervised/lease matrix = 221 passed; compileall, `git diff --check`, and UTF-8 audit PASS. Prior PR #168 CI at `8fd3c10...` is stale after this repair and must be replaced by exact-head CI + independent review before merge.
