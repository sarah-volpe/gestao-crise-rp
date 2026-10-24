"""Login no X sem copiar cookies à mão: gera o storage_state.json sozinho.

Como funciona (e por que não é bloqueado):
  1. Abre o Chrome (ou o Edge) instalado no computador como um processo
     comum, num perfil separado só para a conta descartável (pasta
     .sessao_x/, fora do git). Não é o navegador do Playwright, então o X
     vê um navegador normal.
  2. Você faz o login normalmente. Nenhuma automação se conecta à página
     durante o login: o script só consulta, de fora, o endereço da aba
     aberta.
  3. Quando a aba chega na página inicial do X, o script se conecta, lê os
     cookies `auth_token` e `ct0` e grava o storage_state.json no mesmo
     formato do session_from_cookies.py.
  4. O perfil fica salvo. Quando a sessão expirar, rode de novo: se o perfil
     ainda estiver logado, a renovação é automática, sem digitar nada.

Uso:
  python src\\login_x.py
  python src\\login_x.py --navegador "C:\\caminho\\para\\chrome.exe"
  python src\\login_x.py --novo-perfil     # apaga o perfil e começa do zero (trocar de conta)

O storage_state.json e a pasta .sessao_x/ equivalem à senha da conta:
nunca compartilhe nem envie ao GitHub (já estão no .gitignore).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from session_from_cookies import build_storage_state  # noqa: E402

PERFIL = Path(".sessao_x")
SAIDA = Path("storage_state.json")
URL_LOGIN = "https://x.com/login"
URL_COOKIES = "https://x.com"


def achar_navegador() -> str | None:
    env = os.environ
    candidatos = [
        Path(env.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
        Path(env.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
        Path(env.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
        Path(env.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
        Path(env.get("PROGRAMFILES", r"C:\Program Files")) / "Microsoft/Edge/Application/msedge.exe",
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
    ]
    for c in candidatos:
        if str(c) and c.is_file():
            return str(c)
    for nome in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"):
        achado = shutil.which(nome)
        if achado:
            return achado
    return None


def porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def abas(porta: int) -> list[dict]:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{porta}/json/list", timeout=2) as r:
            return [a for a in json.load(r) if a.get("type") == "page"]
    except Exception:
        return []


def logado(url: str) -> bool:
    """Chegou numa página do X que não é login/cadastro/verificação."""
    if not url.startswith(("https://x.com/", "https://twitter.com/")):
        return False
    return not any(p in url for p in ("/login", "/i/flow", "/account/access", "/i/jf/", "/logout"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Login no X que gera o storage_state.json automaticamente.")
    ap.add_argument("--navegador", help="caminho do chrome.exe ou msedge.exe (detectado sozinho se omitido)")
    ap.add_argument("--novo-perfil", action="store_true", help="apaga o perfil salvo (para trocar de conta)")
    ap.add_argument("--espera-max", type=int, default=600, help="segundos para esperar o login (padrão 600)")
    ap.add_argument("--url", default=URL_LOGIN, help=argparse.SUPPRESS)  # usado nos testes
    ap.add_argument("--args-extra", default="", help=argparse.SUPPRESS)  # usado nos testes
    a = ap.parse_args()

    exe = a.navegador or achar_navegador()
    if not exe:
        sys.exit("Não achei o Chrome nem o Edge. Informe o caminho com --navegador \"C:\\...\\chrome.exe\".")
    if a.novo_perfil and PERFIL.exists():
        shutil.rmtree(PERFIL)
    PERFIL.mkdir(exist_ok=True)

    porta = porta_livre()
    proc = subprocess.Popen([
        exe, f"--remote-debugging-port={porta}", f"--user-data-dir={PERFIL.resolve()}",
        "--no-first-run", "--no-default-browser-check", "--new-window", *a.args_extra.split(), a.url,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("Abri o navegador numa janela separada.")
    print("Faça login no X com a CONTA DESCARTÁVEL. Quando a página inicial carregar, eu sigo sozinho.")
    print("(Se o perfil já estiver logado, não precisa fazer nada.)\n")

    inicio, chegou = time.time(), False
    try:
        while time.time() - inicio < a.espera_max:
            if proc.poll() is not None:
                sys.exit("O navegador foi fechado antes de terminar o login. Rode de novo.")
            if any(logado(t.get("url", "")) for t in abas(porta)):
                chegou = True
                break
            time.sleep(2)
        if not chegou:
            sys.exit(f"Passaram {a.espera_max // 60} minutos sem login. Rode de novo quando quiser.")

        time.sleep(3)  # deixa o X terminar de gravar os cookies da sessão
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{porta}")
            cookies = browser.contexts[0].cookies([URL_COOKIES]) if browser.contexts else []
        valores = {c["name"]: c["value"] for c in cookies if c["name"] in ("auth_token", "ct0")}
        if len(valores) < 2:
            sys.exit("A página abriu, mas não encontrei os cookies de sessão. Confira se o login terminou "
                     "e rode de novo.")
        SAIDA.write_text(json.dumps(build_storage_state(valores["auth_token"], valores["ct0"]), indent=2),
                         encoding="utf-8")
        print(f"Sessão salva em {SAIDA}. Pode seguir com a coleta.")
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    main()
