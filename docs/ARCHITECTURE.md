# Architecture Guide

## 1. Purpose

This document describes the technical architecture of the web registration automation platform, including runtime components, data flow, fault-tolerance behavior, and cloud execution lifecycle.

---

## 2. System Context

The platform automates product registration into a web application and provides operational intelligence through historical datasets and a Streamlit dashboard.

Core design goals:

- deterministic automated form submission
- resilient execution in local and cloud contexts
- traceable outcomes per run and per record
- management-friendly observability

---

## 3. High-Level Components

### 3.1 Automation Runtime (`cadastro_web.py`)

Responsibilities:

- read source dataset (`data/produtos.csv`)
- authenticate in target web app
- fill and submit registration form per record
- validate submission with evidence signals
- apply fallback logic when frontend evidence is unstable
- persist structured outputs in `logs/`

### 3.2 Cloud Orchestrator (`registration-web.yml`)

Responsibilities:

- provision Python + Chrome runner
- execute automation with parameterized runtime controls
- generate summary payloads
- update historical datasets
- publish artifacts and execution summary
- optionally notify stakeholders by email

### 3.3 Analytics Upsert Scripts (`scripts/`)

- `summarize_run.py`: extracts latest run KPIs from report CSV
- `update_history.py`: upserts run-level dataset
- `update_detailed_history.py`: upserts record-level dataset

### 3.4 Executive Dashboard (`dashboard.py`)

Responsibilities:

- render KPIs and trends
- expose failure investigation tables
- support filtering and exports
- use local logs when available, with cloud-safe fallback to analytics datasets

---

## 4. End-to-End Data Flow

```text
data/produtos.csv
    -> cadastro_web.py
    -> logs/relatorio_cadastro_*.csv
    -> scripts/summarize_run.py
    -> logs/run_summary.json + logs/run_summary.md
    -> scripts/update_history.py            -> analytics/history_runs.csv
    -> scripts/update_detailed_history.py   -> analytics/detailed_runs.csv
    -> dashboard.py (logs + analytics + optional remote URLs)
```

---

## 5. Automation Runtime Internals

### 5.1 Input Validation Layer

`carregar_tabela()` validates:

- file existence
- required columns contract
- optional slicing by offset/limit

### 5.2 Selector Strategy

The automation uses selector lists per field and attempts each locator with bounded timeout (`encontrar_elemento`).

Benefit:

- improved adaptability against moderate UI selector drift

### 5.3 Submission Confirmation Strategy

For each record, the runtime captures baseline evidence:

- table row count in DOM
- LocalStorage list length

After submit, it confirms success by comparing post-submit signals.

Possible statuses:

- `ok`
- `ok_parcial`
- `nao_confirmado`
- `erro`

### 5.4 Fallback Insertion Strategy

If no clear evidence appears and table did not grow, runtime attempts JS fallback insertion (`inserir_produto_via_fallback_js`) and revalidates record presence.

### 5.5 Incremental Persistence Strategy

To reduce observability loss on interruption/timeout:

- partial CSV persistence every `RELATORIO_PARCIAL_CADA`
- partial HTML persistence every `HTML_PARCIAL_CADA`

---

## 6. Cloud Workflow Architecture

### 6.1 Trigger Modes

- manual (`workflow_dispatch`) with operational input controls
- scheduled (`schedule`) with optional enable gate (`ENABLE_REGISTRATION_SCHEDULE`)

### 6.2 Job Lifecycle

1. checkout
2. setup python/chrome
3. install dependencies
4. run automation
5. summarize run
6. update run-level history
7. update detailed history
8. commit/push analytics files
9. optional email notification
10. upload artifacts

### 6.3 Fault-Isolation Patterns

- history commit step uses `continue-on-error`
- email step is optional/non-blocking
- summary remains available even when optional steps fail

---

## 7. Data Model

### 7.1 Record-Level Report (`logs/relatorio_cadastro_*.csv`)

Representative fields:

- `indice_csv`, `codigo`, `marca`, `tipo`, `categoria`
- `preco_unitario`, `custo`, `obs`
- `status_execucao`, `detalhe`

### 7.2 Run-Level History (`analytics/history_runs.csv`)

Representative fields:

- `run_id`, `run_datetime`, `report_file`
- `total`, `ok`, `ok_parcial`, `nao_confirmado`, `erro`
- `falhas_criticas`, `success_rate`
- `github_run_id`, `github_run_number`, `run_url`, `actor`, `event_name`

Upsert key priority:

- `github_run_id` (when available)

### 7.3 Detailed Consolidated History (`analytics/detailed_runs.csv`)

Representative fields:

- all record-level fields from report
- `run_id`, `run_datetime`, `report_file`, `github_run_id`
- `history_updated_at_utc`

---

## 8. Dashboard Architecture

### 8.1 Data Loading Modes

1. **Primary local mode**: load from `logs/relatorio_cadastro_*.csv`
2. **Cloud fallback mode**: load from `analytics/detailed_runs.csv`
3. **Remote fallback mode**: optional `*_REMOTE_URL`

### 8.2 Analytical Layers

- Executive: KPI cards + SLA gauge
- Operational: trend/composition/distribution views
- Quality: failure queue and detailed table

### 8.3 Cache Model

- Streamlit `@st.cache_data` with configurable TTL (`DASHBOARD_CACHE_TTL`)

---

## 9. Reliability and Resilience Patterns

Implemented:

1. multi-selector lookup strategy
2. multiple submission evidence channels
3. controlled JS fallback path
4. periodic persistence of intermediate outputs
5. consolidated immutable-like historical datasets
6. cloud-safe dashboard fallback to analytics data

---

## 10. Deployment Considerations

### 10.1 Local

- install Chrome
- configure credentials via env vars
- run automation + dashboard manually

### 10.2 Cloud (GitHub Actions + Streamlit)

- configure secrets for login (mandatory)
- configure optional SMTP secrets
- ensure workflow write permissions for analytics commits
- optionally configure Streamlit secrets for remote CSV fallback

---

## 11. Current Constraints

- UI selector changes in target app may require locator updates
- no dedicated automated test suite yet
- no centralized external datastore (CSV-based persistence by design)

---

## 12. Recommended Next Architectural Enhancements

1. Introduce CI quality gates (tests + lint + static checks)
2. Add schema validation for analytics CSVs
3. Add SLO alerting channel (Slack/Teams/email thresholds)
4. Migrate persistent history to a managed data store (optional future)
5. Add synthetic health run for proactive monitoring
