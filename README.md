<p align="center">
  <img src="docs/assets/banner-instrumento.png" alt="Fraus — leia o que ficou nas entrelinhas" width="100%">
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
Ápate/Dolos, que Cícero nomeia entre a prole de Érebo e da Noite, ao lado de
*Dolus*, *Metus* e *Senectus*[^4] — lê o que foi dito de verdade.

## Como funciona

### Da análise à operação

Na tela **Analisar**, envie um arquivo ou cole CSV/JSON/transcrição. A opção
**Salvar as conversas analisadas nos indicadores e no grafo** publica o lote no
banco configurado da API (`FRAUS_DATABASE_URL` para PostgreSQL/Supabase).
Horários reais e motor real são obrigatórios; o mesmo conteúdo não duplica os
atendimentos. A confirmação abre o período correto nos indicadores e no grafo.
Desmarque salvar para manter a análise avulsa.

**Operação** reúne sete ferramentas sobre esses registros:

- Radar de temas recorrentes e crescimento de taxas, com evidências.
- Equipes, competências e simulação de escala, filas e custo por canal.
- Jornadas por referência pseudônima explícita entre contatos.
- Investigações com responsáveis, prazo, ações e comparação antes/depois.
- Replay com estimativa por prefixo, sem mensagens futuras.
- Laboratório de cenários e comparação de fusores nas mesmas features.
- Mapa de acessos por canal, exportação temporária, revogação de sessões e auditoria.

Equipes têm **proprietário → gestor → membro**. Na aba Equipe e escala, gere um
link com papel, validade (até sete dias) e limite de pessoas. O visitante entra
ou cria conta e aceita o convite. Links podem ser revogados; a última pessoa
proprietária não pode ser removida. Hierarquia da equipe não concede papel `dev`.

Contas criadas por convite começam sem acesso às conversas. Ao aceitar, recebem
os canais explicitamente cadastrados na equipe. Remoção recalcula esse escopo;
políticas manuais do administrador são preservadas. Equipe sem canais não libera
conversas. Contas anteriores sem política conservam seu acesso anterior.

O NPS continua **inferido**. Seu cartão oculta o ponto abaixo de 30 conversas com
sinal; o intervalo AW(3,T) mede incerteza amostral, não a calibração do modelo.
Simulações e diferenças antes/depois não demonstram causalidade.

Para comparar fusores, configure `FRAUS_FUSOR_CANDIDATO` com o arquivo de um
artefato compatível no servidor. Nada é promovido ou repontuado automaticamente.
Os testes locais podem usar `scripts/validar_operacao_real.py` e
`dashboard/scripts/validar-operacao-playwright.mjs` (dados temporários).

Sinais independentes, calculados sobre um modelo canônico de conversa e fundidos
por um classificador leve:

