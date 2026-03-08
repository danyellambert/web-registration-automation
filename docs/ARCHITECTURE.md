# Architecture Guide

## 1. Purpose

This document describes the current technical architecture of the Web Registration Automation platform, including runtime components, data flow, resilience behavior, and cloud execution lifecycle.

---

## 2. System Context

The platform automates product registration into a web interface (RegFlow Platform) and provides operational intelligence through consolidated historical datasets and a Streamlit dashboard.

Primary architecture goals:

- deterministic form submission automation
- resilient behavior across local and cloud execution contexts
- traceable outcomes by run and by record
- management-ready observability

---

## 3. High-Level Components

### 3.1 Automation Runtime (`registration_web.py`)

Responsibilities:

- read source dataset from `data/products.csv`
- authenticate in target web page
- fill and submit one product record at a time
- confirm submission using multiple evidence signals
- apply fallback insertion when frontend evidence is unstable
- persist run artifacts in `logs/`

### 3.2 Cloud Orchestrator (`.github/workflows/registration-web.yml`)

Responsibilities:

- provision Python and Chrome runtime
- execute automation with parameterized controls
- generate run summary payloads
- update consolidated analytics files
- publish artifacts and execution summary
- optionally notify stakeholders by email

### 3.3 Analytics Upsert Scripts (`scripts/`)

- `summarize_run.py`: summarizes latest run report metrics
- `update_history.py`: upserts run-level history
- `update_detailed_history.py`: upserts record-level detailed history

### 3.4 Executive Dashboard (`dashboard.py`)

Responsibilities:

- render KPI and trend views
- expose failure investigation queues
- support filtering and exports
- load local reports first, then cloud-safe analytics fallback

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

Legacy report naming is still supported for backward compatibility:

- `logs/relatorio_cadastro_*.csv`

---

## 5. Automation Runtime Internals

### 5.1 Input Validation and Normalization

`load_input_table()` handles:

- CSV existence validation
- required canonical schema enforcement
- legacy column alias mapping to English schema
- optional slicing by `RECORD_OFFSET` and `MAX_RECORDS`

Canonical required columns:

- `product_code`, `brand`, `product_type`, `category`, `unit_price`, `cost`, `notes`

### 5.2 Selector Resolution Strategy

The runtime stores locator lists for each target field and attempts each locator with bounded wait time (`find_element`).

Benefit:

- improved resilience against moderate UI selector drift

### 5.3 Local Target Auto-Start

If `LOGIN_URL` is local (`127.0.0.1` / `localhost`) and unreachable, the runtime can auto-start the static site from `web_page/exclusive_page` when `AUTO_START_LOCAL_SITE=1`.

### 5.4 Submission Confirmation Strategy

For each submitted record, baseline and post-submit evidence are compared:

- DOM table row count
- localStorage list length (`productList`)
- submitted product code presence

Possible `execution_status` values:

- `ok`
- `partial_success`
- `not_confirmed`
- `error`

### 5.5 JavaScript Fallback Strategy

When no clear evidence appears and table rows did not increase, runtime attempts `insert_product_with_js_fallback()` and revalidates product code presence.

### 5.6 Incremental Persistence Strategy

To reduce evidence loss on interruption/timeout:

- partial report persistence every `PARTIAL_REPORT_EVERY`
- partial HTML persistence every `PARTIAL_HTML_EVERY`

---

## 6. Cloud Workflow Architecture

### 6.1 Trigger Modes

- manual trigger via `workflow_dispatch`
- scheduled trigger via cron (`0 11 * * *`)
- optional schedule gate via repository variable `ENABLE_REGISTRATION_SCHEDULE=true`

### 6.2 Job Lifecycle

1. checkout repository
2. set up Python and Chrome
3. install dependencies
4. run automation
5. generate summary files
6. update run-level history
7. update detailed history
8. commit/push analytics files (if changed)
9. send optional email notification
10. upload logs/analytics artifacts

### 6.3 Fault-Isolation Patterns

- analytics commit step uses `continue-on-error`
- email sending is optional and non-blocking
- summary artifacts are generated with `if: always()`

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

- full record-level report schema
- `run_id`, `run_datetime`, `report_file`, `github_run_id`
- `history_updated_at_utc`

---

## 8. Dashboard Architecture

### 8.1 Data Loading Modes

1. **Primary local mode**: `logs/registration_report_*.csv`
2. **Cloud fallback mode**: `analytics/detailed_runs.csv`
3. **Optional remote fallback mode**: `HISTORY_REMOTE_URL` / `DETAILED_REMOTE_URL`

Legacy local reports are still recognized:

- `logs/relatorio_cadastro_*.csv`

### 8.2 Analytical Layers

- **Executive:** KPI cards + SLA gauge
- **Operational:** trend/composition/efficiency views
- **Quality:** failure queue and detailed inspection table

### 8.3 Cache Model

- `@st.cache_data` with configurable TTL (`DASHBOARD_CACHE_TTL`)

---

## 9. Reliability and Resilience Patterns

Implemented patterns:

1. multi-selector lookup
2. multi-signal submission confirmation
3. controlled JavaScript fallback insertion
4. periodic intermediate persistence
5. consolidated run-level and record-level history
6. cloud-safe dashboard data fallback

---

## 10. Deployment Considerations

### 10.1 Local Deployment

- install Chrome
- configure environment variables
- run automation and dashboard manually

### 10.2 Cloud Deployment (GitHub Actions + Streamlit)

- configure required login secrets
- configure optional SMTP secrets
- ensure workflow write permissions for analytics commits
- optionally configure Streamlit remote URL fallbacks

---

## 11. Current Constraints

- frontend selector changes may require locator updates
- no dedicated automated test suite yet
- persistence currently CSV-based (no centralized external datastore)

---

## 12. Recommended Next Enhancements

1. add CI quality gates (tests, lint, static checks)
2. add schema validation for analytics CSV files
3. add proactive SLO alerts (email/Slack/Teams)
4. consider managed data store for long-term history
5. add synthetic health checks for proactive monitoring
