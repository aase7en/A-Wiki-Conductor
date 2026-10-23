// @vitest-environment node
import { describe, expect, it } from 'vitest';
import { createServer as createHttpServer, request } from 'node:http';
import { createServer as createViteServer } from 'vite';
import config, { admittedRequest } from '../vite.config';

describe('proxy authority guard', () => {
  it.each(['127.0.0.1:5173', 'localhost:5173'])('admits exact local authority %s', host => {
    expect(admittedRequest({ rawHeaders: ['Host', host], headers: { host } })).toBe(true);
    expect(admittedRequest({ rawHeaders: ['Host', host, 'Origin', `http://${host}`], headers: { host, origin: `http://${host}` } })).toBe(true);
  });
  it.each([
    { host: 'evil.example:5173' },
    { host: 'localhost:5174' },
    { host: 'localhost:5173.evil.example' },
    { host: '127.0.0.1:5173', origin: 'https://evil.example' },
    { host: '127.0.0.1:5173', origin: 'null' },
    { host: '127.0.0.1:5173', origin: 'http://localhost:5173' },
    {},
  ])('rejects mismatched or missing authority %j', headers => {
    expect(admittedRequest({ rawHeaders: [], headers })).toBe(false);
  });
  it.each(['Host', 'Origin', 'Authorization'])('rejects duplicate %s before forwarding', name => {
    expect(admittedRequest({ rawHeaders: [name, 'one', name.toLowerCase(), 'two'], headers: { host: '127.0.0.1:5173' } })).toBe(false);
  });

  it('guards real proxy traffic before rewriting Host/Origin and preserves bearer headers', async () => {
    const forwarded: { host?: string; origin?: string; authorization?: string }[] = [];
    const backend = createHttpServer((req, res) => {
      forwarded.push(req.headers);
      res.writeHead(200, { 'Content-Type': 'text/event-stream' });
      res.end(': heartbeat\n\n');
    });
    await new Promise<void>(resolve => backend.listen(0, '127.0.0.1', resolve));
    const backendPort = (backend.address() as { port: number }).port;
    const server = await createViteServer({
      ...config, configFile: false,
      server: { ...config.server, port: 0, strictPort: false, hmr: false, proxy: {
        '/api': { target: `http://127.0.0.1:${backendPort}`, changeOrigin: true, headers: { origin: 'http://127.0.0.1:8756' }, ws: false },
      } },
    });
    try {
      await server.listen();
      const port = (server.httpServer!.address() as { port: number }).port;
      function probe(headers: Record<string, string | string[]>, method = 'GET', path = '/api/v1/stream') {
        return new Promise<number>(resolve => {
          const req = request({ host: '127.0.0.1', port, path, method, headers }, res => {
            res.resume(); res.on('end', () => resolve(res.statusCode!));
          });
          req.end();
        });
      }
      expect(await probe({ Host: '127.0.0.1:5173', Origin: 'https://evil.example' })).toBe(403);
      expect(await probe({ Host: 'evil.example:5173' })).toBe(403);
      expect(await probe({ Host: '127.0.0.1:5173', Origin: ['http://127.0.0.1:5173', 'https://evil.example'] })).toBe(403);
      expect(await probe({ Host: '127.0.0.1:5173' }, 'POST')).toBe(405);
      expect(await probe({ Host: '127.0.0.1:5173' }, 'GET', '/api/v1/stream?token=forbidden')).toBe(405);
      expect(forwarded).toHaveLength(0);
      expect(await probe({ Host: '127.0.0.1:5173', Origin: 'http://127.0.0.1:5173', Authorization: 'Bearer test-only-token' })).toBe(200);
      expect(forwarded).toHaveLength(1);
      expect(forwarded[0]).toMatchObject({ host: `127.0.0.1:${backendPort}`, origin: 'http://127.0.0.1:8756', authorization: 'Bearer test-only-token' });
      for (const path of ['/api/v1/metrics', '/api/v1/connectors']) {
        expect(await probe({ Host: '127.0.0.1:5173' }, 'GET', path)).toBe(200);
      }
      for (const method of ['PATCH', 'DELETE']) {
        expect(await probe({ Host: '127.0.0.1:5173', Origin: 'https://evil.example' }, method, '/api/v1/connectors/conn-1234abcd')).toBe(403);
        expect(await probe({ Host: '127.0.0.1:5173', Authorization: 'Bearer test-only-token', 'X-Confirm': 'test-confirmation' }, method, '/api/v1/connectors/conn-1234abcd')).toBe(200);
        expect(await probe({ Host: '127.0.0.1:5173' }, method, '/api/v1/connectors/conn-1234abcd?token=forbidden')).toBe(405);
        expect(await probe({ Host: '127.0.0.1:5173' }, method, '/api/v1/workers/a-worker-test')).toBe(405);
      }
      expect(forwarded).toHaveLength(5);
      expect(forwarded[4]).toMatchObject({ authorization: 'Bearer test-only-token', 'x-confirm': 'test-confirmation' });
    } finally {
      await server.close();
      await new Promise<void>((resolve, reject) => backend.close(error => error ? reject(error) : resolve()));
    }
  });
});
