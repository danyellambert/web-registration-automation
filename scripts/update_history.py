"""Atualiza histórico consolidado de execuções da automação.

Uso típico:
    python scripts/update_history.py \
      --summary-json logs/run_summary.json \
      --history-csv analytics/history_runs.csv \
      --github-run-id "$GITHUB_RUN_ID" \
      --github-run-number "$GITHUB_RUN_NUMBER" \
      --github-run-attempt "$GITHUB_RUN_ATTEMPT" \
      --repository "$GITHUB_REPOSITORY" \
      --ref-name "$GITHUB_REF_NAME" \
      --actor "$GITHUB_ACTOR" \
      --event-name "$GITHUB_EVENT_NAME" \
      --run-url "$RUN_URL"
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def _to_int(valor: object, padrao: int = 0) -> int:
    try:
        if valor is None:
            return padrao
        return int(str(valor).strip())
    except Exception:
        return padrao


def _to_float(valor: object, padrao: float = 0.0) -> float:
    try:
        if valor is None:
            return padrao
        return float(str(valor).strip().replace(",", "."))
    except Exception:
        return padrao


def extrair_run_id(report_file: str) -> str:
    match = re.search(r"(\d{8}_\d{6})", report_file or "")
    return match.group(1) if match else "desconhecido"


def extrair_run_datetime(report_file: str, generated_at: str) -> pd.Timestamp:
    run_id = extrair_run_id(report_file)
    if run_id != "desconhecido":
        try:
            return pd.to_datetime(run_id, format="%Y%m%d_%H%M%S")
        except Exception:
            pass

    try:
        # Exemplo de entrada: 2026-03-05 17:30:06 UTC
        if generated_at.endswith(" UTC"):
            generated_at = generated_at.replace(" UTC", "")
        return pd.to_datetime(generated_at, format="%Y-%m-%d %H:%M:%S")
    except Exception:
        return pd.Timestamp.utcnow().tz_localize(None)


def carregar_summary(summary_json: Path) -> dict[str, object]:
    if not summary_json.exists():
        raise FileNotFoundError(f"Arquivo de summary não encontrado: {summary_json}")
    return json.loads(summary_json.read_text(encoding="utf-8"))


def montar_linha(summary: dict[str, object], args: argparse.Namespace) -> dict[str, object]:
    report_file = str(summary.get("report_file") or "")
    generated_at = str(summary.get("generated_at") or "")
    run_datetime = extrair_run_datetime(report_file, generated_at)

    linha = {
        "history_updated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "run_id": extrair_run_id(report_file),
        "run_datetime": run_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "report_file": report_file,
        "total": _to_int(summary.get("total")),
        "ok": _to_int(summary.get("ok")),
        "ok_parcial": _to_int(summary.get("ok_parcial")),
        "nao_confirmado": _to_int(summary.get("nao_confirmado")),
        "erro": _to_int(summary.get("erro")),
        "outros_status": _to_int(summary.get("outros_status")),
        "falhas_criticas": _to_int(summary.get("falhas_criticas")),
        "success_rate": _to_float(summary.get("success_rate")),
        "github_run_id": str(args.github_run_id or ""),
        "github_run_number": str(args.github_run_number or ""),
        "github_run_attempt": str(args.github_run_attempt or ""),
        "repository": str(args.repository or ""),
        "ref_name": str(args.ref_name or ""),
        "actor": str(args.actor or ""),
        "event_name": str(args.event_name or ""),
        "run_url": str(args.run_url or ""),
    }
    return linha


def upsert_history(history_csv: Path, linha: dict[str, object]) -> bool:
    history_csv.parent.mkdir(parents=True, exist_ok=True)

    if history_csv.exists() and history_csv.stat().st_size > 0:
        historico = pd.read_csv(history_csv)
    else:
        historico = pd.DataFrame()

    if "github_run_id" in historico.columns:
        historico["github_run_id"] = historico["github_run_id"].fillna("").astype(str)

    run_id = str(linha.get("github_run_id") or "")
    alterou = False

    if historico.empty:
        historico = pd.DataFrame([linha])
        alterou = True
    else:
        if "github_run_id" in historico.columns:
            historico["github_run_id"] = historico["github_run_id"].fillna("").astype(str)

        if run_id and "github_run_id" in historico.columns:
            mascara = historico["github_run_id"] == run_id
            if mascara.any():
                for chave, valor in linha.items():
                    historico.loc[mascara, chave] = valor
                alterou = True
            else:
                historico = pd.concat([historico, pd.DataFrame([linha])], ignore_index=True)
                alterou = True
        else:
            historico = pd.concat([historico, pd.DataFrame([linha])], ignore_index=True)
            alterou = True

    if "run_datetime" in historico.columns:
        historico["_run_dt_sort"] = pd.to_datetime(historico["run_datetime"], errors="coerce")
        historico = historico.sort_values("_run_dt_sort").drop(columns=["_run_dt_sort"])

    historico.to_csv(history_csv, index=False, encoding="utf-8-sig")
    return alterou


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--history-csv", required=True)
    parser.add_argument("--github-run-id", default="")
    parser.add_argument("--github-run-number", default="")
    parser.add_argument("--github-run-attempt", default="")
    parser.add_argument("--repository", default="")
    parser.add_argument("--ref-name", default="")
    parser.add_argument("--actor", default="")
    parser.add_argument("--event-name", default="")
    parser.add_argument("--run-url", default="")
    args = parser.parse_args()

    summary_json = Path(args.summary_json)
    history_csv = Path(args.history_csv)

    summary = carregar_summary(summary_json)
    linha = montar_linha(summary, args)
    upsert_history(history_csv, linha)
    print(f"Histórico atualizado em: {history_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
