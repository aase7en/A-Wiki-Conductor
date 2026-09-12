# WO-P1-222 — ZRA-2 Phase C0 safe integration fold gate

Status: PREPARED / HOLD_FOR_WO220_PASS / NO SOURCE MUTATION AUTHORIZED
Parent: WO216 + WO218 + WO219 / PR #296 + #299 / Issue #214
Owner: GPT-5.6 Sol integrator
Base at packet creation: `3e10b0464017f30b250314ba3ece9ebf9edf202f`
Risk: R3 identity / integration provenance

## Why this gate exists

WO216 source (`ade1628...`) is a known independently rejected parent. WO219 repair (`a2cb571...`) is stacked on that parent. Merging #296 and then #299 would place the rejected intermediate tree on main even temporarily and make reviewed-tree provenance harder to audit.

If WO220 independently PASSes exact repaired SHA `a2cb571d33e528840f47660d98fcdec80cad889b`, integrate C0 by a fresh-main fold rather than by merging the stacked PRs directly.

## Release gate

Do not materialize an integration candidate until all are true:

- WO220 verdict is PASS for exact `a2cb571d33e528840f47660d98fcdec80cad889b`;
- PR #299 hosted CI is terminal green for that exact head;
- GPT/integrator accepts WO220 evidence and Issue #214 releases integration;
- current `origin/main` is re-pinned;
- no current-main drift touches the five reviewed C0 paths below;
- no overlapping owner/claim exists on those paths.

Unknown/conflicting state => `SAFE_TO_FOLD_C0=NO`.

## Reviewed stack provenance

Merge-base of current main and repaired candidate at packet creation: `8700d21887500965ffc33bcbffa1f33602d9c2f6`.

Ordered candidate commits from that merge-base:

1. `8a5603c` — WO216 long-shift release docs
2. `ba594c3` — WO216 implementation claim/release verification
3. `ade1628` — WO216 C0 implementation (known rejected alone)
4. `5f779dd` — WO219 persisted provenance repair
5. `a2cb571` — WO219 NativeFileSystem authority repair

Only the final combined repaired tree is eligible for publication/integration. Never publish or merge an intermediate head ending at `ade1628` or `5f779dd`.

## Exact reviewed path identity at `a2cb571...`

| Path | SHA-256 | Git blob |
|---|---|---|
| `docs/prompts/GLM-WO216-ZRA2-PHASE-C0-LONGSHIFT.md` | `d3221233141321f7d93cda9a3deebdb0bf01739b50d5e7573fe869a3431e7aea` | `6a82a64241bcd715c66215b2309f5b1ea382a4f2` |
| `docs/work-orders/WO-P1-216-zra2-phase-c0-implementation.md` | `8abef6c068627788cf8c06bd9ab8bd2696202911cc3c0378c3c212f8843947c4` | `80d60294683cc672eac574c4ee28024ca007d142` |
| `docs/work-orders/WO-P1-219-zra2-c0-provenance-repair.md` | `bffaa684df4b43280693ba41193cb3fa480097919187ff6bbb3e02c26a59b3d7` | `db13122fb15e923a6219fb224ed3087c80196f26` |
| `src/a_conductor/zero_relay_review_task.py` | `27294b0d4dd6bbdb55649532e8d9fe4e4c46fadff39aeb26aa4389672b32fbfc` | `b3cc26b1b79e649c578d9b3d1ef00229abf05f04` |
| `tests/test_zero_relay_review_task.py` | `4a3901bd6d4691700ef1746da65fbec0d629e262866073f430fbd82ba2987bc3` | `6d8cb358768b46fb3403477cdc3252d66f75a0b4` |

At packet creation, `git log 8700d21..origin/main -- <five paths>` returned no drift. Recheck at execution time.

## Fold procedure after release

1. Fetch and pin latest `origin/main`.
2. Re-run five-path drift/ownership checks. Any drift/conflict => STOP and adjudicate.
3. Create a fresh isolated integration worktree/branch from then-current main.
4. Materialize the five-commit C0 stack locally without publishing intermediate states. Prefer either:
   - `cherry-pick -n` of the ordered five commits followed by one final commit; or
   - exact-path checkout only if and only if it preserves all intended C0 docs/source/test bytes and no candidate commit contains other authorized content.
5. If any cherry-pick conflict occurs => STOP `BLOCKED_CHERRY_PICK_CONFLICT`; do not hand-edit reviewed source to make it fit.
6. Before committing, prove all five paths have exact Git blob/SHA-256 identity matching the table above.
7. Prove no unintended paths are staged.
8. Run the accepted C0/WO219 verification floor plus any WO220-specific regression/falsification required by the PASS evidence.
9. Freeze a single final fold commit and open a fresh PR to current main.
10. Hosted CI must be terminal green.
11. Merge only the final repaired fold PR. Never merge #296/#299 directly as the integration mechanism.
12. On actual merge commit/main, prove the five path identities again and rerun focused/related tests.
13. Only then mark C0 `ACCEPTED + MERGED + POST_MAIN_VERIFIED` and release C1/WO221 as allowed by the WO220 result-contract adjudication.

## Verification floor

At minimum after fold materialization:

- `tests/test_zero_relay_review_task.py`
- `tests/test_native_execution.py`
- `tests/test_zero_relay_repair_materializer.py`
- `tests/test_zero_relay.py`
- `tests/test_claude_code_harness.py`
- `tests/test_parallel_ready_execution.py`
- `tests/test_agent_change_packets.py`
- `tests/test_review_mailbox_adapter.py`
- any additional exact tests demanded by WO220 PASS evidence
- compile/import
- `git diff --check`
- strict UTF-8/U+FFFD
- changed/untracked scope audit
- secret-like added-line scan

## Stop gates

STOP on non-PASS WO220, nonterminal/failing CI, main drift, overlap/claim conflict, cherry-pick conflict, exact-byte mismatch, required source reinterpretation, unknown authority, hosted CI gate, merge gate, or post-main mismatch.

This packet authorizes no source mutation by itself.
