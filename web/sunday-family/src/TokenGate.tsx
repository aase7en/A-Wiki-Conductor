import { useState, type ReactNode } from 'react';

const TOKEN_KEY = 'sunday-family.monitor-token';

export function TokenGate({ children }: { children: (token: string, disconnect: () => void) => ReactNode }) {
  const [token, setToken] = useState(() => {
    try { return sessionStorage.getItem(TOKEN_KEY) ?? ''; } catch { return ''; }
  });
  const [error, setError] = useState('');

  function disconnect() {
    try { sessionStorage.removeItem(TOKEN_KEY); } catch { /* Memory is cleared even if storage is blocked. */ }
    setToken('');
  }

  if (token) return children(token, disconnect);

  return <main className="token-gate">
    <section className="panel token-panel" aria-labelledby="gate-title">
      <p className="eyebrow">SUNDAY FAMILY / READ-ONLY MONITOR</p>
      <h1 id="gate-title">Connect to Conductor</h1>
      <p>Enter the local Monitor API bearer token. It stays in this tab's session storage, never in a URL.</p>
      <form onSubmit={event => {
        event.preventDefault();
        const form = event.currentTarget;
        const value = String(new FormData(form).get('token') ?? '').trim();
        if (!value || /\s/.test(value)) { setError('Enter a token without whitespace.'); return; }
        try {
          sessionStorage.setItem(TOKEN_KEY, value);
          form.reset();
          setError('');
          setToken(value);
        } catch { setError('Session storage is unavailable. Enable it to connect.'); }
      }}>
        <label htmlFor="monitor-token">Bearer token</label>
        <input id="monitor-token" name="token" type="password" required autoComplete="off" spellCheck={false} />
        {error && <p role="alert">{error}</p>}
        <button type="submit">Connect monitor</button>
      </form>
      <p className="muted">Local development: 127.0.0.1:5173 &gt; 127.0.0.1:8756</p>
    </section>
  </main>;
}
