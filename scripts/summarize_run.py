"""Gera resumo executivo da última execução da automação.

Uso típico no GitHub Actions:
    python scripts/summarize_run.py \
      --logs-dir logs \
      --json-output logs/run_summary.json \
      --markdown-output logs/run_summary.md \
      --run-url "$RUN_URL"

Também escreve outputs para o step do Actions quando a variável
GITHUB_OUTPUT estiver disponível.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class RunSummary:
    report_file: str
    generated_at: str
    run_url: str
    total: int
    ok: int
    ok_parcial: int
    nao_confirmado: int
    erro: int
    outros_status: int
    falhas_criticas: int
    success_rate: float


def encontrar_relatorio_mais_recente(logs_dir: Path) -> Path | None:
    arquivos = sorted(logs_dir.glob("relatorio_cadastro_*.csv"))
    if not arquivos:
        return None
    return max(arquivos, key=lambda caminho: caminho.stat().st_mtime)


def extrair_run_id(report_file: str) -> str:
    match = re.search(r"(\d{8}_\d{6})", report_file)
    return match.group(1) if match else "desconhecido"


def calcular_metricas(relatorio_csv: Path, run_url: str) -> RunSummary:
    contadores = {
        "ok": 0,
        "ok_parcial": 0,
        "nao_confirmado": 0,
        "erro": 0,
        "outros_status": 0,
    }

    total = 0
    with relatorio_csv.open("r", encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        for linha in leitor:
            total += 1
            status = (linha.get("status_execucao") or "").strip()
            if status in contadores:
                contadores[status] += 1
            else:
                contadores["outros_status"] += 1

    falhas_criticas = contadores["nao_confirmado"] + contadores["erro"]
    taxa_sucesso = (contadores["ok"] / total * 100.0) if total else 0.0

    return RunSummary(
        report_file=relatorio_csv.name,
        generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        run_url=run_url,
        total=total,
        ok=contadores["ok"],
        ok_parcial=contadores["ok_parcial"],
        nao_confirmado=contadores["nao_confirmado"],
        erro=contadores["erro"],
        outros_status=contadores["outros_status"],
        falhas_criticas=falhas_criticas,
        success_rate=round(taxa_sucesso, 2),
    )


def gerar_markdown(summary: RunSummary) -> str:
    run_id = extrair_run_id(summary.report_file)
    linhas = [
        "## 📦 Resumo da automação de cadastro",
        f"- **Run ID:** `{run_id}`",
        f"- **Relatório analisado:** `{summary.report_file}`",
        f"- **Gerado em:** {summary.generated_at}",
    ]
    if summary.run_url:
        linhas.append(f"- **Execução no GitHub Actions:** {summary.run_url}")

    linhas.extend(
        [
            "",
            "| Métrica | Valor |",
            "|---|---:|",
            f"| Total processado | {summary.total} |",
            f"| OK | {summary.ok} |",
            f"| OK parcial | {summary.ok_parcial} |",
            f"| Não confirmado | {summary.nao_confirmado} |",
            f"| Erro | {summary.erro} |",
            f"| Outros status | {summary.outros_status} |",
            f"| Falhas críticas | {summary.falhas_criticas} |",
            f"| Taxa de sucesso | {summary.success_rate:.2f}% |",
            "",
        ]
    )
    return "\n".join(linhas)


def persistir_arquivos(summary: RunSummary, json_output: Path, md_output: Path) -> None:
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)

    json_output.write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output.write_text(gerar_markdown(summary), encoding="utf-8")


def exportar_para_github_output(summary: RunSummary, report_path: str) -> None:
    caminho_output = os.getenv("GITHUB_OUTPUT")
    if not caminho_output:
        return

    pares = {
        "has_report": "true",
        "report_file": summary.report_file,
        "report_path": report_path,
        "total": str(summary.total),
        "ok": str(summary.ok),
        "ok_parcial": str(summary.ok_parcial),
        "nao_confirmado": str(summary.nao_confirmado),
        "erro": str(summary.erro),
        "falhas_criticas": str(summary.falhas_criticas),
        "success_rate": f"{summary.success_rate:.2f}",
    }

    with Path(caminho_output).open("a", encoding="utf-8") as arquivo:
        for chave, valor in pares.items():
            arquivo.write(f"{chave}={valor}\n")


def exportar_sem_relatorio() -> None:
    caminho_output = os.getenv("GITHUB_OUTPUT")
    if not caminho_output:
        return

    with Path(caminho_output).open("a", encoding="utf-8") as arquivo:
        arquivo.write("has_report=false\n")
        arquivo.write("report_file=\n")
        arquivo.write("report_path=\n")
        arquivo.write("total=0\n")
        arquivo.write("ok=0\n")
        arquivo.write("ok_parcial=0\n")
        arquivo.write("nao_confirmado=0\n")
        arquivo.write("erro=0\n")
        arquivo.write("falhas_criticas=0\n")
        arquivo.write("success_rate=0.00\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--logs-dir", default="logs")
    parser.add_argument("--json-output", default="logs/run_summary.json")
    parser.add_argument("--markdown-output", default="logs/run_summary.md")
    parser.add_argument("--run-url", default="")
    args = parser.parse_args()

    logs_dir = Path(args.logs_dir)
    json_output = Path(args.json_output)
    markdown_output = Path(args.markdown_output)

    relatorio = encontrar_relatorio_mais_recente(logs_dir)
    if relatorio is None:
        mensagem = (
            "## 📦 Resumo da automação de cadastro\n"
            "- Nenhum `relatorio_cadastro_*.csv` encontrado em `logs/`.\n"
        )
        json_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(
            json.dumps(
                {
                    "report_file": "",
                    "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "run_url": args.run_url,
                    "total": 0,
                    "ok": 0,
                    "ok_parcial": 0,
                    "nao_confirmado": 0,
                    "erro": 0,
                    "outros_status": 0,
                    "falhas_criticas": 0,
                    "success_rate": 0.0,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        markdown_output.write_text(mensagem, encoding="utf-8")
        exportar_sem_relatorio()
        return 0

    summary = calcular_metricas(relatorio, args.run_url)
    persistir_arquivos(summary, json_output=json_output, md_output=markdown_output)
    exportar_para_github_output(summary, report_path=str(relatorio))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
