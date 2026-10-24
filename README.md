# Monitoramento de crises de marca com IA generativa

Repositório do Trabalho de Conclusão de Curso de **Sarah Pelicon Volpe**
(Relações Públicas, UFPR, 2026; orientação: Prof.ª Fabia Ioscote).

O trabalho analisa três crises de marca de 2025 no Brasil (**Tânia Bulhões**,
**Colgate** e **Cacau Show**) a partir de publicações públicas do X, usando
inteligência artificial generativa para classificar o sentimento do público
em relação a cada marca antes, durante e depois da crise.

Este repositório reúne tudo o que é preciso para entender, conferir e
repetir o procedimento: as fichas dos casos, os prompts usados, o código e
os resultados.

## Como ler este repositório (sem precisar programar)

| Se você quer… | Abra |
|---|---|
| entender o procedimento em linguagem simples | [`metodologia/protocolo.md`](metodologia/protocolo.md) |
| ver as datas, marcos e palavras-chave de cada caso | [`casos/`](casos/) (um arquivo por caso) |
| ler os prompts exatamente como foram usados | [`metodologia/prompts_gerados/`](metodologia/prompts_gerados/) |
| ver como os prompts e o código foram criados | [`metodologia/prompts_de_desenvolvimento.md`](metodologia/prompts_de_desenvolvimento.md) |
| ver os resultados em gráficos | o **painel**: https://sarah-volpe.github.io/gestao-crise-rp/ |
| conferir os números | `dados/` (tabelas sem identificação de autores) |

## O procedimento em quatro etapas

1. **Coleta.** Para cada dia do período de cada caso, a mesma busca é feita no
   X. São lidas até 300 publicações por dia e sorteadas até 15, de forma
   reprodutível. Os autores são anonimizados.
2. **Classificação.** Um modelo de IA generativa lê só o texto de cada
   publicação e indica o sentimento em relação à marca (negativo, positivo,
   neutro ou fora do tema), o eixo temático, se há ironia e o grau de
   confiança.
3. **Validação humana.** A pesquisadora classifica sozinha uma amostra
   sorteada, sem ver a resposta da IA, e a concordância entre as duas é
   medida pelo kappa de Cohen.
4. **Consolidação.** Os resultados são reunidos por caso e por fase (pré-crise,
   crise e pós-crise) e comparados entre os casos.

As mesmas regras valem para os três casos. O que muda de um caso para outro
está todo na sua ficha, em `casos/`.

## Organização

```
casos/                      fichas dos casos: datas, marcos, buscas, critérios (ÚNICO lugar de configuração)
metodologia/
  protocolo.md              o procedimento, as decisões de método e as limitações
  prompt_coleta.md          modelo único do prompt de coleta
  prompt_analise.md         modelo único do prompt de classificação
  prompts_gerados/          prompts finais de cada caso (os do apêndice)
  prompts_de_desenvolvimento.md   pedidos feitos à IA para construir o processo
painel/                     painel de resultados (página publicada pelo GitHub Pages)
src/                        código (ver metodologia/protocolo.md, seção "Como executar")
dados/                      resultados publicados (tabelas sem identificação de autores)
```

## Dados e privacidade

- A tabela que liga os códigos U001, U002… aos perfis do X **nunca é
  publicada**: ela fica fora do repositório.
- Os links das publicações usam o formato `x.com/i/status/<número>`, que não
  mostra o nome do autor.
- O texto de uma publicação pública pode ser encontrado por busca, o que
  permite identificar o autor mesmo com a anonimização. Por isso, a versão
  pública do repositório traz os identificadores e as classificações; os
  textos integrais ficam disponíveis à orientação e à banca mediante
  solicitação.

## Uso de IA neste trabalho

A IA generativa foi usada em duas funções, ambas documentadas aqui:

- **Como objeto de pesquisa:** a classificação de sentimento, com o prompt em
  `metodologia/prompts_gerados/`, o modelo e a data registrados em cada
  resultado.
- **Como apoio ao desenvolvimento:** o código de coleta e de análise foi
  escrito com auxílio de IA. Os pedidos feitos estão em
  `metodologia/prompts_de_desenvolvimento.md`.
