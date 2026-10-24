Você vai classificar o sentimento de publicações do X para um Trabalho de Conclusão de Curso em Relações Públicas (UFPR) sobre a crise da marca Colgate Total Clean Mint em 2025.

CONTEXTO DO CASO
O creme dental Colgate Total Prevenção Ativa Clean Mint substituiu a linha Total 12 em julho de 2024 e passou a acumular relatos de reações adversas (ardência, aftas, inchaço). A Anvisa interditou a venda em março de 2025; a Colgate recorreu, afirmou que não faria recolhimento e manteve o produto à venda enquanto o recurso valia. Depois retirou o recurso, o produto voltou a ser interditado e, em junho, a empresa anunciou o fim da fabricação.

O QUE CLASSIFICAR: o sentimento em relação à Colgate (marca, produto ou empresa). Não classifique o humor geral do post nem a opinião sobre outras pessoas.

SENTIMENTO (escolha um):
- negativo: relata reação ao produto, critica, acusa, expressa medo, decepção ou desconfiança, anuncia troca de marca ou critica a postura da empresa.
- positivo: defende ou elogia a marca, diz que usa sem problemas e vai continuar, ou avalia bem alguma atitude da empresa.
- neutro: informa sem opinar (compartilha notícia da Anvisa, pergunta qual lote foi afetado) ou menciona de passagem.
- fora_do_tema: não fala da marca: spam, promoção, sorteio.

EIXO TEMÁTICO (o assunto principal do post; escolha um):
- reacao_adversa_saude: sintomas, alergia, aftas, ardência, inchaço, ida ao médico.
- anvisa_regulacao: decisões da Anvisa, interdição, proibição, fiscalização.
- resposta_da_empresa: notas, recurso, recusa em recolher, comunicados da Colgate.
- mudanca_de_formula: troca da Total 12 pela Clean Mint, ingredientes, fluoreto estanoso.
- confianca_troca_de_marca: desconfiança, 'nunca mais compro', mudança para outra marca.
- atendimento_reembolso: SAC, troca, reembolso, devolução.
- humor_meme: piada ou meme sem assunto identificável entre os demais eixos.
- outro: nenhum dos anteriores.
Se o post é uma piada ou meme, o eixo é o assunto da piada. Use humor_meme só quando não houver assunto identificável.

IRONIA: "sim" quando o sentido literal contradiz o sentido pretendido (sarcasmo, elogio irônico); "nao" nos demais casos, inclusive piadas sem inversão de sentido.

CONFIANÇA: "alta" quando a leitura é inequívoca; "media" quando depende de uma interpretação razoável; "baixa" quando há dúvida real entre duas classes.

REGRAS:
- Ironia e sarcasmo contam pelo sentido, não pelas palavras ("que delícia escovar os dentes e ganhar três aftas de brinde" é negativo, eixo reacao_adversa_saude, ironia sim).
- Relato de sintoma em primeira pessoa é negativo, mesmo sem palavras de crítica.
- Pergunta com tom preocupado ("será que minha afta é da Colgate?") é negativo com confiança "media"; pergunta puramente informativa é neutro.
- Post que só menciona ou marca a marca, sem conteúdo avaliável, é neutro.
- Em caso de dúvida real entre duas classes, escolha a mais provável e marque confiança "baixa".
- Use apenas o texto do post. Não use informações externas ao texto e não suponha o conteúdo de imagens, vídeos ou links.
- Classifique todos os posts recebidos, na mesma ordem, sem pular nenhum.

SAÍDA: somente uma tabela CSV separada por ponto e vírgula, com o cabeçalho:
id;sentimento;eixo_tematico;ironia;confianca;justificativa
- ironia: sim ou nao; confianca: alta, media ou baixa (sem acento)
- justificativa: no máximo 15 palavras, sem ponto e vírgula

POSTS (id;texto):
{{POSTS}}
