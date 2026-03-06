# Web Registration Automation

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.55-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Selenium](https://img.shields.io/badge/Selenium-4.41-43B02A?logo=selenium&logoColor=white)](https://www.selenium.dev/)
[![Workflow](https://img.shields.io/badge/GitHub%20Actions-Enabled-2088FF?logo=githubactions&logoColor=white)](./.github/workflows/registration-web.yml)

Production-grade product registration automation with cloud orchestration, historical analytics, and executive observability.

**Live dashboard:** https://web-registration-automation-dashboard.streamlit.app/

---

## Overview

This project automates product registration in a web application using Selenium, executes reliably in GitHub Actions, consolidates analytics across runs, and exposes operational KPIs in Streamlit.

It is designed to be both:

- **practical for day-to-day operations** (manual/scheduled execution, optional notifications, artifacts)
- **structured for corporate environments** (historical traceability, failure visibility, reproducible workflows)

---

## Key Capabilities

- Resilient browser automation (`cadastro_web.py`)
- Manual and scheduled cloud execution (`registration-web.yml`)
- Run summary generation (`scripts/summarize_run.py`)
- Consolidated run-level history (`analytics/history_runs.csv`)
- Consolidated record-level detailed history (`analytics/detailed_runs.csv`)
- Executive dashboard with cloud fallback support (`dashboard.py`)

---

## Quick Start

### 1) Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2) Configure local credentials

```bash
export LOGIN_EMAIL="your-user@example.com"
export LOGIN_PASSWORD="your-password"
```

Legacy compatibility: `LOGIN_SENHA` is still supported as a fallback.

### 3) Run automation

```bash
python cadastro_web.py
```

### 4) Run dashboard

```bash
streamlit run dashboard.py
```

---

## Data Source

Input dataset path:

- `data/produtos.csv`

> The file name and column names are intentionally kept in Portuguese for compatibility
> with the target web application and existing historical datasets.

Required columns:

- `codigo`
- `marca`
- `tipo`
- `categoria`
- `preco_unitario`
- `custo`
- `obs`

---

## Main Runtime Variables (Automation)

| Variable | Default | Description | Legacy alias (still supported) |
|---|---:|---|---|
| `LOGIN_EMAIL` | `your-user@example.com` | Target system login user | — |
| `LOGIN_PASSWORD` | `your-password` | Target system login password | `LOGIN_SENHA` |
| `HEADLESS` | `0` | Run in headless mode (`1`/`0`) | — |
| `KEEP_OPEN` | `1` | Keep browser open in local visual mode | — |
| `MAX_RECORDS` | `0` | Maximum rows to process (`0` = all) | `LIMITE_REGISTROS` |
| `RECORD_OFFSET` | `0` | Skip first N rows | `OFFSET_REGISTROS` |
| `GENERATE_REPORT` | `1` | Generate run CSV report | `GERAR_RELATORIO` |
| `SAVE_FINAL_HTML` | `1` | Save final HTML evidence | `SALVAR_HTML_FINAL` |
| `SAVE_FINAL_PDF` | `0` | Save final PDF evidence | `SALVAR_PDF_FINAL` |
| `SUBMISSION_CONFIRMATION_TIMEOUT` | `6` | Max confirmation wait time per submission | `TEMPO_CONFIRMACAO_ENVIO` |
| `MAX_WAIT_WITHOUT_EVIDENCE` | `2.5` | Early fallback threshold | `TEMPO_MAX_ESPERA_SEM_EVIDENCIA` |
| `PARTIAL_REPORT_EVERY` | `10` | Partial CSV persistence frequency | `RELATORIO_PARCIAL_CADA` |
| `PARTIAL_HTML_EVERY` | `25` | Partial HTML persistence frequency | `HTML_PARCIAL_CADA` |

---

## Dashboard Variables

| Variable | Default | Description |
|---|---:|---|
| `HISTORY_REMOTE_URL` | empty | Optional remote history CSV fallback |
| `DETAILED_REMOTE_URL` | empty | Optional remote detailed CSV fallback |
| `DASHBOARD_CACHE_TTL` | `60` | Streamlit cache TTL in seconds |

---

## Outputs and Artifacts

Generated during execution:

- `logs/registration_report_YYYYMMDD_HHMMSS.csv`
- `logs/final_page_YYYYMMDD_HHMMSS.html` (optional)
- `logs/final_page_YYYYMMDD_HHMMSS.pdf` (optional)
- `logs/run_summary.json`
- `logs/run_summary.md`
- `analytics/history_runs.csv`
- `analytics/detailed_runs.csv`

Legacy report names (`relatorio_cadastro_*`, `pagina_final_*`) are still recognized
for backward compatibility.

---

## Cloud Workflow

Workflow file:

- `.github/workflows/registration-web.yml`

Trigger modes:

1. `workflow_dispatch` (manual with inputs)
2. `schedule` (cron)

Optional schedule enablement variable:

- `ENABLE_REGISTRATION_SCHEDULE=true`

Required secrets:

- `LOGIN_EMAIL`
- `LOGIN_PASSWORD` (or `LOGIN_SENHA` for backward compatibility)

Optional email secrets:

- `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_TO`, `EMAIL_FROM`

---

## Documentation

For complete enterprise documentation, see:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md)

---

## Contribution

Recommended commit prefixes:

- `feat:` feature
- `fix:` bugfix
- `chore:` maintenance
- `docs:` documentation
