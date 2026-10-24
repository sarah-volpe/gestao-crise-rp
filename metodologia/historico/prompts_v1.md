# Prompts de pesquisa — versão 1 (substituída)

Versão anterior dos prompts, mantida para registro. A versão em uso é gerada
a partir de `metodologia/prompt_coleta.md`, `metodologia/prompt_analise.md` e
das fichas em `casos/`. As diferenças estão em
`metodologia/prompts_de_desenvolvimento.md`.

---

## TÂNIA BULHÕES

### Coleta de dados

Você vai me ajudar a coletar publicações públicas do X (antigo Twitter) para um Trabalho de Conclusão de Curso em Relações Públicas (UFPR) sobre monitoramento de crises de marca.

CASO: crise da marca Tânia Bulhões (2025). Uma influenciadora mostrou no TikTok uma xícara idêntica à da coleção Marquesa sendo usada num café simples na Tailândia, o que gerou questionamentos sobre origem de fabricação, preço e autenticidade. A marca falou em medidas jurídicas (04/02/2025), descontinuou quatro coleções (07/02/2025) e ofereceu troca ou devolução.

PERÍODO E FASES (o operador until: do X não inclui o dia informado):
- Pré-crise: 15/01/2025 a 28/01/2025
- Crise: 29/01/2025 a 14/02/2025
- Pós-crise: 15/02/2025 a 28/02/2025

BUSCA PRINCIPAL (a mesma em todas as fases, para que a comparação entre fases seja válida):
("Tânia Bulhões" OR "Tania Bulhões" OR "Tania Bulhoes" OR taniabulhoes OR @taniabulhoes) lang:pt -filter:retweets

BUSCA COMPLEMENTAR (somente na fase de crise; marque essas publicações com origem = "complementar"):
("xícara Marquesa" OR "xicara marquesa" OR "xícara da Tailândia" OR "porcelana Tânia") lang:pt -filter:retweets

PROCEDIMENTO:
1. Use a busca avançada do X na aba "Mais recentes".
2. Faça uma busca por dia, acrescentando since:AAAA-MM-DD until:AAAA-MM-DD (dia seguinte).
3. Colete no máximo 15 publicações por dia. Se o dia tiver menos, colete todas.
4. Para cada dia, anote também uma estimativa de quantas publicações apareceram no total (ex.: "~8", "mais de 100"). O volume é um dado da pesquisa.
5. Inclua: posts originais e respostas em português que falem da marca.
6. Exclua: retuítes puros, anúncios, spam, perfis de lojas revendendo produtos sem opinião e posts em que "Tânia" claramente se refere a outra pessoa.

REGRA ESSENCIAL: registre somente publicações que você realmente viu na tela, com o link. Nunca invente, resuma ou reconstrua um post. Se não conseguir acessar o X ou a busca não retornar nada, diga isso claramente em vez de preencher a tabela.

SAÍDA: uma tabela em formato CSV com as colunas:
id;data;fase;origem;link;autor_anonimizado;texto_integral;curtidas;respostas;reposts
- id: TB-001, TB-002...
- autor_anonimizado: U001, U002... (guarde a correspondência com o @ numa tabela separada, que não vai para o trabalho)
- texto_integral: o texto exatamente como aparece

Ao final, entregue uma segunda tabela com o volume por dia:
data;fase;posts_coletados;volume_estimado_no_dia

### Análise de sentimentos

Você vai classificar o sentimento de publicações do X para um TCC em Relações Públicas (UFPR) sobre a crise da marca Tânia Bulhões em 2025 (xícara da coleção Marquesa encontrada num café na Tailândia; questionamentos sobre origem, preço e autenticidade; notas da marca, descontinuação de coleções e oferta de troca ou devolução).

O QUE CLASSIFICAR: o sentimento EM RELAÇÃO À MARCA TÂNIA BULHÕES, não o humor geral do post.
- negativo: critica, ironiza, ridiculariza, acusa ou expressa decepção com a marca, os produtos, os preços ou a resposta dela. Memes que zombam da marca são negativos.
- positivo: defende, elogia ou declara intenção de continuar comprando; avalia bem a resposta da marca.
- neutro: informa sem opinar (compartilha notícia, pergunta, descreve o caso) ou menciona a marca de passagem.
- fora_do_tema: não fala da marca (spam, homônimo, propaganda).

EIXO TEMÁTICO (escolha o principal):
origem_fabricacao | preco_valor | autenticidade_fraude | resposta_da_marca | historico_da_fundadora | humor_meme | luxo_e_classe_social | outro

REGRAS:
- Ironia e sarcasmo contam pelo sentido, não pelas palavras ("amei pagar R$ 200 numa xícara da Tailândia" é negativo).
- Em caso de dúvida real entre duas classes, escolha a mais provável e marque confiança "baixa".
- Não use informações externas ao texto do post.
- Classifique todos os posts recebidos, na mesma ordem, sem pular nenhum.

SAÍDA: somente uma tabela CSV com as colunas:
id;sentimento;eixo_tematico;ironia(sim/nao);confianca(alta/media/baixa);justificativa
A justificativa deve ter no máximo 15 palavras.

