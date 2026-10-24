"""Protocolo de coleta do TCC: fases, dias e buscas de cada caso.

Lê casos/<caso>.yaml, a ficha única de cada caso.

Fuso horário: os operadores since:/until: do X trabalham em dias UTC, mas as
fases do TCC são em horário de Brasília (UTC-3). Um dia de Brasília D vai
de D 03:00 UTC a D+1 03:00 UTC, ou seja, fica coberto pelas buscas UTC D e
D+1. Por isso a coleta faz uma busca por dia UTC cobrindo o intervalo
[início da fase, fim da fase + 1] e, na montagem (tcc_montar.py), cada post
recebe a data e a fase pela hora real de publicação em Brasília.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import yaml

CONFIG_DIR = Path("casos")
RAW_ROOT = Path("data/raw/x_tcc")
TCC_ROOT = Path("dados")
PRIVADO_ROOT = Path("data/privado")


@dataclass(frozen=True)
class Fase:
    nome: str
    inicio: date
    fim: date          # inclusivo
    opcional: bool = False

    def contem(self, d: date) -> bool:
        return self.inicio <= d <= self.fim


@dataclass(frozen=True)
class BuscaDia:
    origem: str        # "principal" | "complementar"
    dia_utc: date
    texto: str         # query final com since:/until:

    @property
    def since(self) -> str:
        return self.dia_utc.isoformat()

    @property
    def until(self) -> str:
        return (self.dia_utc + timedelta(days=1)).isoformat()

    @property
    def grupo(self) -> str:  # compatibilidade com Query (collect_x_scrape)
        return self.origem


def casos_disponiveis() -> list[str]:
    return sorted(p.stem for p in CONFIG_DIR.glob("*.yaml"))


def carregar(caso: str) -> dict:
    p = CONFIG_DIR / f"{caso}.yaml"
    if not p.exists():
        sys.exit(f"{p} não existe. Casos: {', '.join(casos_disponiveis())}")
    cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    cfg["_fases"] = [
        Fase(f["nome"], date.fromisoformat(str(f["inicio"])),
             date.fromisoformat(str(f["fim"])), bool(f.get("opcional", False)))
        for f in cfg["fases"]
    ]
    return cfg


def fases_ativas(cfg: dict, incluir_opcionais: bool) -> list[Fase]:
    return [f for f in cfg["_fases"] if incluir_opcionais or not f.opcional]


def fase_de(d: date, fases: list[Fase]) -> str | None:
    for f in fases:
        if f.contem(d):
            return f.nome
    return None


def _dias(ini: date, fim: date) -> list[date]:
    return [ini + timedelta(days=i) for i in range((fim - ini).days + 1)]


def buscas(cfg: dict, incluir_opcionais: bool = False) -> list[BuscaDia]:
    """Uma busca por dia UTC, por origem. Mesma busca principal em todas as
    fases; a complementar só nos dias das fases listadas no config."""
    fases = fases_ativas(cfg, incluir_opcionais)
    comp = cfg.get("busca_complementar") or {}
    fases_comp = set(comp.get("fases") or [])

    dias_principal: set[date] = set()
    dias_comp: set[date] = set()
    for f in fases:
        for d in _dias(f.inicio, f.fim):
            cobertura = {d, d + timedelta(days=1)}  # dia BR D = dias UTC D e D+1
            dias_principal |= cobertura
            if f.nome in fases_comp:
                dias_comp |= cobertura

    principal = " ".join(cfg["busca_principal"].split())
    out = [BuscaDia("principal", d, f"{principal} since:{d} until:{d + timedelta(days=1)}")
           for d in sorted(dias_principal)]
    if comp.get("query"):
        q = " ".join(comp["query"].split())
        out += [BuscaDia("complementar", d, f"{q} since:{d} until:{d + timedelta(days=1)}")
                for d in sorted(dias_comp)]
    return out


def raw_dir(caso: str, origem: str) -> Path:
    d = RAW_ROOT / caso / origem
    d.mkdir(parents=True, exist_ok=True)
    return d


def tcc_dir(caso: str) -> Path:
    d = TCC_ROOT / caso
    d.mkdir(parents=True, exist_ok=True)
    return d


def privado_dir() -> Path:
    PRIVADO_ROOT.mkdir(parents=True, exist_ok=True)
    return PRIVADO_ROOT


if __name__ == "__main__":  # python src/tcc_protocolo.py tania_bulhoes [--opcionais]
    caso = sys.argv[1] if len(sys.argv) > 1 else "tania_bulhoes"
    cfg = carregar(caso)
    bs = buscas(cfg, incluir_opcionais="--opcionais" in sys.argv)
    for f in fases_ativas(cfg, "--opcionais" in sys.argv):
        print(f"fase {f.nome:13s} {f.inicio} a {f.fim} ({(f.fim - f.inicio).days + 1} dias)")
    print(f"\n{len(bs)} buscas "
          f"({sum(b.origem == 'principal' for b in bs)} principal, "
          f"{sum(b.origem == 'complementar' for b in bs)} complementar). Exemplos:")
    for b in bs[:2] + [b for b in bs if b.origem == "complementar"][:1]:
        print(f"  [{b.origem}] {b.texto}")
