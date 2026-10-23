import { useEffect, useState } from 'react';
import { errorMessage, getConnectors, type Connector } from './api';
import { ConnectorRow } from './ConnectorRow';

export function ConnectorsPanel({ token }: { token: string }) {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(''); setConnectors([]);
    void getConnectors(token, controller.signal).then(value => {
      if (!controller.signal.aborted) setConnectors(value);
    }).catch(cause => {
      if (!controller.signal.aborted) setError(errorMessage(cause));
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [token, attempt]);

  return <section id="connectors" className="panel" aria-labelledby="connectors-title">
    <div className="panel-heading"><h2 id="connectors-title">Connectors</h2>
      <button disabled={loading} onClick={() => setAttempt(value => value + 1)}>Refresh connectors</button></div>
    <p className="muted">App-session records only. Not persisted Tk connectors or runtime health; reset on API restart.</p>
    {error && <p role="alert">{error}</p>}
    {loading ? <p role="status">Loading connectors...</p> : !error && (connectors.length === 0
      ? <p>No connectors created in this API session.</p>
      : <div className="table-scroll"><table>
        <thead><tr><th scope="col">Connector</th><th scope="col">State</th><th scope="col">Actions</th></tr></thead>
        <tbody>{connectors.map(connector => <ConnectorRow key={connector.connector_id} connector={connector} token={token}
          onChanged={() => setAttempt(value => value + 1)} />)}</tbody>
      </table></div>)}
  </section>;
}
