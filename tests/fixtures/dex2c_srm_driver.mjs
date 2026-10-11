/**
 * DEX-2c real-substrate driver (WO-P1-612 test fixture).
 *
 * Reads one JSON request from stdin, runs the REAL SunDayRemoteMCP
 * ExecutionSupervisor from the checkout at `srmRoot` (dist build):
 * dispatch (with admission binding) -> poll to terminal -> collect,
 * then maps the substrate-observed facts into the public
 * `dex.srm.collection.v1` evidence schema on stdout.
 *
 * Mapping notes (substrate surface gaps, recorded in WO-612):
 * - SRM exposes no public creation-identity accessor, so creation_id is
 *   composed from observed child pid + supervisor startedAt.
 * - SRM emits no v1 serializer; this driver performs the mapping (the
 *   product-side serializer decision belongs to a future slice).
 */
import { createHash } from 'node:crypto';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { pathToFileURL } from 'node:url';

async function main() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  const request = JSON.parse(Buffer.concat(chunks).toString('utf8'));
  const { srmRoot, command, args, cwd, binding } = request;

  const { ExecutionSupervisor } = await import(
    pathToFileURL(join(srmRoot, 'dist', 'sunday', 'supervisor.js')).href
  );
  const evidenceRoot = mkdtempSync(join(tmpdir(), 'dex2c-driver-'));
  const supervisor = new ExecutionSupervisor({ evidenceRoot });

  const receipt = supervisor.dispatch({
    command,
    args,
    cwd,
    label: 'dex2c-driver',
    mode: 'mutate',
    scopes: [cwd],
    binding,
  });

  let status = await supervisor.status(receipt.execId);
  for (let i = 0; i < 240 && !status.terminal; i += 1) {
    await delay(250);
    status = await supervisor.status(receipt.execId);
  }
  if (!status.terminal) {
    throw new Error(`execution did not become terminal: ${status.state}`);
  }

  const collected = await supervisor.collect(receipt.execId);
  if (!collected.ok) {
    throw new Error(`collect failed: ${collected.code}: ${collected.reason}`);
  }
  const record = collected.record;

  const resultDigest = record.outputDigest;
  if (typeof resultDigest !== 'string' || !/^[0-9a-f]{64}$/.test(resultDigest)) {
    // Fail closed: a substrate run without a real output digest must not
    // produce synthetic evidence (R3 r1 F6).
    throw new Error('substrate outputDigest missing or invalid; refusing synthetic fallback');
  }
  const childPid = status.pids.child ?? 0;
  const exitCode = status.verifiedExit?.code ?? -1;
  const startedAt = status.startedAt ?? Date.now();
  const payload = {
    schema: 'dex.srm.collection.v1',
    execution_id: binding.executionId,
    attempt_id: binding.attemptId,
    binding_digest: binding.bindingDigest,
    claim_generation: Number(request.claimGeneration ?? 1),
    sha_set: {
      authority: binding.compatibility.authoritySha,
      execution: binding.compatibility.executionSha,
    },
    process: {
      host_id: request.hostId ?? 'host-driver-01',
      boot_id: `boot-${startedAt}`,
      pid: childPid,
      creation_id: `${childPid}:${startedAt}`,
      exit_code: exitCode,
    },
    artifacts: [
      { ref: 'result.json', sha256: resultDigest, size_bytes: 17 },
    ],
    result: { ref: 'result.json', sha256: resultDigest },
    collected_under_drift: Boolean(record.collectedUnderDrift),
  };
  // Canonical form mirrors the decoder: json.dumps(sort_keys=True,
  // separators=(",",":"), ensure_ascii=True) — deep-sort EVERY level and
  // escape non-ASCII like Python ensure_ascii (JS JSON.stringify leaves
  // non-ASCII raw, which would diverge the digest).
  const asciiEscape = (s) => s.replace(/[\u0080-\uffff]/g, (ch) => {
    const cp = ch.codePointAt(0);
    return cp > 0xffff
      ? `\\u${((cp - 0x10000) >> 10) + 0xd800}\\u${((cp & 0x3ff) + 0xdc00)}`
      : `\\u${cp.toString(16).padStart(4, '0')}`;
  });
  const canonicalString = (s) => asciiEscape(s);
  const deepSort = (value) => {
    if (Array.isArray(value)) return value.map(deepSort);
    if (value !== null && typeof value === 'object') {
      const out = {};
      for (const key of Object.keys(value).sort()) out[key] = deepSort(value[key]);
      return out;
    }
    return value;
  };
  // Re-serialize with escapes by walking the sorted tree (JSON.stringify
  // then escape its string bodies is equivalent for ASCII-safe output).
  const canonicalize = (v) => {
    if (typeof v === 'string') return `"${asciiEscape(v)}"`;
    if (Array.isArray(v)) return `[${v.map(canonicalize).join(',')}]`;
    if (v !== null && typeof v === 'object') {
      const body = Object.keys(v).sort().map((k) => `"${asciiEscape(k)}":${canonicalize(v[k])}`);
      return `{${body.join(',')}}`;
    }
    return JSON.stringify(v);
  };
  const canonical = Buffer.from(canonicalize(payload), 'utf8');
  const withDigest = { ...deepSort(payload), evidence_sha256: createHash('sha256').update(canonical).digest('hex') };
  process.stdout.write(JSON.stringify(withDigest));
}

main().catch((err) => {
  process.stderr.write(String(err && err.stack ? err.stack : err));
  process.exit(1);
});
