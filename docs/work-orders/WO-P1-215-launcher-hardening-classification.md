# WO-P1-215 — launcher hardening classification boundary repair

Status: IMPLEMENTED / CANDIDATE FREEZE PENDING
Parent stack: PR #266 `8339e4c9e15c8eefd94693245ef9ef4b627c00de` + PR #285 `f7d23c96690f7cdb94d2ebe62cac6d4669ad6f00`
Independent finding: WO212 review `3f1c7d27543c9a8bebd8fe3844085d59261638aa`
Owner: GPT-5.6 Sol bounded repair lane
Branch: `fix/wo-p1-215-launcher-complete-classification`
Base: `f7d23c96690f7cdb94d2ebe62cac6d4669ad6f00`
Risk: R3 source boundary; no live deployment authority

## 1. Accepted finding

WO212 independently returned `CHANGES_REQUIRED`, P0=0/P1=0/P2=1/P3=3.

The accepted P2 is that the string-only launcher hardener could treat the presence of all four structural marker lines as sufficient evidence that a launcher was already hardened. A manually/partially modified launcher could therefore contain those markers while still retaining a legacy `Wait-Process` or stale method-wait seam. The helper would return the bytes unchanged.

The production consequence matters because `create_instance()` writes the helper's returned text into the newly created instance. `unchanged` therefore did not mean fail-closed at the operation boundary; it could silently copy an ambiguous launcher.

This WO repairs that P2 only.

## 2. Scope

Mutable source/test paths:

- `src/a_conductor/instance_create.py`
- `tests/test_instance_create.py`
- `DEFECT_LESSONS.md` (new defect-memory entry only)
- this work-order document

Forbidden:

- existing Worker `start.ps1` files;
- live Worker process/tunnel/service state;
- credentials/secrets;
- WO192 deployment/runtime state;
- unrelated P3 cleanup from WO212;
- scheduler/provider/lease/runtime source.

No deployment or Worker restart is authorized by this work order.

## 3. Call-path archaeology

At exact parent `f7d23c9...`, production has one relevant caller of `_harden_start_script_runtime_forensics(text) -> str`: `create_instance()`.

`create_instance()` reads reference `start.ps1`, calls the string transformer for Start scripts, and writes the returned bytes to the target instance. Thus the previous conservative helper behavior (`ambiguous -> unchanged`) was not sufficient as an operation-level fail-closed contract.

The generic/minimal reference shape used by existing instance creation is intentionally outside the runtime-forensics migration vocabulary and must remain backward compatible.

## 4. Repair design

Keep the original string transformer semantics intact and add an internal typed classification boundary:

- `TRANSFORMED`
- `ALREADY_HARDENED`
- `PASSTHROUGH_UNRECOGNIZED`
- `REFUSED_AMBIGUOUS`

A strong hardened-shape verifier requires the actual generated forensics structure rather than marker presence alone. It checks exactly one occurrence of the expected archive assignment, archive Move-Item line, WaitForExit, Refresh, exit-code capture, success/failure logging markers, and final exit command; rejects a remaining legacy `Wait-Process -Id ...` or stale direct `$RuntimeProcess.ExitCode` failure branch; and verifies generated ordering.

Classification semantics:

1. transformer changes bytes + generated shape verifies -> `TRANSFORMED`;
2. transformer changes bytes but generated shape cannot be proven -> original bytes + `REFUSED_AMBIGUOUS`;
3. unchanged bytes + generated hardened shape verifies -> `ALREADY_HARDENED`;
4. unchanged bytes with runtime-forensics structural signals/seams -> `REFUSED_AMBIGUOUS`;
5. unchanged generic script with no such signals -> `PASSTHROUGH_UNRECOGNIZED`.

`create_instance()` now classifies the reference start script during validation **before target directories are created**. `REFUSED_AMBIGUOUS` raises stable `REFERENCE_START_SCRIPT_UNSAFE`, preserving the existing preflight invariant that an invalid reference does not leave a half-built target.

The Start script is classified again after profile/name substitutions before write, so a future substitution cannot silently convert the input to an ambiguous state.

## 5. RED evidence

Before source repair, new production-boundary tests proved:

- complete hardening markers pasted around a legacy `Wait-Process` seam did **not** raise and the target was created;
- a partial structural marker plus legacy method-wait seam did **not** raise and the target was created;
- already-hardened positive control remained accepted.

Initial focused result:

