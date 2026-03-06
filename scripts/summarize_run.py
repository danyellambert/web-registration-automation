"""Generate an executive summary for the latest automation run.

Typical GitHub Actions usage:
    python scripts/summarize_run.py \
      --logs-dir logs \
      --json-output logs/run_summary.json \
      --markdown-output logs/run_summary.md \
      --run-url "$RUN_URL"

When `GITHUB_OUTPUT` is available, this script also exports step outputs.

Compatibility notes:
- Supports both report naming conventions:
  - `registration_report_*.csv` (current)
  - `relatorio_cadastro_*.csv` (legacy)
- Keeps summary field names compatible with historical schema
  (`ok_parcial`, `nao_confirmado`, etc.).
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


def find_latest_report(logs_dir: Path) -> Path | None:
    current_pattern = sorted(logs_dir.glob("registration_report_*.csv"))
    legacy_pattern = sorted(logs_dir.glob("relatorio_cadastro_*.csv"))
    all_reports = current_pattern + legacy_pattern
    if not all_reports:
        return None
    return max(all_reports, key=lambda path: path.stat().st_mtime)


def extract_run_id(report_file: str) -> str:
    match = re.search(r"(\d{8}_\d{6})", report_file)
    return match.group(1) if match else "unknown"


def compute_metrics(report_csv: Path, run_url: str) -> RunSummary:
    counters = {
        "ok": 0,
        "ok_parcial": 0,
        "nao_confirmado": 0,
        "erro": 0,
        "outros_status": 0,
    }

    total = 0
    with report_csv.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            total += 1
            status = (row.get("status_execucao") or "").strip()
            if status in counters:
                counters[status] += 1
            else:
                counters["outros_status"] += 1

    critical_failures = counters["nao_confirmado"] + counters["erro"]
    success_rate = (counters["ok"] / total * 100.0) if total else 0.0

    return RunSummary(
        report_file=report_csv.name,
        generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        run_url=run_url,
        total=total,
        ok=counters["ok"],
        ok_parcial=counters["ok_parcial"],
        nao_confirmado=counters["nao_confirmado"],
        erro=counters["erro"],
        outros_status=counters["outros_status"],
        falhas_criticas=critical_failures,
        success_rate=round(success_rate, 2),
    )


def build_markdown(summary: RunSummary) -> str:
    run_id = extract_run_id(summary.report_file)
    lines = [
        "## 📦 Registration automation summary",
        f"- **Run ID:** `{run_id}`",
        f"- **Analyzed report:** `{summary.report_file}`",
        f"- **Generated at:** {summary.generated_at}",
    ]
    if summary.run_url:
        lines.append(f"- **GitHub Actions run:** {summary.run_url}")

    lines.extend(
        [
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Total processed | {summary.total} |",
            f"| OK | {summary.ok} |",
            f"| OK partial | {summary.ok_parcial} |",
            f"| Not confirmed | {summary.nao_confirmado} |",
            f"| Error | {summary.erro} |",
            f"| Other statuses | {summary.outros_status} |",
            f"| Critical failures | {summary.falhas_criticas} |",
            f"| Success rate | {summary.success_rate:.2f}% |",
            "",
        ]
    )
    return "\n".join(lines)


def persist_outputs(summary: RunSummary, json_output: Path, markdown_output: Path) -> None:
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)

    json_output.write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown_output.write_text(build_markdown(summary), encoding="utf-8")


def export_github_outputs(summary: RunSummary, report_path: str) -> None:
    github_output_path = os.getenv("GITHUB_OUTPUT")
    if not github_output_path:
        return

    pairs = {
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

    with Path(github_output_path).open("a", encoding="utf-8") as file:
        for key, value in pairs.items():
            file.write(f"{key}={value}\n")


def export_no_report_state() -> None:
    github_output_path = os.getenv("GITHUB_OUTPUT")
    if not github_output_path:
        return

    with Path(github_output_path).open("a", encoding="utf-8") as file:
        file.write("has_report=false\n")
        file.write("report_file=\n")
        file.write("report_path=\n")
        file.write("total=0\n")
        file.write("ok=0\n")
        file.write("ok_parcial=0\n")
        file.write("nao_confirmado=0\n")
        file.write("erro=0\n")
        file.write("falhas_criticas=0\n")
        file.write("success_rate=0.00\n")


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

    report = find_latest_report(logs_dir)
    if report is None:
        message = (
            "## 📦 Registration automation summary\n"
            "- No `registration_report_*.csv` or legacy `relatorio_cadastro_*.csv` found in `logs/`.\n"
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
        markdown_output.write_text(message, encoding="utf-8")
        export_no_report_state()
        return 0

    summary = compute_metrics(report, args.run_url)
    persist_outputs(summary, json_output=json_output, markdown_output=markdown_output)
    export_github_outputs(summary, report_path=str(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
