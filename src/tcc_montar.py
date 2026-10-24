"""Monta as tabelas do TCC a partir do bruto coletado (tcc_coletar.py).

Passos, na ordem:
  1. data e fase de cada post pela hora real de publicação em Brasília;
  2. exclusões objetivas: fora das fases, anúncio (promovido), retuíte,
     publicação da própria marca (contas_oficiais da ficha), idioma diferente de pt, texto vazio, complementar fora das fases dela;
  3. deduplicação por id do post (se veio nas duas buscas, fica "principal");
  4. volume do dia = posts únicos válidos que a busca retornou;
  5. amostra: até `max_por_dia` posts por dia e por origem, sorteados com
     semente fixa (reprodutível); dias com menos posts entram inteiros;
  6. ids sequenciais (TB-001...), autores anonimizados (U001...) e link
     sem o @ do autor (https://x.com/i/status/<id>).

Exclusões que dependem de leitura (spam, loja revendendo sem opinião,
homônimo) NÃO são feitas aqui: elas são a classe `fora_do_tema` da
classificação, para ficarem auditáveis.

Saídas em dados/<caso>/:
  <caso>_posts.csv              tabela 1 do protocolo (vai para o trabalho; com texto, fora do git)
  <caso>_posts_publico.csv      a mesma tabela sem o texto (vai para o repositório público)
  <caso>_volume_diario.csv      tabela 2 do protocolo (vai para o trabalho)
  <caso>_volume_detalhado.csv   volume por origem, limite atingido, buscas feitas
  <caso>_auditoria.csv          hora exata, texto possivelmente truncado, data da coleta
  <caso>_montagem.json          contagens de exclusão, semente, parâmetros
e em data/privado/ (NUNCA vai para o trabalho):
  <caso>_autores.csv            U001 -> @usuario

Uso:
  python src/tcc_montar.py --caso tania_bulhoes
  python src/tcc_montar.py --caso colgate --incluir-opcionais
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcc_protocolo as proto  # noqa: E402

TZ_BR = "America/Sao_Paulo"
ORIGENS = ("principal", "complementar")
COLUNAS_POSTS = ["id", "data", "fase", "origem", "link", "autor_anonimizado",
                 "texto_integral", "curtidas", "respostas", "reposts"]


def _carregar_bruto(caso: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    linhas, metas = [], []
    for origem in ORIGENS:
        d = proto.RAW_ROOT / caso / origem
        for meta in sorted(d.glob("*.meta.json")):
            metas.append(json.loads(meta.read_text(encoding="utf-8")))
        for arq in sorted(d.glob("*.jsonl")):
            for ln in arq.read_text(encoding="utf-8").splitlines():
                if ln.strip():
                    linhas.append(json.loads(ln))
    if not linhas:
        sys.exit(f"Nenhum bruto em {proto.RAW_ROOT / caso}. Rode tcc_coletar.py antes.")
    return pd.DataFrame(linhas), pd.DataFrame(metas)


def _limpar_texto(t: str) -> str:
    """Só remove artefatos do innerText em coletas antigas (URL partida em
    linhas). Texto vindo do tcc_coletar.py já sai fiel e não muda aqui."""
    t = re.sub(r"(https?://)\n", r"\1", t)
    return t.strip()


def _mascarar(t: str, manter: set[str]) -> str:
    return re.sub(r"@(\w{1,15})", lambda m: m.group(0) if m.group(1).lower() in manter else "@usuario", t)


def montar(caso: str, incluir_opcionais: bool, mascarar_mencoes: bool) -> None:
    cfg = proto.carregar(caso)
    fases = proto.fases_ativas(cfg, incluir_opcionais)
    fases_comp = set((cfg.get("busca_complementar") or {}).get("fases") or [])
    col = cfg["coleta"]
    max_dia = int(col.get("max_por_dia", 15))
    seed = int(col.get("seed", 2025))

    df, metas = _carregar_bruto(caso)
    contagem: dict[str, int] = {"linhas_brutas": len(df)}

    df["dt_br"] = pd.to_datetime(df["created_at_utc"], utc=True, errors="coerce").dt.tz_convert(TZ_BR)
    df = df.dropna(subset=["dt_br"])
    df["data"] = df["dt_br"].dt.date
    df["fase"] = df["data"].map(lambda d: proto.fase_de(d, fases))

    def excluir(mask: pd.Series, motivo: str) -> None:
        nonlocal df
        contagem[f"excluido_{motivo}"] = int(mask.sum())
        df = df[~mask]

    excluir(df["fase"].isna(), "fora_das_fases")
    excluir(df.get("promovido", pd.Series(False, index=df.index)).fillna(False).astype(bool), "anuncio")
    excluir(df["is_retweet"].fillna(False).astype(bool), "retuite")
    oficiais = {h.lower().lstrip("@") for h in cfg.get("contas_oficiais") or []}
    excluir(df["author_handle"].fillna("").str.lower().isin(oficiais), "conta_oficial_da_marca")
    excluir(~df["lang"].fillna("").isin(["pt"]), "idioma_nao_pt")
    df["text"] = df["text"].fillna("").astype(str).map(_limpar_texto)
    excluir(df["text"].str.len() == 0, "texto_vazio")
    excluir((df["origem"] == "complementar") & ~df["fase"].isin(fases_comp), "complementar_fora_da_fase")

    antes = len(df)
    df["_ordem_origem"] = df["origem"].map({"principal": 0, "complementar": 1})
    df = df.sort_values(["_ordem_origem", "dt_br"]).drop_duplicates("id", keep="first")
    contagem["duplicados_entre_buscas"] = antes - len(df)
    contagem["posts_validos"] = len(df)

    # --- volume e amostra por dia e origem ---
    amostras = []
    for (d, origem), g in df.groupby(["data", "origem"]):
        n = min(max_dia, len(g))
        rs = seed + d.toordinal() * 2 + (origem == "complementar")
        amostras.append(g.sample(n=n, random_state=rs) if len(g) > n else g)
    am = pd.concat(amostras).sort_values(["dt_br", "id"]).reset_index(drop=True)

    largura = max(3, len(str(len(am))))
    am["id_tcc"] = [f"{cfg['prefixo_id']}-{i:0{largura}d}" for i in range(1, len(am) + 1)]
    autores = {h: f"U{i:03d}" for i, h in enumerate(dict.fromkeys(am["author_handle"].fillna("?")), 1)}
    am["autor_anonimizado"] = am["author_handle"].fillna("?").map(autores)

    texto = am["text"]
    if mascarar_mencoes:
        manter = {h.lower().lstrip("@") for h in re.findall(r"@\w+", cfg["busca_principal"])}
        texto = texto.map(lambda t: _mascarar(t, manter))

    posts = pd.DataFrame({
        "id": am["id_tcc"],
        "data": am["data"].astype(str),
        "fase": am["fase"],
        "origem": am["origem"],
        "link": "https://x.com/i/status/" + am["id"].astype(str),
        "autor_anonimizado": am["autor_anonimizado"],
        "texto_integral": texto,
        "curtidas": pd.to_numeric(am["likes"], errors="coerce").fillna(0).astype(int),
        "respostas": pd.to_numeric(am["replies"], errors="coerce").fillna(0).astype(int),
        "reposts": pd.to_numeric(am["retweets"], errors="coerce").fillna(0).astype(int),
    })[COLUNAS_POSTS]

    # --- volume diário: todos os dias das fases, inclusive os vazios ---
    metas["dia_utc"] = pd.to_datetime(metas["dia_utc"]).dt.date
    linhas_vol, linhas_det = [], []
    for f in fases:
        d = f.inicio
        while d <= f.fim:
            cobertura = {d, d + timedelta(days=1)}
            vol, amo, lim, feitas = {}, {}, False, []
            for origem in ORIGENS:
                if origem == "complementar" and f.nome not in fases_comp:
                    continue
                m = metas[(metas["origem"] == origem) & metas["dia_utc"].isin(cobertura)]
                feitas.append(f"{origem}:{len(m)}/2")
                lim = lim or bool(m["limite_atingido"].any())
                vol[origem] = int(((df["data"] == d) & (df["origem"] == origem)).sum())
                amo[origem] = int(((am["data"] == d) & (am["origem"] == origem)).sum())
            total_vol, total_amo = sum(vol.values()), sum(amo.values())
            completo = all(x.endswith("2/2") for x in feitas)
            if not completo:
                nada_feito = all(x.split(":")[1].startswith("0") for x in feitas)
                estimado = "nao_coletado" if nada_feito and total_vol == 0 else f"parcial ({total_vol})"
            else:
                estimado = f"mais de {total_vol}" if lim else str(total_vol)
            linhas_vol.append({"data": d.isoformat(), "fase": f.nome, "posts_coletados": total_amo,
                               "volume_estimado_no_dia": estimado})
            linhas_det.append({"data": d.isoformat(), "fase": f.nome,
                               "volume_principal": vol.get("principal", 0),
                               "volume_complementar": vol.get("complementar", ""),
                               "amostra_principal": amo.get("principal", 0),
                               "amostra_complementar": amo.get("complementar", ""),
                               "limite_atingido": lim, "buscas_feitas": " ".join(feitas)})
            d += timedelta(days=1)

    out = proto.tcc_dir(caso)
    kw = dict(sep=";", index=False, encoding="utf-8-sig")
    posts.to_csv(out / f"{caso}_posts.csv", **kw)
    # versão para o repositório público: sem o texto (que permite reidentificar o autor por busca)
    posts.drop(columns=["texto_integral"]).to_csv(out / f"{caso}_posts_publico.csv", **kw)
    pd.DataFrame(linhas_vol).to_csv(out / f"{caso}_volume_diario.csv", **kw)
    pd.DataFrame(linhas_det).to_csv(out / f"{caso}_volume_detalhado.csv", **kw)
    pd.DataFrame({
        "id": am["id_tcc"], "post_id": am["id"].astype(str),
        "data_hora_brasilia": am["dt_br"].dt.strftime("%Y-%m-%d %H:%M:%S"),
        "origem": am["origem"], "dia_utc_da_busca": am.get("busca_dia_utc"),
        "texto_possivelmente_truncado": am.get("texto_possivelmente_truncado", pd.Series(pd.NA, index=am.index)),
        "coleta_legada": am.get("coleta_legada", pd.Series(False, index=am.index)).fillna(False),
    }).to_csv(out / f"{caso}_auditoria.csv", **kw)

    priv = proto.privado_dir()
    nomes = am.drop_duplicates("author_handle").set_index("author_handle")["author_name"]
    pd.DataFrame([{"autor_anonimizado": u, "autor_usuario": "@" + h, "autor_nome": nomes.get(h, "")}
                  for h, u in autores.items()]).to_csv(priv / f"{caso}_autores.csv", **kw)

    coletas = metas["coletado_em"].dropna().astype(str)
    resumo = {
        "caso": caso, "fases": [f.nome for f in fases], "max_por_dia_por_origem": max_dia,
        "semente_sorteio": seed, "mascarar_mencoes": mascarar_mencoes,
        "coleta_de": coletas.min() if len(coletas) else None,
        "coleta_ate": coletas.max() if len(coletas) else None,
        **contagem, "posts_na_amostra": len(posts), "autores_distintos": len(autores),
        "amostra_por_fase": posts["fase"].value_counts().to_dict(),
        "amostra_por_origem": posts["origem"].value_counts().to_dict(),
        "dias_com_limite_atingido": int(sum(r["limite_atingido"] for r in linhas_det)),
    }
    (out / f"{caso}_montagem.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2, default=str),
                                               encoding="utf-8")
    print(json.dumps(resumo, ensure_ascii=False, indent=2, default=str))
    print(f"\nTabelas em {out}/  |  correspondência de autores em {priv}/ (fora do trabalho)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Monta as tabelas do protocolo do TCC.")
    ap.add_argument("--caso", required=True, choices=proto.casos_disponiveis())
    ap.add_argument("--incluir-opcionais", action="store_true")
    ap.add_argument("--mascarar-mencoes", action="store_true",
                    help="troca @menções a terceiros por @usuario no texto (mantém o @ da marca)")
    a = ap.parse_args()
    montar(a.caso, a.incluir_opcionais, a.mascarar_mencoes)


if __name__ == "__main__":
    main()
