Você vai coletar publicações públicas do X (antigo Twitter) para um Trabalho de Conclusão de Curso em Relações Públicas (UFPR) sobre monitoramento de crises de marca com apoio de inteligência artificial generativa.

CASO: Colgate Total Clean Mint (2025)
O creme dental Colgate Total Prevenção Ativa Clean Mint substituiu a linha Total 12 em julho de 2024 e passou a acumular relatos de reações adversas (ardência, aftas, inchaço). A Anvisa interditou a venda em março de 2025; a Colgate recorreu, afirmou que não faria recolhimento e manteve o produto à venda enquanto o recurso valia. Depois retirou o recurso, o produto voltou a ser interditado e, em junho, a empresa anunciou o fim da fabricação.

MARCOS DO CASO (só para situar as fases; não use para escolher posts)
- 27/03/2025: Anvisa interdita cautelarmente venda e consumo
- 01/04/2025: Colgate recorre; interdição fica suspensa durante o recurso; empresa diz que não fará recolhimento
- 30/04/2025: Colgate retira o recurso e a Anvisa volta a interditar o produto
- 25/06/2025: Colgate anuncia que vai parar de fabricar o Clean Mint

PERÍODO E FASES (horário de Brasília; o último dia de cada fase está incluído)
- pre_crise: 06/03/2025 a 19/03/2025
- crise: 20/03/2025 a 10/04/2025
- pos_crise: 11/04/2025 a 24/04/2025
- reinterdicao: 25/04/2025 a 08/05/2025 (opcional: colete se houver tempo)
- segunda_onda: 18/06/2025 a 09/07/2025 (opcional: colete se houver tempo)
Atenção: as reclamações sobre o produto começaram em 2024, então a pré-crise (06 a 19/03) não é um período "normal": ela registra os sinais anteriores à decisão da Anvisa. Os relatos de reação adversa desse período devem ser coletados normalmente. Na pós-crise (11 a 24/04) o produto estava à venda por causa do recurso.

BUSCA PRINCIPAL (a mesma em todas as fases, para que a comparação entre fases seja válida):
(Colgate OR @ColgateBrasil) ("creme dental" OR "pasta de dente" OR "pasta de dentes" OR "Clean Mint" OR "Total 12" OR Anvisa OR alergia OR alérgica OR afta OR aftas OR ardência OR boca OR língua OR lábio OR lábios OR gengiva OR inchaço OR interditada OR proibida OR recolhimento) lang:pt -filter:retweets

BUSCA COMPLEMENTAR (somente nas fases: crise, reinterdicao, segunda_onda; marque essas publicações com origem = "complementar"):
("Clean Mint" OR "fluoreto estanoso" OR "Colgate Total" OR "Total Prevenção Ativa") lang:pt -filter:retweets
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
- id: CG-001, CG-002... em ordem cronológica
- autor_anonimizado: U001, U002... (a correspondência com o @ fica numa tabela separada, que não vai para o trabalho)
- curtidas, respostas e reposts: como aparecem no dia da coleta; registre a data da coleta

SAÍDA 2 — volume por dia (todos os dias das fases, inclusive os sem publicações):
data;fase;posts_coletados;volume_estimado_no_dia
