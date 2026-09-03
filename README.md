<p align="center">
  <img src="docs/assets/fraus-logo.svg" alt="Fraus" width="140">
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

Sinais independentes, calculados sobre um modelo canônico de conversa e fundidos
por um classificador leve:

| Sinal | O que mede | Por quê |
|---|---|---|
| **Texto** | BERTimbau fine-tunado, probabilidade **por mensagem** | permite apontar *quais trechos* puxaram a nota |
| **Emoji** | polaridade e **posição relativa** na mensagem | a polaridade do emoji cresce perto do fim da frase |
| **Tempo** | latência, escalação, abandono | o efeito é não-linear — o peso é aprendido, não arbitrado |
| **Emoção** | as 7 emoções humanas, por mensagem | requisito de banca; a nota diz *quanto*, a emoção diz *o quê* |
| **Léxico** | SentiLex-PT02 com escopo de **negação**, mais o [léxico curado](#léxico-curado) | polaridade de procedência independente do BERTimbau |
| **Ironia** ⚠️ | cabeça binária sobre o IDPT 2021 | texto positivo com sentido negativo derruba a leitura dos outros sinais |
| **Estilo** | caixa alta, pontuação, alongamento, palavrão, censura | a forma de escrever carrega afeto que a palavra sozinha não carrega |
| **Incongruência** | polaridade emoji×texto, marcador de contraste, hipérbole, aspas irônicas | texto e emoji discordando é o formato clássico da ironia |

As oito famílias somam **40 features** (as cinco de `incongruencia_*` entraram
em 03/09/2026) e todas entram no vetor desde 21/08/2026 — ver [contrato de
features](docs/treinamento.md#contrato-de-features).

⚠️ *a cabeça de ironia tem vazamento de corpus medido e pontua assim mesmo — é
dívida assumida, não pendência de integração; ver [pendência 1](#1-retreinar-a-cabeça-de-ironia--vazamento-de-corpus-medido-dívida-assumida).*

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
os três BERTimbau de novo por conversa — o vetor é de 40 features e o fusor exige
as 40, então não existe recalcular só as três léxicas e as cinco de emoji. Em
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
uv run python -m uvicorn fraus.api.main:app --reload   # http://127.0.0.1:8000
```

> `python -m uvicorn`, e não `uv run uvicorn`: o segundo passa pelo trampolim
> que o `uv` instala para o `uvicorn.exe` do `.venv`, e ele quebra com
> `uv trampoline failed to canonicalize script path` se o venv foi recriado ou
> movido. Chamar o módulo pelo interpretador não depende de shim nenhum.

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
| `FRAUS_CAMINHO_CHAVES` | `.fraus-chaves.txt` | onde a **primeira subida** grava a mestra e a chave de acesso que ela gera. Única cópia em claro delas; fora do git, e criado com permissão **`0600`** — só o dono lê (em POSIX; no Windows quem manda é a ACL herdada da pasta) |
| `FRAUS_CHAVE_MESTRA` | (nenhum) | a mestra vinda do ambiente. Definida, ela é a **única** mestra: a gravada no banco **deixa de valer** enquanto a variável existir (ver *Precedência*, abaixo). Sem ela e sem mestra no banco, a API é aberta (uso local), com aviso no boot. Com qualquer uma das duas, toda rota exige `Authorization: Bearer` — a mestra, uma chave de acesso ou um **token de sessão** — exceto `POST /ingestao` (chave de fonte), o webhook (assinatura própria) e as públicas (`/saude`, `/acesso/estado`, `/auth/estado`, `/auth/registrar`, `/auth/entrar`) |
| `FRAUS_JWT_SEGREDO` | (nenhum) | assina o **JWT de sessão** do login de usuário (`POST /auth/entrar`). Sem ela, o login responde 503 dizendo o que falta, `/auth/estado` anuncia `disponivel: false` e a dashboard abre **sem exigir login** — o modo aberto local, mesmo contrato da API sem mestra |
| `FRAUS_CODIGO_DEV` | (nenhum) | o código de convite que permite um cadastro nascer com papel **`dev`** (administra Integrações, Modelo, Configurações, importação e léxico). Sem ela, nenhum cadastro nasce dev — todo mundo nasce `usuario` (analista: Visão geral e Atendimentos). Código errado é 403 explícito, nunca rebaixamento silencioso |

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
`GET /saude` responde (30 a 60 s, o tempo de carregar os três BERTimbau).

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

### 6. Publicando a dashboard com a API na sua máquina (túnel)

Para **demonstrar** a dashboard publicada (Vercel) falando com a API de verdade,
sem hospedar a API em lugar nenhum: um túnel dá um endereço `https` público
temporário para o `uvicorn` que roda no seu computador.

**Por que não hospedar a API junto da dashboard:** a Vercel é serverless, e só o
`torch` ocupa 497 MB instalado contra o teto de 250 MB de uma função — os três
BERTimbau somam mais 1,25 GB, e cada requisição roda inferência em CPU. O
Hugging Face Spaces resolveria o tamanho, mas Docker Space exige assinatura PRO
(`402 Payment Required` no plano gratuito); o tier gratuito do Render dá 512 MB
de RAM, e os três modelos carregados não cabem. Hospedar de verdade pede um
container com ~2 GB de RAM e disco — ver [docs/hospedagem.md](docs/hospedagem.md).

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

### Entregue

| Frente | Estado | O que existe |
|---|---|---|
| **Modelo canônico e sinais** | ✅ | `Conversa`/`Mensagem`, as oito famílias de sinal (texto, emoji, tempo, emoção, léxico, ironia, estilo e incongruência), e o score 0–100 → nota 0–10 → categoria de NPS |
| **Três cabeças treinadas** | ✅ ⚠️ | satisfação, emoção (7 classes) e ironia no ar; a de **ironia não é confiável** — ver pendência 1 |
| **Fusor** | ⚠️ | contrato e artefato **voltaram a divergir em 03/09/2026**: `NOMES_FEATURES` subiu de 35 para 40 (família `incongruencia_*`), e `modelos/fusor.joblib` continua sendo o artefato de 35 treinado em 24/08/2026 — `n_features_in_ = 35`. **`Fusor.carregar` é `joblib.load` puro, sem validação de forma — a API real SOBE normalmente com esse artefato desatualizado**, e `/modelo/simular` também funciona (não usa o fusor), o que engana quem está testando à mão. O `ValueError` do `StandardScaler` só aparece como 500 na primeira pontuação de verdade, em `/ingestao` ou `/conversas/importar` — é risco de demonstração ao vivo, não uma trava que impede o servidor de subir. Ver invariante 7 (a intenção é falha alta e explícita; o código hoje não garante isso na carga, só na primeira predição). Corrige quando o retreino descrito em [docs/treinamento.md](docs/treinamento.md#retreino-do-fusor-apos-as-features-de-incongruencia-03092026) rodar de novo no Colab |
| **Ingestão** | ✅ | CSV de `dados_brutos/` (com contenção de caminho) e `POST /ingestao` pela rede, por chave de fonte |
| **API modular** | ✅ | `main.py` só monta o app; um router por domínio, `Contexto` por injeção. O contrato HTTP foi verificado **byte a byte** no OpenAPI contra a versão anterior |
| **Autenticação** | ✅ | mestra + chaves de acesso (`fra_`) + chaves de fonte (`frs_`), decisão **por requisição**, hash no banco, revogação na hora |
| **Nasce fechada** | ✅ | a primeira subida gera mestra e chave de acesso, grava em `.fraus-chaves.txt` e a dashboard lê de lá — sem clique e sem cópia |
| **Ligar a autenticação sem terminal** | ✅ | botão em Configurações, para instalação antiga ou reaberta; a mestra sobrevive a reiniciar |
| **Gerenciar chaves sem terminal** | ✅ | painel que emite, lista e revoga chaves de acesso, pedindo a mestra; e `scripts/resetar_mestra.py` para quando ela se perde |
| **Dashboard sem terminal** | ✅ | **Iniciar API** (sem abrir janela de console) e **Desligar**, este último só para a API que a própria dashboard subiu — travas em [§5](#5-quando-a-api-não-está-no-ar) |
| **Diagnóstico honesto** | ✅ | régua de estado quando a API não responde; `/saude` fora da credencial; estado vazio nunca afirma "não há atendimento" quando a causa é conexão |
| **Agregação no servidor (fim do N+1)** | ✅ | `/serie-temporal`, `/lexico`, `/indicadores` (com tempo mediano) e o recorte `de`/`ate` em `/conversas`; **nenhuma tela baixa transcrição** no caminho feliz |
| **Origem das escritas** | ✅ | as rotas do servidor Next que mudam estado recusam **403** o que vem de outro site (`Sec-Fetch-Site`, com `Origin` de reserva) |
| **Teto de corpo** | ✅ | **413** por `Content-Length` antes de qualquer parse, e o upload de `/analisar` lido em pedaços com abort no primeiro byte excedente |
| **Léxico curado** | ✅ | o que o analista ensina por cima do SentiLex e do ranking de emoji de 2015: cadastro, edição e revogação por rota e por painel; a curadoria **vence** o léxico base e atravessa até o score. Cada escrita versiona, a conversa grava com qual versão foi pontuada, a Visão geral **nomeia** a régua misturada e `POST /conversas/repontuar` a zera |
| **Suíte** | ✅ | **481 testes** de Python passando, build da dashboard verde, contraste AA verificado por `npm run contraste`. O front ganhou runner próprio em 25/08 (`cd dashboard && npm test`, vitest) — a primeira lógica **comportamental** dele, o contador do easter egg da marca, é testada; renderização continua coberta por build e contraste |

### Falta

Em ordem, com o detalhe em [Pendências](#pendências):

1. **Retreinar a cabeça de ironia — dívida assumida, não mais bloqueio.** O
   vazamento está medido em `tests/test_ironia_dominio.py` (6 em 10 falas
   sinceras marcadas como irônicas) e o gerador já foi corrigido; falta rodar
   `notebooks/04_treino_ironia.ipynb` de novo. **A ironia já entra no score**
   desde o item 2 — o aviso antigo ("não treinar o fusor sobre uma cabeça que
   erra 6 em 10") deixou de valer como trava e passou a descrever o que
   acontece hoje: o score carrega esse vazamento até este notebook rodar de
   novo.
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

Fora de escopo por decisão, não por falta de tempo: **deploy e k8s** (o destino
é a máquina local e a banca) e **login de usuário** na dashboard — o cookie da
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

## Pendências

O que falta, em ordem de importância. Cada item diz o que existe hoje e o que
o desbloqueia.

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

**Isto passou de pré-requisito a dívida assumida em 21/08/2026.** Antes do
contrato de 35 features, o aviso deste item era uma trava: "não treinar o
fusor sobre uma cabeça de ironia que erra 6 em 10 injetaria o vazamento dela
no score" — e por isso o item 2 ficava bloqueado por este aqui. O contrato
subiu mesmo assim, `ironia_*` entrou no vetor, e a trava não foi respeitada:
**a ironia pontua hoje com a cabeça que erra 6 em 10**, então o score de todo
atendimento carrega esse vazamento até este notebook rodar de novo. Não é um
risco resolvido nem neutro — é um risco que já está dentro do número que a
tela mostra.

### 2. Retreinar o fusor no contrato vigente (agora 40, era 35)

São duas coisas distintas, e só uma está feita.

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

**Isto voltou a ser dívida em 03/09/2026.** O contrato subiu de novo, para
**40 features** (a família `incongruencia_*` — ver [docs/treinamento.md](docs/treinamento.md#retreino-do-fusor-apos-as-features-de-incongruencia-03092026)),
e o artefato em `modelos/` **continua sendo o de 35** treinado em 24/08/2026.
Eles não batem agora: `n_features_in_` do artefato vigente é 35,
`len(NOMES_FEATURES)` é 40.

**Isso NÃO impede a API de subir.** Diferente do episódio de 24/08/2026
descrito acima — onde o vetor era exigido na carga —, `Fusor.carregar` (em
`fraus/fusor.py`) é `joblib.load` puro, sem nenhuma validação de forma contra
`NOMES_FEATURES`. Medido: `Fusor.carregar("modelos/fusor.joblib")` carrega
sem erro mesmo com `n_features_in_ = 35` contra um contrato de 40. A API sobe
normalmente, e `/modelo/simular` funciona e engana — essa rota não passa pelo
fusor. **O `ValueError` do `StandardScaler` só estoura como HTTP 500 na
primeira pontuação real**, em `/ingestao` ou em `/conversas/importar`, quando
`vetorizar` monta um vetor de 40 posições e o scaler treinado para 35 rejeita.
Isto é risco de demonstração ao vivo: um teste manual rápido pela API de
simulação, ou só o servidor subir sem erro no log, pode convencer quem está
validando de que está tudo certo quando não está. A invariante 7 pede falha
alta e explícita para modelo ausente/incompatível; o comportamento atual
cumpre a metade "explícita" (o 500 é claro) mas não a metade "na carga" — a
falha só aparece quando alguém tenta pontuar de verdade. Isto não é
histórico — é o estado atual, até o retreino acontecer.

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

O `app` real carrega o BERTimbau do disco e **falha alto** se `modelos/` não
existir — por design. Enquanto o treino do Colab não roda, a dashboard é
desenvolvida contra um servidor de demonstração que usa um motor dublê
(pontuação determinística derivada do texto, sem modelo nenhum) e semeia um
banco temporário com conversas do simulador, incluindo atendimentos **sem fala
do cliente** para exercitar o estado "sem sinal":

```bash
uv run python scripts/api_demo.py   # http://127.0.0.1:8000
```

**Nunca use `scripts/api_demo.py` em produção.** Os números que ele devolve não
são predição de modelo.

[^1]: [Conversation logs as a source of insight: predicting user satisfaction for customer service chatbots](https://link.springer.com/article/10.1007/s41233-025-00071-8) — Quality and User Experience, Springer, 2025.
[^2]: [Refining the prediction of user satisfaction on chat-based AI applications](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11793979/).
[^3]: [RAG vs Fine-Tuning 2026: A Decision Framework](https://winder.ai/rag-vs-fine-tuning-2026-decision-framework/).
[^4]: Cícero, *De Natura Deorum* III.17 — na enumeração da prole de Érebo e Nox aparecem *Amor, Dolus, Metus, Labor, Invidentia, Fatum, Senectus, Mors, Tenebrae, Miseria, Querella, Gratia,* **Fraus**, *Pertinacia*, as Parcas, as Hespérides e os Sonhos. **Correção de 25/08/2026:** esta nota creditava a Virgílio (*Eneida* VI, 273-281) a presença de Fraus no vestíbulo do Orco. Ela **não está** naquela lista — lá estão Luctus, Curae, Morbi, Senectus, Metus, Fames, Egestas, Letum, Labos, Sopor, Bellum, as Eumênides e Discórdia. Cícero é quem a nomeia, e dá a genealogia junto: irmã de *Dolus*, que é o nome antigo deste projeto nas specs.
