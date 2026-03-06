"""Atualiza base detalhada consolidada para uso no dashboard cloud.

Lê o relatório CSV da execução atual e faz upsert em `analytics/detailed_runs.csv`.
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


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


def extrair_run_id(report_file: str) -> str:
    match = re.search(r"(\d{8}_\d{6})", report_file or "")
    return match.group(1) if match else "desconhecido"


def extrair_run_datetime(report_file: str) -> str:
    run_id = extrair_run_id(report_file)
    if run_id != "desconhecido":
        try:
            dt = pd.to_datetime(run_id, format="%Y%m%d_%H%M%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def carregar_relatorio(report_csv: Path) -> pd.DataFrame:
    if not report_csv.exists() or report_csv.stat().st_size == 0:
        return pd.DataFrame(columns=COLUNAS_BASE)

    try:
        df = pd.read_csv(report_csv, encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame(columns=COLUNAS_BASE)

    for coluna in COLUNAS_BASE:
        if coluna not in df.columns:
            df[coluna] = pd.NA

    return df[COLUNAS_BASE].copy()


def upsert_detalhado(
    detailed_csv: Path,
    relatorio_df: pd.DataFrame,
    run_id: str,
    run_datetime: str,
    report_file: str,
    github_run_id: str,
) -> bool:
    detailed_csv.parent.mkdir(parents=True, exist_ok=True)

    if detailed_csv.exists() and detailed_csv.stat().st_size > 0:
        try:
            base = pd.read_csv(detailed_csv, encoding="utf-8-sig")
        except Exception:
            base = pd.DataFrame()
    else:
        base = pd.DataFrame()

    if not base.empty:
        for col in ["run_id", "github_run_id"]:
            if col in base.columns:
                base[col] = base[col].fillna("").astype(str)

        if "run_id" in base.columns:
            base = base[base["run_id"] != str(run_id)]

    if relatorio_df.empty:
        base.to_csv(detailed_csv, index=False, encoding="utf-8-sig")
        return False

    novo = relatorio_df.copy()
    novo["run_id"] = str(run_id)
    novo["run_datetime"] = str(run_datetime)
    novo["report_file"] = str(report_file)
    novo["github_run_id"] = str(github_run_id or "")
    novo["history_updated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    resultado = pd.concat([base, novo], ignore_index=True)
    resultado["run_datetime"] = pd.to_datetime(resultado["run_datetime"], errors="coerce")
    resultado = resultado.sort_values(["run_datetime", "indice_csv"], ascending=[True, True])
    resultado.to_csv(detailed_csv, index=False, encoding="utf-8-sig")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-csv", required=True)
    parser.add_argument("--detailed-csv", required=True)
    parser.add_argument("--github-run-id", default="")
    args = parser.parse_args()

    report_csv = Path(args.report_csv)
    detailed_csv = Path(args.detailed_csv)

    report_file = report_csv.name
    run_id = extrair_run_id(report_file)
    run_datetime = extrair_run_datetime(report_file)
    relatorio_df = carregar_relatorio(report_csv)

    alterou = upsert_detalhado(
        detailed_csv=detailed_csv,
        relatorio_df=relatorio_df,
        run_id=run_id,
        run_datetime=run_datetime,
        report_file=report_file,
        github_run_id=args.github_run_id,
    )

    print(f"Detalhado atualizado em: {detailed_csv}")
    print(f"Registros da execução: {len(relatorio_df)}")
    print(f"Alterou arquivo: {'sim' if alterou else 'não'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
