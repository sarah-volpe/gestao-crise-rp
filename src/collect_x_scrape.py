"""Coleta no X via scraping da busca pública com Playwright.

Alternativa ao twscrape (`collect_twscrape.py`): não loga em nenhuma conta
contra a API interna do X, então não carrega o mesmo risco de ToS e
banimento de conta. Em troca, só enxerga o que a página pública de busca
renderiza no DOM — mais lento, mais sensível a mudanças de HTML do X, e sem
garantia de recall completo (não pagina além do que o scroll carrega, e
alguns campos como seguidores do autor não aparecem no card do resultado de
busca). Ver README, seção "Leia antes de rodar".

Reaproveita a mesma matriz de queries (`queries.py`, `since:`/`until:`
embutidos no texto da query) e o mesmo checkpoint resumível do
`collect_twscrape.py`: os dois coletores escrevem para o mesmo
`data/raw/*.jsonl` e alimentam o mesmo `normalize.py`. Troque o coletor
usado em `coleta.metodo` no config (`scrape` | `twscrape`).

O HTML e os atributos `data-testid`/`aria-label` usados aqui foram
adaptados do protótipo em sarah_tcc/functions/collect_x_data/x_scraper.py.
O X muda esse markup sem aviso — valide com `--debug-artifacts` antes de
confiar cegamente nos números extraídos (curtidas, reposts etc.) em uma
coleta real.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from queries import Query, build_queries  # noqa: E402
import paths  # noqa: E402

STATUS_RE = re.compile(r"^/([^/]+)/status/(\d+)")
COUNT_RE = re.compile(
    r"([\d.,]+)\s*([KkMm]?)\s*"
    r"(repl(?:y|ies)|respostas?|repost|retweets?|reposts?|quotes?|"
    r"cita[cç][oõ]es?|likes?|curtidas?|bookmarks?|views?|visualiza[cç][oõ]es?)",
    re.IGNORECASE,
)
COUNT_FIELD = {
    "reply": "replies", "replies": "replies", "respostas": "replies", "resposta": "replies",
    "repost": "retweets", "retweets": "retweets", "retweet": "retweets",
    "reposts": "retweets",
    "quotes": "quotes", "quote": "quotes",
    "citacoes": "quotes", "citações": "quotes", "citacao": "quotes", "citação": "quotes",
    "likes": "likes", "like": "likes", "curtidas": "likes", "curtida": "likes",
    "bookmarks": "bookmarks", "bookmark": "bookmarks",
    "views": "views", "view": "views",
    "visualizacoes": "views", "visualizações": "views", "visualizacao": "views",
}
LOGIN_MARKERS = [
    "continuar com telefone", "continue with google", "e-mail ou nome de utilizador",
    "entrar", "log in", "sign in",
]

# Esconde os sinais mais comuns que sites usam para detectar Chromium
# controlado por automação (Playwright/Puppeteer). Reduz falsos positivos de
# antifraude durante a coleta, mas não neutraliza detecção mais sofisticada
# (fingerprint de TLS, análise comportamental) — não é garantia contra bloqueio.
_STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
window.chrome = window.chrome || { runtime: {} };
const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
if (originalQuery) {
  window.navigator.permissions.query = (params) =>
    params.name === 'notifications'
      ? Promise.resolve({ state: Notification.permission })
      : originalQuery(params);
}
"""

