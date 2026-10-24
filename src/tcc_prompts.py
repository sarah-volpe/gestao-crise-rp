"""Gera os prompts finais de cada caso a partir da ficha (casos/<caso>.yaml)
e dos modelos únicos (metodologia/prompt_coleta.md e prompt_analise.md).

Os três casos usam exatamente o mesmo texto de prompt; só mudam os campos
da ficha. Os arquivos gerados em metodologia/prompts_gerados/ são os que vão
para o apêndice do trabalho, e o de análise é o que o classificador envia ao
modelo (o hash SHA-256 dele fica registrado em cada classificação).

Uso:
  python src/tcc_prompts.py            # gera para todos os casos
  python src/tcc_prompts.py colgate    # só um caso
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcc_protocolo as proto  # noqa: E402

MODELOS = Path("metodologia")
SAIDA = MODELOS / "prompts_gerados"


def _br(d: str) -> str:
    return date.fromisoformat(d).strftime("%d/%m/%Y") if d else "data a confirmar"


def _preencher(modelo: str, campos: dict[str, str]) -> str:
    for k, v in campos.items():
        modelo = modelo.replace("{{" + k + "}}", v)
    return modelo


def _campos_comuns(cfg: dict) -> dict[str, str]:
    return {
        "nome": cfg["nome"],
        "ano": str(cfg["ano"]),
        "contexto": " ".join(cfg["contexto"].split()),
        "prefixo_id": cfg["prefixo_id"],
    }


def render_coleta(cfg: dict) -> str:
    comp = cfg.get("busca_complementar") or {}
    fases = "\n".join(
        f"- {f.nome}: {f.inicio:%d/%m/%Y} a {f.fim:%d/%m/%Y}"
        + (" (opcional: colete se houver tempo)" if f.opcional else "")
        for f in cfg["_fases"]
    )
    marcos = "\n".join(f"- {_br(m['data'])}: {m['evento']}" for m in cfg.get("marcos", []))
    return _preencher((MODELOS / "prompt_coleta.md").read_text(encoding="utf-8"), {
        **_campos_comuns(cfg),
        "marcos": marcos,
        "fases": fases,
        "nota_linha_de_base": " ".join((cfg.get("nota_linha_de_base") or "").split()),
        "busca_principal": " ".join(cfg["busca_principal"].split()),
        "busca_complementar": " ".join((comp.get("query") or "(não há)").split()),
        "fases_complementar": ", ".join(comp.get("fases") or []) or "nenhuma",
    })


def render_analise(cfg: dict) -> str:
    c = cfg["classificacao"]
    regras = "".join(f"- {r}\n" for r in c.get("regras_especificas") or [])
    return _preencher((MODELOS / "prompt_analise.md").read_text(encoding="utf-8"), {
        **_campos_comuns(cfg),
        "alvo": c["alvo"],
        "sentimentos": "\n".join(f"- {k}: {v}" for k, v in c["sentimentos"].items()),
        "eixos": "\n".join(f"- {k}: {v}" for k, v in c["eixos"].items()),
        "exemplo_ironia": c["exemplo_ironia"],
        "regras_especificas": regras,
    })


def gerar(caso: str) -> tuple[Path, Path]:
    cfg = proto.carregar(caso)
    SAIDA.mkdir(parents=True, exist_ok=True)
    p_col = SAIDA / f"{caso}_coleta.md"
    p_ana = SAIDA / f"{caso}_analise.md"
    p_col.write_text(render_coleta(cfg), encoding="utf-8")
    p_ana.write_text(render_analise(cfg), encoding="utf-8")
    return p_col, p_ana


def main() -> None:
    casos = sys.argv[1:] or proto.casos_disponiveis()
    for caso in casos:
        for p in gerar(caso):
            print(f"-> {p}")


if __name__ == "__main__":
    main()
