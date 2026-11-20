import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from '../src/App';
import { API_VERSION } from '../src/api';
import { WorkView } from '../src/WorkView';
import { SECTIONS } from '../src/sections';
import { snapshot, streamResponse } from './fixtures';

const TOKEN = 'test-only-token';

function stubMonitorApi(payload = snapshot) {
  const fetch = vi.fn().mockImplementation((path: string) => {
    if (path.endsWith('/health')) return Promise.resolve(Response.json({
      api_version: API_VERSION, status: 'ok', degraded: false, profile: 'headless-read-only', version: '1', conditions: [],
    }));
    if (path.endsWith('/snapshot')) return Promise.resolve(Response.json(payload));
    if (path.endsWith('/connectors')) return Promise.resolve(Response.json({ scope: 'app-session', connectors: [] }));
    return Promise.resolve(streamResponse([`data: ${JSON.stringify(payload)}\n\n`]));
  });
  vi.stubGlobal('fetch', fetch);
  return fetch;
}

function navButton(thai: string) {
  return screen.getByRole('button', { name: new RegExp(thai) });
}

afterEach(() => vi.unstubAllGlobals());

describe('Work & Lanes section (WO-P1-774 slice B)', () => {
  it('renders cockpit lane projection with truth metadata', async () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    stubMonitorApi();
    render(<App />);
    fireEvent.click(navButton('งานและเลน'));
    expect(screen.getByRole('heading', { level: 1, name: /งานและเลน/ })).toBeInTheDocument();
    expect(await screen.findByText('WO-P1-690')).toBeInTheDocument();
    expect(screen.getByText('a-worker-01')).toBeInTheDocument();
    expect(screen.getByText('LANE_PROJECTION_FROM_COCKPIT')).toBeInTheDocument();
    expect(screen.getAllByText(/2026-10-21T05:00:00Z/).length).toBeGreaterThan(0);
    expect(screen.getByText('1 observed')).toBeInTheDocument();
  });

  it('groups Projects/Claims/Roadmap inside Work & Lanes as honest unavailable, never top-level', async () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    stubMonitorApi();
    render(<App />);
    fireEvent.click(navButton('งานและเลน'));
    for (const code of ['PROJECT_DTO_NOT_PROVIDED', 'CLAIM_PROJECTION_NOT_PROVIDED', 'ROADMAP_DTO_NOT_PROVIDED']) {
      expect(await screen.findByText(code)).toBeInTheDocument();
    }
    expect(screen.getAllByText(/^ไม่มีหลักฐาน/).length).toBeGreaterThanOrEqual(3);
    expect(screen.queryByText(/^0 (โปรเจกต์|งาน|รายการ)/)).toBeNull();
    const nav = screen.getByRole('navigation', { name: 'ส่วนงานหลัก / Primary sections' });
    expect(nav.querySelectorAll('.nav-item')).toHaveLength(SECTIONS.length);
    expect(screen.queryByRole('button', { name: /โปรเจกต์/ })).toBeNull();
  });

  it('states unknown owner/HEAD/claim explicitly as ไม่ทราบ', async () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    stubMonitorApi();
    render(<App />);
    fireEvent.click(navButton('งานและเลน'));
    expect(await screen.findByText('CLAIM_PROJECTION_NOT_PROVIDED')).toBeInTheDocument();
    expect(screen.getAllByText(/ไม่ทราบ/).length).toBeGreaterThanOrEqual(3);
  });

  it('surfaces stale snapshots instead of rendering them current', () => {
    const stale = { ...snapshot, stale: true, stale_reason: 'WORK_STALE_TEST' };
    render(<WorkView snapshot={stale} error="" onRetry={() => {}} />);
    expect(screen.getByText('Stale: WORK_STALE_TEST')).toBeInTheDocument();
  });

  it('renders an honest empty statement when the snapshot has no lanes', () => {
    render(<WorkView snapshot={{ ...snapshot, cockpit: { lanes: [] } }} error="" onRetry={() => {}} />);
    expect(screen.getByText('No execution lanes in this snapshot.')).toBeInTheDocument();
  });

  it('fails closed on an unrecognized lane state code', () => {
    const ghost = { ...snapshot, cockpit: { lanes: [{ ...snapshot.cockpit.lanes[0], state: 'GHOST' }] } };
    render(<WorkView snapshot={ghost} error="" onRetry={() => {}} />);
    expect(screen.getByText(/รหัสสถานะไม่รู้จัก/)).toBeInTheDocument();
  });

  it('shows canonical cockpit states and MC-1 wait details without calling them UNKNOWN', () => {
    const waiting = {
      ...snapshot.cockpit.lanes[0], state: 'WAITING_CI',
      wait_reason: 'CI_QUEUE', next_recheck_at: '2026-11-20T12:00:00Z',
      countdown_seconds: 42, capacity_class: 'PARKED',
    };
    const cooldown = { ...snapshot.cockpit.lanes[0], state: 'COOLDOWN' };
    const verified = { ...snapshot.cockpit.lanes[0], state: 'COMPLETED_VERIFIED' };
    const { container } = render(<WorkView
      snapshot={{ ...snapshot, cockpit: { lanes: [waiting, cooldown, verified] } }}
      error="" onRetry={() => {}} />);
    for (const state of ['WAITING_CI', 'COOLDOWN', 'COMPLETED_VERIFIED']) {
      expect(container.querySelector(`.sf-badge[data-state="${state}"]`)).not.toBeNull();
    }
    expect(screen.getByText(/CI_QUEUE/)).toBeInTheDocument();
    expect(screen.getByText(/2026-11-20T12:00:00Z/)).toBeInTheDocument();
    expect(screen.getByText(/42 seconds/)).toBeInTheDocument();
    expect(screen.getByText(/PARKED/)).toBeInTheDocument();
  });

  it('shows an honest unavailable panel when no snapshot has loaded', () => {
    render(<WorkView snapshot={null} error="Snapshot unavailable" onRetry={() => {}} />);
    expect(screen.getByText(/^ไม่มีหลักฐาน/)).toBeInTheDocument();
    expect(screen.getByText('SNAPSHOT_NOT_LOADED')).toBeInTheDocument();
    expect(screen.getByText('Snapshot unavailable')).toBeInTheDocument();
  });
});
