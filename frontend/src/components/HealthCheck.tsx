import { useEffect, useState } from 'react';
import { health } from '../services/api';
import type { HealthStatus } from '../types';

export function HealthCheck() {
  const [status, setStatus] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const data = await health();
        if (alive) setStatus(data);
      } catch {
        if (alive) setStatus({ status: 'degraded', service: 'vanguard-breach', version: '1.0.0', env: 'unknown', time: Date.now() });
      }
      setLoading(false);
    };
    tick();
    const id = setInterval(tick, 15000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  if (loading) return <div className="health-loading">Checking runtime health…</div>;

  return (
    <div className="health-card">
      <div className={`health-status health-${status?.status ?? 'unknown'}`}>{status?.status ?? 'unknown'}</div>
      <dl className="health-meta">
        <dt>Service</dt><dd>{status?.service ?? '-'}</dd>
        <dt>Version</dt><dd>{status?.version ?? '-'}</dd>
        <dt>Env</dt><dd>{status?.env ?? '-'}</dd>
        <dt>Time</dt><dd>{new Date(status?.time ?? Date.now()).toLocaleString()}</dd>
      </dl>
    </div>
  );
}
