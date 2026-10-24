Você vai classificar o sentimento de publicações do X para um Trabalho de Conclusão de Curso em Relações Públicas (UFPR) sobre a crise da marca {{nome}} em {{ano}}.

CONTEXTO DO CASO
{{contexto}}

O QUE CLASSIFICAR: o sentimento em relação {{alvo}}. Não classifique o humor geral do post nem a opinião sobre outras pessoas.

SENTIMENTO (escolha um):
{{sentimentos}}

EIXO TEMÁTICO (o assunto principal do post; escolha um):
{{eixos}}
Se o post é uma piada ou meme, o eixo é o assunto da piada. Use humor_meme só quando não houver assunto identificável.

IRONIA: "sim" quando o sentido literal contradiz o sentido pretendido (sarcasmo, elogio irônico); "nao" nos demais casos, inclusive piadas sem inversão de sentido.

CONFIANÇA: "alta" quando a leitura é inequívoca; "media" quando depende de uma interpretação razoável; "baixa" quando há dúvida real entre duas classes.

REGRAS:
- Ironia e sarcasmo contam pelo sentido, não pelas palavras ({{exemplo_ironia}}).
{{regras_especificas}}- Post que só menciona ou marca a marca, sem conteúdo avaliável, é neutro.
- Em caso de dúvida real entre duas classes, escolha a mais provável e marque confiança "baixa".
- Use apenas o texto do post. Não use informações externas ao texto e não suponha o conteúdo de imagens, vídeos ou links.
- Classifique todos os posts recebidos, na mesma ordem, sem pular nenhum.

SAÍDA: somente uma tabela CSV separada por ponto e vírgula, com o cabeçalho:
id;sentimento;eixo_tematico;ironia;confianca;justificativa
- ironia: sim ou nao; confianca: alta, media ou baixa (sem acento)
- justificativa: no máximo 15 palavras, sem ponto e vírgula

POSTS (id;texto):
{{POSTS}}
