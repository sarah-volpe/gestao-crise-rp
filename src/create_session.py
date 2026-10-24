"""Abre o login do X e salva uma sessão local do Playwright.

AVISO: o X costuma detectar e bloquear o login feito dentro de um navegador
controlado por automação (mensagem "Limitamos temporariamente seu acesso"),
mesmo com você digitando a senha manualmente. Se isso acontecer, use
`session_from_cookies.py` em vez deste script: você loga uma vez num
navegador comum e importa os cookies de lá.

Depois de gerar o arquivo, aponte `coleta.storage_state_path` no
config.yaml para ele. O arquivo contém cookies de sessão — nunca versione.
"""

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    ap = argparse.ArgumentParser(description="Login manual no X para gerar storage_state do Playwright.")
    ap.add_argument("--output", default="storage_state.json")
    args = ap.parse_args()

    output_path = Path(args.output)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(locale="pt-BR", viewport={"width": 1366, "height": 900})
        page = context.new_page()
        page.goto("https://x.com/login", wait_until="domcontentloaded", timeout=60000)

        print("Faça login no X na janela do navegador.")
        print("Depois que a home ou busca carregar, volte aqui e pressione Enter.")
        input()

        context.storage_state(path=str(output_path))
        browser.close()

    print(f"Sessão salva em: {output_path}")


if __name__ == "__main__":
    main()
