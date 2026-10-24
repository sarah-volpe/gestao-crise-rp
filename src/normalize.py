"""Limpeza, deduplicação, filtro de relevância e enriquecimento do bruto."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from sentiment import strip_accents

TZ_BR = "America/Sao_Paulo"


def carregar_raw(raw_root: Path) -> pd.DataFrame:
    """Lê todos os posts.jsonl de data/raw/<fonte>/<topico>/<AAAA-MM>/ e junta."""
    arquivos = sorted(raw_root.glob("*/posts.jsonl"))
    if not arquivos:
        raise SystemExit(f"Nenhum posts.jsonl em {raw_root}. Rode a coleta primeiro.")

    linhas = []
    for arq in arquivos:
        with arq.open(encoding="utf-8") as fh:
            for ln in fh:
                ln = ln.strip()
                if ln:
                    try:
                        linhas.append(json.loads(ln))
                    except json.JSONDecodeError:
                        continue
    print(f"{len(linhas)} linhas brutas em {len(arquivos)} partição(ões).")
    return pd.DataFrame(linhas)


def _compilar_eixos(analise: dict) -> list[tuple[str, re.Pattern]]:
    """Eixos temáticos vêm do config do tópico (analise.eixos), não são
    fixos no código — cada crise tem seus próprios eixos. Ordem importa: o
    primeiro que casar é o principal."""
    return [(nome, re.compile(pat, re.IGNORECASE)) for nome, pat in analise.get("eixos", [])]


def _eixo(texto_norm: str, eixos: list[tuple[str, re.Pattern]]) -> str:
    achados = [nome for nome, pat in eixos if pat.search(texto_norm)]
    return achados[0] if achados else "outro"


def _eixos_todos(texto_norm: str, eixos: list[tuple[str, re.Pattern]]) -> str:
    return "; ".join(nome for nome, pat in eixos if pat.search(texto_norm)) or "outro"


def processar(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    rel = cfg.get("relevancia", {})
    per = cfg["periodo"]
    analise = cfg.get("analise", {})
    brand_re = re.compile(analise.get("marca_regex", r"(?!)"), re.IGNORECASE)  # (?!) nunca casa se ausente
    eixos = _compilar_eixos(analise)

    if df.empty:
        return df

    # --- dedup ---
    antes = len(df)
    df = df.drop_duplicates(subset=["id"], keep="first").copy()
    print(f"Dedup por id: {antes} -> {len(df)}")

    # --- datas ---
    df["created_at_utc"] = pd.to_datetime(df["created_at_utc"], utc=True, errors="coerce")
    df = df.dropna(subset=["created_at_utc"])
    df["data_hora_br"] = df["created_at_utc"].dt.tz_convert(TZ_BR)
    df["data"] = df["data_hora_br"].dt.date
    df["hora"] = df["data_hora_br"].dt.hour
    df["semana"] = df["data_hora_br"].dt.isocalendar().week

    # --- janela do período (em horário de Brasília) ---
    ini = pd.Timestamp(per["since"], tz=TZ_BR)
    fim = pd.Timestamp(per["until"], tz=TZ_BR)
    antes = len(df)
    df = df[(df["data_hora_br"] >= ini) & (df["data_hora_br"] < fim)]
    print(f"Filtro de período: {antes} -> {len(df)}")

    # --- texto ---
    df["text"] = df["text"].fillna("").astype(str).str.strip()
    df = df[df["text"].str.len() > 0]
    df["texto_norm"] = df["text"].map(lambda t: strip_accents(t.lower()))
    df["texto_len"] = df["text"].str.len()

    # --- retweets ---
    if rel.get("descartar_retweets", True):
        antes = len(df)
        df = df[~df["is_retweet"].fillna(False).astype(bool)]
        print(f"Descarte de retweets: {antes} -> {len(df)}")

    # --- relevância ---
    df["cita_marca"] = df["texto_norm"].map(lambda t: bool(brand_re.search(t)))
    if rel.get("exigir_marca", False):
        antes = len(df)
        df = df[df["cita_marca"]]
        print(f"Exigir menção à marca: {antes} -> {len(df)}")

    # --- enriquecimento ---
    df["eixo_principal"] = df["texto_norm"].map(lambda t: _eixo(t, eixos))
    df["eixos"] = df["texto_norm"].map(lambda t: _eixos_todos(t, eixos))

    for col in ["likes", "retweets", "replies", "quotes", "views", "author_followers"]:
        df[col] = pd.to_numeric(df.get(col), errors="coerce").fillna(0).astype("int64")
    df["engajamento_total"] = df["likes"] + df["retweets"] + df["replies"] + df["quotes"]

    df = df.sort_values("data_hora_br").reset_index(drop=True)
    print(f"Base final: {len(df)} posts únicos.")
    return df
