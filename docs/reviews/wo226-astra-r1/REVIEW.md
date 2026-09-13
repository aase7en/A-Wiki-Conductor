# Astra rereview of WO226 R1 — CHANGES_REQUIRED

Candidate: 609a8781ad60a89501a73d4817499654a0a5eba5, PR314.
Reviewer: Poppy Javis / GPT Astra. Date: 2026-09-13.
Claim: WO226-ASTRA-R1-REREVIEW-001 (Issue214 comment5649755317).

**The R1 batch/generation repair is present and focused tests pass, but the
combined repair is incomplete: AF1–AF4 remain 3 P1 + 1 P2.**

Sol already adopted all four in the same repair lane, in the amendment on branch
`docs/wo-p1-226-repair-r1` at `e5d7a27cc51982b1d8955d11c536638fde65a41a`:
`docs/prompts/GLM-WO226-REPAIR-R1.md` (Binding Sol amendment) and the WO section7.
Issue214 comments5649623129/5649626172 assign the existing owner before freeze.
The source diff78ec598→609a878 touches only admission replay cross-binding and its
focused tests; it does not implement the adopted Astra obligations.

## Independent exact-candidate verification

Original four probes copied byte-for-byte from frozen review5df9ebe; no changes to
source/tests or assertions. Run from this worktree:

```sh
python3 -m pytest -q -s docs/reviews/wo226-astra-r1/test_adversarial.py
python3 -m pytest -q tests/test_zero_relay_review_execution.py tests/test_zcode_production_assembly.py tests/test_zcode_composition_truth.py
```

- **4 FAILED** safe-behavior assertions, 0.55s; see adversarial.txt.
- **58 passed, 6 skipped**, 0.80s; includes all38 WO226 focused tests. Six skips
  are Windows real-helper tests on this macOS/Python3.12 host; see focused.txt.
- Diff limited to released two source/test paths; diff-check PASS. No source/test
  mutation by reviewer, live model/process, secrets, merge or duplicate executor.
- Remote original source worktree read-only verified clean at609a878. Canonical
  Windows repair-packet worktree verified at e5d7a27 and amendment present.
- Hosted CI PASS is reported by GLM comment5649730640, not rerun by Astra.

| Finding | Observation on609a878 | Status |
|---|---|---|
| AF1/P1 | Paused live winner owns ACTIVE admission/lease; losing identical dispatch returns NOT_ATTEMPTED_CLEANED and releases both; winner resumes EXECUTED. | OPEN |
| AF2/P2 | RUNNING timeout then durable FAILED; replay exits EQUIVALENT_TERMINAL_NOT_USABLE, both resources remain held. | OPEN |
| AF3/P1 | Injected terminal same-fingerprint foreign-worker record yields EXECUTED handoff worker01 while durable record is worker99. | OPEN |
| AF4/P1 | Canonical policy says TASK_NETWORK_DENIED for matching current external provider/task; bridge performs one synthetic effect and returns EXECUTED. | OPEN |

These are unchanged defects, not four new findings. Prior report source anchors
need the +25/+27-line offsets introduced by R1; reproduction identifies current
behavior directly. AF3 is a supported fault-seam test, not a claim the normal
runner changes worker identity. AF1 proves premature release, not duplicate model
launch. AF2 TTL expiry does not satisfy exact terminal cleanup. No external network
was contacted in AF4; endpoint uses .invalid and runner is synthetic.

The remote result.md tail still states P1=0/P2=0 and describes obsolete
acquire-then-release recovery. Owner must refresh final findings/next-action text
against actual amended acceptance criteria; do not carry old success totals as
completion proof. The duplicate pointer session correctly stood down, but its
completion is not combined implementation completion (comment5649636658).

## Next safe action — existing owner only

Continue **WO-P1-226-REPAIR-R1-GLM-001**, after checking latest ownership and SHA,
using the already-amended canonical packet:

`A:/GitHub/_worktrees/A-Wiki-Conductor-wo226-repair-r1/docs/prompts/GLM-WO226-REPAIR-R1.md`

No new implementation lane, master plan or scope expansion is proposed. Already
released AF1–AF4 must be RED→GREEN alongside preserved R1, then freeze a new exact
candidate for independent review. If AF1 needs another authority/schema/lock,
follow existing DESIGN_GAP stop. Otherwise no new human scope approval is needed
for the existing two-file amendment. No merge or dependent-roadmap advancement.

Results remain in the original source worktree runs/WO-P1-226/result.md, directly
readable by Sol/Astra. Human fallback is one pointer to the same owning session;
do not send it to a new duplicate session.
