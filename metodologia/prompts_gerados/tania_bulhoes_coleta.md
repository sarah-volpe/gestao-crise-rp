Você vai coletar publicações públicas do X (antigo Twitter) para um Trabalho de Conclusão de Curso em Relações Públicas (UFPR) sobre monitoramento de crises de marca com apoio de inteligência artificial generativa.

CASO: Tânia Bulhões (2025)
Uma influenciadora mostrou no TikTok uma xícara idêntica à da coleção Marquesa, da Tânia Bulhões, sendo usada num café simples na Tailândia. O vídeo gerou questionamentos sobre a origem de fabricação, o preço e a autenticidade das porcelanas da marca. A marca se pronunciou, descontinuou coleções e ofereceu troca ou devolução aos clientes.

MARCOS DO CASO (só para situar as fases; não use para escolher posts)
- 04/02/2025: Marca fala em medidas jurídicas
- 07/02/2025: Marca anuncia no Instagram a descontinuação de coleções
- 12/02/2025: Imprensa noticia oferta de troca ou devolução das porcelanas

PERÍODO E FASES (horário de Brasília; o último dia de cada fase está incluído)
- pre_crise: 15/01/2025 a 28/01/2025
- crise: 29/01/2025 a 14/02/2025
- pos_crise: 15/02/2025 a 28/02/2025
A pré-crise (15 a 28/01) é a linha de base: mostra como se falava da marca antes da repercussão do vídeo.

BUSCA PRINCIPAL (a mesma em todas as fases, para que a comparação entre fases seja válida):
("Tânia Bulhões" OR "Tania Bulhões" OR "Tânia Bulhoes" OR "Tania Bulhoes" OR taniabulhoes OR @taniabulhoes) lang:pt -filter:retweets

BUSCA COMPLEMENTAR (somente nas fases: crise; marque essas publicações com origem = "complementar"):
("xícara Marquesa" OR "xicara marquesa" OR "xícara da Tailândia" OR "xicara da tailandia" OR "crise da xícara" OR "crise da xicara" OR "porcelana Tânia") lang:pt -filter:retweets
Uma publicação que aparecer nas duas buscas conta como origem = "principal".

PROCEDIMENTO:
1. Use a busca avançada do X na aba "Mais recentes".
2. Faça uma busca por dia, acrescentando since:AAAA-MM-DD until:AAAA-MM-DD (dia seguinte). O X conta os dias em UTC (3 horas à frente de Brasília). Por isso, faça também a busca do dia seguinte ao último dia de cada fase e registre a data de cada publicação pelo horário de Brasília em que ela foi publicada, não pela busca em que ela apareceu.
3. Leia todas as publicações que a busca retornar no dia, até 300. O total de publicações válidas é o volume do dia. Se passar de 300, registre "mais de 300".
4. Se o dia tiver até 15 publicações válidas por origem, registre todas. Se tiver mais, sorteie 15 entre todas as do dia (não pegue as primeiras da lista: na aba "Mais recentes" elas são só as últimas horas do dia). Registre como o sorteio foi feito.
5. Inclua: posts originais e respostas em português que falem da marca, do produto, da empresa ou de seus representantes no contexto da empresa.
6. Exclua: retuítes puros, anúncios (marcados como "Promovido"), publicações em outro idioma e publicações fora das fases. Não exclua por leitura de conteúdo (spam, homônimo, loja revendendo): essas publicações seguem para a análise de sentimento, que as marca como "fora_do_tema".
7. Registre o link no formato https://x.com/i/status/<número do post>, que não mostra o nome do autor.

REGRA ESSENCIAL: registre somente publicações que você realmente viu na tela, com o link. Nunca invente, resuma ou reconstrua um post. Copie o texto exatamente como aparece, com emojis e links. Se não conseguir acessar o X, se a busca não retornar nada ou se o X bloquear a busca, registre isso para aquele dia em vez de preencher a tabela.

SAÍDA 1 — publicações (CSV separado por ponto e vírgula):
id;data;fase;origem;link;autor_anonimizado;texto_integral;curtidas;respostas;reposts
- id: TB-001, TB-002... em ordem cronológica
- autor_anonimizado: U001, U002... (a correspondência com o @ fica numa tabela separada, que não vai para o trabalho)
- curtidas, respostas e reposts: como aparecem no dia da coleta; registre a data da coleta

SAÍDA 2 — volume por dia (todos os dias das fases, inclusive os sem publicações):
data;fase;posts_coletados;volume_estimado_no_dia
