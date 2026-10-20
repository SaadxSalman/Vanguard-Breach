import { useState } from 'react';
import { useStream } from '../hooks/use-stream';
import { useCampaignRun } from '../hooks/use-campaign-run';
import { useFindings } from '../hooks/use-campaigns';
import { EventStream } from './EventStream';
import type { Finding } from '../types';

export function RunMonitor({ runId }: { runId: string }) {
  const { run, loading, refresh } = useCampaignRun(runId);
  const { findings: runFindings = [], refresh: refreshFindings } = useFindings(runId);
  const { events, connected } = useStream(runId);

  useEffect(() => {
    if (runId) refresh();
  }, [runId, refresh]);

  const bySeverity = useMemo(() => {
    const map: Record<string, number> = {};
    for (const f of runFindings) {
      map[f.severity_label ?? 'INFO'] = (map[f.severity_label ?? 'INFO'] ?? 0) + 1;
    }
    return map;
  }, [runFindings]);

  return (
    <div className="run-monitor">
      <div className="run-monitor__header">
        <h2>Run Monitor</h2>
        <div className="run-monitor__meta">
          <span>run: <code>{runId}</code></span>
          <span>status: <strong className={`badge badge--${run?.status?.toLowerCase() ?? 'unknown'}`}>{run?.status}</strong></span>
          <span>progress: {run?.progress ?? 0}%</span>
        </div>
      </div>

      <div className="run-monitor__grid">
        <div className="card">
          <h3 className="card__title">Live Stream</h3>
          <EventStream runId={runId} />
        </div>

        <div className="card">
          <h3 className="card__title">Stats</h3>
          <div className="stats-grid">
            <div className="stat"><span className="stat__value">{run?.findings_count ?? 0}</span><span className="stat__label">Findings</span></div>
            <div className="stat"><span className="stat__value">{loading ? '…' : run?.progress ?? 0}%</span><span className="stat__label">Progress</span></div>
            <div className="stat"><span className="stat__value">{run?.has_graph ? '✓' : '✗'}</span><span className="stat__label">Attack Graph</span></div>
            <div className="stat"><span className="stat__value">{runFindings.length}</span><span className="stat__label">Findings (this run)</span></div>
          </div>
        </div>

        <div className="card">
          <h3 className="card__title">Findings</h3>
          <div className="findings-list">
            {runFindings.slice(0, 8).map((f) => (
              <div className="finding-row" key={f.id}>
                <span className={`severity-badge severity-${f.severity ?? 0}`}>{f.severity?.toFixed(1)}</span>
                <span className="finding-row__title">{f.title}</span>
                <span className="finding-row__cat">{f.category}</span>
                <span className="finding-row__target">{f.target_id}</span>
              </div>
            ))}
            {runFindings.length === 0 && <div className="muted">No findings recorded yet.</div>}
          </div>
        </div>
      </div>

      <div className="run-monitor__drift">
        <h3 className="card__title">Drift summary</h3>
        <div className="drift-mini">
          {Object.entries(bySeverity).map(([label, n]) => (
            <div key={label} className="drift-chip">
              <span className={`badge badge--${label.toLowerCase()}`}>{label}</span>
              <span>{n}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
