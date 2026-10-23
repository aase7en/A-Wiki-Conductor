export const API_VERSION = 'sunday-family.monitor.v1';

export interface Lane {
  identity: {
    work_order_ref: string | null;
    task_ref: string | null;
    lane: string | null;
    execution_id: string | null;
    lease_id: string | null;
    provenance: string | null;
  };
  state: string;
  state_markers: string[];
  blocker_code: string | null;
  next_safe_action: string | null;
  last_activity: string | null;
  last_meaningful_progress: string | null;
  gates: Record<string, string | null>;
}

export interface Snapshot {
  api_version: string;
  generated_at: string | null;
  cockpit: { lanes: Lane[] };
  monitor: { error: string; gate: string };
  stale: boolean;
  stale_reason: string | null;
  degraded_observability: string[];
  monitor_stream_degraded: boolean;
}

export interface Health {
  status: string;
  api_version: string;
  version: string;
  profile: string;
  conditions: string[];
  degraded: boolean;
}

export interface Connector {
  connector_id: string;
  name: string;
  state: string;
}

export interface SystemMetrics {
  cpu_percent: number | null;
  memory_used_bytes: number | null;
  memory_total_bytes: number | null;
  uptime_seconds: number;
}

export class ApiError extends Error {
  constructor(public readonly status: number) {
    super(status === 401 ? 'Token rejected. Disconnect and enter a valid token.'
      : `Monitor request failed (HTTP ${status}).`);
  }
}

async function request(path: string, token: string, signal: AbortSignal, stream = false) {
  const response = await fetch(`/api/v1/${path}`, {
    headers: { Authorization: `Bearer ${token}`, Accept: stream ? 'text/event-stream' : 'application/json' },
    signal,
    cache: 'no-store',
    credentials: 'omit',
    redirect: 'error',
  });
  if (!response.ok) throw new ApiError(response.status);
  return response;
}

export function parseSnapshot(value: unknown): Snapshot {
  if (!value || typeof value !== 'object') throw new Error('Invalid monitor snapshot.');
  const data = value as Snapshot;
  if (data.api_version !== API_VERSION || !Array.isArray(data.cockpit?.lanes)
    || !(data.generated_at === null || typeof data.generated_at === 'string')
    || !(data.stale_reason === null || typeof data.stale_reason === 'string')
    || typeof data.stale !== 'boolean' || typeof data.monitor_stream_degraded !== 'boolean'
    || !Array.isArray(data.degraded_observability) || !data.monitor
    || typeof data.monitor.error !== 'string' || typeof data.monitor.gate !== 'string'
    || !data.degraded_observability.every(item => typeof item === 'string')
    || !data.cockpit.lanes.every(lane => lane && typeof lane.state === 'string'
      && lane.identity && typeof lane.identity === 'object' && Array.isArray(lane.state_markers)
      && ['work_order_ref', 'task_ref', 'lane', 'execution_id', 'lease_id', 'provenance']
        .every(field => {
          const value = lane.identity[field as keyof Lane['identity']];
          return value === null || typeof value === 'string';
        })
      && ['blocker_code', 'next_safe_action', 'last_activity', 'last_meaningful_progress']
        .every(field => {
          const value = lane[field as keyof Lane];
          return value === null || typeof value === 'string';
        })
      && lane.state_markers.every(item => typeof item === 'string')
      && lane.gates && typeof lane.gates === 'object'
      && Object.values(lane.gates).every(item => item === null || typeof item === 'string'))) {
    throw new Error('Unsupported or invalid monitor snapshot.');
  }
  return data;
}

export async function getSnapshot(token: string, signal: AbortSignal): Promise<Snapshot> {
  return parseSnapshot(await (await request('snapshot', token, signal)).json());
}

export async function getHealth(token: string, signal: AbortSignal): Promise<Health> {
  const data: Health = await (await request('health', token, signal)).json();
  if (data.api_version !== API_VERSION || typeof data.status !== 'string'
    || typeof data.profile !== 'string' || typeof data.version !== 'string'
    || typeof data.degraded !== 'boolean' || !Array.isArray(data.conditions)
    || !data.conditions.every(item => typeof item === 'string')) {
    throw new Error('Unsupported or invalid monitor health.');
  }
  return data;
}

export async function getMetrics(token: string, signal: AbortSignal): Promise<SystemMetrics> {
  const data: SystemMetrics = await (await request('metrics', token, signal)).json();
  const numeric = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value) && value >= 0;
  if (!data || !(data.cpu_percent === null || (numeric(data.cpu_percent) && data.cpu_percent <= 100))
    || !(data.memory_used_bytes === null || numeric(data.memory_used_bytes))
    || !(data.memory_total_bytes === null || numeric(data.memory_total_bytes))
    || !numeric(data.uptime_seconds)) throw new Error('Invalid system metrics.');
  return data;
}

export async function getConnectors(token: string, signal: AbortSignal): Promise<Connector[]> {
  const data = await (await request('connectors', token, signal)).json();
  if (data?.scope !== 'app-session' || !Array.isArray(data.connectors)
    || !data.connectors.every((item: Connector) => item && typeof item.connector_id === 'string'
      && typeof item.name === 'string' && typeof item.state === 'string')) throw new Error('Invalid connector list.');
  return data.connectors;
}

export async function mutateConnector(token: string, signal: AbortSignal, id: string, name?: string): Promise<void> {
  const response = await fetch(`/api/v1/connectors/${encodeURIComponent(id)}`, {
    method: name === undefined ? 'DELETE' : 'PATCH',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json',
      'X-Confirm': crypto.randomUUID() },
    body: name === undefined ? undefined : JSON.stringify({ name }),
    signal, cache: 'no-store', credentials: 'omit', redirect: 'error',
  });
  if (!response.ok) throw new ApiError(response.status);
}

export async function streamSnapshots(token: string, signal: AbortSignal, onSnapshot: (view: Snapshot) => void) {
  const response = await request('stream', token, signal, true);
  if (!response.headers.get('content-type')?.toLowerCase().startsWith('text/event-stream') || !response.body) {
    throw new Error('Monitor did not return an event stream.');
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (!signal.aborted) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      // CRLF can straddle network chunks; normalize only once a full frame exists.
      let boundary: RegExpExecArray | null;
      while ((boundary = /\r?\n\r?\n/.exec(buffer))) {
        const frame = buffer.slice(0, boundary.index);
        buffer = buffer.slice(boundary.index + boundary[0].length);
        if (frame.length > 262_144) throw new Error('Monitor frame exceeds size limit.');
        const data = frame.split(/\r?\n/).filter(line => line.startsWith('data:'))
          .map(line => line.slice(5).replace(/^ /, '')).join('\n');
        if (!data) continue;
        const payload: unknown = JSON.parse(data);
        if (payload && typeof payload === 'object' && 'error' in payload) {
          throw new Error('Monitor projection unavailable. Last snapshot is not live.');
        }
        onSnapshot(parseSnapshot(payload));
      }
      if (buffer.length > 262_144) throw new Error('Monitor frame exceeds size limit.');
    }
  } finally {
    await reader.cancel().catch(() => undefined);
    reader.releaseLock();
  }
}

export function errorMessage(error: unknown): string {
  // Do not echo server bodies or exception details that could contain credentials.
  return error instanceof ApiError ? error.message : 'Monitor unavailable or response invalid. Check the local API.';
}