`2 failed, 1 passed`

with both failures `Failed: DID NOT RAISE InstanceCreateError`.

An initially over-broad classifier then correctly exposed an additional compatibility requirement: generic minimal reference fixtures have no runtime-forensics structure and must not be classified ambiguous. That version produced eight instance-creation failures. The design was corrected by adding `PASSTHROUGH_UNRECOGNIZED`; tests/fixtures were not weakened or rewritten to manufacture green.

## 6. GREEN evidence

After the bounded repair and adding both legacy seam variants to the complete-marker test, author-side falsification found a second defect in the same classification boundary: broad substring/count checks let comment-only marker text become `ALREADY_HARDENED` authority and let quoted marker text become `REFUSED_AMBIGUOUS`. RED evidence was `2 failed, 30 deselected` with the two states misclassified exactly as predicted.

The classifier first moved to line-anchored executable PowerShell forms. A second adversarial round then proved line anchoring alone was still insufficient: block comments and here-strings can contain marker text at column zero, and a block-comment archive marker could suppress a real legacy seam. RED evidence was `3 failed, 33 deselected`.

The accepted implementation now builds a same-length **executable view** of the PowerShell source before any hardening/classification regex runs. It masks line comments, nested block comments, and here-string bodies/terminators while preserving source offsets and newlines. Here-string termination is recognized conservatively only at column zero; an indented marker-like terminator remains body text and cannot release following body lines into authority. Structural matches therefore retain exact slice positions into the original text without letting non-executing regions gain authority. Ordinary quoted command arguments remain visible so the generated hardening shape can still be verified exactly.

Current GREEN floor:

- multiline non-executing provenance matrix (block, nested block, here-string, false terminator, suppression attempts): 6 passed
- `python -m pytest -q tests/test_instance_create.py`: 39 passed
- `python -m pytest -q tests/test_setup_wizard.py tests/test_ps1_encoding_and_quoting.py tests/test_doctor_fixes.py tests/test_desktop_control.py`: 72 passed
- explicit current floor: 111 passed
- `python -m compileall -q src/a_conductor/instance_create.py` -> PASS
- `git diff --check` -> clean

Positive controls cover:

- recognized legacy method-wait transforms;
- recognized legacy Wait-Process transforms;
- already hardened reference remains byte-identical/accepted;
- generic unrelated reference remains passthrough-compatible;
- line-comment and quoted marker text remain non-authoritative;
- block-comment, nested block-comment and here-string marker regions remain non-authoritative;
- non-executing marker regions cannot suppress a real legacy hardening transform;
- complete-marker + either legacy seam is rejected before materialization;
- partial structural marker + legacy seam is rejected before materialization.

## 7. Static diagnostics

Serena/Pyright reports two `_shared_paths` optional-member diagnostics in an unchanged area near the top of `instance_create.py`. That function and those lines are outside the WO215 diff and the same diagnostics were observed on the parent stack before this repair. They are pre-existing and are not widened into this bounded repair.

## 8. P3 findings intentionally not repaired here

WO212 P3 advisories remain separate:

- raw CRLF direct helper input may fail unchanged at the legacy method-wait regex boundary;
- a manually mangled extra bare wait can survive as unreachable dead text after generated `exit`;
- documentation/policy wording around complete vs ambiguous input should follow the accepted typed classification semantics.

They are not required to close the accepted P2 and are not bundled into this source repair.

## 9. Acceptance requirements

Before this repair can be accepted:

1. candidate source/test/doc scope must remain bounded;
2. exact candidate hosted CI must be terminal green or any failure independently classified;
3. an independent reviewer must attempt to falsify the typed classifier and operation-level preflight, including false-complete marker states, both legacy seams, generic passthrough, true hardened positive control, idempotency, no-target-on-refusal, and read-only live-shape checks where authorized;
4. P0/P1/P2 blocker count must be zero;
5. no deployment may occur merely from source acceptance.

Implementation author must not self-accept or self-merge.

## 10. External stop gates

After candidate freeze/push/Draft PR:

- non-terminal hosted CI -> `BLOCKED_EXTERNAL_CI`, STOP;
- terminal green -> `BLOCKED_EXTERNAL_INDEPENDENT_REVIEW`, STOP;
- review blocker -> fresh repair authority required;
- review PASS -> GPT/integrator acceptance/merge decision;
- live rollout remains a separate WO192 operational gate.

