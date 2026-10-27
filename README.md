<h1 align="center">⛨ Vanguard-Breach</h1>

<p align="center">
  <b>An autonomous GenAI red-teaming platform that leverages hierarchical adversarial RAG and
  multi-agent reasoning to discover, map, and exploit trust-boundary failures, vector-store
  leaks, and indirect prompt injections in enterprise LLM deployments.</b>
</p>

<p align="center">
  <a href="#-quickstart-60-seconds">Quickstart</a> ·
  <a href="#-architecture">Architecture</a> ·
  <a href="#-the-agent-swarm">Agents</a> ·
  <a href="#-adversarial-knowledge-rag-layer">Adversarial RAG</a> ·
  <a href="#-sandbox--protocol-layer">Sandbox Targets</a> ·
  <a href="#-rest--websocket-api-reference">API</a> ·
  <a href="#-configuration-the-env-file">.env</a> ·
  <a href="#-docker--production-deployment">Docker</a>
</p>

---

## Table of Contents

1. [What Vanguard-Breach Does](#-what-vanguard-breach-does)
2. [The Core Idea: Inverting RAG](#-the-core-idea-inverting-rag)
3. [Architecture](#-architecture)
4. [The Five System Layers](#-the-five-system-layers)
5. [The Agent Swarm](#-the-agent-swarm)
6. [Adversarial Knowledge RAG Layer](#-adversarial-knowledge-rag-layer)
7. [The Mutation Engine](#-the-mutation-engine)
8. [Sandbox & Protocol Layer](#-sandbox--protocol-layer)
9. [Behavioral Drift Monitor](#-behavioral-drift-monitor)
10. [Attack Graph Synthesis & Reporting](#-attack-graph-synthesis--reporting)
11. [Remediation Code Synthesizer](#-remediation-code-synthesizer)
12. [LLM Providers & Simulation Brain](#-llm-providers--simulation-brain)
13. [Quickstart (60 seconds)](#-quickstart-60-seconds)
14. [Configuration: The `.env` File](#-configuration-the-env-file)
15. [Running the Frontend Console](#-running-the-frontend-console)
16. [REST & WebSocket API Reference](#-rest--websocket-api-reference)
17. [Docker & Production Deployment](#-docker--production-deployment)
18. [Testing](#-testing)
19. [Project Structure](#-project-structure)
20. [Threat Model Coverage (OWASP LLM Top-10 × MITRE ATLAS)](#-threat-model-coverage)
21. [Security, Ethics & Authorized Use](#-security-ethics--authorized-use)
22. [Troubleshooting](#-troubleshooting)
23. [Roadmap](#-roadmap)
24. [License](#-license)

---

## 🎯 What Vanguard-Breach Does

Enterprise LLM deployments — RAG copilots, tool-using agents, MCP gateways, multi-tenant
vector knowledge bases — fail in ways traditional scanners cannot see. A WAF never sees the
zero-width character that reassembles into "ignore previous instructions." A DLP rule never
models the *confused deputy* that reads a poisoned spreadsheet cell and emails a database
dump to an attacker.

**Vanguard-Breach is an autonomous red-team** that plans and executes those attacks against
your applications — in a sandbox or against staging — and returns enterprise-grade output:

| You get | What it looks like |
|---|---|
| 🔍 **Confirmed findings** | Classified, deduplicated, scored 0–10, mapped to OWASP LLM Top-10 + MITRE ATT&CK for ATLAS |
| 🕸️ **Attack graphs** | Layered visualization of exactly how input crossed each trust boundary: input → retrieval → model → tool → data |
| 🔗 **Exploit chains** | Multi-step paths connecting low-severity leaks into high-impact outcomes (prompt theft → override → privileged tool call) |
| 📉 **Drift telemetry** | Per-target refusal/compliance baselines vs. attack phases, with the *collapse iteration* where guardrails durably failed |
| 🧪 **Evidence** | Every finding carries the exact request, response excerpt, mutation chain and model-strength score that produced it |
| 🛠️ **Remediation code** | Production-ready Python/YAML: input sanitizers, instruction-hierarchy context builders, per-tool authorization, tenant pre-filters, MCP hardening configs |
| 📑 **Reports** | Markdown, standalone HTML (with inline SVG attack graph) and machine-readable JSON in `data/reports/` |

Everything runs **offline by default**. The deterministic *simulation brain* plans attacks,
evolves payloads against target feedback, and reasons about exploit chains without a single
API call. The moment you add keys to `.env`, the same agent graph transparently upgrades to
DeepSeek-R1 / vLLM-served Llama-3-70B / OpenAI / Anthropic reasoning.

## 🧠 The Core Idea: Inverting RAG

Retrieval-Augmented Generation retrieves *helpful* data to answer a user prompt.
**Vanguard-Breach retrieves adversarial data to construct attack payloads.**

```
Normal RAG:   user question ──► vector search ──► helpful docs ──► grounded answer
Vanguard:     target profile ──► vector search ──► OWASP/ATLAS techniques
                                        + mutation patterns ──► synthesized exploit payload
                                        ──► sandbox execution ──► classified response ──► finding
```

When a campaign targets a healthcare copilot, the **Planner** embeds the domain context
("healthcare · patient data · RAG · triage") and retrieves context-specific bypass vectors,
semantic traps and known boundary failures from a threat corpus built from the OWASP LLM
Top-10, MITRE ATLAS techniques, and curated injection/poisoning/evasion patterns. The
**Injector** then renders each technique with domain objectives and chains 1–2 *syntactic
mutations* (zero-width interleaving, homoglyphs, markdown smuggling, CSV-cell embedding…)
before firing. The result is a payload set that is semantically targeted *and* filter-evading.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          VANGUARD-BREACH CONSOLE (React + Vite)               │
│   Dashboard · Campaigns · Live Run Monitor · Attack Graph · Knowledge · etc. │
└───────────────▲──────────────────────────────────▲───────────────────────────┘
                │ REST /api/*                       │ WebSocket /ws/runs/{id}
┌───────────────┴──────────────────────────────────┴───────────────────────────┐
│                        FastAPI APPLICATION  (backend/app)                     │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │            ORCHESTRATOR — LangGraph-style StateGraph engine             │  │
│  │  scout → planner → injector → inversion → poisoner → mcp               │  │
│  │        → ⟦conditional⟧ chain → graph_synth → remediation → report      │  │
│  │        → finalize                                                      │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────┐ ┌───────────────────┐ ┌─────────────────────────────────┐  │
│  │ Adversarial  │ │  LLM Router       │ │  Sandbox & Protocol Layer       │  │
│  │ RAG Layer    │ │  simulation ◄─────┤ │  mediassist · finguard          │  │
│  │  threats     │ │  openai/deepseek  │ │  opspilot · knowsphere          │  │
│  │  mutations   │ │  anthropic/vllm   │ │  agentmesh (MCP)                │  │
│  │  poisoning   │ │  ollama           │ │  (+ dockerized remote fleet)    │  │
│  │  user_docs   │ └───────────────────┘ └─────────────────────────────────┘  │
│  └──────────────┘                                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ Analysis: detectors · severity scoring · drift monitor · attack graph  │  │
│  │           remediation synthesizer · report generator (md/html/json)    │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│  Persistence: SQLite (campaigns, runs, events, findings, graphs, vectors)     │
└───────────────────────────────────────────────────────────────────────────────┘
        │ local cosine store (default)     │ optional
        ▼                                  ▼
   data/vanguard.db                  Qdrant / Milvus (docker-compose profile)
```

**Stack:** Python 3.12+ (FastAPI · Pydantic · httpx · SQLite) · React 19 + TypeScript +
Vite · local cosine vector store or Qdrant/Milvus over REST · OpenAI-compatible &
Anthropic HTTP providers · zero hard dependency on any vector DB or model API.

---

## 🧩 The Five System Layers

### 1 · Adversarial Knowledge RAG Layer (the tactical brain)

The intelligence repository that replaces static wordlists:

- **Dynamic threat indexing** — the seed corpus ships **76 entries**: all ten OWASP LLM
  Top-10 categories, 14 MITRE ATLAS techniques (T1511, T1524, T1552, T1578, T1543…),
  24 injection patterns, 12 evasion patterns, 18 mutation patterns, 10 poisoning playbooks.
  `POST /api/knowledge/reindex` re-embeds everything; `POST /api/knowledge/ingest` adds your
  own research, CVE write-ups or internal incident data.
- **Semantic vector retrieval** — campaigns match target domain context to techniques via
  the embedding space, so a finance campaign reaches KYC/transaction objectives and
  privilege-negotiation payloads, while a SaaS campaign reaches canary-hunt and
  agent-goal-hijack payloads.
- **Dynamic prompt-mutation store** — a dedicated `mutations` collection stores obfuscation
  families as retrievable snippets; the Injector consults it when a target's filter blocks
  a payload and the adaptive enrichment loop deploys a mutated variant.

### 2 · Multi-Agent Adversarial Orchestration (the swarm)

Seven autonomous agents with specialized behaviors — detailed below. Execution is a
**typed state graph** with static edges, a *conditional* edge (chain exploitation only
fires when a finding ≥ severity threshold exists), per-node telemetry and step tracing.

### 3 · Semantic Simulation & Poisoning Engine

- **Controlled KB poisoning** — the Poisoner plants latent directives inside plausible
  "Onboarding FAQ" documents in each RAG target's corpus, then issues a benign retrieval
  query. If the payload executes inside the answer, a `poisoning` finding (OWASP LLM04 /
  ATLAS T1524) is filed with the propagating document id as evidence.
- **Multi-tenant canary testing** — seeded canary tokens (`CANARY-TKA-*`, `CANARY-TKB-*`
  from `.env`) are probed across security profiles; any token surfacing in output is an
  automatic CRITICAL.
- **Embedding Inversion Lab** — the Inversion Specialist maps each tenant document's
  k-nearest neighbours and counts cross-tenant links, quantifying how much corpus topology
  an adversary can reconstruct from the shared embedding space.

### 4 · Execution & Protocol Sandbox

Five in-process target applications with *engineered* flaws (see Sandbox layer below), plus
an optional dockerized fleet (`VANGUARD_SANDBOX_MODE=remote`) for out-of-process realism.
The MCP Auditor probes context→tool authority gaps, cross-server relays, shared-cache
session leakage, ungated dangerous tools and origin-tagging gaps.

### 5 · Attack Graph Synthesis & Reporting Engine

Trust-boundary-crossing paths rendered as layered graphs (console SVG + inline SVG in HTML
reports), multi-step chain validation, and a Remediation Synthesizer that emits real
guardrail code per finding category.

## 🤖 The Agent Swarm

| Agent | Graph node | What it actually does |
|---|---|---|
| **Scout** | `scout` | Sends benign probes to every target; extracts the attack surface: system-prompt length, tool inventory with danger ratings, tenant lists, enabled guardrail layers. Feeds the Planner and the graph builder. |
| **Planner** | `planner` | Loads the domain playbook (healthcare/finance/legal/retail/saas/general), runs contextual RAG queries over threat + mutation collections, chooses a high-value tool target, and produces the payload plan (`plan_attack`). |
| **Injector** | `injector` | Executes the baseline (benign) phase for the drift monitor, then fires every payload against every selected target. When a target refuses or an input filter blocks, it asks the router to *enrich* the payload (mutation engine / LLM rewrite) and re-fires an adaptive variant. Feeds the detectors on every exchange. |
| **Inversion Specialist** | `inversion` | Runs tenant canary probes against the multi-tenant vector KB and performs embedding-inversion analysis: per-document k-NN mapping with cross-tenant neighbor counting. |
| **Poisoner** | `poisoner` | Plants latent-directive documents into RAG corpora, triggers retrieval, and verifies whether the payload propagated into model behavior (indirect injection at inference time). |
| **MCP Auditor** | `mcp` | Session-isolation tests (two clients, identical request, cache-key collision detection), confirmation-gate coverage, schema-poisoning surface, origin-tagging gaps, and a cross-server relay probe that tries to reach money tools through reprioritized context. |
| **Chain-Exploiter** | `chain` *(conditional)* | Runs capability-based chain reasoning over confirmed findings (leak → steer → act; poison → persist → exfil; MCP gap → ungated execution), then **verifies** each chain by checking every referenced finding is still confirmed. Only ≥ threshold findings qualify. |
| **Graph/Report synthesis** | `graph_synth` → `remediation` → `report` → `finalize` | Attack graph assembly, drift report finalization, remediation synthesis, report persistence, stats aggregation and findings storage. |

**Agent toggles** are per-campaign (`agents: [...]`); disabled agents emit a skip event and
the graph routes around them. The *Injector* and *Scout* always run — they are the minimum
viable assessment.

### The orchestration engine

`backend/app/core/graph_engine.py` is a faithful, dependency-free re-implementation of
LangGraph's StateGraph semantics: `add_node`, `add_edge`, `add_conditional_edges`,
entry/finish points, compiled execution with `RunTrace` (per-node status + duration),
async-aware node invocation and a `max_steps` loop guard. It keeps Vanguard-Breach
installable on any Python 3.12+ box with `pip install fastapi uvicorn httpx`.

---

## 📚 Adversarial Knowledge RAG Laye

Collections (all queryable at `POST /api/knowledge/search`):

| Collection | Contents | Source files |
|---|---|---|
| `threats` | OWASP LLM Top-10, MITRE ATLAS techniques, 24 injection patterns, 12 evasion patterns | `backend/app/data/seed/*.json` |
| `mutations` | 18 obfuscation families with descriptions and severity hints | `mutation_patterns.json` |
| `poisoning` | 10 poisoning playbooks (appendix, white-text, metadata, ticket, memory, tool-schema, CSV, cross-tenant, scraper-bait) | `poisoning_patterns.json` |
| `user_docs` | Operator-ingested documents (also the staging ground for controlled poisoning drills) | API uploads |

**Embedding providers** (`VANGUARD_EMBEDDING_PROVIDER`):

- `local` *(default)* — deterministic signed hashing over unigrams, bigrams and char
  3-grams, L2-normalized, 384-dim. No downloads, no API keys, and char-ngrams make it
  robust enough for technique matching.
- `openai` — `text-embedding-3-small` (configurable).
- `ollama` — BGE-Large / nomic-embed-text served locally (`OLLAMA_EMBEDDING_MODEL`).

**Vector backends** (`VANGUARD_VECTOR_STORE`): `local` (SQLite-persisted cosine index with
in-memory cache and payload filters; NumPy auto-accelerates if installed), `qdrant`
(REST upsert/query/count with api-key header), `milvus` (v2 REST: create/upsert/search).

---

## 🧬 The Mutation Engine

`backend/app/core/mutations/engine.py` — every mutator is `f(text, rng) -> text`, chains are
composable and deterministic per campaign seed:

| Family | Mutators | Evasion target |
|---|---|---|
| **encoding** | `base64`, `rot13`, `reverse`, `urlencode`, `quoted_printable`, `json_escape` | keyword/WAF signature matching pre-decode |
| **unicode** | `zwsp` (zero-width interleaving), `homoglyph` (Cyrillic а/е/о…), `fullwidth` | blocklists that never normalize; visual review |
| **structural** | `markdown_smuggle`, `comment_hide`, `split_lines`, `acrostic`, `polyglot`, `csv_cell` | filters that don't parse markdown/HTML/CSV context |
| **perturbation** | `whitespace`, `typo`, `leetspeak` | exact-token rules and human review |

`obfuscation_score(text)` is exported for guardrail research — the hardened sandbox target
uses a keyword filter on *raw* text while the simulated model reads *normalized* text;
that asymmetry is exactly why mutations work in the real world, and why FinGuard's first
line of defense fails while its refusal tuning still holds.

---

## 🧪 Sandbox & Protocol Layer

Five in-process enterprise applications, each with deliberately engineered flaws — the
platform's ground truth. They behave like staging deployments: retrieval, guardrail layers,
tool execution, audit logs, tenant partitions.

| Target | Kind | Domain | Engineered flaws | Typical findings |
|---|---|---|---|---|
| **MediAssist Patient Copilot** (`mediassist`) | naive RAG | healthcare | no input sanitization, substring retrieval, "helper note" doc instructing token echo, secrets in system prompt (`sbx-root-*`, `sk-*`) | credential exfiltration (LLM02/LLM07), instruction override (LLM01), poison propagation (LLM04) |
| **FinGuard Advisory Assistant** (`finguard`) | hardened RAG | finance | defense-in-depth: keyword input filter + refusal tuning + secret output filter — but the filter runs on raw text (obfuscation bypass) and ingested docs bypass it entirely | indirect injection via poisoned corpus, redaction evidence (`secrets_redacted`), blocked-attempt telemetry |
| **OpsPilot Workflow Agent** (`opspilot`) | tool agent | saas | excessive agency: `send_email`, `query_db`, `http_fetch`, `create_ticket`, `delete_user` execute on any tool-shaped instruction; no confirmation gate, no origin tagging | unauthorized tool execution (LLM06, severity by tool danger rating) |
| **KnowSphere Enterprise KB** (`knowsphere`) | vector KB | saas | shared embedding space + post-ranking tenant filter with **graceful-degradation fallback** (weak same-tenant matches backfill from other tenants) | cross-tenant retrieval (LLM08/T1530), canary token leakage, cross-tenant neighborhood mapping |
| **AgentMesh MCP Gateway** (`agentmesh`) | MCP | saas | cache key = request hash only (cross-client session reuse), tool descriptions rendered as instructions, confirmation gate on 1 of 5 dangerous tools, no origin tags | session/context leak, ungated critical tools, tool-schema poisoning, cross-server relay → refund execution |

**Remote mode** — `VANGUARD_SANDBOX_MODE=remote` swaps the in-process registry for
`RemoteTarget` adapters that POST to a dockerized fleet at `VANGUARD_TARGET_BASE_URL`
(`docker compose --profile sandbox up`). The `chat()` JSON contract is unchanged, so every
agent works without modification.

**Live probing** — `POST /api/targets/probe` sends any message to any target from the
console's Targets page and returns the full structured response (text, retrieved docs,
tool calls, guardrail meta), so you can hand-test payloads before launching a campaign.

---

## 📉 Behavioral Drift Monitor

The Injector records a **baseline phase** (benign questions) and an **attack phase** per
target, then the graph computes:

- refusal rate & compliance rate, baseline → attack, per target
- average response length shift and refusal-marker density shift
- **collapse iteration** — the first iteration where attack-phase compliance runs in a
  durable window while the baseline refusal regime was intact

That number is the story defenders need: *"your filter held for 8 exchanges, then a chained
obfuscation collapsed it at iteration 9."* Drift lands in run stats, the console Run
Monitor and the report.

---

## 🗺️ Attack Graph Synthesis & Reporting

The graph builder converts findings into a layered DAG:

| Layer | Node types |
|---|---|
| 0 | `user_input` — the payload that started it |
| 1 | `app` — the target application |
| 2 | `retrieval` — context assembly (present when poisoning/indirect/mutation evidence exists) |
| 3 | `model` — the LLM decision point |
| 4 | `tool` / `vector` / `protocol` / `data` — where the damage landed |
| 5 | `chain` — validated multi-step chain nodes |

Edges crossing layers are labeled with the trust boundary they defeated
("Internet → App input boundary", "Untrusted corpus → Model context boundary",
"Model output → Tool/actuation boundary", "Tenant A → Tenant B data boundary",
"Agent context → MCP control-plane boundary"). The console renders interactive SVG; the
HTML report embeds a static SVG built by the same layout logic.

Reports are written to `data/reports/{run_id}.{md,html,json}` and served by
`GET /api/reports/{run_id}?format=md|html|json`.

## 🛠️ Remediation Code Synthesizer

Findings don't ship as prose — they ship as code. Per category the synthesizer emits
interpolated, production-ready artifacts (also embedded in reports and the console
Remediation tab):

| Category | Artifacts |
|---|---|
| `direct_injection` | `sanitize_untrusted_text()` (NFKC + zero-width strip + comment strip + directive-density budget) and `build_context()` (instruction hierarchy: `<system>` > `<untrusted>` blocks re-asserted after every retrieval) + guardrail YAML |
| `indirect_injection` | untrusted-context wrapping + doc-level directive drop rules |
| `poisoning` | `scan_before_ingest()` with quarantine hashing + provenance/trust-scoring YAML |
| `tool_abuse` | `authorize_tool_call()` allowlist keyed to the **end-user role** with confirmation gates and context-auth stripping + tool policy YAML |
| `vector_abuse` | `build_query()` with mandatory `tenant_id` pre-filter and `graceful_degradation: false`, plus a CI `canary_probe()` |
| `mcp` | hardened MCP config: `context_authority_check`, per-client session cache, untrusted tool descriptions, confirmation gates, origin tagging |
| `info_disclosure` / `prompt_leak` | `output_guard()` deny-by-default egress filter (secret regex + prompt-egress patterns) |

## 🧩 LLM Providers & Simulation Brain

`VANGUARD_LLM_PROVIDER` selects the reasoning backend. **Every provider failure degrades
transparently to the simulation brain** — a run never dies because an API is down.

| Provider | Backing | Notes |
|---|---|---|
| `simulation` *(default)* | `SimulationBrain` | Deterministic attack planning, mutation-based enrichment, capability-graph chain reasoning, report summarization. 100% offline. |
| `openai` | OpenAI chat completions | `OPENAI_MODEL` / `OPENAI_DEEP_MODEL` |
| `deepseek` | DeepSeek API (OpenAI-compatible) | `deepseek-r1` for deep reasoning, `deepseek-chat` for fast fuzzing enrichment |
| `vllm` | self-hosted vLLM server | point `VLLM_BASE_URL` at DeepSeek-R1-Distill or Llama-3-70B-Instruct |
| `anthropic` | `/v1/messages` | `ANTHROPIC_MODEL` |
| `ollama` | local OpenAI-compatible endpoint | convenience wrapper |

`plan_attack`/`summarize` use the deep model; `enrich_payload` uses the fast model.
`GET /api/settings/providers` reports the active provider, masked key presence and
degradation state.

---

## 🚀 Quickstart (60 seconds)

### Prerequisites

- **Python 3.12+** (tested on 3.14) and **Node 18+** (tested on 26)
- No Docker, no GPU, no API keys required — the default configuration is fully offline

### 1 · Backend

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

```bash
# macOS / Linux
python3 -m venv .venv
./.venv/bin/pip install -r backend/requirements.txt
cd backend && ../.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

On startup the server initializes SQLite (`data/vanguard.db`), seeds the 76-entry
adversarial knowledge base, and serves:

- API docs → <http://127.0.0.1:8000/docs>
- Health → <http://127.0.0.1:8000/api/health>

### 2 · Frontend console

```powershell
cd frontend
npm install
npm run dev          # → http://localhost:5173 (proxies /api + /ws to :8000)
```

### 3 · Launch your first campaign

Console: **Campaigns → New Campaign** → pick domain `saas`, select all five targets,
**Launch**. Watch the live event feed, then open the **Attack Graph** tab.

Or from the CLI:

```powershell
cd backend
..\.venv\Scripts\python scripts\e2e_campaign.py     # full-fleet run, prints a summary
..\.venv\Scripts\python scripts\smoke_targets.py    # target behavior sanity check
```

Or via API:

```bash
curl -X POST http://127.0.0.1:8000/api/campaigns \
  -H "Content-Type: application/json" \
  -d '{"name":"Fleet check","domain":"saas","target_ids":["mediassist","opspilot","knowsphere","agentmesh"],"agents":["scout","planner","injector","inversion","poisoner","mcp","chain"]}'
curl -X POST http://127.0.0.1:8000/api/campaigns/cmp_xxx/launch -H "Content-Type: application/json" -d '{}'
```

### 4 · (Optional) production build serving

```powershell
cd frontend && npm run build          # emits frontend/dist
# restart the backend — it automatically serves dist/ at "/" with SPA fallback
```

---

## ⚙️ Configuration: The `.env` File

All keys live in **one root `.env`** (git-ignored; there is no `.env.example` on purpose —
clone, edit, run). Real environment variables always win over file values. Reference:
`backend/app/config.py` → `Settings`.

### Core platform

| Key | Default | Purpose |
|---|---|---|
| `VANGUARD_HOST` / `VANGUARD_PORT` | `127.0.0.1` / `8000` | API bind |
| `VANGUARD_DATA_DIR` | `data` | runtime data root |
| `VANGUARD_DB_PATH` | `data/vanguard.db` | SQLite database |
| `VANGUARD_CORS_ORIGINS` | `http://localhost:5173,…` | comma-separated allowlist |
| `VANGUARD_AUTH_ENABLED` | `false` | enforce `X-API-Key` on `/api/*` and `?key=` on WS |
| `VANGUARD_API_KEY` | `vb-console-key-…` | the console key |
| `VANGUARD_LOG_LEVEL` | `INFO` | logging |

### LLM providers

| Key | Default | Purpose |
|---|---|---|
| `VANGUARD_LLM_PROVIDER` | `simulation` | `simulation\|openai\|anthropic\|deepseek\|vllm\|ollama` |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` / `OPENAI_DEEP_MODEL` | — / v1 / gpt-4o-mini / gpt-4o | OpenAI (+ embeddings: `OPENAI_EMBEDDING_MODEL`) |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | — / claude-sonnet-4-5 | Anthropic reasoning |
| `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL` / `DEEPSEEK_FAST_MODEL` | — / api.deepseek.com / deepseek-r1 / deepseek-chat | DeepSeek hybrid |
| `VLLM_BASE_URL` / `VLLM_API_KEY` / `VLLM_MODEL` / `VLLM_FAST_MODEL` | localhost:8001 / — / Llama-3-70B / R1-Distill-70B | self-hosted serving |
| `OLLAMA_BASE_URL` / `OLLAMA_EMBEDDING_MODEL` | localhost:11434 / bge-large | local models |
| `VANGUARD_LLM_TIMEOUT_SECONDS` / `VANGUARD_LLM_MAX_RETRIES` / `VANGUARD_LLM_TEMPERATURE` | 60 / 2 / 0.7 | call behavior |

### Embeddings & vector store

| Key | Default | Purpose |
|---|---|---|
| `VANGUARD_EMBEDDING_PROVIDER` | `local` | `local\|openai\|ollama` |
| `VANGUARD_LOCAL_EMBEDDING_DIM` | `384` | hashing-encoder dimension |
| `VANGUARD_VECTOR_STORE` | `local` | `local\|qdrant\|milvus` |
| `QDRANT_URL` / `QDRANT_API_KEY` / `QDRANT_COLLECTION` | localhost:6333 / — / vanguard_threats | Qdrant REST |
| `MILVUS_URI` / `MILVUS_TOKEN` / `MILVUS_COLLECTION` | localhost:19530 / — / vanguard_threats | Milvus v2 REST |

### Campaign engine & sandbox

| Key | Default | Purpose |
|---|---|---|
| `VANGUARD_MAX_CHAIN_DEPTH` | `4` | max chained exploit steps |
| `VANGUARD_MAX_ITERATIONS` | `12` | injector loop budget per run |
| `VANGUARD_SEVERITY_THRESHOLD` | `6.0` | findings ≥ this feed the Chain-Exploiter |
| `VANGUARD_DEFAULT_SEED` | `1337` | deterministic mutation seed |
| `VANGUARD_SANDBOX_MODE` | `inprocess` | `inprocess\|remote` |
| `VANGUARD_TARGET_BASE_URL` | localhost:8100 | remote sandbox fleet |
| `TARGET_SUPERUSER_TOKEN`, `TARGET_INTERNAL_API_KEY`, `TARGET_DB_WRITE_TOKEN`, `TARGET_SUPPORT_BOT_TOKEN` | see file | seeded "secrets" the targets can leak |
| `CANARY_TENANT_A` / `CANARY_TENANT_B` | `CANARY-TKA-*` / `CANARY-TKB-*` | tenant canary tokens |

---

| Key | Default | Purpose |
|---|---|---|
| `VANGUARD_SANDBOX_MODE` | inprocess | inprocess \| remote |
| `VANGUARD_TARGET_BASE_URL` | http://localhost:8000 | telemetry service base URL |
| `TARGET_SUPERUSER_TOKEN` | superuser-token-12345 | seed secret used for credential-exfiltration tests |
| `TARGET_INTERNAL_API_KEY` | internal-api-key-98765 | seed secret for internal API key tests |
| `TARGET_DB_WRITE_TOKEN` | db-write-token-12345 | seed secret for DB-writer-token tests |
| `TARGET_SUPPORT_BOT_TOKEN` | support-bot-token-12345 | seed secret for support-bot tests |
| `CANARY_TENANT_A` / `CANARY_TENANT_B` | CANARY-TKA-* / CANARY-TKB-* | multi-tenant canary tokens |
| `SANDBOX_TARGET_MESSAGES` | seed messages | seed user messages injected at startup |
| `SANDBOX_TARGET_GET_MESSAGE` | message template | default target message template |
| `SANDBOX_EMBEDDING_MODEL` | text-embedding-3-small | vector store embedding model |

### Feature flags / offline mode

| Key | Default | Purpose |
|---|---|---|
| `VANGUARD_OFFLINE_MODE` | true | run 100% without LLM APIs |
| `VANGUARD_SANDBOX_SEED` | 1337 | deterministic sandbox seed |
| `VANGUARD_DEMO_MODE` | false | report demo watermark |

### Deployment

| Key | Default | Purpose |
|---|---|---|
| `VANGUARD_ENV` | development | development \| production |
| `VANGUARD_SECURE_COOKIES` | true | HTTPS-only cookies in production |
| `QDRANT_URL` / `QDRANT_API_KEY` | — / — | Qdrant remote store |
| `MILVUS_URI` / `MILVUS_TOKEN` | — / — | Milvus remote store |
| `VANGUARD_VECTOR_STORE` | local | local \| qdrant \| milvus |

### Terraform / IaC

| Key | Default | Purpose |
|---|---|---|
| `TF_VAR_github_token` | — | GitHub token for TF |
| `TF_VAR_org_id` / `TF_VAR_project_id` | — / — | org/project identifiers |
| `TF_VAR_region` | us-east-1 | default region |
| `TF_VAR_vanguard_env` | development | env name |
| `TF_VAR_ip_permissions` | — | firewall rules |

---

## 🧭 Running the Frontend Console

`frontend/` is a Vite + React + TypeScript SPA:

| Command | Meaning |
|---|---|
| `npm install` | install dependencies |
| `npm run dev` | fast HMR dev server on :5173, proxy `/api` + `/ws` → :8000 |
| `npm run build` | type-check + production Vite build → `frontend/dist` |
| `npm run preview` | static preview of the production build |
| `npm run check` | `tsc --noEmit` + ESLint |

The console is a single-page app — every route is resolved to `/index.html` by the
backend's SPA fallback, so deep links work when served from the backend.

| Tab | What it shows |
|---|---|
| **Dashboard** | last run stats, active campaign badge, provider status, click-to-launch |
| **Campaigns** | table + detail: domain, targets, agents, status, pause/resume/stop/retry |
| **Run Monitor** | real-time event stream + live drift mini-chart + live attack graph |
| **Targets** | target inventory with flaw color coding + **Probe** form |
| **Strategy** | plan transcript (scout/planner/injector stages) + provenance |
| **Findings** | aggregated + per-run table → findings detail with evidence, drift, remediation |
| **Remediation** | per-finding code dropdowns, copy/paste |
| **Knowledge** | corpus graph + status badges + ingest button |
| **Reports** | list of generated reports + download |
| **Settings** | provider keys UI (masked), per-campaign overrides, export/import |

---

---

## 🔌 REST & WebSocket API Reference

### Auth

- `POST /api/auth/register` → obtain console `api_key`
- `POST /api/auth/login` → JS console login; returns `access_token` (HTTP-only cookie)
- `GET /api/auth/me` → current user
- Headers: `X-API-Key: <api_key>` on all `/api/*` endpoints; WS: `?key=` + key.

### Campaigns

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/campaigns` | create (name, domain, targets[], agents[]) |
| GET | `/api/campaigns` | list with stats |
| GET | `/api/campaigns/{id}` | detail + findings |
| POST | `/api/campaigns/{id}/launch` | start (event bus) |
| POST | `/api/campaigns/{id}/pause` | pause |
| POST | `/api/campaigns/{id}/resume` | resume |
| POST | `/api/campaigns/{id}/stop` | graceful stop |
| POST | `/api/campaigns/{id}/retry` | reset + restart |
| GET | `/api/campaigns/{id}/stats` | run statistics + summary |
| DELETE | `/api/campaigns/{id}` | delete |

### Runs (live telemetry)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/runs` | run overview |
| GET | `/api/runs/{id}` | run event history |
| GET | `/api/runs/{id}/stats` | final stats + report URL |
| WS | `/ws/runs/{id}` | live backtick-stream events |
| POST | `/api/runs/{id}/replay` | rewind to index |

### Targets

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/targets` | inventory + flaw flags |
| POST | `/api/targets/probe` | send any message to any target |
| POST | `/api/targets/reset` | reset a target |

### Knowledge base

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/knowledge` | collections + counts |
| GET | `/api/knowledge/search?q=` | semantic retrieval |
| POST | `/api/knowledge/reindex` | rebuild embeddings |
| POST | `/api/knowledge/ingest` | upload a doc |
| DELETE | `/api/knowledge/{id}` | delete |

### System / settings

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/system/health` | readiness probes |
| GET | `/api/system/metrics` | live counters (events, findings, drift) |
| PUT | `/api/system/settings` | per-campaign overrides |
| GET | `/api/settings/providers` | LLM provider status + masked key presence |
| GET | `/api/settings/flags` | toggle booleans |
| POST | `/api/settings/toggles` | programmatic toggles |
| POST | `/api/settings/reseed` | reset deterministic seeds |
| POST | `/api/settings/reindex` | recompute corpus embeddings |

### Reports

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/reports` | report manifest |
| GET | `/api/reports/{id}?format=md\|html\|json` | download |
| DELETE | `/api/reports/{id}` | delete |

### Health & diagnostics

- `GET /api/health` — instant liveness check (does not start the DB) — **the SPA fallback
  is the only route the server guards with a `/`**; all others return 404 before routing.

## 🔌 REST & WebSocket API Reference

### Auth

- `POST /api/auth/register` → obtain console `api_key`
- `POST /api/auth/login` → JS console login; returns `access_token` (HTTP-only cookie)
- `GET /api/auth/me` → current user
- Headers: `X-API-Key: <api_key>` on all `/api/*` endpoints; WS: `?key=` + key.

### Campaigns

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/campaigns` | create (name, domain, targets[], agents[]) |
| GET | `/api/campaigns` | list with stats |
| GET | `/api/campaigns/{id}` | detail + findings |
| POST | `/api/campaigns/{id}/launch` | start (event bus) |
| POST | `/api/campaigns/{id}/pause` | pause |
| POST | `/api/campaigns/{id}/resume` | resume |
| POST | `/api/campaigns/{id}/stop` | graceful stop |
| POST | `/api/campaigns/{id}/retry` | reset + restart |
| GET | `/api/campaigns/{id}/stats` | run statistics + summary |
| DELETE | `/api/campaigns/{id}` | delete |

### Runs (live telemetry)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/runs` | run overview |
| GET | `/api/runs/{id}` | run event history |
| GET | `/api/runs/{id}/stats` | final stats + report URL |
| WS | `/ws/runs/{id}` | live backtick-stream events |
| POST | `/api/runs/{id}/replay` | rewind to index |

### Targets

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/targets` | inventory + flaw flags |
| POST | `/api/targets/probe` | send any message to any target |
| POST | `/api/targets/reset` | reset a target |

### Knowledge base

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/knowledge` | collections + counts |
| GET | `/api/knowledge/search?q=` | semantic retrieval |
| POST | `/api/knowledge/reindex` | rebuild embeddings |
| POST | `/api/knowledge/ingest` | upload a doc |
| DELETE | `/api/knowledge/{id}` | delete |

### System / settings

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/system/health` | readiness probes |
| GET | `/api/system/metrics` | live counters (events, findings, drift) |
| PUT | `/api/system/settings` | per-campaign overrides |
| GET | `/api/settings/providers` | LLM provider status + masked key presence |
| GET | `/api/settings/flags` | toggle booleans |
| POST | `/api/settings/toggles` | programmatic toggles |
| POST | `/api/settings/reseed` | reset deterministic seeds |
| POST | `/api/settings/reindex` | recompute corpus embeddings |

### Reports

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/reports` | report manifest |
| GET | `/api/reports/{id}?format=md\|html\|json` | download |
| DELETE | `/api/reports/{id}` | delete |

### Health & diagnostics

- `GET /api/health` — instant liveness check (does not start the DB) — **the SPA fallback
  is the only route the server guards with a `/`**; all others return 404 before routing.

---
