import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from '../src/App';
import { API_VERSION } from '../src/api';
import { ActivityView } from '../src/ActivityView';
import { JevView } from '../src/JevView';
import { SettingsView } from '../src/SettingsView';
import { liveSnapshot, snapshot, streamResponse } from './fixtures';

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

describe('Settings section (WO-P1-774 slice D)', () => {
  it('previews only server-reported effective policy with no edit controls', async () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    stubMonitorApi();
    render(<App />);
    fireEvent.click(navButton('ตั้งค่า'));
    expect(screen.getByRole('heading', { level: 1, name: /ตั้งค่า/ })).toBeInTheDocument();
    expect(await screen.findByText('headless-read-only')).toBeInTheDocument();
    expect(screen.getByText(/นโยบายที่มีผลจาก server/)).toBeInTheDocument();
    expect(screen.getAllByText('SETTINGS_READ_MODEL_PENDING').length).toBeGreaterThan(0);
    expect(screen.getByText(/ไม่มีการบันทึกหรือติดตั้งใดๆ จากหน้านี้/)).toBeInTheDocument();
    for (const forbidden of ['Save', 'Install', 'ติดตั้ง', 'บันทึก']) {
      expect(screen.queryByRole('button', { name: forbidden })).toBeNull();
    }
  });

  it('shows an honest error when the policy read fails, never a fabricated policy', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('health read failed')));
    render(<SettingsView token={TOKEN} />);
    expect(await screen.findByText(/อ่านนโยบายไม่สำเร็จ/)).toBeInTheDocument();
    expect(screen.getByText('EFFECTIVE_POLICY_READ_FAILED')).toBeInTheDocument();
    expect(screen.queryByText('headless-read-only')).toBeNull();
  });
});

describe('Jev section (WO-P1-774 slice D)', () => {
  it('renders advisory-only unavailable with no authorization or execute actions', async () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    stubMonitorApi();
    render(<App />);
    fireEvent.click(navButton('มุมตัดสินใจ'));
    expect(screen.getByRole('heading', { level: 1, name: /มุมตัดสินใจ/ })).toBeInTheDocument();
    expect(await screen.findByText('JEV_ADVISORY_UNAVAILABLE')).toBeInTheDocument();
    expect(screen.getAllByText(/คำแนะนำไม่ใช่คำอนุมัติ/).length).toBeGreaterThan(0);
    expect(screen.getByText('UNKNOWN')).toBeInTheDocument();
    for (const forbidden of ['Execute', 'Auto-approve', 'Retry advisory']) {
      expect(screen.queryByRole('button', { name: forbidden })).toBeNull();
    }
  });

  it('renders standalone without snapshot dependency', () => {
    render(<JevView />);
    expect(screen.getByText('JEV_ADVISORY_UNAVAILABLE')).toBeInTheDocument();
  });
});

describe('Activity & Logs section (WO-P1-774 slice D)', () => {
  it('renders monitor timeline as monitor events only, never work progress', async () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    stubMonitorApi(liveSnapshot);
    render(<App />);
    fireEvent.click(navButton('บันทึกกิจกรรม'));
    expect(screen.getByRole('heading', { level: 1, name: /บันทึกกิจกรรม/ })).toBeInTheDocument();
    expect(await screen.findByText('MONITOR_TIMELINE_ONLY')).toBeInTheDocument();
    expect(screen.getAllByText('OBSERVE').length).toBeGreaterThan(0);
    expect(screen.getByText(/2026-11-13T00:00:00Z/)).toBeInTheDocument();
    expect(screen.getByText(/SSE connected ไม่ใช่ความคืบหน้า/)).toBeInTheDocument();
    expect(screen.getByText(/จำนวนแถวที่ได้รับ: 1/)).toBeInTheDocument();
  });

  it('keeps the work-activity region explicitly unavailable', async () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    stubMonitorApi(liveSnapshot);
    render(<App />);
    fireEvent.click(navButton('บันทึกกิจกรรม'));
    expect(await screen.findByText('MONITOR_TIMELINE_ONLY')).toBeInTheDocument();
    expect(screen.getByText('ACTIVITY_READER_UNAVAILABLE')).toBeInTheDocument();
    expect(screen.getAllByText(/^ไม่มีหลักฐาน/).length).toBeGreaterThan(0);
  });

  it('does not claim observed zero when the timeline producer is absent', () => {
    const monitor = liveSnapshot.monitor;
    if ('error' in monitor) throw new Error('expected live fixture');
    const unavailable = {
      ...liveSnapshot,
      monitor: { ...monitor, timeline: [], health: {
        ...monitor.health, conditions: ['MONITOR_BUS_ABSENT'],
      } },
    };
    render(<ActivityView snapshot={unavailable} />);
    expect(screen.getByText('MONITOR_TIMELINE_SOURCE_UNAVAILABLE')).toBeInTheDocument();
    expect(screen.queryByText('0 events')).toBeNull();
    expect(screen.queryByText(/ไม่มีเหตุการณ์ใน timeline นี้/)).toBeNull();
  });

  it('renders timeline unavailable when the monitor projection is absent', () => {
    render(<ActivityView snapshot={snapshot} />);
    expect(screen.getByText('TIMELINE_NOT_PROVIDED')).toBeInTheDocument();
    expect(screen.getAllByText(/^ไม่มีหลักฐาน/).length).toBeGreaterThan(0);
  });

  it('renders honest unavailable when no snapshot has loaded', () => {
    render(<ActivityView snapshot={null} />);
    expect(screen.getByText('SNAPSHOT_NOT_LOADED')).toBeInTheDocument();
  });
});
