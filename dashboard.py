"""Corporate Streamlit dashboard for monitoring registration automation.

Analysis layers:
1) Executive (KPIs and trend)
2) Operational (status by dimension and distribution)
3) Quality and investigation (failures and record-level detail)

Important compatibility notes:
- Data schema fields from automation/history remain in Portuguese where required
  (e.g., execution_status, not_confirmed, critical_failures, etc.).
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


def _positive_int_env(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
        return value if value > 0 else default
    except Exception:
        return default


LOG_DIR = Path(__file__).resolve().parent / "logs"
HISTORY_CSV = Path(__file__).resolve().parent / "analytics" / "history_runs.csv"
DETAILED_DASHBOARD_CSV = Path(__file__).resolve().parent / "analytics" / "detailed_runs.csv"
HISTORY_REMOTE_URL = os.getenv("HISTORY_REMOTE_URL", "").strip()
DETAILED_REMOTE_URL = os.getenv("DETAILED_REMOTE_URL", "").strip()
CACHE_TTL_SECONDS = _positive_int_env("DASHBOARD_CACHE_TTL", 60)

REPORT_PATTERNS = ["registration_report_*.csv", "relatorio_cadastro_*.csv"]
STATUS_ORDER = ["ok", "partial_success", "not_confirmed", "error"]

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

HISTORY_COLUMNS = [
    "history_updated_at_utc",
    "run_id",
    "run_datetime",
    "report_file",
    "total",
    "ok",
    "partial_success",
    "not_confirmed",
    "error",
    "other_statuses",
    "critical_failures",
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


def extract_run_info_from_filename(filename: str) -> tuple[str, pd.Timestamp]:
    match = re.search(r"(\d{8}_\d{6})", filename)
    if not match:
        return filename, pd.NaT

    run_id = match.group(1)
    try:
        run_datetime = pd.to_datetime(run_id, format="%Y%m%d_%H%M%S")
    except ValueError:
        run_datetime = pd.NaT
    return run_id, run_datetime


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def load_reports(log_dir: str) -> pd.DataFrame:
    logs_path = Path(log_dir)
    if not logs_path.exists():
        return pd.DataFrame()

    report_files: list[Path] = []
    for pattern in REPORT_PATTERNS:
        report_files.extend(logs_path.glob(pattern))
    report_files = sorted(set(report_files))
    if not report_files:
        return pd.DataFrame()

    merged_frames: list[pd.DataFrame] = []

    for file_path in report_files:
        try:
            df = pd.read_csv(file_path)
        except Exception:
            continue

        for column in BASE_COLUMNS:
            if column not in df.columns:
                df[column] = pd.NA

        run_id, run_datetime = extract_run_info_from_filename(file_path.name)
        df["source_file"] = file_path.name
        df["run_id"] = run_id
        df["run_datetime"] = run_datetime
        merged_frames.append(df)

    if not merged_frames:
        return pd.DataFrame()

    data = pd.concat(merged_frames, ignore_index=True)
    data["run_datetime"] = pd.to_datetime(data["run_datetime"], errors="coerce")
    data["run_date"] = data["run_datetime"].dt.date

    for column in ["product_code", "brand", "product_type", "category", "execution_status", "detail"]:
        data[column] = data[column].fillna("").astype(str)

    for numeric_column in ["unit_price", "cost"]:
        data[numeric_column] = pd.to_numeric(data[numeric_column], errors="coerce").fillna(0.0)

    data["margem_unitaria"] = data["unit_price"] - data["cost"]
    return data


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def load_cloud_detailed_data(detailed_csv: str, detailed_remote_url: str = "") -> pd.DataFrame:
    detailed_path = Path(detailed_csv)
    detailed = pd.DataFrame()

    if detailed_path.exists() and detailed_path.stat().st_size > 0:
        try:
            detailed = pd.read_csv(detailed_path, encoding="utf-8-sig")
        except Exception:
            detailed = pd.DataFrame()

    if detailed.empty and detailed_remote_url:
        try:
            detailed = pd.read_csv(detailed_remote_url)
        except Exception:
            detailed = pd.DataFrame()

    if detailed.empty:
        return pd.DataFrame()

    for column in BASE_COLUMNS:
        if column not in detailed.columns:
            detailed[column] = pd.NA

    if "source_file" not in detailed.columns:
        if "report_file" in detailed.columns:
            detailed["source_file"] = detailed["report_file"].fillna("").astype(str)
        else:
            detailed["source_file"] = "analytics/detailed_runs.csv"

    if "run_id" not in detailed.columns:
        detailed["run_id"] = "unknown"

    if "run_datetime" not in detailed.columns:
        if "report_file" in detailed.columns:
            detailed["run_datetime"] = detailed["report_file"].apply(
                lambda name: extract_run_info_from_filename(str(name))[1]
            )
        else:
            detailed["run_datetime"] = pd.NaT

    detailed["run_datetime"] = pd.to_datetime(detailed["run_datetime"], errors="coerce")
    detailed["run_date"] = detailed["run_datetime"].dt.date

    for column in [
        "product_code",
        "brand",
        "product_type",
        "category",
        "execution_status",
        "detail",
        "source_file",
    ]:
        detailed[column] = detailed[column].fillna("").astype(str)

    for numeric_column in ["unit_price", "cost"]:
        detailed[numeric_column] = pd.to_numeric(
            detailed[numeric_column], errors="coerce"
        ).fillna(0.0)

    detailed["margem_unitaria"] = detailed["unit_price"] - detailed["cost"]
    return detailed


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def load_history(history_csv: str, history_remote_url: str = "") -> pd.DataFrame:
    history_path = Path(history_csv)
    history = pd.DataFrame()

    if history_path.exists() and history_path.stat().st_size > 0:
        try:
            history = pd.read_csv(history_path, encoding="utf-8-sig")
        except Exception:
            history = pd.DataFrame()

    if history.empty and history_remote_url:
        try:
            history = pd.read_csv(history_remote_url)
        except Exception:
            history = pd.DataFrame()

    if history.empty:
        return pd.DataFrame()

    for column in HISTORY_COLUMNS:
        if column not in history.columns:
            history[column] = pd.NA

    history["run_datetime"] = pd.to_datetime(history["run_datetime"], errors="coerce")
    history["run_date"] = history["run_datetime"].dt.date

    for column in [
        "total",
        "ok",
        "partial_success",
        "not_confirmed",
        "error",
        "other_statuses",
        "critical_failures",
        "success_rate",
    ]:
        history[column] = pd.to_numeric(history[column], errors="coerce").fillna(0)

    for column in ["run_id", "run_url", "event_name", "actor", "github_run_id"]:
        history[column] = history[column].fillna("").astype(str)

    return history


def normalize_date_range(
    period: tuple[date, date] | list[date] | date,
    min_date: date,
    max_date: date,
) -> tuple[date, date]:
    if isinstance(period, tuple):
        if len(period) == 2:
            return period[0], period[1]
        if len(period) == 1:
            return period[0], period[0]
    if isinstance(period, list):
        if len(period) == 2:
            return period[0], period[1]
        if len(period) == 1:
            return period[0], period[0]
    if isinstance(period, date):
        return period, period
    return min_date, max_date


def format_whole_number(value: float | int) -> str:
    return f"{value:,.0f}".replace(",", ".")


def build_sla_gauge(success_rate: float, target: float) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=float(success_rate),
            number={"suffix": "%"},
            delta={"reference": float(target), "relative": False},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#00A36C" if success_rate >= target else "#FF4B4B"},
                "steps": [
                    {"range": [0, 85], "color": "#ffe5e5"},
                    {"range": [85, target], "color": "#fff5cc"},
                    {"range": [target, 100], "color": "#e6f7ef"},
                ],
                "threshold": {
                    "line": {"color": "#222", "width": 2},
                    "thickness": 0.75,
                    "value": float(target),
                },
            },
            title={"text": "Success SLA"},
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
    st.caption("Executive, operational, and quality monitoring for registration automation.")

    if "auto_refresh" not in st.session_state:
        st.session_state.auto_refresh = False

    data_source = "logs"
    data = load_reports(str(LOG_DIR))
    loaded_legacy_report_name = False
    if not data.empty:
        loaded_legacy_report_name = data["source_file"].str.contains(
            r"^relatorio_cadastro_", regex=True, na=False
        ).any()

    if data.empty:
        data = load_cloud_detailed_data(str(DETAILED_DASHBOARD_CSV), DETAILED_REMOTE_URL)
        if not data.empty:
            data_source = "analytics"
    history = load_history(str(HISTORY_CSV), HISTORY_REMOTE_URL)

    if data.empty and history.empty:
        st.info(
            "No data available. Run automation first to generate `logs/` and `analytics/history_runs.csv`."
        )
        return

    if data_source == "analytics":
        st.info(
            "Detailed data loaded from consolidated history in `analytics/detailed_runs.csv` "
            "(cloud mode without local `logs/`)."
        )
    elif loaded_legacy_report_name:
        st.info(
            "Legacy local report names (`relatorio_cadastro_*.csv`) were detected and loaded. "
            "Current executions generate `registration_report_*.csv`."
        )

    date_chunks = []
    if not data.empty:
        date_chunks.append(data["run_date"].dropna())
    if not history.empty:
        date_chunks.append(history["run_date"].dropna())

    valid_dates = pd.concat(date_chunks) if date_chunks else pd.Series(dtype="object")
    if valid_dates.empty:
        min_date = max_date = date.today()
    else:
        min_date = valid_dates.min()
        max_date = valid_dates.max()

    available_brands = sorted(brand for brand in (data["brand"].unique() if not data.empty else []) if brand)
    available_events = sorted(
        event for event in (history["event_name"].unique() if not history.empty else []) if event
    )

    with st.sidebar:
        st.header("Refresh")
        st.caption(f"Cache TTL: ~{CACHE_TTL_SECONDS}s")
        if st.button("🔄 Refresh now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.session_state.auto_refresh = st.toggle(
            f"Auto-refresh ({CACHE_TTL_SECONDS}s)",
            value=st.session_state.auto_refresh,
        )

        st.divider()
        st.header("Global filters")
        period = st.date_input(
            "Period",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        search_term = st.text_input("Search by code/brand", value="").strip()
        selected_brands = st.multiselect("Brands", options=available_brands, default=[])
        selected_events = st.multiselect(
            "Event type (history)", options=available_events, default=[]
        )
        sla_target = st.slider("Success target (%)", min_value=80, max_value=100, value=97)

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

    start_date, end_date = normalize_date_range(period, min_date, max_date)

    detailed = pd.DataFrame()
    if not data.empty:
        detailed = data[(data["run_date"] >= start_date) & (data["run_date"] <= end_date)].copy()
        if selected_brands:
            detailed = detailed[detailed["brand"].isin(selected_brands)]
        if search_term:
            mask = detailed["product_code"].str.contains(search_term, case=False, na=False) | detailed[
                "brand"
            ].str.contains(search_term, case=False, na=False)
            detailed = detailed[mask]

    filtered_history = pd.DataFrame()
    if not history.empty:
        filtered_history = history[
            (history["run_date"] >= start_date) & (history["run_date"] <= end_date)
        ].copy()
        if selected_events:
            filtered_history = filtered_history[filtered_history["event_name"].isin(selected_events)]

    if detailed.empty and filtered_history.empty:
        st.warning("No data for the selected filters.")
        return

    # -----------------------------
    # Executive KPIs
    # -----------------------------
    if not filtered_history.empty:
        total_runs = int(filtered_history["run_id"].nunique())
        total_records = int(filtered_history["total"].sum())
        total_ok = int(filtered_history["ok"].sum())
        critical_failures = int(filtered_history["critical_failures"].sum())
        success_rate = (total_ok / total_records * 100) if total_records else 0.0
        latest_run = filtered_history["run_datetime"].max()
    else:
        total_runs = int(detailed["run_id"].nunique()) if not detailed.empty else 0
        total_records = int(len(detailed))
        total_ok = int((detailed["execution_status"] == "ok").sum()) if not detailed.empty else 0
        critical_failures = (
            int(detailed["execution_status"].isin(["error", "not_confirmed"]).sum())
            if not detailed.empty
            else 0
        )
        success_rate = (total_ok / total_records * 100) if total_records else 0.0
        latest_run = detailed["run_datetime"].max() if not detailed.empty else pd.NaT

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Runs", format_whole_number(total_runs))
    col2.metric("Records", format_whole_number(total_records))
    col3.metric("Success", f"{success_rate:.2f}%")
    col4.metric("Critical failures", format_whole_number(critical_failures))
    col5.metric("Latest run", "-" if pd.isna(latest_run) else str(latest_run)[:16])

    st.plotly_chart(build_sla_gauge(success_rate, sla_target), use_container_width=True)

    # -----------------------------
    # Row 1 - trends and composition
    # -----------------------------
    if not filtered_history.empty:
        trend_base = filtered_history.sort_values("run_datetime").copy()
        trend_base["success_rate_calc"] = pd.to_numeric(
            trend_base["success_rate"], errors="coerce"
        ).fillna(0)
        trend_base["failures"] = pd.to_numeric(
            trend_base["critical_failures"], errors="coerce"
        ).fillna(0)
    else:
        trend_base = (
            detailed.groupby(["run_id", "run_datetime"], dropna=False)
            .agg(
                total=("execution_status", "size"),
                ok=("execution_status", lambda values: int((values == "ok").sum())),
                failures=(
                    "execution_status",
                    lambda values: int(values.isin(["error", "not_confirmed"]).sum()),
                ),
            )
            .reset_index()
            .sort_values("run_datetime")
        )
        trend_base["success_rate_calc"] = (
            trend_base["ok"] / trend_base["total"] * 100
        ).fillna(0)

    if not detailed.empty:
        status_counts = (
            detailed.groupby("execution_status", dropna=False)
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        )
    elif not filtered_history.empty:
        status_counts = pd.DataFrame(
            {
                "execution_status": ["ok", "partial_success", "not_confirmed", "error"],
                "count": [
                    int(filtered_history["ok"].sum()),
                    int(filtered_history["partial_success"].sum()),
                    int(filtered_history["not_confirmed"].sum()),
                    int(filtered_history["error"].sum()),
                ],
            }
        )
        status_counts = status_counts[status_counts["count"] > 0]
    else:
        status_counts = pd.DataFrame(columns=["execution_status", "count"])

    if not status_counts.empty:
        status_counts["execution_status"] = pd.Categorical(
            status_counts["execution_status"], categories=STATUS_ORDER, ordered=True
        )
        status_counts = status_counts.sort_values("execution_status")

    trend_fig = px.line(
        trend_base,
        x="run_datetime",
        y="success_rate_calc",
        markers=True,
        hover_data={"run_id": True, "total": True, "ok": True, "failures": True},
        title="Success trend by run",
    )
    trend_fig.update_layout(yaxis_title="Success (%)", xaxis_title="Run", yaxis_range=[0, 100])

    status_fig = px.pie(
        status_counts,
        names="execution_status",
        values="count",
        title="Status composition",
        hole=0.5,
    )

    row1_col1, row1_col2 = st.columns((2, 1))
    row1_col1.plotly_chart(trend_fig, use_container_width=True)
    row1_col2.plotly_chart(status_fig, use_container_width=True)

    # -----------------------------
    # Row 2 - efficiency by dimension
    # -----------------------------
    if not detailed.empty:
        by_brand = (
            detailed.groupby("brand", dropna=False)
            .agg(
                total=("execution_status", "size"),
                ok=("execution_status", lambda values: int((values == "ok").sum())),
                failures=(
                    "execution_status",
                    lambda values: int(values.isin(["error", "not_confirmed"]).sum()),
                ),
                average_margin=("margem_unitaria", "mean"),
            )
            .reset_index()
        )
        by_brand["success_rate"] = (by_brand["ok"] / by_brand["total"] * 100).fillna(0)
        by_brand = by_brand.sort_values("total", ascending=False).head(12)

        brand_fig = px.bar(
            by_brand,
            x="brand",
            y="success_rate",
            color="total",
            text_auto=".1f",
            title="Efficiency by brand (Top 12 by volume)",
        )
        brand_fig.update_layout(yaxis_title="Success (%)", xaxis_title="Brand")

        heat_data = (
            detailed.assign(status_fallback=detailed["execution_status"].replace("", "no_status"))
            .groupby(["category", "status_fallback"], dropna=False)
            .size()
            .reset_index(name="count")
        )
        heatmap_fig = px.density_heatmap(
            heat_data,
            x="status_fallback",
            y="category",
            z="count",
            color_continuous_scale="Blues",
            title="Heatmap category x status",
        )

        row2_col1, row2_col2 = st.columns(2)
        row2_col1.plotly_chart(brand_fig, use_container_width=True)
        row2_col2.plotly_chart(heatmap_fig, use_container_width=True)

    # -----------------------------
    # Management tables
    # -----------------------------
    st.subheader("🧾 Consolidated run history")
    if filtered_history.empty:
        st.info("No consolidated history for current filters.")
    else:
        history_view = filtered_history[
            [
                "run_datetime",
                "run_id",
                "total",
                "ok",
                "partial_success",
                "not_confirmed",
                "error",
                "critical_failures",
                "success_rate",
                "event_name",
                "actor",
                "run_url",
            ]
        ].sort_values("run_datetime", ascending=False)
        st.dataframe(history_view, use_container_width=True, hide_index=True)

    st.subheader("🚨 Failure investigation queue")
    if detailed.empty:
        st.info("No local detailed base available for investigation under current filters.")
    else:
        failures = (
            detailed[detailed["execution_status"].isin(["error", "not_confirmed", "partial_success"])][
                [
                    "run_datetime",
                    "run_id",
                    "row_index",
                    "product_code",
                    "brand",
                    "product_type",
                    "category",
                    "execution_status",
                    "detail",
                    "source_file",
                ]
            ]
            .sort_values(["run_datetime", "row_index"], ascending=[False, True])
            .reset_index(drop=True)
        )
        if failures.empty:
            st.success("No critical/partial failures found for selected filters.")
        else:
            st.dataframe(failures, use_container_width=True, hide_index=True)

    st.subheader("📦 Filtered detailed dataset")
    if detailed.empty:
        st.info("No detailed records for current filters.")
    else:
        detailed_view = detailed.sort_values(
            ["run_datetime", "row_index"], ascending=[False, True]
        ).reset_index(drop=True)
        st.dataframe(detailed_view, use_container_width=True, hide_index=True)

        csv_filename = f"dashboard_detailed_{datetime.now():%Y%m%d_%H%M%S}.csv"
        st.download_button(
            label="⬇️ Download filtered detailed dataset",
            data=detailed_view.to_csv(index=False, encoding="utf-8-sig"),
            file_name=csv_filename,
            mime="text/csv",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
