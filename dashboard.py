"""Dashboard Streamlit para análise dos relatórios de cadastro web.

Lê os arquivos `logs/relatorio_cadastro_*.csv` gerados pela automação
e apresenta indicadores corporativos de execução.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

LOG_DIR = Path(__file__).resolve().parent / "logs"
PATTERN_RELATORIO = "relatorio_cadastro_*.csv"
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


@st.cache_data(show_spinner=False)
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
            # Ignora arquivos corrompidos para não derrubar o dashboard.
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

    for coluna_texto in ["codigo", "marca", "status_execucao", "detalhe"]:
        dados[coluna_texto] = dados[coluna_texto].fillna("").astype(str)

    return dados


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


def main() -> None:
    st.set_page_config(
        page_title="Dashboard de Cadastro Web",
        page_icon="📊",
        layout="wide",
    )

    st.title("📊 Dashboard de Resultados da Automação de Cadastro")
    st.caption(
        "Visão executiva de desempenho, falhas e histórico das execuções "
        "a partir dos relatórios CSV em logs/."
    )

    dados = carregar_relatorios(str(LOG_DIR))

    if dados.empty:
        st.info(
            "Nenhum relatório encontrado em logs/. "
            "Execute `python cadastro_web.py` para gerar arquivos `relatorio_cadastro_*.csv`."
        )
        return

    datas_validas = dados["run_date"].dropna()
    if datas_validas.empty:
        min_date = max_date = date.today()
    else:
        min_date = datas_validas.min()
        max_date = datas_validas.max()

    status_disponiveis = sorted(s for s in dados["status_execucao"].unique() if s)

    with st.sidebar:
        st.header("Filtros")
        periodo = st.date_input(
            "Período da execução",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

        status_selecionados = st.multiselect(
            "Status",
            options=status_disponiveis,
            default=status_disponiveis,
        )

        busca = st.text_input("Buscar por código ou marca", value="").strip()

    inicio, fim = normalizar_periodo(periodo, min_date, max_date)

    filtrado = dados[(dados["run_date"] >= inicio) & (dados["run_date"] <= fim)].copy()

    if status_selecionados:
        filtrado = filtrado[filtrado["status_execucao"].isin(status_selecionados)]

    if busca:
        mascara_busca = filtrado["codigo"].str.contains(
            busca, case=False, na=False
        ) | filtrado["marca"].str.contains(busca, case=False, na=False)
        filtrado = filtrado[mascara_busca]

    total_registros = len(filtrado)
    total_execucoes = filtrado["run_id"].nunique()
    total_ok = int((filtrado["status_execucao"] == "ok").sum())
    total_falhas = int(
        filtrado["status_execucao"].isin(["erro", "nao_confirmado"]).sum()
    )
    taxa_sucesso = (total_ok / total_registros * 100) if total_registros else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Execuções", total_execucoes)
    c2.metric("Registros processados", total_registros)
    c3.metric("Taxa de sucesso", f"{taxa_sucesso:.1f}%")
    c4.metric("Falhas críticas", total_falhas)

    if filtrado.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return

    resumo_status = (
        filtrado.groupby("status_execucao", dropna=False)
        .size()
        .reset_index(name="quantidade")
        .sort_values("quantidade", ascending=False)
    )

    fig_status = px.bar(
        resumo_status,
        x="status_execucao",
        y="quantidade",
        color="status_execucao",
        text_auto=True,
        title="Distribuição por status",
    )
    fig_status.update_layout(showlegend=False, xaxis_title="Status", yaxis_title="Qtd")

    resumo_execucao = (
        filtrado.groupby(["run_id", "run_datetime"], dropna=False)
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
    resumo_execucao["taxa_sucesso"] = (
        resumo_execucao["ok"] / resumo_execucao["total"] * 100
    ).fillna(0)

    fig_tendencia = px.line(
        resumo_execucao,
        x="run_datetime",
        y="taxa_sucesso",
        markers=True,
        hover_data={"run_id": True, "total": True, "ok": True, "falhas": True},
        title="Taxa de sucesso por execução",
    )
    fig_tendencia.update_layout(
        xaxis_title="Data/Hora da execução",
        yaxis_title="Taxa de sucesso (%)",
        yaxis_range=[0, 100],
    )

    g1, g2 = st.columns(2)
    g1.plotly_chart(fig_status, use_container_width=True)
    g2.plotly_chart(fig_tendencia, use_container_width=True)

    st.subheader("Falhas e registros para investigação")
    falhas = (
        filtrado[filtrado["status_execucao"] != "ok"][
            [
                "run_datetime",
                "run_id",
                "indice_csv",
                "codigo",
                "marca",
                "status_execucao",
                "detalhe",
                "arquivo_origem",
            ]
        ]
        .sort_values(["run_datetime", "indice_csv"], ascending=[False, True])
        .reset_index(drop=True)
    )

    if falhas.empty:
        st.success("Nenhuma falha encontrada para os filtros selecionados.")
    else:
        st.dataframe(falhas, use_container_width=True, hide_index=True)

    st.subheader("Dados filtrados")
    visualizacao = filtrado.sort_values(
        ["run_datetime", "indice_csv"], ascending=[False, True]
    ).reset_index(drop=True)
    st.dataframe(visualizacao, use_container_width=True, hide_index=True)

    arquivo_download = (
        f"dashboard_registros_filtrados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )
    st.download_button(
        label="⬇️ Baixar CSV com dados filtrados",
        data=visualizacao.to_csv(index=False, encoding="utf-8-sig"),
        file_name=arquivo_download,
        mime="text/csv",
        use_container_width=True,
    )


if __name__ == "__main__":
    main()
