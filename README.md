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
- `SMTP_SECURE` (opcional, padrão `true`)

#### Exemplo rápido (Gmail)

- `SMTP_SERVER = smtp.gmail.com`
- `SMTP_PORT = 465`
- `SMTP_SECURE = true`
- `SMTP_USERNAME = seuemail@gmail.com`
- `SMTP_PASSWORD = APP PASSWORD de 16 caracteres` (não é a senha normal)
- `EMAIL_FROM = seuemail@gmail.com`
- `EMAIL_TO = seuemail@gmail.com`

> Importante: no Gmail, habilite 2FA e gere uma **App Password**.
> Erro `535-5.7.8 Username and Password not accepted` normalmente indica
> credencial inválida (senha normal no lugar da App Password, usuário incorreto,
> ou app password expirada).

#### Observação de robustez

Se o SMTP falhar, o workflow **não derruba a automação principal**.
Ele registra aviso no summary e continua publicando artifacts.

### O que o workflow gera

- artifacts com `logs/*.csv`, `logs/*.html`, `logs/*.pdf`
- `logs/run_summary.json`
- `logs/run_summary.md`
- `analytics/history_runs.csv` (histórico consolidado de execuções)
- `analytics/detailed_runs.csv` (base detalhada consolidada por registro)
- resumo no `GITHUB_STEP_SUMMARY`

## Histórico consolidado (Fase 3)

Agora o workflow atualiza automaticamente `analytics/history_runs.csv` a cada execução,
salvando métricas agregadas por run (total, ok, falhas, taxa de sucesso, run URL etc.).

Esse arquivo é comitado automaticamente pelo GitHub Actions na branch atual.

### Pré-requisito

Em `Settings -> Actions -> General`, garanta permissão de escrita para o token:

- **Workflow permissions: Read and write permissions**

Sem isso, a automação principal roda, mas o push do histórico pode falhar.

## Dashboard com histórico cloud (Fase 4)

O `dashboard.py` agora lê duas fontes:

1. `logs/relatorio_cadastro_*.csv` (detalhe local por registro)
2. `analytics/history_runs.csv` (histórico consolidado por execução)

Quando estiver em ambiente cloud sem a pasta `logs/`, o dashboard usa fallback para:

- `analytics/detailed_runs.csv` (base detalhada versionada no repositório)

Opcionalmente, você pode definir a variável de ambiente `HISTORY_REMOTE_URL`
para carregar um CSV remoto de histórico quando não houver arquivo local.

Opcionalmente, você pode definir `DETAILED_REMOTE_URL` para carregar a base detalhada
de um CSV remoto quando necessário.

### Atualização automática do dashboard (sem reboot)

O dashboard possui controles para evitar reboot manual:

- botão **🔄 Atualizar agora** (limpa cache e recarrega dados)
- toggle **Auto-refresh** no intervalo configurado
- cache com TTL configurável via variável de ambiente

Variável opcional:

- `DASHBOARD_CACHE_TTL` (segundos, padrão `60`)

Exemplo no Streamlit Cloud (Settings → Secrets):

```toml
HISTORY_REMOTE_URL = "https://raw.githubusercontent.com/danyellambert/web-registration-automation/main/analytics/history_runs.csv"
DETAILED_REMOTE_URL = "https://raw.githubusercontent.com/danyellambert/web-registration-automation/main/analytics/detailed_runs.csv"
DASHBOARD_CACHE_TTL = "60"
```

### Link do dashboard no email da execução

O email enviado pelo workflow agora inclui também o link direto do dashboard:

- `https://web-registration-automation-dashboard.streamlit.app/`
