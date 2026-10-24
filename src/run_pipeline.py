"""Orquestrador da pipeline.

  python src/run_pipeline.py collect     # só coleta (grava data/raw/*.jsonl)
  python src/run_pipeline.py process     # bruto -> tabela final com sentimento
  python src/run_pipeline.py all         # coleta + processa
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import paths  # noqa: E402
from normalize import carregar_raw, processar  # noqa: E402
from sentiment import get_analyzer  # noqa: E402

# Ordem das colunas no entregável. O que foi pedido vem primeiro.
COLUNAS = [
    "data", "data_hora_br", "text", "sentimento", "sentimento_score",
    "sentimento_confianca", "sentimento_metodo", "sentimento_evidencia",
    "eixo_principal", "eixos", "cita_marca",
    "author_handle", "author_name", "author_followers", "author_verified",
    "likes", "retweets", "replies", "quotes", "views", "engajamento_total",
    "is_reply", "is_quote", "lang", "texto_len", "hora", "semana",
    "subreddit", "tipo",
    "url", "id", "conversation_id", "query_grupo",
]

RENOMEAR = {
    "data": "data_post",
    "data_hora_br": "data_hora_brasilia",
    "text": "texto",
    "sentimento": "classificacao_sentimento",
    "author_handle": "autor_usuario",
    "author_name": "autor_nome",
    "author_followers": "autor_seguidores",
    "author_verified": "autor_verificado",
    "likes": "curtidas",
    "retweets": "reposts",
    "replies": "respostas",
    "quotes": "citacoes",
    "views": "visualizacoes",
    "is_reply": "eh_resposta",
    "is_quote": "eh_citacao",
    "lang": "idioma",
    "texto_len": "tamanho_texto",
    "hora": "hora_do_dia",
    "semana": "semana_iso",
}


def aplicar_sentimento(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    sen = cfg.get("sentimento", {})
    an = get_analyzer(
        sen.get("metodo", "auto"),
        limiar=sen.get("limiar", 0.12),
        provider=sen.get("llm_provider", "anthropic"),
        modelo=sen.get("modelo_llm"),  # None -> LLMAnalyzer escolhe o padrão do provider
        lote=sen.get("lote_llm", 15),
        concorrencia=sen.get("concorrencia_llm", 4),
        descricao=cfg.get("descricao", ""),
    )

    textos = df["text"].tolist()
    print(f"Classificando {len(textos)} posts com backend '{an.metodo}'...")

    if hasattr(an, "analisar_lote"):
        resultados = an.analisar_lote(textos)
    else:
        resultados = []
        for i, t in enumerate(textos, start=1):
            resultados.append(an.analisar(t))
            if i % 500 == 0:
                print(f"  {i}/{len(textos)}")

    df["sentimento"] = [r.label for r in resultados]
    df["sentimento_score"] = [r.score for r in resultados]
    df["sentimento_confianca"] = [r.confianca for r in resultados]
    df["sentimento_metodo"] = [r.metodo for r in resultados]
    df["sentimento_evidencia"] = [r.termos for r in resultados]
    return df


def resumo(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Agregações auxiliares que vão para abas separadas do .xlsx."""
    total = len(df)
    dist = (
        df["sentimento"].value_counts().rename("posts").to_frame()
        .assign(percentual=lambda d: (d["posts"] / total * 100).round(1))
        .reset_index(names="sentimento")
    )

    diario = (
        df.pivot_table(index="data", columns="sentimento", values="id",
                       aggfunc="count", fill_value=0)
        .assign(total=lambda d: d.sum(axis=1))
        .reset_index()
    )

    eixos = (
        df.pivot_table(index="eixo_principal", columns="sentimento", values="id",
                       aggfunc="count", fill_value=0)
        .assign(total=lambda d: d.sum(axis=1))
        .sort_values("total", ascending=False)
        .reset_index()
    )

    top = (
        df.nlargest(min(100, total), "engajamento_total")
        [["data", "author_handle", "author_followers", "engajamento_total",
          "sentimento", "eixo_principal", "text", "url"]]
    )

    return {"distribuicao": dist, "por_dia": diario, "por_eixo": eixos, "top_engajamento": top}


