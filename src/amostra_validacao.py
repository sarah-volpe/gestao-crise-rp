"""Amostra estratificada para validação manual do léxico de sentimento.

Sorteia até N posts por classe (positivo/negativo/neutro) da tabela
processada e gera um CSV para você preencher, na coluna `sentimento_manual`,
o que julgar ser o sentimento real do post (positivo, negativo ou neutro).
Depois, rode com `medir` para comparar com o que o léxico previu e ver a
taxa de acerto real — é o número que vai no método do TCC, não uma taxa
estimada de cabeça.

Uso:
  python src\\amostra_validacao.py gerar --n-por-classe 30
  # preencha a coluna sentimento_manual no CSV gerado
  python src\\amostra_validacao.py medir
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml

import paths

CLASSES = ["positivo", "negativo", "neutro"]


def gerar(cfg: dict, fonte: str, n_por_classe: int, seed: int) -> Path:
    out_dir = paths.processed_dir(fonte, cfg["topico"])
    basename = cfg["saida"].get("basename", cfg["topico"])
    csv_path = out_dir / f"{basename}.csv"
    if not csv_path.exists():
        raise SystemExit(f"{csv_path} não existe. Rode primeiro: python src\\run_pipeline.py process")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    partes = []
    for classe in CLASSES:
        sub = df[df["classificacao_sentimento"] == classe]
        n = min(n_por_classe, len(sub))
        if n < n_por_classe:
            print(f"Aviso: só {n} posts disponíveis na classe '{classe}' (pedido {n_por_classe}).")
        partes.append(sub.sample(n=n, random_state=seed))

    amostra = pd.concat(partes).sample(frac=1, random_state=seed).reset_index(drop=True)
    amostra = amostra[["id", "data_post", "texto", "classificacao_sentimento",
                        "sentimento_evidencia", "url"]].copy()
    amostra["sentimento_manual"] = ""  # preencha: positivo / negativo / neutro

    dest = out_dir / f"{basename}_amostra_validacao.csv"
    amostra.to_csv(dest, index=False, encoding="utf-8-sig")
    print(f"\n{len(amostra)} posts sorteados -> {dest}")
    print("Preencha a coluna sentimento_manual (positivo/negativo/neutro) e rode:")
    print("  python src\\amostra_validacao.py medir")
    return dest


def medir(cfg: dict, fonte: str) -> None:
    out_dir = paths.processed_dir(fonte, cfg["topico"])
    basename = cfg["saida"].get("basename", cfg["topico"])
    dest = out_dir / f"{basename}_amostra_validacao.csv"
    if not dest.exists():
        raise SystemExit(f"{dest} não existe. Rode antes: python src\\amostra_validacao.py gerar")

    df = pd.read_csv(dest, encoding="utf-8-sig")
    df["sentimento_manual"] = df["sentimento_manual"].astype(str).str.strip().str.lower()

    faltando = (~df["sentimento_manual"].isin(CLASSES)).sum()
    if faltando:
        invalidos = sorted(set(df.loc[~df["sentimento_manual"].isin(CLASSES), "sentimento_manual"]) - {"", "nan"})
        print(f"Aviso: {faltando} linha(s) sem rótulo válido em sentimento_manual "
              f"(vazias ou fora de {CLASSES}{': ' + str(invalidos) if invalidos else ''}) — ignoradas.")
    df = df[df["sentimento_manual"].isin(CLASSES)]

    if df.empty:
        raise SystemExit("Nenhuma linha com sentimento_manual preenchido corretamente ainda.")

    acerto = (df["classificacao_sentimento"] == df["sentimento_manual"]).mean()
    print(f"\nAmostra avaliada: {len(df)} posts")
    print(f"Taxa de acerto geral do léxico: {acerto*100:.1f}%\n")

    print("Matriz de confusão (linha = previsto pelo léxico, coluna = rótulo manual):")
    print(pd.crosstab(df["classificacao_sentimento"], df["sentimento_manual"],
                       rownames=["previsto"], colnames=["manual"]))

    print("\nAcerto por classe real (recall — dos posts que você rotulou X, quanto % o léxico acertou):")
    for classe in CLASSES:
        sub = df[df["sentimento_manual"] == classe]
        if len(sub) == 0:
            continue
        rec = (sub["classificacao_sentimento"] == classe).mean()
        print(f"  {classe:9s}: {rec*100:5.1f}% ({len(sub)} posts)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Amostra e mede a taxa de acerto do léxico contra rotulagem manual.")
    ap.add_argument("acao", choices=["gerar", "medir"])
    ap.add_argument("--topico", default="tania_bulhoes", help="nome do tópico -> lê config/<topico>.yaml")
    ap.add_argument("--fonte", default="twitter", choices=["twitter", "reddit"])
    ap.add_argument("--n-por-classe", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    cfg_path = Path("config") / f"{args.topico}.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    if args.acao == "gerar":
        gerar(cfg, args.fonte, args.n_por_classe, args.seed)
    else:
        medir(cfg, args.fonte)


if __name__ == "__main__":
    main()
