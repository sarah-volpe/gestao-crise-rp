# Validação humana x IA — colgate

Posts rotulados e classificados: **59**


## Sentimento (n = 59)

- Concordância simples: 91.5%
- Kappa de Cohen: **0.865** (IC 95% 0.739 a 0.971) — concordância quase perfeita

### Matriz de confusão (linhas = humano, colunas = IA)

| sentimento_humano | fora_do_tema | negativo | neutro | positivo |
|---|---|---|---|---|
| fora_do_tema | 29 | 0 | 0 | 0 |
| negativo | 0 | 8 | 3 | 1 |
| neutro | 1 | 0 | 16 | 0 |
| positivo | 0 | 0 | 0 | 1 |

### Por classe (humano como referência)

| classe | n_humano | n_ia | precisao | recall | f1 |
|---|---|---|---|---|---|
| fora_do_tema | 29 | 30 | 0.967 | 1.0 | 0.983 |
| negativo | 12 | 8 | 1.0 | 0.667 | 0.8 |
| neutro | 17 | 19 | 0.842 | 0.941 | 0.889 |
| positivo | 1 | 2 | 0.5 | 1.0 | 0.667 |

### Kappa por fase

- crise: kappa 1.000 (n = 23)
- pos_crise: kappa 0.250 (n = 7)
- pre_crise: kappa 1.000 (n = 10)
- reinterdicao: kappa 0.800 (n = 9)
- segunda_onda: kappa 0.861 (n = 10)

Divergências salvas em colgate_divergencias.csv (5 posts), das quais 3 com confiança baixa da IA.

## Eixo temático (n = 30)

- Concordância simples: 56.7%
- Kappa de Cohen: **0.457** (IC 95% 0.288 a 0.631) — concordância moderada


## Ironia (n = 30)

- Concordância simples: 93.3%
- Kappa de Cohen: **0.000** (IC 95% 0.000 a 1.000) — concordância pobre
