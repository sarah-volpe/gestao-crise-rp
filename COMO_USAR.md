# Como usar: passo a passo

Guia para quem vai **executar** a coleta e a análise. Para entender o método,
leia `metodologia/protocolo.md`.

**Como funciona a divisão de trabalho:** tudo roda no seu computador. O
GitHub só guarda o código e os resultados públicos e exibe o painel. A
ordem é sempre: rodar uma etapa no computador, conferir o resultado e
enviar para o GitHub.

```
[seu computador]                                        [GitHub]
login no X → coleta → montagem → classificação →
validação → painel  ───── git push (só arquivos públicos) ─────→  repositório + painel
```

Comandos para o PowerShell, dentro da pasta do projeto. Troque
`tania_bulhoes` por `colgate` ou `cacau_show` para os outros casos.

---

## 0. Preparar o computador (uma vez só)

```powershell
cd D:\Projetos\tb-crise-xicara
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

Nas próximas vezes, basta ativar o ambiente:
`.\.venv\Scripts\Activate.ps1`.

## 1. Fazer login no X (quando a sessão expirar)

O X só mostra resultados de busca para quem está logado. Use uma **conta
descartável**, nunca a pessoal: a coleta automatizada pode levar o X a
bloquear a conta.

```powershell
python src\login_x.py
```

1. Abre uma janela do Chrome (ou do Edge) separada da que você usa no dia a
   dia.
2. Faça login no X com a conta descartável.
3. Quando a página inicial do X carregar, o script grava a sessão e fecha a
   janela sozinho.

Da segunda vez em diante, o mesmo comando renova a sessão sem pedir login,
porque o perfil dessa janela fica salvo na pasta `.sessao_x`. Para trocar
de conta, use `python src\login_x.py --novo-perfil`.

A sessão (`storage_state.json`) e a pasta `.sessao_x` funcionam como a
senha da conta. As duas já estão fora do git e não devem ser
compartilhadas. Quando a coleta avisar "X pediu login", rode este passo de
novo e repita o comando da coleta: ela continua de onde parou.

<details>
<summary>Alternativa manual (se o script não achar o navegador)</summary>

1. No navegador, entre em x.com com a conta descartável.
2. Aperte F12 → aba **Application** → **Cookies** → `https://x.com`.
3. Copie os valores de `auth_token` e `ct0`.
4. Rode `python src\session_from_cookies.py --auth-token COLE_AQUI --ct0 COLE_AQUI`.

Ou indique o navegador: `python src\login_x.py --navegador "C:\caminho\chrome.exe"`.
</details>

## 2. Testar com um dia

```powershell
python src\tcc_coletar.py --caso tania_bulhoes --so-dia 2025-02-04 --headed
```

O `--headed` abre o navegador para você ver a busca acontecendo. Confira se
aparecem publicações e se o terminal mostra algo como `-> 87 posts`. Se vier
`0 posts` num dia que deveria ter publicações, a sessão ou a busca têm
problema. Resolva isso antes de seguir.

## 3. Coletar o caso inteiro

```powershell
python src\tcc_coletar.py --caso tania_bulhoes
python src\tcc_coletar.py --caso colgate --incluir-opcionais    # inclui reinterdição e segunda onda
python src\tcc_coletar.py --caso cacau_show
```

- São de 60 a 120 buscas por caso, cada uma levando de 20 segundos a 2
  minutos. Reserve **de 30 minutos a 3 horas por caso**, com o computador
  ligado.
- Se cair ou for interrompida, rode o mesmo comando: as buscas já feitas são
  puladas.
- Se aparecer "5 buscas seguidas vazias", o X pode estar limitando a conta.
  Pare, espere algumas horas e refaça os dias afetados com
  `--refazer --so-dia AAAA-MM-DD`.

### Atalho: coletar, montar e atualizar o painel de uma vez

```powershell
python src\tcc_rodar.py --casos colgate cacau_show
```

Coleta tudo o que falta dos casos indicados, usando o **seu Chrome** (com o
perfil salvo pelo `login_x.py`). Uma janela do Chrome abre e fica fazendo as
buscas: deixe aberta (pode minimizar). Se o X mostrar a verificação
"Confirme que é humano", o terminal avisa e a coleta pausa até você clicar
nela na janela do Chrome; depois continua sozinha. Se a sessão do X cair, renova
pelo `login_x.py` e continua (até 4 rodadas). O computador não entra em
suspensão enquanto o comando roda. No fim, monta as tabelas, atualiza o
painel e mostra quantos dias de cada caso ficaram completos, parciais ou sem
coleta. Com ele, os passos 4 e 7 já ficam feitos.

