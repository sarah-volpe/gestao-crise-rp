"""Gera os dados do painel (painel/dados.js) a partir dos resultados públicos.

Lê, para cada caso em casos/:
  casos/<caso>.yaml                         nome, fases, marcos
  dados/<caso>/<caso>_posts_publico.csv     publicações SEM texto
  dados/<caso>/<caso>_volume_diario.csv     volume por dia
  dados/<caso>/<caso>_classificacao.csv     classificação da IA
  dados/<caso>/<caso>_classificacao_meta.json, <caso>_montagem.json
  dados/<caso>/validacao/<caso>_validacao_resultado.json (se houver)

Casos ainda sem coleta aparecem no painel como "aguardando coleta".
O texto integral das publicações nunca entra no painel.

Gera painel/dados.js (window.PAINEL = {...}), que funciona tanto no GitHub
Pages quanto abrindo painel/index.html direto do disco.

Uso:
  python src/tcc_painel.py
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcc_protocolo as proto  # noqa: E402

SENT = ["negativo", "neutro", "positivo", "fora_do_tema"]
DESTINO = Path("painel/dados.js")


def _ler_csv(p: Path) -> pd.DataFrame | None:
    return pd.read_csv(p, sep=";", encoding="utf-8-sig", dtype=str) if p.exists() else None


def _ler_json(p: Path) -> dict | None:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _volume(v: str) -> tuple[int | None, bool]:
    """'123' -> (123, False); 'mais de 300' -> (300, True); 'nao_coletado' -> (None, False)."""
    v = str(v or "").strip()
    if v.startswith("mais de"):
        return int(v.split()[-1]), True
    if v.startswith("parcial"):
        return int(v.strip("parcial() ")), False
    return (int(v), False) if v.isdigit() else (None, False)


def montar_caso(caso: str) -> dict:
    cfg = proto.carregar(caso)
    d = proto.TCC_ROOT / caso
    base = {
        "caso": caso, "nome": cfg["nome"], "ano": cfg["ano"],
        "contexto": " ".join(cfg["contexto"].split()),
        "nota_linha_de_base": " ".join((cfg.get("nota_linha_de_base") or "").split()),
        "fases": [{"nome": f.nome, "inicio": f.inicio.isoformat(), "fim": f.fim.isoformat(),
                   "opcional": f.opcional} for f in cfg["_fases"]],
        "marcos": [{"data": m["data"], "evento": m["evento"]} for m in cfg.get("marcos", []) if m.get("data")],
        "status": "aguardando_coleta",
    }
    posts = _ler_csv(d / f"{caso}_posts_publico.csv")
    vol = _ler_csv(d / f"{caso}_volume_diario.csv")
    if posts is None or vol is None:
        return base
    base["status"] = "coletado"
    base["montagem"] = _ler_json(d / f"{caso}_montagem.json")

    cla = _ler_csv(d / f"{caso}_classificacao.csv")
    if cla is not None:
        posts = posts.merge(cla, on="id", how="left")
        base["status"] = "classificado" if posts["sentimento"].notna().all() else "classificacao_parcial"
        base["classificacao"] = _ler_json(d / f"{caso}_classificacao_meta.json")
        if base["classificacao"]:
            base["classificacao"].pop("lotes_desta_execucao", None)
    else:
        posts["sentimento"] = None
    for c in ["curtidas", "respostas", "reposts"]:
        posts[c] = pd.to_numeric(posts[c], errors="coerce").fillna(0).astype(int)

    # só fases que têm dias no volume (fases opcionais não coletadas ficam de fora)
    fases_com_dados = set(vol["fase"])
    base["fases"] = [f for f in base["fases"] if f["nome"] in fases_com_dados]

    dias = []
    for r in vol.itertuples():
        n, mais = _volume(r.volume_estimado_no_dia)
        sub = posts[posts["data"] == r.data]
        dias.append({
            "data": r.data, "fase": r.fase, "volume": n, "volume_mais_de": mais,
            "coletado": str(r.volume_estimado_no_dia) != "nao_coletado",
            "parcial": str(r.volume_estimado_no_dia).startswith("parcial"),
            "amostra": int(r.posts_coletados),
            "sent": {s: int((sub["sentimento"] == s).sum()) for s in SENT},
        })
    base["dias"] = dias

    if posts["sentimento"].notna().any():
        cl = posts[posts["sentimento"].notna()]
        base["por_fase"] = [{"fase": f["nome"], **{s: int(((cl["fase"] == f["nome"]) & (cl["sentimento"] == s)).sum())
                                                  for s in SENT}} for f in base["fases"]]
        eixos = []
        for eixo, g in cl.groupby("eixo_tematico"):
            eixos.append({"eixo": eixo, **{s: int((g["sentimento"] == s).sum()) for s in SENT}})
        base["eixos"] = sorted(eixos, key=lambda e: -sum(e[s] for s in SENT))
        base["ironia"] = int((cl["ironia"] == "sim").sum())
        base["confianca"] = cl["confianca"].value_counts().to_dict()
        cl = cl.assign(eng=cl["curtidas"] + cl["respostas"] + cl["reposts"])
        base["destaques"] = [
            {"id": r.id, "link": r.link, "data": r.data, "fase": r.fase, "sentimento": r.sentimento,
             "eixo": r.eixo_tematico, "justificativa": r.justificativa, "engajamento": int(r.eng)}
            for r in cl[cl["sentimento"] != "fora_do_tema"].nlargest(8, "eng").itertuples()
        ]
    base["validacao"] = _ler_json(d / "validacao" / f"{caso}_validacao_resultado.json")
    return base


def main() -> None:
    dados = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "casos": [montar_caso(c) for c in ["tania_bulhoes", "colgate", "cacau_show"]
                  if c in proto.casos_disponiveis()]
                 + [montar_caso(c) for c in proto.casos_disponiveis()
                    if c not in ("tania_bulhoes", "colgate", "cacau_show")],
    }
    DESTINO.parent.mkdir(exist_ok=True)
    DESTINO.write_text("window.PAINEL = " + json.dumps(dados, ensure_ascii=False, default=str) + ";\n",
                       encoding="utf-8")
    for c in dados["casos"]:
        print(f"{c['nome']:28s} {c['status']}")
    print(f"-> {DESTINO}")


if __name__ == "__main__":
    main()
