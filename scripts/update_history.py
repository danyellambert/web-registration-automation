"""Update consolidated automation run history.

Typical usage:
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

Compatibility notes:
- Keeps history schema column names unchanged where required
  (e.g., `ok_parcial`, `nao_confirmado`, `falhas_criticas`).
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def to_int(value: object, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(str(value).strip())
    except Exception:
        return default


def to_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(str(value).strip().replace(",", "."))
    except Exception:
        return default


def extract_run_id(report_file: str) -> str:
    match = re.search(r"(\d{8}_\d{6})", report_file or "")
    return match.group(1) if match else "unknown"


def extract_run_datetime(report_file: str, generated_at: str) -> pd.Timestamp:
    run_id = extract_run_id(report_file)
    if run_id != "unknown":
        try:
            return pd.to_datetime(run_id, format="%Y%m%d_%H%M%S")
        except Exception:
            pass

    try:
        # Example input: 2026-03-05 17:30:06 UTC
        if generated_at.endswith(" UTC"):
            generated_at = generated_at.replace(" UTC", "")
        return pd.to_datetime(generated_at, format="%Y-%m-%d %H:%M:%S")
    except Exception:
        return pd.Timestamp.utcnow().tz_localize(None)


def load_summary(summary_json: Path) -> dict[str, object]:
    if not summary_json.exists():
        raise FileNotFoundError(f"Summary file not found: {summary_json}")
    return json.loads(summary_json.read_text(encoding="utf-8"))


def build_history_row(summary: dict[str, object], args: argparse.Namespace) -> dict[str, object]:
    report_file = str(summary.get("report_file") or "")
    generated_at = str(summary.get("generated_at") or "")
    run_datetime = extract_run_datetime(report_file, generated_at)

    row = {
        "history_updated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "run_id": extract_run_id(report_file),
        "run_datetime": run_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "report_file": report_file,
        "total": to_int(summary.get("total")),
        "ok": to_int(summary.get("ok")),
        "ok_parcial": to_int(summary.get("ok_parcial")),
        "nao_confirmado": to_int(summary.get("nao_confirmado")),
        "erro": to_int(summary.get("erro")),
        "outros_status": to_int(summary.get("outros_status")),
        "falhas_criticas": to_int(summary.get("falhas_criticas")),
        "success_rate": to_float(summary.get("success_rate")),
        "github_run_id": str(args.github_run_id or ""),
        "github_run_number": str(args.github_run_number or ""),
        "github_run_attempt": str(args.github_run_attempt or ""),
        "repository": str(args.repository or ""),
        "ref_name": str(args.ref_name or ""),
        "actor": str(args.actor or ""),
        "event_name": str(args.event_name or ""),
        "run_url": str(args.run_url or ""),
    }
    return row


def upsert_history(history_csv: Path, row: dict[str, object]) -> bool:
    history_csv.parent.mkdir(parents=True, exist_ok=True)

    if history_csv.exists() and history_csv.stat().st_size > 0:
        history = pd.read_csv(history_csv, encoding="utf-8-sig")
    else:
        history = pd.DataFrame()

    if "github_run_id" in history.columns:
        history["github_run_id"] = history["github_run_id"].fillna("").astype(str)

    github_run_id = str(row.get("github_run_id") or "")
    changed = False

    if history.empty:
        history = pd.DataFrame([row])
        changed = True
    else:
        if "github_run_id" in history.columns:
            history["github_run_id"] = history["github_run_id"].fillna("").astype(str)

        if github_run_id and "github_run_id" in history.columns:
            mask = history["github_run_id"] == github_run_id
            if mask.any():
                for key, value in row.items():
                    history.loc[mask, key] = value
                changed = True
            else:
                history = pd.concat([history, pd.DataFrame([row])], ignore_index=True)
                changed = True
        else:
            history = pd.concat([history, pd.DataFrame([row])], ignore_index=True)
            changed = True

    if "run_datetime" in history.columns:
        history["_run_dt_sort"] = pd.to_datetime(history["run_datetime"], errors="coerce")
        history = history.sort_values("_run_dt_sort").drop(columns=["_run_dt_sort"])

    history.to_csv(history_csv, index=False, encoding="utf-8-sig")
    return changed


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

    summary = load_summary(summary_json)
    row = build_history_row(summary, args)
    upsert_history(history_csv, row)
    print(f"History updated at: {history_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
