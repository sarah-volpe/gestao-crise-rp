# Monitor de crise em redes sociais — coleta e análise de sentimento

> **Protocolo do TCC (Tânia Bulhões, Colgate, Cacau Show):** ver
> [README_TCC.md](README_TCC.md). O restante deste arquivo descreve a
> pipeline exploratória (léxico, Reddit, American Eagle).

Pipeline gratuita e multi-caso: coleta posts do X (Twitter) e do Reddit sobre
uma crise de marca/reputação e classifica sentimento (positivo/negativo/neutro).
Pensado para múltiplos estudos de caso no mesmo projeto, sem misturar dados.

Entrega mínima por tópico: uma tabela (`.csv` + `.xlsx`) com **data do post,
texto, classificação de sentimento**, mais métricas de contexto (autor,
engajamento, eixo temático da crise).

---

## Estrutura de dados: fonte > tópico > período

```
data/raw/<fonte>/<topico>/<AAAA-MM>/posts.jsonl
data/raw/<fonte>/<topico>/checkpoint_queries.txt
data/processed/<fonte>/<topico>/<basename>.csv (+ .xlsx, gráficos, amostra de validação)
```

- **fonte**: `twitter` ou `reddit`.
- **tópico**: um estudo de caso — hoje `tania_bulhoes` e
  `american_eagle_sydney_sweeney`. Cada um tem seu próprio config em
  `config/<topico>.yaml` (termos de busca, período, eixos temáticos da
  crise, backend de sentimento).
- **período**: partição mensal (`AAAA-MM`), atribuída pela **data real do
  post** (não pela janela da query) — uma query "marca+preço" que cobre o
  período inteiro pode espalhar resultados por vários meses, e cada um vai
  pro arquivo certo automaticamente.

Fontes e tópicos nunca se misturam: coletar/processar `american_eagle_sydney_sweeney`
não toca em nada de `tania_bulhoes`, e Reddit nunca escreve em cima de dados do
Twitter. Isso é o que garante que ligar uma fonte/tópico novo é sempre um
incremento, nunca uma sobrescrita.

> Dados de antes dessa reestruturação (coleta original de `tania_bulhoes` no
> X, arquivos `tweets_*.jsonl` flat) foram migrados sem perda para
> `data/raw/twitter/tania_bulhoes/` — os 782 registros únicos batem exatamente
> com o que já existia. O formato antigo ficou preservado em
> `data/raw/_legacy_flat_backup/` e `data/processed/_legacy_flat_backup/`,
> só por precaução; pode ignorar essas pastas.

---

## Tópicos configurados

| tópico | fonte(s) | idioma | status |
|---|---|---|---|
| `tania_bulhoes` | twitter (reddit desligado) | pt | 781 posts coletados, 03/01–15/04/2025. Léxico validado (63,3% de acerto, ver seção de validação). |
| `american_eagle_sydney_sweeney` | twitter + reddit (ambos desligados por padrão) | en (+ pt) | config criado e datas/fatos **verificados via busca** (campanha lançada 23/07/2025, pico político ~04–07/08 com Trump e ação da AEO subindo 23%). **Nenhuma coleta rodada ainda** — as queries em si não foram testadas contra volume real, só desenhadas a partir da cobertura jornalística. Ligue `ativo: true` na fonte que quiser depois de revisar. Sentimento usa `llm` (conteúdo majoritariamente em inglês). |

Todo tópico nasce com `fontes.<fonte>.ativo: false` até você revisar os termos
e ligar explicitamente no config.

---

## Instalação

