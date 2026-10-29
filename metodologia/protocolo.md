# Protocolo de coleta e classificação

Este documento descreve o procedimento em linguagem simples, as decisões de
método e as limitações. Ele é a referência para o capítulo de metodologia.

## 1. Onde fica cada coisa

| o quê | onde |
|---|---|
| datas, marcos, fases, buscas e critérios de cada caso | `casos/<caso>.yaml`, a ficha do caso e **único** lugar de configuração |
| texto dos prompts (igual para os três casos) | `metodologia/prompt_coleta.md` e `metodologia/prompt_analise.md` |
| prompts finais de cada caso (apêndice) | `metodologia/prompts_gerados/<caso>_coleta.md` e `<caso>_analise.md` |
| resultados | `dados/<caso>/` |

Os prompts finais são gerados juntando o modelo com a ficha do caso. Assim,
os três casos seguem literalmente o mesmo procedimento e só mudam os dados
de cada um, como pede o estudo de casos múltiplos (Yin, 2005).

## 2. Fases e linha de base

Cada caso tem uma **pré-crise**, que serve de linha de base (como se falava
da marca antes), uma **crise** que começa quando a repercussão aparece na
coleta (às vezes antes do primeiro marco oficial) e uma **pós-crise** de 14
dias.

| caso | pré-crise | crise | pós-crise | fases extras (opcionais) |
|---|---|---|---|---|
| Tânia Bulhões | 01–12/01/2025 | 13/01–14/02 | 15–28/02 | — |
| Colgate | 06–19/03/2025 | 20/03–10/04 | 11–24/04 | reinterdição 25/04–08/05; segunda onda 18/06–09/07 |
| Cacau Show | 12–25/05/2025 | 26/05–12/06 | 13–26/06 | — |

Cuidados de leitura:
- **Tânia Bulhões:** na primeira versão a pré-crise era 15–28/01, mas a
  coleta mostrou as primeiras publicações sobre a xícara da Tailândia entre
  13 e 16/01, o que contaminava a linha de base (40% de negativas). As fases
  foram redefinidas para pré-crise 01–12/01 e crise 13/01–14/02, antes da
  classificação final. Na nova pré-crise a marca quase não aparece no X:
  a linha de base tem poucas publicações e deve ser lida com cautela.
- **Colgate:** a pré-crise não é um período "normal", porque as queixas
  começaram em 2024 (68% das publicações sobre a marca nessa fase já são
  negativas). As fases foram mantidas, porque recuar a pré-crise não
  encontraria um período sem queixas; ela deve ser lida como "crise latente"
  anterior à interdição, e não como linha de base neutra. Na pós-crise o produto estava de volta à venda por
  causa do recurso. Em 30/04 a Anvisa voltou a interditar o produto, daí a
  fase de reinterdição.
- **Cacau Show:** a pré-crise começa logo depois do Dia das Mães, com mais
  promoções e sorteios (que caem em `fora_do_tema`).

## 3. Coleta

Segue `metodologia/prompt_coleta.md` e é executada pelo script
`src/tcc_coletar.py`, que abre a busca do X num navegador automatizado e
registra o que aparece na tela.

| regra do protocolo | como é cumprida | por quê |
|---|---|---|
| mesma busca principal em todas as fases | busca idêntica todos os dias | comparação válida entre fases |
| busca complementar só na crise | marcada como `origem = complementar`; post que aparece nas duas buscas fica como `principal` | não inflar a crise nem duplicar posts |
| uma busca por dia | uma busca por dia **UTC** + a do dia seguinte ao fim de cada fase; a data do post é a de Brasília | o X conta os dias em UTC; sem isso, posts das 21h às 24h cairiam no dia seguinte |
| até 15 posts por dia | lê até 300 e **sorteia** 15 por dia e origem, com semente fixa (2025) | os primeiros 15 de "Mais recentes" seriam só os da noite; o sorteio espalha a amostra e é reprodutível |
| volume do dia | contagem dos posts únicos válidos; "mais de 300" se bater o limite | número verificável no lugar de estimativa |
| texto exatamente como aparece | texto lido trecho a trecho, com emojis e links | o X desenha emojis como imagem e uma leitura simples os descartava |
| excluir anúncio, retuíte, outro idioma | filtro automático, com contagem registrada | auditável |
| excluir spam, homônimo, loja sem opinião | **não** é excluído na coleta: vira `fora_do_tema` na classificação | decisão de leitura fica registrada e entra na validação |
| anonimização | autores U001, U002…; link `x.com/i/status/<id>`; correspondência fora do repositório | o link padrão contém o @ do autor |

## 4. Classificação

Segue `metodologia/prompt_analise.md` e é executada por
`src/tcc_classificar.py`.

- O modelo recebe **só** `id;texto`, sem data, fase, autor ou engajamento.
- Lotes de até 50 posts, sorteados depois de embaralhar a base inteira, para
  que um lote não seja só de um dia ou fase.
- Cada eixo temático tem definição escrita (o "livro de códigos"), usada
  igualmente pela IA e pela validação humana.
- Respostas fora do formato (classe inexistente, post faltando) voltam para
  um novo lote, no máximo duas vezes; o número de retentativas é registrado.
- Ficam registrados: modelo, data, hash SHA-256 do prompt e distribuição dos
  resultados (`dados/<caso>/<caso>_classificacao_meta.json`).
