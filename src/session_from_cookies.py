"""Gera storage_state.json a partir de cookies copiados de um login manual.

`create_session.py` faz o login DENTRO do navegador automatizado do
Playwright — e o X detecta o Chromium controlado por automação (CDP) bem no
momento de login, bloqueando com "Limitamos temporariamente seu acesso"
mesmo sendo você digitando a senha de verdade.

Este script evita isso: você loga uma vez num navegador comum (Chrome/Edge
do dia a dia, sem Playwright), copia dois cookies da sessão já autenticada,
e eles viram o storage_state.json que o scraper usa. O Playwright nunca
participa do login em si, só da navegação/leitura depois.

Como pegar os cookies (Chrome/Edge):
  1. Faça login normalmente em x.com com a conta descartável.
  2. F12 -> aba "Application" (Chrome) ou "Aplicativo" (Edge) -> Cookies -> https://x.com
  3. Copie o "Value" de `auth_token` e de `ct0`.

Uso:
  python src\\session_from_cookies.py --auth-token SEU_VALOR --ct0 SEU_VALOR

O storage_state.json contém, em essência, a senha da conta em outro formato
— trate como segredo (já está no .gitignore) e nunca cole esses valores em
lugar público (chat, print, repositório).
"""

import argparse
import json
import time
from pathlib import Path


def build_storage_state(auth_token: str, ct0: str, expires_days: int = 180) -> dict:
    expires = time.time() + expires_days * 86400
    cookies = []
    for domain in (".x.com", ".twitter.com"):
        cookies.append({
            "name": "auth_token",
            "value": auth_token,
            "domain": domain,
            "path": "/",
            "expires": expires,
            "httpOnly": True,
            "secure": True,
            "sameSite": "None",
        })
        cookies.append({
            "name": "ct0",
            "value": ct0,
            "domain": domain,
            "path": "/",
            "expires": expires,
            "httpOnly": False,
            "secure": True,
            "sameSite": "Lax",
        })
    return {"cookies": cookies, "origins": []}


def main() -> None:
    ap = argparse.ArgumentParser(description="Monta storage_state.json a partir dos cookies auth_token e ct0.")
    ap.add_argument("--auth-token", required=True, help="valor do cookie auth_token")
    ap.add_argument("--ct0", required=True, help="valor do cookie ct0")
    ap.add_argument("--output", default="storage_state.json")
    ap.add_argument("--expires-days", type=int, default=180)
    args = ap.parse_args()

    state = build_storage_state(args.auth_token, args.ct0, args.expires_days)
    Path(args.output).write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"Sessão salva em: {args.output}")
    print("Valide com: python src\\collect_x_scrape.py --grupo marca_ampla --headed --debug-artifacts")


if __name__ == "__main__":
    main()
