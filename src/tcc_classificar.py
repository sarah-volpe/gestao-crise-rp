"""Classificação de sentimento do TCC com o prompt literal de cada caso.

Desenho (o que vai para o método):
  - o modelo recebe SÓ `id;texto`: sem data, fase, autor nem engajamento;
  - lotes de até 50 posts, montados após embaralhar a base com semente
    fixa, para que um lote não seja só de um dia/fase (o contexto de posts
    vizinhos poderia contaminar a leitura);
  - o prompt é gerado da ficha do caso (src/tcc_prompts.py) em
    metodologia/prompts_gerados/<caso>_analise.md, idêntico ao do apêndice; o hash
    SHA-256 dele fica registrado com cada resposta;
  - saída validada: id existente no lote, classes e eixos permitidos,
    ironia sim/nao, confiança alta/media/baixa. Linhas inválidas ou ausentes
    voltam para um novo lote (até 2 retentativas) e o número da tentativa
    fica registrado;
  - cache por (id, hash do prompt, modelo): rodar de novo não paga de novo.

Provedores (--provider):
  anthropic  API da Anthropic (ANTHROPIC_API_KEY). Modelo padrão: claude-sonnet-5-5.
  zai        Z.ai/GLM gratuito com rate limit (ZAI_API_KEY, pip install openai).
  manual     custo zero de API: grava cada lote em um .txt para colar no Claude
             (chat), e lê a resposta que você salvar ao lado. Rode de novo
             depois de salvar as respostas.

Uso:
  python src/tcc_classificar.py --caso tania_bulhoes --provider manual
  python src/tcc_classificar.py --caso tania_bulhoes --provider anthropic
  python src/tcc_classificar.py --caso colgate --provider anthropic --modelo claude-haiku-5-5
  python src/tcc_classificar.py --caso tania_bulhoes --estimar
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcc_protocolo as proto  # noqa: E402

CONFIANCAS = {"alta", "media", "baixa"}
SAIDA_COLS = ["id", "sentimento", "eixo_tematico", "ironia", "confianca", "justificativa"]
PADRAO_MODELO = {"anthropic": "claude-sonnet-5-5", "zai": "glm-4.5-flash", "manual": "manual"}


def _sem_acento(s: str) -> str:
    return (s.lower().strip().replace("é", "e").replace("ê", "e").replace("ã", "a")
            .replace("á", "a").replace("í", "i").replace("ó", "o").replace("ú", "u"))


def montar_prompt(template: str, lote: pd.DataFrame) -> str:
    linhas = "\n".join(f"{r.id};{' '.join(str(r.texto_integral).split())}" for r in lote.itertuples())
    return template.replace("{{POSTS}}", linhas)


def parse_resposta(texto: str, ids_lote: set[str], sentimentos: set[str], eixos: set[str]) -> tuple[dict, list[str]]:
    """Devolve ({id: linha válida}, [problemas])."""
    validos: dict[str, dict] = {}
    problemas: list[str] = []
    for bruto in texto.splitlines():
        ln = bruto.strip().strip("`").strip()
        if not ln or ln.lower().startswith("id;") or ";" not in ln:
            continue
        partes = [p.strip().strip('"') for p in ln.split(";", 5)]
        if len(partes) < 6:
            problemas.append(f"colunas faltando: {ln[:60]}")
            continue
        pid, sent, eixo, ironia, conf, just = partes
        if pid not in ids_lote:
            problemas.append(f"id fora do lote: {pid}")
            continue
        sent, eixo = _sem_acento(sent), _sem_acento(eixo)
        ironia, conf = _sem_acento(ironia), _sem_acento(conf)
        erros = []
        if sent not in sentimentos:
            erros.append(f"sentimento '{sent}'")
        if eixo not in eixos:
            erros.append(f"eixo '{eixo}'")
        if ironia not in {"sim", "nao"}:
            erros.append(f"ironia '{ironia}'")
        if conf not in CONFIANCAS:
            erros.append(f"confianca '{conf}'")
        if erros:
            problemas.append(f"{pid}: " + ", ".join(erros))
            continue
        if pid in validos:
            problemas.append(f"{pid}: repetido (mantida a 1a linha)")
            continue
        validos[pid] = {"id": pid, "sentimento": sent, "eixo_tematico": eixo, "ironia": ironia,
                        "confianca": conf, "justificativa": just}
    return validos, problemas


class Chamador:
    def __init__(self, provider: str, modelo: str):
        self.provider, self.modelo = provider, modelo
        if provider == "anthropic":
            import anthropic
            self.client = anthropic.Anthropic(timeout=180.0)
        elif provider == "zai":
            from openai import OpenAI
            key = os.environ.get("ZAI_API_KEY") or sys.exit("Falta ZAI_API_KEY no ambiente.")
            self.client = OpenAI(api_key=key, base_url="https://api.z.ai/api/paas/v4/", timeout=180.0)

    def __call__(self, prompt: str) -> str:
        for tentativa in range(1, 4):
            try:
                if self.provider == "anthropic":
                    kw = dict(model=self.modelo, max_tokens=6000,
                              messages=[{"role": "user", "content": prompt}])
                    try:
                        r = self.client.messages.create(temperature=0, **kw)
                    except Exception as exc:  # alguns modelos não aceitam temperature
                        if "temperature" not in str(exc):
                            raise
                        r = self.client.messages.create(**kw)
                    return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
                r = self.client.chat.completions.create(
                    model=self.modelo, temperature=0, messages=[{"role": "user", "content": prompt}])
                return r.choices[0].message.content or ""
            except Exception as exc:
                espera = (100 if "429" in str(exc) or "RateLimit" in type(exc).__name__ else 10) * tentativa
                print(f"  !! {type(exc).__name__}: {exc} — nova tentativa em {espera}s", flush=True)
                if tentativa == 3:
                    raise
                time.sleep(espera)
        return ""


def classificar(caso: str, provider: str, modelo: str | None, estimar: bool) -> None:
    cfg = proto.carregar(caso)
    ccfg = cfg["classificacao"]
    modelo = modelo or PADRAO_MODELO[provider]
    from tcc_prompts import gerar as gerar_prompts
    gerar_prompts(caso)  # o prompt sempre reflete a ficha atual do caso
    template = Path(ccfg["prompt"]).read_text(encoding="utf-8")
    sha = hashlib.sha256(template.encode("utf-8")).hexdigest()
    sentimentos, eixos = set(ccfg["sentimentos"]), set(ccfg["eixos"])
    tam = int(ccfg.get("lote", 50))
    seed = int(cfg["coleta"].get("seed", 2025))

    out = proto.tcc_dir(caso)
    posts = pd.read_csv(out / f"{caso}_posts.csv", sep=";", encoding="utf-8-sig", dtype=str)
    pasta = out / "classificacao"
    pasta.mkdir(exist_ok=True)
    cache_path = pasta / "cache.jsonl"

    # cada post é identificado também pelo hash do texto enviado: se a montagem
    # for refeita e um id passar a apontar para outro post, o cache não vale
    posts["texto_sha1"] = posts["texto_integral"].fillna("").map(
        lambda t: hashlib.sha1(" ".join(t.split()).encode("utf-8")).hexdigest())
    sha_por_id = dict(zip(posts["id"], posts["texto_sha1"]))
    cache: dict[str, dict] = {}
    if cache_path.exists():
        for ln in cache_path.read_text(encoding="utf-8").splitlines():
            r = json.loads(ln)
            if (r["prompt_sha256"] == sha and r["modelo"] == modelo
                    and sha_por_id.get(r["id"]) == r.get("texto_sha1")):
                cache[r["id"]] = r

    if estimar:
        n_lotes = -(-len(posts) // tam)
        chars = len(template) * n_lotes + posts["texto_integral"].str.len().sum()
        print(f"{len(posts)} posts, {n_lotes} lotes de até {tam}. Já no cache: {len(cache)}.")
        print(f"Entrada estimada: ~{chars / 3.5 / 1000:.0f} mil tokens; saída: ~{len(posts) * 30 / 1000:.0f} mil tokens.")
        return

    chamar = None if provider == "manual" else Chamador(provider, modelo)
    por_id = posts.set_index("id")
    log: list[dict] = []

    # Manifesto: a composição dos lotes é sorteada uma vez e fica fixa entre
    # execuções (essencial no modo manual, em que as respostas chegam aos poucos).
    man_path = pasta / f"lotes_{modelo}_{sha[:8]}.json"
    manifesto = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {"lotes": []}
    no_manifesto = {i for l in manifesto["lotes"] for i in l["ids"]}
    if manifesto["lotes"] and (no_manifesto != set(posts["id"])
                               or manifesto.get("texto_sha1") != sha_por_id):
        arq = pasta / f"arquivado_{datetime.now():%Y%m%d_%H%M%S}"
        arq.mkdir()
        for f in list(pasta.glob("t*_lote*.txt")) + [man_path]:
            f.rename(arq / f.name)
        print(f"A base de posts mudou desde o último sorteio de lotes: lotes antigos movidos para {arq}. "
              "O que já foi classificado continua no cache.")
        manifesto = {"lotes": []}

    def novos_lotes(tentativa: int) -> None:
        manifesto["texto_sha1"] = sha_por_id
        pend = [i for i in posts["id"] if i not in cache]
        random.Random(seed + tentativa).shuffle(pend)
        for k in range(0, len(pend), tam):
            manifesto["lotes"].append({"nome": f"t{tentativa}_lote{k // tam + 1:03d}",
                                       "tentativa": tentativa, "ids": pend[k:k + tam]})
        man_path.write_text(json.dumps(manifesto, ensure_ascii=False, indent=1), encoding="utf-8")

    if not manifesto["lotes"]:
        novos_lotes(0)

    lidos: set[str] = set()
    while True:
        aguardando = False
        for lote in manifesto["lotes"]:
            nome, ids = lote["nome"], lote["ids"]
            resp_path = pasta / f"{nome}_resposta.txt"
            if nome in lidos or all(i in cache for i in ids):
                continue
            prompt = montar_prompt(template, por_id.loc[ids].reset_index())
            if provider == "manual":
                (pasta / f"{nome}_prompt.txt").write_text(prompt, encoding="utf-8")
                if not resp_path.exists():
                    aguardando = True
                    continue
                resposta = resp_path.read_text(encoding="utf-8")
            elif resp_path.exists():
                resposta = resp_path.read_text(encoding="utf-8")
            else:
                print(f"  {nome}: {len(ids)} posts…", flush=True)
                resposta = chamar(prompt)
                resp_path.write_text(resposta, encoding="utf-8")
            lidos.add(nome)

            validos, problemas = parse_resposta(resposta, set(ids), sentimentos, eixos)
            agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
            with cache_path.open("a", encoding="utf-8") as fh:
                for r in validos.values():
                    if r["id"] in cache:
                        continue
                    r.update(prompt_sha256=sha, texto_sha1=sha_por_id[r["id"]], modelo=modelo, provider=provider,
                             lote=nome, tentativa=lote["tentativa"], classificado_em=agora)
                    cache[r["id"]] = r
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            faltando = sum(i not in cache for i in ids)
            log.append({"lote": nome, "posts": len(ids), "validos": len(ids) - faltando,
                        "faltando_ou_invalidos": faltando, "problemas": problemas[:20]})
            if faltando:
                print(f"    {nome}: {faltando} sem resposta válida. {problemas[:3]}")

        ultima = max(l["tentativa"] for l in manifesto["lotes"])
        restam = [i for i in posts["id"] if i not in cache]
        if aguardando or not restam or ultima >= 2:
            break
        print(f"Retentativa {ultima + 1}: {len(restam)} posts em lote novo.")
        novos_lotes(ultima + 1)

    faltam = posts[~posts["id"].isin(cache)]
    if provider == "manual" and len(faltam):
        print(f"\nModo manual: {len(faltam)} posts aguardando resposta.\n"
              f"Abra cada *_prompt.txt em {pasta}/, cole no Claude, salve a resposta como "
              f"<mesmo nome>_resposta.txt e rode este comando de novo.")

    res = pd.DataFrame([cache[i] for i in posts["id"] if i in cache])
    if res.empty:
        return
    res[SAIDA_COLS].to_csv(out / f"{caso}_classificacao.csv", sep=";", index=False, encoding="utf-8-sig")
    longas = int((res["justificativa"].str.split().str.len() > 15).sum())
    meta = {
        "caso": caso, "provider": provider, "modelo": modelo, "prompt": ccfg["prompt"],
        "prompt_sha256": sha, "tamanho_lote": tam, "semente_embaralhamento": seed,
        "posts": len(posts), "classificados": len(res), "sem_classificacao": len(faltam),
        "classificados_em_retentativa": int((res["tentativa"] > 0).sum()),
        "justificativas_acima_de_15_palavras": longas,
        "distribuicao_sentimento": res["sentimento"].value_counts().to_dict(),
        "distribuicao_eixo": res["eixo_tematico"].value_counts().to_dict(),
        "primeira_classificacao": res["classificado_em"].min(),
        "ultima_classificacao": res["classificado_em"].max(),
        "lotes_desta_execucao": log,
    }
    (out / f"{caso}_classificacao_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                                        encoding="utf-8")
    print(f"\n{len(res)}/{len(posts)} classificados -> {out / f'{caso}_classificacao.csv'}")
    print(json.dumps(meta["distribuicao_sentimento"], ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser(description="Classificação de sentimento do protocolo do TCC.")
    ap.add_argument("--caso", required=True, choices=proto.casos_disponiveis())
    ap.add_argument("--provider", choices=["anthropic", "zai", "manual"], default="manual")
    ap.add_argument("--modelo")
    ap.add_argument("--estimar", action="store_true", help="só mostra nº de lotes e tokens estimados")
    a = ap.parse_args()
    classificar(a.caso, a.provider, a.modelo, a.estimar)


if __name__ == "__main__":
    main()
