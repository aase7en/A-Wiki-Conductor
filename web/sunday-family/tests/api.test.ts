import { afterEach, describe, expect, it, vi } from 'vitest';
import { getSnapshot, parseSnapshot, streamSnapshots, type MonitorViews } from '../src/api';
import { liveMonitor, snapshot, streamResponse } from './fixtures';

afterEach(() => vi.unstubAllGlobals());

describe('authenticated monitor client', () => {
  it('sends the bearer in a header, never URL or cookies', async () => {
    const fetch = vi.fn().mockResolvedValue(Response.json(snapshot));
    vi.stubGlobal('fetch', fetch);
    const signal = new AbortController().signal;
    expect(await getSnapshot('test-only-token', signal)).toEqual(snapshot);
    expect(fetch).toHaveBeenCalledWith('/api/v1/snapshot', expect.objectContaining({
      headers: { Authorization: 'Bearer test-only-token', Accept: 'application/json' },
      credentials: 'omit', redirect: 'error', cache: 'no-store', signal,
    }));
  });

  it('parses fragmented SSE, CRLF, comments, and multiple frames', async () => {
    const frame = `event: snapshot\r\ndata: ${JSON.stringify(snapshot)}\r\n\r\n`;
    const fetch = vi.fn().mockResolvedValue(streamResponse([
      ': heartbeat\n\n', frame.slice(0, 35), frame.slice(35, -1), frame.slice(-1),
      `event: update\ndata: ${JSON.stringify({ ...snapshot, stale: true })}\n\n`,
    ]));
    vi.stubGlobal('fetch', fetch);
    const received = vi.fn();
    await streamSnapshots('test-only-token', new AbortController().signal, received);
    expect(received).toHaveBeenCalledTimes(2);
    expect(received.mock.calls[1][0].stale).toBe(true);
    expect(fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer test-only-token');
  });

  it('preserves UTF-8 split across bytes', async () => {
    const bytes = new TextEncoder().encode(`data: ${JSON.stringify({ ...snapshot, degraded_observability: ['TEST_ภาษาไทย'] })}\n\n`);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(new ReadableStream({
      start(controller) { for (const byte of bytes) controller.enqueue(new Uint8Array([byte])); controller.close(); },
    }), { headers: { 'Content-Type': 'text/event-stream' } })));
    const received = vi.fn();
    await streamSnapshots('test-only-token', new AbortController().signal, received);
    expect(received.mock.calls[0][0].degraded_observability).toEqual(['TEST_ภาษาไทย']);
  });

  it('rejects authorization failures without exposing server bodies', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('secret details', { status: 401 })));
    await expect(getSnapshot('test-only-token', new AbortController().signal)).rejects.toThrow('Token rejected');
  });

  it.each([
    ['monitor errors', 'data: {"error":"MONITOR_PROJECTION_UNAVAILABLE"}\n\n'],
    ['malformed JSON', 'data: invalid\n\n'],
    ['oversized frames', `data: ${'x'.repeat(262_145)}`],
  ])('rejects %s', async (_, frame) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(streamResponse([frame])));
    await expect(streamSnapshots('test-only-token', new AbortController().signal, vi.fn())).rejects.toThrow();
  });

  it('rejects non-SSE responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json(snapshot)));
    await expect(streamSnapshots('test-only-token', new AbortController().signal, vi.fn())).rejects.toThrow('event stream');
  });

  it.each([
    { ...snapshot, api_version: 'other' },
    { ...snapshot, cockpit: null },
    { ...snapshot, cockpit: { lanes: [{ ...snapshot.cockpit.lanes[0], state: {} }] } },
    { ...snapshot, cockpit: { lanes: [{ ...snapshot.cockpit.lanes[0], identity: { lane: {} } }] } },
  ])('rejects unsupported or malformed snapshots', value => {
    expect(() => parseSnapshot(value)).toThrow();
  });
});

