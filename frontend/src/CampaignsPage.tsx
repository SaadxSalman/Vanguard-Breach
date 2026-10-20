import { useState } from 'react';
import { CampaignTable, CampaignLauncher } from '../components/CampaignCard';
import { CampaignDetail } from './App';
import { useCampaigns } from '../hooks/use-campaigns';
import type { Campaign } from '../types';

function CampaignsPage() {
  return (
    <div className="page">
      <section className="page__header">
        <h1>Campaigns</h1>
        <p>Manage attack campaigns — name, domain, targets, and agent swarm.</p>
      </section>
      <CampaignList />
    </div>
  );
}

function CampaignList() {
  const { campaigns, loading, error } = useCampaigns();
  const [selecting, setSelecting] = useState(false);
  const [selected, setSelected] = useState<Campaign | null>(null);

  if (selecting && selected) {
    return (
      <div className="page">
        <section className="page__header">
          <h1>Campaign: {selected.name}</h1>
        </section>
        <CampaignDetail campaign={selected} onBack={() => setSelected(null)} />
      </div>
    );
  }

  return (
    <div className="page">
      <section className="page__header">
        <h1>Campaigns</h1>
        <div className="page__actions">
          <button className="btn btn--primary" onClick={() => setSelecting(true)}>+ New campaign</button>
        </div>
      </section>
      <CampaignTable loading={loading} error={error} campaigns={campaigns} onSelect={(id) => { window.location.href = `/campaigns/${id}`; }} />
    </div>
  );
}

export { CampaignsPage };
