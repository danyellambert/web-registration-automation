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
export LOGIN_SENHA="your-password"
```

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

| Variable | Default | Description |
|---|---:|---|
| `LOGIN_EMAIL` | `meuemail@gmail.com` | Target system login user |
| `LOGIN_SENHA` | `senhanormal` | Target system login password |
| `HEADLESS` | `0` | Run in headless mode (`1`/`0`) |
| `KEEP_OPEN` | `1` | Keep browser open in local visual mode |
| `LIMITE_REGISTROS` | `0` | Maximum rows to process (`0` = all) |
| `OFFSET_REGISTROS` | `0` | Skip first N rows |
| `GERAR_RELATORIO` | `1` | Generate run CSV report |
| `SALVAR_HTML_FINAL` | `1` | Save final HTML evidence |
| `SALVAR_PDF_FINAL` | `0` | Save final PDF evidence |
| `TEMPO_CONFIRMACAO_ENVIO` | `6` | Max confirmation wait time per submission |
| `TEMPO_MAX_ESPERA_SEM_EVIDENCIA` | `2.5` | Early fallback threshold |
| `RELATORIO_PARCIAL_CADA` | `10` | Partial CSV persistence frequency |
| `HTML_PARCIAL_CADA` | `25` | Partial HTML persistence frequency |

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

- `logs/relatorio_cadastro_YYYYMMDD_HHMMSS.csv`
- `logs/pagina_final_YYYYMMDD_HHMMSS.html` (optional)
- `logs/pagina_final_YYYYMMDD_HHMMSS.pdf` (optional)
- `logs/run_summary.json`
- `logs/run_summary.md`
- `analytics/history_runs.csv`
- `analytics/detailed_runs.csv`

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
- `LOGIN_SENHA`

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
