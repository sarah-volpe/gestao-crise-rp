"""Converte posts coletados manualmente (copiar/colar do X) para o JSONL bruto.

Use quando o X bloquear tanto o scraping quanto o twscrape (conta suspensa,
rate limit persistente). Preencha um CSV com as colunas abaixo e rode este
script — o resultado entra em data/raw/ e segue normalmente para
`run_pipeline.py process`.

Colunas aceitas (todas exceto `text` são opcionais):
  url, text, created_at (ISO 8601), author_handle, author_name, lang,
  likes, retweets, replies, quotes, views, is_retweet, is_quote, is_reply
"""

import argparse
import csv
import json
import re
from pathlib import Path

STATUS_RE = re.compile(r"/([^/]+)/status/(\d+)")


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "sim", "yes", "x"}


def _int(value: str | None) -> int:
    try:
        return int(str(value).strip().replace(".", "").replace(",", "") or 0)
    except ValueError:
        return 0


def _status_parts(url: str) -> tuple[str | None, str | None]:
    m = STATUS_RE.search(url or "")
    return (m.group(1), m.group(2)) if m else (None, None)


def import_csv(input_path: Path, query_grupo: str) -> list[dict]:
    registros = []
    with input_path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            text = (row.get("text") or "").strip()
            if not text:
                continue

            url = (row.get("url") or "").strip() or None
            handle, post_id = _status_parts(url or "")
            handle = (row.get("author_handle") or handle or "").removeprefix("@").strip() or None
            post_id = post_id or (row.get("id") or "").strip() or None

            registros.append(
                {
                    "id": post_id,
                    "url": url,
                    "created_at_utc": (row.get("created_at") or "").strip() or None,
                    "text": text,
                    "lang": (row.get("lang") or "").strip() or None,
                    "author_handle": handle,
                    "author_name": (row.get("author_name") or "").strip() or None,
                    "author_followers": _int(row.get("author_followers")),
                    "author_verified": _bool(row.get("author_verified")),
                    "likes": _int(row.get("likes")),
                    "retweets": _int(row.get("retweets")),
                    "replies": _int(row.get("replies")),
                    "quotes": _int(row.get("quotes")),
                    "bookmarks": _int(row.get("bookmarks")),
                    "views": _int(row.get("views")),
                    "is_retweet": _bool(row.get("is_retweet")),
                    "is_quote": _bool(row.get("is_quote")),
                    "is_reply": _bool(row.get("is_reply")),
                    "conversation_id": post_id,
                    "hashtags": [],
                    "place": None,
                    "query_grupo": query_grupo,
                    "query_texto": "manual_import",
                }
            )
    return registros


def main() -> None:
    ap = argparse.ArgumentParser(description="Converte CSV coletado manualmente para JSONL do pipeline.")
    ap.add_argument("--input", default="manual_posts.csv")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--query-grupo", default="manual")
    args = ap.parse_args()

    input_path = Path(args.input)
    raw_dir = Path(args.raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_path = raw_dir / "tweets_manual_import.jsonl"

    registros = import_csv(input_path, args.query_grupo)
    with output_path.open("a", encoding="utf-8") as fh:
        for rec in registros:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Input: {input_path}")
    print(f"Output (append): {output_path}")
    print(f"Registros: {len(registros)}")


if __name__ == "__main__":
    main()
