import { useState } from 'react';
import { useAlert } from '../hooks/use-alert';
import { useCampaignsCrud } from '../hooks/use-campaigns-crud';
import { campaigns, targets } from '../services/api';
import type { Campaign } from '../types';

export function CampaignLauncher() {
  const { alerts, push, remove } = useAlert();
  const { create, launch, loading, error } = useCampaignsCrud();
  const [name, setName] = useState('');
  const [domain, setDomain] = useState('general');
  const [targetIds, setTargetIds] = useState<string[]>([]);
  const [agents, setAgents] = useState<string[]>(['scout', 'planner', 'injector', 'chain']);
  const [targets, setTargets] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const fetchTargets = async () => {
    try {
      const data = await targets();
      setTargets(data.map((t) => t.id));
    } catch {
      /* empty */
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSubmitting(true);
    try {
      const camp = await create({ name, description: `Autonomous assessment of ${targets.length} target(s)`, domain, target_ids: targetIds.length ? targetIds : undefined, agents });
      push('success', `Campaign '${name}' created (id ${camp.id})`);
      // don't auto-launch; user clicks Launch once they've reviewed
    } catch (e: unknown) {
      push('error', e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card">
      <h3 className="card__title">🚀 Launch a campaign</h3>
      <form className="form-inline" onSubmit={handleSubmit}>
        <div className="form-field">
          <label htmlFor="camp-name">Campaign name</label>
          <input
            id="camp-name"
            className="input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Q4 LLM fleet test"
          />
        </div>
        <div className="form-field">
          <label htmlFor="camp-domain">Domain</label>
          <select
            id="camp-domain"
            className="input"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
          >
            <option value="general">General</option>
            <option value="healthcare">Healthcare</option>
            <option value="finance">Finance</option>
            <option value="legal">Legal</option>
            <option value="retail">Retail</option>
            <option value="saas">SaaS</option>
          </select>
        </div>
        <div className="form-field">
          <label className="sr-only" htmlFor="camp-targets">Select targets</label>
          <select
            id="camp-targets"
            className="input"
            multiple
            value={targetIds}
            onChange={(e) => {
              const next = Array.from(e.target.selectedOptions).map((o) => o.value);
              setTargetIds(next);
            }}
          >
            {targets.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <span className="hint">Hold Ctrl/Cmd to multi-select.</span>
        </div>
        <div className="form-field">
          <label className="sr-only" htmlFor="camp-agents">Select agents</label>
          <select
            id="camp-agents"
            className="input"
            multiple
            value={agents}
            onChange={(e) => {
              const next = Array.from(e.target.selectedOptions).map((o) => o.value);
              setAgents(next);
            }}
          >
            <option value="scout">Scout</option>
            <option value="planner">Planner</option>
            <option value="injector">Injector</option>
            <option value="inversion">Inversion</option>
            <option value="poisoner">Poisoner</option>
            <option value="mcp">MCP Auditor</option>
            <option value="chain">Chain Exploit</option>
          </select>
          <span className="hint">Hold Ctrl/Cmd to multi-select.</span>
        </div>
        <div className="form-actions">
          <button type="button" className="btn btn--secondary" onClick={fetchTargets}>Refresh targets</button>
          <button type="submit" className="btn btn--primary" disabled={submitting || !name.trim()}>
            {submitting ? 'Creating…' : 'Create campaign'}
          </button>
        </div>
      </form>
      {error && <div className="alert alert--error">{error}</div>}
      <div className="alert-list">
        {alerts.map((a) => (
          <div key={a.id} className={`alert ${a.type === 'success' ? 'alert--success' : a.type === 'error' ? 'alert--error' : a.type === 'warning' ? 'alert--warning' : 'alert--info'}`}>
            {a.message}
            <button type="button" className="alert__close" onClick={() => remove(a.id)}>×</button>
          </div>
        ))}
      </div>
    </div>
  );
}
