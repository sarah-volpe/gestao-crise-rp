# Prompts de desenvolvimento

Registro dos pedidos feitos à IA generativa (Claude, Anthropic) para
construir o procedimento de coleta e classificação. Os textos estão como
foram enviados. As respostas da IA (código e documentos) estão no próprio
repositório.

Distinção importante:
- **Prompts de pesquisa** são os que produzem os dados analisados no
  trabalho. Estão em `metodologia/prompts_gerados/`.
- **Prompts de desenvolvimento** (este arquivo) foram usados para
  *construir* o procedimento: escrever os prompts de pesquisa, o código e a
  documentação. Eles não produzem dados.

> Lacuna conhecida: os pedidos que geraram a primeira versão do código de
> coleta e do léxico de sentimento (antes de outubro de 2026, incluindo o
> protótipo com Google Natural Language API) não estão registrados aqui.
> Acrescente-os se ainda estiverem disponíveis nos históricos de conversa.

---

## Etapa 1 — Pedido dos prompts de coleta e análise (versão 1)

**Pedido** (enviado a uma conversa anterior; gerou a versão 1 dos prompts,
reproduzida em `historico/prompts_v1.md`):

> chat, seguinte: até entao, esse é meu tcc. precisamos melhorar ele, tirar
> claude do titulo e citar ia, arrumar referencia. mas, primeiro, precisamos
> finalizar a parte sobre coleta de dados e analise de sentimento. quero que
> vc crie dois prompts, um pra coleta de dados do X e outro pra analise de
> sentimento. vamos pesquisar sobre 3 casos de crise publica de 2025: o caso
> tania bulhoes, o caso colgate e o caso da cacau show. no prompt precisa
> conter: 1. data (considerando alguns dias antes e apos a crise, para
> entendermos qual o sentimento normal) 2. palavras chave de pesquisa. leia o
> tcc até o momento, veja se estamos indo por um bom caminho, faça o prompt
> com aquilo que for adequado para o trabalho, também sugira melhorias. estou
> entrevistando pessoas para fazer sentido ter uma visão humana.

## Etapa 2 — Agente de análise de crise (24/10/2026)

**Pedido:**

> # PERSONA E PAPEL
> Você é o **PR Crisis Sentinel**, um agente especialista em Inteligência
> Artificial aplicado às Relações Públicas, Comunicação Corporativa e Gestão
> de Riscos Reputacionais.
>
> Sua missão é analisar dados brutos de redes sociais, identificar padrões
> emocionais e comportamentais nas interações dos usuários e **prever
> potenciais crises de imagem antes que elas se tornem incontroláveis**.
>
> # PIPELINE DE ATUAÇÃO
> ### ETAPA 1: Tratamento e Classificação de Dados
> - **Polaridade:** Classifique cada menção em [Positivo | Neutro | Negativo].
> - **Sentimento/Emoção Predominante:** Identifique o tom (ex: *Raiva/Indignação*,
>   *Frustração/Decepção*, *Ironia/Sarcasmo*, *Apoio/Entusiasmo*).
> - **Clusterização de Temas:** Agrupe os comentários por tópicos recorrentes.
>
> ### ETAPA 2: Matriz de Risco e Previsão de Crise
> - 🟢 Verde (Normalidade) · 🟡 Amarelo (Atenção) · 🟧 Laranja (Pré-Crise) ·
>   🔴 Vermelho (Crise Iminente/Instalada)
>
> ### ETAPA 3: Estruturação do Output (Relatório Executivo)
> 1. Resumo do Panorama Geral · 2. Principais Focos de Tensão · 3. Diagnóstico
> do Nível de Risco · 4. Recomendações Estratégicas de RP · 5. Dashboard de
> acompanhamento de reputação com insights e avaliação histórica de saúde.

**Resultado:** a IA pediu os dados brutos e propôs uma simulação. Esse
agente fica como referência para o painel; ele não é usado na
classificação do corpus, que segue o protocolo da Etapa 3.

## Etapa 3 — Agentes de coleta e de análise (24/10/2026)

**Pedido:**

> Consigo montar tudo aqui? Ter um agente de scrapping e um agente de analise?

seguido dos seis prompts da versão 1 (coleta e análise para cada caso),
reproduzidos em `historico/prompts_v1.md`.

**Resultado:** a IA estimou o custo de coleta por navegação assistida (cerca
de 240 buscas) e recomendou quatro ajustes de método: sorteio no lugar dos
15 primeiros posts, registro da data da coleta, declaração de posts
apagados e validação humana com kappa.