_EXTRACT_JS = r"""
() => Array.from(document.querySelectorAll('article[data-testid="tweet"]')).map((article) => {
  const timeEl = article.querySelector('time');
  const statusAnchor = timeEl ? timeEl.closest('a[href*="/status/"]') : null;
  const nameBlock = article.querySelector('div[data-testid="User-Name"]');
  const userLink = nameBlock ? nameBlock.querySelector('a[role="link"][href^="/"]') : null;
  const handleLink = nameBlock ? nameBlock.querySelector('a[href^="/"] span') : null;
  const tweetTextEl = article.querySelector('div[data-testid="tweetText"]');
  const group = article.querySelector('div[role="group"]');
  const socialContext = article.querySelector('div[data-testid="socialContext"]');
  const statusHrefs = [...new Set(
    Array.from(article.querySelectorAll('a[href*="/status/"]')).map(a => {
      const m = a.getAttribute('href').match(/^(\/[^/]+\/status\/\d+)/);
      return m ? m[1] : a.getAttribute('href');
    })
  )];
  const hashtags = tweetTextEl
    ? Array.from(tweetTextEl.querySelectorAll('a[href^="/hashtag/"]')).map(a => a.textContent.trim())
    : [];
  return {
    status_href: statusAnchor ? statusAnchor.getAttribute('href') : (statusHrefs[0] || null),
    all_status_hrefs: statusHrefs,
    created_at: timeEl ? timeEl.getAttribute('datetime') : null,
    author_name: nameBlock && nameBlock.querySelector('span') ? nameBlock.querySelector('span').textContent : null,
    verified: !!article.querySelector('svg[data-testid="icon-verified"]'),
    text: tweetTextEl ? tweetTextEl.innerText : '',
    lang: tweetTextEl ? tweetTextEl.getAttribute('lang') : null,
    group_aria: group ? group.getAttribute('aria-label') : null,
    social_context: socialContext ? socialContext.innerText : null,
    reply_context: /Respondendo a|Replying to/.test(article.innerText),
    hashtags,
  };
})
"""


def build_search_url(query_texto: str) -> str:
    return f"https://x.com/search?q={quote(query_texto)}&src=typed_query&f=live"


def _parse_counts(aria_label: str | None) -> dict[str, int]:
    metrics = {"replies": 0, "retweets": 0, "quotes": 0, "likes": 0, "bookmarks": 0, "views": 0}
    if not aria_label:
        return metrics
    for value, suffix, label in COUNT_RE.findall(aria_label):
        field = COUNT_FIELD.get(label.lower())
        if not field:
            continue
        metrics[field] = _parse_count(value, suffix)
    return metrics


def _parse_count(value: str, suffix: str) -> int:
    try:
        if suffix:
            num = float(value.replace(",", "."))
            mult = 1_000 if suffix.lower() == "k" else 1_000_000
            return int(num * mult)
        return int(value.replace(".", "").replace(",", ""))
    except ValueError:
        return 0


def _status_parts(href: str | None) -> tuple[str | None, str | None]:
    if not href:
        return None, None
    m = STATUS_RE.match(href)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def _normalize_item(item: dict[str, Any], query: Query) -> dict[str, Any] | None:
    handle, post_id = _status_parts(item.get("status_href"))
    if not post_id:
        return None

    social_ctx = (item.get("social_context") or "").lower()
    is_retweet = "repost" in social_ctx or "retweet" in social_ctx or "retuitou" in social_ctx

    return {
        "id": post_id,
        "url": f"https://x.com{item['status_href']}" if item.get("status_href") else None,
        "created_at_utc": item.get("created_at"),
        "text": (item.get("text") or "").strip(),
        "lang": item.get("lang"),
        "author_handle": handle,
        "author_name": item.get("author_name"),
        "author_followers": 0,  # não disponível no card de busca; ver README
        "author_verified": bool(item.get("verified")),
        **_parse_counts(item.get("group_aria")),
        "is_retweet": is_retweet,
        "is_quote": len(item.get("all_status_hrefs") or []) > 1,
        "is_reply": bool(item.get("reply_context")),
        "conversation_id": post_id,  # aproximação: raiz da conversa não é visível na busca
        "hashtags": item.get("hashtags") or [],
        "place": None,  # não disponível no card de busca
        "query_grupo": query.grupo,
        "query_texto": query.texto,
    }


