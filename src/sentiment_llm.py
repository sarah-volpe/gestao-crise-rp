"""Backend OPCIONAL de sentimento via LLM — Claude API (pago) ou Z.ai/GLM
(tem modelos gratuitos, com rate limit).

Vale quando o léxico erra muito em ironia/sarcasmo — comum em crise de marca
("que marca maravilhosa, parabéns pela transparência 🙃"), e é o único
backend que cobre idiomas fora do PT-BR (o léxico é só português). Classifica
em lotes para reduzir custo/nº de chamadas.

Providers (config: sentimento.llm_provider):
  anthropic (padrão)  requer ANTHROPIC_API_KEY + pip install anthropic. Pago:
                       ~1.500 posts em lotes de 15 dão ~100 chamadas; com
                       claude-opus-5 fica na casa de poucos dólares.
  zai                  requer ZAI_API_KEY + pip install openai (usa o SDK da
                       OpenAI apontado para o endpoint compatível da Z.ai).
                       Modelo padrão glm-4.5-flash é gratuito, com rate
                       limit — se voar muito de posts, pode precisar de
                       pausas maiores entre lotes (ajuste `lote` no config).

Nunca cole a API key em código nem no config — configure como variável de
ambiente antes de rodar:
  PowerShell:  $env:ANTHROPIC_API_KEY="..."   ou   $env:ZAI_API_KEY="..."
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import sys
import time

from sentiment import Sentimento

TIMEOUT_S = 90.0  # timeout por chamada — evita travar minutos numa requisição presa

SYSTEM_TEMPLATE = """You classify the sentiment of social media posts (X/Twitter, Reddit) \
about the following case, which may be discussed in English, Portuguese, or a mix:

{descricao}

Rules:
- Sentiment is the author's stance TOWARD THE SUBJECT ABOVE, not the general mood of the post.
- Irony and sarcasm are common: an ironic compliment is NEGATIVE. Flag irony as `ironia: true` \
and lower the confidence.
- "negativo" = criticism, outrage, mockery, boycott, accusation of bad faith.
- "positivo" = praise, defending the subject, downplaying the controversy, purchase intent.
- "neutro" = news, factual data, factual question, mention with no value judgment.
- A post that criticizes the critics counts as POSITIVE toward the subject.
- If the post is unrelated to the subject/case above, use "neutro" and `off_topic: true`.
- Reply in the same schema regardless of the post's language; `justificativa` may be in \
Portuguese or English, whichever is more natural for that post."""

