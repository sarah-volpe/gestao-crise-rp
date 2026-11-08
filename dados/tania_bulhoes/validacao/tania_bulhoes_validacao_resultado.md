# Validação humana x IA — tania_bulhoes

Posts rotulados e classificados: **50**


## Sentimento (n = 50)

- Concordância simples: 78.0%
- Kappa de Cohen: **0.664** (IC 95% 0.474 a 0.826) — concordância substancial

### Matriz de confusão (linhas = humano, colunas = IA)

| sentimento_humano | fora_do_tema | negativo | neutro | positivo |
|---|---|---|---|---|
| fora_do_tema | 3 | 1 | 0 | 0 |
| negativo | 0 | 16 | 5 | 0 |
| neutro | 0 | 3 | 15 | 0 |
| positivo | 0 | 0 | 2 | 5 |

### Por classe (humano como referência)

| classe | n_humano | n_ia | precisao | recall | f1 |
|---|---|---|---|---|---|
| fora_do_tema | 4 | 3 | 1.0 | 0.75 | 0.857 |
| negativo | 21 | 20 | 0.8 | 0.762 | 0.78 |
| neutro | 18 | 22 | 0.682 | 0.833 | 0.75 |
| positivo | 7 | 5 | 1.0 | 0.714 | 0.833 |

### Kappa por fase

- crise: kappa 0.603 (n = 29)
- pos_crise: kappa 0.708 (n = 20)
- pre_crise: kappa 1.000 (n = 1)

Divergências salvas em tania_bulhoes_divergencias.csv (11 posts), das quais 6 com confiança baixa da IA.

## Eixo temático (n = 46)

- Concordância simples: 63.0%
- Kappa de Cohen: **0.569** (IC 95% 0.401 a 0.727) — concordância moderada


## Ironia (n = 46)

- Concordância simples: 87.0%
- Kappa de Cohen: **0.618** (IC 95% 0.311 a 0.872) — concordância substancial