```powershell
cd d:\Projetos\tb-crise-xicara
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

---

## Fonte: X / Twitter

### Leia antes de rodar: o que é viável de graça

Coleta **histórica** no X é a parte difícil. Situação real:

| Caminho | Custo | Status |
|---|---|---|
| **scraping da busca pública** (`metodo: scrape`, padrão) | Grátis | Não usa conta logada contra API nenhuma — só lê o HTML da busca pública. Mais lento, sensível a mudança de layout do X. |
| `twscrape` (`metodo: twscrape`, opcional) | Grátis | Mais volume, mas usa contas logadas contra a API interna do X — **viola os ToS**, risco de suspensão. Só com contas descartáveis. |
| API oficial — Free/Basic | $0 / $200/mês | Busca limitada aos últimos 7 dias — inútil para eventos passados. |
| API oficial — Pro (full-archive) | **~$5.000/mês** | Único caminho 100% dentro dos ToS. |

Consequências para o método do TCC:

1. **Amostra por conveniência, não censo.** A busca do X não indexa tudo, e
   posts de contas suspensas/deletadas somem. Reporte volume coletado, não
   "volume total de menções".
2. **Campos são best-effort.** O scraper lê `data-testid`/`aria-label` do
   HTML público, que o X muda sem aviso. `author_followers` e `place` não
   ficam disponíveis; curtidas/reposts, `is_quote`/`is_reply` são
   aproximações — valide com `--debug-artifacts` antes de confiar.
3. **Risco de conta só no modo `twscrape`.** Use contas descartáveis, nunca
   pessoal/corporativa.

### Sessão do X (necessária, modo `scrape`)

O X hoje exige login até para busca. Use sempre uma **conta descartável**.

```powershell
python src\session_from_cookies.py --auth-token SEU_VALOR --ct0 SEU_VALOR
```

Pegue os valores fazendo login normal em x.com com a conta descartável, F12 →
Application → Cookies → `https://x.com` → copie `auth_token` e `ct0`.

Existe também `create_session.py` (login dentro do próprio Playwright), mas o
X costuma bloquear esse login automatizado com "Limitamos temporariamente seu
acesso" mesmo com senha digitada manualmente — prefira `session_from_cookies.py`.

O arquivo gerado (`storage_state.json`, não versionado) vale como uma senha:
nunca compartilhe. **A sessão expira/é derrubada com uso** — se a coleta
voltar a pedir login, gere de novo e rode `collect` de novo (o checkpoint
retoma sozinho de onde parou).

Valide um grupo de query antes de rodar tudo:

```powershell
python src\collect_x_scrape.py --topico tania_bulhoes --grupo marca_ampla --headed --debug-artifacts
```

Isso salva `debug/debug_page.png`, `debug_page.html`, `debug_meta.json`.

### Se X bloquear tudo: importação manual

```powershell
python src\import_manual_csv.py --input manual_posts.csv --raw-dir data/raw/twitter/<topico>
```

---

## Fonte: Reddit

Ao contrário do X, o Reddit tem **API oficial gratuita** para leitura pública
— sem scraping, sem sessão arriscada, sem risco de ban. É o motivo pelo qual
essa fonte foi adicionada: discussão mais aberta (sem paywall de login) e
sem o desgaste operacional que o X vem dando.

### Credenciais (grátis, 2 minutos)

1. Acesse [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) logado
   com sua conta Reddit.
2. "create app" → tipo **script**. Nome: qualquer um. Redirect URI:
   `http://localhost:8080` (não é usado, só precisa preencher algo válido).
3. Depois de criado: o `client_id` é o texto abaixo do nome do app; o
   `client_secret` é o campo "secret".
4. Configure as variáveis de ambiente **antes** de rodar (nunca coloque isso
   no config.yaml nem versione):

```powershell
$env:REDDIT_CLIENT_ID="seu_client_id"
$env:REDDIT_CLIENT_SECRET="seu_client_secret"
```

### Rodando

```powershell
python src\collect_reddit.py --topico tania_bulhoes
```

Busca por termo em uma lista de subreddits (ou `"all"` para o Reddit
inteiro), configurável em `fontes.reddit` no config do tópico. Para cada post
encontrado dentro do período, também traz os `comentarios_por_post` comentários
de maior score — é ali que costuma estar a discussão mais "quente" que citou
motivou essa fonte. Checkpoint resumível igual ao do X (`--no-resume` refaz
tudo).