## 4. Montar as tabelas

```powershell
python src\tcc_montar.py --caso tania_bulhoes
```

O terminal mostra um resumo: publicações válidas, exclusões e amostra por
fase. Abra `dados\tania_bulhoes\tania_bulhoes_volume_diario.csv` e veja se
algum dia ficou como `nao_coletado` ou `parcial`. Se ficou, volte ao passo 3
para esse dia.

## 5. Classificar com IA

**Opção A — sem custo de API (pelo chat do Claude):**

```powershell
python src\tcc_classificar.py --caso tania_bulhoes --provider manual
```

1. Abra a pasta `dados\tania_bulhoes\classificacao\`.
2. Para cada `t0_lote001_prompt.txt`, `t0_lote002_prompt.txt`…: copie todo o
   conteúdo, cole numa **conversa nova** do Claude e salve a resposta num
   arquivo com o mesmo nome terminado em `_resposta.txt` (por exemplo,
   `t0_lote001_resposta.txt`).
3. Rode o mesmo comando de novo. Linhas que vierem com erro viram um lote
   `t1_...`; repita o processo para ele.

Use uma conversa nova a cada lote, para que um lote não influencie o outro,
e anote o modelo usado: ele aparece no registro do trabalho.

**Opção B — pela API (automático):**

```powershell
$env:ANTHROPIC_API_KEY = "sua_chave"
pip install anthropic
python src\tcc_classificar.py --caso tania_bulhoes --provider anthropic
```

Para ver o tamanho do trabalho antes de rodar:
`python src\tcc_classificar.py --caso tania_bulhoes --estimar`.

## 6. Validação humana

```powershell
python src\tcc_validar.py gerar --caso tania_bulhoes
```

1. Abra `dados\tania_bulhoes\validacao\tania_bulhoes_validacao_cega.xlsx`.
2. A pesquisadora preenche sentimento, eixo e ironia de cada linha,
   seguindo a aba "critérios". **Não abra a classificação da IA antes de
   terminar**: ver a resposta da IA influencia o julgamento e invalida o
   kappa.
3. Salve a planilha e rode:

```powershell
python src\tcc_validar.py medir --caso tania_bulhoes
```

O resultado (kappa, matriz de confusão e divergências) fica em
`dados\tania_bulhoes\validacao\`.

## 7. Atualizar o painel

```powershell
python src\tcc_painel.py
```

Para ver o painel no seu computador antes de enviar, abra
`painel\index.html` no navegador.

## 8. Enviar para o GitHub

```powershell
git add .
git status
git commit -m "Tânia Bulhões: coleta e classificação"
git push
```

No `git status`, confira que **não** aparecem:
- `storage_state.json`, `credentials.local.json` ou `accounts.db`;
- arquivos `*_posts.csv` (com texto), a pasta `classificacao\` ou a
  planilha `.xlsx` de validação;
- nada em `data\` (bruto e tabela de autores).

O `.gitignore` já bloqueia todos eles. Se algum aparecer, não faça o commit
e verifique o motivo.

O painel online (https://sarah-volpe.github.io/gestao-crise-rp/) se
atualiza um ou dois minutos depois do push. Na primeira vez, ative em
*Settings → Pages → Deploy from a branch → main / (root)*.

Vale enviar ao fim de cada etapa: o histórico de commits passa a documentar
quando cada parte foi feita.

---

## Mudar datas, palavras-chave ou critérios

Tudo fica em `casos\<caso>.yaml`. Depois de editar, rode
`python src\tcc_prompts.py` para atualizar os prompts do apêndice. Mudar a
busca **depois** de coletar exige coletar de novo (`--refazer`), senão as
fases deixam de ser comparáveis.

## Problemas comuns

| mensagem | o que fazer |
|---|---|
| `X pediu login` | sessão expirou: `python src\login_x.py` e rode a coleta de novo |
| `5 buscas seguidas vazias` | possível limite do X: espere e refaça os dias com `--refazer --so-dia` |
| `Nenhum bruto em data/raw/x_tcc/...` | a coleta ainda não rodou para esse caso |
| `sem resposta válida` na classificação | normal em poucas linhas: elas voltam num lote `t1_`/`t2_` |
| `já existe` ao gerar a validação | a planilha já foi sorteada: não sorteie outra, preencha a existente |
