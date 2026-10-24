"""Coleta do protocolo do TCC no X (Playwright, mesma sessão do scraper atual).

Para cada dia UTC e cada origem (principal/complementar) roda a busca
literal do protocolo na aba "Mais recentes" e grava TUDO o que a página
carregar, até `limite_bruto_por_busca`. O teto de 15 posts/dia é aplicado
depois, por sorteio reprodutível (tcc_montar.py), o que evita o viés de
pegar só os últimos posts da noite.

Diferenças em relação ao collect_x_scrape.py:
  - texto extraído nó a nó: emojis (que o X desenha como <img alt>) e links
    completos são preservados; o innerText usado antes descartava emojis
    e quebrava URLs em várias linhas;
  - marca posts com "Mostrar mais" (texto possivelmente truncado na busca)
    e posts promovidos (anúncios, excluídos na montagem);
  - um arquivo por busca (data/raw/x_tcc/<caso>/<origem>/<dia>.jsonl),
    reescrito ao refazer o dia: refazer nunca duplica dados;
  - registra data/hora da coleta (as métricas de engajamento são as do dia
    da coleta, não as de 2025).

Uso:
  python src/tcc_coletar.py --caso tania_bulhoes
  python src/tcc_coletar.py --caso tania_bulhoes --so-dia 2025-02-04 --headed
  python src/tcc_coletar.py --caso colgate --incluir-opcionais
  python src/tcc_coletar.py --caso cacau_show --refazer
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcc_protocolo as proto  # noqa: E402
from collect_x_scrape import (  # noqa: E402
    _EXTRACT_JS, _STEALTH_JS, _is_login_page, _normalize_item, build_search_url,
)

# Extração complementar, por status_href: texto fiel + flags.
_EXTRA_JS = r"""
() => Array.from(document.querySelectorAll('article[data-testid="tweet"]')).map((article) => {
  const timeEl = article.querySelector('time');
  const a = timeEl ? timeEl.closest('a[href*="/status/"]') : null;
  const el = article.querySelector('div[data-testid="tweetText"]');
  let out = '';
  const walk = (n) => {
    if (n.nodeType === 3) { out += n.nodeValue; return; }
    if (n.nodeType !== 1) return;
    const tag = n.tagName;
    if (tag === 'IMG') { out += n.getAttribute('alt') || ''; return; }
    if (tag === 'BR') { out += '\n'; return; }
    if (tag === 'A') {
      let t = '';
      const w = (m) => {
        if (m.nodeType === 3) { t += m.nodeValue; return; }
        if (m.nodeType === 1 && m.tagName === 'IMG') { t += m.getAttribute('alt') || ''; return; }
        m.childNodes.forEach(w);
      };
      w(n);
      out += t.replace(/\s+/g, '');
      return;
    }
    n.childNodes.forEach(walk);
  };
  if (el) walk(el);
  const spans = Array.from(article.querySelectorAll('span')).map(s => s.textContent.trim());
  return {
    status_href: a ? a.getAttribute('href') : null,
    texto_fiel: out.trim(),
    show_more: !!article.querySelector('[data-testid="tweet-text-show-more-link"]'),
    promovido: spans.includes('Promovido') || spans.includes('Ad') || spans.includes('Anúncio'),
  };
})
"""


def _caminhos(caso: str, b: proto.BuscaDia) -> tuple[Path, Path]:
    d = proto.raw_dir(caso, b.origem)
    return d / f"{b.since}.jsonl", d / f"{b.since}.meta.json"


def _coletar_busca(page, b: proto.BuscaDia, limite: int, scrolls: int, sem_novidade_max: int) -> list[dict]:
    page.goto(build_search_url(b.texto), wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(4000)
    if _is_login_page(page):
        raise RuntimeError("login_wall")

    registros: dict[str, dict] = {}
    sem_novidade = 0
    for _ in range(max(1, scrolls)):
        antes = len(registros)
        extras = {e["status_href"]: e for e in page.evaluate(_EXTRA_JS) if e.get("status_href")}
        for item in page.evaluate(_EXTRACT_JS):
            rec = _normalize_item(item, b)  # type: ignore[arg-type]
            if not rec or rec["id"] in registros:
                continue
            ex = extras.get(item.get("status_href"), {})
            rec["texto_innerText"] = rec["text"]
            if ex.get("texto_fiel"):
                rec["text"] = ex["texto_fiel"]
            rec["texto_possivelmente_truncado"] = bool(ex.get("show_more"))
            rec["promovido"] = bool(ex.get("promovido"))
            rec["origem"] = b.origem
            rec["busca_dia_utc"] = b.since
            registros[rec["id"]] = rec
            if len(registros) >= limite:
                break
        if len(registros) >= limite:
            break
        sem_novidade = 0 if len(registros) > antes else sem_novidade + 1
        if sem_novidade >= sem_novidade_max:
            break
        page.mouse.wheel(0, 2600)
        page.wait_for_timeout(2200)
    return list(registros.values())


def coletar(caso: str, incluir_opcionais: bool, refazer: bool, so_dia: str | None,
            so_origem: str | None, headed: bool) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("playwright não instalado: pip install -r requirements.txt && python -m playwright install chromium")

    cfg = proto.carregar(caso)
    col = cfg["coleta"]
    todas = proto.buscas(cfg, incluir_opcionais)
    if so_dia:
        todas = [b for b in todas if b.since == so_dia]
    if so_origem:
        todas = [b for b in todas if b.origem == so_origem]
    pendentes = [b for b in todas if refazer or not _caminhos(caso, b)[1].exists()]
    print(f"[{caso}] {len(pendentes)} de {len(todas)} buscas a executar.")
    if not pendentes:
        return

    limite = int(col.get("limite_bruto_por_busca", 300))
    scrolls = int(col.get("scrolls_por_query", 40))
    sem_nov = int(col.get("scrolls_sem_novidade_max", 4))
    delay = float(col.get("delay_entre_queries", 8.0))
    state = col.get("storage_state_path")
    if not state or not Path(state).exists():
        sys.exit(f"Sessão do X não encontrada ({state}). Gere com: python src/session_from_cookies.py "
                 "--auth-token ... --ct0 ...")

    zeros = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed, args=["--disable-dev-shm-usage", "--no-sandbox"])
        ctx = browser.new_context(
            locale="pt-BR", viewport={"width": 1366, "height": 900}, storage_state=state,
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"),
        )
        ctx.add_init_script(_STEALTH_JS)
        page = ctx.new_page()

        for i, b in enumerate(pendentes, 1):
            print(f"[{i}/{len(pendentes)}] {b.origem} {b.since}", flush=True)
            try:
                regs = _coletar_busca(page, b, limite, scrolls, sem_nov)
            except RuntimeError:
                print("  !! X pediu login: sessão expirada. Gere de novo e rode o mesmo comando "
                      "(retoma de onde parou).")
                break
            except Exception as exc:
                print(f"  !! falhou ({type(exc).__name__}: {exc}); busca NÃO marcada como feita")
                time.sleep(15)
                continue

            dados, meta = _caminhos(caso, b)
            with dados.open("w", encoding="utf-8") as fh:
                for r in regs:
                    fh.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
            meta.write_text(json.dumps({
                "caso": caso, "origem": b.origem, "dia_utc": b.since, "query": b.texto,
                "posts_lidos": len(regs), "limite": limite, "limite_atingido": len(regs) >= limite,
                "coletado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  -> {len(regs)} posts{' (LIMITE ATINGIDO)' if len(regs) >= limite else ''}")

            zeros = zeros + 1 if not regs else 0
            if zeros == 5:
                print("  !! 5 buscas seguidas vazias: pode ser bloqueio do X, não ausência de posts. "
                      "Confira no navegador (--headed) antes de seguir; use --refazer --so-dia para repetir.")
            time.sleep(delay + random.uniform(0, 2))
        browser.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Coleta do protocolo do TCC no X.")
    ap.add_argument("--caso", required=True, choices=proto.casos_disponiveis())
    ap.add_argument("--incluir-opcionais", action="store_true", help="inclui fases opcionais (ex.: segunda_onda)")
    ap.add_argument("--refazer", action="store_true", help="refaz buscas já feitas (sobrescreve o dia)")
    ap.add_argument("--so-dia", help="AAAA-MM-DD (dia UTC da busca)")
    ap.add_argument("--so-origem", choices=["principal", "complementar"])
    ap.add_argument("--headed", action="store_true", help="mostra o navegador")
    a = ap.parse_args()
    coletar(a.caso, a.incluir_opcionais, a.refazer, a.so_dia, a.so_origem, a.headed)


if __name__ == "__main__":
    main()
