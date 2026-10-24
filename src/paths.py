"""Caminhos padronizados da estrutura fonte > tópico > período.

  data/raw/<fonte>/<topico>/<AAAA-MM>/posts.jsonl
  data/raw/<fonte>/<topico>/checkpoint_queries.txt
  data/processed/<fonte>/<topico>/<basename>.csv (+ .xlsx, gráficos, amostras)
"""

from __future__ import annotations

from pathlib import Path


def raw_root(fonte: str, topico: str) -> Path:
    return Path("data/raw") / fonte / topico


def raw_partition(fonte: str, topico: str, ano_mes: str) -> Path:
    d = raw_root(fonte, topico) / ano_mes
    d.mkdir(parents=True, exist_ok=True)
    return d


def checkpoint_path(fonte: str, topico: str) -> Path:
    root = raw_root(fonte, topico)
    root.mkdir(parents=True, exist_ok=True)
    return root / "checkpoint_queries.txt"


def processed_dir(fonte: str, topico: str) -> Path:
    d = Path("data/processed") / fonte / topico
    d.mkdir(parents=True, exist_ok=True)
    return d


def combined_dir(topico: str) -> Path:
    """Saída combinada entre fontes, para um mesmo tópico."""
    d = Path("data/processed/combined") / topico
    d.mkdir(parents=True, exist_ok=True)
    return d


def combined_geral_dir() -> Path:
    """Saída combinada entre todos os tópicos e fontes."""
    d = Path("data/processed/combined/geral")
    d.mkdir(parents=True, exist_ok=True)
    return d


def ano_mes(iso_date: str) -> str:
    """'2025-02-11' ou '2025-02-11T10:00:00Z' -> '2025-02'."""
    return iso_date[:7]