## 11. Repair-2 addendum — enclosing brace-ancestry fail-closed proof (2026-10-16)

Status: REPAIR-2 CANDIDATE COMPLETE / AWAITING INDEPENDENT FALSIFICATION REVIEW
Authority framing: R3; GPT/integrator exact-SHA review of this PR (2026-10-16) returned CHANGES_REQUIRED P2 — `_is_runtime_forensics_hardened` proves marker presence/order only, not reachability: the complete hardened shape under `if ($false) { ... }` (full or partial wrap of `exit $RuntimeExitCode`) still classified `ALREADY_HARDENED`, bypassing `REFUSED_AMBIGUOUS`, so `create_instance()` could materialize the target. Claim: PR #293 comment `6218811712`. Implementation: Kilo/GLM session (macOS), isolated worktree `A-Wiki-Conductor-wo293-repair`, base HEAD `525f5fff702735c20011dc02764ea63372997b0a`.

### 11.1 Repair design

- `_enclosing_block_headers(executable, position)`: quote-aware brace scan over the SAME `_powershell_executable_view` output; returns the enclosing header stack (innermost first) of a marker position, or `None` when ancestry is unprovable (negative depth / unterminated quote).
- Every structural marker in `_is_runtime_forensics_hardened` must now have an ancestry exactly equal to its generated canonical context: top level; `try {` for the runtime-exit sequence (method-wait variant); `if ($RuntimeExitCode -eq 0) {` and `} else {` (optionally under `try {`) for the STOPPED/TUNNEL_START_FAILED logs; `if (Test-Path -LiteralPath $RuntimeLog -PathType Leaf) {` + `foreach ($RuntimeLog in @($RuntimeStdout, $RuntimeStderr)) {` for the archive Move-Item. Any other header (e.g. `if ($false) {`, `if ($true) {`, switch/while) or unprovable ancestry fails closed.
- Fail-closed flow preserved: unknown ancestry ⇒ not hardened ⇒ existing `_has_runtime_forensics_structural_signal` path ⇒ `REFUSED_AMBIGUOUS` ⇒ `create_instance` raises `REFERENCE_START_SCRIPT_UNSAFE` during preflight, before target materialization.
- The here-string opener (`@"`/`@'`) is now masked in the executable view like block-comment delimiters, so the ancestry scanner cannot observe a phantom unterminated quote in text whose here-string body/terminator are already masked. Canonical positive controls stay green.
- `_has_runtime_forensics_structural_signal` intentionally unchanged: a marker under an unknown guard must remain a structural signal so the classification lands on `REFUSED_AMBIGUOUS`, never `PASSTHROUGH_UNRECOGNIZED`.

### 11.2 Declared verification-enabler repair (same claimed file)

Base HEAD `525f5ff` carried a pre-existing POSIX-only defect inside the claimed mutable file: the `render_sh_scripts(...)` call site passed `health_port=` while `instance_templates_sh.render_sh_scripts` defines `port=` (mismatch present since parent `f7d23c9`). Every `create_instance()` call crashed on macOS/Linux after materialization, which (a) made the operation-level refusal test untruthful on this platform and (b) caused 11 pre-existing baseline failures in `tests/test_instance_create.py`. The one-kwarg call-site repair (`port=health_port`) is inside the claimed `src/a_conductor/instance_create.py` scope and is required for truthful cross-platform verification. Evidence: base-HEAD rerun in a throwaway detached worktree = `11 failed, 28 passed`; after repair = `49 passed`. Independent review verdict on this fix: valid, kept.

### 11.3 RED evidence

Revision 1 (brace ancestry): the untracked standalone RED suite `tests/test_wo215_repair2_false_guard.py` (temporary, outside final committed scope; deleted after integration) produced exactly `3 failed, 1 passed`: full false-wrap and partial false-wrap misclassified `ALREADY_HARDENED`, and the operation-level test failed via the pre-existing `TypeError: render_sh_scripts() got an unexpected keyword argument 'health_port'` instead of the classifier gate; the canonical positive control passed.

Revision 2 (terminal control flow + block-shape bounds): an in-memory rev-1-vs-rev-2 probe of the verifier (no working-tree mutation; temp module removed afterward) showed all 8 adversarial shapes accepted by the rev-1 verifier and refused by rev-2 — `exit 0`/`throw 'x'` prefixes (both variants), `exit 0` after the first marker, `catch`-weakened try, replaced `finally` header, trailing unmatched `}`, unclosed trailing block — while canonical wait-process and method-wait controls stayed accepted in both revisions, proving the generated canonical output is preserved and the new tests are genuine regression discriminators.

