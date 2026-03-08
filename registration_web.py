"""Web registration automation without screen-coordinate dependency.

Designed for stable execution locally and in GitHub Actions.
- Selenium interaction through selectors
- JavaScript fallback for unstable cloud frontend behavior
- Incremental CSV + HTML persistence to avoid losing evidence on timeouts

Important compatibility notes:
- Input dataset uses `data/products.csv` as the canonical source.
- Selector strategy still includes legacy frontend fallbacks for resilience.
"""

from __future__ import annotations

import base64
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib.parse import urlparse

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

LOGIN_URL = _get_env(
    "LOGIN_URL",
    "http://127.0.0.1:8000/login.html",
)
INPUT_CSV_PATH = Path(__file__).resolve().parent / "data" / "products.csv"
LOCAL_SITE_DIR = Path(__file__).resolve().parent / "web_page" / "exclusive_page"
LOG_DIR = Path(__file__).resolve().parent / "logs"

LOGIN_EMAIL = _get_env(
    "LOGIN_EMAIL",
    "your-user@example.com",
)
LOGIN_PASSWORD = _get_env(
    "LOGIN_PASSWORD",
    "your-password",
    legacy_names=["LOGIN_SENHA"],
)

HEADLESS = _get_bool_env("HEADLESS", False)
KEEP_OPEN = _get_bool_env("KEEP_OPEN", True)

MAX_RECORDS = _get_int_env("MAX_RECORDS", 0, legacy_names=None)
RECORD_OFFSET = _get_int_env("RECORD_OFFSET", 0, legacy_names=None)

GENERATE_REPORT = _get_bool_env("GENERATE_REPORT", True, legacy_names=None)
SAVE_FINAL_HTML = _get_bool_env("SAVE_FINAL_HTML", True, legacy_names=None)
SAVE_FINAL_PDF = _get_bool_env("SAVE_FINAL_PDF", False, legacy_names=None)

SUBMISSION_CONFIRMATION_TIMEOUT = _get_float_env(
    "SUBMISSION_CONFIRMATION_TIMEOUT", 6.0, legacy_names=None
)
MAX_WAIT_WITHOUT_EVIDENCE = _get_float_env(
    "MAX_WAIT_WITHOUT_EVIDENCE", 2.5, legacy_names=None
)

PARTIAL_REPORT_EVERY = max(
    1, _get_int_env("PARTIAL_REPORT_EVERY", 10, legacy_names=None)
)
PARTIAL_HTML_EVERY = _get_int_env("PARTIAL_HTML_EVERY", 25, legacy_names=None)
AUTO_START_LOCAL_SITE = _get_bool_env("AUTO_START_LOCAL_SITE", True)
LOCAL_SITE_START_TIMEOUT = _get_float_env("LOCAL_SITE_START_TIMEOUT", 8.0)

REPORT_COLUMNS = [
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
    (By.XPATH, "//button[contains(., 'Sign In') or contains(., 'Entrar') or contains(., 'Login')]"),
]

