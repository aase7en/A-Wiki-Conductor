import { fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from '../src/App';
import { API_VERSION } from '../src/api';
import { FleetView } from '../src/FleetView';
import { ToolsView } from '../src/ToolsView';
import { liveSnapshot, snapshot, streamResponse } from './fixtures';

const TOKEN = 'test-only-token';

function stubMonitorApi(payload = snapshot, connectors: unknown[] = []) {
  const fetch = vi.fn().mockImplementation((path: string) => {
    if (path.endsWith('/health')) return Promise.resolve(Response.json({
      api_version: API_VERSION, status: 'ok', degraded: false, profile: 'headless-read-only', version: '1', conditions: [],
    }));
    if (path.endsWith('/snapshot')) return Promise.resolve(Response.json(payload));
    if (path.endsWith('/connectors')) return Promise.resolve(Response.json({ scope: 'app-session', connectors }));
    return Promise.resolve(streamResponse([`data: ${JSON.stringify(payload)}\n\n`]));
  });
  vi.stubGlobal('fetch', fetch);
  return fetch;
}

function navButton(thai: string) {
  return screen.getByRole('button', { name: new RegExp(thai) });
}

afterEach(() => vi.unstubAllGlobals());

describe('Fleet section (WO-P1-774 slice C)', () => {
  it('renders device projection as honest UNKNOWN without a fleet device DTO', async () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    stubMonitorApi();
    render(<App />);
    fireEvent.click(navButton('ทีมเครื่อง'));
    expect(screen.getByRole('heading', { level: 1, name: /ทีมเครื่อง/ })).toBeInTheDocument();
    expect(await screen.findByText('FLEET_PROJECTION_NOT_PROVIDED')).toBeInTheDocument();
    for (const device of ['Windows', 'Mac']) {
      const row = screen.getByText(new RegExp(device), { selector: 'strong' }).closest('tr') as HTMLElement;
      expect(within(row).getByText('UNKNOWN')).toBeInTheDocument();
      expect(within(row).getAllByText(/ไม่ทราบ|ยังไม่มีหลักฐาน/).length).toBeGreaterThan(0);
    }
    expect(screen.queryByText('READY')).toBeNull();
  });

  it('shows session connectors as clearly-labeled evidence, not fleet devices', async () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    stubMonitorApi(snapshot, [{
      connector_id: 'conn-fleet-test', name: 'Session probe', state: 'STOPPED', created_at: '2026-11-18T00:00:00Z',
    }]);
    render(<App />);
    fireEvent.click(navButton('ทีมเครื่อง'));
    expect(await screen.findByText('Session probe')).toBeInTheDocument();
    expect(screen.getByText(/connector ของ session นี้เท่านั้น — ไม่ใช่อุปกรณ์ในทีมเครื่อง/)).toBeInTheDocument();
    expect(screen.getByText('conn-fleet-test')).toBeInTheDocument();
  });

  it('offers no device or connector control actions in the Fleet section', async () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    stubMonitorApi(snapshot, [{
      connector_id: 'conn-fleet-test', name: 'Session probe', state: 'STOPPED', created_at: '2026-11-18T00:00:00Z',
    }]);
    render(<App />);
    fireEvent.click(navButton('ทีมเครื่อง'));
    await screen.findByText('Session probe');
    for (const forbidden of ['Rename', 'Delete', 'Start', 'Stop', 'Pair', 'Rebind']) {
      expect(screen.queryByRole('button', { name: forbidden })).toBeNull();
    }
  });

  it('direct render handles connector load failure honestly', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Connector read failed')));
    render(<FleetView token={TOKEN} />);
    expect(await screen.findByText(/ไม่สามารถอ่าน connectors ได้/)).toBeInTheDocument();
    expect(screen.getByText('CONNECTORS_READ_FAILED')).toBeInTheDocument();
  });
});

describe('Tools & Usage section (WO-P1-774 slice C)', () => {
  it('renders inspector tools with phase, provenance, and truthful state badges', async () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    stubMonitorApi(liveSnapshot);
    render(<App />);
    fireEvent.click(navButton('เครื่องมือและการใช้งาน'));
    expect(screen.getByRole('heading', { level: 1, name: /เครื่องมือและการใช้งาน/ })).toBeInTheDocument();
    expect(await screen.findByText('INSPECTOR_FROM_MONITOR_VIEWS')).toBeInTheDocument();
    expect(screen.getByText('windows-local')).toBeInTheDocument();
    expect(screen.getByText('CONNECTED')).toBeInTheDocument();
    expect(screen.getByText('probe:readyz')).toBeInTheDocument();
    expect(screen.getByText('READY')).toBeInTheDocument();
  });

  it('reports retained counts and truncation truthfully per section', async () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    stubMonitorApi(liveSnapshot);
    render(<App />);
    fireEvent.click(navButton('เครื่องมือและการใช้งาน'));
    expect(await screen.findByText('INSPECTOR_FROM_MONITOR_VIEWS')).toBeInTheDocument();
    expect(screen.getByText('เครื่องมือ / Tools')).toBeInTheDocument();
    expect(screen.getByText(/READY 1/)).toBeInTheDocument();
    expect(screen.getAllByText(/ไม่มีรายการที่เก็บไว้/).length).toBeGreaterThanOrEqual(2);
  });

  it('shows usage as unavailable — inventory is never usage history', async () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    stubMonitorApi(liveSnapshot);
    render(<App />);
    fireEvent.click(navButton('เครื่องมือและการใช้งาน'));
    expect(await screen.findByText('USAGE_EVENT_SOURCE_NOT_PROVIDED')).toBeInTheDocument();
    expect(screen.getByText(/inventory ไม่ใช่ usage history/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Run|Invoke/ })).toBeNull();
  });

  it('renders honest unavailable when the inspector projection is absent', () => {
    render(<ToolsView snapshot={snapshot} />);
    expect(screen.getByText('INSPECTOR_NOT_PROVIDED')).toBeInTheDocument();
    expect(screen.getByText(/^ไม่มีหลักฐาน/)).toBeInTheDocument();
  });

  it('renders honest unavailable when no snapshot has loaded', () => {
    render(<ToolsView snapshot={null} />);
    expect(screen.getByText('SNAPSHOT_NOT_LOADED')).toBeInTheDocument();
  });
});
