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

A dashboard fala com a API pelo endereço de `NEXT_PUBLIC_API_URL`
(padrão `http://localhost:8000`):

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Como é uma variável `NEXT_PUBLIC_*`, ela é lida **em tempo de build/boot** —
mudar depois exige reiniciar o processo.

## Limitações conhecidas

- **A API não tem autenticação e é destinada a uso local.** Não há login nem
  token: quem alcança a porta lê tudo e importa qualquer arquivo dentro da raiz
  de importação. Não exponha na internet. A raiz configurável
  (`FRAUS_RAIZ_IMPORTACAO`) limita o estrago, não substitui autenticação.
  As origens liberadas para o navegador são uma **lista explícita**
  (`FRAUS_ORIGENS`, padrão `localhost`/`127.0.0.1` nas portas 3000 e 3001) e
  nunca `*` — sem autenticação, `*` deixaria qualquer página aberta no mesmo
  navegador varrer as conversas.
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

### 1. Treinar o modelo — bloqueia tudo o que é "IA de verdade"

Enquanto os artefatos não existirem, o que roda é o **motor dublê** do servidor
de demonstração: pontuação determinística derivada do texto, sem modelo nenhum.
A interface é honesta sobre isso — a tela **Modelo** mostra as métricas de
treino em estado vazio em vez de inventar número — mas nada do que ela exibe é
predição.

Para destravar: rodar `notebooks/01_treino_bertimbau.ipynb` e depois
`notebooks/02_treino_fusor.ipynb` no Colab, e colocar em `modelos/` a pasta
`bertimbau-satisfacao/`, o `fusor.joblib` e o `metricas.json`. Aí
`uvicorn fraus.api.main:app` sobe com o motor real.

### 2. Notebooks 03 e 04 — as 7 emoções e a ironia

Requisito de banca ainda não entregue. Os módulos `fraus/sinais/emocao.py`,
`fraus/sinais/lexico.py` e `fraus/sinais/ironia.py` existem e estão cobertos por
testes, e os notebooks `03_treino_emocao.ipynb` e `04_treino_ironia.ipynb` estão
escritos — falta **rodar**. As features só entram no vetor do fusor depois que os
modelos existirem: expandir `NOMES_FEATURES` antes disso quebraria o notebook 02
e a API sem nada em troca.

**O notebook 03 roda hoje** — o `go_emotions_ptbr` é público. **O 04 depende de
liberação:** o corpus IDPT 2021 não tem download aberto e precisa ser solicitado
aos [organizadores](https://sites.google.com/inf.ufpel.edu.br/idpt2021/). Se não
sair a tempo, a saída honesta é declarar a ironia como trabalho futuro — trocar
por sarcasmo em inglês traduzido repetiria o vazamento de procedência que já
custou o primeiro fusor.

Depois dos dois: subir o contrato de 16 para 30 features e **retreinar o fusor**.
Detalhes de corpus, rótulo e limitação em
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

### 4. Atribuição por sentença do classificador

O endpoint de atribuição existe, mas a transcrição só marca evidência
**observável** (polaridade de emoji e tempo de espera). A contribuição do sinal
de texto por sentença depende do modelo treinado — cai junto com a pendência 1.

### 5. Definição da empresa

A spec ainda não fixa a empresa fictícia do trabalho, e ela atravessa a
apresentação inteira: define o volume plausível de atendimentos, os canais e o
que conta como bom tempo de resposta.

### 6. Decisões em aberto

- **Tema claro.** A dashboard é dark-only, herdado do chassi. Projetor de banca
  costuma lavar tema escuro, e adicionar depois é retrabalho.
- **Merge da branch.** `feat/motor-e-dashboard` está no PR #1, ainda não
  integrada em `main`.

## Desenvolvimento

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
