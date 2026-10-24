"""Gera demo/raw/amostra.jsonl com posts SINTÉTICOS (escritos à mão, não coletados).

Objetivo: validar a pipeline de processamento e o formato da tabela final sem
depender de contas do X. Não use estes dados em nenhuma análise real.
"""

from __future__ import annotations

import json
from pathlib import Path

POSTS = [
    ("2025-02-03T14:22:00+00:00", "gente a xícara da Tania Bulhoes custa 1.500 reais e é FABRICADA NA TAILÂNDIA, alguém me explica", 1240, 890, 210, 45),
    ("2025-02-03T18:40:00+00:00", "propaganda enganosa pura da Tania Bulhoes, vender porcelana terceirizada como artesanal brasileira é golpe", 3400, 2100, 380, 120),
    ("2025-02-04T09:05:00+00:00", "Tania Bulhoes inaugura nova loja no Shopping Cidade Jardim nesta semana", 12, 3, 1, 0),
    ("2025-02-04T21:15:00+00:00", "amo os difusores da Tania Bulhões, o cheiro é maravilhoso e a embalagem é impecável, vale cada centavo", 210, 8, 14, 2),
    ("2025-02-05T11:33:00+00:00", "achei exagero esse boicote todo, a marca sempre foi transparente e a qualidade é ótima", 88, 5, 40, 3),
    ("2025-02-05T16:50:00+00:00", "não gostei nada da nota oficial da Tania Bulhoes, zero responsabilidade, só jogaram a culpa no fornecedor", 940, 410, 95, 22),
    ("2025-02-06T08:12:00+00:00", "que marca maravilhosa, parabéns pela transparência 🙃 kkkk sqn", 1500, 700, 60, 30),
    ("2025-02-07T13:00:00+00:00", "alguém sabe se o Procon vai abrir processo contra a Tania Bulhoes por causa da xícara?", 60, 12, 25, 4),
    ("2025-02-10T19:45:00+00:00", "MENTIRA DESCARADA. Nunca mais compro nada dessa marca 🤮 vergonha", 2200, 1300, 140, 70),
    ("2025-02-12T10:20:00+00:00", "crise da xícara mostrou que markup de luxo no Brasil é surreal, 1500 reais numa peça de porcelana importada", 780, 320, 55, 18),
    ("2025-02-14T22:10:00+00:00", "presente de dia dos namorados: kit Tania Bulhoes. ela adorou, produto lindíssimo", 45, 1, 3, 0),
    ("2025-02-18T15:30:00+00:00", "a Tania Bulhoes apagou os comentários do post, isso sim é péssima gestão de crise", 610, 250, 40, 15),
    ("2025-02-20T12:00:00+00:00", "faturamento da Tania Bulhoes deve cair depois dessa polêmica, o dano reputacional foi grande", 130, 30, 12, 5),
    ("2025-02-25T17:55:00+00:00", "sigo comprando Tania Bulhoes, qualidade excelente e atendimento ótimo, o resto é mimimi da internet", 95, 6, 48, 2),
    ("2025-02-27T20:05:00+00:00", "resumo do mês: xícara de 1.500 reais, made in Thailand, e a marca fingindo que nada aconteceu. fiasco", 1800, 900, 110, 40),
]


def main() -> None:
    dest = Path(__file__).resolve().parent / "raw"
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / "amostra.jsonl"

    with out.open("w", encoding="utf-8") as fh:
        for i, (dt, texto, likes, rts, replies, quotes) in enumerate(POSTS, start=1):
            fh.write(json.dumps({
                "id": f"demo{i:04d}",
                "url": f"https://x.com/usuario_demo{i}/status/demo{i:04d}",
                "created_at_utc": dt,
                "text": texto,
                "lang": "pt",
                "author_handle": f"usuario_demo{i}",
                "author_name": f"Usuário Demo {i}",
                "author_followers": 500 * i,
                "author_verified": i % 5 == 0,
                "likes": likes, "retweets": rts, "replies": replies,
                "quotes": quotes, "bookmarks": 0, "views": likes * 30,
                "is_retweet": False, "is_quote": False, "is_reply": False,
                "conversation_id": f"demo{i:04d}",
                "hashtags": [], "place": None,
                "query_grupo": "demo", "query_texto": "demo",
            }, ensure_ascii=False) + "\n")

    print(f"{len(POSTS)} posts sintéticos em {out}")


if __name__ == "__main__":
    main()
