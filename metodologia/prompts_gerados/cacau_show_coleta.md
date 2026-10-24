Você vai coletar publicações públicas do X (antigo Twitter) para um Trabalho de Conclusão de Curso em Relações Públicas (UFPR) sobre monitoramento de crises de marca com apoio de inteligência artificial generativa.

CASO: Cacau Show (2025)
Franqueados e ex-funcionários fizeram denúncias contra a Cacau Show (assédio, pressão sobre franqueados e "rituais" corporativos apelidados de "seita da Cacau Show"), reunidas pelo perfil "A Doce Amargura" e publicadas pelo Metrópoles. A marca divulgou comunicado, o CEO Alê Costa apareceu no MasterChef no dia seguinte e o caso chegou ao Ministério Público do Trabalho.

MARCOS DO CASO (só para situar as fases; não use para escolher posts)
- 29/05/2025: Metrópoles publica as denúncias reunidas pelo perfil A Doce Amargura
- 02/06/2025: Cacau Show divulga comunicado e explica os 'rituais'
- 03/06/2025: CEO Alê Costa aparece no MasterChef
- data a confirmar: Caso chega ao Ministério Público do Trabalho

PERÍODO E FASES (horário de Brasília; o último dia de cada fase está incluído)
- pre_crise: 12/05/2025 a 25/05/2025
- crise: 26/05/2025 a 12/06/2025
- pos_crise: 13/06/2025 a 26/06/2025
A pré-crise (12 a 25/05) é a linha de base. Atenção à sazonalidade: ela começa no dia seguinte ao Dia das Mães (11/05/2025), data forte para chocolates; promoções e sorteios do período tendem a cair em fora_do_tema.

BUSCA PRINCIPAL (a mesma em todas as fases, para que a comparação entre fases seja válida):
("Cacau Show" OR cacaushow OR @cacaushow OR "Alê Costa" OR "Ale Costa") lang:pt -filter:retweets

BUSCA COMPLEMENTAR (somente nas fases: crise; marque essas publicações com origem = "complementar"):
("Doce Amargura" OR "seita da Cacau" OR "ritual do cacau" OR "rituais da Cacau" OR "franqueados Cacau" OR "boicote Cacau") lang:pt -filter:retweets
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
- id: CS-001, CS-002... em ordem cronológica
- autor_anonimizado: U001, U002... (a correspondência com o @ fica numa tabela separada, que não vai para o trabalho)
- curtidas, respostas e reposts: como aparecem no dia da coleta; registre a data da coleta

SAÍDA 2 — volume por dia (todos os dias das fases, inclusive os sem publicações):
data;fase;posts_coletados;volume_estimado_no_dia
