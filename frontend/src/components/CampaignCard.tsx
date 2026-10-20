import { Fragment } from 'react';
import type { Campaign } from '../types';

export function CampaignCard({ campaign, onClick }: { campaign: Campaign; onClick: () => void }) {
  const statusLabel = campaign.status ?? 'unknown';
  const meta = `${campaign.target_ids?.length ?? 0} target(s) · ${campaign.agents?.length ?? 0} agent(s)`;

  return (
    <button
      type="button"
      className="campaign-card"
      onClick={onClick}
      aria-label={`Open campaign ${campaign.name}`}
    >
      <header className="campaign-card__header">
        <h3 className="campaign-card__name">{campaign.name}</h3>
        <span className={`campaign-card__status badge badge--${statusLabel.toLowerCase()}`}>{statusLabel}</span>
      </header>
      {campaign.description && <p className="campaign-card__desc">{campaign.description}</p>}
      <div className="campaign-card__meta">
        <span>📦 {campaign.target_ids?.length ?? 0} targets</span>
        <span>👥 {campaign.agents?.length ?? 0} agents</span>
        <span>{meta}</span>
      </div>
    </button>
  );
}

export function CampaignTable({ campaigns, loading, error, onSelect }: {
  campaigns: Campaign[];
  loading: boolean;
  error: string | null;
  onSelect: (id: string) => void;
}) {
  if (loading) return <div className="skeleton-row" />;
  if (error) return <div className="alert alert--error">{error}</div>;
  if (campaigns.length === 0) return <div className="empty-state">No campaigns yet. Create one to start.</div>;

  return (
    <table className="table table--campaigns">
      <thead>
        <tr>
          <th>Name</th>
          <th>Domain</th>
          <th>Targets</th>
          <th>Agents</th>
          <th>Status</th>
          <th>Updated</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {campaigns.map((c) => (
          <tr key={c.id}>
            <td className="campaign-table__name">{c.name}</td>
            <td>{c.domain}</td>
            <td className="campaign-table__targets">{c.target_ids?.join(', ') ?? '-'}</td>
            <td>{c.agents?.join(', ') ?? '-'}</td>
            <td><span className={`badge badge--${c.status?.toLowerCase() ?? 'unknown'}`}>{c.status}</span></td>
            <td>{new Date(c.updated_at * 1000).toLocaleString()}</td>
            <td className="campaign-table__actions">
              <button type="button" className="btn btn--ghost" onClick={() => onSelect(c.id)}>Open</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function CampaignCardList({ campaigns, onSelect }: { campaigns: Campaign[]; onSelect: (id: string) => void }) {
  return (
    <div className="campaign-grid">
      {campaigns.map((c) => (
        <Fragment key={c.id}>
          <CampaignCard campaign={c} onClick={() => onSelect(c.id)} />
          <hr className="campaign-grid__divider" />
        </Fragment>
      ))}
    </div>
  );
}