POSTS (id;texto):
[cole aqui um lote de até 50 posts]

---

## COLGATE

### Coleta de dados

Você vai me ajudar a coletar publicações públicas do X (antigo Twitter) para um Trabalho de Conclusão de Curso em Relações Públicas (UFPR) sobre monitoramento de crises de marca.

CASO: crise do creme dental Colgate Total Clean Mint (2025). O produto substituiu a linha Total 12 em julho de 2024 e passou a acumular relatos de reações adversas (ardência, aftas, inchaço). A Anvisa interditou a venda em 27/03/2025; a Colgate recorreu, disse que não faria recolhimento e manteve o produto à venda. Em 25/06/2025 a empresa anunciou a suspensão das vendas.

PERÍODO E FASES (o operador until: do X não inclui o dia informado):
Janela principal:
- Pré-crise: 06/03/2025 a 19/03/2025
- Crise: 20/03/2025 a 10/04/2025
- Pós-crise: 11/04/2025 a 24/04/2025
Segunda onda (colete se houver tempo; marque fase = "segunda_onda"):
- 18/06/2025 a 09/07/2025

BUSCA PRINCIPAL (a mesma em todas as fases):
(Colgate OR @ColgateBrasil) ("creme dental" OR "pasta de dente" OR "pasta de dentes" OR "Clean Mint" OR "Total 12" OR Anvisa OR alergia OR afta OR aftas OR ardência OR boca) lang:pt -filter:retweets

BUSCA COMPLEMENTAR (somente nas fases de crise e segunda onda; marque origem = "complementar"):
("Clean Mint" OR "fluoreto estanoso" OR "Colgate Total") lang:pt -filter:retweets

PROCEDIMENTO:
1. Use a busca avançada do X na aba "Mais recentes".
2. Faça uma busca por dia, acrescentando since:AAAA-MM-DD until:AAAA-MM-DD (dia seguinte).
3. Colete no máximo 15 publicações por dia. Se o dia tiver menos, colete todas.
4. Para cada dia, anote também uma estimativa de quantas publicações apareceram no total.
5. Inclua: posts originais e respostas em português que falem da marca ou do produto.
6. Exclua: retuítes puros, anúncios, promoções de supermercado, spam e sorteios.

ATENÇÃO À PRÉ-CRISE: se já houver relatos de reações adversas antes de 27/03, colete-os normalmente. Eles são importantes para a pesquisa, porque mostram sinais da crise antes da decisão oficial.

REGRA ESSENCIAL: registre somente publicações que você realmente viu na tela, com o link. Nunca invente, resuma ou reconstrua um post. Se não conseguir acessar o X ou a busca não retornar nada, diga isso claramente em vez de preencher a tabela.

SAÍDA: uma tabela em formato CSV com as colunas:
id;data;fase;origem;link;autor_anonimizado;texto_integral;curtidas;respostas;reposts
- id: CG-001, CG-002...
- autor_anonimizado: U001, U002... (guarde a correspondência com o @ numa tabela separada, que não vai para o trabalho)

Ao final, entregue uma segunda tabela com o volume por dia:
data;fase;posts_coletados;volume_estimado_no_dia

### Análise de sentimentos

Você vai classificar o sentimento de publicações do X para um TCC em Relações Públicas (UFPR) sobre a crise do creme dental Colgate Total Clean Mint em 2025 (relatos de reações adversas, interdição pela Anvisa em 27/03, recurso da empresa sem recolhimento, suspensão das vendas em 25/06).

O QUE CLASSIFICAR: o sentimento EM RELAÇÃO À COLGATE (marca, produto ou empresa), não o humor geral do post.
- negativo: relata reação ao produto, critica, acusa, expressa medo, decepção ou desconfiança; anuncia troca de marca; critica a postura da empresa.
- positivo: defende, elogia, diz que usa sem problemas e vai continuar; avalia bem alguma atitude da empresa.
- neutro: informa sem opinar (compartilha notícia da Anvisa, pergunta qual lote foi afetado) ou menciona de passagem.
- fora_do_tema: não fala da marca (spam, promoção, sorteio).

EIXO TEMÁTICO (escolha o principal):
reacao_adversa_saude | anvisa_regulacao | resposta_da_empresa | mudanca_de_formula | confianca_troca_de_marca | atendimento_reembolso | humor_meme | outro

REGRAS:
- Relato de sintoma em primeira pessoa é negativo, mesmo sem palavras de crítica.
- Pergunta com tom preocupado ("será que minha afta é da Colgate?") é negativo com confiança "media"; pergunta puramente informativa é neutro.
- Ironia e sarcasmo contam pelo sentido, não pelas palavras.
- Em caso de dúvida real, escolha a classe mais provável e marque confiança "baixa".
- Não use informações externas ao texto do post.
- Classifique todos os posts recebidos, na mesma ordem, sem pular nenhum.

SAÍDA: somente uma tabela CSV com as colunas:
id;sentimento;eixo_tematico;ironia(sim/nao);confianca(alta/media/baixa);justificativa
A justificativa deve ter no máximo 15 palavras.

