"""Coleta no Reddit via API oficial (PRAW) — leitura pública, sem risco de ToS.

Ao contrário do X, o Reddit tem API gratuita e oficial para leitura pública,
então esse coletor não precisa de scraping nem de sessão logada arriscada.

Credenciais (gratuitas, leva 2 minutos):
  1. Acesse https://www.reddit.com/prefs/apps logado com sua conta Reddit.
  2. "create app" (ou "create another app") -> tipo "script".
  3. Nome: qualquer um. redirect uri: http://localhost:8080 (não é usado).
  4. Depois de criado, o client_id é o texto embaixo do nome do app; o
     client_secret aparece no campo "secret".
  5. Configure as variáveis de ambiente antes de rodar:
       PowerShell:  $env:REDDIT_CLIENT_ID="..."; $env:REDDIT_CLIENT_SECRET="..."
     Nunca coloque essas credenciais no config.yaml nem em código versionado.

Busca por termo em uma lista de subreddits (ou "all" para busca no Reddit
inteiro), grava posts e os comentários de maior score de cada post
encontrado, particionados por mês, com checkpoint resumível. Mesmo schema
de campos usado pelo coletor do X (id, url, created_at_utc, text, likes...)
para reaproveitar normalize.py/sentiment.py sem alterações.

Uso:
  python src\\collect_reddit.py --topico tania_bulhoes
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _normalize_submission(sub, termo: str, subreddit_alvo: str) -> dict:
    texto = (sub.title or "").strip()
    if getattr(sub, "selftext", ""):
        texto = f"{texto}\n\n{sub.selftext.strip()}"
    return {
        "id": sub.id,
        "url": f"https://www.reddit.com{sub.permalink}",
        "created_at_utc": _iso(sub.created_utc),
        "text": texto,
        "lang": None,  # Reddit não informa idioma do post
        "author_handle": str(sub.author) if sub.author else None,
        "author_name": None,
        "author_followers": 0,  # sem equivalente público no Reddit
        "author_verified": False,
        "likes": int(sub.score or 0),
        "retweets": int(getattr(sub, "num_crossposts", 0) or 0),  # crosspost é o mais próximo de "repost"
        "replies": int(sub.num_comments or 0),
        "quotes": 0,
        "bookmarks": 0,
        "views": 0,  # não exposto publicamente pela API
        "is_retweet": False,
        "is_quote": False,
        "is_reply": False,
        "conversation_id": sub.id,
        "hashtags": [],
        "place": None,
        "subreddit": str(sub.subreddit),
        "tipo": "post",
        "query_grupo": f"subreddit:{subreddit_alvo}",
        "query_texto": termo,
    }


def _normalize_comment(com, submission_id: str, subreddit_alvo: str, termo: str) -> dict:
    return {
        "id": com.id,
        "url": f"https://www.reddit.com{com.permalink}",
        "created_at_utc": _iso(com.created_utc),
        "text": (com.body or "").strip(),
        "lang": None,
        "author_handle": str(com.author) if com.author else None,
        "author_name": None,
        "author_followers": 0,
        "author_verified": False,
        "likes": int(com.score or 0),
        "retweets": 0,
        "replies": 0,
        "quotes": 0,
        "bookmarks": 0,
        "views": 0,
        "is_retweet": False,
        "is_quote": False,
        "is_reply": True,
        "conversation_id": submission_id,
        "hashtags": [],
        "place": None,
        "subreddit": str(subreddit_alvo),
        "tipo": "comentario",
        "query_grupo": f"subreddit:{subreddit_alvo}",
        "query_texto": termo,
    }


def _gravar_particionado(topico: str, registros: list[dict]) -> int:
    por_mes: dict[str, list[dict]] = {}
    for rec in registros:
        mes = paths.ano_mes(rec["created_at_utc"])
        por_mes.setdefault(mes, []).append(rec)
    for mes, recs in por_mes.items():
        destino = paths.raw_partition("reddit", topico, mes) / "posts.jsonl"
        with destino.open("a", encoding="utf-8") as fh:
            for rec in recs:
                fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    return len(registros)


def coletar(cfg: dict, retomar: bool = True) -> Path:
    try:
        import praw
    except ImportError:
        sys.exit("praw não instalado. Rode: pip install -r requirements.txt")

    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        sys.exit(
            "Faltam credenciais do Reddit.\n"
            "Configure REDDIT_CLIENT_ID e REDDIT_CLIENT_SECRET (ver docstring "
            "deste arquivo para como criar um app gratuito em "
            "https://www.reddit.com/prefs/apps)."
        )

    topico = cfg["topico"]
    red = cfg["fontes"]["reddit"]
    if not red.get("ativo", False):
        sys.exit(f"fontes.reddit.ativo está false no config de '{topico}'. Ative antes de rodar.")

    per = cfg["periodo"]
    since_ts = datetime.fromisoformat(per["since"]).replace(tzinfo=timezone.utc).timestamp()
    until_ts = datetime.fromisoformat(per["until"]).replace(tzinfo=timezone.utc).timestamp()

    ckpt_path = paths.checkpoint_path("reddit", topico)
    feitas: set[str] = set()
    if retomar and ckpt_path.exists():
        feitas = set(ckpt_path.read_text(encoding="utf-8").splitlines())
        print(f"Retomando: {len(feitas)} combinações subreddit+termo já concluídas serão puladas.")

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=red.get("user_agent", f"tcc-crise-monitor/0.1 (topico:{topico})"),
    )
    reddit.read_only = True

    subreddits = red.get("subreddits") or ["all"]
    termos = red.get("termos_busca") or []
    ordenacao = red.get("ordenacao", "new")
    janela_top = red.get("janela_top", "all")
    limite = int(red.get("limit_por_busca", 300))
    n_comentarios = int(red.get("comentarios_por_post", 20))

    pares = [(sr, termo) for sr in subreddits for termo in termos]
    pendentes = [(sr, termo) for sr, termo in pares if f"{sr}::{termo}" not in feitas]
    print(f"{len(pendentes)} de {len(pares)} combinações subreddit+termo a executar.")

    total_posts = 0
    total_comentarios = 0

    for i, (sr, termo) in enumerate(pendentes, start=1):
        print(f"[{i}/{len(pendentes)}] r/{sr} :: {termo}", flush=True)
        try:
            sub = reddit.subreddit(sr)
            resultados = list(sub.search(
                termo, sort=ordenacao, limit=limite,
                time_filter=janela_top if ordenacao == "top" else "all",
            ))
        except Exception as exc:
            print(f"  !! falhou ({type(exc).__name__}: {exc}) — combinação NÃO marcada como concluída")
            time.sleep(5)
            continue

        no_periodo = [s for s in resultados if since_ts <= s.created_utc < until_ts]
        registros = [_normalize_submission(s, termo, sr) for s in no_periodo]

        for s in no_periodo:
            try:
                s.comment_sort = "top"
                s.comments.replace_more(limit=0)
                comentarios = sorted(s.comments.list(), key=lambda c: c.score or 0, reverse=True)
                for com in comentarios[:n_comentarios]:
                    if com.body in ("[deleted]", "[removed]"):
                        continue
                    registros.append(_normalize_comment(com, s.id, sr, termo))
            except Exception as exc:
                print(f"    (comentários de {s.id} falharam: {type(exc).__name__})")

        _gravar_particionado(topico, registros)

        n_posts = len(no_periodo)
        n_com = len(registros) - n_posts
        total_posts += n_posts
        total_comentarios += n_com
        print(f"  -> {n_posts} posts + {n_com} comentários "
              f"(acumulado {total_posts} posts, {total_comentarios} comentários)")

        with ckpt_path.open("a", encoding="utf-8") as ck:
            ck.write(f"{sr}::{termo}\n")

        time.sleep(1.5)  # a API oficial tem rate limit generoso; ainda assim, não martele

    print(f"\n{total_posts + total_comentarios} registros salvos em "
          f"data/raw/reddit/{topico}/<AAAA-MM>/posts.jsonl")
    return paths.raw_root("reddit", topico)


def main() -> None:
    ap = argparse.ArgumentParser(description="Coleta posts+comentários do Reddit via API oficial.")
    ap.add_argument("--topico", default="tania_bulhoes", help="nome do tópico -> lê config/<topico>.yaml")
    ap.add_argument("--no-resume", action="store_true", help="ignora o checkpoint e refaz tudo")
    args = ap.parse_args()

    cfg_path = Path("config") / f"{args.topico}.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    coletar(cfg, retomar=not args.no_resume)


if __name__ == "__main__":
    main()
