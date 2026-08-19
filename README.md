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
uv run python -m uvicorn fraus.api.main:app --reload   # http://localhost:8000
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
| `FRAUS_CAMINHO_CHAVES` | `.fraus-chaves.txt` | onde a **primeira subida** grava a mestra e a chave de acesso que ela gera. Única cópia em claro delas; fora do git |
| `FRAUS_CHAVE_MESTRA` | (nenhum) | a mestra vinda do ambiente, que **vence** a gravada. Sem ela e sem mestra no banco, a API é aberta (uso local), com aviso no boot. Com qualquer uma das duas, toda rota exige `Authorization: Bearer` — a mestra ou uma chave de acesso — exceto `POST /ingestao` (chave de fonte) e `GET /acesso/estado` (pública) |

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
curl -X POST localhost:8000/conversas/importar \
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
curl -X POST localhost:8000/ingestao \
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

Invoke-RestMethod -Uri http://localhost:8000/ingestao -Method Post `
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

## Roadmap

Onde o trabalho está. **Entregue** é o que existe no repositório e tem teste ou
verificação por trás; **falta** está detalhado em [Pendências](#pendências), e a
ordem lá é a ordem de importância.

### Entregue

| Frente | Estado | O que existe |
|---|---|---|
| **Modelo canônico e sinais** | ✅ | `Conversa`/`Mensagem`, sinais de texto, emoji e tempo, e o score 0–100 → nota 0–10 → categoria de NPS |
| **Três cabeças treinadas** | ✅ ⚠️ | satisfação, emoção (7 classes) e ironia no ar; a de **ironia não é confiável** — ver pendência 1 |
| **Fusor** | ✅ ⚠️ | 16 features (texto, emoji, tempo); emoção e ironia ficam **fora do score**, marcadas em `sinais_fora_do_score` |
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
| **Suíte** | ✅ | **350 testes** passando, build da dashboard verde, contraste AA verificado por `npm run contraste` |

### Falta

Em ordem, com o detalhe em [Pendências](#pendências):

1. **Retreinar a cabeça de ironia** — o vazamento está medido em
   `tests/test_ironia_dominio.py` e o gerador já foi corrigido; falta rodar
   `notebooks/04_treino_ironia.ipynb` de novo. **Bloqueia o item 2.**
2. **Subir o fusor de 16 para 30 features**, colocando emoção e ironia na nota.
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
uv run python scripts/api_demo.py   # http://localhost:8000
```

**Nunca use `scripts/api_demo.py` em produção.** Os números que ele devolve não
são predição de modelo.

[^1]: [Conversation logs as a source of insight: predicting user satisfaction for customer service chatbots](https://link.springer.com/article/10.1007/s41233-025-00071-8) — Quality and User Experience, Springer, 2025.
[^2]: [Refining the prediction of user satisfaction on chat-based AI applications](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11793979/).
[^3]: [RAG vs Fine-Tuning 2026: A Decision Framework](https://winder.ai/rag-vs-fine-tuning-2026-decision-framework/).
[^4]: Virgílio, *Eneida*, Livro VI, v. 273-281 — Fraus (Fraude/Engano) personificada no vestíbulo do Orco, ao lado de Luto, Curae, Morbi, Senectus e Metus.
