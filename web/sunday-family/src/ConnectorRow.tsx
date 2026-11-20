import { useEffect, useRef, useState } from 'react';
import { errorMessage, mutateConnector, type Connector } from './api';

export function ConnectorRow({ connector, token, onChanged }: {
  connector: Connector; token: string; onChanged: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(connector.name);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);

  async function change(newName?: string) {
    if (pending) return;
    const controller = new AbortController();
    request.current = controller;
    setPending(true); setError('');
    try {
      await mutateConnector(token, controller.signal, connector.connector_id, newName);
      if (!controller.signal.aborted) { setEditing(false); onChanged(); }
    } catch (cause) {
      if (!controller.signal.aborted) setError(`${errorMessage(cause)} Refresh connectors to reconcile before retrying.`);
    } finally {
      if (!controller.signal.aborted) setPending(false);
    }
  }

  return <tr>
    <td><strong>{connector.name}</strong><div className="muted">{connector.connector_id}</div></td>
    <td><span className="status">{connector.state}</span><div className="muted">Session metadata only</div></td>
    <td>
      {editing ? <form className="row-editor" onSubmit={event => { event.preventDefault(); void change(name.trim()); }}>
        <label htmlFor={`rename-${connector.connector_id}`}>Connector name</label>
        <input id={`rename-${connector.connector_id}`} autoFocus required maxLength={128} value={name}
          disabled={pending} onChange={event => setName(event.target.value)} />
        <div className="row-actions"><button disabled={pending || !name.trim()} type="submit">Save name</button>
          <button disabled={pending} type="button" onClick={() => setEditing(false)}>Cancel</button></div>
      </form> : <div className="row-actions">
        <button disabled={pending} onClick={() => { setName(connector.name); setEditing(true); }}>Rename</button>
        <button className="destructive" disabled={pending || connector.state !== 'STOPPED'} onClick={() => {
          if (window.confirm(`Delete connector "${connector.name}"? This removes its app-session record only.`)) void change();
        }}>Delete</button>
      </div>}
      {pending && <p role="status">Updating connector...</p>}
      {error && <p role="alert">{error}</p>}
    </td>
  </tr>;
}
