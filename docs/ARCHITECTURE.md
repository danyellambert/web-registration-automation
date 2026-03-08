# Architecture Guide

## 1. Purpose

This document describes the technical architecture of the web registration automation platform, including runtime components, data flow, resilience behavior, and cloud execution lifecycle.

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

### 3.1 Automation Runtime (`registration_web.py`)

Responsibilities:

- read source dataset (`data/products.csv`)
- authenticate in the target web app
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
data/products.csv
    -> registration_web.py
    -> logs/registration_report_*.csv
    -> scripts/summarize_run.py
    -> logs/run_summary.json + logs/run_summary.md
    -> scripts/update_history.py            -> analytics/history_runs.csv
    -> scripts/update_detailed_history.py   -> analytics/detailed_runs.csv
    -> dashboard.py (logs + analytics + optional remote URLs)
```

Legacy report names are still supported for backward compatibility:

- `logs/relatorio_cadastro_*.csv`

---

## 5. Automation Runtime Internals

### 5.1 Input Validation Layer

`load_input_table()` validates:

- file existence
- required column contract
- optional slicing by offset/limit

### 5.2 Selector Strategy

The automation uses selector lists per field and attempts each locator with bounded timeout (`find_element`).

Benefit:

- improved adaptability against moderate UI selector drift

### 5.3 Submission Confirmation Strategy

For each record, the runtime captures baseline evidence:

- table row count in DOM
- localStorage list length

After submit, it confirms success by comparing post-submit signals.

Possible statuses:

- `ok`
- `partial_success`
- `not_confirmed`
- `error`

> Status values are intentionally kept in Portuguese for compatibility with existing
> analytics schema and downstream dashboards.

### 5.4 Fallback Insertion Strategy

If no clear evidence appears and table did not grow, runtime attempts JavaScript fallback insertion (`insert_product_with_js_fallback`) and revalidates record presence.

### 5.5 Incremental Persistence Strategy

To reduce observability loss on interruption/timeout:

- partial CSV persistence every `PARTIAL_REPORT_EVERY`
- partial HTML persistence every `PARTIAL_HTML_EVERY`

Legacy aliases are still supported:

- `RELATORIO_PARCIAL_CADA`
- `HTML_PARCIAL_CADA`

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

### 7.1 Record-Level Report (`logs/registration_report_*.csv`)

Representative fields:

- `row_index`, `product_code`, `brand`, `product_type`, `category`
- `unit_price`, `cost`, `notes`
- `execution_status`, `detail`

### 7.2 Run-Level History (`analytics/history_runs.csv`)

Representative fields:

- `run_id`, `run_datetime`, `report_file`
- `total`, `ok`, `partial_success`, `not_confirmed`, `error`
- `critical_failures`, `success_rate`
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

1. **Primary local mode**: load from `logs/registration_report_*.csv`
2. **Cloud fallback mode**: load from `analytics/detailed_runs.csv`
3. **Remote fallback mode**: optional `*_REMOTE_URL`

Legacy local report names are still recognized:

- `logs/relatorio_cadastro_*.csv`

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
3. controlled JavaScript fallback path
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

- configure login secrets (mandatory)
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
