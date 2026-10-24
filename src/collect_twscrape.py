"""Coleta no X/Twitter via twscrape.

Grava um JSONL bruto por execução em data/raw/ (append-only, nada é sobrescrito),
mais um checkpoint de queries já concluídas para permitir retomada.

Requer contas do X cadastradas na pool. Ver README ("Contas").
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from queries import Query, build_queries  # noqa: E402
import paths  # noqa: E402


def _safe(obj, *caminho, default=None):
    """getattr aninhado tolerante — twscrape muda nomes de campo entre versões."""
    cur = obj
    for nome in caminho:
        if cur is None:
            return default
        cur = getattr(cur, nome, None)
    return default if cur is None else cur


def _extrair(tweet, query: Query) -> dict:
    """Achata um objeto Tweet do twscrape no nosso schema."""
    data = _safe(tweet, "date")
    if isinstance(data, datetime):
        iso = data.astimezone(timezone.utc).isoformat()
    else:
        iso = str(data) if data else None

    rt = _safe(tweet, "retweetedTweet")
    qt = _safe(tweet, "quotedTweet")

    return {
        "id": str(_safe(tweet, "id", default="")),
        "url": _safe(tweet, "url"),
        "created_at_utc": iso,
        "text": _safe(tweet, "rawContent") or _safe(tweet, "content") or "",
        "lang": _safe(tweet, "lang"),
        "author_handle": _safe(tweet, "user", "username"),
        "author_name": _safe(tweet, "user", "displayname"),
        "author_followers": _safe(tweet, "user", "followersCount", default=0),
        "author_verified": bool(_safe(tweet, "user", "verified", default=False)),
        "likes": _safe(tweet, "likeCount", default=0),
        "retweets": _safe(tweet, "retweetCount", default=0),
        "replies": _safe(tweet, "replyCount", default=0),
        "quotes": _safe(tweet, "quoteCount", default=0),
        "bookmarks": _safe(tweet, "bookmarkedCount", default=0),
        "views": _safe(tweet, "viewCount", default=0),
        "is_retweet": rt is not None,
        "is_quote": qt is not None,
        "is_reply": _safe(tweet, "inReplyToTweetId") is not None,
        "conversation_id": str(_safe(tweet, "conversationId", default="")),
        "hashtags": _safe(tweet, "hashtags", default=[]),
        "place": _safe(tweet, "place", "fullName"),
        "query_grupo": query.grupo,
        "query_texto": query.texto,
    }


async def coletar(cfg: dict, retomar: bool) -> Path:
    try:
        from twscrape import API
    except ImportError:
        sys.exit("twscrape não instalado. Rode: pip install -r requirements.txt")

    topico = cfg["topico"]
    col = cfg["fontes"]["twitter"]
    ckpt_path = paths.checkpoint_path("twitter", topico)

    feitas: set[str] = set()
    if retomar and ckpt_path.exists():
        feitas = set(ckpt_path.read_text(encoding="utf-8").splitlines())
        print(f"Retomando: {len(feitas)} queries já concluídas serão puladas.")

    api = API()
    contas = await api.pool.accounts_info()
    ativas = [c for c in contas if c.get("active")]
    if not ativas:
        sys.exit(
            "Nenhuma conta ativa na pool do twscrape.\n"
            "Cadastre com:  twscrape add_accounts accounts.txt "
            "username:password:email:email_password\n"
            "e depois:      twscrape login_accounts\n"
            "Ver README, seção 'Contas'."
        )
    print(f"{len(ativas)} conta(s) ativa(s) na pool.")

    todas = build_queries(cfg)
    pendentes = [q for q in todas if q.texto not in feitas]
    print(f"{len(pendentes)} de {len(todas)} queries a executar.")

    limite = int(col.get("limit_por_query", 3000))
    produto = col.get("product", "Latest")
    delay = float(col.get("delay_entre_queries", 1.5))
    total = 0

    for i, q in enumerate(pendentes, start=1):
        print(f"[{i}/{len(pendentes)}] {q.grupo} :: {q.texto}", flush=True)
        registros = []
        try:
            async for tweet in api.search(q.texto, limit=limite, kv={"product": produto}):
                registros.append(_extrair(tweet, q))
        except Exception as exc:  # rate limit, conta banida, mudança de API
            print(f"  !! falhou ({type(exc).__name__}: {exc}) — query NÃO marcada como concluída")
            await asyncio.sleep(30)
            continue

        por_mes: dict[str, list[dict]] = {}
        for rec in registros:
            dt = rec.get("created_at_utc")
            mes = paths.ano_mes(dt) if dt else "sem_data"
            por_mes.setdefault(mes, []).append(rec)
        for mes, recs in por_mes.items():
            destino = paths.raw_partition("twitter", topico, mes) / "posts.jsonl"
            with destino.open("a", encoding="utf-8") as fh:
                for rec in recs:
                    fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")

        with ckpt_path.open("a", encoding="utf-8") as ck:
            ck.write(q.texto + "\n")
        total += len(registros)
        print(f"  -> {len(registros)} posts (acumulado {total})")
        await asyncio.sleep(delay + random.uniform(0, 1.0))

    print(f"\n{total} posts salvos em data/raw/twitter/{topico}/<AAAA-MM>/posts.jsonl")
    return paths.raw_root("twitter", topico)


def main() -> None:
    ap = argparse.ArgumentParser(description="Coleta posts do X para a análise da crise.")
    ap.add_argument("--topico", default="tania_bulhoes", help="nome do tópico -> lê config/<topico>.yaml")
    ap.add_argument("--no-resume", action="store_true", help="ignora o checkpoint e refaz tudo")
    args = ap.parse_args()

    cfg_path = Path("config") / f"{args.topico}.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    asyncio.run(coletar(cfg, retomar=not args.no_resume))


if __name__ == "__main__":
    main()
