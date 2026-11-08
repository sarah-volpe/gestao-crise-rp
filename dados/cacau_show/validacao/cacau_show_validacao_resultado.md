# Validação humana x IA — cacau_show

Posts rotulados e classificados: **83**


## Sentimento (n = 83)

- Concordância simples: 73.5%
- Kappa de Cohen: **0.628** (IC 95% 0.492 a 0.749) — concordância substancial

### Matriz de confusão (linhas = humano, colunas = IA)

| sentimento_humano | fora_do_tema | negativo | neutro | positivo |
|---|---|---|---|---|
| fora_do_tema | 29 | 0 | 6 | 4 |
| negativo | 2 | 12 | 4 | 1 |
| neutro | 1 | 1 | 6 | 3 |
| positivo | 0 | 0 | 0 | 14 |

### Por classe (humano como referência)

| classe | n_humano | n_ia | precisao | recall | f1 |
|---|---|---|---|---|---|
| fora_do_tema | 39 | 32 | 0.906 | 0.744 | 0.817 |
| negativo | 19 | 13 | 0.923 | 0.632 | 0.75 |
| neutro | 11 | 16 | 0.375 | 0.545 | 0.444 |
| positivo | 14 | 22 | 0.636 | 1.0 | 0.778 |

### Kappa por fase

- crise: kappa 0.649 (n = 42)
- pos_crise: kappa 0.663 (n = 20)
- pre_crise: kappa 0.508 (n = 21)

Divergências salvas em cacau_show_divergencias.csv (22 posts), das quais 6 com confiança baixa da IA.

## Eixo temático (n = 44)

- Concordância simples: 68.2%
- Kappa de Cohen: **0.469** (IC 95% 0.271 a 0.660) — concordância moderada


## Ironia (n = 44)

- Concordância simples: 75.0%
- Kappa de Cohen: **0.248** (IC 95% -0.042 a 0.536) — concordância razoável