SCHEMA = {
    "type": "object",
    "properties": {
        "resultados": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "i": {"type": "integer", "description": "índice do post no lote"},
                    "sentimento": {"type": "string", "enum": ["positivo", "negativo", "neutro"]},
                    "confianca": {"type": "number", "description": "0.0 a 1.0"},
                    "ironia": {"type": "boolean"},
                    "off_topic": {"type": "boolean"},
                    "justificativa": {"type": "string", "description": "no máximo 12 palavras"},
                },
                "required": ["i", "sentimento", "confianca", "ironia", "off_topic", "justificativa"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["resultados"],
    "additionalProperties": False,
}

_SCORE = {"positivo": 1.0, "negativo": -1.0, "neutro": 0.0}

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _extrair_json(texto: str) -> dict:
    """Alguns modelos embrulham a resposta em ```json ... ``` mesmo pedindo
    JSON puro — remove a cerca de código antes de fazer parse."""
    limpo = _FENCE_RE.sub("", texto.strip())
    return json.loads(limpo)


class LLMAnalyzer:
    metodo = "llm"

    def __init__(
        self,
        provider: str = "anthropic",
        modelo: str | None = None,
        lote: int = 15,
        concorrencia: int = 4,
        descricao: str = "a brand/case under public criticism",
        **_,
    ):
        self.provider = provider
        self.lote = max(1, int(lote))
        self.concorrencia = max(1, int(concorrencia))
        self.system = SYSTEM_TEMPLATE.format(descricao=descricao.strip())

        if provider == "zai":
            try:
                from openai import OpenAI
            except ImportError:
                sys.exit("openai não instalado (usado como cliente para a Z.ai). Rode: pip install openai")
            api_key = os.environ.get("ZAI_API_KEY")
            if not api_key:
                sys.exit(
                    "Falta ZAI_API_KEY no ambiente.\n"
                    "Crie uma chave em https://z.ai/manage-apikey/apikey-list e configure:\n"
                    '  PowerShell:  $env:ZAI_API_KEY="sua_chave"'
                )
            self.client = OpenAI(api_key=api_key, base_url="https://api.z.ai/api/paas/v4/", timeout=TIMEOUT_S)
            self.modelo = modelo or "glm-4.5-flash"
        else:
            import anthropic

            self.client = anthropic.Anthropic(timeout=TIMEOUT_S)
            self.modelo = modelo or "claude-opus-5"

    # --- um post por vez (interface comum aos outros backends) ---
    def analisar(self, texto: str) -> Sentimento:
        return self.analisar_lote([texto])[0]

    def analisar_lote(self, textos: list[str]) -> list[Sentimento]:
        """Classifica em lotes de `self.lote` posts, disparando até
        `self.concorrencia` chamadas de API em paralelo (threads — o
        trabalho é I/O, não CPU). O gargalo do backend gratuito costuma ser
        latência/rate-limit por chamada, não volume de token, então rodar
        vários lotes ao mesmo tempo é o que realmente acelera."""
        blocos = [textos[ini: ini + self.lote] for ini in range(0, len(textos), self.lote)]
        resultados: list[list[Sentimento] | None] = [None] * len(blocos)
        concluidos = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.concorrencia) as executor:
            futuros = {executor.submit(self._classificar_bloco, bloco): i for i, bloco in enumerate(blocos)}
            for fut in concurrent.futures.as_completed(futuros):
                i = futuros[fut]
                resultados[i] = fut.result()
                concluidos += len(blocos[i])
                print(f"  LLM ({self.provider}, {self.concorrencia}x paralelo): "
                      f"{concluidos}/{len(textos)} posts", flush=True)

        saida: list[Sentimento] = []
        for r in resultados:
            saida.extend(r)
        return saida

    def _com_retentativas(self, chamar, tentativas: int = 3):
        for tentativa in range(1, tentativas + 1):
            try:
                return chamar()
            except Exception as exc:
                if tentativa == tentativas:
                    raise
                rate_limited = "RateLimit" in type(exc).__name__ or "429" in str(exc)
                # o free tier do zai tem rate limit por conta na casa de ~1,5-2min entre
                # chamadas — backoff curto (ex.: 20s/40s) falha de novo garantido
                espera = (100.0 if rate_limited else 5.0) * tentativa
                print(f"  !! tentativa {tentativa}/{tentativas} falhou "
                      f"({type(exc).__name__}: {exc}) — retry em {espera:.0f}s", flush=True)
                time.sleep(espera)

    def _montar_prompt(self, bloco: list[str]) -> str:
        posts = "\n\n".join(
            f"[{i}] {t.replace(chr(10), ' ')[:600]}" for i, t in enumerate(bloco)
        )
        return (
            f"Classifique os {len(bloco)} posts abaixo. Devolva APENAS um objeto JSON "
            f'no formato exato {{"resultados": [{{"i": <int>, "sentimento": '
            f'"positivo"|"negativo"|"neutro", "confianca": <0.0-1.0>, "ironia": <bool>, '
            f'"off_topic": <bool>, "justificativa": "<até 12 palavras>"}}, ...]}}, '
            f"um item por post, sem nenhum texto fora do JSON.\n\n{posts}"
        )

    def _classificar_bloco(self, bloco: list[str]) -> list[Sentimento]:
        prompt = self._montar_prompt(bloco)
        chamar = self._chamar_zai if self.provider == "zai" else self._chamar_anthropic
        try:
            dados = self._com_retentativas(lambda: chamar(prompt))
        except Exception as exc:
            print(f"  !! bloco falhou após retentativas ({type(exc).__name__}: {exc}) "
                  f"— marcado como llm_erro", flush=True)
            dados = None
        return self._parse_resultados(dados, len(bloco))

    def _chamar_anthropic(self, prompt: str) -> list[dict] | None:
        kwargs = dict(
            model=self.modelo,
            max_tokens=8000,
            system=self.system,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        )
        try:
            # fallback server-side: se um classificador de segurança recusar, a
            # própria API roteia para outro modelo em vez de devolver nada
            resp = self.client.beta.messages.create(
                betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs
            )
        except Exception:
            resp = self.client.messages.create(**kwargs)

        if getattr(resp, "stop_reason", None) == "refusal":
            return None

        texto = next((b.text for b in resp.content if b.type == "text"), "{}")
        return _extrair_json(texto).get("resultados", [])

    def _chamar_zai(self, prompt: str) -> list[dict]:
        resp = self.client.chat.completions.create(
            model=self.modelo,
            messages=[
                {"role": "system", "content": self.system},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        texto = resp.choices[0].message.content or "{}"
        return _extrair_json(texto).get("resultados", [])

    def _parse_resultados(self, dados: list[dict] | None, n: int) -> list[Sentimento]:
        if dados is None:
            return [Sentimento("neutro", 0.0, 0.0, "llm_erro") for _ in range(n)]

        por_indice = {int(d["i"]): d for d in dados if "i" in d}
        res = []
        for i in range(n):
            d = por_indice.get(i)
            if not d:
                res.append(Sentimento("neutro", 0.0, 0.0, "llm_missing"))
                continue
            label = d.get("sentimento", "neutro")
            conf = float(d.get("confianca", 0.5))
            if d.get("ironia"):
                conf *= 0.85
            res.append(Sentimento(
                label=label,
                score=round(_SCORE.get(label, 0.0) * conf, 4),
                confianca=round(conf, 3),
                metodo=f"{self.metodo}_{self.provider}",
                termos=d.get("justificativa", "")[:120],
            ))
        return res
