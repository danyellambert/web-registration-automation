# Operations Guide

## 1. Scope

This runbook defines how to operate, monitor, and troubleshoot the web registration automation in both local and cloud environments.

---

## 2. Operational Modes

### 2.1 Local Manual Run

Use when:

- validating selector behavior
- debugging registration issues
- testing small record subsets

Command:

```bash
python registration_web.py
```

### 2.2 Cloud Manual Run (GitHub Actions)

Use when:

- requiring an auditable run context
- sharing artifacts with stakeholders
- executing with controlled runtime inputs

Trigger path:

- GitHub Actions -> `Registration Web (Cloud)` -> `Run workflow`

### 2.3 Cloud Scheduled Run

Use when:

- recurring execution is required (for example, daily)

Enablement control:

- repository variable `ENABLE_REGISTRATION_SCHEDULE=true`

---

## 3. Pre-Run Checklist

Before each run, verify:

1. `LOGIN_EMAIL` and `LOGIN_PASSWORD` are configured (`LOGIN_SENHA` fallback is also accepted)
2. input file exists at `data/products.csv`
3. input schema contains required columns
4. Chrome dependency is available (local mode)
5. workflow has write permission for analytics updates (cloud mode)

---

## 4. Runtime Controls

Primary controls:

- `HEADLESS` (0/1)
- `KEEP_OPEN` (0/1)
- `MAX_RECORDS`
- `RECORD_OFFSET`
- `SUBMISSION_CONFIRMATION_TIMEOUT`
- `MAX_WAIT_WITHOUT_EVIDENCE`
- `PARTIAL_REPORT_EVERY`
- `PARTIAL_HTML_EVERY`

Legacy aliases still accepted for compatibility:

- `LOGIN_SENHA` (password alias)
- report naming: `relatorio_cadastro_*.csv` (read compatibility)

Recommended operational presets:

### 4.1 Local debug preset

- `HEADLESS=0`
- `KEEP_OPEN=1`
- `MAX_RECORDS=10`

### 4.2 Cloud stable preset

- `HEADLESS=1`
- `KEEP_OPEN=0`
- `MAX_RECORDS=0`

---

## 5. Expected Outputs Per Run

Operationally relevant outputs:

- `logs/registration_report_*.csv`
- `logs/final_page_*.html` (if enabled)
- `logs/final_page_*.pdf` (if enabled)
- `logs/run_summary.json`
- `logs/run_summary.md`

Consolidated historical datasets:

- `analytics/history_runs.csv`
- `analytics/detailed_runs.csv`

---

## 6. Suggested SLOs

### 6.1 Reliability SLO

- `success_rate >= 95%` for regular scheduled runs

### 6.2 Critical Failure SLO

- `critical_failures = 0` in at least 90% of runs

### 6.3 Pipeline Freshness SLO

- latest scheduled run reflected in `analytics/history_runs.csv` within 30 minutes

### 6.4 Dashboard Freshness SLO

- dashboard data no older than 24h for daily schedules

---

## 7. Monitoring and Health Review

### 7.1 Daily Review (recommended)

1. open dashboard
2. check KPI cards (Total, Success Rate, Critical Failures)
3. inspect trend for degradation
4. inspect failure queue for recurring patterns

### 7.2 Weekly Review

1. evaluate sustained success-rate trend
2. identify top recurring failure details
3. check whether fallback usage is increasing
4. assess selector maintenance needs

---

## 8. Incident Classification

### P1 — Major outage

Criteria:

- automation cannot log in or cannot submit any record
- dashboard is unavailable for stakeholders

Target response:

- immediate triage (same hour)

### P2 — Partial degradation

Criteria:

- elevated `not_confirmed` / `error`
- unstable frontend evidence with partial throughput

Target response:

- same business day

### P3 — Minor issue

Criteria:

- cosmetic dashboard issue
- isolated non-critical optional step failure (for example, email notification)

Target response:

- next planned maintenance window

---

## 9. Incident Runbooks

### 9.1 Login failure

Symptoms:

- early run termination
- errors locating login fields/buttons

Actions:

1. verify credentials in env vars/secrets
2. validate target URL availability
3. run locally in non-headless mode for visual inspection
4. update selectors if frontend changed

### 9.2 High `not_confirmed` rate

Symptoms:

- many records classified as `not_confirmed`

Actions:

1. increase `SUBMISSION_CONFIRMATION_TIMEOUT` gradually
2. review latest final HTML evidence (`logs/final_page_*.html`)
3. inspect `detail` in latest report
4. validate compatibility of fallback insertion path

### 9.3 Analytics not updated

Symptoms:

- workflow completed but `analytics/*.csv` did not change

Actions:

1. inspect workflow logs for `update_history.py` and `update_detailed_history.py`
2. verify workflow token write permissions
3. validate CSV schema assumptions in scripts
4. retry a manual run with a small dataset

### 9.4 Dashboard empty in cloud

Symptoms:

- no data rendered in Streamlit cloud

Actions:

1. verify `analytics/history_runs.csv` and `analytics/detailed_runs.csv` exist
2. confirm branch includes the latest analytics commit
3. if remote fallback is used, validate `HISTORY_REMOTE_URL` / `DETAILED_REMOTE_URL`
4. reduce cache staleness with `DASHBOARD_CACHE_TTL`

---

## 10. Post-Incident Procedure

After stabilization:

1. document root cause
2. document corrective action
3. add preventive improvement (selector hardening, timeout tuning, validation)
4. record incident date, impact, and resolution in operations notes

---

## 11. Change Management Recommendations

Before merging operationally relevant changes:

1. run a local smoke test (`MAX_RECORDS=5`)
2. run the cloud workflow manually
3. validate analytics file updates
4. validate dashboard behavior after refresh

---

## 12. Security and Secrets Handling

Guidelines:

- never hardcode credentials in source code
- keep sensitive values in environment variables or GitHub secrets
- rotate credentials periodically
- restrict repository write/admin access

---

## 13. Useful Operational Commands

Run automation locally:

```bash
python registration_web.py
```

Run dashboard locally:

```bash
streamlit run dashboard.py
```

Quick syntax validation:

```bash
python -m py_compile registration_web.py dashboard.py scripts/*.py
```

Run local static target page:

```bash
python -m http.server 8000 --directory web_page/exclusive_page
```

---

## 14. Operational Roadmap (Suggested)

1. add automated tests in CI
2. add lint/format quality gates
3. add proactive SLO alerts (email/Slack/Teams)
4. create monthly operations review template
5. define on-call ownership if the project becomes business-critical
