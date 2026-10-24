"""Menu interativo de terminal para configurar e rodar a pipeline sem editar
YAML nem decorar flags de linha de comando.

Deixa escolher, numa sessão: tópico, quais fontes (X/Reddit) e quais
endpoints delas (grupos de query do X, subreddits do Reddit), período
(since/until) e a etapa a rodar (collect/process/all) — com log ao vivo no
próprio terminal, porque roda tudo no mesmo processo. Também gerencia as
credenciais (Reddit, LLM, sessão do X) num arquivo local fora do git.

As alterações de fontes/endpoints/período valem só para a sessão do menu —
não sobrescrevem o `config/<topico>.yaml`.

Uso:
  python src\\menu.py
"""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from queries import build_queries  # noqa: E402

CONFIG_DIR = Path("config")
CRED_PATH = Path("credentials.local.json")

CRED_KEYS = [
    ("REDDIT_CLIENT_ID", "Reddit — client_id"),
    ("REDDIT_CLIENT_SECRET", "Reddit — client_secret"),
    ("ANTHROPIC_API_KEY", "Sentimento LLM — Anthropic (ANTHROPIC_API_KEY)"),
    ("ZAI_API_KEY", "Sentimento LLM — Z.ai (ZAI_API_KEY)"),
]


# ---------------------------------------------------------------------------
# credenciais
# ---------------------------------------------------------------------------

def carregar_credenciais() -> dict[str, str]:
    if not CRED_PATH.exists():
        return {}
    dados = json.loads(CRED_PATH.read_text(encoding="utf-8"))
    for k, v in dados.items():
        if v:
            os.environ[k] = v
    return dados


def salvar_credenciais(dados: dict[str, str]) -> None:
    CRED_PATH.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")


def _mascarar(valor: str | None) -> str:
    if not valor:
        return "(não definida)"
    if len(valor) <= 6:
        return "*" * len(valor)
    return valor[:3] + "*" * (len(valor) - 6) + valor[-3:]


def _regenerar_sessao_x() -> None:
    print("\nPegue os cookies logado em x.com com a conta descartável:")
    print("F12 -> Application -> Cookies -> https://x.com -> copie auth_token e ct0")
    auth_token = input("auth_token: ").strip()
    ct0 = input("ct0: ").strip()
    if not auth_token or not ct0:
        print("Cancelado — os dois valores são obrigatórios.")
        return
    from session_from_cookies import build_storage_state

    estado = build_storage_state(auth_token, ct0)
    Path("storage_state.json").write_text(json.dumps(estado, indent=2), encoding="utf-8")
    print("storage_state.json atualizado.")


def menu_credenciais() -> None:
    dados = carregar_credenciais()
    while True:
        print("\n--- Credenciais ---")
        for i, (chave, rotulo) in enumerate(CRED_KEYS, start=1):
            print(f"  {i}. {rotulo}: {_mascarar(os.environ.get(chave))}")
        n = len(CRED_KEYS)
        estado_x = "existe" if Path("storage_state.json").exists() else "não existe"
        print(f"  {n + 1}. Sessão do X (storage_state.json): {estado_x} — gerar/regenerar")
        print("  0. Voltar")
        escolha = input("Escolha: ").strip()
        if escolha in ("0", ""):
            return
        if not escolha.isdigit():
            continue
        idx = int(escolha)
        if 1 <= idx <= n:
            chave, rotulo = CRED_KEYS[idx - 1]
            valor = input(f"Novo valor para {rotulo} (Enter para limpar): ").strip()
            if valor:
                dados[chave] = valor
                os.environ[chave] = valor
            else:
                dados.pop(chave, None)
                os.environ.pop(chave, None)
            salvar_credenciais(dados)
            print("Salvo em credentials.local.json (fora do git).")
        elif idx == n + 1:
            _regenerar_sessao_x()


# ---------------------------------------------------------------------------
# seleção genérica
# ---------------------------------------------------------------------------