- **Modo manual:** cada lote vira um arquivo de texto para colar no Claude
  (chat) e a resposta é salva ao lado, sem custo de API.

## 5. Validação humana

`src/tcc_validar.py` sorteia 12% dos posts de cada caso, com no mínimo 50,
proporcional às fases, e gera uma planilha só com id e texto, **sem a
resposta da IA**, para que o julgamento não seja influenciado. A pesquisadora
classifica com os mesmos critérios (aba "critérios" da planilha). Depois, o
script calcula:
- concordância simples e **kappa de Cohen** com intervalo de confiança de
  95%, para sentimento, eixo e ironia;
- matriz de confusão e precisão e recall por classe;
- kappa por fase e lista das divergências.

Interpretação do kappa (Landis; Koch, 1977): até 0,20 leve; 0,21–0,40
razoável; 0,41–0,60 moderada; 0,61–0,80 substancial; acima de 0,80 quase
perfeita.

## 6. Limitações a declarar

- Amostra por conveniência da busca do X, não censo. Posts apagados e contas
  suspensas desde 2025 não aparecem.
- Curtidas, respostas e reposts são os do dia da coleta, não os de 2025.
- Posts longos podem aparecer cortados na busca ("Mostrar mais"); ficam
  marcados em `dados/<caso>/<caso>_auditoria.csv`.
- A IA classifica só o texto: imagens e vídeos dos posts não são lidos. Respostas a outras publicações
  ("Poxa mãe!") aparecem sem o post original e tendem a cair em `fora_do_tema` ou `neutro`.
- Publicações dos perfis da própria marca (`contas_oficiais` na ficha) são excluídas: são comunicação da
  empresa, não opinião do público.
- Se a coleta antiga for reaproveitada (`src/tcc_importar_legado.py`), ela não
  tinha os filtros `lang:pt` e `-filter:retweets` na busca (aplicados depois),
  perdeu emojis e tinha limite de 200 posts por dia. Esses registros ficam
  marcados como `coleta_legada`.
  Na versão final, a Tânia Bulhões foi coletada de novo com o protocolo atual;
  a coleta antiga ficou guardada em `data/raw/x_tcc_legado/` e não entra nas tabelas.

## 7. Como executar

O passo a passo de execução (login no X, coleta, classificação, validação,
painel e envio ao GitHub) está em [`COMO_USAR.md`](../COMO_USAR.md).

### Painel

`painel/index.html` mostra, para cada caso: volume por dia com os marcos,
percentual de negativas por dia contra a linha de base da pré-crise,
sentimento por fase, eixos temáticos, publicações com mais engajamento,
validação humana e o registro da execução (modelo, hash do prompt, datas).
A aba "Comparação" põe os três casos lado a lado. O painel lê só os arquivos
públicos (sem o texto das publicações) e mostra "aguardando coleta" para
casos sem dados.

Para publicar: no GitHub, *Settings → Pages → Build and deployment →
Deploy from a branch → main / (root)*. O endereço fica
`https://sarah-volpe.github.io/gestao-crise-rp/`. Depois de cada etapa,
rode `python src\tcc_painel.py`, faça commit de `painel/dados.js` e dos
arquivos públicos de `dados/`, e envie.

Saídas em `dados/<caso>/`:

| arquivo | conteúdo | repositório público? |
|---|---|---|
| `<caso>_posts.csv` | tabela de publicações com texto | não |
| `<caso>_posts_publico.csv` | a mesma tabela sem o texto | sim |
| `<caso>_volume_diario.csv` | volume por dia | sim |
| `<caso>_classificacao.csv` e `_meta.json` | classificação da IA e registro da execução | sim |
| `validacao/<caso>_validacao_resultado.md` | kappa e matriz de confusão | sim |
| `<caso>_volume_detalhado.csv`, `_auditoria.csv`, `_montagem.json` | controle | sim |
| `data/privado/<caso>_autores.csv` | U001 → @perfil | **nunca** |

## 8. Rascunho para o capítulo de metodologia

> A coleta seguiu um protocolo único para os três casos (Apêndice A). Para
> cada dia das fases de pré-crise, crise e pós-crise, foi feita a mesma busca
> na aba "Mais recentes" da busca avançada do X. Na fase de crise, uma busca
> complementar ampliou a captura de termos específicos de cada caso. A busca
> foi executada por um script desenvolvido com auxílio de IA generativa, que
> registra as publicações exibidas na tela, até 300 por dia. O volume diário
> corresponde ao total de publicações únicas retornadas. De cada dia foram
> sorteadas até 15 publicações por origem de busca, com semente fixa, o que
> garante a reprodutibilidade e distribui a amostra ao longo do dia. Os
> autores foram anonimizados.
>
> A classificação de sentimento foi feita pelo modelo [MODELO], com o prompt
> do Apêndice B, em lotes de até 50 publicações embaralhadas e sem acesso a
> data, fase ou autor. Uma amostra de [N] publicações ([P]%), estratificada
> por fase, foi classificada de forma independente pela pesquisadora, sem
> acesso aos rótulos do modelo. A concordância foi medida pelo kappa de
> Cohen (κ = [K]; IC 95% [A]–[B]). Código, prompts e resultados estão
> disponíveis em [link do repositório].

Referência a acrescentar se a escala de interpretação for citada: LANDIS, J.
Richard; KOCH, Gary G. The measurement of observer agreement for categorical
data. **Biometrics**, v. 33, n. 1, p. 159–174, 1977.