Campos sem equivalente no Reddit (`views`, `quotes`, seguidores do autor)
ficam zerados/nulos — documentado na tabela de colunas mais abaixo.

---

## Uso

### Menu interativo (recomendado)

```powershell
python src\menu.py
```

Tela de terminal para escolher tópico, ligar/desligar X e Reddit nesta
sessão, selecionar quais endpoints rodar (grupos de query do X — `marca_ampla`,
`marca+modN`, `livreN` — ou subreddits do Reddit), ajustar `since`/`until` sem
tocar no YAML, gerenciar credenciais (Reddit, chave do LLM, sessão do X) e
disparar `collect`/`process`/`all` com o log ao vivo no próprio terminal.
Credenciais ficam salvas em `credentials.local.json` (fora do git — ver
`.gitignore`); alterações de fonte/endpoints/período valem só para a sessão
do menu, o `config/<topico>.yaml` não é sobrescrito.

### Linha de comando direta

```powershell
# inspecionar as queries do X antes de gastar tempo
python src\queries.py config\tania_bulhoes.yaml

# coletar (todas as fontes com ativo:true no config do tópico)
python src\run_pipeline.py collect --topico tania_bulhoes

# só uma fonte
python src\run_pipeline.py collect --topico tania_bulhoes --fonte twitter
python src\run_pipeline.py collect --topico american_eagle_sydney_sweeney --fonte reddit

# processar: dedup, filtros, sentimento, export
python src\run_pipeline.py process --topico tania_bulhoes

# tudo de uma vez
python src\run_pipeline.py all --topico tania_bulhoes
```

A coleta é **retomável** em ambas as fontes: cada combinação já concluída é
registrada em `data/raw/<fonte>/<topico>/checkpoint_queries.txt`. Se cair no
meio, rode `collect` de novo — ele pula o que já foi feito. `--no-resume`
força refazer tudo.

### Validar sem credenciais

```powershell
python demo\gerar_amostra.py
python src\run_pipeline.py process --config config.demo.yaml
```

(a demo é standalone, fora da estrutura fonte/tópico — só serve para conferir
o formato da tabela sem precisar de nenhuma credencial)

---

## Estratégia de busca no X

Três camadas por tópico, montadas em [src/queries.py](src/queries.py) a
partir de `fontes.twitter` no config:

1. **`marca_ampla`** — só os termos da marca/caso, **fatiado dia a dia**
   (recall muito maior que uma query única pro período inteiro).
2. **`marca+modN`** — marca × eixo da crise, período inteiro.
3. **`livreN`** — termos da crise sem exigir o nome da marca.

Nada de termo hardcoded no código — tudo fica no `config/<topico>.yaml`.

---

## Análise de sentimento

Backends, escolhidos em `sentimento.metodo` no config do tópico:

| método | idioma | dependência | quando usar |
|---|---|---|---|
| `lexicon` | **só PT-BR** | nenhuma | Léxico de ~300 termos calibrado para crise de marca, com negação, intensificadores, emoji, ironia explícita. Rápido e **auditável** — `sentimento_evidencia` mostra os termos que decidiram cada post. Usado em `tania_bulhoes`. |
| `transformer` | pt (BERTabaporu) | `pysentimiento` + `torch` (~2GB) | Alternativa gratuita ao léxico. Testado neste projeto: só 60% de concordância com o léxico, com um novo padrão de erro (interpreta comparação irônica com produto barato como elogio) — não é claramente melhor, ver seção de validação. |
| `llm` | **qualquer idioma** | ver `llm_provider` abaixo | Único backend usado para tópicos em inglês, como `american_eagle_sydney_sweeney` — o léxico é só PT-BR. O prompt é montado a partir de `descricao` no config do tópico (ver `src/sentiment_llm.py`), então cobre qualquer caso sem editar código. |
| `auto` | — | — | Tenta `transformer`, cai para `lexicon` se não estiver instalado. |

