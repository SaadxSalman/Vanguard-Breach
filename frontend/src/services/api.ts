import type { BaseResponse, Campaign, CampaignRun, EventPayload, Finding, HealthStatus, IngestionDoc, IngestResponse, ProbeRequest, ProbeResponse, KnowledgeStats, ProvidersConfig, Report, RunDetail, SandboxStatus, VectorStoreStatus } from '../types';

const API = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    let msg = `Request failed: ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) msg = body.detail;
    } catch {
      /* ignore non-json bodies */
    }
    throw new Error(msg);
  }
  return (await res.json()) as T;
}

export const health = () => request<HealthStatus>('/system/health');
export const providers = () => request<ProvidersConfig>('/system/providers');
export const dashboard = () => request('/dashboard');
export const targets = () => request<TargetDescriptor[]>('/targets');
export const targetDetail = (id: string) => request<TargetDescriptor>(`/targets/${id}`);
export const campaigns = () => request<Campaign[]>('/campaigns');
export const campaign = (id: string) => request<Campaign>(`/campaigns/${id}`);
export const runDetail = (id: string) => request<RunDetail>(`/runs/${id}`);
export const runEvents = (id: string, sinceId = 0) =>
  request<EventPayload[]>(`/runs/${id}/events?since_id=${sinceId}`);
export const findings = (runId?: string) => {
  const q = runId ? `?run_id=${runId}` : '';
  return request<Finding[]>(`/findings${q}`);
};
export const createCampaign = (body: { name: string; description: string; domain: string; target_ids: string[]; agents: string[]; config?: Record<string, unknown> }) =>
  request<Campaign>('/campaigns', {
    method: 'POST',
    body: JSON.stringify(body),
  });
export const deleteCampaign = (id: string) =>
  fetch(`${API}/campaigns/${id}`, { method: 'DELETE' });
export const launchCampaign = (id: string, opts?: { seed?: number; max_iterations?: number; severity_threshold?: number }) =>
  request<{ run_id: string; campaign_id: string; status: string }>(`/campaigns/${id}/launch`, {
    method: 'POST',
    body: JSON.stringify(opts),
  });
export const stopCampaign = (id: string) =>
  fetch(`${API}/campaigns/${id}/stop`, { method: 'POST' });
export const pauseCampaign = (id: string) =>
  fetch(`${API}/campaigns/${id}/pause`, { method: 'POST' });
export const resumeCampaign = (id: string) =>
  fetch(`${API}/campaigns/${id}/resume`, { method: 'POST' });
export const retryCampaign = (id: string) =>
  fetch(`${API}/campaigns/${id}/retry`, { method: 'POST' });
export const probeTarget = (body: ProbeRequest) =>
  request<ProbeResponse>('/targets/probe', {
    method: 'POST',
    body: JSON.stringify(body),
  });
export const ingestDoc = (doc: IngestionDoc) =>
  request<IngestResponse>('/knowledge/ingest', {
    method: 'POST',
    body: JSON.stringify(doc),
  });
export const deleteDoc = (id: string) =>
  fetch(`${API}/knowledge/${id}`, { method: 'DELETE' });
export const knowledgeStats = () => request<KnowledgeStats>('/knowledge/stats');
export const knowledgeEntries = (source?: string) => {
  const q = source ? `?source=${source}` : '';
  return request<Record<string, unknown>[]>(`/knowledge/entries${q}`);
};
export const reindexKnowledge = () =>
  request<Record<string, unknown>>('/knowledge/reindex', { method: 'POST' });
export const mutationDemos = () => request<Record<string, string>>('/knowledge/mutations');
export const reports = (runId: string) => request<Report>(`/reports/${runId}?format=json`);
export const deleteReport = (id: string) =>
  fetch(`${API}/reports/${id}`, { method: 'DELETE' });
export const listReports = () => request<Record<string, unknown>[]>('/reports');

export const ws = (runId: string): WebSocket => {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return new WebSocket(`${protocol}//${location.host}/ws/runs/${runId}`);
};

export const settings = {
  toggle: (key: string, value: boolean) =>
    fetch(`${API}/settings/toggles`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key, value }),
    }).then<BaseResponse>(r => r.json()),
  reseed: () => fetch(`${API}/settings/reseed`, { method: 'POST' }).then<BaseResponse>(r => r.json()),
  reindex: () => fetch(`${API}/settings/reindex`, { method: 'POST' }).then<BaseResponse>(r => r.json()),
};
