# C1 physical workspace identity — implementation proposal

Status: PROPOSED / NOT PRODUCTION AUTHORITY
WO: WO-P1-196 / WO196-ASTRA-C1-DESIGN-001
Parent: Issue #216 / GPT1-ZRA4-PREFLIGHT-001
Author: Poppy Javis / GPT-6 Astra on home macOS
Source baseline: 46f90b329d4991211f5c8a26406f3aca2162e9a7

## 1. Decision and limits

Extend the existing identity -> candidate -> lease -> execution chain with host-observed
physical resource evidence. Do not replace windows_worktree_key with filesystem I/O:
registry.py explicitly promises a pure metadata registry. Keep observation at an adapter
boundary and consume its bounded, typed result through existing authorities.

A physical root key alone cannot prove all writes independent. The design distinguishes
worktree data, individual file objects and shared Git metadata. Schedule only when the
necessary resource observations agree and the existing lease authority reserves their
conflict domains atomically. No second lock/lease/scheduler registry is proposed.

This document frames implementation; it does not enable ZRA-4, migrate a live database,
change a public schema, or authorize code changes. Parent acceptance plus accepted ZRA-3
and a fresh R3 source claim are required for production work. The accompanying GLM lab
may produce synthetic evidence now under a separate non-production scope.

## 2. What was actually reproduced

| Observation | Native Mac | Native Windows | Meaning |
|---|---|---|---|
| Two directory names resolve to same object | symlink: true | junction: true | Names alone are insufficient |
| windows_worktree_key equality for those aliases | false | false | Existing key misses physical equality |
| Same scope, distinct synthetic workers, one SQLite broker/store | LEASED + LEASED | LEASED + LEASED | Alias keys bypass the same-key conflict query |
| Active synthetic leases afterward | 2 | 2 | This is broker behavior, not just string inequality |
| Hard-linked a.txt/b.txt same object | true | not tested in this pass | Root identity alone misses per-file aliasing |
| Existing overlap function for a.txt/b.txt | false | not tested | Literal scope disjointness is not physical disjointness |
| src/x.py vs src/../src/x.py overlap | false | not tested | Scope semantics need a separate validated projection |
| src/x.py vs src\\x.py overlap | false | not tested | Separator interpretation must be platform-aware |
| Two linked Git worktrees share physical root | false | not tested | Data trees are independent objects |
| Those worktrees share physical git-common-dir | true | not tested | Some Git resources remain shared |

All probes used synthetic temp roots/SQLite stores and fake clean worker facts. No
production Worker, lease, provider, secret, private file or real task was changed.
Broker observations prove this isolated seam, not a demonstrated production overwrite.
Mac Git evidence used a temporary repository with no remote and one empty fixture commit.
Windows junction was removed explicitly before its owned temp directory was removed.

Mac and Windows inspected source blobs matched:
- registry.py: 5a50d3d6717c8230992518f21730271c0fd3f2f1
- worker_lease.py: dad529bbb2670439f9ae2a76d3f15a61a93d91b4
- graph/analyze.py: 670b5e84258550b0f2a36510cbf9b52bc3af1b09

These are Git blob IDs, not SHA-256 file hashes. Evidence at runs/WO-P1-196/mac-proof.json
is ignored; this table preserves the portable result. A subsequent lab must name its
actual host and source identity rather than treating these observations as fresh forever.

## 3. Current source authority map

| Seam at baseline | Current responsibility | Proposed change boundary |
|---|---|---|
| registry.py:36 windows_worktree_key | lexical Windows path key; pure/no I/O | retain legacy behavior during compatibility; never inject hidden stat calls |
| worker_candidate_assembly.py:293,409,779 | candidate/request worktree identity | consume the same verified observation as lease intake |
| worker_lease.py:134,143 | scope shape and authorization inclusion | validate grammar before projecting conflict resources |
| worker_lease.py:418,453 | existing-lease identity/recovery | version-aware comparison, fail closed on legacy uncertainty |
| worker_lease.py:984,1024 | key construction + atomic active-scope query | integrate physical resources into THIS transaction authority |
| graph/analyze.py:116,136 | authoritative glob intersection | reuse after semantic projection; no independent overlap algorithm |
| parallel_ready_execution.py:237 | request/dispatch identity consistency | preserve observation identity through dispatch |
| native_execution.py:278 | resolve + root confinement | separate point-in-time observation from operation-time safety |

