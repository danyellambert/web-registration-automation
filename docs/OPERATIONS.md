# Operations Guide

## 1. Scope

This runbook defines how to operate, monitor, and troubleshoot the web registration automation in both local and cloud environments.

---

## 2. Operational Modes

### 2.1 Local Manual Run

Use when:

- validating selector changes
- debugging registration behavior
- testing small subsets of records

Command:

```bash
python cadastro_web.py
```

### 2.2 Cloud Manual Run (GitHub Actions)

Use when:

- requiring auditable run context
- sharing artifacts with stakeholders
- executing with controlled runtime inputs

Trigger:

- GitHub Actions → `Registration Web Automation` → `Run workflow`

### 2.3 Cloud Scheduled Run

Use when:

- recurring execution is required (e.g., nightly)

Enablement control:

- repository variable `ENABLE_REGISTRATION_SCHEDULE=true`

---

## 3. Pre-Run Checklist

Before execution, validate:

1. `LOGIN_EMAIL` and `LOGIN_SENHA` configured
2. input file available at `data/produtos.csv`
3. file schema includes required columns
4. Chrome dependency is available (local)
5. workflow permissions allow committing analytics files (cloud)

---

## 4. Runtime Controls

Primary controls:

- `HEADLESS` (0/1)
- `KEEP_OPEN` (0/1)
- `LIMITE_REGISTROS`
- `OFFSET_REGISTROS`
- `TEMPO_CONFIRMACAO_ENVIO`
- `TEMPO_MAX_ESPERA_SEM_EVIDENCIA`
- `RELATORIO_PARCIAL_CADA`
- `HTML_PARCIAL_CADA`

Recommended operational presets:

### 4.1 Debug preset

- `HEADLESS=0`
- `KEEP_OPEN=1`
- `LIMITE_REGISTROS=10`

### 4.2 Cloud stable preset

- `HEADLESS=1`
- `KEEP_OPEN=0`
- `LIMITE_REGISTROS=0`

---

## 5. Expected Outputs per Run

Operationally relevant outputs:

- `logs/relatorio_cadastro_*.csv`
- `logs/pagina_final_*.html` (if enabled)
- `logs/pagina_final_*.pdf` (if enabled)
- `logs/run_summary.json`
- `logs/run_summary.md`

Consolidated historical datasets:

- `analytics/history_runs.csv`
- `analytics/detailed_runs.csv`

---

## 6. SLOs and Service Objectives (Suggested)

These are practical initial targets for corporate operation:

### 6.1 Reliability SLO

- `success_rate >= 95%` for regular scheduled runs

### 6.2 Critical Failure SLO

- `falhas_criticas = 0` in at least 90% of runs

### 6.3 Pipeline Freshness SLO

- latest scheduled run reflected in `analytics/history_runs.csv` within 30 minutes

### 6.4 Dashboard Freshness SLO

- dashboard data no older than 24h for daily schedule

---

## 7. Monitoring and Health Review

### 7.1 Daily Review (Recommended)

1. open dashboard
2. verify KPI cards (Total / Success Rate / Critical Failures)
3. inspect trend for degradation
4. inspect failure queue for repeated patterns

### 7.2 Weekly Review

1. check sustained success-rate trajectory
2. identify top recurring failure details
3. validate if fallback usage increased
4. review need for selector maintenance

---

## 8. Incident Classification

### P1 — Major outage

Criteria:

- automation cannot login or cannot submit any record
- dashboard unavailable for stakeholders

Action target:

- immediate triage (same hour)

### P2 — Partial degradation

Criteria:

- elevated `nao_confirmado` / `erro`
- unstable frontend signals but partial throughput

Action target:

- same business day

### P3 — Minor issue

Criteria:

- cosmetic dashboard issue
- isolated non-critical step failure (e.g., email notification)

Action target:

- next planned maintenance window

---

## 9. Incident Runbooks

## 9.1 Login failure

Symptoms:

- early run termination
- errors locating login fields/buttons

Actions:

1. verify credentials in secrets/env vars
2. confirm target URL availability
3. run locally in non-headless mode for visual inspection
4. validate login selectors and update if page changed

### 9.2 High `nao_confirmado` rate

Symptoms:

- many records not confirmed

Actions:

1. increase `TEMPO_CONFIRMACAO_ENVIO` gradually
2. review `logs/pagina_final_*.html`
3. inspect `detalhe` column in latest report
4. validate if fallback JS path is still compatible with frontend

### 9.3 Analytics not updated

Symptoms:

- workflow run completed, but `analytics/*.csv` unchanged

Actions:

1. inspect workflow step logs (`update_history.py` / `update_detailed_history.py`)
2. verify repository write permissions for workflow token
3. validate CSV schema expectations in scripts
4. retry manual run with small dataset

### 9.4 Dashboard empty in cloud

Symptoms:

- no data rendered in Streamlit cloud

Actions:

1. verify `analytics/history_runs.csv` and `analytics/detailed_runs.csv` existence
2. confirm repo branch contains latest analytics commit
3. if using remote fallback, validate `*_REMOTE_URL`
4. reduce cache staleness via `DASHBOARD_CACHE_TTL`

---

## 10. Post-Incident Procedure

After stabilization:

1. document root cause
2. document corrective action
3. add preventive change (selector hardening, timing, validation)
4. record incident date + impact + resolution in operations notes

---

## 11. Change Management Recommendations

Before merging operationally relevant changes:

1. run local smoke test (`LIMITE_REGISTROS=5`)
2. run workflow manually in GitHub Actions
3. validate analytics files update
4. validate dashboard after refresh

---

## 12. Security and Secrets Handling

Guidelines:

- never hardcode credentials in source code
- keep sensitive values in env vars or GitHub secrets
- rotate credentials periodically
- restrict repository admin/write access

---

## 13. Useful Operational Commands

Run automation locally:

```bash
python cadastro_web.py
```

Run dashboard locally:

```bash
streamlit run dashboard.py
```

Quick syntax check:

```bash
python -m py_compile cadastro_web.py dashboard.py scripts/*.py
```

---

## 14. Operational Roadmap (Recommended)

1. Add automated tests in CI
2. Add lint and formatting gates
3. Add proactive alerting (email/Slack) on SLO breach
4. Add monthly operations review template
5. Define formal on-call ownership (if project becomes business-critical)
