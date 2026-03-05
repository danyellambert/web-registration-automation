# Web Registration Automation

Automação de cadastro de produtos com Selenium (`cadastro_web.py`) + dashboard corporativo em Streamlit (`dashboard.py`) para análise histórica dos resultados.

## Pré-requisitos

- Python 3.11+
- Google Chrome instalado (para execução do Selenium)

## Instalação

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Executar a automação

```bash
python cadastro_web.py
```

### Variáveis de ambiente principais

- `LOGIN_EMAIL`
- `LOGIN_SENHA`
- `HEADLESS` (`1` ou `0`)
- `KEEP_OPEN` (`1` ou `0`)

Os relatórios são gerados em `logs/` como:

- `relatorio_cadastro_YYYYMMDD_HHMMSS.csv`
- `pagina_final_YYYYMMDD_HHMMSS.html` (quando habilitado)

## Dashboard de resultados (novo)

O dashboard lê automaticamente os arquivos `logs/relatorio_cadastro_*.csv` e mostra:

- KPIs executivos (execuções, registros processados, taxa de sucesso, falhas críticas)
- filtros por período/status/busca por código ou marca
- gráfico de distribuição por status
- tendência da taxa de sucesso por execução
- tabela de falhas para investigação
- download de CSV filtrado

Para abrir o dashboard:

```bash
streamlit run dashboard.py
```

## Execução 100% cloud com GitHub Actions

O workflow `.github/workflows/registration-web.yml` roda a automação na nuvem com Chrome headless.

### Disparos disponíveis

- **Manual** (`workflow_dispatch`) com parâmetros customizáveis
- **Agendado** (`schedule`) com cron diário

> O cron é **opcional**: ele só executa se a variável do repositório
> `ENABLE_REGISTRATION_SCHEDULE` estiver como `true`.

### Como deixar o cron opcional

No GitHub, configure:

1. `Settings` → `Secrets and variables` → `Actions` → `Variables`
2. Crie `ENABLE_REGISTRATION_SCHEDULE`
3. Valor:
   - `true` = habilita execução agendada
   - `false` (ou não definir) = desabilita execução agendada

### Secrets obrigatórios da automação

- `LOGIN_EMAIL`
- `LOGIN_SENHA`

### Secrets opcionais para envio de email automático

Se todos estiverem configurados, o workflow envia um email no fim da execução:

- `SMTP_SERVER`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `EMAIL_TO`
- `EMAIL_FROM`

### O que o workflow gera

- artifacts com `logs/*.csv`, `logs/*.html`, `logs/*.pdf`
- `logs/run_summary.json`
- `logs/run_summary.md`
- resumo no `GITHUB_STEP_SUMMARY`