## Etapa 4 — Aprimorar a pipeline existente (24/10/2026)

**Pedido:**

> Esse tipo de pipeline é muito custosa, eu tinha uma desenvolvida, me ajude
> a aprimorar dentro dos parâmetros definidos no TCC

**Resultado:** a IA leu o código existente e implementou o protocolo da
versão 1 como módulo próprio (`src/tcc_*.py`). Foram corrigidos: buscas
diferentes das do protocolo, diferença de fuso entre UTC e Brasília, link
que expunha o autor, perda de emojis na leitura do texto e validação que
mostrava o rótulo da máquina ao avaliador. Também foram adicionados o modo
manual sem custo de API e a validação cega com kappa de Cohen.

## Etapa 5 — Revisão do TCC, prompts versão 2 e centralização (24/10/2026)

**Pedido:** o pedido da Etapa 1, com o PDF do TCC anexado, acrescido de:

> Pensando sobre a parte técnica, gostaria de diminuir o quanto for possível
> a barreira técnica para a apresentação, pois tudo que for apresentado
> precisaria entender o método por trás e a pipeline não é exatamente o foco
> disso tudo.
>
> Estive pensando em termos tudo centralizado em um lugar. A configuração dos
> clientes, config dos tópicos e períodos e o mais importante, o dashboard
> para a análise de IA.
>
> Porém como eu disse, o foco não é técnico, preciso ter tudo documentado,
> prompts usados para criar cada parte do processo, etc.
>
> irei montar um repositório no Github onde ira conter tudo, o código,
> metodologia, prompts usados para cada processo pra que seja validado por
> qualquer orientador ou pessoa interessada

**Resultado:** versão 2 dos prompts (abaixo), fichas únicas por caso em
`casos/`, documentação deste repositório e revisão do texto do TCC.

### O que mudou da versão 1 para a versão 2 dos prompts

| mudança | motivo |
|---|---|
| um único modelo de prompt para os três casos, preenchido pela ficha do caso | garante procedimento idêntico entre os casos (Yin, 2005) |
| eixos temáticos com definição escrita | sem definição, IA e avaliador humano interpretam os eixos de forma diferente, o que derruba o kappa |
| regra "o eixo de um meme é o assunto da piada" | evita que memes sobre preço ou origem caiam todos em `humor_meme` |
| definições de ironia e de níveis de confiança | os três níveis não estavam definidos |
| post que só marca a marca é neutro; não supor conteúdo de imagens e links | casos frequentes no X que geravam dúvida |
| coleta: sorteio de 15 posts entre todos os do dia | os 15 primeiros de "Mais recentes" são só os da noite |
| coleta: aviso sobre UTC e data pelo horário de Brasília | o `since/until` do X usa UTC |
| coleta: spam e homônimo vão para a análise como `fora_do_tema` | decisão de leitura fica registrada e validada |
| coleta: link `x.com/i/status/<id>` | o link padrão expõe o @ do autor |
| Tânia Bulhões: + "Tânia Bulhoes" na principal; + "crise da xícara" e grafias sem acento na complementar | variações encontradas na coleta anterior |
| Colgate: + língua, lábio(s), gengiva, inchaço, alérgica, interditada, proibida, recolhimento na principal; + "Total Prevenção Ativa" (nome completo do produto) na complementar | relatos de sintoma sem as palavras da versão 1 |
| Colgate: nova fase opcional de reinterdição (25/04–08/05) | a Anvisa voltou a interditar o produto em 30/04/2025, fora das fases da versão 1 |
| Cacau Show: + "rituais da Cacau" na complementar | variação do termo "ritual" |
| marcos de cada caso com fonte jornalística | datas verificáveis; as sem fonte estão marcadas "A CONFIRMAR" |

## Etapa 6 — Painel (24/10/2026)

**Pedido:**

> e quanto ao dashboard?

**Resultado:** painel estático em `painel/`, publicado pelo GitHub Pages e
gerado por `src/tcc_painel.py` a partir dos arquivos públicos de `dados/`.
Ele tem uma aba por caso e uma de comparação, tabela equivalente para cada
gráfico, tema claro e escuro, e não exibe o texto das publicações. As cores
de sentimento (vermelho, cinza e azul) foram conferidas quanto à
distinguibilidade para daltonismo.
