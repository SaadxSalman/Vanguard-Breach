export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  env: string;
  time: number;
}

export interface ProviderStatus {
  configured_provider: string;
  active_provider: string;
  degraded_to_simulation: boolean;
  key_present: boolean;
  key_masked: string | null;
}

export interface EmbeddingStatus {
  provider: string;
  local_dim: number;
}

export interface VectorStoreStatus {
  backend: string;
  url: string;
  uri: string;
  collections: Record<string, unknown>;
}

export interface SandboxStatus {
  mode: string;
  targets: string[];
}

export interface ProvidersConfig {
  llm: ProviderStatus;
  embeddings: EmbeddingStatus;
  vector_store: VectorStoreStatus;
  sandbox: SandboxStatus;
  auth_enabled: boolean;
  env_file: string;
}

export interface Campaign {
  id: string;
  name: string;
  description: string;
  domain: string;
  target_ids: string[];
  agents: string[];
  config: Record<string, unknown>;
  status: string;
  latest_run: RunSummary | null;
  created_at: number;
  updated_at: number;
}

export interface RunSummary {
  id: string;
  status: string;
  created_at: number;
  progress: number;
  finished_at?: number;
  started_at?: number;
}

export interface RunDetail extends RunSummary {
  campaign_id: string;
  stats: Record<string, unknown>;
  has_graph: boolean;
  findings_count: number;
  error?: string;
}

export interface TargetDescriptor {
  id: string;
  name: string;
  vendor: string;
  domain: string;
  kind: string;
  description: string;
  system_prompt_excerpt: string;
  system_prompt_chars: number;
  tools: ToolDef[];
  tenants: string[];
  corpus_size: number;
  guardrail: Record<string, unknown>;
}

export interface ToolDef {
  name: string;
  args: string[];
  scope: string;
  danger: string;
  gate?: boolean;
}

export interface Finding {
  id: string;
  run_id: string;
  campaign_id: string;
  title: string;
  category: string;
  severity: number;
  severity_label: string;
  owasp: string;
  atlas: string;
  target_id: string;
  description: string;
  evidence: Record<string, unknown>;
  remediation: string;
  chain_id: string;
  status: string;
  created_at: number;
}

export interface CampaignRun {
  id: string;
  campaign_id: string;
  status: string;
  current_node: string;
  progress: number;
  seed: number;
  stats: string;
  error: string;
  started_at?: number;
  finished_at?: number;
  created_at: number;
}

export interface EventPayload {
  level: string;
  node: string;
  agent: string;
  message: string;
  data: Record<string, unknown>;
}

export interface BaseResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface ProbeRequest {
  target_id: string;
  message: string;
  user_id?: string;
  tenant?: string;
}

export interface ProbeResponse {
  target_id: string;
  response: Record<string, unknown>;
}

export interface IngestionDoc {
  title: string;
  content: string;
  category?: string;
  source?: string;
  meta?: Record<string, unknown>;
}

export interface IngestResponse {
  id: string;
  title: string;
  category: string;
}

export interface MutationDemo {
  [mutator: string]: string;
}

export interface KnowledgeStats {
  total_docs: number;
  by_source: Record<string, number>;
  by_category: Record<string, number>;
  store: Record<string, unknown>;
  embedding_provider: string;
}

export interface Report {
  markdown: string;
  html: string;
  json: Record<string, unknown>;
}