| Sinal | O que mede | Por quê |
|---|---|---|
| **Texto** | BERTimbau fine-tunado, probabilidade **por mensagem** | permite apontar *quais trechos* puxaram a nota |
| **Emoji** | polaridade e **posição relativa** na mensagem | a polaridade do emoji cresce perto do fim da frase |
| **Tempo** | latência, escalação, abandono | o efeito é não-linear — o peso é aprendido, não arbitrado |
| **Emoção** | as 7 emoções humanas, por mensagem | requisito de banca; a nota diz *quanto*, a emoção diz *o quê* |
| **Léxico** | SentiLex-PT02 com escopo de **negação**, mais o [léxico curado](#léxico-curado) | polaridade de procedência independente do BERTimbau |
| **Ironia** ⚠️ | cabeça binária sobre o IDPT 2021, lida por mensagem | texto positivo com sentido negativo — mas **não entra no score**, ver abaixo |
| **Estilo** | caixa alta, pontuação, alongamento, palavrão, censura | a forma de escrever carrega afeto que a palavra sozinha não carrega |
| **Incongruência** | polaridade, emoji×texto, marcador de contraste, hipérbole, aspas irônicas e elogio com situação negativa | texto e emoji discordando é o formato clássico da ironia |

Sete das oito famílias — todas menos ironia — somam **39 features** no vetor
do fusor: cinco de `incongruencia_*` entraram em 03/09/2026 e a sexta,
`incongruencia_situacao_negativa`, em 04/09/2026 — ver [contrato de
features](docs/treinamento.md#contrato-de-features).

⚠️ *a cabeça de ironia continua treinada, obrigatória e exibida por mensagem
na dashboard, mas **saiu do vetor do fusor em 04/09/2026**: medida no próprio
corpus de treino, ela funciona como detector de sentimento positivo, não de
ironia (74% das resenhas satisfeitas marcadas como irônicas, contra 9% das
insatisfeitas) — ver [pendência 1](#1-retreinar-a-cabeça-de-ironia--vazamento-de-corpus-medido-dívida-assumida)
e [a decisão em docs/treinamento.md](docs/treinamento.md#a-ironia-sai-do-vetor-04092026).*

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

O score é `100 * (P(satisfeito) + 0.75 * P(neutro))`. O peso do neutro é o que
faz **as três classes do modelo caírem nas três categorias do NPS**:

| classe pura | score | nota | categoria |
|---|---|---|---|
| insatisfeito | 0 | 0 | detrator |
| neutro | 75 | 8 | neutro |
| satisfeito | 100 | 10 | promotor |

Ele já foi `0.5`, e o efeito não era sutil: a classe neutra pontuava 50, virava
nota 5 e caía em 0–6 — **detrator**. Não numa borda rara: a classe inteira.
Medido com o motor real em 90 conversas do simulador (30 por classe,
equilibradas por construção), os **30 neutros iam todos para detrator** e o NPS
saía **−36,67** onde o esperado era ≈ 0. Não era erro de treino — o fusor
separa as classes com folga, medianas de score 0,84 / 75,06 / 99,68 — era a
composição entre o peso e a faixa. Com `0.75`: **32,2% detrator · 35,6% neutro
· 32,2% promotor**, NPS **+0,00**.

A medida se reproduz, e é para isso que o script existe:

```bash
uv run python scripts/medir_faixas.py                    # a régua vigente
uv run python scripts/medir_faixas.py --peso-neutro 0.5  # a régua antiga
uv run python scripts/conferir_fusor.py                  # laudo do artefato vigente
```

O peso é **constante** (`fraus.fusor.PESO_NEUTRO_NO_SCORE`), não configuração,
e a assimetria em relação à faixa de NPS — que *é* configurável — é
deliberada: `categoria` é derivada na leitura e refatia dado que já existe, mas
o peso muda o `score` **gravado**. Um botão aqui deixaria o banco com scores de
duas réguas somados no mesmo agregado, sem nenhuma leitura capaz de separá-los.

## Léxico curado

O SentiLex-PT02 tem 79.189 formas e não tem `lentíssimo`. O Emoji Sentiment
Ranking anotou 751 emojis **em 2015** — tudo que o Unicode acrescentou depois
vale zero. Nenhum dos dois conhece o jargão da empresa que opera o atendimento.
O léxico curado é o que o analista acrescenta por cima.

**O que o peso faz:** alimenta o sinal léxico, e o fusor treinado decide o
quanto isso move a nota — exatamente como já faz com as 79.189 formas do
SentiLex. **O que ele não faz:** corrigir score. Um ajuste por cima do número do
modelo criaria uma **segunda régua**, que é a mesma dor documentada acima em
`PESO_NEUTRO_NO_SCORE`. O analista conserta o dicionário, nunca a nota.

**A curadoria vence o léxico base**, e é isso que a faz servir aos dois casos:
preencher buraco (o termo não existe) e corrigir polaridade errada para o
domínio. Peso `0` não é "ausente" — é **curado como neutro**, e silencia um
termo que o SentiLex anota com polaridade errada para atendimento.

**As duas escalas não são a mesma, e não podem ser:**

| tipo | escala | por quê |
|---|---|---|
| palavra | inteiro **−1 / 0 / +1** | é a escala em que `lexico_polaridade_media` foi treinada; um `-0.7` injetaria na feature um valor que o fusor nunca viu |
| emoji | float em **[−1, 1]** | é a escala contínua do Emoji Sentiment Ranking |

A API recusa com `400` o que sai da escala, e a interface nem oferece: palavra
tem três opções, nunca campo numérico livre.

**A versão, e a régua misturada.** Cada escrita no léxico curado incrementa uma
versão, e toda conversa grava **com qual versão foi pontuada**. Como o `score` é
gravado na importação, curar uma palavra não mexe no que já existe — e um banco
com conversas pontuadas antes e depois soma duas réguas no mesmo agregado. A
Visão geral **nomeia** isso ("41 de 62 atendimentos foram pontuados com um
léxico anterior") em vez de esconder, e a contagem ignora o filtro de período de
propósito: a régua misturada é propriedade do banco, não da semana que se olha.

`POST /conversas/repontuar` zera a divergência. **Limitação declarada:** ele roda
os três BERTimbau de novo por conversa — o vetor é de 39 features e o fusor exige
as 39, então não existe recalcular só as três léxicas e as cinco de emoji. Em
dezenas de atendimentos são segundos; em milhares vira trabalho de fila, e a fila
não existe. A rota é **síncrona de propósito**: uma fila que ninguém observa
seria pior que uma espera que se vê.

```
GET    /lexico/curado          lista os termos curados
POST   /lexico/curado          cadastra ou EDITA (tipo, termo, peso, motivo)
DELETE /lexico/curado/{id}     revoga — o termo volta a valer o léxico base
POST   /conversas/repontuar    repontua o banco inteiro com o léxico vigente
```

## Stack

Python 3.11 · transformers + torch/ONNX Runtime (CPU) · scikit-learn · FastAPI ·
SQLite/Postgres (Supabase) · Next.js + Recharts

Sem base vetorial: a tarefa é classificação, e para classificação o fine-tuning
vence RAG em acurácia e latência[^3].

## Documentação

- [Estado operacional — 30/09/2026](docs/notas/2026-09-30-operacao-producao.md) — análise persistida, sete abas de Operação, convites, permissões e evidências da publicação
- [Handoff interno](docs/handoff.md) — estado atual e histórico de decisões
- [Spec de design](docs/superpowers/specs/2026-08-13-dolos-design.md) — decisões e referências
- [Plano de implementação](docs/superpowers/plans/2026-08-13-dolos-implementacao.md) — 10 tasks
- [Treinamento](docs/treinamento.md) — os notebooks do Colab, os corpora de cada sinal, os artefatos que eles produzem e o registro do vazamento que matou o primeiro fusor
- [Deploy gratuito](docs/deploy-vercel.md) — dashboard e API na Vercel, modelos no Oracle Object Storage e estado no Supabase
- [Limitações conhecidas](docs/limitacoes.md) — limites científicos e operacionais que permanecem
- [Integração com o Tars](docs/integracao-tars.md) — sincronização idempotente entre os projetos, sem banco compartilhado

## Como rodar

Requisitos: Python 3.11+ com [`uv`](https://docs.astral.sh/uv/), Node 20+ e npm.

### 1. Dependências do Python

```bash
uv sync --extra dev --extra torch   # API real com backend Torch (padrão)
```

> Os extras são opt-in: `uv sync` puro remove pytest e Torch. Para ONNX, use
> `uv sync --extra dev --extra onnx`, defina `FRAUS_BACKEND=onnx` no ambiente
> e instale os artefatos ONNX. Ao adicionar `docs`, conserve os extras de
> desenvolvimento que usa.

### 2. Testes

```bash
uv run pytest -q       # ou -v para ver caso a caso
```

### 3. API

```bash
uv run python -m uvicorn fraus.api.main:app --port 8001 --reload --reload-dir fraus
```

> `python -m uvicorn`, e não `uv run uvicorn`: o segundo passa pelo trampolim
> que o `uv` instala para o `uvicorn.exe` do `.venv`, e ele quebra com
> `uv trampoline failed to canonicalize script path` se o venv foi recriado ou
> movido. Chamar o módulo pelo interpretador não depende de shim nenhum.

A API real **exige os classificadores treinados e o fusor** em `modelos/`
(ou os grafos em `modelos-onnx/`, com `FRAUS_BACKEND=onnx`). O provedor aquece
em segundo plano e expõe o estado; `/saude/prontidao` responde 503 até ficar
pronto. Modelo ausente fica como falha explícita, sem predição substituta.
Os artefatos de satisfação e fusor saem dos notebooks
`01_treino_bertimbau.ipynb` e `02_treino_fusor.ipynb`; emoção e ironia também
são obrigatórias, conforme
[docs/treinamento.md](docs/treinamento.md).

Variáveis de ambiente reconhecidas:

| Variável | Padrão | O que faz |
|---|---|---|
| `FRAUS_CAMINHO_MODELO_TEXTO` | `modelos/bertimbau-satisfacao` | modelo de texto |
| `FRAUS_CAMINHO_FUSOR` | `modelos/fusor.joblib` | regressão logística de fusão |
| `FRAUS_IRONIA_BACKEND` | `padrao` | `laya` troca somente a cabeça de ironia pelo Laya multilíngue; exige `uv sync --extra laya` |
| `FRAUS_LAYA_REVISAO` | `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851` | revisão imutável do checkpoint Laya |
| `FRAUS_CAMINHO_BANCO` | `fraus.db` | SQLite |
| `FRAUS_POSTGRES_MIN_CONEXOES` | `0` | mínimo do pool por instância; zero evita reservar conexão em função fria |
| `FRAUS_POSTGRES_MAX_CONEXOES` | `2` | máximo do pool por instância serverless (1–20) |
| `FRAUS_POSTGRES_TIMEOUT_S` | `10` | segundos máximos esperando conexão do pool (0,1–60) |
| `FRAUS_RAIZ_IMPORTACAO` | `dados_brutos` | **única** pasta de onde `POST /conversas/importar` pode ler |
| `FRAUS_CAMINHO_CHAVES` | `.fraus-chaves.txt` | onde a **primeira subida** grava a mestra e a chave de acesso que ela gera. Única cópia em claro delas; fora do git, e criado com permissão **`0600`** — só o dono lê (em POSIX; no Windows quem manda é a ACL herdada da pasta) |
| `FRAUS_CHAVE_MESTRA` | (nenhum) | a mestra vinda do ambiente. Definida, ela é a **única** mestra: a gravada no banco **deixa de valer** enquanto a variável existir (ver *Precedência*, abaixo). Sem ela e sem mestra no banco, a API é aberta (uso local), com aviso no boot. Com qualquer uma das duas, toda rota exige `Authorization: Bearer` — a mestra, uma chave de acesso ou um **token de sessão** — exceto `POST /ingestao` (chave de fonte), o webhook (assinatura própria) e as públicas (`/saude`, `/acesso/estado`, `/auth/estado`, `/auth/registrar`, `/auth/entrar`) |
| `FRAUS_JWT_SEGREDO` | (nenhum) | assina o **JWT de sessão** do login de usuário (`POST /auth/entrar`). Sem ela, o login responde 503 dizendo o que falta, `/auth/estado` anuncia `disponivel: false` e a dashboard abre **sem exigir login** — o modo aberto local, mesmo contrato da API sem mestra |
| `FRAUS_CODIGO_CONVITE` | (nenhum) | o código exigido para **criar conta** em `POST /auth/registrar`. Sem ela o cadastro fica **aberto** — o certo para uso local, e perigoso quando a API está publicada: ver *A porta destrancada*, logo abaixo. Não confundir com a de baixo: esta decide **se** a conta pode nascer; `FRAUS_CODIGO_DEV` decide **com qual papel** |
| `FRAUS_CODIGO_DEV` | (nenhum) | o código de convite que permite um cadastro nascer com papel **`dev`** (administra Integrações, Modelo, Configurações, importação e léxico). Sem ela, nenhum cadastro nasce dev — todo mundo nasce `usuario` (analista: Visão geral e Atendimentos). Código errado é 403 explícito, nunca rebaixamento silencioso |

#### A porta destrancada — leia antes de publicar a API

Definir `FRAUS_CHAVE_MESTRA` **não fecha a API** se o login de usuário estiver
ligado e o cadastro estiver aberto. A sequência abaixo roda inteira, sem
credencial nenhuma:

| Passo | Resposta |
|---|---|
| `GET /conversas` anônimo | **401** — a mestra parece proteger |
| `POST /auth/registrar` | **201** — conta criada |
| `POST /auth/entrar` | **200** — devolve o JWT |
| `GET /conversas` com o JWT | **200** — lê tudo |

`/auth/registrar` é isenta de credencial por desenho (quem se cadastra ainda
não tem nenhuma), e o middleware de acesso aceita uma sessão válida do mesmo
jeito que aceita a mestra. **Deixar de ser anônimo é de graça.**

O conserto é uma variável: `FRAUS_CODIGO_CONVITE`. Com ela definida, criar
conta exige o código. Desde 08/09/2026 a API **avisa no boot** quando a
combinação perigosa está no ar — mestra ligada, login ligado, convite ausente:

```
ATENCAO: a API responde 401 para anonimo, mas o CADASTRO esta aberto.
  POST /auth/registrar -> POST /auth/entrar -> o JWT le tudo que a
  mestra protege. Deixar de ser anonimo custa tres chamadas.
  Defina FRAUS_CODIGO_CONVITE para exigir codigo em /auth/registrar,
  ou nao publique esta instalacao fora da maquina.
```

Continua sendo **aviso, não recusa de subir**: cadastro aberto é o
comportamento certo em `localhost`, que é o uso declarado do projeto. O que
faltava era a frase, não a tranca.

#### A autenticação já vem ligada

**Na primeira vez que a API sobe, ela liga sozinha.** Gera a chave mestra e uma
chave de acesso para a dashboard, grava as duas em `.fraus-chaves.txt` (fora do
git) e anuncia o caminho no boot:

```
Primeira subida: autenticacao LIGADA.
  Mestra e chave de acesso gravadas em: .../.fraus-chaves.txt
  Esta e a unica copia em claro delas -- o banco guarda so o hash.
```

Você não clica em nada e não copia nada: **a dashboard lê a chave de acesso
desse arquivo sozinha**. Gerar credencial é trabalho do projeto, não de quem só
quer usar o produto — ninguém deveria precisar saber que uma chave mestra
existe para estar protegido por ela.

A **ordem** dessa geração é a parte que importa: o arquivo é escrito **antes**
de o hash da mestra ir para o banco. Se a escrita falhar (pasta somente
leitura, disco cheio), nada é gravado e a API sobe **aberta, com aviso** — uma
API aberta que avisa é um problema recuperável; uma API fechada cuja única
chave não existe em lugar nenhum é um tijolo.

Não liga sozinha quando já há mestra no banco (não é a primeira subida) ou
quando `FRAUS_CHAVE_MESTRA` está no ambiente — a variável vence a gravada, e
gerar uma segunda credencial que perde para ela seria escrever no arquivo uma
chave que não abre nada.

**Ligando à mão**, se a instalação é antiga ou você reabriu a API: abra
**Configurações → Autenticação** e clique em *Ligar autenticação*. A API gera a chave mestra, grava o hash dela e emite junto
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
FRAUS_CHAVE_MESTRA=<segredo> uv run python -m uvicorn fraus.api.main:app

# 3. Toda rota agora exige chave. Gere uma chave de ACESSO para a dashboard:
curl -X POST 127.0.0.1:8000/acesso/chaves \
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

#### Precedência: a variável **exclui** a gravada

Definida a `FRAUS_CHAVE_MESTRA`, a mestra do banco **deixa de autorizar** — não
é uma segunda credencial válida em paralelo, é substituição. Sem a variável, a
gravada volta a valer sozinha, e é isso que faz a autenticação ligada pelo botão
sobreviver a reiniciar o processo.

> **Corrigido em 25/08/2026, e a inversão é deliberada.** Até aqui `e_mestra`
> devolvia `ambiente OU banco`: as duas valiam ao mesmo tempo. Havia teste
> afirmando isso, com o argumento de que recusar a do banco trancaria fora quem
> tinha ligado pela tela. O argumento tem saída trivial — **apagar a variável
> devolve o posto à mestra do banco**. O que a união criava não tinha saída: este
> README apresenta a variável como o caminho de quem **perdeu ou vazou** a
> mestra, e com a união a vazada continuava abrindo tudo. Pior, a variável
> definida faz `POST /acesso/mestra` recusar a rotação com 409 — então não
> restava caminho nenhum pela API para matar a chave vazada.
>
> A assimetria é o argumento inteiro: ser trancado fora é **reversível**;
> credencial vazada que sobrevive ao procedimento de revogação documentado
> **não é**. Fixado em `tests/test_autenticacao_runtime.py`, nos dois sentidos.

`GET /acesso/estado` responde `{"ligada": ..., "origem": "ambiente"|"banco"|null}`
e é a **única** rota que continua pública com a autenticação ligada — a tela
precisa dela justamente quando ainda não há credencial para apresentar.

**Desligar não é botão.** Um controle que baixa a defesa numa tela sem login não
tem contrapartida de risco aceitável: desligar é apagar a variável e a linha
`chave_mestra` do banco.

**As chaves de acesso têm painel próprio**, em Configurações → *Chaves de
acesso*: lista o que existe (nome, dica dos 4 últimos caracteres, data — nunca
o hash), emite uma nova (que aparece em claro **uma única vez**) e revoga, com
confirmação. Como gerenciar chave é privilégio da mestra e a dashboard carrega
apenas a de acesso, o painel **pede a mestra** — ela fica só na memória da aba,
nunca em cookie, `localStorage` ou URL. Com a API aberta ele carrega sozinho,
porque nesse estado a API não cobra credencial e pedi-la seria a tela inventar
uma exigência.

Pelas rotas, o mesmo: `GET /acesso/chaves` lista, `POST` emite e
`DELETE /acesso/chaves/{id}` revoga na hora — a chamada seguinte com a chave
revogada leva 401. Se uma chave de acesso vazar, revogue-a sem trocar a mestra;
se a **mestra** vazar, troque-a: as chaves de acesso continuam valendo, quem
perde o posto é só ela.

**Se a mestra se perdeu**, ela não volta — o banco guarda só o hash. Além da
saída pelo ambiente (`FRAUS_CHAVE_MESTRA` vence a gravada), há o comando que
reabre a API de vez:

```bash
uv run python scripts/resetar_mestra.py   # pede a palavra DESLIGAR
```

Ele apaga a linha `chave_mestra` e devolve a API ao estado aberto, para ligar
de novo ser possível. **As chaves de acesso e de fonte não são apagadas**: quem
perdeu a mestra não perdeu o que já distribuiu, e elas voltam a valer quando a
autenticação for ligada. É comando de terminal, e não botão, pela mesma razão
de sempre — desligar pela rede seria uma chamada que baixa a defesa, alcançável
justamente quando a API está aberta.

Para importar um CSV, coloque o arquivo dentro de `dados_brutos/` e mande o
caminho relativo a ela:

```bash
curl -X POST 127.0.0.1:8000/conversas/importar \
  -H 'content-type: application/json' \
  -d '{"caminho": "atendimentos.csv"}'
```

Qualquer caminho que escape dessa raiz (`../..`, caminho absoluto de fora) é
rejeitado com **400**. Coluna estrutural ausente no CSV também dá **400**,
nomeando a coluna; linha individual malformada não derruba o lote — ela volta
na resposta, em `motivos`.

#### Enviando um atendimento pela rede (`POST /ingestao`)

É o único caminho de escrita que não pede acesso ao disco da máquina, e a
**chave de fonte** (`frs_...`) é a única credencial aceita nele — a mestra e a
chave de acesso levam 401 aqui, de propósito: uma credencial por rota. O
**canal** é o da fonte cadastrada, não o que vier no corpo.

**Tem teto: 120 escritas por minuto, por fonte** — e o webhook tem o mesmo, com
contador próprio (uma fonte pode receber pelos dois caminhos, e janela
compartilhada faria a importação por uma rota cortar a integração da outra). Passou disso, `429` com
`Retry-After`. Cada escrita roda o Motor inteiro (BERTimbau, emoção, ironia,
fusor) em CPU, e sem teto uma chave vazada valia um laço de shell ocupando o
processo — [OWASP API4:2023](https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/).
A contagem é **por fonte autenticada**, nunca pela chave crua: o id da fonte
vem em texto claro dentro da chave, então contar antes de conferir o hash
deixaria um anônimo gastar a janela da integração legítima — a defesa viraria
a arma. Duas fontes não dividem janela, e o teto não alcança leitura.

```bash
curl -X POST 127.0.0.1:8000/ingestao \
  -H "Authorization: Bearer frs_..." \
  -H 'content-type: application/json' \
  -d '{"id":"atendimento-123","mensagens":[
        {"autor":"cliente","texto":"meu pedido não chegou","enviada_em":"2026-08-14T10:00:00-03:00"},
        {"autor":"bot","texto":"vou verificar","enviada_em":"2026-08-14T10:00:12-03:00"}
      ]}'
```

**No PowerShell esse comando não roda** — e falha de um jeito que não parece
falha de shell. `curl` ali é **alias de `Invoke-WebRequest`**, que não conhece
`-X`, `-H` nem `-d`, e a `\` no fim da linha não continua comando nenhum: cada
linha vira um comando solto (`O termo '-H' não é reconhecido…`). O equivalente
nativo, que é o que rodar na banca:

```powershell
$corpo = @{
  id = "atendimento-123"
  mensagens = @(
    @{ autor = "cliente"; texto = "meu pedido não chegou"; enviada_em = "2026-08-14T10:00:00-03:00" }
    @{ autor = "bot";     texto = "vou verificar";         enviada_em = "2026-08-14T10:00:12-03:00" }
  )
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri http://127.0.0.1:8000/ingestao -Method Post `
  -Headers @{ Authorization = "Bearer frs_..." } `
  -ContentType "application/json; charset=utf-8" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($corpo))
```

O `UTF8.GetBytes` **não é firula**: passar `-Body` como string faz o
PowerShell 5.1 serializar na codepage do sistema, e `não chegou` chega à API
como `n?o chegou`. O léxico perde a negação, o BERTimbau lê outro texto, e o
score sai errado por um defeito de terminal — o tipo de bug que se procura no
modelo por horas.

Se preferir o curl de verdade, chame-o pelo nome completo (`curl.exe`), **numa
linha só** e trocando a `\` pela crase `` ` `` — o Windows 11 traz o binário.
Nos outros exemplos deste README vale a mesma tradução; e para definir variável
de ambiente, `$env:FRAUS_CHAVE_MESTRA = "..."` antes do comando, já que
`VAR=valor comando` é sintaxe de bash.

#### Recebendo atendimento por webhook (`POST /integracoes/webhook/{fonte_id}`)

É o segundo caminho de escrita pela rede, ao lado de `POST /ingestao`. A
diferença é a credencial: `/ingestao` pede uma chave `frs_` no cabeçalho
`Authorization`, e este endpoint confere uma **assinatura HMAC** sobre o corpo,
no padrão [Standard Webhooks](https://www.standardwebhooks.com/) — quem integra
usa biblioteca de prateleira, em vez de ler a nossa documentação. Depois de
autenticar, o que as duas rotas fazem é o **mesmo código**
(`fraus/api/registro.py`): o canal vem da fonte cadastrada, e o veredito é
derivado no servidor.

**1. Cadastre a fonte, com `tipo: "webhook"` e o nome de uma variável de
ambiente** (ela ainda não precisa existir no ambiente — só o nome):

```bash
curl -X POST 127.0.0.1:8000/integracoes/fontes \
  -H 'content-type: application/json' \
  -d '{"nome":"WhatsApp","canal":"whatsapp","tipo":"webhook","variavel_segredo":"FRAUS_SEGREDO_WHATSAPP"}'
```

Errou o nome? **Corrija sem recriar a fonte** — recriar troca o `fonte_id`, e
com ele a URL que a plataforma já tem configurada. O campo aceita só formato de
variável de ambiente (`FRAUS_SEGREDO_WHATSAPP`), o que recusa o engano de colar
o próprio `whsec_...` ali; `null` limpa. Na tela, é o botão "Corrigir o nome da
variável" no bloco do segredo.

```bash
curl -X PATCH 127.0.0.1:8000/integracoes/fontes/1 \
  -H "Authorization: Bearer <mestra>" -H 'content-type: application/json' \
  -d '{"variavel_segredo":"FRAUS_SEGREDO_WHATSAPP"}'
```

**2. Gere o segredo** (privilégio da mestra, como as demais rotas de
credencial):

```bash
curl -X POST 127.0.0.1:8000/integracoes/fontes/1/segredo \
  -H "Authorization: Bearer <mestra>"
# → {"segredo": "whsec_...", "variavel": "FRAUS_SEGREDO_WHATSAPP", "aviso": "..."}
```

O segredo sai em claro **uma única vez** — o Fraus não grava essa resposta em
lugar nenhum, nem o hash: HMAC exige o segredo em claro no servidor toda vez
que uma assinatura é conferida, e guardar valor recuperável no SQLite desfaria
a propriedade que faz um backup vazado não levar credencial junto. Perder o
segredo custa gerar outro.

**3. Defina a variável no ambiente da API — e REINICIE o processo.**
`os.environ` é lido pelo processo em execução; escrever a variável e continuar
com a mesma API no ar não muda nada que ela enxerga. Sem reiniciar, o operador
vê **503** com o segredo aparentemente "definido" (definido no terminal onde
ele rodou o `export`, não no processo que está de pé):

```bash
export FRAUS_SEGREDO_WHATSAPP=whsec_...
uv run python -m uvicorn fraus.api.main:app --reload
```

**4. Entregue a URL e o segredo à plataforma**, e assine cada evento antes de
mandar.

O contrato:

- **URL:** `POST /integracoes/webhook/{fonte_id}`, o id devolvido no cadastro
  da fonte.
- **Três cabeçalhos**, no padrão Standard Webhooks: `webhook-id` (identifica o
  evento — é a chave da deduplicação), `webhook-timestamp` (segundos desde a
  época) e `webhook-signature` (`v1,<assinatura em base64>`; pode trazer mais
  de uma assinatura separada por espaço, para rotação de segredo sem janela de
  indisponibilidade).
- **O que se assina:** `{webhook-id}.{webhook-timestamp}.{corpo}`, os três
  concatenados nessa ordem, com o corpo em **bytes crus** — nunca o
  dict/JSON re-serializado, porque HMAC é byte-exato e reordenar uma chave ou
  mudar um espaço muda a assinatura.
- **Corpo:** o mesmo contrato de `POST /ingestao` (`PedidoIngestao`) — `id`,
  `mensagens` (com `autor`, `texto`, `enviada_em` timezone-aware) e os campos
  opcionais `encerrada_em`/`escalou_para_humano`. O canal não entra: é o da
  fonte cadastrada.

Exemplo de assinar em Python, curto o bastante para colar direto — a chave
HMAC é o **base64 decodificado** do segredo, não a string `whsec_...` inteira
(usar a string inteira mataria o único motivo de adotar o padrão: a biblioteca
do outro lado faz o decode, geraria outra assinatura, e nada bateria):

```python
import base64
import hashlib
import hmac
import time

segredo = "whsec_..."          # o valor gerado no passo 2
webhook_id = "evt-001"         # um id por evento, único por fonte
timestamp = str(int(time.time()))
corpo = b'{"id":"atendimento-123","mensagens":[...]}'   # bytes exatos do POST

chave = base64.b64decode(segredo.removeprefix("whsec_"))
conteudo = f"{webhook_id}.{timestamp}.".encode() + corpo
assinatura = base64.b64encode(
    hmac.new(chave, conteudo, hashlib.sha256).digest()
).decode()

headers = {
    "webhook-id": webhook_id,
    "webhook-timestamp": timestamp,
    "webhook-signature": f"v1,{assinatura}",
    "content-type": "application/json",
}
# requests.post(f"http://127.0.0.1:8000/integracoes/webhook/1", data=corpo, headers=headers)
```

A conferência dos status, na ordem em que o porteiro os produz — identidade,
depois autoridade, depois parse, nunca o contrário:

| Status | Quando |
|---|---|
| **201** | aceito: a conversa foi gravada, o corpo da resposta traz o veredito |
| **200** | reentrega: mesmo `webhook-id` já **aceito** antes para esta fonte — o Standard Webhooks manda a plataforma retentar diante de qualquer resposta fora de 2xx, então responder erro a uma reentrega legítima poria a integração em laço |
| **400** | corpo fora do contrato, `webhook-timestamp` fora da janela de 5 minutos, ou um dos três cabeçalhos ausente |
| **401** | assinatura não confere |
| **403** | fonte cadastrada e desativada |
| **404** | `fonte_id` inexistente |
| **503** | variável de ambiente ausente, ou com valor que não é um segredo válido |

**Por que o último é 503 e não 401.** Variável ausente é defeito da **máquina
que hospeda a API**, não de quem chamou — a assinatura de quem integra pode
estar perfeita e a resposta seria a mesma. Responder 401 mandaria o integrador
caçar um problema que não é dele: reconferir a assinatura, gerar segredo novo,
reler a própria implementação — quando o conserto real é reiniciar o processo
da API com a variável definida.

**A ressalva honesta: HMAC prova origem e integridade, não confidencialidade.**
A assinatura garante que o corpo veio de quem tem o segredo e não foi alterado
no caminho — não que ninguém no caminho o leu. O corpo trafega **legível**
para qualquer um posicionado entre a plataforma e a API, e ele carrega fala
real de cliente. Quem publica a API precisa de TLS; ver
[docs/hospedagem.md](docs/hospedagem.md), que já descreve o túnel Cloudflare
usado para demonstração.

**Limitação declarada: não há adaptador de plataforma nenhuma.** O Fraus
recebe eventos num **contrato documentado** — o mesmo de `PedidoIngestao` —, e
não há tradutor embutido para o formato de Zendesk, Meta (WhatsApp Business),
Twilio ou qualquer outra plataforma nomeada. Traduzir o payload da plataforma
para este contrato, e assinar com o segredo dela, é trabalho de quem integra.
Não é plug-and-play.

#### Conferindo as integrações contra um servidor de verdade

```bash
uv run python scripts/smoke_integracoes.py
```

Sobe a API **real** num banco e num arquivo de chaves temporários (apagados no
fim), com a autenticação ligada, e percorre fonte → chave → `/ingestao` →
webhook assinado → reentrega → assinatura inválida → leitura, conferindo cada
status. Existe porque a suíte usa `TestClient`, e a armadilha 8 do handoff (o
middleware recusando o webhook antes de olhar a assinatura) só aparece com
uvicorn de pé e a mestra ligada. Sai com código 1 se algo divergir.

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
`http://127.0.0.1:8000`), anexando `Authorization: Bearer ${FRAUS_CHAVE_ACESSO}`
quando essa variável existe. A chave de acesso nunca toca o navegador.

```bash
FRAUS_API_URL=http://127.0.0.1:8000 FRAUS_CHAVE_ACESSO=fra_... npm run dev
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

### 5. Quando a API não está no ar

A dashboard é uma casca sobre a API: sem ela, toda tela fica vazia. Um aviso no
topo de qualquer tela diz isso com todas as letras — *as telas ficam vazias
porque o dado vem dela, não porque não há atendimento* — e carrega o comando
para subir, pronto para copiar, mais um botão de **tentar de novo**.

**Modo local.** Rodando `npm run dev`, o aviso já vem com um botão **Iniciar
API** — sem precisar de nenhuma variável: ele sobe o `uvicorn` como processo
filho do servidor Next, mostra "subindo…" e recarrega a tela sozinho quando
`GET /saude` responde. Essa rota não carrega os três BERTimbau;
`GET /saude/prontidao` distingue `frio`, `carregando`, `pronto` e `erro`.

```bash
cd dashboard && npm run dev
```

**Em produção (`npm run build && npm run start`) o botão some por padrão.**
`FRAUS_MODO_LOCAL` é o override explícito nos dois sentidos: `=1` liga mesmo
num build de produção (raro, e por isso exige o passo extra), `=0` desliga
mesmo em dev, para testar a dashboard como ela se comporta publicada.

**Não habilite isso num deploy real.** É uma rota HTTP que executa um comando —
em uso local é conveniência, publicada é execução remota de código. Ela existe
sob cinco travas: desligada por padrão fora de desenvolvimento (sem ela
responde **404**, não 403 — quem não deveria saber que ela existe não
descobre); comando **literal** no código-fonte, sem nada vindo da requisição e
sem shell; uma instância por vez (consulta `/saude` antes de subir e confere se
o processo lembrado ainda está vivo); a API subida escuta apenas em
`127.0.0.1`; e **só a própria dashboard pode chamá-la** — requisição de outro
site leva 403, porque as quatro travas anteriores defendem contra *comando*
arbitrário e nenhuma delas perguntava *quem* pediu. Se `FRAUS_API_URL` aponta
para outra máquina, o botão não aparece — não há o que iniciar aqui.

**Desligar** tem botão, no rodapé da navegação, ao lado do "API no ar" — e ele
só aparece para a API que **esta dashboard subiu**. Um `uvicorn` que você
iniciou no terminal continua fora do alcance da tela: a rota responde **409**
dizendo isso, porque derrubar processo de outra pessoa não é poder que uma tela
sem login deva ter. O que ela encerra é a **árvore** do processo, não o pid: o
que a dashboard inicia é o `uv`, e o servidor que atende na porta é neto dele —
matar só o pid deixaria a API no ar, órfã, com o botão anunciando que a
desligou.

A subida **não abre janela de terminal**. O `stdout` da API vai para
`dashboard/.fraus-api.log`, que é onde olhar quando ela falha — o motivo mais
comum é modelo ausente em `modelos/`, que derruba o boot por design.

### 6. Produção: dashboard e API separadas

Desde **17/09/2026**, o Fraus roda integralmente em produção sem depender da
máquina de desenvolvimento:

```text
dashboard Next.js (Vercel: fraus)
        │ proxy server-side + FRAUS_CHAVE_ACESSO
        ▼
API FastAPI/ONNX (Vercel: fraus-api, Large Function)
        ├── estado persistente → Supabase Postgres (transaction pooler :6543)
        └── modelos no build  → Oracle Object Storage (bucket privado + PAR)
```

Os dois projetos Vercel usam o mesmo repositório, mas têm configurações
independentes: [`dashboard/vercel.json`](dashboard/vercel.json) impede o build
do front de herdar o comando da API; [`vercel.json`](vercel.json) prepara a
função Python. Durante o build, `scripts/preparar_modelos_vercel.py` baixa um
ZIP privado, confere o SHA-256, recusa *path traversal*, valida os três grafos
ONNX, tokenizadores e fusor, e só então permite o deploy.

O runtime usa satisfação e emoção em ONNX fp32 e ironia quantizada em int8. O
pacote publicado em **30/09/2026 tem 1,95 GB** (1,46 GB na entrega de 17/09),
aceito por Large Functions. Isso é tamanho do pacote, não memória consumida.
Importar a função é barato; o provedor aquece os modelos em segundo plano no
boot e em `/saude`. `/saude/prontidao` responde 503 até terminar. Na medição
histórica de 17/09, o primeiro `/saude` levou **10,8 s** e uma inferência logo
depois, **0,8 s**; esses tempos não são uma promessa para instâncias novas.

Dashboard e API publicam separadamente. Em 30/09, a API da PR #75 foi
publicada a partir da `main` (`ab1b5da`), corrigindo o 404 de Operação. O
workflow da API é manual e ainda precisa de secrets; merge do front não o aciona.

Endereços verificados em 17/09/2026:

- dashboard: <https://fraus-one.vercel.app>;
- API: <https://fraus-api.vercel.app>;
- saúde via API e via proxy: `{"status":"ok","motor":"real"}`.

O passo a passo, as variáveis e o diagnóstico das falhas encontradas estão em
[Deploy gratuito na Vercel](docs/deploy-vercel.md).

#### Alternativa temporária: API na sua máquina por túnel

Para **demonstrar** a dashboard publicada (Vercel) falando com a API de verdade,
sem hospedar a API em lugar nenhum: um túnel dá um endereço `https` público
temporário para o `uvicorn` que roda no seu computador.

O túnel continua útil para desenvolvimento e contingência. Ele não é mais o
caminho de produção: a combinação ONNX + Large Functions + artefatos baixados
no build removeu o limite que impedia empacotar os modelos na função.

Enquanto a API vive na sua máquina, o túnel é o caminho de dois minutos.

```bash
# 1. Suba a API com os modelos (uma vez; leva 30-60 s carregando os BERTimbau).
#    Windows/PowerShell: troque `export X=y` por `$env:X = "y"`.
export FRAUS_CAMINHO_MODELO_TEXTO=modelos/bertimbau-satisfacao
export FRAUS_CAMINHO_MODELO_EMOCAO=modelos/bertimbau-emocao
export FRAUS_CAMINHO_MODELO_IRONIA=modelos/bertimbau-ironia
export FRAUS_CAMINHO_FUSOR=modelos/fusor.joblib
export FRAUS_CAMINHO_METRICAS=modelos/bertimbau-satisfacao/metricas.json
export FRAUS_CAMINHO_METRICAS_EMOCAO=modelos/metricas_emocao.json
export FRAUS_CAMINHO_METRICAS_IRONIA=modelos/metricas_ironia.json
export FRAUS_CHAVE_MESTRA=$(openssl rand -hex 32)   # GUARDE: some ao fechar o shell
uv run python -m uvicorn fraus.api.main:app --host 127.0.0.1 --port 8000

# 2. Gere a chave de ACESSO da dashboard (outro terminal), com a mestra acima.
curl -X POST http://127.0.0.1:8000/acesso/chaves \
  -H "Authorization: Bearer $FRAUS_CHAVE_MESTRA" \
  -H "Content-Type: application/json" \
  -d '{"nome":"dashboard-vercel"}'
# → devolve `fra_...` UMA única vez.

# 3. Abra o túnel (outro terminal). A URL sai no stdout, em "Your quick Tunnel".
cloudflared tunnel --url http://127.0.0.1:8000
```

No `uv run`, prefira `python -m uvicorn` a chamar `uvicorn` direto: no Git Bash
do Windows o executável do `uv` falha com *"trampoline failed to canonicalize
script path"*.

Na Vercel (**Settings → Environment Variables**, depois um redeploy — variável
server-side só entra em processo novo):

| Variável | Valor |
|---|---|
| `FRAUS_API_URL` | a URL `https://....trycloudflare.com` do passo 3 |
| `FRAUS_CHAVE_ACESSO` | a chave `fra_...` do passo 2 |

`FRAUS_ORIGENS` **não** é necessária: quem chama a API é o servidor Next, não o
navegador, e requisição de servidor não faz preflight de CORS.

**O que o túnel exige, e o que ele não perdoa:**

- **Sua máquina precisa estar ligada** com os dois processos vivos. Fechou o
  terminal, acabou a demonstração.
- **A URL muda a cada `cloudflared tunnel --url`.** Um túnel rápido é anônimo e
  descartável; reabrir significa atualizar `FRAUS_API_URL` na Vercel e
  redeployar. Para um endereço fixo, é preciso túnel nomeado com domínio.
- **Defina `FRAUS_CHAVE_MESTRA` ANTES de abrir o túnel.** Sem ela a API sobe
  aberta, e o túnel publica na internet uma API que grava no seu banco. Com ela,
  quem chegar no endereço esbarra em **401** — em toda rota menos duas, que têm
  credencial própria e por isso não passam pela chave: `POST /ingestao` (chave
  de fonte `frs_`) e `POST /integracoes/webhook/{fonte_id}` (assinatura HMAC).
- **A rota do webhook é anônima por desenho, e continua sendo uma porta pública
  de escrita.** Ela não pede `Authorization` porque a credencial dela é a
  assinatura do corpo: a plataforma que entrega ali não tem, nem pode ter, uma
  chave `fra_`. Quem não souber o segredo daquela fonte não consegue gravar nada
  — sem assinatura válida a entrega para no porteiro, e cada tentativa fica no
  histórico de entregas da fonte. O que fica exposto é o endereço: com o túnel
  aberto, qualquer um pode **chamar** `/integracoes/webhook/{id}` e gerar
  tentativas recusadas. Publique sabendo disso, e guarde o segredo com o mesmo
  cuidado da chave mestra.
- A mestra protege a **API**, não a **dashboard**: a dashboard publicada não tem
  login, e quem tem o link lê os dados por ela. Para demonstrar com atendimento
  real, ligue também a **Vercel Deployment Protection**.
- **Feche o túnel quando terminar** (`Ctrl+C`).

**Sem a API no ar, o deploy não quebra.** Todas as telas são `force-dynamic` e
`lib/api.ts` devolve `Resultado<T>` em vez de lançar: o build da Vercel passa sem
falar com a API, e cada tela nomeia o que falta em vez de mostrar zero. Publicar
a dashboard antes de resolver a hospedagem é uma opção honesta.

## Roadmap

Onde o trabalho está. **Entregue** é o que existe no repositório e tem teste ou
verificação por trás; **falta** está detalhado em [Pendências](#pendências), e a
ordem lá é a ordem de importância.

### Estado atual — 30/09/2026

Análise persistida, Operação e convites estão mesclados e publicados. A suíte
da `main` passou nos dois dialetos de banco. Contratos, validações e pendências
de configuração estão na [referência interna](docs/notas/2026-09-30-operacao-producao.md).

### Revisão histórica — 17/09/2026

Revisão do projeto inteiro (testes rodados, API real e webhook exercitados com
`curl`, front auditado). Esta revisão registra o estado daquela data; o estado
operacional atual está acima. As pendências científicas exigem sua própria
evidência de resolução e não são encerradas pela publicação de Operação.

**Verificado em 14/09/2026:** a API real (`motor: real`) e o webhook funcionam
de ponta a ponta **com a mestra ligada** — cadastro de fonte, chave `frs_`,
`POST /ingestao` (201), webhook assinado (201), duplicada (200), assinatura
inválida (401), log de entregas. 205 testes de API/webhook/autenticação/vazão
verdes. Suíte completa: **860 passed, 1 failed** (a falha é ambiente — `psycopg`
ausente no venv; `uv sync --extra dev` resolve).

#### P0 — ameaça a banca

- [ ] **Decidir o domínio do tempo no score.** Com 3 h de espera, a latência
  pesa −85 contra +4,6 do texto (z-score explode fora da distribuição de
  treino). Opções: teto na latência, escala log (ambas com retreino do fusor)
  ou declarar como limitação. **Medido** por
  `scripts/medir_dominio_do_tempo.py`: o relógio empata com o texto em **411 s
  (6,9 min)** — 4 desvios acima da média do treino — e manda dali em diante,
  sem teto. Detalhe em `docs/handoff.md` §7.
- [ ] **Ironia ainda sai promotor** quando o relógio não contradiz — limite da
  cabeça de texto, hoje marcado pela contestação. Declarar ou atacar.
- [ ] **Retreinar a cabeça de ironia** (`notebooks/04_treino_ironia.ipynb`) e
  apertar os limiares de `tests/test_ironia_dominio.py`.
- [x] **Hospedagem sem VM e sem custo fixo** — concluída em 17/09/2026. Front e
  API são projetos Vercel separados; modelos vêm do Oracle Object Storage e o
  estado persiste no Supabase. Não depende mais de conseguir uma Ampere A1 nem
  de manter a máquina local ligada. Ver [deploy](docs/deploy-vercel.md).

#### P0 — desempenho pós-deploy

A hospedagem resolveu disponibilidade, não latência. Medição de 17/09/2026:
landing quente em 0,26–0,59 s, API quente em 0,17–0,66 s, mas cold start da API
em **10,8 s**. A landing transfere cerca de **799 KB de JavaScript** em 12
chunks, além de 71 KB de HTML. Diagnóstico completo em
[Pendências pós-deploy](docs/notas/2026-09-17-pendencias-pos-deploy.md).

- [x] **Separar plano de controle e motor.** `/saude`, autenticação e CRUD não
  carregam os três BERTimbau. Um provedor thread-safe inicializa o motor apenas
  quando usado, e `/saude/prontidao` expõe seu estado sem aquecê-lo.
- [ ] **Tornar a landing independente da API.** Hoje ela consulta sessão e
  disponibilidade de login antes de renderizar, perde cache de CDN e pode
  pagar o cold start inteiro apenas para escolher o texto do CTA.
- [ ] **Reduzir o JavaScript da landing.** Adiar partículas/WebGL e Motion,
  definir orçamento de bundle e medir dispositivo móvel antes de preservar
  animação puramente decorativa.
- [ ] **Instrumentar latência.** Registrar cold/warm start, tempo de modelo,
  banco e proxy; coletar Web Vitals. Sem decomposição, “site lento” volta a ser
  impressão em vez de regressão verificável.

#### P0 — ingestão genérica: analisar qualquer arquivo sem código por formato

Hoje cada estrutura exige um adaptador à mão (`csv_driver`, `totalk`,
`transcricao`). O desenho proposto, **sem LLM em runtime** (invariante 1):

- [x] **Camada leitor** — **feita em 14/09/2026** (`fraus/ingest/leitores.py`), só com biblioteca padrão: codificação utf-8→cp1252→latin-1, delimitador por consistência de largura (vence o `;` do Excel pt-BR com vírgula dentro de aspas), JSON/JSONL aninhado com herança do id do pai, WhatsApp Android/iOS. Pendente: MarkItDown para docx/pdf e CleverCSV/charset-normalizer só se um arquivo real vencer as regras. Desenho original: formato → tabela.
  `charset-normalizer` (encoding), `CleverCSV` (dialeto, resolve o `;` do Excel
  pt-BR), `openpyxl` (xlsx), `json` + `json_normalize` (JSON aninhado: Discord,
  Telegram, Zendesk), parser próprio de WhatsApp `.txt` (**não** usar whatstk:
  GPL-3.0), `MarkItDown` para docx/pdf (MIT, offline). Docling descartado
  (baixa modelos, lento em CPU).
- [x] **Camada mapeador** — **feita em 14/09/2026** (`fraus/ingest/mapeador.py`, `difflib` no lugar do `rapidfuzz`, atribuição gulosa no lugar da húngara; quem é cliente por recorrência entre conversas ou por quem abre). Desenho: tabela → `Conversa` com
  confiança por papel (`conversa_id`, `autor`, `texto`, `enviada_em`, `canal`).
  Nome de coluna por sinônimos pt/en com `rapidfuzz` + perfil de conteúdo
  (coluna que parseia como data, poucos valores distintos = autor, texto longo
  = mensagem, cardinalidade em blocos = id) + atribuição húngara.
- [x] **Data ambígua** — **feita em 14/09/2026** (armadilha Totalk `MM/DD`): campo > 12 desempata; senão a
  interpretação com menos saltos negativos na ordem das mensagens; empate =
  confirmação obrigatória. Data sem fuso vira **aviso visível**, nunca naive
  silencioso (invariante 6). Sem horário, sem nota (§3.2 do handoff).
- [x] **Perfis de mapeamento** — **feito em 14/09/2026**: tabela
  `perfis_mapeamento` (só nomes de coluna e papéis, nunca conteúdo), chave =
  assinatura das colunas sem ordem/caixa/acento, aplicado sozinho no próximo
  arquivo e avisado. Gravar e apagar são rota administrativa, como o léxico.
  **A Totalk NÃO virou perfil, por decisão:** o export dela exige lógica que
  mapa de colunas não expressa (`De: X Para: Y`, assinatura `*Nome:*` separando
  bot de atendente, id dentro de URL) — continua adaptador.
- [x] **Prévia e confirmação** — **feitas em 14/09/2026**. `POST /analisar/previa`
  (sem modelo, sem gravar: mapeamento sugerido, amostra censurada, avisos,
  perfil casado); `/analisar/arquivo` aceita `mapeamento` e `ordem_data`
  confirmados (nunca score — invariante 3); `GET/POST/DELETE
  /perfis-mapeamento`. Na tela de Analisar, o painel **Conferir colunas**
  aparece só quando as colunas foram inferidas: um seletor por papel com a
  força da evidência (não "confiança" — não é probabilidade calibrada), a
  ordem da data quando ambígua, as primeiras linhas e "lembrar este
  mapeamento". Verificado na API real com Playwright, inclusive a 390px.
- [x] **Prévia na importação em lote** — **feita em 15/09/2026**. A importação
  lê qualquer formato pelo mesmo `extrair` da análise; colunas inferidas **só
  gravam com perfil confirmado** (409 sem ele) e arquivo sem horário é recusado
  (400). `POST /conversas/importar/previa` e a mesma conferência de colunas na
  tela de Integrações. O corpo da importação segue só com `caminho`.
- [x] **docx com tabela** — **feito em 15/09/2026**, sem MarkItDown: o
  `python-docx` já instalado lê a tabela, que passa pelo mapeador e recebe nota
  quando tem coluna de horário. Tabela sem cabeçalho (uma linha por fala) segue
  como prosa, para não perder a primeira fala. **PDF com tabela fica de fora**:
  exigiria extração de layout pesada, e PDF de atendimento raramente traz hora.
- [ ] Fixtures de **exports reais** (Discord, Telegram, Zendesk, Blip) — os testes de 14/09 cobrem WhatsApp, JSON aninhado e CSV `;` em cp1252 sintéticos. Declarar o limite: "qualquer arquivo" = qualquer estrutura com
  texto e autor identificáveis.

#### P1

- [x] **Branches** — **resolvidas em 14/09/2026**: #40, #41 e #42 mescladas;
  `pendencias/sinais-invertidos-e-vazao-do-webhook` não tinha nada fora da main;
  o único commit de `medicao/dominio-do-tempo` (o laudo
  `scripts/medir_dominio_do_tempo.py`) foi trazido.
- [x] **Webhook — lacunas de uso** — **feitas em 14/09/2026**: `PATCH
  /integracoes/fontes/{id}` corrige `variavel_segredo` (e recusa nome que não
  seja de variável de ambiente), com botão na tela; exemplo em Python que
  calcula a assinatura no `ContratoDoWebhook`, **executado** por
  `tests/test_exemplo_de_assinatura.py`; `scripts/smoke_integracoes.py`. O
  reinício após trocar o segredo já estava documentado (passo 3).
- [x] **Invariante 2** — **feita em 14/09/2026**: a barra de classes do
  `Analisador` exige as três probabilidades, sem `?? 0`.
- [x] **Documentação desatualizada** — **feita em 14/09/2026** (handoff e
  tabela Entregue com 909/77 testes e contrato de 39).
- [ ] **Site da documentação:** criar `DEPLOY_KEY_DOCS`, `REPO_DOCS` e
  `FRAUS_URL_DASHBOARD` no repositório.

#### P1 — visual

- [x] **Piso de 11px** — **feito em 14/09/2026**, com guarda em
  `lib/tipografia.test.ts`. As etiquetas "estimativa" estavam em 10px.
- [ ] **Tema claro / modo apresentação para projetor** — decisão do dono do
  projeto (DESIGN.md §8: tema é decisão dele). Não feito.
- [x] **Foco de teclado** — contorno cheio de 2px em `:focus-visible` para quem
  não desenhava anel próprio; `TabsContent` ganhou anel.
- [x] **"NPS estimado"** sem asterisco de 9px; a nota virou frase direta.
- [x] **Celular (390px)** — conferido com Playwright. Achados e corrigidos:
  hidratação falhando em toda tela da dashboard abaixo de 768px; cabeçalho do
  atendimento espremido; vitrine rolando 96px na horizontal (a armadilha 0 do
  handoff media errado: `overflow-x: hidden` não barra rolagem programática).
  O grafo cabe.
- [x] **Contraste de texto atenuado** — `muted-foreground` a 60–70% saía
  2,8–3,4:1 sobre o vidro; opacidade removida, guarda em
  `lib/opacidade-de-texto.test.ts`.
- [x] **Vitrine sem WebGL** — a página inteira caía; agora só o campo de
  partículas some.

#### P2

- [x] ~~Agregados de léxico por classe e tempo mediano~~ — já existiam (`/lexico`, `/indicadores`, com recorte `de`/`ate`); o item estava desatualizado.
- [ ] Decisões: empresa fictícia, pin do `scikit-learn==1.6.1`, remover
  `content/fraus` da raiz.

### Entregue

| Frente | Estado | O que existe |
|---|---|---|
| **Modelo canônico e sinais** | ✅ | `Conversa`/`Mensagem`, as oito famílias de sinal (texto, emoji, tempo, emoção, léxico, ironia, estilo e incongruência), e o score 0–100 → nota 0–10 → categoria de NPS |
| **Três cabeças treinadas** | ✅ ⚠️ | satisfação, emoção (7 classes) e ironia no ar; a de **ironia não é confiável e, desde 04/09/2026, não pontua mais** — ver pendência 1 |
| **Fusor** | ✅ ⚠️ | **contrato em 39 features desde 04/09/2026** e **artefato em dia desde 08/09/2026**: `n_features_in_ = 39`, classes `[0 1 2]`, acurácia **0,950** e F1-macro **0,950** (contra 0,943 do fusor de 38). A API real sobe. O ⚠️ é outro: `incongruencia_situacao_negativa` entrou para alcançar a frase canônica e **não a alcançou** — ela continua saindo promotor sempre que o relógio não a contradiz — medido em 08/09/2026: 99,69 com 181 s de espera, 99,21 com 300 s (item 0 de [Falta](#falta)). A feature não nasceu morta — peso −0,193 no eixo satisfeito−insatisfeito —, só não é suficiente. Confira qualquer artefato com `uv run python scripts/conferir_fusor.py` |
| **Ingestão** | ✅ | CSV de `dados_brutos/` (com contenção de caminho) e `POST /ingestao` pela rede, por chave de fonte |
| **API modular** | ✅ | `main.py` só monta o app; um router por domínio, `Contexto` por injeção. O contrato HTTP foi verificado **byte a byte** no OpenAPI contra a versão anterior |
| **Autenticação** | ✅ | mestra + chaves de acesso (`fra_`) + chaves de fonte (`frs_`), decisão **por requisição**, hash no banco, revogação na hora |
| **Nasce fechada** | ✅ | a primeira subida gera mestra e chave de acesso, grava em `.fraus-chaves.txt` e a dashboard lê de lá — sem clique e sem cópia |
| **Ligar a autenticação sem terminal** | ✅ | botão em Configurações, para instalação antiga ou reaberta; a mestra sobrevive a reiniciar |
| **Gerenciar chaves sem terminal** | ✅ | painel que emite, lista e revoga chaves de acesso, pedindo a mestra; e `scripts/resetar_mestra.py` para quando ela se perde |
| **Dashboard sem terminal** | ✅ | **Iniciar API** (sem abrir janela de console) e **Desligar**, este último só para a API que a própria dashboard subiu — travas em [§5](#5-quando-a-api-não-está-no-ar) |
| **Diagnóstico honesto** | ✅ | régua de estado quando a API não responde; `/saude` fora da credencial declara qual motor serve e seu estado; `/saude/prontidao` separa readiness de liveness sem iniciar a carga; a barra lateral escreve "motor dublê — números sintéticos" em vez de "API no ar" quando o que responde é o dublê; estado vazio nunca afirma "não há atendimento" quando a causa é conexão |
| **Agregação no servidor (fim do N+1)** | ✅ | `/serie-temporal`, `/lexico`, `/indicadores` (com tempo mediano) e o recorte `de`/`ate` em `/conversas`; **nenhuma tela baixa transcrição** no caminho feliz |
| **Origem das escritas** | ✅ | as rotas do servidor Next que mudam estado recusam **403** o que vem de outro site (`Sec-Fetch-Site`, com `Origin` de reserva) |
| **Teto de corpo** | ✅ | **413** por `Content-Length` antes de qualquer parse, e o upload de `/analisar` lido em pedaços com abort no primeiro byte excedente |
| **Léxico curado** | ✅ | o que o analista ensina por cima do SentiLex e do ranking de emoji de 2015: cadastro, edição e revogação por rota e por painel; a curadoria **vence** o léxico base e atravessa até o score. Cada escrita versiona, a conversa grava com qual versão foi pontuada, a Visão geral **nomeia** a régua misturada e `POST /conversas/repontuar` a zera |
| **Análise persistida** | ✅ | `POST /analisar/registrar`, motor real, horários reais, gravação transacional e deduplicação; filtros, indicadores e grafo consultam o banco atualizado |
| **Operação** | ✅ | sete abas: Radar, Equipe e escala, Jornadas, Investigações, Replay, Laboratório e Acessos; hipóteses e limites explícitos; comparação de fusores depende do artefato candidato |
| **Equipes e convites** | ✅ | proprietário/gestor/membro, links com validade e limite, revogação e aceite transacional com JWT; escopo por canais e proteção do último proprietário |
| **Escopo e auditoria** | ✅ | filtros por canal antes da paginação, exportação temporária, versão de sessão revalidada e eventos encadeados por hash |
| **Hospedagem da aplicação real** | ✅ | dois projetos Vercel; pacote Python de **1,95 GB** em 30/09/2026; ONNX no build e Supabase persistente; rotas de Operação e proxy verificados; API tem publicação separada |
| **Suíte** | ✅ | CI da `main` em 30/09/2026: **1.091 passed, 4 skipped, 1 deselected** em cada dialeto (SQLite e PostgreSQL); **163 testes** no front (20 arquivos), TypeScript e build aprovados |

### Falta

Em ordem, com o detalhe em [Pendências](#pendências):

0. **A ironia continua escapando do score — limitação declarada, e a tentativa
   de conserto FALHOU.** A frase canônica do projeto, `"que atendimento
   maravilhoso, so esperei 3 horas"`, sai **promotor sempre que o relógio não a
   contradiz** — 99,69 com 181 s de espera, 99,21 com 300 s, medidos em
   08/09/2026 contra a API real. (Com três horas *dentro do log* o relógio já
   derruba o score sozinho, para 0,00; os 99,9 são o caso rápido, que é real e
   comum — o cliente ironiza sobre uma espera ocorrida **fora** daquele
   atendimento. Desde 08/09/2026 a faixa do meio carrega a **contestação**, ver
   [Limitações conhecidas](#limitações-conhecidas).)

   A rota proposta foi implementada e treinada: `incongruencia_situacao_negativa`
   (lista curada de situação negativa de atendimento, desenho em
   [docs/superpowers/specs/2026-09-04-incongruencia-implicita-design.md](docs/superpowers/specs/2026-09-04-incongruencia-implicita-design.md))
   entrou no vetor em 04/09/2026 e o fusor de 39 features foi treinado em
   08/09/2026. **Não resolveu.** A feature funciona isoladamente — dispara na
   frase canônica e ganhou peso −0,193 no eixo satisfeito−insatisfeito, não
   nasceu morta —, mas uma feature binária com esse peso não vence as de texto
   (`texto_prob_satisfeito_media` pesa +2,78) quando o BERTimbau lê a frase como
   elogio sincero com 99% de confiança.

   O diagnóstico honesto é que **o problema não está no vetor, está na cabeça de
   texto**: nenhuma feature agregada de conversa reverte uma probabilidade
   saturada por mensagem. Reconhecer isso vale mais para a banca do que mais uma
   feature — é o limite do desenho, e ele está medido, não suposto. Reproduza com
   `uv run python scripts/conferir_fusor.py` (seção 5, frases-sonda).
1. **Retreinar a cabeça de ironia — dívida assumida, não mais bloqueio de
   confiabilidade, mas continua obrigatória para a API subir.** O vazamento
   está medido em `tests/test_ironia_dominio.py` (6 em 10 falas sinceras
   marcadas como irônicas) e o gerador já foi corrigido; falta rodar
   `notebooks/04_treino_ironia.ipynb` de novo. **A ironia NÃO entra mais no
   score desde 04/09/2026** (item 0 acima) — o vazamento não se propaga mais
   para a nota, mas a cabeça continua sendo lida por mensagem e exibida na
   dashboard, então retreiná-la continua valendo a pena para essa leitura ser
   confiável.
2. ~~**Retreinar o fusor no contrato de 35.**~~ **RESOLVIDO em 24/08/2026.** O
   contrato subiu para 35 em 21/08 e o artefato ficou para trás por três dias;
   `modelos/fusor.joblib` era de 16 features e a API real não subia. O
   `notebooks/02_treino_fusor.ipynb` rodou e o artefato novo bate as 35 chaves
   de `NOMES_FEATURES` na ordem.

   **O que veio junto, e é a parte que interessa:** a acurácia **caiu de 0,96
   para 0,93**, e isso é o resultado saudável, não uma piora. O fusor de 16
   features media um problema mais fácil; com dezenove features a mais, três
   delas vindas de uma cabeça de ironia com vazamento conhecido (item 1), um
   número menor é o esperado. A invariante 10 diz que acurácia alta demais é
   sintoma — 0,93 com os pesos liderados por texto e emoji é o perfil de um
   modelo que aprendeu, não de um que leu o relógio.

   A ressalva do item 1 continua valendo e agora está **assumida nos pesos**:
   este fusor foi treinado com a cabeça de ironia vazando, então retreinar a
   ironia obriga a retreinar o fusor de novo.
3. **Fixar a empresa fictícia** do trabalho — ela define volume, canais e o que
   conta como bom tempo de resposta na apresentação.
4. **Decisões em aberto** — tema claro para projetor de banca, pin do
   `scikit-learn` no `pyproject.toml`, e remover `content/fraus` da raiz.

Fora de escopo por decisão, não por falta de tempo: **k8s** (o deploy atual é
serverless e não justifica um orquestrador) e **login de usuário** na dashboard — o cookie da
autenticação é meio caminho, e dizer o contrário seria o mesmo tipo de mentira
que o projeto existe para não cometer.

## Limitações conhecidas

- **A API nasce fechada:** a primeira subida gera a mestra e a chave de acesso
  e as grava em `.fraus-chaves.txt`. Ela só fica aberta se alguém apagar a
  mestra do banco (`scripts/resetar_mestra.py`) ou se a escrita desse arquivo
  falhar — e nesse caso o boot avisa, porque ligar sem guardar a chave em lugar
  nenhum trancaria o dono para fora. A decisão
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
  assim que se liga a autenticação sem terminal. Como ela **não** nasce aberta,
  essa janela não é mais o primeiro uso: ela só existe nos dois casos acima
  (mestra apagada, ou escrita do arquivo falhada) — e nesses, **quem chegar
  primeiro** liga a autenticação e fica com a mestra. É a razão de o boot
  gritar quando sobe aberto: a janela é curta, mas é real enquanto durar.
  Depois de ligada, ela
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
- **As rotas do servidor Next que mudam estado recusam chamada de outro site.**
  O proxy escreve na API com a credencial do deploy, e `/api/fraus/iniciar`
  executa um comando: sem essa trava, qualquer página aberta noutra aba
  disparava as duas: o navegador bloqueia a *leitura* da resposta, nunca o
  *envio* do pedido. A decisão usa `Sec-Fetch-Site` (cabeçalho que o JS da
  página não consegue forjar), com `Origin` como reserva para navegador antigo.
  Requisição **sem** esses cabeçalhos passa — é `curl`/script, e um navegador
  não consegue omiti-los. `GET` não é afetado.
- **O corpo da requisição tem teto em duas camadas.** `Content-Length` acima de
  2 MB leva **413** no middleware, antes de qualquer parse — é a única trava
  que age antes de o corpo ser lido, porque quando o handler de
  `/analisar/arquivo` começa a rodar o multipart já foi lido e já escorreu para
  um temporário em disco. O teto da rota (200 kB) continua valendo e agora
  aborta a leitura no primeiro byte excedente, em vez de materializar o arquivo
  inteiro para recusá-lo na linha seguinte. Cliente que omite `Content-Length`
  (corpo `chunked`) escapa da primeira camada e é pego pela segunda.
- O NPS é **inferido do texto**, nunca perguntado ao cliente. A interface
  rotula como estimativa em todo lugar onde o número aparece.
- Série temporal, léxico por classe e tempo mediano de resposta saem agregados
  do servidor (`/serie-temporal`, `/lexico`, `/indicadores`), com recorte de
  período nas duas pontas inclusivas. **Nenhuma tela baixa transcrição no
  caminho feliz**: a Visão geral só as busca quando um desses agregados falha,
  como plano B, e a lista de atendimentos nunca as buscou — a ficha operacional
  de cada linha já vem derivada em `GET /conversas`. A agregação do servidor
  ainda varre as conversas do recorte em memória (uma consulta, não N), o que é
  o custo certo no volume do trabalho (dezenas de atendimentos).
- A atribuição por sentença sai de `GET /conversas/{id}/atribuicao`, que
  devolve a probabilidade **por mensagem** do classificador de texto — a
  transcrição marca a fala com o que o modelo achou dela, não só evidência
  observável. **Só a fala do cliente** recebe probabilidade: bot e humano vêm
  com os três campos nulos, porque as cabeças foram fine-tunadas em texto de
  cliente e pontuar o roteiro do bot seria número sem lastro. Se a leitura da
  atribuição falha, a transcrição aparece **sem marcação nenhuma** em vez de
  cair num plano B que pareceria a mesma coisa com outra régua.
- Latência **não é persistida**: é sempre derivada dos timestamps na leitura.
- Os cortes de latência da interface (10 s / 60 s / 180 s por padrão) são de
  **exibição** e saem de `GET /configuracoes`: eles movem onde a leitura chama
  a espera de imediata, saudável, longa ou crítica, e não mexem em nenhuma
  feature do modelo.
- A tela **Configurações** não reimplementa a validação: quando a faixa de NPS
  não cobre 0–10 de forma contígua, quem escreve a mensagem é a API, que nomeia
  a nota descoberta.
- **A categoria de NPS é uma composição, e a fronteira do neutro é apertada.**
  O peso do neutro (0,75) alinha as três classes às três categorias — ver
  *Indicadores* —, mas o alinhamento passa por `score → nota → faixa`, e a nota
  do neutro puro é `round(7,5)`, que dá **8** só porque o Python arredonda para
  o par mais próximo. Não há margem: com peso 0,65 seria `round(6,5) = 6`, de
  volta a detrator, pela mesma regra. A fronteira está fixada em teste
  (`tests/test_indicadores.py`) exatamente porque é frágil. Consequência
  prática: **mudar a faixa de NPS em Configurações pode desalinhar a classe
  neutra de novo** — a API valida que as faixas cubram 0–10 sem buraco, e não
  que a nota 8 continue caindo em neutro.
- **Mudar o peso do neutro exige repontuar o banco.** Ele é constante, não
  configuração, e o `score` é gravado na importação: um banco com conversas
  pontuadas antes e depois da mudança soma duas réguas no mesmo agregado, e
  nenhuma leitura consegue separá-las. O caminho é
  `POST /conversas/repontuar`, que existe desde o léxico curado e serve aos dois
  casos — ele repontua com o motor e o léxico vigentes, seja o que mudou o peso
  ou a curadoria. A mudança de 0,5 para 0,75 não precisou dele: o banco estava
  vazio quando ela foi feita.

  **O aviso de régua misturada, porém, só enxerga a versão do léxico.** A
  conversa grava com qual versão do léxico curado foi pontuada, e é isso que a
  contagem de `/indicadores` compara — o peso do neutro não é versionado, então
  mudá-lo mistura duas réguas **sem que nenhuma tela avise**. É a razão a mais
  para ele continuar constante e não virar botão.
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
- **A ironia de atendimento continua escapando do score, e agora ela é
  marcada.** A frase canônica — *"que atendimento maravilhoso, só esperei 3
  horas"* — sai como **promotor sempre que o relógio não a contradiz**. Nenhuma
  feature agregada de conversa reverte uma probabilidade saturada por mensagem:
  a `incongruencia_situacao_negativa` dispara nela e perde, com −0,193 contra
  os +2,78 de `texto_prob_satisfeito_media`.

  **Quanto a conversa pontua depende do relógio**, e isto foi medido em
  08/09/2026 contra a API real, com a mesma fala e só a latência variando:

  | latência | score | nota | categoria | contestada |
  |---:|---:|---:|---|---|
  | 10 s | 99,92 | 10 | promotor | — |
  | 179 s | 99,70 | 10 | promotor | — |
  | **181 s** | **99,69** | **10** | **promotor** | **SIM** |
  | **300 s** | **99,21** | **10** | **promotor** | **SIM** |
  | 600 s | 93,25 | 9 | promotor | — |
  | 1800 s | 17,19 | 2 | detrator | — |
  | 10800 s | 0,00 | 0 | detrator | — |

  Com as três horas **dentro do log**, o relógio já derruba o score sozinho. Os
  99,9 são o caso rápido — real e comum: o cliente abre um atendimento novo e
  ironiza sobre uma espera que aconteceu **fora** daquele log.

  Desde 08/09/2026 o atendimento na faixa do meio carrega uma **contestação**:
  quando o score passa de 95 **e** a latência mediana passa de 180 s (a faixa
  crítica de *From Seconds to Sentiments*, IJHCI 2025), a tela escreve "leitura
  contestada — elogio saturado contra espera de 5 min" ao lado da nota, e o CSV
  leva a coluna `contestada`. **A janela é estreita de propósito** — de ~3 a ~9
  minutos: abaixo disso não há contradição a marcar, e acima o modelo já acerta
  sem ajuda.

  **Ela marca, não corrige.** Score, nota e categoria seguem exibidos e o
  atendimento continua contando no NPS, no CSAT e na contenção. Tirar do
  agregado seria mais honesto no caso isolado e mais perigoso no conjunto — um
  limiar mal calibrado esvaziaria o indicador em silêncio.

  **Por que não virou a feature 40 do fusor.** O corpus não pode ensiná-la: o
  texto vem do B2W e a latência sai de distribuição por rótulo, então
  satisfeito-e-lento está rotulado *satisfeito* por construção, e a interação
  nasceria com peso **positivo** — o mesmo modo de falha que tirou
  `ironia_prob_*` do vetor em 04/09. Fica como trabalho futuro condicionado a
  corpus de atendimento real, a mesma condição que trava o retreino da cabeça
  de ironia. Base formal da abstenção: *The Art of Abstention* (ACL 2021); a
  **composição** dos dois sinais é desenho nosso, sem receita publicada, e está
  declarada assim em
  [docs/superpowers/specs/2026-09-08-abstencao-por-contestacao-design.md](docs/superpowers/specs/2026-09-08-abstencao-por-contestacao-design.md).

## Pendências

O que falta, em ordem de importância. Cada item diz o que existe hoje e o que
o desbloqueia.

### ~~Hospedar a API sem depender da máquina local~~ — RESOLVIDO em 17/09/2026

A limitação original era dupla: os checkpoints com PyTorch ultrapassavam o
tamanho padrão de função, e a Oracle não oferecia capacidade Ampere A1 na
região. A solução não foi reduzir a qualidade do classificador nem pagar uma
VPS: os três executores passaram para ONNX, os artefatos saíram do Git e são
baixados de um bucket privado no build, e a API ganhou um projeto Vercel
próprio com Large Functions.

O Supabase substitui o SQLite efêmero usando o transaction pooler na porta
`6543`. A dashboard continua na Vercel, mas fala com a API somente pelo proxy
server-side. Isto retira do roadmap as pendências **“conseguir VM Oracle”**,
**“manter API/túnel local ligado”**, **“escolher VPS paga”** e **“encontrar host
gratuito com RAM para PyTorch”**. Permanecem limites operacionais de cold start
e cota gratuita, documentados em [Limitações conhecidas](#limitações-conhecidas).

### 1. Retreinar a cabeça de ironia — vazamento de corpus MEDIDO, DÍVIDA ASSUMIDA

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

**Isto passou de pré-requisito a dívida assumida em 21/08/2026, e mudou de
natureza de novo em 04/09/2026.** Entre 21/08 e 03/09, o aviso deste item era
uma trava: "não treinar o fusor sobre uma cabeça de ironia que erra 6 em 10
injetaria o vazamento dela no score" — e por isso o item 2 ficava bloqueado
por este aqui. O contrato subiu mesmo assim, `ironia_*` entrou no vetor, e a
trava não foi respeitada: a ironia pontuou entre 21/08 e 03/09 com a cabeça que
erra 6 em 10. Em 04/09/2026, uma medição separada (ver
[docs/treinamento.md](docs/treinamento.md#a-ironia-sai-do-vetor-04092026))
mostrou que o problema da cabeça era ainda mais profundo do que o vazamento de
registro conversacional: no corpus de treino do fusor ela funciona como
detector de sentimento POSITIVO. **`ironia_prob_media` e `ironia_prob_max`
saíram do vetor por causa disso — a ironia não pontua mais**, e este item
passa a ser sobre a QUALIDADE da leitura por mensagem que a dashboard exibe,
não sobre o score.

### 2. ~~Retreinar o fusor no contrato vigente~~ — RESOLVIDO em 08/09/2026

**O artefato está em dia com o contrato de 39 features.** O histórico abaixo fica
como registro porque o mesmo descompasso aconteceu **quatro vezes** em três
semanas (16 → 35 → 40 → 38 → 39), e o padrão vale mais que qualquer episódio:
toda vez que uma feature entra ou sai de `NOMES_FEATURES`, o notebook 02 precisa
rodar de novo, e até rodar a API real não sobe.

São duas coisas distintas, e as duas estão feitas.

**O contrato subiu — feito em 21/08/2026.** O vetor é de **35 features**, das
sete famílias — texto, emoji, tempo, emoção, léxico, ironia e estilo. As
quatro últimas passaram a entrar no vetor quando os notebooks 03 e 04 ficaram
prontos; `sinais_fora_do_score` continua existindo no payload, mas vem vazio.
Isso é código: `montar_features`, `vetorizar` e `NOMES_FEATURES`.

**O fusor foi retreinado em 24/08/2026** e o descompasso acabou. Por três dias
o contrato foi de 35 e o artefato de 16, e nesse intervalo **a API real não
subia**: `Fusor.pontuar` chama `vetorizar`, que exige as 35 chaves de
`NOMES_FEATURES`, e o `StandardScaler` de 16 rejeitava o vetor
(`X has 35 features, but StandardScaler is expecting 16`).

Vale registrar que aquilo **era o comportamento correto**, não um bug: a
invariante 9 proíbe zero silencioso em feature faltante e a 7 manda tratar
modelo incompatível como falha alta e explícita. Servir predição com um fusor
que ignora dezenove features seria pior que estar fora do ar — e a falha
apareceu na carga, não em silêncio no meio de um relatório.

O artefato daquela época tinha `n_features_in_ = 35` e classes `[0 1 2]`
(insatisfeito, neutro, satisfeito — invariante 8). Verificado ponta a ponta
com os três BERTimbau carregados, sobre conversas do simulador: rótulo
insatisfeito pontua ~0, neutro ~73–75, satisfeito ~99, e as três categorias de
NPS saem certas. **Essa separação limpa não é evidência de qualidade**: são
conversas do próprio gerador sintético, e o número honesto continua sendo os
**0,93** do conjunto de teste separado.

**A dívida voltou em 03/09/2026 e foi fechada em 04/09/2026.** O contrato subiu
para **40 features** (a família `incongruencia_*` — ver [docs/treinamento.md](docs/treinamento.md#retreino-do-fusor-apos-as-features-de-incongruencia-03092026))
e por um dia o artefato em `modelos/` continuou sendo o de 35. O retreino
rodou: `n_features_in_ = 40`, classes `[0 1 2]`, **acurácia 0,947** e
**F1-macro 0,947** no conjunto de teste separado (900 treino / 300 teste),
contra 0,93 do fusor de 35. A subida de ~1,7 ponto é modesta de propósito —
salto grande seria sintoma de vazamento, não vitória.

`scripts/medir_faixas.py` com o artefato novo: insatisfeito 30/30 detrator
(mediana 0,14), neutro 29/30 neutro (mediana 74,97), satisfeito 27/30 promotor
(mediana 99,42), NPS −4,44 num lote equilibrado por construção. A régua
continua de pé.

**A dívida que essa história deixou, e o conserto — 04/09/2026.** O contrato
caiu de 40 para 38 features quando `ironia_prob_media` e `ironia_prob_max`
saíram de `NOMES_FEATURES` (ver
[docs/treinamento.md](docs/treinamento.md#a-ironia-sai-do-vetor-04092026)), e
pela terceira vez em três semanas o artefato ficou para trás do contrato. O que
tornava isso perigoso não era o desencontro em si — era que `Fusor.carregar`
era `joblib.load` puro, **sem validação de forma**: a API subia normalmente,
`/modelo/simular` funcionava e enganava (não passa pelo fusor), e o `ValueError`
do `StandardScaler` só estourava como HTTP 500 na primeira pontuação real. A
invariante 7 pede falha alta e explícita; o comportamento cumpria a metade
"explícita" e não a metade "na carga".

**Consertado:** `Fusor.carregar` compara `n_features_in_` com
`len(NOMES_FEATURES)` e levanta `FusorIncompativelError` nomeando os dois
números e apontando o notebook. Artefato desatualizado agora derruba a API na
subida. `vetorizar` também passou a recusar chave EXTRA, não só chave faltando.

O retreino com 38 features rodou no mesmo dia: **acurácia 0,943**, F1-macro
0,944, contra 0,947 do fusor de 40. A queda é o resultado saudável — as duas
features removidas estavam ajudando como detectores de sentimento positivo
disfarçados, e trocar uma feature que mente por nenhuma feature é o negócio
certo. Conferência completa em
[docs/treinamento.md](docs/treinamento.md#o-fusor-de-38-features--04092026),
reproduzível com `uv run python scripts/conferir_fusor.py`.

**O quarto e último capítulo — 39 features, 08/09/2026.** O contrato subiu para
39 em 04/09 com `incongruencia_situacao_negativa`, e pela quarta vez o artefato
ficou para trás. Desta vez a falha foi exatamente a que a invariante 7 pede:
`FusorIncompativelError` **na carga**, nomeando os dois números e apontando o
notebook — a API recusou subir por quatro dias, em vez de pontuar errado em
silêncio.

O retreino rodou: `n_features_in_ = 39`, classes `[0 1 2]`, **acurácia 0,950** e
**F1-macro 0,950** (900 treino / 300 teste), contra 0,943 do fusor de 38. A
subida de meio ponto é modesta, que é o esperado ao acrescentar uma feature
binária e esparsa — salto grande seria sintoma.

Três coisas que o laudo do `conferir_fusor.py` mostra e vale saber antes da
banca:

- **A feature nova não nasceu morta:** peso −0,193 no eixo satisfeito−insatisfeito,
  e nenhuma das 39 ficou com |peso| < 0,02. O risco da invariante 10 (feature
  constante no treino nasce com peso zero) não se concretizou — o catálogo de
  situação negativa cobre entrega e promessa não cumprida, que aparecem em
  review de produto.
- **E também não resolveu o que foi feita para resolver:** a frase canônica
  segue saindo promotor quando o relógio não a contradiz — 99,69 com 181 s de
  espera. Ver item 0 de [Falta](#falta).
- **Três features têm sinal contra-intuitivo, e a investigação fechou em
  08/09/2026** — `texto_prob_satisfeito_ultima` (−0,49, esperado positivo),
  `emoji_frac_positivos` (−0,19, esperado positivo) e `emoji_frac_negativos`
  (+0,59, esperado negativo). Não é regressão de retreino: os mesmos sinais
  estão no artefato de 38 (−0,50 / −0,18 / +0,60).

  **São correção de colinearidade, não erro de aprendizado.** Cada uma tem uma
  irmã forte que carrega o mesmo sinal com o sinal certo — `emoji_score_medio`
  (+1,55) e `texto_prob_satisfeito_media` (+2,78) —, e no corpus elas se movem
  praticamente juntas: `corr(score_medio, frac_positivos) = +0,94`,
  `corr(score_medio, frac_negativos) = −0,90`. Quando features dividem um efeito
  único, a mais forte fica com ele e a redundante recebe um peso pequeno de
  ajuste, com sinal frequentemente oposto — **o coeficiente individual deixa de
  significar "o efeito desta feature"**.

  O que importa é o efeito **líquido** da família, e ele aponta para o lado
  certo. Indo de 4 emojis negativos a 4 positivos, a contribuição somada das
  cinco features de emoji vai de **−0,06 para +1,93**; no texto, de
  P(satisfeito) 0,05 a 0,95, vai de **−2,23 para +4,56**.

  Reproduza com `uv run python scripts/investigar_sinais_invertidos.py`. O aviso
  de `conferir_fusor.py` **continua saindo de propósito**: a próxima inversão
  pode não ter esta explicação.

Existem dois corpora PT-BR reais de ironia, ambos sem download público — a tese de
[Vieira e Silva (USP, 2025)](https://teses.usp.br/teses/disponiveis/8/8139/tde-28082025-163511/publico/2025_AndressaVieiraESilva_VCorr.pdf),
com 1.186 exemplos anotados por três humanos, e o
[projeto IDPT/UFPel](https://institucional.ufpel.edu.br/projetos/id/u3345).
Qualquer um dos dois serve como **conjunto de teste independente**, o papel que
o XED-pt cumpre no notebook 03 — e é o que falta para a ironia ter uma métrica
que não seja otimista por construção. Detalhes de corpus, rótulo e limitação em
[docs/treinamento.md](docs/treinamento.md).

### 3. Definição da empresa

A spec ainda não fixa a empresa fictícia do trabalho, e ela atravessa a
apresentação inteira: define o volume plausível de atendimentos, os canais e o
que conta como bom tempo de resposta.

### 4. Decisões em aberto

- **Tema claro.** A dashboard é dark-only, herdado do chassi: `:root` e `.dark`
  recebem os mesmos valores em `globals.css` e o `layout.tsx` renderiza sempre
  com a classe `.dark`. Projetor de banca costuma lavar tema escuro, e adicionar
  depois é retrabalho.

Resolvidas: o **pin do `scikit-learn`** existe (`scikit-learn==1.6.1` no
`pyproject.toml` e no `Dockerfile`, que é a versão que serializou o
`fusor.joblib`; a venv local roda essa mesma), e **`content/fraus`** já saiu da
árvore.

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

O `app` real carrega o BERTimbau no primeiro uso do motor e **falha alto** se
`modelos/` não existir — por design. O `scripts/api_demo.py` existe para desenvolver a interface
sem esse custo: ele semeia um banco temporário com conversas do simulador,
incluindo atendimentos **sem fala do cliente** para exercitar o estado "sem
sinal".

```bash
uv run python scripts/api_demo.py   # http://127.0.0.1:8000
```

**Ele NÃO é sempre o dublê**, e essa é a parte que engana: desde que os três
BERTimbau e o fusor estão no disco, `montar_motor` carrega o **motor real** e só
cai no dublê quando falta artefato. A precedência é pela **presença dos
arquivos**, não por uma flag — flag desligada por engano voltaria ao dublê em
silêncio. `FRAUS_DEMO_DUBLE=1` força o dublê para quem quer iterar na interface
sem esperar o modelo carregar.

⚠️ **A armadilha, paga em 04/09/2026 e consertada:** os caminhos dos artefatos
eram relativos, logo resolvidos contra o **diretório de trabalho do processo**.
Um `uvicorn` lançado de fora da raiz não encontrava nenhum dos quatro, o
`api_demo` caía para o dublê sem nada quebrar, e a dashboard exibiu número
sintético com cara de predição por um dia inteiro — inclusive os pesos por
feature, que saíram numa progressão `0,2 / 0,25 / 0,3` e passaram por peso de
regressão. Hoje os artefatos ancoram na **raiz do projeto**, e `GET /saude`
**declara qual motor está servindo** (`motor: "real" | "duble"`), com a dúvida
caindo sempre para `duble`. A barra lateral escreve "motor dublê — números
sintéticos" em cor de aviso quando é o caso.

**Nunca use `scripts/api_demo.py` em produção**, nem quando ele está com o motor
real: o banco é temporário e semeado, e as conversas não são suas.

[^1]: [Conversation logs as a source of insight: predicting user satisfaction for customer service chatbots](https://link.springer.com/article/10.1007/s41233-025-00071-8) — Quality and User Experience, Springer, 2025.
[^2]: [Refining the prediction of user satisfaction on chat-based AI applications](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11793979/).
[^3]: [RAG vs Fine-Tuning 2026: A Decision Framework](https://winder.ai/rag-vs-fine-tuning-2026-decision-framework/).
[^4]: Cícero, *De Natura Deorum* III.17 — na enumeração da prole de Érebo e Nox aparecem *Amor, Dolus, Metus, Labor, Invidentia, Fatum, Senectus, Mors, Tenebrae, Miseria, Querella, Gratia,* **Fraus**, *Pertinacia*, as Parcas, as Hespérides e os Sonhos. **Correção de 25/08/2026:** esta nota creditava a Virgílio (*Eneida* VI, 273-281) a presença de Fraus no vestíbulo do Orco. Ela **não está** naquela lista — lá estão Luctus, Curae, Morbi, Senectus, Metus, Fames, Egestas, Letum, Labos, Sopor, Bellum, as Eumênides e Discórdia. Cícero é quem a nomeia, e dá a genealogia junto: irmã de *Dolus*, que é o nome antigo deste projeto nas specs.