POSTS (id;texto):
[cole aqui um lote de até 50 posts]

---

## CACAU SHOW

### Coleta de dados

Você vai me ajudar a coletar publicações públicas do X (antigo Twitter) para um Trabalho de Conclusão de Curso em Relações Públicas (UFPR) sobre monitoramento de crises de marca.

CASO: crise da Cacau Show (2025). Franqueados e ex-funcionários fizeram denúncias (assédio, pressão sobre franqueados, "rituais" corporativos apelidados de "seita da Cacau Show"), reunidas pelo perfil "A Doce Amargura" e publicadas pelo Metrópoles em 29/05/2025. A marca publicou comunicado em 02/06/2025, o CEO Alê Costa apareceu no MasterChef em 03/06/2025 e o caso chegou ao Ministério Público do Trabalho.

PERÍODO E FASES (o operador until: do X não inclui o dia informado):
- Pré-crise: 12/05/2025 a 25/05/2025
- Crise: 26/05/2025 a 12/06/2025
- Pós-crise: 13/06/2025 a 26/06/2025

BUSCA PRINCIPAL (a mesma em todas as fases):
("Cacau Show" OR cacaushow OR @cacaushow OR "Alê Costa" OR "Ale Costa") lang:pt -filter:retweets

BUSCA COMPLEMENTAR (somente na fase de crise; marque origem = "complementar"):
("Doce Amargura" OR "seita da Cacau" OR "ritual do cacau" OR "franqueados Cacau" OR "boicote Cacau") lang:pt -filter:retweets

PROCEDIMENTO:
1. Use a busca avançada do X na aba "Mais recentes".
2. Faça uma busca por dia, acrescentando since:AAAA-MM-DD until:AAAA-MM-DD (dia seguinte).
3. Colete no máximo 15 publicações por dia. Se o dia tiver menos, colete todas.
4. Para cada dia, anote também uma estimativa de quantas publicações apareceram no total.
5. Inclua: posts originais e respostas em português que falem da marca, da empresa ou do CEO no contexto da empresa.
6. Exclua: retuítes puros, anúncios, promoções, sorteios, golpes de "promoção falsa" e spam.

REGRA ESSENCIAL: registre somente publicações que você realmente viu na tela, com o link. Nunca invente, resuma ou reconstrua um post. Se não conseguir acessar o X ou a busca não retornar nada, diga isso claramente em vez de preencher a tabela.

SAÍDA: uma tabela em formato CSV com as colunas:
id;data;fase;origem;link;autor_anonimizado;texto_integral;curtidas;respostas;reposts
- id: CS-001, CS-002...
- autor_anonimizado: U001, U002... (guarde a correspondência com o @ numa tabela separada, que não vai para o trabalho)

Ao final, entregue uma segunda tabela com o volume por dia:
data;fase;posts_coletados;volume_estimado_no_dia

### Análise de sentimentos

Você vai classificar o sentimento de publicações do X para um TCC em Relações Públicas (UFPR) sobre a crise da Cacau Show em 2025 (denúncias de franqueados e ex-funcionários sobre assédio, pressão comercial e "rituais" corporativos; perfil "A Doce Amargura"; reportagem do Metrópoles em 29/05; comunicado da marca em 02/06; CEO Alê Costa no MasterChef em 03/06; inquérito no MPT).

O QUE CLASSIFICAR: o sentimento EM RELAÇÃO À CACAU SHOW (marca, empresa ou CEO enquanto representante da empresa), não o humor geral do post.
- negativo: critica, acusa, ironiza, chama de "seita", anuncia boicote, expressa indignação ou decepção com a empresa ou com a resposta dela.
- positivo: defende a empresa, desacredita as denúncias, elogia produtos ou o CEO, declara que vai continuar comprando.
- neutro: informa sem opinar (compartilha notícia, pergunta o que aconteceu) ou menciona de passagem.
- fora_do_tema: não fala da marca (spam, promoção, sorteio, golpe).

EIXO TEMÁTICO (escolha o principal):
condicoes_de_trabalho_assedio | relacao_com_franqueados | seita_rituais | resposta_da_empresa_ceo | boicote_consumo | exposicao_midiatica_masterchef | defesa_da_marca | humor_meme | outro

REGRAS:
- Ironia e sarcasmo contam pelo sentido, não pelas palavras ("vou ali comprar um ovo abençoado" é negativo).
- Críticas a quem fez as denúncias, sem crítica à marca, são positivas para a marca (eixo defesa_da_marca).
- Em caso de dúvida real, escolha a classe mais provável e marque confiança "baixa".
- Não use informações externas ao texto do post.
- Classifique todos os posts recebidos, na mesma ordem, sem pular nenhum.

SAÍDA: somente uma tabela CSV com as colunas:
id;sentimento;eixo_tematico;ironia(sim/nao);confianca(alta/media/baixa);justificativa
A justificativa deve ter no máximo 15 palavras.

POSTS (id;texto):
[cole aqui um lote de até 50 posts]