Line numbers are navigation anchors at the pinned base. Re-resolve symbols if source
changes. No source mutation is performed by this design task.

## 4. Four identities, four questions

| Identity | Question answered | Never use it to infer |
|---|---|---|
| Logical project/repo | Which authorized project/task does this belong to? | Physical independence from another checkout |
| Physical worktree root | Are these names the same local directory object? | Independence of hard-linked files or Git common state |
| Mutation resource footprint | Can these operations affect a common object/subtree? | Authorization to write all resources being reserved |
| Git metadata domain | Which refs/config/common store can these Git operations affect? | That all file editing in linked worktrees must serialize |

Remote URL, branch name, HEAD, project_id and a hash of a path are not physical identity.
Two Mac/Windows clones of the same GitHub repo normally have separate local files, yet
still need logical ownership and merge policy. Conversely, distinct registered projects
can point at the same local folder: project_id must not partition away a real conflict.

Identity observation has three outcomes: SAME, DISTINCT_WITHIN_SUPPORTED_DOMAIN, UNKNOWN.
UNKNOWN never becomes DISTINCT merely because strings differ. Identity is scoped to the
executing host/observer authority and supported filesystem. A missing/forged caller host
label is not a new namespace permitting otherwise conflicting leases.

No host_id authority was found in the relevant source inventory. Therefore C1's first
production slice must stay host-local under one existing lease/store authority. A genuine
cross-host observer trust/enrollment contract is a separate future decision, not a new
host registry smuggled into this task. Shared SMB/NFS/cloud-sync roots across machines
remain unsupported for concurrent mutation until their identity/coordination semantics
are explicitly accepted. Read-only diagnosis may still report them.

## 5. Observation contract (semantic fields, not an accepted wire schema)

An observer result should bind:
- existing task/project/worktree/worker expectation and the local authority context;
- platform/filesystem capability class; supported/unknown reason;
- opened root object identity and its observation lifetime;
- display/final path for explanation, never the sole equality key;
- case/normalization policy known for the relevant directory or unsupported status;
- distinct Git per-worktree metadata and common metadata observations;
- a versioned projection of permitted scope into reserved resource classes;
- generation/observation provenance used by admission and operation-time revalidation.

Do not accept these fields as arbitrary caller assertions. Construct observations at the
trusted host adapter; downstream input identity must bind back to that observation. Use
existing factory/admission/lease provenance patterns, not a boolean verified=True escape.

On Windows evaluate open directory handles + FILE_ID_INFO (volume serial and 128-bit ID).
Microsoft documents that these identify files on one computer; the final path is useful
for explanation but not a universal SMB identity oracle. Normalized SMB path queries may
fail because component traversal lacks access. Such failure cannot silently fall back to
lexical equality. [FILE_ID_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_id_info),
[GetFinalPathNameByHandleW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfinalpathnamebyhandlew).

On macOS evaluate opened directory descriptors and fstat identity under the supported
local filesystem; retain descriptor lifetime through the relevant boundary where needed.
Do not copy Windows casefold assumptions onto case-sensitive APFS. Do not claim a lone
O_NOFOLLOW protects intermediate path components: its documented check is the final
component. A component-wise anchored design needs its own native proof.
[Apple open(2)](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/open.2.html).

