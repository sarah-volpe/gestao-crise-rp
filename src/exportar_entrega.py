"""Gera os artefatos da primeira entrega do TCC a partir da tabela processada.

Lê data/processed/<basename>.csv (gerado por `run_pipeline.py process`) e produz:

  <basename>_tabela_simples.csv     data do post, texto, classificação de sentimento
  <basename>_sentimento_diario.png  linha do tempo: sentimento médio por dia

Uso:
  python src\\exportar_entrega.py --topico tania_bulhoes --fonte twitter
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import yaml

import paths

# cores do par divergente (dataviz skill): score de sentimento é uma medida
# de polaridade em torno de zero, não uma categoria — por isso divergente
# (azul/vermelho), não uma cor categórica por rótulo.
COR_POSITIVO = "#2a78d6"
COR_NEGATIVO = "#e34948"
COR_ZERO = "#c3c2b7"      # baseline/axis
COR_GRADE = "#e1e0d9"     # gridline hairline
COR_TEXTO = "#0b0b0b"     # tinta primária
COR_TEXTO_SEC = "#52514e"  # tinta secundária
COR_EIXO = "#898781"      # muted (eixo/labels)
COR_SUPERFICIE = "#fcfcfb"


def gerar_tabela_simples(df: pd.DataFrame, dest: Path) -> Path:
    simples = df[["data_post", "texto", "classificacao_sentimento"]].copy()
    simples = simples.sort_values("data_post")
    simples.columns = ["data do post", "texto", "sentimento"]

    if dest.suffix == ".xlsx":
        from openpyxl.styles import Alignment

        with pd.ExcelWriter(dest, engine="openpyxl") as xw:
            simples.to_excel(xw, sheet_name="posts", index=False)
            ws = xw.sheets["posts"]
            ws.column_dimensions["A"].width = 14
            ws.column_dimensions["B"].width = 100
            ws.column_dimensions["C"].width = 14
            for row in ws.iter_rows(min_row=2, max_col=2, max_row=ws.max_row):
                row[1].alignment = Alignment(wrap_text=True, vertical="top")
    else:
        simples.to_csv(dest, index=False, encoding="utf-8-sig")
    return dest


def gerar_grafico_temporal(df: pd.DataFrame, dest: Path, titulo: str, granularidade: str = "semana") -> Path:
    serie = df.assign(data_post=pd.to_datetime(df["data_post"]))

    if granularidade == "semana":
        # semana ISO (segunda a domingo), rotulada pelo primeiro dia da semana
        serie["bucket"] = serie["data_post"].dt.to_period("W-MON").apply(lambda p: p.start_time)
    else:
        serie["bucket"] = serie["data_post"]

    agregado = (
        serie.groupby("bucket")["sentimento_score"]
        .mean()
        .reset_index()
        .sort_values("bucket")
    )

    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=150)
    fig.patch.set_facecolor(COR_SUPERFICIE)
    ax.set_facecolor(COR_SUPERFICIE)

    x = agregado["bucket"]
    y = agregado["sentimento_score"]

    ax.fill_between(x, y, 0, where=(y >= 0), color=COR_POSITIVO, alpha=0.18,
                     interpolate=True, linewidth=0, zorder=2)
    ax.fill_between(x, y, 0, where=(y <= 0), color=COR_NEGATIVO, alpha=0.18,
                     interpolate=True, linewidth=0, zorder=2)
    ax.plot(x, y, color=COR_TEXTO, linewidth=2, solid_capstyle="round",
            marker="o", markersize=4, markerfacecolor=COR_SUPERFICIE,
            markeredgecolor=COR_TEXTO, markeredgewidth=1.5, zorder=3)
    ax.axhline(0, color=COR_ZERO, linewidth=1, zorder=1)

    ax.set_ylim(-1, 1)
    ax.set_ylabel("sentimento médio (score -1 a +1)", color=COR_TEXTO_SEC, fontsize=9)
    ax.set_title(titulo, color=COR_TEXTO, fontsize=12, loc="left", pad=12)

    ax.grid(axis="y", color=COR_GRADE, linewidth=0.8, zorder=0)
    ax.grid(False, axis="x")
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(COR_EIXO)
    ax.tick_params(colors=COR_EIXO, labelsize=8)

    if granularidade == "semana":
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0, interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    else:
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    fig.autofmt_xdate(rotation=45, ha="right")

    ax.text(0.01, 0.96, "positivo", transform=ax.transAxes, color=COR_POSITIVO,
             fontsize=8, va="top")
    ax.text(0.01, 0.05, "negativo", transform=ax.transAxes, color=COR_NEGATIVO,
             fontsize=8, va="bottom")

    fig.tight_layout()
    fig.savefig(dest, facecolor=fig.get_facecolor())
    plt.close(fig)
    return dest


def main() -> None:
    ap = argparse.ArgumentParser(description="Gera a tabela simples e o gráfico da 1a entrega.")
    ap.add_argument("--topico", default="tania_bulhoes", help="nome do tópico -> lê config/<topico>.yaml")
    ap.add_argument("--fonte", default="twitter", choices=["twitter", "reddit"])
    ap.add_argument("--granularidade", choices=["semana", "dia"], default="semana",
                     help="agregação do gráfico de sentimento médio (padrão: semana)")
    args = ap.parse_args()

    cfg_path = Path("config") / f"{args.topico}.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    out_dir = paths.processed_dir(args.fonte, cfg["topico"])
    basename = cfg["saida"].get("basename", cfg["topico"])
    csv_path = out_dir / f"{basename}.csv"
    if not csv_path.exists():
        raise SystemExit(f"{csv_path} não existe. Rode primeiro: "
                          f"python src\\run_pipeline.py process --topico {args.topico} --fonte {args.fonte}")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    gerar_tabela_simples(df, out_dir / f"{basename}_tabela_simples.csv")
    tabela_path = gerar_tabela_simples(df, out_dir / f"{basename}_tabela_simples.xlsx")
    rotulo = "semana" if args.granularidade == "semana" else "dia"
    titulo = f"Sentimento médio por {rotulo} — {cfg['topico']} ({args.fonte})"
    sufixo = "semanal" if args.granularidade == "semana" else "diario"
    grafico_path = gerar_grafico_temporal(
        df, out_dir / f"{basename}_sentimento_{sufixo}.png", titulo, args.granularidade
    )

    print(f"Tabela simples -> {tabela_path} ({len(df)} posts)")
    print(f"Gráfico {rotulo:<7} -> {grafico_path}")


if __name__ == "__main__":
    main()
