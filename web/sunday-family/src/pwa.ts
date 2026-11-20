export async function registerServiceWorker(production = import.meta.env.PROD): Promise<void> {
  if (!production || !('serviceWorker' in navigator)) return;
  try {
    await navigator.serviceWorker.register('/sw.js', { scope: '/', updateViaCache: 'none' });
  } catch {
    // Installation is optional; a blocked SW must not prevent online monitoring.
    console.warn('Offline shell unavailable: service worker registration failed.');
  }
}