Do not transplant Linux-only openat2 into macOS. Linux can be a later adapter with its
own capability tests; its resolve constraints illustrate why a prior realpath check is
not equivalent to an anchored operation. [Linux openat2](https://man7.org/linux/man-pages/man2/openat2.2.html).

Handle/object identifiers are observations, not forever identities. Reboot, remount,
replacement, ID reuse and lost handles invalidate assumptions. Do not cache an observation
indefinitely or hash object IDs into a permanent migration key without lifetime evidence.

## 6. Resource conflicts and scope semantics

Proposal: same-root data mutations initially reserve the whole physical root. This is
conservative and blocks two disjoint scopes inside one checkout; ordinary linked
worktrees still offer parallel data editing when their roots differ. Preserve original
allowed/forbidden scopes as authorization. A larger reservation is not broader write
permission. Fine-grained same-root concurrency is a later acceptance objective.

That conservative default still does not cover every alias across different roots.
Before declaring data roots independent, the supported mutation interface must address
nested roots, child reparse/symlink escapes and existing hard-linked write targets.

| Case | Required first-slice disposition |
|---|---|
| Root junction/symlink resolving to same opened directory | SAME; one mutation reservation winner |
| Different project IDs, same root object | conflict; do not partition by project label |
| Ancestor/descendant roots | reserve overlapping subtree/root domain or refuse narrower concurrent mutation |
| Internal symlink/junction to another root | no independence claim without contained operation proof; unsupported mutation otherwise |
| Existing target with multiple hard links | refuse unsupported direct mutation or prove a safe resource policy; do not infer different path means different file |
| Nonexistent destination | validate/anchor existing parent + constrained leaf; reserve parent/subtree, not fabricated object ID |
| Unknown case policy or filesystem | UNKNOWN/unsupported; do not lowercase optimistically |
| Drive-relative/device/ADS/ambiguous namespace spelling | typed refusal until explicitly supported |
| Same Git common dir, separate worktree data | data edits may proceed; shared Git mutations require their own serialized resource |

Define scope grammar before normalization. Reject absolute/drive-relative, NUL, traversal
and ambiguous separator forms for mutation intake, or explicitly migrate them through a
single reviewed adapter. Never normalize an escaping expression into an allowed one.
Glob language must retain the existing documented fnmatch-style semantics; changing '**'
to path-segment semantics would be a separate compatibility change. Feed validated semantic
forms to graph.analyze.write_sets_overlap rather than creating a second glob solver.

Glob authorization and physical conflict are different predicates. An allowed expression
can still conflict; a conflict-free expression can still be unauthorized. Negative/forbidden
scope checks stay fail closed before execution, and cannot be weakened by whole-root locks.

## 7. Shared Git metadata

Use Git's own --absolute-git-dir / --git-common-dir outputs, then observe those objects.
A .git file is not necessarily the metadata directory. Linked worktrees have per-worktree
state plus common objects/refs/config; external object alternates add further sharing.
[Git repository layout](https://git-scm.com/docs/gitrepository-layout).

Do not serialize all source editing just because git-common-dir matches. Classify
operations: confined data write; per-worktree index/HEAD operation; shared ref/config/
maintenance mutation. Unclassified Git mutation conservatively reserves the common Git
resource or is refused. Existing Git native lock handling remains necessary, but a
.lock file's existence/absence is not enough to decide application task ownership.

Do not build another Git lock service in C1. If the existing lease schema cannot express
shared resources, freeze the observation-only slice and require a separately accepted
extension of the SAME store/transaction. SQLite atomicity over a lexical key does not
make an incorrect equality relation safe.

## 8. TOCTOU and the actual safety claim

A path can change after observation and before write (time of check to time of use).
A refreshed stat immediately before execution narrows a window; it does not close it.

Future acceptance must distinguish:
1. ALIAS_DETECTION: known aliases converge during intake;
2. ADMISSION_EXCLUSION: two cooperating callers cannot reserve a conflicting resource;
3. OPERATION_CONFINEMENT: the actual write remains bound to the intended root/object;
4. CROSS_HOST_COORDINATION: all writers share an accepted authority (not in initial C1).

Passing item1 is not enough to label all four safe. A script/agent that can write arbitrary
host paths can escape an application-side reservation. State the cooperative-writer threat
model explicitly. Arbitrary external processes/humans are not fenced by a SQLite lease.
For stronger guarantees the mutation adapter needs anchored native operations or a verified
sandbox; an observer-only wrapper must refuse claims beyond its enforced capabilities.

Boundary sequence to prove: observe -> acquire existing authoritative lease -> revalidate
bound identity -> perform supported anchored operation -> reconcile -> release. Inject
swaps at EVERY boundary with deterministic barriers. A mismatch after possible side effect
means RECOVERY_REQUIRED; no automatic replay, no capacity release based solely on timeout.
Held handles, rename/delete sharing policy and resource lifetimes must be documented per OS.

## 9. Legacy migration — no dual authority window

Old active leases use lexical worktree_key. Do not let a v2 client reserve a physical key
while a v1 owner retains the same folder under an incomparable lexical key.

Before any source migration, enumerate all consumers/writers and decide one of:
- stop new mutation intake, reconcile existing active owners under existing authority,
  then migrate all comparable rows in a single coordinated version transition; or
- retain a conservative compatibility exclusion in the SAME acquisition transaction,
  with explicit version fencing preventing an old writer from bypassing new checks.

This is an integrator decision. Neither strategy authorizes killing a worker, expiring a
lease, marking uncertain work released or altering live stores in the lab. Unresolved
legacy identity remains capacity-consuming/quarantined according to existing semantics.
Copied databases and fake clocks only for proof. Unsupported old writers must fail closed,
not silently downgrade. Rollback cannot discard active v2 ownership or resume v1 writes
against incomparable live rows. Avoid online mixed-version mutation until proven.

## 10. Proposed delivery slices for the parent integrator

| Slice | Output | Gate |
|---|---|---|
| C1-LAB (now) | adversarial native probes, pure identity model, source map, minimized counterexamples | WO196 evidence-only claim |
| C1-OBS | host-local observer with typed supported/unknown outcomes; pure registry unchanged | ZRA3 + parent design acceptance + new source claim |
| C1-LEASE | one versioned projection through candidate/lease/recovery/dispatch + copied-store migration | observer proof + cross-consumer contract + R3 review |
| C1-IO | actual mutation confinement + case/scope/hardlink policy | operation-time native proofs |
| C1-GIT | operation-specific shared metadata exclusion in existing authority | accepted Git resource map |
| Parent C2/ZRA4 | deterministic batch/fan-out/fan-in integration | owned separately; not dispatched by WO196 |

Do not implement all slices in a single unreviewed 20h source goal. GLM's stamina is used
for finite proof programs and reproducible artifacts. Once a slice is accepted, its exact
scope can become a new durable implementation packet without another broad research pass.

## 11. Proof obligations and ready-to-implement gate

Required cases: root alias, drive mapping/8.3 when available, distinct supported roots,
case-sensitive/insensitive directories, Unicode names, trailing dots/spaces/ADS rejection,
nested roots, child links, hard links, nonexistent targets, unknown filesystem, denied
observation, root replacement after observation, stale identity after restart, competing
stores on one broker database, distinct project IDs on one root, same project on independent
clones, linked-worktree common metadata, old/new writer mixing and interrupted migration.

Every test reports native vs simulated evidence, exact source/probe SHA, support/skip reason,
expected admission/write outcome and observed side effects. A bare equal hash assertion is
not a proof of fenced writes. A cross-host test must not manufacture a trusted host ID.

A production packet is READY only when the integrator has selected supported host/filesystem
classes, observer provenance, conflict granularity, scope compatibility, lifecycle/version
migration, operation-time guarantee and exact affected consumers. Until then, lab output is
useful design evidence; product mutation remains HOLD.
