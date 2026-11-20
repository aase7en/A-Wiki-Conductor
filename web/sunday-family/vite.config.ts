import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';
import type { IncomingMessage } from 'node:http';
import type { Plugin } from 'vite';
import { pwaAssets } from './pwa-build';

const hosts = new Set(['127.0.0.1:5173', 'localhost:5173']);
const upstream = 'http://127.0.0.1:8756';
const endpoints = new Set(['/api/v1/health', '/api/v1/snapshot', '/api/v1/stream', '/api/v1/metrics', '/api/v1/connectors']);

export function admittedRequest(request: Pick<IncomingMessage, 'rawHeaders' | 'headers'>): boolean {
  for (const name of ['host', 'origin', 'authorization']) {
    let count = 0;
    for (let i = 0; i < request.rawHeaders.length; i += 2) {
      if (request.rawHeaders[i].toLowerCase() === name) count++;
    }
    if (count > 1) return false;
  }
  const { host, origin } = request.headers;
  return typeof host === 'string' && hosts.has(host)
    && (origin === undefined || origin === `http://${host}`);
}

function loopbackGuard(): Plugin {
  return {
    name: 'sunday-loopback-guard',
    configureServer(server) {
      // Installed before Vite's proxy. Never rewrite an unvalidated authority.
      server.middlewares.use((request, response, next) => {
        if (!admittedRequest(request)) {
          response.writeHead(403).end('Forbidden Host or Origin');
          return;
        }
        if (request.url?.startsWith('/api')) {
          const read = request.method === 'GET' && endpoints.has(request.url);
          const connectorMutation = (request.method === 'PATCH' || request.method === 'DELETE')
            && /^\/api\/v1\/connectors\/conn-[a-f0-9]{8}$/.test(request.url);
          if (!read && !connectorMutation) {
            response.writeHead(405).end('Supported monitor endpoint required');
            return;
          }
        }
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [loopbackGuard(), react(), pwaAssets()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    cors: false,
    allowedHosts: ['localhost'],
    proxy: {
      '/api': {
        target: upstream,
        changeOrigin: true,
        headers: { origin: upstream },
        ws: false,
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    restoreMocks: true,
  },
});
