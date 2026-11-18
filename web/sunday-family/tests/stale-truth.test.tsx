import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from '../src/App';
import { API_VERSION } from '../src/api';
import { LanesTable } from '../src/LanesTable';
import { SnapshotView } from '../src/SnapshotView';
import { liveSnapshot, snapshot, streamResponse } from './fixtures';

afterEach(() => { vi.unstubAllGlobals(); sessionStorage.clear(); });

describe('stale projection fail-closed (WO-P1-774 GPT P1 repair)', () => {
  it('never shows a verified READY badge for a stale lane snapshot', () => {
    const lane = { ...snapshot.cockpit.lanes[0], state: 'READY' };
    const { container } = render(<LanesTable lanes={[lane]}
      generatedAt={snapshot.generated_at} stale={true}
      staleReason="STREAM_STALE" streamDegraded={false} />);
    expect(screen.getByText('STALE')).toBeInTheDocument();
    expect(screen.getByText(/Last reported: READY \(unverified\)/)).toBeInTheDocument();
    const badge = container.querySelector('.sf-badge');
    expect(badge?.getAttribute('data-state')).toBe('STALE');
    expect(badge?.className).not.toContain('verified');
  });

  it('never marks the Monitor healthy when source freshness is stale', () => {
    const { container } = render(<SnapshotView snapshot={{
      ...liveSnapshot, stale: true, stale_reason: 'SOURCE_STALE',
      monitor: { ...liveSnapshot.monitor, health: {
        degraded: false, counters: {}, conditions: null,
      } },
    }} />);
    expect(container.querySelector('#monitor .status')?.textContent?.trim()).toBe('STALE');
    expect(container.querySelector('#monitor .status')?.className).toContain('warning');
  });
});
describe('snapshot refresh failure', () => {
  it('retains data only as STALE across navigation after a successful read then a failed refresh', async () => {
    sessionStorage.setItem('sunday-family.monitor-token', 'test-token');
    let snapshotCalls = 0;
    const fetch = vi.fn((path: string, _init?: RequestInit) => {
      if (path.endsWith('/snapshot')) {
        snapshotCalls += 1;
        return snapshotCalls === 1
          ? Promise.resolve(Response.json({
            ...snapshot, cockpit: { lanes: [{ ...snapshot.cockpit.lanes[0], state: 'READY' }] },
          }))
          : Promise.reject(new Error('NETWORK_OFFLINE'));
      }
      if (path.endsWith('/health')) return Promise.resolve(Response.json({
        api_version: API_VERSION, status: 'ok', degraded: false,
        profile: 'headless-read-only', version: '1', conditions: [],
      }));
      if (path.endsWith('/connectors')) return Promise.resolve(Response.json({
        scope: 'app-session', connectors: [],
      }));
      return Promise.resolve(streamResponse([]));
    });
    vi.stubGlobal('fetch', fetch);
    const { container } = render(<App />);
    expect(await screen.findByText('Current at source')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /งานและเลน/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Refresh snapshot' }));
    await waitFor(() => expect(screen.getByText(/Stale: SNAPSHOT_REFRESH_FAILED/)).toBeInTheDocument());
    expect(screen.queryByText('Current at source')).toBeNull();
    expect(container.querySelector('.sf-badge[data-state="STALE"]')).not.toBeNull();
    expect(container.querySelector('.sf-badge--verified')).toBeNull();
    expect(screen.getByRole('alert')).toHaveTextContent(/ข้อมูลที่ค้างอยู่เป็น STALE/);
    fireEvent.click(screen.getByRole('button', { name: /เครื่องมือและการใช้งาน/ }));
    expect(screen.getByRole('alert')).toHaveTextContent(/ข้อมูลที่ค้างอยู่เป็น STALE/);
    fireEvent.click(screen.getByRole('button', { name: /บันทึกกิจกรรม/ }));
    expect(screen.getByRole('alert')).toHaveTextContent(/ข้อมูลที่ค้างอยู่เป็น STALE/);
    expect(snapshotCalls).toBe(2);
    expect(fetch.mock.calls.every(([path, init]) =>
      path.startsWith('/api/v1/') && (!init?.method || init.method === 'GET'))).toBe(true);
  });
});
