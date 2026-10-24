"""Monta a matriz de queries do X a partir do config."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Query:
    """Uma busca a ser executada no X."""

    grupo: str          # rótulo legível, vai para a coluna query_origin
    texto: str          # query final, com operadores since:/until:
    since: str
    until: str

    def __str__(self) -> str:
        return self.texto


def _or_group(termos: list[str]) -> str:
    return "(" + " OR ".join(termos) + ")"


def _dias(since: str, until: str) -> list[tuple[str, str]]:
    """Fatia o período em janelas de 1 dia. `until` é exclusivo."""
    d0 = date.fromisoformat(since)
    d1 = date.fromisoformat(until)
    janelas = []
    while d0 < d1:
        prox = d0 + timedelta(days=1)
        janelas.append((d0.isoformat(), prox.isoformat()))
        d0 = prox
    return janelas


def build_queries(cfg: dict) -> list[Query]:
    """Gera a lista completa de buscas para a fonte twitter.

    Estratégia em três camadas:
      1. marca_ampla  -> só o nome da marca, fatiado por dia (o grosso do volume)
      2. marca+modificador -> período inteiro, para pescar o que a camada 1 perdeu
      3. queries_livres -> termos da crise sem exigir o nome da marca

    `cfg` é o config do tópico inteiro (com `periodo` no nível raiz e os
    termos de busca em `fontes.twitter`).
    """
    per = cfg["periodo"]
    col = cfg["fontes"]["twitter"]
    since, until = per["since"], per["until"]

    lang = col.get("lang")
    sufixo_lang = f" lang:{lang}" if lang else ""

    marca = _or_group(col["marca"]["termos"])
    queries: list[Query] = []

    def add(grupo: str, corpo: str, s: str, u: str) -> None:
        texto = f"{corpo}{sufixo_lang} since:{s} until:{u}"
        queries.append(Query(grupo=grupo, texto=texto, since=s, until=u))

    # Camada 1 - marca sozinha
    if col.get("fatiar_por_dia", True):
        for s, u in _dias(since, until):
            add("marca_ampla", marca, s, u)
    else:
        add("marca_ampla", marca, since, until)

    # Camada 2 - marca + eixo da crise
    for i, mod in enumerate(col.get("modificadores") or [], start=1):
        add(f"marca+mod{i}", f"{marca} ({mod})", since, until)

    # Camada 3 - termos da crise sem a marca
    for i, livre in enumerate(col.get("queries_livres") or [], start=1):
        add(f"livre{i}", f"({livre})", since, until)

    return queries


if __name__ == "__main__":  # inspeção rápida: python src/queries.py
    import sys
    from pathlib import Path

    import yaml

    cfg_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("config/tania_bulhoes.yaml")
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    qs = build_queries(cfg)
    print(f"{len(qs)} queries:\n")
    for q in qs:
        print(f"[{q.grupo}] {q.texto}")
