"""Update consolidated detailed dataset for cloud dashboard usage.

Reads the current run CSV report and upserts records into
`analytics/detailed_runs.csv`.

Compatibility notes:
- Keeps detailed schema field names unchanged where required
  (e.g., `row_index`, `execution_status`, `detail`).
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


BASE_COLUMNS = [
    "row_index",
    "product_code",
    "brand",
    "product_type",
    "category",
    "unit_price",
    "cost",
    "notes",
    "execution_status",
    "detail",
]


def extract_run_id(report_file: str) -> str:
    match = re.search(r"(\d{8}_\d{6})", report_file or "")
    return match.group(1) if match else "unknown"


def extract_run_datetime(report_file: str) -> str:
    run_id = extract_run_id(report_file)
    if run_id != "unknown":
        try:
            dt = pd.to_datetime(run_id, format="%Y%m%d_%H%M%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def load_report(report_csv: Path) -> pd.DataFrame:
    if not report_csv.exists() or report_csv.stat().st_size == 0:
        return pd.DataFrame(columns=BASE_COLUMNS)

    try:
        df = pd.read_csv(report_csv, encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame(columns=BASE_COLUMNS)

    for column in BASE_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA

    return df[BASE_COLUMNS].copy()


def upsert_detailed(
    detailed_csv: Path,
    report_df: pd.DataFrame,
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

    if report_df.empty:
        base.to_csv(detailed_csv, index=False, encoding="utf-8-sig")
        return False

    new_data = report_df.copy()
    new_data["run_id"] = str(run_id)
    new_data["run_datetime"] = str(run_datetime)
    new_data["report_file"] = str(report_file)
    new_data["github_run_id"] = str(github_run_id or "")
    new_data["history_updated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    result = pd.concat([base, new_data], ignore_index=True)
    result["run_datetime"] = pd.to_datetime(result["run_datetime"], errors="coerce")
    result = result.sort_values(["run_datetime", "row_index"], ascending=[True, True])
    result.to_csv(detailed_csv, index=False, encoding="utf-8-sig")
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
    run_id = extract_run_id(report_file)
    run_datetime = extract_run_datetime(report_file)
    report_df = load_report(report_csv)

    changed = upsert_detailed(
        detailed_csv=detailed_csv,
        report_df=report_df,
        run_id=run_id,
        run_datetime=run_datetime,
        report_file=report_file,
        github_run_id=args.github_run_id,
    )

    print(f"Detailed history updated at: {detailed_csv}")
    print(f"Run records processed: {len(report_df)}")
    print(f"File changed: {'yes' if changed else 'no'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
