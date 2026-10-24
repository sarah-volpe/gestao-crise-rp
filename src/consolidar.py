"""Consolida os tópicos e fontes já processados numa tabela única + análises
comparativas.

Junta `data/processed/<fonte>/<topico>/<basename>.csv` de toda combinação
tópico x fonte que já tenha passado por `run_pipeline.py process`. Não roda o
processamento sozinho — combinações com bruto coletado mas ainda não
processadas (em especial as que usam `sentimento.metodo: llm`, que podem
levar horas) só são reportadas como ausentes; rode
`python src\\run_pipeline.py process --topico <t> --fonte <f>` primeiro.

Gera em `data/processed/combined/geral/`:

  consolidado.csv / consolidado.xlsx
    aba posts               tabela única com colunas topico/fonte + todas as
                             colunas do entregável por tópico
    aba resumo_geral         total de posts, distribuição de sentimento e
                             engajamento médio por topico x fonte
    aba distribuicao_sentimento  mesma distribuição em formato longo
                             (topico, fonte, sentimento, posts, percentual)
    aba volume_diario        contagem de posts por dia, por topico x fonte
    aba por_eixo              sentimento por eixo temático, por tópico
                             (eixos são específicos de cada tópico, não se
                             misturam entre tania_bulhoes e american_eagle)
    aba top_engajamento       50 posts de maior engajamento no total combinado

  sentimento_por_topico.png
    barras: distribuição percentual de sentimento por tópico

  volume_por_dia_da_crise.png
    linha: posts por dia desde o início do período configurado de cada
    tópico — compara a curva de repercussão das duas crises mesmo com
    janelas de calendário diferentes

Uso:
  python src\\consolidar.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

FONTES = ("twitter", "reddit")

COR_POSITIVO = "#2a78d6"
COR_NEGATIVO = "#e34948"
COR_NEUTRO = "#898781"
COR_GRADE = "#e1e0d9"
COR_TEXTO = "#0b0b0b"
COR_TEXTO_SEC = "#52514e"
COR_EIXO = "#898781"
COR_SUPERFICIE = "#fcfcfb"
PALETA_TOPICO = ["#2a78d6", "#eb6834"]  # slots 1/2 do tema categórico


def listar_topicos() -> list[str]:
    return sorted(p.stem for p in Path("config").glob("*.yaml"))


def carregar_cfg(topico: str) -> dict:
    return yaml.safe_load((Path("config") / f"{topico}.yaml").read_text(encoding="utf-8"))


def buscar_processado(fonte: str, topico: str, cfg: dict) -> Path | None:
    basename = cfg.get("saida", {}).get("basename", topico)
    csv_path = paths.processed_dir(fonte, topico) / f"{basename}.csv"
    if csv_path.exists():
        return csv_path

    raw = paths.raw_root(fonte, topico)
    if raw.exists() and list(raw.glob("*/posts.jsonl")):
        print(f"[{topico}/{fonte}] bruto coletado mas ainda não processado — "
              f"rode: python src\\run_pipeline.py process --topico {topico} --fonte {fonte}")
    return None


def carregar_tudo() -> pd.DataFrame:
    partes = []
    for topico in listar_topicos():
        cfg = carregar_cfg(topico)
        for fonte in FONTES:
            if fonte not in cfg.get("fontes", {}):
                continue
            csv_path = buscar_processado(fonte, topico, cfg)
            if csv_path is None:
                continue
            df = pd.read_csv(csv_path, encoding="utf-8-sig")
            df.insert(0, "fonte", fonte)
            df.insert(0, "topico", topico)
            partes.append(df)
            print(f"[{topico}/{fonte}] {len(df)} posts carregados.")

    if not partes:
        sys.exit("Nenhuma combinação tópico/fonte processada encontrada.")

    return pd.concat(partes, ignore_index=True, sort=False)


def resumo_geral(df: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for (topico, fonte), grupo in df.groupby(["topico", "fonte"]):
        total = len(grupo)
        dist = grupo["classificacao_sentimento"].value_counts(normalize=True) * 100
        linhas.append({
            "topico": topico,
            "fonte": fonte,
            "total_posts": total,
            "pct_positivo": round(dist.get("positivo", 0.0), 1),
            "pct_negativo": round(dist.get("negativo", 0.0), 1),
            "pct_neutro": round(dist.get("neutro", 0.0), 1),
            "engajamento_medio": round(grupo["engajamento_total"].mean(), 1),
            "periodo_inicio": grupo["data_post"].min(),
            "periodo_fim": grupo["data_post"].max(),
        })
    return pd.DataFrame(linhas).sort_values(["topico", "fonte"])


def distribuicao_sentimento(df: pd.DataFrame) -> pd.DataFrame:
    agg = (
        df.groupby(["topico", "fonte", "classificacao_sentimento"])
        .size()
        .rename("posts")
        .reset_index()
    )
    agg["percentual"] = (
        agg["posts"] / agg.groupby(["topico", "fonte"])["posts"].transform("sum") * 100
    ).round(1)
    return agg.sort_values(["topico", "fonte", "classificacao_sentimento"])


def volume_diario(df: pd.DataFrame) -> pd.DataFrame:
    agg = df.groupby(["topico", "fonte", "data_post"]).size().rename("posts").reset_index()
    return agg.sort_values(["topico", "fonte", "data_post"])


def por_eixo(df: pd.DataFrame) -> pd.DataFrame:
    agg = (
        df.groupby(["topico", "eixo_principal", "classificacao_sentimento"])
        .size()
        .rename("posts")
        .reset_index()
    )
    return agg.sort_values(["topico", "posts"], ascending=[True, False])


def top_engajamento(df: pd.DataFrame, n: int = 50) -> pd.DataFrame:
    cols = ["topico", "fonte", "data_post", "autor_usuario", "engajamento_total",
            "classificacao_sentimento", "eixo_principal", "texto", "url"]
    cols = [c for c in cols if c in df.columns]
    return df.nlargest(n, "engajamento_total")[cols]


def exportar_tabelas(df: pd.DataFrame, dest_dir: Path) -> None:
    csv_path = dest_dir / "consolidado.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"CSV consolidado -> {csv_path} ({len(df)} posts)")

    xlsx_path = dest_dir / "consolidado.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as xw:
        df.to_excel(xw, sheet_name="posts", index=False)
        resumo_geral(df).to_excel(xw, sheet_name="resumo_geral", index=False)
        distribuicao_sentimento(df).to_excel(xw, sheet_name="distribuicao_sentimento", index=False)
        volume_diario(df).to_excel(xw, sheet_name="volume_diario", index=False)
        por_eixo(df).to_excel(xw, sheet_name="por_eixo", index=False)
        top_engajamento(df).to_excel(xw, sheet_name="top_engajamento", index=False)
    print(f"XLSX consolidado -> {xlsx_path} (6 abas)")


def _estilo_eixos(ax) -> None:
    ax.grid(axis="y", color=COR_GRADE, linewidth=0.8, zorder=0)
    ax.grid(False, axis="x")
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(COR_EIXO)
    ax.tick_params(colors=COR_EIXO, labelsize=8)


def grafico_sentimento_por_topico(df: pd.DataFrame, dest: Path) -> Path:
    dist = (
        df.groupby(["topico", "classificacao_sentimento"])
        .size()
        .rename("posts")
        .reset_index()
    )
    dist["percentual"] = dist["posts"] / dist.groupby("topico")["posts"].transform("sum") * 100

    topicos = sorted(dist["topico"].unique())
    sentimentos = ["positivo", "neutro", "negativo"]
    cores = {"positivo": COR_POSITIVO, "neutro": COR_NEUTRO, "negativo": COR_NEGATIVO}

    x = np.arange(len(topicos))
    largura = 0.25

    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=150)
    fig.patch.set_facecolor(COR_SUPERFICIE)
    ax.set_facecolor(COR_SUPERFICIE)

    for j, s in enumerate(sentimentos):
        vals = [
            dist.loc[(dist["topico"] == t) & (dist["classificacao_sentimento"] == s), "percentual"].sum()
            for t in topicos
        ]
        deslocamento = (j - 1) * largura
        barras = ax.bar(x + deslocamento, vals, largura, label=s.capitalize(),
                         color=cores[s], zorder=2)
        for b, v in zip(barras, vals):
            if v > 0:
                ax.text(b.get_x() + b.get_width() / 2, v + 1.2, f"{v:.0f}%",
                        ha="center", va="bottom", fontsize=8, color=COR_TEXTO_SEC)

    ax.set_xticks(x)
    ax.set_xticklabels(topicos, fontsize=9)
    ax.set_ylabel("% dos posts", color=COR_TEXTO_SEC, fontsize=9)
    ax.set_ylim(0, dist["percentual"].max() + 15)
    ax.set_title("Distribuição de sentimento por tópico", color=COR_TEXTO, fontsize=12, loc="left", pad=12)

    _estilo_eixos(ax)
    ax.legend(loc="upper right", frameon=False, fontsize=8, labelcolor=COR_TEXTO_SEC)

    fig.tight_layout()
    fig.savefig(dest, facecolor=fig.get_facecolor())
    plt.close(fig)
    return dest


def grafico_volume_por_dia(df: pd.DataFrame, cfgs: dict[str, dict], dest: Path) -> Path:
    tmp = df.copy()
    tmp["data_post"] = pd.to_datetime(tmp["data_post"])
    tmp["inicio_periodo"] = tmp["topico"].map(lambda t: pd.Timestamp(cfgs[t]["periodo"]["since"]))
    tmp["dia_relativo"] = (tmp["data_post"] - tmp["inicio_periodo"]).dt.days

    serie = tmp.groupby(["topico", "dia_relativo"]).size().rename("posts").reset_index()
    topicos = sorted(serie["topico"].unique())

    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=150)
    fig.patch.set_facecolor(COR_SUPERFICIE)
    ax.set_facecolor(COR_SUPERFICIE)

    for cor, topico in zip(PALETA_TOPICO, topicos):
        s = serie[serie["topico"] == topico].sort_values("dia_relativo")
        ax.plot(s["dia_relativo"], s["posts"], color=cor, linewidth=2,
                solid_capstyle="round", label=topico, zorder=3)
        ax.text(s["dia_relativo"].iloc[-1] + 1, s["posts"].iloc[-1], topico,
                color=cor, fontsize=8, va="center")

    ax.set_xlabel("dias desde o início do período configurado", color=COR_TEXTO_SEC, fontsize=9)
    ax.set_ylabel("posts no dia", color=COR_TEXTO_SEC, fontsize=9)
    ax.set_title("Volume de posts por dia da crise — comparação entre tópicos",
                 color=COR_TEXTO, fontsize=12, loc="left", pad=12)

    _estilo_eixos(ax)
    ax.legend(loc="upper right", frameon=False, fontsize=8, labelcolor=COR_TEXTO_SEC)

    fig.tight_layout()
    fig.savefig(dest, facecolor=fig.get_facecolor())
    plt.close(fig)
    return dest


def main() -> None:
    dest_dir = paths.combined_geral_dir()
    df = carregar_tudo()
    exportar_tabelas(df, dest_dir)

    cfgs = {t: carregar_cfg(t) for t in df["topico"].unique()}
    g1 = grafico_sentimento_por_topico(df, dest_dir / "sentimento_por_topico.png")
    g2 = grafico_volume_por_dia(df, cfgs, dest_dir / "volume_por_dia_da_crise.png")
    print(f"Gráfico -> {g1}")
    print(f"Gráfico -> {g2}")

    print("\n--- Resumo geral ---")
    print(resumo_geral(df).to_string(index=False))


if __name__ == "__main__":
    main()
