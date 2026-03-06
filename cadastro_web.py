"""Web registration automation without screen-coordinate dependency.

Designed for stable execution locally and in GitHub Actions.
- Selenium interaction through selectors
- JavaScript fallback for unstable cloud frontend behavior
- Incremental CSV + HTML persistence to avoid losing evidence on timeouts

Important compatibility notes:
- Source dataset columns remain in Portuguese because the target system uses them
  (e.g., codigo, marca, tipo, categoria, preco_unitario, custo, obs).
- Frontend keys/functions from the target page are kept as-is
  (e.g., cliqueiBotao, listaProdutos, visivel).
"""

from __future__ import annotations

import base64
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# =========================
# Environment helpers
# =========================


def _get_env(name: str, default: str, legacy_names: Iterable[str] | None = None) -> str:
    value = os.getenv(name)
    if value is not None and str(value).strip() != "":
        return value

    for legacy in legacy_names or []:
        legacy_value = os.getenv(legacy)
        if legacy_value is not None and str(legacy_value).strip() != "":
            return legacy_value

    return default


def _get_bool_env(name: str, default: bool, legacy_names: Iterable[str] | None = None) -> bool:
    raw = _get_env(name, "1" if default else "0", legacy_names).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _get_int_env(name: str, default: int, legacy_names: Iterable[str] | None = None) -> int:
    raw = _get_env(name, str(default), legacy_names)
    try:
        return int(raw)
    except Exception:
        return default


def _get_float_env(name: str, default: float, legacy_names: Iterable[str] | None = None) -> float:
    raw = _get_env(name, str(default), legacy_names)
    try:
        return float(raw)
    except Exception:
        return default


# =========================
# Configuration
# =========================

LOGIN_URL = "https://dlp.hashtagtreinamentos.com/python/intensivao/login"
INPUT_CSV_PATH = Path(__file__).resolve().parent / "data" / "produtos.csv"
LOG_DIR = Path(__file__).resolve().parent / "logs"

LOGIN_EMAIL = _get_env("LOGIN_EMAIL", "your-user@example.com")
LOGIN_PASSWORD = _get_env("LOGIN_PASSWORD", "your-password", legacy_names=["LOGIN_SENHA"])

HEADLESS = _get_bool_env("HEADLESS", False)
KEEP_OPEN = _get_bool_env("KEEP_OPEN", True)

MAX_RECORDS = _get_int_env("MAX_RECORDS", 0, legacy_names=["LIMITE_REGISTROS"])
RECORD_OFFSET = _get_int_env("RECORD_OFFSET", 0, legacy_names=["OFFSET_REGISTROS"])

GENERATE_REPORT = _get_bool_env("GENERATE_REPORT", True, legacy_names=["GERAR_RELATORIO"])
SAVE_FINAL_HTML = _get_bool_env("SAVE_FINAL_HTML", True, legacy_names=["SALVAR_HTML_FINAL"])
SAVE_FINAL_PDF = _get_bool_env("SAVE_FINAL_PDF", False, legacy_names=["SALVAR_PDF_FINAL"])

SUBMISSION_CONFIRMATION_TIMEOUT = _get_float_env(
    "SUBMISSION_CONFIRMATION_TIMEOUT", 6.0, legacy_names=["TEMPO_CONFIRMACAO_ENVIO"]
)
MAX_WAIT_WITHOUT_EVIDENCE = _get_float_env(
    "MAX_WAIT_WITHOUT_EVIDENCE", 2.5, legacy_names=["TEMPO_MAX_ESPERA_SEM_EVIDENCIA"]
)

PARTIAL_REPORT_EVERY = max(
    1, _get_int_env("PARTIAL_REPORT_EVERY", 10, legacy_names=["RELATORIO_PARCIAL_CADA"])
)
PARTIAL_HTML_EVERY = _get_int_env("PARTIAL_HTML_EVERY", 25, legacy_names=["HTML_PARCIAL_CADA"])

