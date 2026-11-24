import { useEffect, useState } from 'react';
import { errorMessage, getHealth, type Health } from './api';
import { sectionMeta } from './sections';
import { EmptyState, ReasonLine } from './StatusPanels';

// WO-P1-774 slice D: Settings read-only. The only accepted source is the
// server-reported effective policy (/health: profile/version/degraded/
// conditions) rendered as a preview. No settings DTO exists for anything
// else; there is no Save/Install and no browser policy authority.
// Wording settled with Jev 2026-11-18 (overpromise noul 0.27 = no risk).
export function SettingsView({ token }: { token: string }) {
  const meta = sectionMeta('settings');
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setError('');
    void getHealth(token, controller.signal).then(value => {
      if (!controller.signal.aborted) setHealth(value);
    }).catch(cause => {
      if (!controller.signal.aborted) setError(errorMessage(cause));
    });
    return () => controller.abort();
  }, [token, attempt]);

  return <>
    <section className="panel" aria-labelledby="settings-policy-title">
      <div className="panel-heading"><h2 id="settings-policy-title">{meta.thai} / {meta.english} — นโยบายที่มีผลจาก server</h2></div>
      <p className="muted">แสดงเฉพาะค่าที่ server รายงาน — ไม่มีการบันทึกหรือติดตั้งใดๆ จากหน้านี้</p>
      {error ? <div role="alert" className="notice">
        <p>อ่านนโยบายไม่สำเร็จ — ไม่มีค่าที่จะแสดง</p>
        <ReasonLine reason="EFFECTIVE_POLICY_READ_FAILED" source="/api/v1/health" observedAt={null} />
        <button onClick={() => setAttempt(value => value + 1)}>อ่านนโยบายอีกครั้ง</button>
      </div> : health ? <>
        <dl className="metrics-grid" aria-live="polite">
          <div><dt>Profile</dt><dd>{health.profile}</dd></div>
          <div><dt>Version</dt><dd>{health.version}</dd></div>
          <div><dt>Degraded</dt><dd>{String(health.degraded)}</dd></div>
        </dl>
        {health.conditions.length > 0
          ? <ul className="conditions">{health.conditions.map(condition => <li key={condition}>{condition}</li>)}</ul>
          : <p className="muted">ไม่มีเงื่อนไขผิดปกติที่รายงาน</p>}
        <ReasonLine reason={meta.reasonCode} source="/api/v1/health (policy preview only)" observedAt={null} />
      </> : <p role="status">กำลังอ่านนโยบายจาก server...</p>}
    </section>
    <section className="panel" aria-labelledby="settings-models-title">
      <div className="panel-heading"><h2 id="settings-models-title">Models &amp; Agents (อ่านอย่างเดียว)</h2>
        <span className="status">SECTION_UNAVAILABLE</span></div>
      <EmptyState reason={meta.reason} source="settings read model (card 05)" />
      <ReasonLine reason={meta.reasonCode} source="settings read model" observedAt={null} />
      <p className="sf-boundary">{meta.boundary}</p>
    </section>
  </>;
}