def selecionar_multiplos(opcoes: list[str], atuais: list[str], titulo: str) -> list[str]:
    print(f"\n--- {titulo} ---")
    for i, op in enumerate(opcoes, start=1):
        marca = "x" if op in atuais else " "
        print(f"  [{marca}] {i}. {op}")
    print("Números separados por vírgula, 'todos', 'nenhum', ou Enter para manter.")
    resp = input("> ").strip().lower()
    if resp == "":
        return atuais
    if resp in ("todos", "all"):
        return list(opcoes)
    if resp in ("nenhum", "none"):
        return []
    escolhidos = []
    for parte in resp.split(","):
        parte = parte.strip()
        if parte.isdigit() and 1 <= int(parte) <= len(opcoes):
            escolhidos.append(opcoes[int(parte) - 1])
    return escolhidos or atuais


# ---------------------------------------------------------------------------
# sessão (tópico + overrides em memória)
# ---------------------------------------------------------------------------

def listar_topicos() -> list[str]:
    return sorted(p.stem for p in CONFIG_DIR.glob("*.yaml"))


def carregar_config(topico: str) -> dict:
    cfg_path = CONFIG_DIR / f"{topico}.yaml"
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8"))


def listar_grupos_twitter(cfg: dict) -> list[str]:
    if "twitter" not in cfg.get("fontes", {}):
        return []
    vistos: list[str] = []
    for q in build_queries(cfg):
        if q.grupo not in vistos:
            vistos.append(q.grupo)
    return vistos


class Sessao:
    def __init__(self, topico: str):
        self.topico = topico
        self.cfg = carregar_config(topico)
        fontes_cfg = self.cfg.get("fontes", {})
        self.fontes_ativas = {f for f in ("twitter", "reddit") if fontes_cfg.get(f, {}).get("ativo")}
        self.grupos_twitter = listar_grupos_twitter(self.cfg)
        self.grupos_selecionados = list(self.grupos_twitter)
        self.subreddits = list(fontes_cfg.get("reddit", {}).get("subreddits") or [])
        self.subreddits_selecionados = list(self.subreddits)
        per = self.cfg.get("periodo", {})
        self.since = per.get("since")
        self.until = per.get("until")

    def cfg_efetivo(self) -> dict:
        cfg = copy.deepcopy(self.cfg)
        cfg["periodo"]["since"] = self.since
        cfg["periodo"]["until"] = self.until
        if "twitter" in cfg.get("fontes", {}):
            cfg["fontes"]["twitter"]["ativo"] = "twitter" in self.fontes_ativas
        if "reddit" in cfg.get("fontes", {}):
            cfg["fontes"]["reddit"]["ativo"] = "reddit" in self.fontes_ativas
            if self.subreddits_selecionados:
                cfg["fontes"]["reddit"]["subreddits"] = list(self.subreddits_selecionados)
        return cfg


# ---------------------------------------------------------------------------
# execução
# ---------------------------------------------------------------------------

def _coletar_twitter(cfg: dict, grupos_selecionados: list[str], grupos_todos: list[str]) -> None:
    metodo = cfg["fontes"]["twitter"].get("metodo", "scrape")
    if metodo == "twscrape":
        import asyncio

        from collect_twscrape import coletar

        print("(twscrape não suporta filtro por grupo — rodando todas as queries)")
        asyncio.run(coletar(cfg, retomar=True))
        return

    from collect_x_scrape import coletar

    grupos = grupos_selecionados or grupos_todos
    if not grupos:
        coletar(cfg, retomar=True)
        return
    for grupo in grupos:
        print(f"-- grupo: {grupo} --")
        coletar(cfg, retomar=True, only_grupo=grupo)


def _coletar_reddit(cfg: dict) -> None:
    from collect_reddit import coletar

    coletar(cfg, retomar=True)


def rodar(sessao: Sessao, etapa: str) -> None:
    fontes = [f for f in ("twitter", "reddit") if f in sessao.fontes_ativas]
    if not fontes:
        print("Nenhuma fonte ativa selecionada — vá em '2. Selecionar fontes e endpoints'.")
        return

    cfg = sessao.cfg_efetivo()

    if etapa in ("collect", "all"):
        for fonte in fontes:
            print(f"\n=== coleta: {fonte} ===")
            if fonte == "twitter":
                _coletar_twitter(cfg, sessao.grupos_selecionados, sessao.grupos_twitter)
            else:
                _coletar_reddit(cfg)

    if etapa in ("process", "all"):
        import run_pipeline

        for fonte in fontes:
            print(f"\n=== processamento: {fonte} ===")
            run_pipeline._processar_fonte(fonte, cfg)