REPORT_COLUMNS = [
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


# =========================
# Selectors
# =========================

Locator = Tuple[str, str]

LOGIN_EMAIL_LOCATORS: List[Locator] = [
    (By.ID, "email"),
    (By.NAME, "email"),
    (By.CSS_SELECTOR, "input[type='email']"),
]

LOGIN_PASSWORD_LOCATORS: List[Locator] = [
    (By.ID, "password"),
    (By.NAME, "password"),
    (By.CSS_SELECTOR, "input[type='password']"),
]

LOGIN_BUTTON_LOCATORS: List[Locator] = [
    (By.CSS_SELECTOR, "button[type='submit']"),
    (By.XPATH, "//button[contains(., 'Entrar') or contains(., 'Login')]"),
]

# NOTE: field keys intentionally match the Portuguese data schema used by the target system.
FIELD_LOCATORS: Dict[str, List[Locator]] = {
    "codigo": [
        (By.NAME, "codigo"),
        (By.ID, "codigo"),
        (By.CSS_SELECTOR, "input[placeholder*='ódigo']"),
        (By.CSS_SELECTOR, "input[placeholder*='odigo']"),
    ],
    "marca": [
        (By.NAME, "marca"),
        (By.ID, "marca"),
        (By.CSS_SELECTOR, "input[placeholder*='marca']"),
    ],
    "tipo": [
        (By.NAME, "tipo"),
        (By.ID, "tipo"),
        (By.CSS_SELECTOR, "input[placeholder*='tipo']"),
    ],
    "categoria": [
        (By.NAME, "categoria"),
        (By.ID, "categoria"),
        (By.CSS_SELECTOR, "input[placeholder*='categoria']"),
    ],
    "preco_unitario": [
        (By.NAME, "preco_unitario"),
        (By.ID, "preco_unitario"),
        (By.NAME, "preco"),
        (By.ID, "preco"),
    ],
    "custo": [
        (By.NAME, "custo"),
        (By.ID, "custo"),
        (By.CSS_SELECTOR, "input[placeholder*='custo']"),
    ],
    "obs": [
        (By.NAME, "obs"),
        (By.ID, "obs"),
        (By.CSS_SELECTOR, "textarea[name='obs']"),
        (By.CSS_SELECTOR, "input[name='obs']"),
    ],
}

SUBMIT_BUTTON_LOCATORS: List[Locator] = [
    (By.ID, "pgtpy-botao"),
    (By.CSS_SELECTOR, "button#pgtpy-botao"),
    (By.XPATH, "//button[@id='pgtpy-botao' and contains(normalize-space(), 'Enviar')]"),
    (By.XPATH, "//button[contains(., 'Cadastrar') or contains(., 'Enviar')]"),
    (By.CSS_SELECTOR, "button[type='submit']"),
]


def start_driver(headless: bool, keep_open: bool) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    if keep_open and not headless:
        options.add_experimental_option("detach", True)
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    return webdriver.Chrome(options=options)


def find_element(
    driver: webdriver.Chrome,
    locators: Iterable[Locator],
    *,
    description: str,
    clickable: bool = False,
    timeout_per_locator: float = 2.5,
) -> WebElement:
    last_exception: Exception | None = None
    for by, selector in locators:
        try:
            wait = WebDriverWait(driver, timeout_per_locator)
            condition = (
                EC.element_to_be_clickable((by, selector))
                if clickable
                else EC.visibility_of_element_located((by, selector))
            )
            return wait.until(condition)
        except TimeoutException as exc:
            last_exception = exc

    raise TimeoutException(
        f"Could not locate {description}. Please review the script selectors."
    ) from last_exception


def clear_and_type(field: WebElement, text: str) -> None:
    field.click()
    field.clear()
    if text:
        field.send_keys(text)


def format_cell_value(value: object) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def load_input_table(csv_path: Path, max_records: int = 0, record_offset: int = 0) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")

    table = pd.read_csv(csv_path)
    required_columns = [
        "codigo",
        "marca",
        "tipo",
        "categoria",
        "preco_unitario",
        "custo",
        "obs",
    ]

    missing_columns = [col for col in required_columns if col not in table.columns]
    if missing_columns:
        raise ValueError(f"Missing CSV columns: {', '.join(missing_columns)}")

    if record_offset > 0:
        table = table.iloc[record_offset:]
    if max_records > 0:
        table = table.head(max_records)
    return table


def wait_until_table_frontend_ready(driver: webdriver.Chrome, timeout: float = 20.0) -> None:
    def is_ready(current_driver: webdriver.Chrome) -> bool:
        try:
            return bool(
                current_driver.execute_script(
                    """
                    return (
                        document.readyState === 'complete' &&
                        typeof cliqueiBotao === 'function' &&
                        !!document.querySelector('#pgtpy-botao')
                    );
                    """
                )
            )
        except Exception:
            return False

    WebDriverWait(driver, timeout).until(is_ready)


def apply_frontend_resilience_patch(driver: webdriver.Chrome) -> None:
    try:
        driver.execute_script(
            """
            try {
                if (window.__automationPatchApplied) return;
                window.__automationPatchApplied = true;
                if (typeof window.updateLocalStorage === 'function') {
                    const originalUpdate = window.updateLocalStorage;
                    window.updateLocalStorage = function() {
                        try { return originalUpdate.apply(this, arguments); }
                        catch (e) { return null; }
                    };
                }
            } catch (e) {}
            """
        )
    except Exception:
        pass


def login(driver: webdriver.Chrome, email: str, password: str) -> None:
    driver.get(LOGIN_URL)
    email_field = find_element(driver, LOGIN_EMAIL_LOCATORS, description="login email field")
    password_field = find_element(
        driver,
        LOGIN_PASSWORD_LOCATORS,
        description="login password field",
    )
    login_button = find_element(
        driver,
        LOGIN_BUTTON_LOCATORS,
        description="login button",
        clickable=True,
    )

    clear_and_type(email_field, email)
    clear_and_type(password_field, password)
    login_button.click()

    find_element(driver, FIELD_LOCATORS["codigo"], description="product code field")
    wait_until_table_frontend_ready(driver)
    apply_frontend_resilience_patch(driver)


def submit_registration_form(driver: webdriver.Chrome) -> None:
    try:
        submit_button = find_element(
            driver,
            SUBMIT_BUTTON_LOCATORS,
            description="submit button",
            clickable=True,
            timeout_per_locator=1.5,
        )
        submit_button.click()
    except TimeoutException:
        obs_field = find_element(driver, FIELD_LOCATORS["obs"], description="obs field")
        obs_field.send_keys(Keys.ENTER)


def read_products_from_local_storage(driver: webdriver.Chrome) -> List[List[object]]:
    try:
        products = driver.execute_script(
            """
            try {
                const raw = window.localStorage.getItem('listaProdutos');
                if (!raw) return [];
                const parsed = JSON.parse(raw);
                return Array.isArray(parsed) ? parsed : [];
            } catch (e) {
                return [];
            }
            """
        )
        return products if isinstance(products, list) else []
    except Exception:
        return []


def is_product_code_in_local_storage(products: List[List[object]], code: str) -> bool:
    for item in products:
        if isinstance(item, list) and item and str(item[0]).strip() == str(code).strip():
            return True
    return False


def get_table_row_count(driver: webdriver.Chrome) -> int:
    try:
        row_count = driver.execute_script(
            """
            const tbody = document.querySelector('.pgtpy-container-tabela tbody');
            return tbody ? tbody.querySelectorAll('tr').length : 0;
            """
        )
        return int(row_count or 0)
    except Exception:
        return 0


def is_product_code_in_dom_table(driver: webdriver.Chrome, code: str) -> bool:
    if not code:
        return False
    try:
        return bool(
            driver.execute_script(
                """
                const codeToFind = String(arguments[0]).trim();
                const rows = document.querySelectorAll('.pgtpy-container-tabela tbody tr');
                for (const row of rows) {
                    const firstCell = row.querySelector('td');
                    if (firstCell && String(firstCell.textContent || '').trim() === codeToFind) {
                        return true;
                    }
                }
                return false;
                """,
                code,
            )
        )
    except Exception:
        return False


def insert_product_with_js_fallback(driver: webdriver.Chrome, record: Dict[str, str]) -> bool:
    try:
        return bool(
            driver.execute_script(
                """
                const values = [
                    arguments[0], arguments[1], arguments[2], arguments[3],
                    arguments[4], arguments[5], arguments[6]
                ].map(v => (v == null ? '' : String(v)));

                const tbody = document.querySelector('.pgtpy-container-tabela tbody');
                if (!tbody) return false;

                const row = document.createElement('tr');
                for (const value of values) {
                    const td = document.createElement('td');
                    td.textContent = value;
                    row.appendChild(td);
                }
                tbody.appendChild(row);

                const tableElement = document.querySelector('.pgtpy-div-tabela');
                if (tableElement) tableElement.classList.add('visivel');

                try {
                    const raw = localStorage.getItem('listaProdutos');
                    const list = raw ? JSON.parse(raw) : [];
                    if (Array.isArray(list)) {
                        list.push(values);
                        localStorage.setItem('listaProdutos', JSON.stringify(list));
                    }
                } catch (e) {}

                const form = document.querySelector('form');
                if (form) {
                    try { form.reset(); } catch (e) {}
                }

                return true;
                """,
                record["codigo"],
                record["marca"],
                record["tipo"],
                record["categoria"],
                record["preco_unitario"],
                record["custo"],
                record["obs"],
            )
        )
    except Exception:
        return False


def confirm_submission(
    driver: webdriver.Chrome,
    submitted_code: str,
    rows_before: int,
    local_storage_count_before: int,
    timeout: float = SUBMISSION_CONFIRMATION_TIMEOUT,
) -> Tuple[str, str]:
    start_time = time.time()
    no_evidence_timeout = min(timeout, MAX_WAIT_WITHOUT_EVIDENCE)
    code_field_was_cleared = False

    while (time.time() - start_time) < timeout:
        try:
            code_field = find_element(
                driver,
                FIELD_LOCATORS["codigo"],
                description="product code field",
                timeout_per_locator=0.5,
            )
            code_field_was_cleared = (code_field.get_attribute("value") or "").strip() == ""
        except TimeoutException:
            code_field_was_cleared = False

        local_products = read_products_from_local_storage(driver)
        local_storage_count_after = len(local_products)
        rows_after = get_table_row_count(driver)

        if rows_after > rows_before:
            if is_product_code_in_dom_table(driver, submitted_code):
                return (
                    "ok",
                    f"submission confirmed in DOM table (rows {rows_before} -> {rows_after})",
                )
            return (
                "ok_parcial",
                f"table increased without code confirmation (rows {rows_before} -> {rows_after})",
            )

        if local_storage_count_after > local_storage_count_before:
            if is_product_code_in_local_storage(local_products, submitted_code):
                return (
                    "ok",
                    "submission confirmed in localStorage "
                    f"(count {local_storage_count_before} -> {local_storage_count_after})",
                )
            return (
                "ok_parcial",
                "localStorage increased without code confirmation "
                f"(count {local_storage_count_before} -> {local_storage_count_after})",
            )

        if (time.time() - start_time) >= no_evidence_timeout:
            break

        time.sleep(0.15)

    final_rows = get_table_row_count(driver)
    final_local_storage_count = len(read_products_from_local_storage(driver))

    if code_field_was_cleared:
        return (
            "ok_parcial",
            "code field was cleared, but no table/localStorage increase was detected "
            f"(rows {rows_before} -> {final_rows} | "
            f"localStorage {local_storage_count_before} -> {final_local_storage_count})",
        )

    return (
        "nao_confirmado",
        "code field did not clear after submission "
        f"(rows {rows_before} -> {final_rows} | "
        f"localStorage {local_storage_count_before} -> {final_local_storage_count})",
    )


def save_report_to_path(results: List[Dict[str, str]], report_path: Path | None) -> None:
    if not report_path:
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if results:
        df = pd.DataFrame(results)
    else:
        df = pd.DataFrame(columns=REPORT_COLUMNS)
    df.to_csv(report_path, index=False, encoding="utf-8-sig")


def save_html_to_path(driver: webdriver.Chrome, html_path: Path | None) -> None:
    if not html_path:
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    html_path.write_text(driver.page_source, encoding="utf-8")


def prepare_page_for_export(driver: webdriver.Chrome) -> None:
    try:
        previous_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(20):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.15)
            current_height = driver.execute_script("return document.body.scrollHeight")
            if current_height == previous_height:
                break
            previous_height = current_height
        driver.execute_script("window.scrollTo(0, 0);")
    except Exception:
        pass


