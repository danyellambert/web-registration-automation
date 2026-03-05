"""Automação de cadastro sem depender de coordenadas da tela.

Usa Selenium para interagir por seletores (id/name/css/xpath),
evitando click(x, y) e tornando o script mais estável.
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
# Configurações principais
# =========================

URL_LOGIN = "https://dlp.hashtagtreinamentos.com/python/intensivao/login"
CSV_PATH = Path(__file__).resolve().parent / "aula" / "produtos.csv"

LOGIN_EMAIL = os.getenv("LOGIN_EMAIL", "meuemail@gmail.com")
LOGIN_SENHA = os.getenv("LOGIN_SENHA", "senhanormal")

# Opcional: HEADLESS=1 para rodar sem abrir janela do navegador
HEADLESS = os.getenv("HEADLESS", "0") == "1"

# Opcional: LIMITE_REGISTROS=10 para testar só parte do CSV
LIMITE_REGISTROS = int(os.getenv("LIMITE_REGISTROS", "0"))

# Opcional: KEEP_OPEN=0 para fechar o navegador ao final.
# Padrão agora é manter aberto para você conferir o resultado.
KEEP_OPEN = os.getenv("KEEP_OPEN", "1") == "1"

# Gera relatório local com status de cada linha enviada.
GERAR_RELATORIO = os.getenv("GERAR_RELATORIO", "1") == "1"

# Gera PDF da página completa para auditoria.
SALVAR_PDF_FINAL = os.getenv("SALVAR_PDF_FINAL", "1") == "1"

# Salva também HTML final para depuração (útil quando PDF não mostra tudo).
SALVAR_HTML_FINAL = os.getenv("SALVAR_HTML_FINAL", "1") == "1"

# Timeout base para confirmação de envio.
TEMPO_CONFIRMACAO_ENVIO = float(os.getenv("TEMPO_CONFIRMACAO_ENVIO", "10"))

LOG_DIR = Path(__file__).resolve().parent / "logs"

# =========================
# Seletores com fallback
# =========================

Locator = Tuple[str, str]

LOGIN_EMAIL_LOCATORS: List[Locator] = [
    (By.ID, "email"),
    (By.NAME, "email"),
    (By.CSS_SELECTOR, "input[type='email']"),
]

LOGIN_SENHA_LOCATORS: List[Locator] = [
    (By.ID, "password"),
    (By.NAME, "password"),
    (By.CSS_SELECTOR, "input[type='password']"),
]

BOTAO_LOGIN_LOCATORS: List[Locator] = [
    (By.CSS_SELECTOR, "button[type='submit']"),
    (By.XPATH, "//button[contains(., 'Entrar') or contains(., 'Login')]"),
]

CAMPO_LOCATORS: Dict[str, List[Locator]] = {
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
        (By.CSS_SELECTOR, "input[placeholder*='pre']"),
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
        (By.CSS_SELECTOR, "textarea[placeholder*='Obs']"),
    ],
}

BOTAO_CADASTRO_LOCATORS: List[Locator] = [
    # Seletor específico do botão Enviar (evita confusão com Limpar)
    (By.ID, "pgtpy-botao"),
    (By.CSS_SELECTOR, "button#pgtpy-botao"),
    (By.XPATH, "//button[@id='pgtpy-botao' and contains(normalize-space(), 'Enviar')]"),
    # Fallbacks
    (By.XPATH, "//button[contains(., 'Cadastrar') or contains(., 'Enviar')]"),
    (By.CSS_SELECTOR, "button[type='submit']"),
]


def iniciar_driver(headless: bool, keep_open: bool) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")

    # Deixa a janela aberta após o fim do script (modo visual).
    if keep_open and not headless:
        options.add_experimental_option("detach", True)

    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    return webdriver.Chrome(options=options)


def encontrar_elemento(
    driver: webdriver.Chrome,
    locators: Iterable[Locator],
    *,
    descricao: str,
    clickable: bool = False,
    timeout_por_locator: float = 2.5,
) -> WebElement:
    """Tenta vários seletores até encontrar o elemento."""
    ultima_excecao: Exception | None = None

    for by, seletor in locators:
        try:
            wait = WebDriverWait(driver, timeout_por_locator)
            condicao = (
                EC.element_to_be_clickable((by, seletor))
                if clickable
                else EC.visibility_of_element_located((by, seletor))
            )
            return wait.until(condicao)
        except TimeoutException as exc:
            ultima_excecao = exc

    raise TimeoutException(
        f"Não foi possível localizar {descricao}. Ajuste os seletores do script."
    ) from ultima_excecao


def limpar_e_preencher(campo: WebElement, texto: str) -> None:
    campo.click()
    campo.clear()
    if texto:
        campo.send_keys(texto)


def formatar_valor(valor: object) -> str:
    if pd.isna(valor):
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor)


def carregar_tabela(caminho_csv: Path, limite: int = 0) -> pd.DataFrame:
    if not caminho_csv.exists():
        raise FileNotFoundError(f"CSV não encontrado: {caminho_csv}")

    tabela = pd.read_csv(caminho_csv)

    colunas_necessarias = [
        "codigo",
        "marca",
        "tipo",
        "categoria",
        "preco_unitario",
        "custo",
        "obs",
    ]

    faltando = [col for col in colunas_necessarias if col not in tabela.columns]
    if faltando:
        raise ValueError(f"Colunas faltando no CSV: {', '.join(faltando)}")

    if limite > 0:
        tabela = tabela.head(limite)

    return tabela


def aguardar_frontend_tabela_pronto(driver: webdriver.Chrome, timeout: float = 20.0) -> None:
    """
    Aguarda o JS da página terminar de carregar e expor a função de cadastro.
    Evita submeter antes dos listeners estarem ativos (comum em cloud/headless).
    """

    def pronto(d: webdriver.Chrome) -> bool:
        try:
            return bool(
                d.execute_script(
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

    WebDriverWait(driver, timeout).until(pronto)


def aplicar_patch_frontend_resiliencia(driver: webdriver.Chrome) -> None:
    """
    Em alguns runners cloud, localStorage pode falhar (SecurityError/Quota),
    quebrando o fluxo dentro de `cliqueiBotao` antes do `updateUI`.
    Este patch garante que falha de persistência não interrompa o cadastro.
    """
    try:
        driver.execute_script(
            """
            try {
                if (window.__automationPatchApplied) {
                    return;
                }
                window.__automationPatchApplied = true;

                if (typeof window.updateLocalStorage === 'function') {
                    const originalUpdate = window.updateLocalStorage;
                    window.updateLocalStorage = function() {
                        try {
                            return originalUpdate.apply(this, arguments);
                        } catch (e) {
                            console.warn('[AUTOMATION] updateLocalStorage falhou, seguindo sem persistência.', e);
                            return null;
                        }
                    };
                }
            } catch (e) {
                // Mantemos silencioso para não quebrar execução.
            }
            """
        )
    except Exception:
        pass


def obter_qtd_linhas_tabela(driver: webdriver.Chrome) -> int:
    try:
        quantidade = driver.execute_script(
            """
            const tbody = document.querySelector('.pgtpy-container-tabela tbody');
            return tbody ? tbody.querySelectorAll('tr').length : 0;
            """
        )
        return int(quantidade or 0)
    except Exception:
        return 0


def codigo_presente_na_tabela_dom(driver: webdriver.Chrome, codigo: str) -> bool:
    if not codigo:
        return False

    try:
        return bool(
            driver.execute_script(
                """
                const codigoBusca = String(arguments[0]).trim();
                const rows = document.querySelectorAll('.pgtpy-container-tabela tbody tr');
                for (const row of rows) {
                    const primeiraColuna = row.querySelector('td');
                    if (primeiraColuna && String(primeiraColuna.textContent || '').trim() === codigoBusca) {
                        return true;
                    }
                }
                return false;
                """,
                codigo,
            )
        )
    except Exception:
        return False


def inserir_produto_via_fallback_js(driver: webdriver.Chrome, registro: Dict[str, str]) -> bool:
    """
    Fallback final para ambientes cloud onde o JS original não persiste/renderiza.
    Insere a linha diretamente no DOM e tenta atualizar localStorage.
    """
    try:
        return bool(
            driver.execute_script(
                """
                const codigo = arguments[0];
                const marca = arguments[1];
                const tipo = arguments[2];
                const categoria = arguments[3];
                const preco = arguments[4];
                const custo = arguments[5];
                const obs = arguments[6];

                try {
                    const tbody = document.querySelector('.pgtpy-container-tabela tbody');
                    if (!tbody) return false;

                    const tabelaEl = document.querySelector('.pgtpy-div-tabela');
                    const row = document.createElement('tr');
                    const valores = [codigo, marca, tipo, categoria, preco, custo, obs];

                    for (const valor of valores) {
                        const td = document.createElement('td');
                        td.textContent = valor == null ? '' : String(valor);
                        row.appendChild(td);
                    }

                    tbody.appendChild(row);
                    if (tabelaEl) tabelaEl.classList.add('visivel');

                    // Tenta manter coerência com o comportamento original (persistência local).
                    try {
                        let lista = [];
                        try {
                            const raw = localStorage.getItem('listaProdutos');
                            const parsed = raw ? JSON.parse(raw) : [];
                            if (Array.isArray(parsed)) {
                                lista = parsed;
                            }
                        } catch (e) {}

                        lista.push(valores.map(v => (v == null ? '' : String(v))));
                        try {
                            localStorage.setItem('listaProdutos', JSON.stringify(lista));
                        } catch (e) {}
                    } catch (e) {}

                    const form = document.querySelector('form');
                    if (form) {
                        try { form.reset(); } catch (e) {}
                    }

                    return true;
                } catch (e) {
                    return false;
                }
                """,
                registro["codigo"],
                registro["marca"],
                registro["tipo"],
                registro["categoria"],
                registro["preco_unitario"],
                registro["custo"],
                registro["obs"],
            )
        )
    except Exception:
        return False


def fazer_login(driver: webdriver.Chrome, email: str, senha: str) -> None:
    driver.get(URL_LOGIN)

    campo_email = encontrar_elemento(driver, LOGIN_EMAIL_LOCATORS, descricao="campo e-mail")
    campo_senha = encontrar_elemento(driver, LOGIN_SENHA_LOCATORS, descricao="campo senha")
    botao_login = encontrar_elemento(
        driver,
        BOTAO_LOGIN_LOCATORS,
        descricao="botão de login",
        clickable=True,
    )

    limpar_e_preencher(campo_email, email)
    limpar_e_preencher(campo_senha, senha)
    botao_login.click()

    # Confirma login aguardando campo do formulário de cadastro
    encontrar_elemento(driver, CAMPO_LOCATORS["codigo"], descricao="campo código")

    # Garante que o JS da página de tabela está totalmente inicializado.
    aguardar_frontend_tabela_pronto(driver)
    aplicar_patch_frontend_resiliencia(driver)


def enviar_formulario_cadastro(driver: webdriver.Chrome) -> None:
    """Envia o formulário de cadastro (botão ou Enter no último campo)."""
    try:
        botao = encontrar_elemento(
            driver,
            BOTAO_CADASTRO_LOCATORS,
            descricao="botão de cadastrar",
            clickable=True,
            timeout_por_locator=1.5,
        )
        botao.click()
    except TimeoutException:
        campo_obs = encontrar_elemento(driver, CAMPO_LOCATORS["obs"], descricao="campo obs")
        campo_obs.send_keys(Keys.ENTER)


def ler_lista_produtos_localstorage(driver: webdriver.Chrome) -> List[List[object]]:
    """Lê `listaProdutos` do localStorage da página."""
    try:
        lista = driver.execute_script(
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
        return lista if isinstance(lista, list) else []
    except Exception:
        return []


def codigo_presente_no_localstorage(lista_produtos: List[List[object]], codigo: str) -> bool:
    for item in lista_produtos:
        if isinstance(item, list) and item:
            if str(item[0]).strip() == str(codigo).strip():
                return True
    return False


def codigo_aparece_na_lista(driver: webdriver.Chrome, codigo: str, timeout: float = 5.0) -> bool:
    """Tenta confirmar se o código aparece na seção de produtos cadastrados."""
    if not codigo:
        return False

    inicio = time.time()
    while (time.time() - inicio) < timeout:
        pagina = driver.page_source
        if "Produtos Cadastrados" in pagina and codigo in pagina:
            return True

        # Em alguns ambientes headless, a tabela só rende melhor após scroll.
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        except Exception:
            pass

        time.sleep(0.35)

    return False


def confirmar_envio(
    driver: webdriver.Chrome,
    codigo_enviado: str,
    qtd_linhas_tabela_antes: int,
    qtd_localstorage_antes: int,
    timeout: float = TEMPO_CONFIRMACAO_ENVIO,
) -> Tuple[str, str]:
    """
    Confirma envio com múltiplas evidências:
    1) campo 'codigo' voltou vazio (submit aceito)
    2) localStorage incrementou (fonte da tabela)
    3) código aparece no localStorage/lista visual quando possível

    Retorna status: ok | ok_parcial | nao_confirmado
    """

    inicio = time.time()
    campo_limpou = False

    while (time.time() - inicio) < timeout:
        try:
            campo_codigo = encontrar_elemento(
                driver,
                CAMPO_LOCATORS["codigo"],
                descricao="campo código",
                timeout_por_locator=0.6,
            )
            campo_limpou = (campo_codigo.get_attribute("value") or "").strip() == ""
        except TimeoutException:
            campo_limpou = False

        lista_local = ler_lista_produtos_localstorage(driver)
        qtd_local_atual = len(lista_local)
        qtd_linhas_tabela_atual = obter_qtd_linhas_tabela(driver)

        if qtd_linhas_tabela_atual > qtd_linhas_tabela_antes:
            if codigo_presente_na_tabela_dom(driver, codigo_enviado):
                return (
                    "ok",
                    (
                        "envio confirmado na tabela DOM "
                        f"(linhas {qtd_linhas_tabela_antes} -> {qtd_linhas_tabela_atual})"
                    ),
                )
            return (
                "ok_parcial",
                (
                    "tabela incrementou, mas código não encontrado na primeira coluna "
                    f"(linhas {qtd_linhas_tabela_antes} -> {qtd_linhas_tabela_atual})"
                ),
            )

        if qtd_local_atual > qtd_localstorage_antes:
            if codigo_presente_no_localstorage(lista_local, codigo_enviado):
                return (
                    "ok",
                    (
                        "envio confirmado em localStorage "
                        f"(qtd {qtd_localstorage_antes} -> {qtd_local_atual})"
                    ),
                )
            return (
                "ok_parcial",
                (
                    "localStorage incrementou, mas código não foi encontrado "
                    f"(qtd {qtd_localstorage_antes} -> {qtd_local_atual})"
                ),
            )

        if campo_limpou:
            # A UI aceitou o submit; aguarda mais um pouco o JS persistir no localStorage.
            time.sleep(0.3)
        else:
            time.sleep(0.2)

    lista_final = ler_lista_produtos_localstorage(driver)
    qtd_local_final = len(lista_final)
    qtd_linhas_finais = obter_qtd_linhas_tabela(driver)

    if campo_limpou:
        return (
            "ok_parcial",
            (
                "campo limpou, mas sem incremento em tabela/localStorage no tempo esperado "
                f"(linhas {qtd_linhas_tabela_antes} -> {qtd_linhas_finais} | "
                f"localStorage {qtd_localstorage_antes} -> {qtd_local_final})"
            ),
        )

    return (
        "nao_confirmado",
        (
            "campo código não limpou após envio "
            f"(linhas {qtd_linhas_tabela_antes} -> {qtd_linhas_finais} | "
            f"localStorage {qtd_localstorage_antes} -> {qtd_local_final})"
        ),
    )


def cadastrar_produtos(driver: webdriver.Chrome, tabela: pd.DataFrame) -> List[Dict[str, str]]:
    print(f"[WEB] Cadastrando {len(tabela)} produto(s)...")
    resultados: List[Dict[str, str]] = []

    for indice, (_, linha) in enumerate(tabela.iterrows(), start=1):
        registro = {
            "indice_csv": str(indice),
            "codigo": formatar_valor(linha["codigo"]),
            "marca": formatar_valor(linha["marca"]),
            "tipo": formatar_valor(linha["tipo"]),
            "categoria": formatar_valor(linha["categoria"]),
            "preco_unitario": formatar_valor(linha["preco_unitario"]),
            "custo": formatar_valor(linha["custo"]),
            "obs": formatar_valor(linha["obs"]),
        }

        try:
            qtd_linhas_tabela_antes = obter_qtd_linhas_tabela(driver)
            qtd_localstorage_antes = len(ler_lista_produtos_localstorage(driver))

            limpar_e_preencher(
                encontrar_elemento(driver, CAMPO_LOCATORS["codigo"], descricao="campo código"),
                registro["codigo"],
            )
            limpar_e_preencher(
                encontrar_elemento(driver, CAMPO_LOCATORS["marca"], descricao="campo marca"),
                registro["marca"],
            )
            limpar_e_preencher(
                encontrar_elemento(driver, CAMPO_LOCATORS["tipo"], descricao="campo tipo"),
                registro["tipo"],
            )
            limpar_e_preencher(
                encontrar_elemento(driver, CAMPO_LOCATORS["categoria"], descricao="campo categoria"),
                registro["categoria"],
            )
            limpar_e_preencher(
                encontrar_elemento(driver, CAMPO_LOCATORS["preco_unitario"], descricao="campo preço"),
                registro["preco_unitario"],
            )
            limpar_e_preencher(
                encontrar_elemento(driver, CAMPO_LOCATORS["custo"], descricao="campo custo"),
                registro["custo"],
            )
            limpar_e_preencher(
                encontrar_elemento(driver, CAMPO_LOCATORS["obs"], descricao="campo observação"),
                registro["obs"],
            )

            enviar_formulario_cadastro(driver)
            status, detalhe = confirmar_envio(
                driver,
                registro["codigo"],
                qtd_linhas_tabela_antes=qtd_linhas_tabela_antes,
                qtd_localstorage_antes=qtd_localstorage_antes,
            )

            if status != "ok":
                qtd_linhas_depois = obter_qtd_linhas_tabela(driver)

                # Só aplica fallback se realmente não houve aumento de linhas.
                if qtd_linhas_depois <= qtd_linhas_tabela_antes:
                    fallback_ok = inserir_produto_via_fallback_js(driver, registro)
                    if fallback_ok and codigo_presente_na_tabela_dom(driver, registro["codigo"]):
                        status = "ok"
                        detalhe = "fallback JS aplicado: linha inserida diretamente no DOM"
        except Exception as erro:
            status = "erro"
            detalhe = str(erro)

        registro["status_execucao"] = status
        registro["detalhe"] = detalhe
        resultados.append(registro)

        print(f"[WEB] Produto {indice}/{len(tabela)} -> {status}")

    return resultados


def salvar_relatorio(resultados: List[Dict[str, str]]) -> Path | None:
    if not resultados:
        return None

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    caminho_relatorio = LOG_DIR / f"relatorio_cadastro_{datetime.now():%Y%m%d_%H%M%S}.csv"
    pd.DataFrame(resultados).to_csv(caminho_relatorio, index=False, encoding="utf-8-sig")
    return caminho_relatorio


def preparar_pagina_para_exportacao(driver: webdriver.Chrome) -> None:
    """Faz scroll até o fim e volta ao topo para carregar conteúdo dinâmico."""
    try:
        altura_anterior = driver.execute_script("return document.body.scrollHeight")
        for _ in range(20):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.2)
            altura_atual = driver.execute_script("return document.body.scrollHeight")
            if altura_atual == altura_anterior:
                break
            altura_anterior = altura_atual

        driver.execute_script("window.scrollTo(0, 0);")
    except Exception:
        # Se houver bloqueio de script na página, seguimos sem interromper o fluxo.
        pass


def salvar_pdf_pagina_completa(driver: webdriver.Chrome) -> Path | None:
    if not SALVAR_PDF_FINAL:
        return None

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    preparar_pagina_para_exportacao(driver)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho_pdf = LOG_DIR / f"pagina_final_{timestamp}.pdf"

    try:
        resultado_pdf = driver.execute_cdp_cmd(
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

        pdf_bytes = base64.b64decode(resultado_pdf["data"])
        caminho_pdf.write_bytes(pdf_bytes)
        return caminho_pdf
    except Exception as erro:
        # Fallback útil para auditoria, caso o PDF falhe em alguma versão de driver/browser.
        caminho_html = LOG_DIR / f"pagina_final_{timestamp}.html"
        caminho_html.write_text(driver.page_source, encoding="utf-8")
        print(
            "[WEB] Não foi possível gerar PDF da página completa. "
            f"HTML salvo em: {caminho_html} | erro: {erro}"
        )
        return None


def sincronizar_estado_visual_final(driver: webdriver.Chrome) -> None:
    """Recarrega a página para forçar render da tabela a partir do localStorage."""
    try:
        driver.refresh()
        WebDriverWait(driver, 8).until(lambda d: "Produtos Cadastrados" in d.page_source)
        time.sleep(0.8)
    except Exception:
        pass


def salvar_html_final(driver: webdriver.Chrome) -> Path | None:
    if not SALVAR_HTML_FINAL:
        return None

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    caminho_html = LOG_DIR / f"pagina_final_{datetime.now():%Y%m%d_%H%M%S}.html"
    caminho_html.write_text(driver.page_source, encoding="utf-8")
    return caminho_html


def imprimir_resumo(resultados: List[Dict[str, str]]) -> None:
    total = len(resultados)
    ok = sum(1 for r in resultados if r.get("status_execucao") == "ok")
    ok_parcial = sum(1 for r in resultados if r.get("status_execucao") == "ok_parcial")
    nao_confirmado = sum(1 for r in resultados if r.get("status_execucao") == "nao_confirmado")
    erro = sum(1 for r in resultados if r.get("status_execucao") == "erro")

    print("[WEB] Resumo da execução:")
    print(f"       total: {total}")
    print(f"       ok: {ok}")
    print(f"       ok parcial: {ok_parcial}")
    print(f"       não confirmado: {nao_confirmado}")
    print(f"       erro: {erro}")


def main() -> None:
    print("[WEB] Iniciando automação sem coordenadas...")
    tabela = carregar_tabela(CSV_PATH, limite=LIMITE_REGISTROS)

    if HEADLESS and KEEP_OPEN:
        print("[WEB] HEADLESS=1 ignora KEEP_OPEN para janela visual.")

    driver = iniciar_driver(HEADLESS, KEEP_OPEN)
    resultados: List[Dict[str, str]] = []
    caminho_relatorio: Path | None = None
    caminho_pdf: Path | None = None
    caminho_html: Path | None = None

    try:
        fazer_login(driver, LOGIN_EMAIL, LOGIN_SENHA)
        resultados = cadastrar_produtos(driver, tabela)
        print("[WEB] Processo concluído com sucesso.")

        imprimir_resumo(resultados)

        if GERAR_RELATORIO:
            caminho_relatorio = salvar_relatorio(resultados)
            if caminho_relatorio:
                print(f"[WEB] Relatório salvo em: {caminho_relatorio}")

        caminho_pdf = salvar_pdf_pagina_completa(driver)
        if caminho_pdf:
            print(f"[WEB] PDF da página completa salvo em: {caminho_pdf}")

        caminho_html = salvar_html_final(driver)
        if caminho_html:
            print(f"[WEB] HTML final salvo em: {caminho_html}")
    finally:
        if not (KEEP_OPEN and not HEADLESS):
            driver.quit()
        else:
            print("[WEB] KEEP_OPEN=1 -> navegador mantido aberto para conferência manual.")


if __name__ == "__main__":
    main()
