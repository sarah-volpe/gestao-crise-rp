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
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcc_protocolo as proto  # noqa: E402
from collect_x_scrape import (  # noqa: E402
    _EXTRACT_JS, _STEALTH_JS, _normalize_item, build_search_url,
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


VERIFICACAO = ("verificação de segurança", "confirme que é humano", "verify you are human",
               "checking your browser", "performing security verification")


def _texto(page) -> str:
    try:
        return page.locator("body").inner_text(timeout=5000).lower()
    except Exception:
        return ""


def _em_verificacao(page) -> bool:
    """Página de verificação anti-robô (Cloudflare). Nunca dispara se há publicações na tela."""
    try:
        if page.locator('article[data-testid="tweet"]').count() > 0:
            return False
        titulo = (page.title() or "").lower()
    except Exception:
        titulo = ""
    t = _texto(page)
    return (any(m in t for m in VERIFICACAO) or "just a moment" in titulo or "um momento" in titulo
            or "challenges.cloudflare.com" in page.content()[:200000])


def _bip() -> None:
    try:
        if os.name == "nt":
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        else:
            print("\a", end="", flush=True)
    except Exception:
        pass


URL_LOGIN_TRECHOS = ("/login", "/i/flow/login", "/i/flow/signup", "/i/jf/onboarding", "/logout")
SELETOR_TWEET = 'article[data-testid="tweet"]'
SELETOR_LOGIN = 'input[autocomplete="username"], [data-testid="loginButton"], [data-testid="signupButton"]'


def _is_login_page(page) -> bool:
    """Página de login do X. Decide pela URL e pelos botões de login, nunca por palavras soltas
    ("entrar" aparece em tweets comuns em português)."""
    if any(t in page.url for t in URL_LOGIN_TRECHOS):
        return True
    try:
        if page.locator(SELETOR_TWEET).count() > 0:
            return False
        return page.locator(SELETOR_LOGIN).count() > 0
    except Exception:
        return False


def _abrir(page, url: str, espera_max: float = 20.0) -> None:
    """Abre a URL e espera aparecer algo decidível: tweets, 'nenhum resultado', login ou verificação."""
    try:
        page.goto(url, wait_until="commit", timeout=60000)
    except Exception:
        pass  # o X às vezes não "termina" de carregar; seguimos e olhamos o que apareceu
    fim = time.time() + espera_max
    while time.time() < fim:
        try:
            if page.locator(SELETOR_TWEET).count() > 0:
                page.wait_for_timeout(1500)
                return
            t = _texto(page)
            if any(m in t for m in SEM_RESULTADOS) or _em_verificacao(page) or _is_login_page(page):
                return
        except Exception:
            pass
        time.sleep(1)


URL_HOME = "https://x.com/home"


def _logado(page) -> bool:
    url = page.url
    return (not _is_login_page(page) and "/i/flow" not in url and "/login" not in url
            and "/i/jf/" not in url)


def preparar_navegador(page) -> bool:
    """Antes de começar: abre o X e resolve login e verificação com a pessoa presente.
    Depois disso, o perfil do Chrome guarda a sessão e a coleta corre sem intervenção."""
    print("\n=== Preparação (fique na frente do computador por 1 ou 2 minutos) ===", flush=True)
    _abrir(page, URL_HOME)
    page.wait_for_timeout(3000)
    if _em_verificacao(page) and not _esperar_pessoa(
            page, "O X pediu a verificação 'Confirme que é humano'. Clique nela na janela do Chrome.",
            lambda: not _em_verificacao(page)):
        return False
    if not _logado(page) and not _esperar_pessoa(
            page, "O X pediu login. Entre com a CONTA DESCARTÁVEL na janela do Chrome.", lambda: _logado(page)):
        return False
    # uma busca de teste: é nela que a verificação costuma aparecer
    _abrir(page, build_search_url("teste lang:pt"))
    if _em_verificacao(page) and not _esperar_pessoa(
            page, "O X pediu a verificação 'Confirme que é humano'. Clique nela na janela do Chrome.",
            lambda: not _em_verificacao(page)):
        return False
    print("=== Tudo certo. A partir daqui a coleta segue sozinha; pode minimizar o Chrome. ===\n", flush=True)
    return True


def _esperar_pessoa(page, motivo: str, checar, max_min: int = 20) -> bool:
    """Pausa até a pessoa resolver algo na janela do Chrome (verificação ou login)."""
    print(f"\n  >>> {motivo}\n  >>> Estou esperando (até {max_min} min). A coleta continua sozinha depois.",
          flush=True)
    try:
        page.bring_to_front()
    except Exception:
        pass
    fim = time.time() + max_min * 60
    proximo_bip = 0.0
    while time.time() < fim:
        if time.time() >= proximo_bip:
            _bip()
            proximo_bip = time.time() + 30
        time.sleep(5)
        try:
            if checar():
                print("  >>> Resolvido, continuando.", flush=True)
                time.sleep(3)
                return True
        except Exception:
            pass
    return False


SEM_RESULTADOS = ("nenhum resultado", "no results for", "não encontramos resultados", "try searching for something else",
                  "tente buscar outra coisa", "tente pesquisar outra coisa")


def _caminhos(caso: str, b: proto.BuscaDia) -> tuple[Path, Path]:
    d = proto.raw_dir(caso, b.origem)
    return d / f"{b.since}.jsonl", d / f"{b.since}.meta.json"


def _coletar_busca(page, b: proto.BuscaDia, limite: int, scrolls: int, sem_novidade_max: int) -> list[dict]:
    _abrir(page, build_search_url(b.texto))
    if _em_verificacao(page):
        raise RuntimeError("verificacao")
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
    if not registros:
        # Zero posts só é aceito se o X disser que não há resultados. Sem essa
        # mensagem, a página provavelmente não carregou a busca (sessão
        # expirada, limite do X) e o dia NÃO pode ser registrado como vazio.
        try:
            corpo = page.locator("body").inner_text(timeout=5000).lower()
        except Exception:
            corpo = ""
        if _is_login_page(page):
            raise RuntimeError("login_wall")
        if not any(m in corpo for m in SEM_RESULTADOS):
            raise RuntimeError("vazio_suspeito")
    return list(registros.values())


def coletar(caso: str, incluir_opcionais: bool, refazer: bool, so_dia: str | None,
            so_origem: str | None, headed: bool, chromium_automatizado: bool = False) -> str | None:
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
    from login_x import PERFIL, achar_navegador, porta_livre
    exe = None if chromium_automatizado else achar_navegador()
    real = exe is not None
    if not real and (not state or not Path(state).exists()):
        sys.exit(f"Sessão do X não encontrada ({state}). Gere com: python src\\login_x.py")

    zeros = suspeitos = 0
    proc = None
    resultado = "ok"
    with sync_playwright() as p:
        if real:
            # Chrome instalado, aberto como programa comum, com o perfil do login_x.py.
            # O X vê um navegador normal; a pessoa pode resolver verificações na janela.
            PERFIL.mkdir(exist_ok=True)
            porta = porta_livre()
            proc = subprocess.Popen([exe, f"--remote-debugging-port={porta}", f"--user-data-dir={PERFIL.resolve()}",
                                     "--no-first-run", "--no-default-browser-check", "--new-window", "about:blank"],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(30):
                try:
                    browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{porta}")
                    break
                except Exception:
                    time.sleep(1)
            else:
                sys.exit("Não consegui me conectar ao Chrome. Feche outras janelas abertas pelo login_x.py e tente de novo.")
            ctx = browser.contexts[0]
            page = ctx.new_page()
            print("Usando o seu Chrome (perfil .sessao_x).", flush=True)
            if not preparar_navegador(page):
                print("!! Login ou verificação não foram feitos a tempo. Rode o comando de novo quando "
                      "estiver na frente do computador.")
                proc.terminate()
                return "parado"
        else:
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
            regs, parar, motivo = None, False, None
            for _tentativa in range(3):
                try:
                    regs = _coletar_busca(page, b, limite, scrolls, sem_nov)
                    break
                except RuntimeError as exc:
                    motivo = str(exc)
                    if motivo == "verificacao" and real:
                        if _esperar_pessoa(page, "O X pediu a verificação 'Confirme que é humano'. Clique nela "
                                           "na janela do Chrome.", lambda: not _em_verificacao(page)):
                            continue
                        parar = True
                    elif motivo == "login_wall" and real:
                        if _esperar_pessoa(page, "O X pediu login. Entre com a conta descartável na janela do Chrome.",
                                           lambda: _logado(page)):
                            continue
                        parar = True
                    break
                except Exception as exc:
                    motivo = f"{type(exc).__name__}: {exc}"
                    break

            if parar:
                print("  !! Ninguém resolveu a tempo. Rode o mesmo comando depois (retoma de onde parou).")
                resultado = "parado"
                break
            if regs is None:
                if motivo == "vazio_suspeito":
                    suspeitos += 1
                    Path("debug").mkdir(exist_ok=True)
                    shot = Path("debug") / f"vazio_{caso}_{b.origem}_{b.since}.png"
                    try:
                        page.screenshot(path=str(shot))
                    except Exception:
                        pass
                    limite_x = "something went wrong" in _texto(page) or "algo deu errado" in _texto(page)
                    print(f"  !! 0 posts {'(limite de buscas do X)' if limite_x else 'sem a mensagem Nenhum resultado do X'}: "
                          f"busca NÃO marcada como feita (imagem da tela em {shot})")
                    if suspeitos >= 3:
                        print("  !! 3 buscas seguidas sem carregar resultados: o X pode estar limitando a conta. "
                              "Espere um pouco e rode o mesmo comando (retoma de onde parou).")
                        break
                    time.sleep(10)
                elif motivo in ("login_wall", "verificacao"):
                    print("  !! X pediu login ou verificação. Rode python src\\login_x.py e depois o mesmo "
                          "comando de coleta (retoma de onde parou).")
                    break
                else:
                    print(f"  !! falhou ({motivo}); busca NÃO marcada como feita")
                    time.sleep(15)
                continue

            suspeitos = 0
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
        if real:
            try:
                page.close()
            except Exception:
                pass
        else:
            browser.close()
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
    return resultado


def main() -> None:
    ap = argparse.ArgumentParser(description="Coleta do protocolo do TCC no X.")
    ap.add_argument("--caso", required=True, choices=proto.casos_disponiveis())
    ap.add_argument("--incluir-opcionais", action="store_true", help="inclui fases opcionais (ex.: segunda_onda)")
    ap.add_argument("--refazer", action="store_true", help="refaz buscas já feitas (sobrescreve o dia)")
    ap.add_argument("--so-dia", help="AAAA-MM-DD (dia UTC da busca)")
    ap.add_argument("--so-origem", choices=["principal", "complementar"])
    ap.add_argument("--headed", action="store_true", help="mostra o navegador (só no modo automatizado)")
    ap.add_argument("--chromium-automatizado", action="store_true",
                    help="usa o Chromium do Playwright em vez do seu Chrome (o X tende a bloquear com verificação)")
    a = ap.parse_args()
    coletar(a.caso, a.incluir_opcionais, a.refazer, a.so_dia, a.so_origem, a.headed, a.chromium_automatizado)


if __name__ == "__main__":
    main()
