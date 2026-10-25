"""Roda a coleta de vários casos de uma vez, até completar (ou não haver progresso).

O que faz, sozinho:
  1. Coleta os dias que faltam de cada caso (retoma de onde parou).
  2. Se a coleta parar com buscas pendentes (sessão expirada ou limite do X),
     renova a sessão com o login_x.py e tenta de novo, até 4 rodadas.
     Se o perfil de login já estiver salvo, a renovação não pede nada.
  3. Monta as tabelas do protocolo e atualiza o painel.
  4. Mostra, por caso, quantos dias ficaram completos, parciais ou sem coleta.

Enquanto roda, impede que o Windows entre em suspensão.

Uso:
  python src\\tcc_rodar.py --casos colgate cacau_show
  python src\\tcc_rodar.py --casos colgate --sem-opcionais     # sem reinterdição/segunda onda
  python src\\tcc_rodar.py --casos cacau_show --so-montar        # não coleta, só monta e atualiza o painel
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcc_protocolo as proto  # noqa: E402


def manter_acordado(ligar: bool) -> None:
    if os.name != "nt":
        return
    import ctypes
    ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if ligar else 0))


def pendentes(caso: str, opcionais: bool) -> int:
    cfg = proto.carregar(caso)
    return sum(not (proto.raw_dir(caso, b.origem) / f"{b.since}.meta.json").exists()
               for b in proto.buscas(cfg, opcionais))


def renovar_sessao() -> bool:
    print("\n>>> Renovando a sessão do X (se pedir, faça login na janela que abrir)...", flush=True)
    r = subprocess.run([sys.executable, str(Path(__file__).parent / "login_x.py")])
    return r.returncode == 0


def resumo_volume(caso: str) -> str:
    import pandas as pd
    p = proto.TCC_ROOT / caso / f"{caso}_volume_diario.csv"
    if not p.exists():
        return "sem tabela"
    v = pd.read_csv(p, sep=";", encoding="utf-8-sig", dtype=str)["volume_estimado_no_dia"]
    falta = v.eq("nao_coletado").sum()
    parc = v.str.startswith("parcial").sum()
    return f"{len(v) - falta - parc} dias completos, {parc} parciais, {falta} sem coleta"


def main() -> None:
    ap = argparse.ArgumentParser(description="Coleta, monta e atualiza o painel de vários casos.")
    ap.add_argument("--casos", nargs="+", required=True, choices=proto.casos_disponiveis())
    ap.add_argument("--sem-opcionais", action="store_true", help="não coleta fases opcionais")
    ap.add_argument("--so-montar", action="store_true", help="pula a coleta")
    ap.add_argument("--rodadas", type=int, default=4)
    a = ap.parse_args()
    opc = not a.sem_opcionais

    if not a.so_montar:
        from tcc_coletar import coletar
        manter_acordado(True)
        inicio = time.time()
        try:
            antes = {c: pendentes(c, opc) for c in a.casos}
            print("Buscas pendentes: " + ", ".join(f"{c} {n}" for c, n in antes.items()), flush=True)
            parado = False
            for rodada in range(1, a.rodadas + 1):
                for caso in a.casos:
                    if pendentes(caso, opc):
                        print(f"\n=== {caso} (rodada {rodada}) ===", flush=True)
                        try:
                            r = coletar(caso, incluir_opcionais=opc, refazer=False, so_dia=None,
                                        so_origem=None, headed=False)
                        except SystemExit as exc:
                            print(f"  coleta interrompida: {exc}")
                            r = "parado"
                        if r == "parado":
                            parado = True
                            break
                if parado:
                    print("\n!! Coleta parada esperando login ou verificação. Rode o mesmo comando quando "
                          "estiver na frente do computador (retoma de onde parou).")
                    break
                agora = {c: pendentes(c, opc) for c in a.casos}
                if not any(agora.values()):
                    break
                if sum(agora.values()) >= sum(antes.values()):
                    print("\n!! Nenhum progresso nesta rodada: o X pode estar limitando a conta. "
                          "Espere algumas horas e rode o mesmo comando (retoma de onde parou).")
                    break
                antes = agora
                time.sleep(30)
        finally:
            manter_acordado(False)
        print(f"\nColeta encerrada em {(time.time() - inicio) / 60:.0f} min.")

    from tcc_montar import montar
    for caso in a.casos:
        print(f"\n=== montando {caso} ===")
        try:
            montar(caso, incluir_opcionais=opc, mascarar_mencoes=False)
        except SystemExit as exc:
            print(f"  {exc}")
    subprocess.run([sys.executable, str(Path(__file__).parent / "tcc_painel.py")])

    print("\n===== RESUMO =====")
    for caso in a.casos:
        print(f"{caso:14s} buscas pendentes: {pendentes(caso, opc):3d} | {resumo_volume(caso)}")
    print("\nPróximo passo: classificar os casos (COMO_USAR.md, passo 5).")


if __name__ == "__main__":
    main()
