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

After the bounded repair and adding both legacy seam variants to the complete-marker test:

- `python -m pytest -q --tb=short tests/test_instance_create.py`
  - 29 passed
  - 1 Tk/display-only skip on this Windows host
- `python -m pytest -q tests/test_setup_wizard.py tests/test_ps1_encoding_and_quoting.py tests/test_doctor_fixes.py tests/test_desktop_control.py`
  - 72 passed
- explicit current floor: 101 passed + 1 expected UI/environment skip
- `python -m compileall -q src/a_conductor/instance_create.py` -> PASS
- `git diff --check` -> clean

Positive controls cover:

- recognized legacy method-wait transforms;
- recognized legacy Wait-Process transforms;
- already hardened reference remains byte-identical/accepted;
- generic unrelated reference remains passthrough-compatible;
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

`merge_performed=false`.