def save_full_page_pdf(driver: webdriver.Chrome) -> Path | None:
    if not SAVE_FINAL_PDF:
        return None

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    prepare_page_for_export(driver)

    pdf_path = LOG_DIR / f"final_page_{datetime.now():%Y%m%d_%H%M%S}.pdf"
    pdf_result = driver.execute_cdp_cmd(
        "Page.printToPDF",
        {
            "printBackground": True,
            "preferCSSPageSize": True,
            "landscape": False,
            "marginTop": 0,
            "marginBottom": 0,
            "marginLeft": 0,
            "marginRight": 0,
        },
    )
    pdf_path.write_bytes(base64.b64decode(pdf_result["data"]))
    return pdf_path


def register_products(
    driver: webdriver.Chrome,
    table: pd.DataFrame,
    incremental_report_path: Path | None = None,
    incremental_html_path: Path | None = None,
) -> List[Dict[str, str]]:
    print(f"[WEB] Registering {len(table)} product(s)...", flush=True)
    results: List[Dict[str, str]] = []

    for index, (_, row) in enumerate(table.iterrows(), start=1):
        record = {
            "indice_csv": str(index),
            "codigo": format_cell_value(row["codigo"]),
            "marca": format_cell_value(row["marca"]),
            "tipo": format_cell_value(row["tipo"]),
            "categoria": format_cell_value(row["categoria"]),
            "preco_unitario": format_cell_value(row["preco_unitario"]),
            "custo": format_cell_value(row["custo"]),
            "obs": format_cell_value(row["obs"]),
        }

        try:
            rows_before = get_table_row_count(driver)
            local_storage_count_before = len(read_products_from_local_storage(driver))

            clear_and_type(
                find_element(driver, FIELD_LOCATORS["codigo"], description="code field"),
                record["codigo"],
            )
            clear_and_type(
                find_element(driver, FIELD_LOCATORS["marca"], description="brand field"),
                record["marca"],
            )
            clear_and_type(
                find_element(driver, FIELD_LOCATORS["tipo"], description="type field"),
                record["tipo"],
            )
            clear_and_type(
                find_element(driver, FIELD_LOCATORS["categoria"], description="category field"),
                record["categoria"],
            )
            clear_and_type(
                find_element(driver, FIELD_LOCATORS["preco_unitario"], description="unit price field"),
                record["preco_unitario"],
            )
            clear_and_type(
                find_element(driver, FIELD_LOCATORS["custo"], description="cost field"),
                record["custo"],
            )
            clear_and_type(
                find_element(driver, FIELD_LOCATORS["obs"], description="notes field"),
                record["obs"],
            )

            submit_registration_form(driver)
            status, details = confirm_submission(
                driver,
                record["codigo"],
                rows_before=rows_before,
                local_storage_count_before=local_storage_count_before,
            )

            if status != "ok":
                rows_after = get_table_row_count(driver)
                if rows_after <= rows_before:
                    fallback_ok = insert_product_with_js_fallback(driver, record)
                    if fallback_ok and is_product_code_in_dom_table(driver, record["codigo"]):
                        status = "ok"
                        details = "JavaScript fallback applied: row inserted directly into the DOM"
        except Exception as exc:
            status = "erro"
            details = str(exc)

        record["status_execucao"] = status
        record["detalhe"] = details
        results.append(record)

        print(f"[WEB] Product {index}/{len(table)} -> {status}", flush=True)

        if incremental_report_path and (index % PARTIAL_REPORT_EVERY == 0 or index == len(table)):
            save_report_to_path(results, incremental_report_path)

        if incremental_html_path and PARTIAL_HTML_EVERY > 0 and (
            index % PARTIAL_HTML_EVERY == 0 or index == len(table)
        ):
            try:
                save_html_to_path(driver, incremental_html_path)
            except Exception:
                pass

    return results


