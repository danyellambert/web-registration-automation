# Web Registration Automation (RegFlow Platform)

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.55-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Selenium](https://img.shields.io/badge/Selenium-4.41-43B02A?logo=selenium&logoColor=white)](https://www.selenium.dev/)
[![Registration Workflow](https://img.shields.io/badge/GitHub%20Actions-Registration%20Web-2088FF?logo=githubactions&logoColor=white)](.github/workflows/registration-web.yml)

Production-ready product registration automation with Selenium, GitHub Actions orchestration, historical analytics consolidation, and an executive Streamlit dashboard.

**Live dashboard:** https://web-registration-automation-dashboard.streamlit.app/

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