# ---------------------------------------------------------------------------
# menus
# ---------------------------------------------------------------------------

def imprimir_status(sessao: Sessao) -> None:
    print("\n" + "=" * 60)
    print(f"Tópico: {sessao.topico}")
    print(f"Fontes ativas nesta sessão: {', '.join(sorted(sessao.fontes_ativas)) or '(nenhuma)'}")
    print(f"Período: {sessao.since} .. {sessao.until} (until exclusivo)")
    if "twitter" in sessao.fontes_ativas:
        print(f"  Grupos X: {', '.join(sessao.grupos_selecionados) or '(nenhum)'}")
    if "reddit" in sessao.fontes_ativas:
        print(f"  Subreddits: {', '.join(sessao.subreddits_selecionados) or '(nenhum)'}")
    print("=" * 60)


def menu_topico(atual: Sessao) -> Sessao:
    topicos = listar_topicos()
    print("\n--- Tópicos ---")
    for i, t in enumerate(topicos, start=1):
        marca = " (atual)" if t == atual.topico else ""
        print(f"  {i}. {t}{marca}")
    escolha = input("Escolha (Enter mantém o atual): ").strip()
    if not escolha:
        return atual
    if escolha.isdigit() and 1 <= int(escolha) <= len(topicos):
        return Sessao(topicos[int(escolha) - 1])
    print("Opção inválida.")
    return atual


def menu_fontes_endpoints(sessao: Sessao) -> None:
    disponiveis = [f for f in ("twitter", "reddit") if f in sessao.cfg.get("fontes", {})]
    sessao.fontes_ativas = set(
        selecionar_multiplos(disponiveis, sorted(sessao.fontes_ativas), "Fontes ativas nesta sessão")
    )
    if "twitter" in sessao.fontes_ativas and sessao.grupos_twitter:
        sessao.grupos_selecionados = selecionar_multiplos(
            sessao.grupos_twitter, sessao.grupos_selecionados, "Grupos de query do X"
        )
    if "reddit" in sessao.fontes_ativas and sessao.subreddits:
        sessao.subreddits_selecionados = selecionar_multiplos(
            sessao.subreddits, sessao.subreddits_selecionados, "Subreddits"
        )


def menu_periodo(sessao: Sessao) -> None:
    print(f"\nPeríodo atual: since={sessao.since} until={sessao.until} (until é exclusivo)")
    novo_since = input(f"Novo since (AAAA-MM-DD, Enter mantém '{sessao.since}'): ").strip()
    novo_until = input(f"Novo until (AAAA-MM-DD, Enter mantém '{sessao.until}'): ").strip()
    if novo_since:
        sessao.since = novo_since
    if novo_until:
        sessao.until = novo_until
    print("(vale só para esta sessão — o YAML do tópico não é alterado)")


def menu_rodar(sessao: Sessao) -> None:
    print("\n--- Rodar ---")
    print("  1. collect (só coleta)")
    print("  2. process (bruto -> tabela com sentimento)")
    print("  3. all (coleta + processa)")
    print("  0. Voltar")
    etapa = {"1": "collect", "2": "process", "3": "all"}.get(input("Escolha: ").strip())
    if etapa:
        rodar(sessao, etapa)


def main() -> None:
    carregar_credenciais()
    topicos = listar_topicos()
    if not topicos:
        sys.exit(f"Nenhum config encontrado em {CONFIG_DIR}\\*.yaml")
    sessao = Sessao(topicos[0])

    while True:
        imprimir_status(sessao)
        print("1. Trocar tópico")
        print("2. Selecionar fontes e endpoints")
        print("3. Editar período")
        print("4. Gerenciar credenciais")
        print("5. Rodar (collect / process / all)")
        print("0. Sair")
        escolha = input("Escolha: ").strip()
        if escolha == "1":
            sessao = menu_topico(sessao)
        elif escolha == "2":
            menu_fontes_endpoints(sessao)
        elif escolha == "3":
            menu_periodo(sessao)
        elif escolha == "4":
            menu_credenciais()
        elif escolha == "5":
            menu_rodar(sessao)
        elif escolha == "0":
            return
        else:
            print("Opção inválida.")


if __name__ == "__main__":
    main()