def _is_login_page(page) -> bool:
    url = page.url.lower()
    if "/login" in url or "mode=login" in url:
        return True
    try:
        texto = page.locator("body").inner_text(timeout=3000).lower()
    except Exception:
        return False
    return any(marker in texto for marker in LOGIN_MARKERS)


def _write_debug_artifacts(page, debug_dir: Path, query: Query, n: int) -> None:
    debug_dir.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(debug_dir / "debug_page.png"), full_page=True)
    (debug_dir / "debug_page.html").write_text(page.content(), encoding="utf-8")
    (debug_dir / "debug_meta.json").write_text(
        json.dumps(
            {
                "records": n,
                "current_url": page.url,
                "query_grupo": query.grupo,
                "query_texto": query.texto,
                "article_count": page.locator('article[data-testid="tweet"]').count(),
                "title": page.title(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _scrape_query(page, query: Query, limite: int, scrolls: int, sem_novidade_max: int) -> list[dict]:
    page.goto(build_search_url(query.texto), wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(4000)

    if _is_login_page(page):
        raise RuntimeError("login_wall")

    registros: list[dict] = []
    vistos: set[str] = set()
    sem_novidade = 0

    for _ in range(max(1, scrolls)):
        novos_nesta_rodada = 0
        for item in page.evaluate(_EXTRACT_JS):
            rec = _normalize_item(item, query)
            if rec and rec["id"] not in vistos:
                vistos.add(rec["id"])
                registros.append(rec)
                novos_nesta_rodada += 1
            if len(registros) >= limite:
                break

        if len(registros) >= limite:
            break

        sem_novidade = 0 if novos_nesta_rodada > 0 else sem_novidade + 1
        if sem_novidade >= sem_novidade_max:
            break  # resultados esgotados para esta query

        page.mouse.wheel(0, 2600)
        page.wait_for_timeout(2200)

    return registros


def _gravar_particionado(fonte: str, topico: str, registros: list[dict]) -> int:
    """Agrupa por mês do created_at_utc de cada registro e acrescenta ao
    posts.jsonl da partição correspondente. Uma query pode espalhar
    resultados por vários meses (camadas marca+mod/livre cobrem o período
    inteiro), então particiona pelo dado real, não pela janela da query."""
    por_mes: dict[str, list[dict]] = {}
    for rec in registros:
        dt = rec.get("created_at_utc")
        mes = paths.ano_mes(dt) if dt else "sem_data"
        por_mes.setdefault(mes, []).append(rec)

    for mes, recs in por_mes.items():
        destino = paths.raw_partition(fonte, topico, mes) / "posts.jsonl"
        with destino.open("a", encoding="utf-8") as fh:
            for rec in recs:
                fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    return len(registros)


def coletar(
    cfg: dict,
    retomar: bool,
    only_grupo: str | None = None,
    headed: bool = False,
    debug_dir: str | None = None,
) -> Path:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit(
            "playwright não instalado. Rode:\n"
            "  pip install -r requirements.txt\n"
            "  python -m playwright install chromium"
        )

    topico = cfg["topico"]
    col = cfg["fontes"]["twitter"]
    ckpt_path = paths.checkpoint_path("twitter", topico)

    feitas: set[str] = set()
    if retomar and ckpt_path.exists():
        feitas = set(ckpt_path.read_text(encoding="utf-8").splitlines())
        print(f"Retomando: {len(feitas)} queries já concluídas serão puladas.")

    todas = build_queries(cfg)
    if only_grupo:
        todas = [q for q in todas if q.grupo == only_grupo]
    pendentes = [q for q in todas if q.texto not in feitas]
    print(f"{len(pendentes)} de {len(todas)} queries a executar.")

    limite = int(col.get("limit_por_query", 200))
    scrolls = int(col.get("scrolls_por_query", 12))
    sem_novidade_max = int(col.get("scrolls_sem_novidade_max", 4))
    delay = float(col.get("delay_entre_queries", 3.0))
    storage_state_path = col.get("storage_state_path")
    if storage_state_path and not Path(storage_state_path).exists():
        storage_state_path = None

    total = 0
    debug_path = Path(debug_dir) if debug_dir else None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not headed,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        context_kwargs: dict[str, Any] = {
            "locale": "pt-BR",
            "viewport": {"width": 1366, "height": 900},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
        }
        if storage_state_path:
            context_kwargs["storage_state"] = storage_state_path
        context = browser.new_context(**context_kwargs)
        context.add_init_script(_STEALTH_JS)
        page = context.new_page()

        zeros_seguidos = 0
        transicao_zero_salva = False

        for i, q in enumerate(pendentes, start=1):
            print(f"[{i}/{len(pendentes)}] {q.grupo} :: {q.texto}", flush=True)
            try:
                registros = _scrape_query(page, q, limite, scrolls, sem_novidade_max)
            except RuntimeError as exc:
                if str(exc) == "login_wall" and debug_path:
                    _write_debug_artifacts(page, debug_path, q, 0)
                print(
                    "  !! X redirecionou para login — sessão necessária. Rode "
                    "session_from_cookies.py e confira fontes.twitter.storage_state_path. "
                    "Query NÃO marcada como concluída."
                )
                break
            except Exception as exc:  # bloqueio, timeout, mudança de HTML
                print(f"  !! falhou ({type(exc).__name__}: {exc}) — query NÃO marcada como concluída")
                time.sleep(15)
                continue

            _gravar_particionado("twitter", topico, registros)

            with ckpt_path.open("a", encoding="utf-8") as ck:
                ck.write(q.texto + "\n")
            total += len(registros)
            print(f"  -> {len(registros)} posts (acumulado {total})")

            if len(registros) == 0:
                zeros_seguidos += 1
            else:
                zeros_seguidos = 0
                transicao_zero_salva = False

            if debug_path and i == 1:
                _write_debug_artifacts(page, debug_path, q, len(registros))
            elif debug_path and zeros_seguidos == 1 and not transicao_zero_salva:
                # primeira query que zerou depois de uma que trouxe resultado:
                # captura o estado da página bem no ponto em que os resultados sumiram
                _write_debug_artifacts(page, debug_path, q, 0)
                transicao_zero_salva = True
                print("  (resultado zerou — artefatos de debug salvos para investigar)")

            if zeros_seguidos == 5:
                print(
                    "  !! 5 buscas seguidas sem nenhum resultado — pode ser bloqueio/limite "
                    "de busca, não ausência real de posts. Confira debug/ antes de confiar "
                    "nesse trecho do período."
                )

            time.sleep(delay + random.uniform(0, 1.5))

        browser.close()

    print(f"\n{total} posts salvos em data/raw/twitter/{topico}/<AAAA-MM>/posts.jsonl")
    return paths.raw_root("twitter", topico)


def main() -> None:
    ap = argparse.ArgumentParser(description="Coleta posts do X (scraping da busca pública) para a análise da crise.")
    ap.add_argument("--topico", default="tania_bulhoes", help="nome do tópico -> lê config/<topico>.yaml")
    ap.add_argument("--no-resume", action="store_true", help="ignora o checkpoint e refaz tudo")
    ap.add_argument("--grupo", default=None, help="roda só um grupo de query (ex: marca_ampla), útil para validar")
    ap.add_argument("--headed", action="store_true", help="abre o navegador visível")
    ap.add_argument("--debug-artifacts", action="store_true", help="salva screenshot/html/meta da primeira query")
    args = ap.parse_args()

    cfg_path = Path("config") / f"{args.topico}.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    coletar(
        cfg,
        retomar=not args.no_resume,
        only_grupo=args.grupo,
        headed=args.headed,
        debug_dir="debug" if args.debug_artifacts else None,
    )


if __name__ == "__main__":
    main()
