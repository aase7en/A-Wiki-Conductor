import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { InstallPrompt } from '../src/InstallPrompt';
import { registerServiceWorker } from '../src/pwa';

afterEach(() => vi.unstubAllGlobals());

describe('PWA manifest', () => {
  it('provides valid standalone metadata and matching local SVG dimensions', () => {
    const manifest = JSON.parse(readFileSync(resolve('public/manifest.webmanifest'), 'utf8'));
    expect(manifest).toMatchObject({ start_url: '/', scope: '/', display: 'standalone' });
    for (const key of ['name', 'short_name', 'description', 'theme_color', 'background_color']) expect(manifest[key]).toBeTruthy();
    expect(manifest.icons.map((icon: { sizes: string }) => icon.sizes)).toEqual(['192x192', '512x512']);
    for (const icon of manifest.icons) {
      expect(icon.type).toBe('image/svg+xml');
      const svg = readFileSync(resolve(`public${icon.src}`), 'utf8');
      const size = icon.sizes.split('x')[0];
      expect(svg).toContain(`width="${size}" height="${size}"`);
    }
    const html = readFileSync(resolve('index.html'), 'utf8');
    expect(html).toContain('rel="manifest" href="/manifest.webmanifest"');
  });
});

describe('SW registration', () => {
  it('registers only in production with cache-bypassing update checks', async () => {
    const register = vi.fn().mockResolvedValue({});
    vi.stubGlobal('navigator', { serviceWorker: { register } });
    await registerServiceWorker(false);
    expect(register).not.toHaveBeenCalled();
    await registerServiceWorker(true);
    expect(register).toHaveBeenCalledWith('/sw.js', { scope: '/', updateViaCache: 'none' });
  });
  it('ignores unsupported browsers', async () => {
    vi.stubGlobal('navigator', {});
    await expect(registerServiceWorker(true)).resolves.toBeUndefined();
  });
  it('contains registration failure without breaking the monitor', async () => {
    const warning = vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.stubGlobal('navigator', { serviceWorker: { register: vi.fn().mockRejectedValue(new Error('blocked')) } });
    await expect(registerServiceWorker(true)).resolves.toBeUndefined();
    expect(warning).toHaveBeenCalledOnce();
  });
});

function installEvent(outcome = 'dismissed', reject = false) {
  const event = new Event('beforeinstallprompt', { cancelable: true });
  const prompt = reject ? vi.fn().mockRejectedValue(new Error('blocked')) : vi.fn().mockResolvedValue(undefined);
  Object.assign(event, { prompt, userChoice: Promise.resolve({ outcome }) });
  act(() => { window.dispatchEvent(event); });
  return { event, prompt };
}

describe('install prompt', () => {
  it('stays hidden until eligible; prompts once on a user click and hides on dismissal', async () => {
    render(<InstallPrompt />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    const { event, prompt } = installEvent();
    expect(event.defaultPrevented).toBe(true);
    expect(prompt).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Install app' }));
    await waitFor(() => expect(prompt).toHaveBeenCalledOnce());
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(screen.queryByText('App installed.')).not.toBeInTheDocument();
  });
  it('clears pending prompt on appinstalled and reports actual installation', () => {
    render(<InstallPrompt />);
    installEvent('accepted');
    act(() => { window.dispatchEvent(new Event('appinstalled')); });
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('App installed.');
  });
  it('does not mistake prompt acceptance for completed installation', async () => {
    render(<InstallPrompt />);
    const { prompt } = installEvent('accepted');
    fireEvent.click(screen.getByRole('button'));
    await waitFor(() => expect(prompt).toHaveBeenCalledOnce());
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });
  it('handles rejected prompts without an unhandled rejection', async () => {
    render(<InstallPrompt />);
    installEvent('dismissed', true);
    fireEvent.click(screen.getByRole('button'));
    expect(await screen.findByRole('status')).toHaveTextContent('Installation unavailable');
  });
  it('removes listeners on unmount', () => {
    const { unmount } = render(<InstallPrompt />);
    unmount();
    expect(installEvent().event.defaultPrevented).toBe(false);
  });
});