def exportar(df: pd.DataFrame, cfg: dict, fonte: str) -> None:
    out = cfg.get("saida", {})
    dest = paths.processed_dir(fonte, cfg["topico"])
    base = out.get("basename", cfg["topico"])

    presentes = [c for c in COLUNAS if c in df.columns]
    tabela = df[presentes].rename(columns=RENOMEAR)
    tabela["data_hora_brasilia"] = tabela["data_hora_brasilia"].dt.strftime("%Y-%m-%d %H:%M:%S")

    csv_path = dest / f"{base}.csv"
    tabela.to_csv(csv_path, index=False, encoding="utf-8-sig")  # utf-8-sig abre certo no Excel
    print(f"CSV  -> {csv_path}")

    aggs = resumo(df)
    xlsx_path = dest / f"{base}.xlsx"
    try:
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as xw:
            tabela.to_excel(xw, sheet_name="posts", index=False)
            for nome, d in aggs.items():
                d.to_excel(xw, sheet_name=nome[:31], index=False)
        print(f"XLSX -> {xlsx_path}")
    except ImportError:
        print("openpyxl ausente — só o CSV foi gerado.")

    print("\n--- Distribuição de sentimento ---")
    print(aggs["distribuicao"].to_string(index=False))
    print("\n--- Volume por dia ---")
    print(aggs["por_dia"].to_string(index=False))


FONTES_VALIDAS = ("twitter", "reddit")


def _fontes_ativas(cfg: dict, fonte_arg: str) -> list[str]:
    disponiveis = [f for f in FONTES_VALIDAS if cfg.get("fontes", {}).get(f, {}).get("ativo")]
    if fonte_arg == "all":
        if not disponiveis:
            sys.exit("Nenhuma fonte com 'ativo: true' no config. Ative twitter e/ou reddit.")
        return disponiveis
    if fonte_arg not in cfg.get("fontes", {}):
        sys.exit(f"Fonte '{fonte_arg}' não existe no config do tópico '{cfg['topico']}'.")
    if not cfg["fontes"][fonte_arg].get("ativo"):
        sys.exit(f"fontes.{fonte_arg}.ativo está false no config do tópico '{cfg['topico']}'.")
    return [fonte_arg]


def _coletar_fonte(fonte: str, cfg: dict, retomar: bool) -> None:
    if fonte == "twitter":
        metodo = cfg["fontes"]["twitter"].get("metodo", "scrape")
        if metodo == "twscrape":
            from collect_twscrape import coletar

            asyncio.run(coletar(cfg, retomar=retomar))
        else:
            from collect_x_scrape import coletar

            coletar(cfg, retomar=retomar)
    elif fonte == "reddit":
        from collect_reddit import coletar

        coletar(cfg, retomar=retomar)


def _processar_fonte(fonte: str, cfg: dict) -> None:
    raw = carregar_raw(paths.raw_root(fonte, cfg["topico"]))
    df = processar(raw, cfg)
    if df.empty:
        print(f"[{fonte}] nada sobrou depois dos filtros — revise o config.")
        return
    df = aplicar_sentimento(df, cfg)
    exportar(df, cfg, fonte)


def main() -> None:
    ap = argparse.ArgumentParser(description="Pipeline multi-tópico / multi-fonte de monitoramento de crise.")
    ap.add_argument("etapa", choices=["collect", "process", "all"])
    ap.add_argument("--topico", default="tania_bulhoes", help="nome do tópico -> lê config/<topico>.yaml")
    ap.add_argument("--fonte", default="all", choices=["all", *FONTES_VALIDAS],
                     help="qual fonte rodar (padrão: todas as marcadas ativo:true no config)")
    ap.add_argument("--no-resume", action="store_true")
    args = ap.parse_args()

    cfg_path = Path("config") / f"{args.topico}.yaml"
    if not cfg_path.exists():
        sys.exit(f"{cfg_path} não existe. Tópicos disponíveis: "
                  + ", ".join(p.stem for p in Path("config").glob("*.yaml")))
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))

    fontes = _fontes_ativas(cfg, args.fonte)
    print(f"Tópico: {cfg['topico']} | fontes: {', '.join(fontes)}")

    if args.etapa in ("collect", "all"):
        for fonte in fontes:
            print(f"\n=== coleta: {fonte} ===")
            _coletar_fonte(fonte, cfg, retomar=not args.no_resume)

    if args.etapa in ("process", "all"):
        for fonte in fontes:
            print(f"\n=== processamento: {fonte} ===")
            _processar_fonte(fonte, cfg)


if __name__ == "__main__":
    main()