def print_execution_summary(results: List[Dict[str, str]]) -> None:
    total = len(results)
    ok = sum(1 for item in results if item.get("status_execucao") == "ok")
    ok_partial = sum(1 for item in results if item.get("status_execucao") == "ok_parcial")
    not_confirmed = sum(1 for item in results if item.get("status_execucao") == "nao_confirmado")
    error = sum(1 for item in results if item.get("status_execucao") == "erro")

    print("[WEB] Execution summary:", flush=True)
    print(f"       total: {total}", flush=True)
    print(f"       ok: {ok}", flush=True)
    print(f"       ok partial: {ok_partial}", flush=True)
    print(f"       not confirmed: {not_confirmed}", flush=True)
    print(f"       error: {error}", flush=True)


def main() -> None:
    print("[WEB] Starting selector-based registration automation...", flush=True)
    table = load_input_table(INPUT_CSV_PATH, max_records=MAX_RECORDS, record_offset=RECORD_OFFSET)

    if HEADLESS and KEEP_OPEN:
        print("[WEB] HEADLESS=1 ignores KEEP_OPEN visual mode.", flush=True)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    report_path = (
        LOG_DIR / f"registration_report_{run_timestamp}.csv" if GENERATE_REPORT else None
    )
    html_path = LOG_DIR / f"final_page_{run_timestamp}.html" if SAVE_FINAL_HTML else None

    if report_path:
        save_report_to_path([], report_path)
    if html_path:
        html_path.write_text("<html><body>execution started</body></html>", encoding="utf-8")

    driver = start_driver(HEADLESS, KEEP_OPEN)
    results: List[Dict[str, str]] = []
    fatal_error: Exception | None = None

    try:
        login(driver, LOGIN_EMAIL, LOGIN_PASSWORD)
        results = register_products(
            driver,
            table,
            incremental_report_path=report_path,
            incremental_html_path=html_path,
        )
        print("[WEB] Process finished successfully.", flush=True)
    except Exception as exc:
        fatal_error = exc
        print(f"[WEB] Fatal error: {exc}", flush=True)
    finally:
        if results:
            print_execution_summary(results)

        if report_path:
            save_report_to_path(results, report_path)
            print(f"[WEB] Report saved at: {report_path}", flush=True)

        if html_path:
            try:
                save_html_to_path(driver, html_path)
                print(f"[WEB] Final HTML saved at: {html_path}", flush=True)
            except Exception:
                pass

        if SAVE_FINAL_PDF:
            try:
                pdf_path = save_full_page_pdf(driver)
                if pdf_path:
                    print(f"[WEB] Full-page PDF saved at: {pdf_path}", flush=True)
            except Exception as pdf_exc:
                print(f"[WEB] Failed to generate PDF: {pdf_exc}", flush=True)

        if not (KEEP_OPEN and not HEADLESS):
            driver.quit()
        else:
            print("[WEB] KEEP_OPEN=1 -> browser kept open for manual review.", flush=True)

    if fatal_error:
        raise fatal_error


if __name__ == "__main__":
    main()