describe('monitor child union validator (WO-P1-750)', () => {
  it('accepts live monitor views with all required sections', () => {
    expect(parseSnapshot({ ...snapshot, monitor: liveMonitor }).monitor).toEqual(liveMonitor);
  });

  it('accepts live views with a degraded inspector marker', () => {
    const monitor: MonitorViews = {
      ...liveMonitor,
      inspector: { state: 'DEGRADED', reason: 'INSPECTOR_PROJECTION_INVALID' },
    };
    expect(parseSnapshot({ ...snapshot, monitor }).monitor).toEqual(monitor);
  });

  it('still accepts the placeholder child', () => {
    expect(parseSnapshot(snapshot).monitor).toEqual(snapshot.monitor);
  });

  const omit = (monitor: MonitorViews, key: keyof MonitorViews): Record<string, unknown> => {
    const copy = { ...monitor } as Record<string, unknown>;
    delete copy[key];
    return copy;
  };
  type FullInspector = Extract<MonitorViews['inspector'], { summary: unknown }>;
  type FullViews = Omit<MonitorViews, 'inspector'> & { inspector: FullInspector };
  const mutate = (patch: (views: FullViews) => unknown): unknown =>
    patch(structuredClone(liveMonitor) as FullViews);

  it.each<[string, unknown]>([
    ['missing required section key', omit(liveMonitor, 'stm')],
    ['health counters with a string value', mutate(v => ({ ...v, health: { ...v.health, counters: { ready: '1' } } }))],
    ['health with non-boolean degraded', mutate(v => ({ ...v, health: { ...v.health, degraded: 'yes' } }))],
    ['oversized health conditions', mutate(v => ({ ...v, health: { ...v.health, conditions: Array.from({ length: 17 }, () => 'X') } }))],
    ['timeline entry with a numeric value', mutate(v => ({ ...v, timeline: [{ event_id: 1 }] }))],
    ['oversized timeline', mutate(v => ({ ...v, timeline: Array.from({ length: 65 }, () => ({})) }))],
    ['stm entry with a non-token state', mutate(v => ({ ...v, stm: [{ partition: 'hooks', state: 'READY', rebuild_required: false, record_count: 0 }] }))],
    ['stm entry with a negative record count', mutate(v => ({ ...v, stm: [{ partition: 'hooks', state: 'FRESH', rebuild_required: false, record_count: -1 }] }))],
    ['correlation with an oversized state', mutate(v => ({ ...v, correlation: { state: 'x'.repeat(33) } }))],
    ['oversized correlation entries', mutate(v => ({ ...v, correlation: { state: 'UNKNOWN', entries: Array.from({ length: 17 }, () => ({})) } }))],
    ['inspector without a summary', mutate(v => ({ ...v, inspector: { tools: [], hooks: [], skills: [] } }))],
    ['inspector summary section without counts', mutate(v => ({ ...v, inspector: { ...v.inspector, summary: { ...v.inspector.summary, tools: { truncated: false, dropped: 0 } } } }))],
    ['inspector with an oversized row list', mutate(v => ({ ...v, inspector: { ...v.inspector, skills: Array.from({ length: 129 }, () => ({})) } }))],
    ['inspector row with an object value', mutate(v => ({ ...v, inspector: { ...v.inspector, tools: [{ name: { nested: true } }] } }))],
    ['arbitrary dict without required sections', { foo: 'bar' }],
    ['placeholder branch with a non-string error', { error: 5 }],
    ['placeholder branch missing gate', { error: 'MONITOR_PROJECTION_UNAVAILABLE' }],
    ['inspector tools row list over 128 entries', { ...liveMonitor, inspector: { ...liveMonitor.inspector, tools: Array.from({ length: 129 }, () => ({ name: 'x' })) } }],
  ])('rejects malformed live monitor views: %s', (_, monitor) => {
    expect(() => parseSnapshot({ ...snapshot, monitor })).toThrow();
  });
});
