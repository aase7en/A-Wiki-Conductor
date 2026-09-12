# GLM5.3 /goal — WO226 bounded repair supplement

State: HELD_FOR_SOL_RELEASE. This is a supplement to the existing WO226 packet,
not a second master plan, claim, ownership authority, or permission to start a
parallel implementation. GPT Sol retains R3 framing, acceptance, merge and release.

1. Run repository entry/re-pin/ownership checks. Read the original released WO226
   and prompt on branch docs/wo-p1-226-zra2-reviewer-execution-bridge (release
   cb7959edce0058603b7b1d3c389fce66f1043007; checkpoint 673f2ac), current Issue214,
   PR314 and ../WO-P1-226-astra-final-review.md. Repair target reviewed here is
   78ec598b9830d802f54eb47642130693a038a39c. Newer source requires re-pin and
   reconciliation; do not overwrite a concurrent worker.
2. Check for a current Sol decision adopting AF1–AF4 and re-releasing WO226.
   Without that decision: return HELD_FOR_SOL_RELEASE to existing result.md;
   do not change source or ask the human to relay test output. Sol can read the
   report and result directly. Never launch another GLM instance.
3. After release, use the existing owning implementation worktree and original
   mutable scope. Nested subgoals: reproduce REDs -> trace existing authority ->
   bounded repair -> each RED GREEN -> related regression -> fault/replay matrix
   -> scope/static check -> new frozen SHA/PR314 -> durable handback and stop.
4. Reproduce all four tests in test_adversarial.py against 78ec598 using temporary
   SQLite state, synthetic runner seam and no live network/process. Port meaningful
   tests into the released focused test file; do not alter expected safe outcomes.
   AF1: loser must preserve winner resources while winner is barrier-paused;
   absence of record proves neither crash nor no effect. AF2: failed terminal
   after timeout must clean exact resources, no handoff/relaunch. AF3: complete
   post-run record identity check before cleanup/handoff, including foreign worker.
   AF4: canonical DENIED provider policy must block before acquisition/effect;
   reuse current provider-authority policy and requirement checks.
5. Preserve positive normal execution, single winner, all-equivalent multiplicity,
   timeout/live/unknown retention, no new resources on replay, default real factory,
   stale generation denial, provider/lease exact cleanup truth, and no C1 parsing.
   Do not create another schema, lock, scheduler, dedup, outbox or authority. If
   AF1/association cannot be proven in original scope, stop with DESIGN_GAP plus
   exact evidence for Sol/Astra. Do not paper over the gap with a new heuristic.
6. Record checkpoints and RED/GREEN evidence in original WO/result destinations
   after each coherent subgoal, including any unchanged baseline failures and
   exact scope. Stop after frozen repaired candidate and hosted CI trigger for
   independent exact-SHA review/GPT acceptance; no merge/release or roadmap jump.

Existing implementation result destination:
A:/GitHub/_worktrees/A-Wiki-Conductor-wo226-review-exec-src/runs/WO-P1-226/result.md

Human fallback is this pointer only; result copy-back is unnecessary.
