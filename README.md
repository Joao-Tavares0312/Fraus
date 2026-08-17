<p align="center">
  <img src="docs/assets/fraus-logo.png" alt="Fraus" width="140">
</p>

<h1 align="center">Fraus</h1>

<p align="center">
  <em>Análise de satisfação em atendimentos por chatbot — sem LLM em runtime.</em>
</p>

---

## O problema

O cliente mente.

Ele digita "ok, obrigado 🙂" e vai embora insatisfeito. Modelos que olham só
características genéricas da conversa — número de mensagens, intents previstos —
explicam cerca de **10% da variância** da satisfação declarada[^1], e há
inconsistência sistemática entre a nota que o cliente dá e o texto que ele
escreve[^2].

Fraus, a divindade romana da fraude e do engano — contraparte latina de
Ápate/Dolos, postada por Virgílio à entrada do Inferno ao lado do Medo e da
Discórdia (*Eneida*, VI)[^4] — lê o que foi dito de verdade.

## Como funciona

Sinais independentes, calculados sobre um modelo canônico de conversa e fundidos
por um classificador leve:

| Sinal | O que mede | Por quê |
|---|---|---|
| **Texto** | BERTimbau fine-tunado, probabilidade **por mensagem** | permite apontar *quais trechos* puxaram a nota |
| **Emoji** | polaridade e **posição relativa** na mensagem | a polaridade do emoji cresce perto do fim da frase |
| **Tempo** | latência, escalação, abandono | o efeito é não-linear — o peso é aprendido, não arbitrado |
| **Emoção** ⏳ | as 7 emoções humanas, por mensagem | requisito de banca; a nota diz *quanto*, a emoção diz *o quê* |
| **Léxico** ⏳ | SentiLex-PT02 com escopo de **negação** | polaridade de procedência independente do BERTimbau |
| **Ironia** ⏳ | cabeça binária sobre o IDPT 2021 | texto positivo com sentido negativo derruba a leitura dos outros sinais |