Revision 3 (loop-control terminal tokens): an in-memory prior-vs-current probe of the verifier (no working-tree mutation; temp module removed afterward) showed all 5 adversarial shapes accepted by the prior verifier and refused by the current one — bare `break` prefix, `BREAK` casing prefix, `continue` prefix (wait/method spread), and `break`/`continue` inserted between the first and second markers — while canonical controls stayed accepted. Prior behavior reproduced the reviewer-reported defect exactly (PowerShell bare `break`/`continue` outside loops terminates the script, yet the shape classified `ALREADY_HARDENED`).

### 11.4 GREEN evidence (this session, exact commands)

- `python3 -m pytest -q tests/test_instance_create.py` → **79 passed** (39 prior + 10 revision-1 cases + 16 revision-2 cases + 14 revision-3 cases: bare `break`/`BREAK`/`continue` prefixes × both variants, `break`/`continue` between markers × both variants, operation-level no-target refusals for loop-control tokens × both variants).
- Base related floor, measured at base HEAD `525f5ff` in a throwaway detached worktree: `python3 -m pytest -q tests/test_setup_wizard.py tests/test_ps1_encoding_and_quoting.py tests/test_doctor_fixes.py tests/test_desktop_control.py tests/test_sh_templates.py` → **7 failed, 69 passed** (5 kwarg-crash failures: 3 × ps1_encoding, 2 × doctor create/rename; plus 2 environment failures below).
- Candidate related floor, same command on this working tree: **2 failed, 74 passed**. Both failures (`test_doctor_fixes.py::test_reap_instance_wrappers_matches_boundary_only`, `test_desktop_control.py::test_apply_worker_settings_to_home_applied`) are pre-existing macOS environment failures (Windows process-reaping capture / `A:\GitHub\A-Wiki` non-absolute on POSIX), proven identical at base HEAD `525f5ff` — i.e. the delta from base to candidate is +5 passing, −5 failures, all attributable to the kwarg fix; the 2 env failures are unchanged.
- Portable floor: `python3 -m pytest -q tests/test_instance_create.py tests/test_setup_wizard.py tests/test_ps1_encoding_and_quoting.py tests/test_sh_templates.py` → **83 passed** (rev-1 snapshot) — re-run after revision 2 below.
- `python3 -m compileall -q src/a_conductor/instance_create.py` → PASS.
- `git diff --check` → clean.
- Final mutable scope: `src/a_conductor/instance_create.py`, `tests/test_instance_create.py`, `DEFECT_LESSONS.md` (new entry only, numbered **#56** — origin/main already carries #54/#54-collision-avoidance documented at #55; local branch file had not seen them), this addendum. No CURRENT-WORK/handoff edits; no commit/push/merge by the implementation session.

### 11.5 Stop state

`READY_FOR_INDEPENDENT_FALSIFICATION_REVIEW` at the working-tree candidate. Required next gates unchanged: implementation author does not self-accept or self-merge; exact-SHA hosted CI terminal green + independent falsification review (full/partial false-wrap, terminal-flow prefixes and mid-body inserts, bare `break`/`continue` prefixes and between-marker inserts with casing variants, non-canonical guards, catch/replaced-finally shapes, unbalanced braces, generic passthrough, true hardened positive controls, idempotency, no-target-on-refusal) with P0/P1/P2 = 0 before GPT/integrator acceptance. Live rollout remains a separate WO192 operational gate.

### 11.6 Revision-2 residual (honest P3 record)

Deliberately bounded, no broad parser rewrite. Refusals now prove: exact per-marker ancestry, canonical generated block headers anywhere in the view, global brace balance/quote termination, a single canonical terminal statement, and absence of bare loop-control tokens. **Residual, unproven:** non-marker, non-terminal, non-loop-control statements sitting under a canonical-context block with mutated inner content (e.g. statements inside a kept `finally {` whose body was altered), and PowerShell grammar constructs outside the block/quote model (splatting, subexpression parsing, exotic escapes) are not individually proven; tokens `while`/`switch`/`for`/`function` are refused only when they open a block (non-canonical header) or break balance, not as bare keywords. Any future widening of the accepted grammar requires an integrator-framed work order with its own evidence.

`merge_performed=false`.
