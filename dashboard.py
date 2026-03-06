"""Dashboard Streamlit corporativo para monitoramento da automação.

Camadas de análise:
1) Executiva (KPIs e tendência)
2) Operacional (status por dimensão e distribuição)
3) Qualidade e investigação (falhas, detalhe por registro)
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def _int_env(nome: str, padrao: int) -> int:
    try:
        valor = int(os.getenv(nome, str(padrao)))
        return valor if valor > 0 else padrao
    except Exception:
        return padrao


LOG_DIR = Path(__file__).resolve().parent / "logs"
HISTORY_CSV = Path(__file__).resolve().parent / "analytics" / "history_runs.csv"
DASHBOARD_DETAILED_CSV = Path(__file__).resolve().parent / "analytics" / "detailed_runs.csv"
HISTORY_REMOTE_URL = os.getenv("HISTORY_REMOTE_URL", "").strip()
DETAILED_REMOTE_URL = os.getenv("DETAILED_REMOTE_URL", "").strip()
CACHE_TTL_SECONDS = _int_env("DASHBOARD_CACHE_TTL", 60)

PATTERN_RELATORIO = "relatorio_cadastro_*.csv"
STATUS_ORDEM = ["ok", "ok_parcial", "nao_confirmado", "erro"]

COLUNAS_BASE = [
    "indice_csv",
    "codigo",
    "marca",
    "tipo",
    "categoria",
    "preco_unitario",
    "custo",
    "obs",
    "status_execucao",
    "detalhe",
]

COLUNAS_HISTORICO = [
    "history_updated_at_utc",
    "run_id",
    "run_datetime",
    "report_file",
    "total",
    "ok",
    "ok_parcial",
    "nao_confirmado",
    "erro",
    "outros_status",
    "falhas_criticas",
    "success_rate",
    "github_run_id",
    "github_run_number",
    "github_run_attempt",
    "repository",
    "ref_name",
    "actor",
    "event_name",
    "run_url",
]


def extrair_execucao_do_nome(nome_arquivo: str) -> tuple[str, pd.Timestamp]:
    match = re.search(r"(\d{8}_\d{6})", nome_arquivo)
    if not match:
        return nome_arquivo, pd.NaT

    run_id = match.group(1)
    try:
        run_datetime = pd.to_datetime(run_id, format="%Y%m%d_%H%M%S")
    except ValueError:
        run_datetime = pd.NaT
    return run_id, run_datetime


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def carregar_relatorios(log_dir: str) -> pd.DataFrame:
    diretorio_logs = Path(log_dir)
    if not diretorio_logs.exists():
        return pd.DataFrame()

    relatorios = sorted(diretorio_logs.glob(PATTERN_RELATORIO))
    if not relatorios:
        return pd.DataFrame()

    consolidado: list[pd.DataFrame] = []

    for arquivo in relatorios:
        try:
            df = pd.read_csv(arquivo)
        except Exception:
            continue

        for coluna in COLUNAS_BASE:
            if coluna not in df.columns:
                df[coluna] = pd.NA

        run_id, run_datetime = extrair_execucao_do_nome(arquivo.name)
        df["arquivo_origem"] = arquivo.name
        df["run_id"] = run_id
        df["run_datetime"] = run_datetime
        consolidado.append(df)

    if not consolidado:
        return pd.DataFrame()

    dados = pd.concat(consolidado, ignore_index=True)
    dados["run_datetime"] = pd.to_datetime(dados["run_datetime"], errors="coerce")
    dados["run_date"] = dados["run_datetime"].dt.date

    for coluna in ["codigo", "marca", "tipo", "categoria", "status_execucao", "detalhe"]:
        dados[coluna] = dados[coluna].fillna("").astype(str)

    for coluna_num in ["preco_unitario", "custo"]:
        dados[coluna_num] = pd.to_numeric(dados[coluna_num], errors="coerce").fillna(0.0)

    dados["margem_unitaria"] = dados["preco_unitario"] - dados["custo"]
    return dados


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def carregar_detalhado_cloud(detailed_csv: str, detailed_remote_url: str = "") -> pd.DataFrame:
    caminho = Path(detailed_csv)
    detalhado = pd.DataFrame()

    if caminho.exists() and caminho.stat().st_size > 0:
        try:
            detalhado = pd.read_csv(caminho, encoding="utf-8-sig")
        except Exception:
            detalhado = pd.DataFrame()

    if detalhado.empty and detailed_remote_url:
        try:
            detalhado = pd.read_csv(detailed_remote_url)
        except Exception:
            detalhado = pd.DataFrame()

    if detalhado.empty:
        return pd.DataFrame()

    for coluna in COLUNAS_BASE:
        if coluna not in detalhado.columns:
            detalhado[coluna] = pd.NA

    if "run_id" not in detalhado.columns:
        detalhado["run_id"] = "desconhecido"

    if "run_datetime" not in detalhado.columns:
        if "report_file" in detalhado.columns:
            detalhado["run_datetime"] = detalhado["report_file"].apply(
                lambda nome: extrair_execucao_do_nome(str(nome))[1]
            )
        else:
            detalhado["run_datetime"] = pd.NaT

    detalhado["run_datetime"] = pd.to_datetime(detalhado["run_datetime"], errors="coerce")
    detalhado["run_date"] = detalhado["run_datetime"].dt.date

    for coluna in ["codigo", "marca", "tipo", "categoria", "status_execucao", "detalhe"]:
        detalhado[coluna] = detalhado[coluna].fillna("").astype(str)

    for coluna_num in ["preco_unitario", "custo"]:
        detalhado[coluna_num] = pd.to_numeric(detalhado[coluna_num], errors="coerce").fillna(0.0)

    detalhado["margem_unitaria"] = detalhado["preco_unitario"] - detalhado["custo"]
    return detalhado


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def carregar_historico(history_csv: str, history_remote_url: str = "") -> pd.DataFrame:
    caminho = Path(history_csv)
    historico = pd.DataFrame()

    if caminho.exists() and caminho.stat().st_size > 0:
        try:
            historico = pd.read_csv(caminho, encoding="utf-8-sig")
        except Exception:
            historico = pd.DataFrame()

    if historico.empty and history_remote_url:
        try:
            historico = pd.read_csv(history_remote_url)
        except Exception:
            historico = pd.DataFrame()

    if historico.empty:
        return pd.DataFrame()

    for coluna in COLUNAS_HISTORICO:
        if coluna not in historico.columns:
            historico[coluna] = pd.NA

    historico["run_datetime"] = pd.to_datetime(historico["run_datetime"], errors="coerce")
    historico["run_date"] = historico["run_datetime"].dt.date

    for coluna in [
        "total",
        "ok",
        "ok_parcial",
        "nao_confirmado",
        "erro",
        "outros_status",
        "falhas_criticas",
        "success_rate",
    ]:
        historico[coluna] = pd.to_numeric(historico[coluna], errors="coerce").fillna(0)

    for coluna in ["run_id", "run_url", "event_name", "actor", "github_run_id"]:
        historico[coluna] = historico[coluna].fillna("").astype(str)

    return historico


def normalizar_periodo(
    periodo: tuple[date, date] | list[date] | date,
    min_date: date,
    max_date: date,
) -> tuple[date, date]:
    if isinstance(periodo, tuple):
        if len(periodo) == 2:
            return periodo[0], periodo[1]
        if len(periodo) == 1:
            return periodo[0], periodo[0]
    if isinstance(periodo, list):
        if len(periodo) == 2:
            return periodo[0], periodo[1]
        if len(periodo) == 1:
            return periodo[0], periodo[0]
    if isinstance(periodo, date):
        return periodo, periodo
    return min_date, max_date


def _formatar_num(valor: float | int) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def _criar_gauge(valor: float, alvo: float) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=float(valor),
            number={"suffix": "%"},
            delta={"reference": float(alvo), "relative": False},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#00A36C" if valor >= alvo else "#FF4B4B"},
                "steps": [
                    {"range": [0, 85], "color": "#ffe5e5"},
                    {"range": [85, alvo], "color": "#fff5cc"},
                    {"range": [alvo, 100], "color": "#e6f7ef"},
                ],
                "threshold": {
                    "line": {"color": "#222", "width": 2},
                    "thickness": 0.75,
                    "value": float(alvo),
                },
            },
            title={"text": "SLA de sucesso"},
        )
    )
    fig.update_layout(height=260, margin=dict(l=20, r=20, t=60, b=20))
    return fig


def main() -> None:
    st.set_page_config(
        page_title="Registration Automation | Executive Dashboard",
        page_icon="📈",
        layout="wide",
    )

    st.title("📈 Registration Automation — Executive Control Tower")
    st.caption(
        "Monitoramento executivo, operacional e de qualidade da automação de cadastro."
    )

    if "auto_refresh" not in st.session_state:
        st.session_state.auto_refresh = False

    dados_origem = "logs"
    dados = carregar_relatorios(str(LOG_DIR))
    if dados.empty:
        dados = carregar_detalhado_cloud(str(DASHBOARD_DETAILED_CSV), DETAILED_REMOTE_URL)
        if not dados.empty:
            dados_origem = "analytics"
    historico = carregar_historico(str(HISTORY_CSV), HISTORY_REMOTE_URL)

    if dados.empty and historico.empty:
        st.info(
            "Sem dados disponíveis. Rode a automação para gerar `logs/` e `analytics/history_runs.csv`."
        )
        return

    if dados_origem == "analytics":
        st.info(
            "Base detalhada carregada do histórico consolidado em `analytics/detailed_runs.csv` "
            "(modo cloud, sem `logs/` locais)."
        )

    datas_partes = []
    if not dados.empty:
        datas_partes.append(dados["run_date"].dropna())
    if not historico.empty:
        datas_partes.append(historico["run_date"].dropna())

    datas_validas = pd.concat(datas_partes) if datas_partes else pd.Series(dtype="object")
    if datas_validas.empty:
        min_date = max_date = date.today()
    else:
        min_date = datas_validas.min()
        max_date = datas_validas.max()

    marcas_disponiveis = sorted(m for m in (dados["marca"].unique() if not dados.empty else []) if m)
    eventos_disponiveis = sorted(
        e for e in (historico["event_name"].unique() if not historico.empty else []) if e
    )

    with st.sidebar:
        st.header("Atualização")
        st.caption(f"TTL cache: ~{CACHE_TTL_SECONDS}s")
        if st.button("🔄 Atualizar agora", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.session_state.auto_refresh = st.toggle(
            f"Auto-refresh ({CACHE_TTL_SECONDS}s)",
            value=st.session_state.auto_refresh,
        )

        st.divider()
        st.header("Filtros globais")
        periodo = st.date_input(
            "Período",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        busca = st.text_input("Buscar código/marca", value="").strip()
        marcas = st.multiselect("Marcas", options=marcas_disponiveis, default=[])
        eventos = st.multiselect("Tipo de evento (history)", options=eventos_disponiveis, default=[])
        alvo_sla = st.slider("Meta de sucesso (%)", min_value=80, max_value=100, value=97)

    if st.session_state.auto_refresh:
        refresh_ms = CACHE_TTL_SECONDS * 1000
        st.markdown(
            f"""
            <script>
            setTimeout(function() {{
                window.parent.location.reload();
            }}, {refresh_ms});
            </script>
            """,
            unsafe_allow_html=True,
        )

    inicio, fim = normalizar_periodo(periodo, min_date, max_date)

    detalhado = pd.DataFrame()
    if not dados.empty:
        detalhado = dados[(dados["run_date"] >= inicio) & (dados["run_date"] <= fim)].copy()
        if marcas:
            detalhado = detalhado[detalhado["marca"].isin(marcas)]
        if busca:
            mask = detalhado["codigo"].str.contains(busca, case=False, na=False) | detalhado[
                "marca"
            ].str.contains(busca, case=False, na=False)
            detalhado = detalhado[mask]

    hist = pd.DataFrame()
    if not historico.empty:
        hist = historico[(historico["run_date"] >= inicio) & (historico["run_date"] <= fim)].copy()
        if eventos:
            hist = hist[hist["event_name"].isin(eventos)]

    if detalhado.empty and hist.empty:
        st.warning("Sem dados para os filtros selecionados.")
        return

    # -----------------------------
    # KPIs executivos
    # -----------------------------
    if not hist.empty:
        total_execucoes = int(hist["run_id"].nunique())
        total_registros = int(hist["total"].sum())
        total_ok = int(hist["ok"].sum())
        falhas_criticas = int(hist["falhas_criticas"].sum())
        taxa_sucesso = (total_ok / total_registros * 100) if total_registros else 0.0
        ultima_exec = hist["run_datetime"].max()
    else:
        total_execucoes = int(detalhado["run_id"].nunique()) if not detalhado.empty else 0
        total_registros = int(len(detalhado))
        total_ok = int((detalhado["status_execucao"] == "ok").sum()) if not detalhado.empty else 0
        falhas_criticas = (
            int(detalhado["status_execucao"].isin(["erro", "nao_confirmado"]).sum())
            if not detalhado.empty
            else 0
        )
        taxa_sucesso = (total_ok / total_registros * 100) if total_registros else 0.0
        ultima_exec = detalhado["run_datetime"].max() if not detalhado.empty else pd.NaT

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Execuções", _formatar_num(total_execucoes))
    col2.metric("Registros", _formatar_num(total_registros))
    col3.metric("Sucesso", f"{taxa_sucesso:.2f}%")
    col4.metric("Falhas críticas", _formatar_num(falhas_criticas))
    col5.metric("Última execução", "-" if pd.isna(ultima_exec) else str(ultima_exec)[:16])

    st.plotly_chart(_criar_gauge(taxa_sucesso, alvo_sla), use_container_width=True)

    # -----------------------------
    # Linha 1 - tendências e composição
    # -----------------------------
    if not hist.empty:
        base_tendencia = hist.sort_values("run_datetime").copy()
        base_tendencia["taxa_sucesso"] = pd.to_numeric(
            base_tendencia["success_rate"], errors="coerce"
        ).fillna(0)
        base_tendencia["falhas"] = pd.to_numeric(base_tendencia["falhas_criticas"], errors="coerce").fillna(0)
    else:
        base_tendencia = (
            detalhado.groupby(["run_id", "run_datetime"], dropna=False)
            .agg(
                total=("status_execucao", "size"),
                ok=("status_execucao", lambda s: int((s == "ok").sum())),
                falhas=(
                    "status_execucao",
                    lambda s: int(s.isin(["erro", "nao_confirmado"]).sum()),
                ),
            )
            .reset_index()
            .sort_values("run_datetime")
        )
        base_tendencia["taxa_sucesso"] = (
            base_tendencia["ok"] / base_tendencia["total"] * 100
        ).fillna(0)

    if not detalhado.empty:
        status_counts = (
            detalhado.groupby("status_execucao", dropna=False)
            .size()
            .reset_index(name="quantidade")
            .sort_values("quantidade", ascending=False)
        )
    elif not hist.empty:
        status_counts = pd.DataFrame(
            {
                "status_execucao": ["ok", "ok_parcial", "nao_confirmado", "erro"],
                "quantidade": [
                    int(hist["ok"].sum()),
                    int(hist["ok_parcial"].sum()),
                    int(hist["nao_confirmado"].sum()),
                    int(hist["erro"].sum()),
                ],
            }
        )
        status_counts = status_counts[status_counts["quantidade"] > 0]
    else:
        status_counts = pd.DataFrame(columns=["status_execucao", "quantidade"])

    fig_tendencia = px.line(
        base_tendencia,
        x="run_datetime",
        y="taxa_sucesso",
        markers=True,
        hover_data={"run_id": True, "total": True, "ok": True, "falhas": True},
        title="Tendência de sucesso por execução",
    )
    fig_tendencia.update_layout(yaxis_title="Sucesso (%)", xaxis_title="Execução", yaxis_range=[0, 100])

    fig_status = px.pie(
        status_counts,
        names="status_execucao",
        values="quantidade",
        title="Composição de status",
        hole=0.5,
    )

    l1, l2 = st.columns((2, 1))
    l1.plotly_chart(fig_tendencia, use_container_width=True)
    l2.plotly_chart(fig_status, use_container_width=True)

    # -----------------------------
    # Linha 2 - eficiência por dimensão
    # -----------------------------
    if not detalhado.empty:
        por_marca = (
            detalhado.groupby("marca", dropna=False)
            .agg(
                total=("status_execucao", "size"),
                ok=("status_execucao", lambda s: int((s == "ok").sum())),
                falhas=(
                    "status_execucao",
                    lambda s: int(s.isin(["erro", "nao_confirmado"]).sum()),
                ),
                margem_media=("margem_unitaria", "mean"),
            )
            .reset_index()
        )
        por_marca["taxa_sucesso"] = (por_marca["ok"] / por_marca["total"] * 100).fillna(0)
        por_marca = por_marca.sort_values("total", ascending=False).head(12)

        fig_marca = px.bar(
            por_marca,
            x="marca",
            y="taxa_sucesso",
            color="total",
            text_auto=".1f",
            title="Eficiência por marca (Top 12 por volume)",
        )
        fig_marca.update_layout(yaxis_title="Sucesso (%)", xaxis_title="Marca")

        heat = (
            detalhado.assign(
                status_padrao=detalhado["status_execucao"].replace("", "sem_status")
            )
            .groupby(["categoria", "status_padrao"], dropna=False)
            .size()
            .reset_index(name="quantidade")
        )
        fig_heat = px.density_heatmap(
            heat,
            x="status_padrao",
            y="categoria",
            z="quantidade",
            color_continuous_scale="Blues",
            title="Mapa de calor categoria x status",
        )

        m1, m2 = st.columns(2)
        m1.plotly_chart(fig_marca, use_container_width=True)
        m2.plotly_chart(fig_heat, use_container_width=True)

    # -----------------------------
    # Tabelas de gestão
    # -----------------------------
    st.subheader("🧾 Histórico consolidado de execuções")
    if hist.empty:
        st.info("Sem histórico consolidado para os filtros atuais.")
    else:
        hist_view = hist[
            [
                "run_datetime",
                "run_id",
                "total",
                "ok",
                "ok_parcial",
                "nao_confirmado",
                "erro",
                "falhas_criticas",
                "success_rate",
                "event_name",
                "actor",
                "run_url",
            ]
        ].sort_values("run_datetime", ascending=False)
        st.dataframe(hist_view, use_container_width=True, hide_index=True)

    st.subheader("🚨 Fila de investigação de falhas")
    if detalhado.empty:
        st.info("Sem base detalhada local para investigação neste filtro.")
    else:
        falhas = (
            detalhado[detalhado["status_execucao"].isin(["erro", "nao_confirmado", "ok_parcial"])][
                [
                    "run_datetime",
                    "run_id",
                    "indice_csv",
                    "codigo",
                    "marca",
                    "tipo",
                    "categoria",
                    "status_execucao",
                    "detalhe",
                    "arquivo_origem",
                ]
            ]
            .sort_values(["run_datetime", "indice_csv"], ascending=[False, True])
            .reset_index(drop=True)
        )
        if falhas.empty:
            st.success("Nenhuma falha crítica/parcial encontrada para os filtros selecionados.")
        else:
            st.dataframe(falhas, use_container_width=True, hide_index=True)

    st.subheader("📦 Base detalhada filtrada")
    if detalhado.empty:
        st.info("Sem registros detalhados para os filtros atuais.")
    else:
        detalhado_view = detalhado.sort_values(
            ["run_datetime", "indice_csv"], ascending=[False, True]
        ).reset_index(drop=True)
        st.dataframe(detalhado_view, use_container_width=True, hide_index=True)

        nome_csv = f"dashboard_detalhado_{datetime.now():%Y%m%d_%H%M%S}.csv"
        st.download_button(
            label="⬇️ Baixar dataset detalhado filtrado",
            data=detalhado_view.to_csv(index=False, encoding="utf-8-sig"),
            file_name=nome_csv,
            mime="text/csv",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