⏳ *módulo pronto e testado; entra no vetor de features quando o modelo for
treinado — ver [contrato de features](docs/treinamento.md#contrato-de-features).*

O resultado é um score de 0 a 100 por atendimento, que vira nota 0–10 e categoria
de NPS (**0–6 detrator · 7–8 neutro · 9–10 promotor**), agregado numa dashboard.

### As 7 emoções

Requisito de banca. São as **seis básicas de Ekman (1992)** — alegria, tristeza,
raiva, medo, nojo, surpresa — mais o **desprezo**; o *neutro* é uma sétima
**classe**, não uma emoção: é a ausência delas.

O desprezo é o único que **não é treinado**, e de propósito: nenhum corpus
rotulado em português o anota, e treiná-lo isoladamente em corpus de outra
procedência ensinaria o modelo a reconhecer o *estilo do texto* em vez da
emoção. Ele é derivado da **díade primária raiva + nojo**, como Plutchik (1980)
o define — referência citável, não rótulo inventado.

## Indicadores

NPS inferido · CSAT · containment rate · tempo mediano de resposta — com NPS e
latência **sobrepostos no mesmo gráfico**, porque otimizar um KPI isolado quebra
outro.

> **Nota metodológica:** o NPS aqui é **inferido do texto**, não perguntado ao
> cliente. A dashboard rotula como estimativa.

## Stack

Python 3.11 · transformers + torch (CPU) · scikit-learn · FastAPI · SQLite ·
Next.js + Recharts

Sem base vetorial: a tarefa é classificação, e para classificação o fine-tuning
vence RAG em acurácia e latência[^3].

## Documentação

- [Spec de design](docs/superpowers/specs/2026-08-13-dolos-design.md) — decisões e referências
- [Plano de implementação](docs/superpowers/plans/2026-08-13-dolos-implementacao.md) — 10 tasks
- [Treinamento](docs/treinamento.md) — os notebooks do Colab, os corpora de cada sinal, os artefatos que eles produzem e o registro do vazamento que matou o primeiro fusor

## Como rodar

Requisitos: Python 3.11+ com [`uv`](https://docs.astral.sh/uv/), Node 20+ e npm.

### 1. Dependências do Python

```bash
uv sync --extra dev
```

> Use `--extra dev`. O `uv sync` puro **remove o pytest**: o grupo `dev` é
> opt-in, e sem ele a suíte não roda.

### 2. Testes

```bash
uv run pytest -q       # ou -v para ver caso a caso
```

### 3. API

```bash
uv run uvicorn fraus.api.main:app --reload   # http://localhost:8000
```

A API real **exige o modelo treinado** em `modelos/` (BERTimbau fine-tunado e
`fusor.joblib`) e **falha alto no boot** se ele não existir — por design:
servir predição sem modelo carregado é pior do que estar fora do ar. Os dois
artefatos saem dos notebooks `01_treino_bertimbau.ipynb` e
`02_treino_fusor.ipynb`, nessa ordem; veja
[docs/treinamento.md](docs/treinamento.md).

Variáveis de ambiente reconhecidas:

| Variável | Padrão | O que faz |
|---|---|---|
| `FRAUS_CAMINHO_MODELO_TEXTO` | `modelos/bertimbau-satisfacao` | modelo de texto |
| `FRAUS_CAMINHO_FUSOR` | `modelos/fusor.joblib` | regressão logística de fusão |
| `FRAUS_CAMINHO_BANCO` | `fraus.db` | SQLite |
| `FRAUS_RAIZ_IMPORTACAO` | `dados_brutos` | **única** pasta de onde `POST /conversas/importar` pode ler |
| `FRAUS_CHAVE_MESTRA` | (nenhum) | a mestra vinda do ambiente, que **vence** a gravada pela tela. Sem ela e sem mestra no banco, a API é aberta (uso local), com aviso no boot. Com qualquer uma das duas, toda rota exige `Authorization: Bearer` — a mestra ou uma chave de acesso — exceto `POST /ingestao` (chave de fonte) e `GET /acesso/estado` (pública) |

#### Ligando a autenticação

**Pela tela, em um clique.** Abra **Configurações → Autenticação** e clique em
*Ligar autenticação*. A API gera a chave mestra, grava o hash dela e emite junto
uma chave de acesso para a dashboard — as duas aparecem **uma única vez**, para
você guardar. O servidor **não é reiniciado**: quem decide é um middleware que
lê o estado a cada requisição, então a exigência de chave vale já na chamada
seguinte. A dashboard continua navegando porque a chave de acesso emitida vai
para um cookie `httpOnly` do servidor Next.

Ligada assim, a mestra **sobrevive a reiniciar a API** (o hash fica no banco, em
`chave_mestra`, uma linha só). Para trocá-la depois, o mesmo painel pede a
mestra **atual** — sem ela a troca é recusada com 409, e é isso que impede
alguém de tomar a API de quem já está dentro.

**Pelo ambiente**, se você opera por variável — e ela **vence** a gravada:

```bash
# 1. Invente um segredo forte:
python -c "import secrets; print(secrets.token_hex(32))"

# 2. Suba a API com ele (PowerShell: $env:FRAUS_CHAVE_MESTRA = "..."):
FRAUS_CHAVE_MESTRA=<segredo> uv run uvicorn fraus.api.main:app

# 3. Toda rota agora exige chave. Gere uma chave de ACESSO para a dashboard:
curl -X POST localhost:8000/acesso/chaves \
  -H "Authorization: Bearer <segredo>" \
  -H 'content-type: application/json' -d '{"nome": "dashboard"}'
# → devolve a chave fra_... UMA única vez; o banco guarda só o hash.

# 4. Suba a dashboard com a chave (server-side, nunca vai ao navegador):
cd dashboard && FRAUS_CHAVE_ACESSO=fra_... npm run dev
```

Com a variável definida, o painel da tela **não troca** a mestra: gravar por
cima criaria duas credenciais com a do ambiente ganhando, e o botão pareceria
funcionar sem mudar nada. A variável é também a saída de quem perdeu a chave
gerada pela tela.

`GET /acesso/estado` responde `{"ligada": ..., "origem": "ambiente"|"banco"|null}`
e é a **única** rota que continua pública com a autenticação ligada — a tela
precisa dela justamente quando ainda não há credencial para apresentar.

**Desligar não é botão.** Um controle que baixa a defesa numa tela sem login não
tem contrapartida de risco aceitável: desligar é apagar a variável e a linha
`chave_mestra` do banco.

`GET /acesso/chaves` lista as chaves emitidas (nome, dica dos 4 últimos
caracteres, nunca o hash) e `DELETE /acesso/chaves/{id}` revoga na hora — a
chamada seguinte com a chave revogada leva 401. Se uma chave de acesso vazar,
revogue-a sem trocar a mestra; se a **mestra** vazar, troque a variável e
reinicie: as chaves de acesso continuam valendo, quem perde o posto é só ela.

Para importar um CSV, coloque o arquivo dentro de `dados_brutos/` e mande o
caminho relativo a ela:

```bash
curl -X POST localhost:8000/conversas/importar \
  -H 'content-type: application/json' \
  -d '{"caminho": "atendimentos.csv"}'
```

Qualquer caminho que escape dessa raiz (`../..`, caminho absoluto de fora) é
rejeitado com **400**. Coluna estrutural ausente no CSV também dá **400**,
nomeando a coluna; linha individual malformada não derruba o lote — ela volta
na resposta, em `motivos`.

### 4. Dashboard

```bash
cd dashboard
npm install
npm run dev      # http://localhost:3000
npm run build    # build de produção
```

A dashboard não fala com a API direto: toda chamada de `lib/api.ts` sai por um
proxy no servidor Next (`app/api/fraus/[...caminho]/route.ts`), que repassa
método, corpo, query string e status para `FRAUS_API_URL` (padrão
`http://localhost:8000`), anexando `Authorization: Bearer ${FRAUS_CHAVE_ACESSO}`
quando essa variável existe. A chave de acesso nunca toca o navegador.

```bash
FRAUS_API_URL=http://localhost:8000 FRAUS_CHAVE_ACESSO=fra_... npm run dev
```

O proxy monta o header com `FRAUS_CHAVE_ACESSO` **ou**, na falta dela, com a
chave guardada no cookie `httpOnly` de quem ligou a autenticação pela tela — o
ambiente vence, e o `Authorization` que vier do navegador continua sendo
**descartado** (a credencial da API é a do deploy, não a que o cliente mandar).

Com `FRAUS_CHAVE_ACESSO` no ambiente, a dashboard publicada continua **sem
login**: quem alcança a URL dela lê os dados pelo proxy, e para publicar com dado
real você ainda precisa proteger o deploy (por exemplo, Vercel Deployment
Protection). Sem a variável, o cookie passa a ser a credencial da sessão — e
então um navegador que não clicou em ligar cai em **401** nas telas de dados, com
o painel de Autenticação explicando o que falta. É meio caminho de um login, não
um login: o cookie não expira por conta própria além da sessão do navegador, e
não há usuários nem senha.

Sem nenhuma das duas, o proxy repassa sem header — desenvolvimento local
contra uma API aberta continua funcionando com zero configuração. Como são
variáveis **server-side**, mudar depois exige reiniciar o processo — mas,
diferente de `NEXT_PUBLIC_*`, elas nunca são embutidas no bundle do navegador.
`NEXT_PUBLIC_API_URL` não é mais lida pelo app: sobrevive só como texto do
exemplo de `curl` na tela de integrações.

## Limitações conhecidas

- **A API é aberta por padrão, e passa a exigir chave quando existe uma mestra**
  — do ambiente (`FRAUS_CHAVE_MESTRA`) ou gravada pelo botão em Configurações,
  que persiste no banco. Sem nenhuma das duas, o comportamento é o de sempre —
  sem login, sem token — pensado para uso local, e o boot avisa disso. A decisão
  é tomada **por requisição**, não no boot: é o que permite ligar a autenticação
  sem reiniciar o servidor. Com mestra, toda rota
  exige `Authorization: Bearer <chave>`: a mestra, ou uma **chave de acesso**
  (`fra_...`) gerada por ela via `POST /acesso/chaves`. A **chave de fonte**
  (`frs_...`) existente continua sendo a única credencial aceita em
  `POST /ingestao` — as duas não se substituem, porque a rota só escreve e uma
  segunda credencial não compraria segurança a mais. `GET /acesso/estado` é a
  única rota que permanece **pública** com a autenticação ligada, e devolve
  apenas se ela está ligada e de onde vem a mestra: sem dica, sem hash, sem
  data. `POST /acesso/mestra` fica alcançável enquanto a API está aberta, e é
  assim que se liga a autenticação sem terminal — o preço é que, numa rede
  compartilhada, **quem chegar primeiro** liga a autenticação e fica com a
  mestra (é o padrão de primeiro uso de Grafana e afins). Depois de ligada, ela
  exige a mestra atual e responde 409 a qualquer outra credencial. Gerenciar
  chaves (criar,
  listar, revogar — tanto de acesso quanto de fonte) é privilégio exclusivo da
  mestra; uma chave de acesso que tenta recebe **403**. Sem a mestra definida,
  não exponha a API na internet: a raiz configurável (`FRAUS_RAIZ_IMPORTACAO`)
  limita o estrago da importação, não substitui autenticação. As origens
  liberadas para o navegador continuam sendo uma **lista explícita**
  (`FRAUS_ORIGENS`, padrão `localhost`/`127.0.0.1` nas portas 3000 e 3001) e
  nunca `*`, como defesa em profundidade — o caminho normal da dashboard virou
  servidor→servidor pelo proxy do Next, mas CORS continua valendo para quem
  chamar a API direto do navegador.
- O NPS é **inferido do texto**, nunca perguntado ao cliente. A interface
  rotula como estimativa em todo lugar onde o número aparece.
- A série temporal sai de `GET /serie-temporal?de=&ate=`, agregada no servidor.
  O N+1 sobrevive para o **léxico por classe** e o **tempo mediano de
  resposta**, que ainda leem o texto e os timestamps de cada transcrição — um
  custo aceitável no volume do trabalho (dezenas de atendimentos).
- A atribuição por sentença do classificador de texto não tem endpoint, então a
  transcrição marca só evidência **observável** (polaridade de emoji e tempo de
  espera) — e diz isso em voz alta em vez de fingir atribuição.
- Latência **não é persistida**: é sempre derivada dos timestamps na leitura.
- Os cortes de latência da interface (10 s / 60 s / 180 s por padrão) são de
  **exibição** e saem de `GET /configuracoes`: eles movem onde a leitura chama
  a espera de imediata, saudável, longa ou crítica, e não mexem em nenhuma
  feature do modelo.
- A tela **Configurações** não reimplementa a validação: quando a faixa de NPS
  não cobre 0–10 de forma contígua, quem escreve a mensagem é a API, que nomeia
  a nota descoberta.
- **A classe neutra do modelo conta como detratora, e o NPS sai pessimista.**
  O score é `100 * (P(satisfeito) + 0.5 * P(neutro))`: uma conversa classificada
  com certeza como neutra pontua **50**, vira nota **5** e cai em **0–6,
  detrator**. A faixa neutra do NPS (7–8) exigiria `P(satisfeito)` entre 0,4 e
  0,8 — um empate entre classes, não uma neutralidade confiante. Medido em 90
  conversas do simulador (30 por classe, equilibradas por construção): **67%
  detrator · 29% promotor · 4% neutro**, com **NPS −38** onde o esperado seria
  ≈ 0. É consequência da composição entre o peso do neutro no score e a faixa
  padrão do NPS, não erro de treino — o fusor separa as três classes com
  medianas 0,11 / 50,99 / 99,03. Mantido assim por decisão de projeto; subir o
  peso do neutro para 0,75 alinharia as três classes às três categorias.
- **O fusor é treinado em conversas sintéticas.** Nenhum corpus público de
  resenha PT-BR tem timestamps de diálogo: latência, escalação e abandono saem
  de distribuições calibradas por literatura de live chat. O texto é real, o
  tempo não é — e as métricas do notebook 02 são otimistas por isso.
- **O corpus de emoção é traduzido por máquina** (GoEmotions → PT-BR, sem
  revisão humana). Por isso a avaliação reporta também o XED-pt, que não passou
  por tradução automática, como conjunto de teste independente.
- **O corpus de ironia (IDPT 2021) é de tweets e comentários de notícia**, não
  de atendimento. A transferência de domínio não está verificada.
- **O SentiLex-PT é léxico de julgamento social:** anota polaridade dirigida a
  entidades humanas. `gostar`, `adorar` e `odiar` valem **0** nele — quem lê
  afeto do próprio falante é o transformer, não o léxico.

## Pendências

O que falta, em ordem de importância. Cada item diz o que existe hoje e o que
o desbloqueia.

### 1. Retreinar a cabeça de ironia — vazamento de corpus MEDIDO

**As três cabeças estão treinadas e no ar** (satisfação, emoção e ironia), e o
`api_demo` carrega o motor real quando os pesos estão em `modelos/`. O dublê
determinístico só entra se eles faltarem, ou com `FRAUS_DEMO_DUBLE=1`.

O que ficou aberto é a **ironia**. Ela reporta acurácia `1.0` — e não sobrevive
a fala de atendimento: **6 em 10 frases sinceras** saem marcadas como irônicas,
com 0,999 de confiança. A causa está medida e nomeada em
`tests/test_ironia_dominio.py`: as dezoito atenuações do gerador abriam com
marcador de discurso (`imagina,`, `tranquilo,`, `olha só,`) e nenhuma família
sincera tinha marcador — o modelo aprendeu **registro conversacional** em vez
de pragmática. Não dá para consertar por limiar: os falsos positivos saem
saturados, em 0,97 ou mais.

**O gerador já foi corrigido** (marcador sorteado nas duas classes, pelo mesmo
gargalo dos emojis e da caixa) e ganhou o teste que faltava. Falta rodar
`notebooks/04_treino_ironia.ipynb` de novo e substituir
`modelos/bertimbau-ironia/`. Até lá a probabilidade de ironia é exibida como
**indício com a ressalva colada**, nunca como veredito.

### 2. As features de emoção e ironia ainda não entram no fusor

O fusor tem **16 features** — texto, emoji e tempo — e nenhuma vem das cabeças
de emoção e ironia. Elas são **leitura, não julgamento**: descrevem a fala sem
mover a nota, e toda resposta que as carrega marca isso em
`sinais_fora_do_score`.

Subir o contrato de 16 para 30 features e **retreinar o fusor** é o passo que
as coloca na nota — e ele só faz sentido depois da pendência 1, porque treinar
o fusor sobre uma cabeça de ironia que erra 6 em 10 injetaria o vazamento dela
no score.

Existem dois corpora PT-BR reais de ironia, ambos sem download público — a tese de
[Vieira e Silva (USP, 2025)](https://teses.usp.br/teses/disponiveis/8/8139/tde-28082025-163511/publico/2025_AndressaVieiraESilva_VCorr.pdf),
com 1.186 exemplos anotados por três humanos, e o
[projeto IDPT/UFPel](https://institucional.ufpel.edu.br/projetos/id/u3345).
Qualquer um dos dois serve como **conjunto de teste independente**, o papel que
o XED-pt cumpre no notebook 03 — e é o que falta para a ironia ter uma métrica
que não seja otimista por construção. Detalhes de corpus, rótulo e limitação em
[docs/treinamento.md](docs/treinamento.md).

### 3. O resto da dívida de escala

`GET /serie-temporal?de=&ate=` **existe**: o gráfico de NPS × latência não
depende mais de baixar transcrição nenhuma, e o recorte de período acontece no
servidor. As duas pontas são inclusivas, data malformada é **400** nomeando o
parâmetro, e o cálculo sobre as transcrições ficou como plano B — se o endpoint
cair, o gráfico continua de pé em vez de sumir.

O que ainda falta para matar o N+1 de vez:

- `GET /conversas?de=&ate=` e `GET /indicadores?de=&ate=` — tirariam do cliente
  o filtro de período da lista e dos cartões;
- um agregado de **léxico por classe** e de **tempo mediano de resposta**, os
  dois últimos consumidores de transcrição na Visão geral.

### 4. Definição da empresa

A spec ainda não fixa a empresa fictícia do trabalho, e ela atravessa a
apresentação inteira: define o volume plausível de atendimentos, os canais e o
que conta como bom tempo de resposta.

### 5. Decisões em aberto

- **Tema claro.** A dashboard é dark-only, herdado do chassi. Projetor de banca
  costuma lavar tema escuro, e adicionar depois é retrabalho.
- **`scikit-learn` sem pin.** O `fusor.joblib` foi serializado com a 1.6.1 e a
  venv local tem a 1.9.0; o sklearn avisa que o resultado *pode* ser inválido.
  Os scores conferidos estão sãos (espalhamento 0–99,9, categorias coerentes),
  mas para o trabalho ser reprodutível o pin precisa existir — o `Dockerfile`
  já fixa `scikit-learn==1.6.1`, o `pyproject.toml` não.
- **`content/fraus` na raiz.** Notebook 01 que o Colab salvou no caminho de
  dentro dele, sem extensão, no commit `66fde10`. Duplicata do que já vive em
  `notebooks/`; é lixo e pode ser removido.

## Desenvolvimento

### Onde mora a API

Nenhuma rota é definida em `fraus/api/main.py`: ele só monta o app — o
`Contexto`, os middlewares na ordem certa e os oito routers. Cada domínio tem
o seu arquivo, e é nele que se mexe:

| Arquivo | O que tem |
|---|---|
| `api/main.py` | montagem do app e `criar_app` — nada mais |
| `api/contexto.py` | `Contexto` (banco, motor, raiz, chave mestra) + os derivados compartilhados; as rotas o recebem por `Depends(obter_contexto)` |
| `api/esquemas.py` | os contratos de **entrada** (nenhum aceita veredito) |
| `api/seguranca.py` | as duas credenciais — chave de acesso/mestra e chave de fonte — e o middleware |
| `api/periodo.py` | validação do recorte `de`/`ate`, pontas inclusivas |
| `api/caminhos.py` | caminhos configuráveis por ambiente + contenção da importação |
| `api/rotas/` | um módulo por domínio: `saude`, `conversas`, `indicadores`, `configuracoes`, `integracoes`, `acesso` (estado, mestra e chaves), `ingestao`, `modelo`, `analise` |

As dependências chegam por injeção, não por fechamento léxico — é o que
permite a rota morar fora do arquivo que constrói o app.

### Servidor de demonstração da interface

O `app` real carrega o BERTimbau do disco e **falha alto** se `modelos/` não
existir — por design. Enquanto o treino do Colab não roda, a dashboard é
desenvolvida contra um servidor de demonstração que usa um motor dublê
(pontuação determinística derivada do texto, sem modelo nenhum) e semeia um
banco temporário com conversas do simulador, incluindo atendimentos **sem fala
do cliente** para exercitar o estado "sem sinal":

```bash
uv run python scripts/api_demo.py   # http://localhost:8000
```

**Nunca use `scripts/api_demo.py` em produção.** Os números que ele devolve não
são predição de modelo.

[^1]: [Conversation logs as a source of insight: predicting user satisfaction for customer service chatbots](https://link.springer.com/article/10.1007/s41233-025-00071-8) — Quality and User Experience, Springer, 2025.
[^2]: [Refining the prediction of user satisfaction on chat-based AI applications](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11793979/).
[^3]: [RAG vs Fine-Tuning 2026: A Decision Framework](https://winder.ai/rag-vs-fine-tuning-2026-decision-framework/).
[^4]: Virgílio, *Eneida*, Livro VI, v. 273-281 — Fraus (Fraude/Engano) personificada no vestíbulo do Orco, ao lado de Luto, Curae, Morbi, Senectus e Metus.