### Backend `llm`: dois provedores

Escolhido em `sentimento.llm_provider` no config do tópico:

| provider | modelo padrão | custo | variável de ambiente |
|---|---|---|---|
| `zai` | `glm-4.5-flash` | **grátis**, com rate limit | `ZAI_API_KEY` |
| `anthropic` | `claude-opus-5` | pago (poucos dólares no volume atual) | `ANTHROPIC_API_KEY` |

`american_eagle_sydney_sweeney` já vem configurado com `llm_provider: "zai"`
por padrão. Pra usar:

```powershell
pip install openai    # cliente usado para falar com o endpoint da Z.ai
$env:ZAI_API_KEY="sua_chave"
```

Chave gratuita em [z.ai/manage-apikey/apikey-list](https://z.ai/manage-apikey/apikey-list).
**Nunca cole a chave no config nem em código** — só como variável de
ambiente, do jeito acima. Se o rate limit do plano gratuito atrapalhar em
volumes grandes, aumente `lote_llm` (menos chamadas, lotes maiores) ou troque
pra `anthropic` (mais previsível, mas pago).

### Decisões metodológicas do léxico PT-BR

- **Termos do tópico não pontuam** (`crise`, `polêmica`, nome da marca) — pontuar o
  que é termo de busca jogaria a base inteira pro mesmo lado, viés de amostragem.
- **O alvo é a marca, não o humor do post.** Quem critica quem critica a marca
  conta como positivo.
- **`nada` não é negador** em PT-BR falado (reforça negação anterior ou é interjeição).
- **Ironia explícita inverte** (`sqn`, `só que não`, `🙃`); ironia possível
  (`kkkk`, `😂`) só reduz `sentimento_confianca`.

### Limite conhecido

Negatividade **implícita**, sem palavra de carga, passa como neutro (ex.:
comparação irônica, deboche via referência sem xingamento). É por isso que
`llm` existe como opção de reclassificação dos casos neutros/baixa confiança.

### Valide antes de reportar

```powershell
python src\amostra_validacao.py gerar --topico tania_bulhoes --fonte twitter
# preencha a coluna sentimento_manual no CSV gerado (positivo/negativo/neutro)
python src\amostra_validacao.py medir --topico tania_bulhoes --fonte twitter
```

Resultado já medido para `tania_bulhoes`: **63,3% de acerto geral** numa
amostra de 90 posts (30 por classe) — 83,3% em positivo, 65,6% em neutro,
56,5% em negativo (o léxico é mais fraco pra pegar negatividade indireta).
Repita esse processo para qualquer tópico/fonte novo antes de citar números
no relatório.

---

## Colunas da tabela final

`data/processed/<fonte>/<topico>/<basename>.csv`

| coluna | descrição |
|---|---|
| `data_post` | data (America/Sao_Paulo) |
| `data_hora_brasilia` | timestamp completo em horário de Brasília |
| `texto` | texto integral do post (ou comentário, no Reddit) |
| **`classificacao_sentimento`** | `positivo` / `negativo` / `neutro` |
| `sentimento_score` | −1,0 a +1,0 |
| `sentimento_confianca` | 0–1 |
| `sentimento_metodo` | backend usado (rastreabilidade) |
| `sentimento_evidencia` | termos/justificativa que decidiram a classificação |
| `eixo_principal`, `eixos` | eixos temáticos da crise, definidos por tópico em `config/<topico>.yaml` → `analise.eixos` |
| `cita_marca` | o post nomeia a marca/caso explicitamente? (`analise.marca_regex`) |
| `autor_usuario`, `autor_nome`, `autor_seguidores`, `autor_verificado` | autor. No Reddit, seguidores/verificado ficam sempre 0/false (sem equivalente público) |
| `curtidas`, `reposts`, `respostas`, `citacoes`, `visualizacoes` | métricas. No Reddit: curtidas=score, reposts=crossposts, respostas=nº de comentários, citações/visualizações sem equivalente (0) |
| `engajamento_total` | curtidas + reposts + respostas + citações |
| `eh_resposta`, `eh_citacao`, `idioma`, `tamanho_texto`, `hora_do_dia`, `semana_iso` | contexto |
| `subreddit`, `tipo` | só no Reddit: nome do subreddit, `post` ou `comentario` |
| `url`, `id`, `conversation_id`, `query_grupo` | rastreabilidade |

O `.xlsx` traz abas extras: `distribuicao`, `por_dia`, `por_eixo`, `top_engajamento`.

---

## Estrutura

```
config/
  tania_bulhoes.yaml                 termos, período, eixos, sentimento — tópico 1
  american_eagle_sydney_sweeney.yaml termos, período, eixos, sentimento — tópico 2 (revisar antes de coletar)
config.demo.yaml                     config standalone da demo offline

src/menu.py                   menu interativo de terminal: tópico, fontes/endpoints, período, credenciais, rodar
src/paths.py                 caminhos padronizados fonte > tópico > período
src/queries.py                matriz de queries do X (lê fontes.twitter do config)
src/collect_x_scrape.py       coleta via scraping da busca pública (Playwright, padrão)
src/collect_twscrape.py       coleta via twscrape, contas logadas (opcional, viola ToS)
src/collect_reddit.py         coleta via API oficial do Reddit (PRAW)
src/session_from_cookies.py   storage_state.json a partir de cookies de login manual (recomendado)
src/create_session.py         login dentro do Playwright -> storage_state.json (o X costuma bloquear)
src/import_manual_csv.py      fallback: converte CSV coletado à mão para o JSONL bruto
src/normalize.py              dedup, filtros, eixos temáticos (lidos do config do tópico)
src/sentiment.py              léxico PT-BR + backend transformer
src/sentiment_llm.py          backend Claude API — prompt montado a partir de `descricao` do tópico
src/run_pipeline.py           orquestrador (collect / process / all, --topico --fonte)
src/exportar_entrega.py       tabela simples (data/texto/sentimento) + gráfico de sentimento por semana/dia
src/amostra_validacao.py      amostra estratificada p/ validar o léxico à mão + taxa de acerto
demo/gerar_amostra.py         15 posts sintéticos para testar sem credenciais

data/raw/<fonte>/<topico>/<AAAA-MM>/posts.jsonl      bruto, particionado (não versionado)
data/raw/_legacy_flat_backup/                        arquivos anteriores à reestruturação
data/processed/<fonte>/<topico>/                     entregáveis .csv/.xlsx/gráficos (não versionado)
data/processed/_legacy_flat_backup/                  idem, entregáveis anteriores à reestruturação
```

> A base de scraping do X (`collect_x_scrape.py`, `create_session.py`,
> `import_manual_csv.py`) foi unificada a partir de um segundo protótipo do
> mesmo TCC (`sarah_tcc`, pipeline serverless no GCP com Playwright + Google
> Natural Language). A análise de sentimento e a estrutura de queries são o
> léxico PT-BR e o pipeline local deste projeto.

## Próximos passos naturais

- Revisar e coletar `american_eagle_sydney_sweeney` (twitter + reddit).
- Ligar `fontes.reddit` em `tania_bulhoes` para comparar volume/tom entre as duas redes.
- Instagram e TikTok, onde uma crise de marca de consumo costuma repercutir mais que no X.
- Reclame Aqui e Google Reviews (sentimento sobre compra, não sobre a polêmica em si).
- Tabela combinada entre fontes por tópico (`src/paths.py` já tem `combined_dir` pronto pra isso).
