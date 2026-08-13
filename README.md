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
Ápate/Dolos, postada por Virgílio à entrada do Inferno ao lado do Medo e da
Discórdia (*Eneida*, VI)[^4] — lê o que foi dito de verdade.

## Como funciona

Três sinais independentes, calculados sobre um modelo canônico de conversa e
fundidos por um classificador leve:

| Sinal | O que mede | Por quê |
|---|---|---|
| **Texto** | BERTimbau fine-tunado, probabilidade **por mensagem** | permite apontar *quais trechos* puxaram a nota |
| **Emoji** | polaridade e **posição relativa** na mensagem | a polaridade do emoji cresce perto do fim da frase |
| **Tempo** | latência, escalação, abandono | o efeito é não-linear — o peso é aprendido, não arbitrado |

O resultado é um score de 0 a 100 por atendimento, que vira nota 0–10 e categoria
de NPS (**0–6 detrator · 7–8 neutro · 9–10 promotor**), agregado numa dashboard.

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
- [Treinamento](docs/treinamento.md) — os dois notebooks do Colab (BERTimbau e fusor) e os artefatos que eles produzem

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
- Não há endpoint de série temporal nem de latência agregada: a dashboard
  deriva as duas das transcrições, o que custa um N+1 aceitável no volume do
  trabalho (dezenas de atendimentos).
- A atribuição por sentença do classificador de texto não tem endpoint, então a
  transcrição marca só evidência **observável** (polaridade de emoji e tempo de
  espera) — e diz isso em voz alta em vez de fingir atribuição.
- Latência **não é persistida**: é sempre derivada dos timestamps na leitura.

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

### 2. Telas de Integrações e Configurações

Não existem, e não foram construídas de propósito: dependem de endpoints que a
API ainda não tem. Precisam, no mínimo, de persistência de configuração
(faixas de NPS, limiares de latência, quais sinais estão ativos) e de um
cadastro de fonte de conversa. Credencial de plataforma **não** deve ir para o
SQLite em texto puro — a decisão de onde guardar ainda está em aberto.

### 3. `GET /serie-temporal` — a dívida de escala

A Visão geral monta o gráfico de NPS × latência baixando **todas** as
transcrições do recorte para ler timestamps. É um N+1 aceitável em dezenas de
atendimentos e insustentável em milhares. Os primos `GET /conversas?de=&ate=` e
`GET /indicadores?de=&ate=` tirariam o filtro de período do cliente.

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
