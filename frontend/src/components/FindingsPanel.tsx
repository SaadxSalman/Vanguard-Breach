import { useState } from 'react';
import { useAlert } from '../hooks/use-alert';
import { useCampaignsCrud } from '../hooks/use-campaigns-crud';
import { findings as fetchFindings, targets, campaign } from '../services/api';
import type { Finding } from '../types';

export function FindingsPanel({ campaignId }: { campaignId?: string }) {
  const { alerts, push, remove } = useAlert();
  const { findings: runFindings = [], refresh, loading } = useFindings(campaignId ?? '');
  const { campaigns, refresh: refreshCamps, loading: campLoading } = useCampaigns();
  const { create, launch, launch: startRun, stop, stop: stopRun, retry, error: crudError, loading: crudLoading } = useCampaignsCrud();
  const [runId, setRunId] = useState<string | null>(null);
  const [msg, setMsg] = useState('');

  const activeFindings = runFindings.filter((f) => campaignId === '' || f.campaign_id === campaignId);

  const handleLaunch = async (id: string) => {
    try {
      const res = await launch(id);
      setRunId(res.run_id);
      push('success', `Run ${res.run_id} launched`);
    } catch (e: unknown) {
      push('error', e instanceof Error ? e.message : String(e));
    }
  };

  const handleStop = async () => {
    if (!runId) return;
    try {
      const ok = await stopRun(runId);
      if (ok) push('success', 'Run stopped');
    } catch (e: unknown) {
      push('error', e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div className="card">
      <h3 className="card__title">Findings workbench</h3>

      <div className="findings-toolbar">
        <div className="field">
          <label>Filter by campaign</label>
          <select
            className="input"
            value={campaignId ?? ''}
            onChange={(e) => {
              const id = e.target.value;
              setCampaignId(id);
              if (id) refresh();
            }}
          >
            <option value="">All campaigns</option>
            {campaigns.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Search terms</label>
          <input
            className="input"
            placeholder="filter findings…"
            onChange={(e) => setMsg(e.target.value)}
          />
        </div>
        <button className="btn btn--primary" onClick={() => refresh()}>Refresh</button>
      </div>

      <div className="findings-list">
        {loading && <div className="skeleton-row" />}
        {!loading && activeFindings.map((f) => (
          <div className="finding-card" key={f.id}>
            <div className="finding-card__head">
              <span className={`severity-badge severity-${f.severity ?? 0}`}>{f.severity?.toFixed(1)}</span>
              <div>
                <strong>{f.title}</strong>
                <span className="finding-card__meta">{f.category} · {f.target_id} · {f.owasp}/{f.atlas}</span>
              </div>
            </div>
            <p className="finding-card__desc">{f.description}</p>
            <div className="finding-card__actions">
              <button className="btn btn--small btn--ghost">Copy remediation</button>
              <button className="btn btn--small btn--ghost">Review</button>
            </div>
          </div>
        ))}
        {!loading && activeFindings.length === 0 && <div className="empty-state">No findings match this filter.</div>}
      </div>
    </div>
  );
}

function useCampaigns() {
  const [items, setItems] = useState<import('../types').Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      setLoading(true);
      const data = await campaigns();
      setItems(data);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, [refresh]);

  return { campaigns: items, loading, error, refresh };
}
