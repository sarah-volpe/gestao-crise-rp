"""Reaproveita a coleta antiga (collect_x_scrape.py, grupo marca_ampla) como
busca principal do protocolo, para quando o X bloquear a coleta nova ou
para testar a montagem sem coletar.

Diferenças da coleta antiga que precisam ser declaradas se ela for usada:
  - a busca não tinha `lang:pt` nem `-filter:retweets` (a montagem filtra
    idioma pt e descarta retuítes, o que aproxima o resultado);
  - termos quase iguais (a antiga tinha também "tânia bulhoes");
  - texto via innerText: emojis perdidos e possíveis truncamentos sem aviso;
  - limite de 200 posts por dia.
Os registros recebem `coleta_legada: true` e aparecem na auditoria.
Nunca sobrescreve um dia já coletado pelo tcc_coletar.py.

Uso:
  python src/tcc_importar_legado.py --caso tania_bulhoes --topico-antigo tania_bulhoes
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcc_protocolo as proto  # noqa: E402

SINCE_RE = re.compile(r"since:(\d{4}-\d{2}-\d{2})")


def importar(caso: str, topico_antigo: str, limite_antigo: int) -> None:
    raiz = Path("data/raw/twitter") / topico_antigo
    por_dia: dict[str, list[dict]] = defaultdict(list)
    for arq in sorted(raiz.glob("*/posts.jsonl")):
        for ln in arq.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            r = json.loads(ln)
            if r.get("query_grupo") != "marca_ampla":
                continue
            m = SINCE_RE.search(r.get("query_texto", ""))
            if m:
                por_dia[m.group(1)].append(r)

    feitos: set[str] = set()
    ck = raiz / "checkpoint_queries.txt"
    if ck.exists():
        for q in ck.read_text(encoding="utf-8").splitlines():
            m = SINCE_RE.search(q)
            if m and " (" not in q.split(")", 1)[1][:3]:  # só a query ampla (sem modificador)
                feitos.add(m.group(1))
    feitos |= set(por_dia)

    destino = proto.raw_dir(caso, "principal")
    novos = 0
    for dia in sorted(feitos):
        meta = destino / f"{dia}.meta.json"
        if meta.exists():
            continue
        regs = {r["id"]: r for r in por_dia.get(dia, [])}.values()
        with (destino / f"{dia}.jsonl").open("w", encoding="utf-8") as fh:
            for r in regs:
                r = {**r, "origem": "principal", "busca_dia_utc": dia, "coleta_legada": True}
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        meta.write_text(json.dumps({
            "caso": caso, "origem": "principal", "dia_utc": dia,
            "query": f"LEGADO marca_ampla ({topico_antigo})", "posts_lidos": len(regs),
            "limite": limite_antigo, "limite_atingido": len(regs) >= limite_antigo,
            "coletado_em": "legado",
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        novos += 1
    print(f"{novos} dias importados da coleta antiga para {destino}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--caso", required=True, choices=proto.casos_disponiveis())
    ap.add_argument("--topico-antigo", required=True)
    ap.add_argument("--limite-antigo", type=int, default=200)
    a = ap.parse_args()
    importar(a.caso, a.topico_antigo, a.limite_antigo)


if __name__ == "__main__":
    main()
