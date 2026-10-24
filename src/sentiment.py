"""Classificação de sentimento PT-BR: positivo / negativo / neutro.

Três backends, mesma interface:

  lexicon      zero dependência extra, léxico PT-BR calibrado para crise de marca
               de consumo/luxo, com negação, intensificadores e emoji.
  transformer  pysentimiento (BERTabaporu, PT-BR). Mais preciso, ~2GB de download.
  llm          Claude API (pago). O único que lida bem com ironia e sarcasmo.

Use `get_analyzer("auto")` para pegar o melhor backend disponível.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass
class Sentimento:
    label: str          # "positivo" | "negativo" | "neutro"
    score: float        # -1.0 .. +1.0
    confianca: float    # 0.0 .. 1.0
    metodo: str
    termos: str = ""    # termos que puxaram a decisão (só no lexicon)


# ---------------------------------------------------------------------------
# Léxico
# ---------------------------------------------------------------------------

NEGATIVOS: dict[str, float] = {
    # indignação genérica
    "vergonha": 2.0, "vergonhoso": 2.0, "vergonhosa": 2.0, "absurdo": 2.0,
    "absurda": 2.0, "revoltante": 2.2, "revolta": 1.8, "escandalo": 2.0,
    "escandaloso": 2.0, "inaceitavel": 2.0, "inadmissivel": 2.0,
    "nojo": 2.2, "nojento": 2.2, "nojenta": 2.2, "ridiculo": 2.0,
    "ridicula": 2.0, "patetico": 2.0, "patetica": 2.0, "lamentavel": 1.8,
    "descaso": 1.8, "desrespeito": 1.8, "desrespeitoso": 1.8,
    # engano / má-fé (núcleo desta crise)
    "mentira": 2.2, "mentiroso": 2.2, "mentirosa": 2.2, "mentindo": 2.0,
    "enganacao": 2.2, "enganosa": 2.2, "enganoso": 2.2, "engana": 1.8,
    "farsa": 2.4, "fraude": 2.4, "golpe": 2.4, "picaretagem": 2.4,
    "estelionato": 2.4, "falsidade": 2.0, "hipocrisia": 2.0,
    "hipocrita": 2.0, "cara de pau": 2.0, "sem vergonha": 2.2,
    "malandragem": 1.6, "oportunista": 1.6, "maquiada": 1.2,
    # preço / exploração
    "caro": 1.2, "carissimo": 1.8, "carissima": 1.8, "superfaturado": 2.2,
    "superfaturada": 2.2, "roubo": 2.2, "roubando": 2.0, "extorsao": 2.2,
    "exploracao": 2.0, "explorando": 1.8, "abusivo": 1.8, "abusiva": 1.8,
    "sonegacao": 2.2, "trabalho escravo": 2.6, "precario": 1.8,
    # decepção com a marca
    "decepcao": 1.8, "decepcionada": 1.8, "decepcionado": 1.8,
    "decepcionante": 1.8, "frustrada": 1.6, "frustrado": 1.6,
    "frustrante": 1.6, "traida": 1.8, "traicao": 1.8, "perdeu a confianca": 2.0,
    "nunca mais": 1.8, "nao compro mais": 2.0, "cancelei": 1.8,
    # qualidade
    "pessimo": 2.0, "pessima": 2.0, "horrivel": 2.0, "terrivel": 2.0,
    "porcaria": 2.0, "lixo": 2.2, "bomba": 1.4, "quebrou": 1.2,
    "defeito": 1.4, "furada": 1.6, "vagabundo": 1.8, "vagabunda": 1.8,
    "chinesice": 1.6, "generico": 1.0,
    # sanção / reputação
    # NOTA: "crise", "polemica", "xicara", "tailandia" NÃO entram aqui de
    # propósito — são termos do TÓPICO, presentes em quase todo post coletado.
    # Pontuá-los jogaria a base inteira para negativo (viés de amostragem).
    "boicote": 1.4, "boicotar": 2.0, "boicotando": 2.0, "cancelada": 1.4,
    "cancelamento": 1.2, "procon": 1.0, "denuncia": 1.4, "denunciar": 1.6,
    "processar": 1.6, "exposta": 1.2, "exposed": 1.2,
    "pegou mal": 1.8, "deu ruim": 1.8, "fiasco": 2.0, "mancada": 1.6,
    "mico": 1.6, "cringe": 1.4, "sem noção": 1.6, "sem nocao": 1.6,
    "elitista": 1.4, "arrogante": 1.8, "esnobe": 1.6, "prepotente": 1.8,
    # ódio direto
    "odeio": 2.2, "detesto": 2.0, "nunca gostei": 1.6, "chata": 1.2,
    "insuportavel": 1.8, "falsa": 1.8, "falso": 1.8,
}

POSITIVOS: dict[str, float] = {
    "amo": 2.0, "amei": 2.0, "adoro": 2.0, "adorei": 2.0, "apaixonada": 2.0,
    "apaixonado": 2.0, "paixao": 1.6, "melhor": 1.6, "maravilhosa": 2.0,
    "maravilhoso": 2.0, "maravilha": 2.0, "perfeita": 2.0, "perfeito": 2.0,
    "incrivel": 1.8, "excelente": 1.8, "otima": 1.6, "otimo": 1.6,
    "otimas": 1.6, "sensacional": 1.8, "impecavel": 1.8, "espetacular": 1.8,
    "linda": 1.6, "lindo": 1.6, "lindissima": 1.8, "belissima": 1.8,
    "elegante": 1.4, "sofisticada": 1.4, "sofisticado": 1.4, "chique": 1.2,
    "requinte": 1.2, "delicada": 1.0, "charmosa": 1.2,
    "qualidade": 1.2, "durabilidade": 1.0, "vale a pena": 1.8,
    "recomendo": 1.8, "indico": 1.4, "top": 1.4, "arraso": 1.6,
    "arrasou": 1.6, "sucesso": 1.4, "parabens": 1.6, "orgulho": 1.6,
    "inspiracao": 1.4, "inspiradora": 1.4, "empreendedora": 1.0,
    "referencia": 1.2, "presente": 0.8, "presentao": 1.6, "sonho": 1.4,
    "desejo": 0.8, "cheirosa": 1.6, "cheiro bom": 1.6, "perfumada": 1.4,
    "atendimento otimo": 1.8, "gentil": 1.2, "obrigada": 0.8,
    # marcadores de DEFESA da marca: quem usa estes termos está do lado dela
    "defendo": 1.6, "injusto": 1.4, "exagero": 1.6, "mimimi": 1.8,
    "linchamento": 1.4, "perseguicao": 1.2, "cancelamento injusto": 1.8,
    "adoravel": 1.4, "gostei": 1.6, "curti": 1.4,
}

# Emoji tratados separadamente (não passam pela tokenização de palavras)
EMOJI: dict[str, float] = {
    "😍": 2.0, "🥰": 2.0, "❤️": 1.6, "❤": 1.6, "💖": 1.6, "😻": 1.6,
    "👏": 1.4, "🙌": 1.4, "✨": 0.8, "😊": 1.2, "🥹": 0.6, "😘": 1.4,
    "🤮": -2.4, "🤢": -2.2, "😡": -2.2, "🤬": -2.4, "😤": -1.6,
    "🙄": -1.6, "😒": -1.6, "💀": -1.2, "🤡": -2.0, "🚮": -1.8,
    "👎": -1.8, "😬": -1.0, "🤨": -1.0, "😱": -0.8, "🥱": -1.0,
}

# "nada" e "nem" ficam FORA de propósito: em PT-BR falado "nada" quase sempre
# reforça uma negação anterior ("não gostei nada") ou é interjeição ("que nada"),
# e como negador ele inverte por engano a palavra da oração seguinte.
NEGADORES = {
    "nao", "não", "nunca", "jamais", "nenhum", "nenhuma", "sem", "tampouco",
}
INTENSIFICADORES = {
    "muito": 1.5, "mto": 1.5, "mt": 1.5, "super": 1.6, "hiper": 1.6,
    "extremamente": 1.8, "totalmente": 1.5, "completamente": 1.5,
    "absurdamente": 1.8, "demais": 1.5, "puta": 1.7, "pra caralho": 1.8,
    "bastante": 1.3, "bem": 1.2, "tao": 1.3, "tão": 1.3, "que": 1.0,
}
DIMINUIDORES = {"pouco": 0.5, "meio": 0.6, "levemente": 0.5, "quase": 0.7, "talvez": 0.7}

# Ironia EXPLÍCITA: inverte um score positivo (elogio irônico = crítica).
IRONIA_FORTE = {"sqn", "so que nao", "só que não", "aham", "ironia", "ironico",
                "irônico", "faz me rir", "faz-me rir", "🙃"}
# Ironia POSSÍVEL: não inverte nada, só reduz a confiança da classificação.
IRONIA_FRACA = {"kkkk", "haha", "hehe", "😂", "🤣", "claro que sim", "ta bom", "tá bom"}

_MULTI_NEG = sorted((t for t in NEGATIVOS if " " in t), key=len, reverse=True)
_MULTI_POS = sorted((t for t in POSITIVOS if " " in t), key=len, reverse=True)


def strip_accents(txt: str) -> str:
    nfkd = unicodedata.normalize("NFKD", txt)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


BARREIRA = "|"


def normalizar(txt: str) -> str:
    """Minúsculas, sem URL/@/#, sem acento.

    Pontuação de fim de oração vira o token-barreira `|`: sem isso a janela de
    negação atravessa orações e inverte a palavra errada ("...que nada
    aconteceu. Fiasco" tornaria "fiasco" positivo).
    """
    t = txt.lower()
    t = re.sub(r"https?://\S+", " ", t)
    t = re.sub(r"@\w+", " ", t)
    t = t.replace("#", " ")
    t = strip_accents(t)
    t = re.sub(r"[.,;:!?()\[\]\n\r\"]+", f" {BARREIRA} ", t)
    t = re.sub(r"[^a-z0-9\s|]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


class LexiconAnalyzer:
    """Léxico + regras. Rápido, auditável, sem download."""

    metodo = "lexicon"

    def __init__(self, limiar: float = 0.12):
        self.limiar = limiar
        self.neg = {strip_accents(k): v for k, v in NEGATIVOS.items()}
        self.pos = {strip_accents(k): v for k, v in POSITIVOS.items()}
        self.negadores = {strip_accents(n) for n in NEGADORES}
        self.intens = {strip_accents(k): v for k, v in INTENSIFICADORES.items()}
        self.dimin = {strip_accents(k): v for k, v in DIMINUIDORES.items()}

    def _pontuar_multi(self, texto_norm: str) -> tuple[float, list[str], str]:
        """Expressões de várias palavras, removidas do texto para não recontar."""
        total = 0.0
        achados = []
        restante = texto_norm
        for termo in _MULTI_NEG:
            t = strip_accents(termo)
            if t in restante:
                total -= self.neg[t]
                achados.append(f"-{termo}")
                restante = restante.replace(t, " ")
        for termo in _MULTI_POS:
            t = strip_accents(termo)
            if t in restante:
                total += self.pos[t]
                achados.append(f"+{termo}")
                restante = restante.replace(t, " ")
        return total, achados, restante

    def analisar(self, texto: str) -> Sentimento:
        if not texto or not texto.strip():
            return Sentimento("neutro", 0.0, 0.0, self.metodo)

        norm = normalizar(texto)
        bruto, achados, restante = self._pontuar_multi(norm)
        tokens = restante.split()

        for i, tok in enumerate(tokens):
            peso = self.neg.get(tok, 0.0) * -1 or self.pos.get(tok, 0.0)
            if peso == 0.0:
                continue

            mult = 1.0
            negado = False
            # janela de até 3 tokens à esquerda, parando no fim da oração
            for j in range(i - 1, max(-1, i - 4), -1):
                anterior = tokens[j]
                if anterior == BARREIRA:
                    break
                if anterior in self.negadores:
                    negado = True
                mult *= self.intens.get(anterior, 1.0)
                mult *= self.dimin.get(anterior, 1.0)

            valor = peso * mult
            if negado:
                # negar elogio vira crítica forte; negar crítica só amortece
                valor = -valor * (1.0 if valor > 0 else 0.5)

            bruto += valor
            achados.append(("+" if valor > 0 else "-") + tok)

        # emoji e CAIXA ALTA no texto original
        for e, w in EMOJI.items():
            if e in texto:
                bruto += w * texto.count(e)
                achados.append(("+" if w > 0 else "-") + e)

        letras = [c for c in texto if c.isalpha()]
        if len(letras) > 12 and sum(c.isupper() for c in letras) / len(letras) > 0.6:
            bruto *= 1.3  # grito

        low = strip_accents(texto.lower())

        # ironia explícita inverte elogio: "que marca maravilhosa, parabéns sqn"
        marcas_ironia = [m for m in IRONIA_FORTE if strip_accents(m) in low or m in texto]
        if marcas_ironia and bruto > 0:
            bruto = -bruto
            achados.append("~ironia:" + marcas_ironia[0])

        # pergunta factual sem exclamação carrega menos carga de opinião
        if "?" in texto and "!" not in texto:
            bruto *= 0.7

        # tanh comprime para -1..1 sem saturar em textos longos
        score = _tanh(bruto / 4.0)

        if score > self.limiar:
            label = "positivo"
        elif score < -self.limiar:
            label = "negativo"
        else:
            label = "neutro"

        confianca = min(1.0, abs(score) * 1.4)
        if marcas_ironia or any(m in low or m in texto for m in IRONIA_FRACA):
            confianca *= 0.6  # ironia detectada: mesma classe, menos confiança

        return Sentimento(label, round(score, 4), round(confianca, 3),
                          self.metodo, ", ".join(achados[:12]))


def _tanh(x: float) -> float:
    import math

    return math.tanh(x)


class TransformerAnalyzer:
    """pysentimiento / BERTabaporu (PT-BR)."""

    metodo = "transformer"

    def __init__(self):
        from pysentimiento import create_analyzer

        self._an = create_analyzer(task="sentiment", lang="pt")
        self._map = {"POS": "positivo", "NEG": "negativo", "NEU": "neutro"}

    def analisar(self, texto: str) -> Sentimento:
        if not texto or not texto.strip():
            return Sentimento("neutro", 0.0, 0.0, self.metodo)
        out = self._an.predict(texto)
        probas = dict(out.probas)
        label = self._map.get(out.output, "neutro")
        score = probas.get("POS", 0.0) - probas.get("NEG", 0.0)
        return Sentimento(label, round(score, 4),
                          round(max(probas.values()), 3), self.metodo)

    def analisar_lote(self, textos: list[str]) -> list[Sentimento]:
        outs = self._an.predict(textos)
        res = []
        for o in outs:
            probas = dict(o.probas)
            res.append(Sentimento(
                self._map.get(o.output, "neutro"),
                round(probas.get("POS", 0.0) - probas.get("NEG", 0.0), 4),
                round(max(probas.values()), 3),
                self.metodo,
            ))
        return res


def get_analyzer(metodo: str = "auto", **kwargs):
    """Devolve o analisador pedido. "auto" = transformer se houver, senão lexicon."""
    metodo = (metodo or "auto").lower()

    if metodo in ("auto", "transformer"):
        try:
            an = TransformerAnalyzer()
            print("Sentimento: pysentimiento (transformer PT-BR).")
            return an
        except Exception as exc:
            if metodo == "transformer":
                raise
            print(f"Sentimento: transformer indisponível ({type(exc).__name__}), usando lexicon.")

    if metodo == "llm":
        from sentiment_llm import LLMAnalyzer

        return LLMAnalyzer(**kwargs)

    return LexiconAnalyzer(limiar=kwargs.get("limiar", 0.12))


if __name__ == "__main__":  # smoke test: python src/sentiment.py
    exemplos = [
        "Xícara de 1.500 reais fabricada na Tailândia. Propaganda enganosa pura, que absurdo.",
        "Amo os produtos da Tania Bulhoes, a porcelana é impecável e o cheiro é maravilhoso",
        "Tania Bulhoes abriu nova loja no shopping Iguatemi hoje",
        "não gostei nada da postura da marca nessa crise da xícara",
        "MENTIRA DESCARADA, nunca mais compro nada dessa marca 🤮",
        "acho exagero esse boicote, a marca é ótima e o preço é o de sempre",
        "que marca maravilhosa, parabéns pela transparência 🙃 kkkk sqn",
        "a marca fingiu que nada aconteceu. fiasco total",
        "alguém sabe se o Procon vai abrir processo contra a marca?",
    ]
    an = get_analyzer("lexicon")
    for t in exemplos:
        s = an.analisar(t)
        print(f"{s.label:9s} score={s.score:+.3f} conf={s.confianca:.2f}  [{s.termos}]")
        print(f"           {t[:90]}\n")