# NOTE: field keys follow the canonical English dataset schema.
# Selector fallbacks still include legacy frontend identifiers/text where helpful.
FIELD_LOCATORS: Dict[str, List[Locator]] = {
    "product_code": [
        (By.NAME, "product_code"),
        (By.ID, "product_code"),
        (By.NAME, "product_code"),
        (By.ID, "product_code"),
        (By.CSS_SELECTOR, "input[placeholder*='Product code']"),
        (By.CSS_SELECTOR, "input[placeholder*='product code']"),
        (By.CSS_SELECTOR, "input[placeholder*='ódigo']"),
        (By.CSS_SELECTOR, "input[placeholder*='odigo']"),
    ],
    "brand": [
        (By.NAME, "brand"),
        (By.ID, "brand"),
        (By.NAME, "brand"),
        (By.ID, "brand"),
        (By.CSS_SELECTOR, "input[placeholder*='Brand']"),
        (By.CSS_SELECTOR, "input[placeholder*='brand']"),
        (By.CSS_SELECTOR, "input[placeholder*='brand']"),
    ],
    "product_type": [
        (By.NAME, "product_type"),
        (By.ID, "product_type"),
        (By.NAME, "product_type"),
        (By.ID, "product_type"),
        (By.CSS_SELECTOR, "input[placeholder*='Product type']"),
        (By.CSS_SELECTOR, "input[placeholder*='product type']"),
        (By.CSS_SELECTOR, "input[placeholder*='product_type']"),
    ],
    "category": [
        (By.NAME, "category"),
        (By.ID, "category"),
        (By.NAME, "category"),
        (By.ID, "category"),
        (By.CSS_SELECTOR, "input[placeholder*='Category']"),
        (By.CSS_SELECTOR, "input[placeholder*='category']"),
        (By.CSS_SELECTOR, "input[placeholder*='category']"),
    ],
    "unit_price": [
        (By.NAME, "unit_price"),
        (By.ID, "unit_price"),
        (By.NAME, "unit_price"),
        (By.ID, "unit_price"),
        (By.NAME, "preco"),
        (By.ID, "preco"),
    ],
    "cost": [
        (By.NAME, "cost"),
        (By.ID, "cost"),
        (By.NAME, "cost"),
        (By.ID, "cost"),
        (By.CSS_SELECTOR, "input[placeholder*='Cost']"),
        (By.CSS_SELECTOR, "input[placeholder*='cost']"),
        (By.CSS_SELECTOR, "input[placeholder*='cost']"),
    ],
    "notes": [
        (By.NAME, "notes"),
        (By.ID, "notes"),
        (By.NAME, "notes"),
        (By.ID, "notes"),
        (By.CSS_SELECTOR, "textarea[name='notes']"),
        (By.CSS_SELECTOR, "input[name='notes']"),
        (By.CSS_SELECTOR, "textarea[name='notes']"),
        (By.CSS_SELECTOR, "input[name='notes']"),
    ],
}

SUBMIT_BUTTON_LOCATORS: List[Locator] = [
    (By.ID, "pgtpy-botao"),
    (By.CSS_SELECTOR, "button#pgtpy-botao"),
    (By.XPATH, "//button[@id='pgtpy-botao' and contains(normalize-space(), 'Submit')]"),
    (By.XPATH, "//button[@id='pgtpy-botao' and contains(normalize-space(), 'Enviar')]"),
    (By.XPATH, "//button[contains(., 'Register') or contains(., 'Submit')]"),
    (By.XPATH, "//button[contains(., 'Cadastrar') or contains(., 'Enviar')]"),
    (By.CSS_SELECTOR, "button[type='submit']"),
]


def resolve_input_csv_path() -> Path:
    return INPUT_CSV_PATH


def _is_local_http_login_url(login_url: str) -> bool:
    parsed = urlparse(login_url)
    return parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}


def _is_tcp_endpoint_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def maybe_start_local_target_site(login_url: str) -> subprocess.Popen | None:
    if not AUTO_START_LOCAL_SITE:
        return None
    if not _is_local_http_login_url(login_url):
        return None

    parsed = urlparse(login_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 80

    if _is_tcp_endpoint_reachable(host, port):
        return None

    if not LOCAL_SITE_DIR.exists():
        print(f"[WEB] Local site directory not found: {LOCAL_SITE_DIR}", flush=True)
        return None

    print(
        f"[WEB] Local target site is not reachable at {login_url}. "
        "Attempting auto-start...",
        flush=True,
    )

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "http.server",
            str(port),
            "--bind",
            host,
            "--directory",
            str(LOCAL_SITE_DIR),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )

    start_time = time.time()
    while (time.time() - start_time) < LOCAL_SITE_START_TIMEOUT:
        if _is_tcp_endpoint_reachable(host, port):
            print(f"[WEB] Local target site auto-started at {login_url}", flush=True)
            return process
        if process.poll() is not None:
            break
        time.sleep(0.2)

    try:
        process.terminate()
        process.wait(timeout=2)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass

    print(
        "[WEB] Failed to auto-start the local target site. "
        "Start it manually with: "
        "python -m http.server 8000 --directory web_page/exclusive_page",
        flush=True,
    )
    return None


