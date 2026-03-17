# Web Registration Automation (RegFlow Platform)

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.55-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Selenium](https://img.shields.io/badge/Selenium-4.41-43B02A?logo=selenium&logoColor=white)](https://www.selenium.dev/)
[![Registration Workflow](https://img.shields.io/badge/GitHub%20Actions-Registration%20Web-2088FF?logo=githubactions&logoColor=white)](.github/workflows/registration-web.yml)

Production-ready product registration automation with Selenium, GitHub Actions orchestration, historical analytics consolidation, and an executive Streamlit dashboard.

**Live dashboard:** https://web-registration-automation-dashboard.streamlit.app/

**Live test website:** https://danyellambert.github.io/web-registration-automation/products.html

---

## Table of Contents

- [1. Project Overview](#1-project-overview)
- [2. Core Capabilities](#2-core-capabilities)
- [3. Repository Structure](#3-repository-structure)
- [4. Prerequisites](#4-prerequisites)
- [5. Local Quick Start](#5-local-quick-start)
- [6. Input Dataset Contract (`data/products.csv`)](#6-input-dataset-contract-dataproductscsv)
- [7. Runtime Environment Variables](#7-runtime-environment-variables)
- [8. GitHub Actions Workflows](#8-github-actions-workflows)
- [9. Outputs and Artifacts](#9-outputs-and-artifacts)
- [10. Dashboard Usage](#10-dashboard-usage)
- [11. Troubleshooting](#11-troubleshooting)
- [12. Security and Operations](#12-security-and-operations)
- [13. Additional Documentation](#13-additional-documentation)
- [14. Contribution Guidelines](#14-contribution-guidelines)

---

## 1. Project Overview

This project automates product registration into a web interface (RegFlow Platform), captures execution evidence, maintains consolidated historical datasets, and exposes operational intelligence through dashboards.

High-level flow:

1. Read records from `data/products.csv`
2. Log in to the target web page
3. Fill and submit each product row
4. Confirm submission using multiple evidence channels
5. Persist reports and run summaries in `logs/`
6. Update historical analytics in `analytics/`
7. Visualize KPIs and trends in `dashboard.py`

---

## 2. Core Capabilities

- Selector-based Selenium automation (`registration_web.py`)
- Local and cloud execution modes (GitHub Actions)
- Automatic local static site startup when needed
- Multi-signal submission confirmation (`DOM` + `localStorage`)
- JavaScript fallback insertion for unstable frontend behavior
- Incremental report/HTML persistence during long runs
- Consolidated run-level and record-level analytics
- Executive, operational, and quality monitoring in Streamlit

---

## 3. Repository Structure

```text
.
├── registration_web.py
├── dashboard.py
├── requirements.txt
├── data/
│   └── products.csv
├── logs/                          # generated run artifacts
├── analytics/
│   ├── history_runs.csv
│   └── detailed_runs.csv
├── scripts/
│   ├── summarize_run.py
│   ├── update_history.py
│   └── update_detailed_history.py
├── docs/
│   ├── ARCHITECTURE.md
│   └── OPERATIONS.md
└── web_page/
    └── exclusive_page/
        ├── index.html
        ├── login.html
        ├── products.html
        └── README_EXCLUSIVE_PAGE.md
```

---

## 4. Prerequisites

### Local

- Python 3.11+
- Google Chrome installed
- macOS/Linux shell (examples use `zsh`/`bash` style)

### Cloud

- GitHub repository with Actions enabled
- Required secrets configured (`LOGIN_EMAIL`, `LOGIN_PASSWORD`)

---

## 5. Local Quick Start

### 5.1 Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5.2 Configure credentials

```bash
export LOGIN_EMAIL="your-user@example.com"
export LOGIN_PASSWORD="your-password"
```

Compatibility fallback:

- `LOGIN_SENHA` is still accepted if `LOGIN_PASSWORD` is not set.

### 5.3 Run automation

```bash
python registration_web.py
```

Default target URL:

- `http://127.0.0.1:8000/login.html`

If the local site is offline and `AUTO_START_LOCAL_SITE=1`, the runtime automatically tries to start:

```bash
python -m http.server 8000 --directory web_page/exclusive_page
```

### 5.4 Run dashboard

```bash
streamlit run dashboard.py
```

### 5.5 Recommended local smoke test

```bash
MAX_RECORDS=5 HEADLESS=0 KEEP_OPEN=1 python registration_web.py
```

---

## 6. Input Dataset Contract (`data/products.csv`)

Canonical required columns:

- `product_code`
- `brand`
- `product_type`
- `category`
- `unit_price`
- `cost`
- `notes`

Legacy column aliases still mapped automatically at runtime:

- `codigo` -> `product_code`
- `marca` -> `brand`
- `tipo` -> `product_type`
- `categoria` -> `category`
- `preco_unitario` / `preco` -> `unit_price`
- `custo` -> `cost`
- `obs` -> `notes`

If `notes` is missing, it is created as an empty column.

---

## 7. Runtime Environment Variables

### 7.1 Automation (`registration_web.py`)

| Variable | Default | Description |
|---|---:|---|
| `LOGIN_URL` | `http://127.0.0.1:8000/login.html` | Target login URL |
| `LOGIN_EMAIL` | `your-user@example.com` | Login username/email |
| `LOGIN_PASSWORD` | `your-password` | Login password |
| `LOGIN_SENHA` | — | Legacy password alias fallback |
| `HEADLESS` | `0` | Headless browser mode (`1/0`) |
| `KEEP_OPEN` | `1` | Keep browser open in visual local mode |
| `MAX_RECORDS` | `0` | Max records to process (`0 = all`) |
| `RECORD_OFFSET` | `0` | Skip first N input records |
| `GENERATE_REPORT` | `1` | Persist report CSV |
| `SAVE_FINAL_HTML` | `1` | Persist final HTML evidence |
| `SAVE_FINAL_PDF` | `0` | Persist final PDF evidence |
| `SUBMISSION_CONFIRMATION_TIMEOUT` | `6.0` | Max per-record confirmation wait (seconds) |
| `MAX_WAIT_WITHOUT_EVIDENCE` | `2.5` | Early no-evidence threshold (seconds) |
| `PARTIAL_REPORT_EVERY` | `10` | Save partial report every N records |
| `PARTIAL_HTML_EVERY` | `25` | Save partial HTML every N records (`0` disables partial HTML saves) |
| `AUTO_START_LOCAL_SITE` | `1` | Auto-start local static site when needed |
| `LOCAL_SITE_START_TIMEOUT` | `8.0` | Auto-start timeout (seconds) |

`execution_status` values:

- `ok`
- `partial_success`
- `not_confirmed`
- `error`

### 7.2 Dashboard (`dashboard.py`)

| Variable | Default | Description |
|---|---:|---|
| `HISTORY_REMOTE_URL` | empty | Optional remote fallback URL for `history_runs.csv` |
| `DETAILED_REMOTE_URL` | empty | Optional remote fallback URL for `detailed_runs.csv` |
| `DASHBOARD_CACHE_TTL` | `60` | Streamlit cache TTL (seconds) |

---

## 8. GitHub Actions Workflows

### 8.1 Registration workflow

File:

- `.github/workflows/registration-web.yml`

Triggers:

- `workflow_dispatch` (manual)
- `schedule` (`0 11 * * *`) with optional gate

Schedule gate variable:

- `ENABLE_REGISTRATION_SCHEDULE=true`

Manual inputs include:

- `target_site` (`local_runner` or `github_pages`)
- `max_records`, `record_offset`
- `submission_confirmation_timeout`, `max_wait_without_evidence`
- `partial_report_every`, `partial_html_every`
- `save_final_html`, `save_final_pdf`

Required secrets:

- `LOGIN_EMAIL`
- `LOGIN_PASSWORD` (or `LOGIN_SENHA` fallback)

Optional SMTP/email secrets:

- `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_TO`, `EMAIL_FROM`

### 8.2 Web page deployment workflow

File:

- `.github/workflows/deploy-web-page.yml`

Deploy trigger:

- push to `main` with changes in `web_page/exclusive_page/**`

Published URL:

- https://danyellambert.github.io/web-registration-automation/

---

## 9. Outputs and Artifacts

Generated by automation:

- `logs/registration_report_YYYYMMDD_HHMMSS.csv`
- `logs/final_page_YYYYMMDD_HHMMSS.html` (optional)
- `logs/final_page_YYYYMMDD_HHMMSS.pdf` (optional)
- `logs/run_summary.json`
- `logs/run_summary.md`

Consolidated analytics:

- `analytics/history_runs.csv` (run-level)
- `analytics/detailed_runs.csv` (record-level)

Legacy report names are still recognized by summary/dashboard logic:

- `logs/relatorio_cadastro_*.csv`

---

## 10. Dashboard Usage

`dashboard.py` provides:

- Executive KPIs (runs, volume, success rate, critical failures)
- SLA success gauge
- Success trend by run
- Status composition
- Efficiency by brand and category/status heatmap
- Failure investigation queue (`error`, `not_confirmed`, `partial_success`)
- Filtered CSV export

Data loading order:

1. Local `logs/` reports
2. `analytics/detailed_runs.csv`
3. Remote URLs (`*_REMOTE_URL`) when configured

---

## 11. Troubleshooting

### 11.1 `ERR_CONNECTION_REFUSED` against local login URL

Start the static site manually:

```bash
python -m http.server 8000 --directory web_page/exclusive_page
```

Then retry automation.

### 11.2 Frontend text/style changes not visible

Use a hard refresh (browser cache issue):

- macOS + Chrome: `Cmd + Shift + R`

### 11.3 High `not_confirmed` volume

- Increase `SUBMISSION_CONFIRMATION_TIMEOUT` gradually
- Inspect `logs/final_page_*.html`
- Review `detail` column in the report CSV

### 11.4 Empty dashboard

- Check whether `logs/registration_report_*.csv` or `analytics/*.csv` exist
- Confirm latest commits include analytics updates
- Validate remote URL environment variables when using cloud fallback

---

## 12. Security and Operations

- Never hardcode credentials
- Use GitHub Secrets in cloud runs
- Keep workflow write permissions properly configured (`contents: write`)
- Rotate credentials periodically
- Restrict repository write/admin access

---

## 13. Additional Documentation

- Architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Operations runbook: [`docs/OPERATIONS.md`](docs/OPERATIONS.md)
- Web page front-end guide: [`web_page/exclusive_page/README_EXCLUSIVE_PAGE.md`](web_page/exclusive_page/README_EXCLUSIVE_PAGE.md)

---

## 14. Contribution Guidelines

Recommended commit prefixes:

- `feat:` feature
- `fix:` bug fix
- `chore:` maintenance
- `docs:` documentation

Recommended pre-PR checks:

1. Local smoke run (`MAX_RECORDS=5`)
2. Syntax validation:

   ```bash
   python -m py_compile registration_web.py dashboard.py scripts/*.py
   ```

3. Update docs whenever runtime behavior, workflow behavior, or operational controls change.

---

## 15. Dependency Reference

All Python dependencies are pinned in `requirements.txt`:

| Package | Version | Purpose in this project |
|---|---:|---|
| `pandas` | `2.3.3` | CSV ingestion, transformation, history consolidation |
| `selenium` | `4.41.0` | Browser automation and DOM interaction |
| `streamlit` | `1.55.0` | Dashboard UI and execution surface |
| `plotly` | `6.6.0` | Interactive visualizations in the dashboard |
| `altair` | `6.0.0` | Included dependency used by Streamlit ecosystem and future charting extensions |

---

## 16. Script and File Reference

### 16.1 Core Python entry points

#### `registration_web.py`

Main automation runtime. It is responsible for:

- reading `data/products.csv`
- mapping legacy CSV column names to the canonical English schema
- opening the target login page
- authenticating using `LOGIN_EMAIL` and `LOGIN_PASSWORD`
- submitting products one by one
- confirming submission through DOM and `localStorage` evidence
- using JavaScript fallback insertion when necessary
- saving reports and evidence files in `logs/`

#### `dashboard.py`

Streamlit application for monitoring:

- total runs and processed records
- success rate and critical failures
- run trend and status composition
- brand/category analysis
- failure investigation queue
- filtered CSV exports

#### `scripts/summarize_run.py`

Creates:

- `logs/run_summary.json`
- `logs/run_summary.md`

It also exports GitHub Actions step outputs when `GITHUB_OUTPUT` is available.

#### `scripts/update_history.py`

Upserts a single run into `analytics/history_runs.csv` using `github_run_id` as the preferred idempotent key when available.

#### `scripts/update_detailed_history.py`

Upserts the detailed report rows from the latest execution into `analytics/detailed_runs.csv`.

### 16.2 Key non-Python runtime files

- `data/products.csv`: canonical input dataset
- `analytics/history_runs.csv`: consolidated run history
- `analytics/detailed_runs.csv`: consolidated record-level history
- `web_page/exclusive_page/login.html`: login page targeted by Selenium
- `web_page/exclusive_page/products.html`: product form and table page targeted by Selenium
- `web_page/exclusive_page/index.html`: redirect entry point for local serving and GitHub Pages

---

## 17. GitHub Actions Manual Input Reference

The `Registration Web (Cloud)` workflow exposes the following `workflow_dispatch` inputs:

| Input | Default | Meaning |
|---|---:|---|
| `target_site` | `local_runner` | Choose whether the workflow uses the runner-hosted local site or the published GitHub Pages site |
| `max_records` | `0` | Limit the number of processed rows (`0 = all`) |
| `record_offset` | `0` | Skip the first N rows |
| `submission_confirmation_timeout` | `6` | Max seconds to wait for evidence after each submit |
| `max_wait_without_evidence` | `2.5` | Early fallback threshold before normal timeout completes |
| `partial_report_every` | `10` | Save partial CSV every N records |
| `partial_html_every` | `25` | Save partial HTML every N records |
| `save_final_html` | `1` | Save final HTML evidence |
| `save_final_pdf` | `0` | Save final PDF evidence |

### 17.1 Cloud target behavior

When `target_site=local_runner`:

- the workflow starts a local static server in the GitHub runner
- it validates `http://127.0.0.1:8000/login.html`

When `target_site=github_pages`:

- the workflow validates `https://danyellambert.github.io/web-registration-automation/login.html`
- the automation points `LOGIN_URL` to the public site

### 17.2 Artifact upload behavior

The workflow uploads a single artifact bundle named:

- `logs-registration-web-${github.run_id}`

Retention:

- `14` days

Included files:

- `logs/*.csv`
- `logs/*.html`
- `logs/*.pdf`
- `logs/run_summary.json`
- `logs/run_summary.md`
- `analytics/history_runs.csv`
- `analytics/detailed_runs.csv`

---

## 18. Execution Status Semantics

The runtime uses the following per-record `execution_status` values:

| Status | Meaning | Operational interpretation |
|---|---|---|
| `ok` | Submission was confirmed through expected evidence | fully successful record |
| `partial_success` | Partial confirmation exists, but not through the strongest evidence path | review if recurring |
| `not_confirmed` | Submission could not be confirmed with available evidence | considered a critical failure candidate |
| `error` | Automation failed due to exception/runtime issue | hard failure |

### 18.1 Critical failures

For run summaries and dashboard KPIs, `critical_failures` is derived from:

- `not_confirmed`
- `error`

---

## 19. Analytics Dataset Reference

### 19.1 `analytics/history_runs.csv`

Run-level history stores consolidated metadata such as:

- `history_updated_at_utc`
- `run_id`
- `run_datetime`
- `report_file`
- `total`
- `ok`
- `partial_success`
- `not_confirmed`
- `error`
- `other_statuses`
- `critical_failures`
- `success_rate`
- `github_run_id`
- `github_run_number`
- `github_run_attempt`
- `repository`
- `ref_name`
- `actor`
- `event_name`
- `run_url`

### 19.2 `analytics/detailed_runs.csv`

Detailed history stores every processed row plus execution metadata, including:

- canonical product fields
- `execution_status`
- `detail`
- `run_id`
- `run_datetime`
- `report_file`
- `github_run_id`
- `history_updated_at_utc`

### 19.3 How history updates happen

In GitHub Actions:

1. `summarize_run.py` generates summary files
2. `update_history.py` updates run-level history
3. `update_detailed_history.py` updates detailed history
4. workflow attempts to commit/push `analytics/*.csv`

---

## 20. Dashboard Feature Map

### 20.1 Data loading priority

`dashboard.py` loads data in this order:

1. local reports from `logs/`
2. `analytics/detailed_runs.csv`
3. remote fallback URLs from environment variables

### 20.2 Sidebar controls

The dashboard currently supports:

- manual refresh button
- optional auto-refresh toggle
- period/date range filter
- free-text search by code/brand
- brand multi-select filter
- event type multi-select filter (history only)
- SLA target slider

### 20.3 Visual sections

The dashboard currently renders:

- KPI summary row
- SLA gauge
- success trend line chart
- status composition pie chart
- brand efficiency bar chart
- category/status heatmap
- consolidated run history table
- failure investigation queue
- filtered detailed dataset table and CSV download

---

## 21. Validation and Release Checklist

Recommended validation flow after significant changes:

1. validate static target locally

   ```bash
   python -m http.server 8000 --directory web_page/exclusive_page
   ```

2. run local smoke automation

   ```bash
   MAX_RECORDS=5 HEADLESS=0 KEEP_OPEN=1 python registration_web.py
   ```

3. validate syntax

   ```bash
   python -m py_compile registration_web.py dashboard.py scripts/*.py
   ```

4. open dashboard and review recent run data

   ```bash
   streamlit run dashboard.py
   ```

5. if the change affects cloud execution, run the GitHub Actions workflow manually

6. if the change affects the static site, confirm GitHub Pages deployment updated successfully

---

## 22. Customization Guide

Common customization points:

### 22.1 Branding

- application name in `login.html` / `index.html`
- logo file at `web_page/exclusive_page/assets/main_logo.webp`
- footer signature text in `login.html` and `products.html`

### 22.2 Target environment

- local runtime target through `LOGIN_URL`
- cloud runtime target through workflow `target_site`

### 22.3 Processing behavior

- control subset size with `MAX_RECORDS` / `RECORD_OFFSET`
- tune timing with `SUBMISSION_CONFIRMATION_TIMEOUT` and `MAX_WAIT_WITHOUT_EVIDENCE`
- enable or disable evidence files with `SAVE_FINAL_HTML` / `SAVE_FINAL_PDF`

### 22.4 Dashboard behavior

- tune cache with `DASHBOARD_CACHE_TTL`
- provide remote fallbacks with `HISTORY_REMOTE_URL` and `DETAILED_REMOTE_URL`

---

## 23. Known Limitations and Non-Goals

Current limitations:

- no formal automated test suite yet
- persistence is file-based (CSV), not database-backed
- the target web interface is a static front-end with client-side persistence only
- selector drift in the target page may still require manual maintenance

Non-goals in the current implementation:

- multi-user authentication backend
- server-side API integration for product persistence
- centralized production database
- enterprise-grade alerting stack out of the box

---

## 24. Why This Repository Is Operationally Useful

This repository is intentionally structured to show more than a simple Selenium script. It demonstrates:

- automated UI interaction
- recoverability and fallback design
- run evidence generation
- historical analytics maintenance
- cloud workflow orchestration
- dashboard-driven observability
- documentation for architecture and operations

That makes it useful both as an operational automation project and as a portfolio-grade engineering artifact.