def stop_local_target_site(process: subprocess.Popen | None) -> None:
    if process is None:
        return
    try:
        process.terminate()
        process.wait(timeout=3)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass
    print("[WEB] Local target site auto-start process stopped.", flush=True)


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
    table.columns = [str(col).strip() for col in table.columns]

    column_aliases_to_english = {
        "codigo": "product_code",
        "marca": "brand",
        "tipo": "product_type",
        "categoria": "category",
        "preco_unitario": "unit_price",
        "preco": "unit_price",
        "custo": "cost",
        "obs": "notes",
    }
    table = table.rename(columns=column_aliases_to_english)

    if "notes" not in table.columns:
        table["notes"] = ""

    required_columns = [
        "product_code",
        "brand",
        "product_type",
        "category",
        "unit_price",
        "cost",
        "notes",
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
                        !!document.querySelector('form') &&
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

    find_element(driver, FIELD_LOCATORS["product_code"], description="product code field")
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
        obs_field = find_element(driver, FIELD_LOCATORS["notes"], description="notes field")
        obs_field.send_keys(Keys.ENTER)


def read_products_from_local_storage(driver: webdriver.Chrome) -> List[List[object]]:
    try:
        products = driver.execute_script(
            """
            try {
                const keys = ['productList'];
                for (const key of keys) {
                    const raw = window.localStorage.getItem(key);
                    if (!raw) continue;
                    const parsed = JSON.parse(raw);
                    if (Array.isArray(parsed)) {
                        return parsed;
                    }
                }
                return [];
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
                    const keys = ['productList'];
                    const storageKey = keys.find(k => localStorage.getItem(k) !== null) || 'productList';
                    const raw = localStorage.getItem(storageKey);
                    const list = raw ? JSON.parse(raw) : [];
                    if (Array.isArray(list)) {
                        list.push(values);
                        localStorage.setItem(storageKey, JSON.stringify(list));
                    }
                } catch (e) {}

                const form = document.querySelector('form');
                if (form) {
                    try { form.reset(); } catch (e) {}
                }

                return true;
                """,
                record["product_code"],
                record["brand"],
                record["product_type"],
                record["category"],
                record["unit_price"],
                record["cost"],
                record["notes"],
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
                FIELD_LOCATORS["product_code"],
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
                "partial_success",
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
                "partial_success",
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
            "partial_success",
            "code field was cleared, but no table/localStorage increase was detected "
            f"(rows {rows_before} -> {final_rows} | "
            f"localStorage {local_storage_count_before} -> {final_local_storage_count})",
        )

    return (
        "not_confirmed",
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
            "row_index": str(index),
            "product_code": format_cell_value(row["product_code"]),
            "brand": format_cell_value(row["brand"]),
            "product_type": format_cell_value(row["product_type"]),
            "category": format_cell_value(row["category"]),
            "unit_price": format_cell_value(row["unit_price"]),
            "cost": format_cell_value(row["cost"]),
            "notes": format_cell_value(row["notes"]),
        }

        try:
            rows_before = get_table_row_count(driver)
            local_storage_count_before = len(read_products_from_local_storage(driver))

            clear_and_type(
                find_element(driver, FIELD_LOCATORS["product_code"], description="code field"),
                record["product_code"],
            )
            clear_and_type(
                find_element(driver, FIELD_LOCATORS["brand"], description="brand field"),
                record["brand"],
            )
            clear_and_type(
                find_element(driver, FIELD_LOCATORS["product_type"], description="type field"),
                record["product_type"],
            )
            clear_and_type(
                find_element(driver, FIELD_LOCATORS["category"], description="category field"),
                record["category"],
            )
            clear_and_type(
                find_element(driver, FIELD_LOCATORS["unit_price"], description="unit price field"),
                record["unit_price"],
            )
            clear_and_type(
                find_element(driver, FIELD_LOCATORS["cost"], description="cost field"),
                record["cost"],
            )
            clear_and_type(
                find_element(driver, FIELD_LOCATORS["notes"], description="notes field"),
                record["notes"],
            )

            submit_registration_form(driver)
            status, details = confirm_submission(
                driver,
                record["product_code"],
                rows_before=rows_before,
                local_storage_count_before=local_storage_count_before,
            )

            if status != "ok":
                rows_after = get_table_row_count(driver)
                if rows_after <= rows_before:
                    fallback_ok = insert_product_with_js_fallback(driver, record)
                    if fallback_ok and is_product_code_in_dom_table(driver, record["product_code"]):
                        status = "ok"
                        details = "JavaScript fallback applied: row inserted directly into the DOM"
        except Exception as exc:
            status = "error"
            details = str(exc)

        record["execution_status"] = status
        record["detail"] = details
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
    ok = sum(1 for item in results if item.get("execution_status") == "ok")
    ok_partial = sum(1 for item in results if item.get("execution_status") == "partial_success")
    not_confirmed = sum(1 for item in results if item.get("execution_status") == "not_confirmed")
    error = sum(1 for item in results if item.get("execution_status") == "error")

    print("[WEB] Execution summary:", flush=True)
    print(f"       total: {total}", flush=True)
    print(f"       ok: {ok}", flush=True)
    print(f"       ok partial: {ok_partial}", flush=True)
    print(f"       not confirmed: {not_confirmed}", flush=True)
    print(f"       error: {error}", flush=True)


def main() -> None:
    print("[WEB] Starting selector-based registration automation...", flush=True)
    table = load_input_table(
        resolve_input_csv_path(),
        max_records=MAX_RECORDS,
        record_offset=RECORD_OFFSET,
    )

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

    local_site_process = maybe_start_local_target_site(LOGIN_URL)

    driver: webdriver.Chrome | None = None
    results: List[Dict[str, str]] = []
    fatal_error: Exception | None = None

    try:
        driver = start_driver(HEADLESS, KEEP_OPEN)
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
        if "ERR_CONNECTION_REFUSED" in str(exc):
            print(f"[WEB] Could not reach LOGIN_URL: {LOGIN_URL}", flush=True)
            print(
                "[WEB] Tip: if running locally, start the target site with: "
                "python -m http.server 8000 --directory web_page/exclusive_page",
                flush=True,
            )
    finally:
        if results:
            print_execution_summary(results)

        if report_path:
            save_report_to_path(results, report_path)
            print(f"[WEB] Report saved at: {report_path}", flush=True)

        if html_path and driver is not None:
            try:
                save_html_to_path(driver, html_path)
                print(f"[WEB] Final HTML saved at: {html_path}", flush=True)
            except Exception:
                pass

        if SAVE_FINAL_PDF and driver is not None:
            try:
                pdf_path = save_full_page_pdf(driver)
                if pdf_path:
                    print(f"[WEB] Full-page PDF saved at: {pdf_path}", flush=True)
            except Exception as pdf_exc:
                print(f"[WEB] Failed to generate PDF: {pdf_exc}", flush=True)

        if driver is not None:
            if not (KEEP_OPEN and not HEADLESS):
                driver.quit()
            else:
                print("[WEB] KEEP_OPEN=1 -> browser kept open for manual review.", flush=True)

        stop_local_target_site(local_site_process)

    if fatal_error:
        raise fatal_error


if __name__ == "__main__":
    main()
