# Diferenciais — visão geral e Fase 0 (14/10/2026)

> Estado: **aguardando aprovação**. Nada abaixo foi implementado. Os specs por
> entrega são `2026-10-14-e1-...` a `2026-10-14-e6-...`, e o plano é
> `docs/superpowers/plans/2026-10-14-diferenciais.md`.

## Tese que as entregas defendem

1. **Sem LLM:** barato, rápido, determinístico e local.
2. **Explicação exata**, feita dos coeficientes, não gerada.
3. **Honestidade sobre incerteza:** calibração, abstenção e deriva.
4. **Conformidade por desenho:** nunca pontua atendente, roda em lote sobre
   conversa encerrada e não decide nada.

Sem o E4 (descartado em 14/10/2026), não há comparação numérica com LLM. A afirmação
sobre concorrentes (Intercom Fin CX Score, Zendesk QA, Observe.AI/Medallia,
Zenvia/Movidesk, Blip) vem de material de marketing de 14/10/2026 e **ainda
não foi reverificada**. Antes de entrar em documento ou slide, cada uma ganha
URL e data registradas em `docs/diferenciais/concorrentes.md`.

## Fatos registrados na Fase 0

**Conjunto de teste do fusor (o "900/300").** Ele não é guardado em lugar
nenhum: é reconstruído a cada vez. Notebook 02, células 5 e 7, e a cópia em
CPU em `scripts/retreinar_fusor_local.py:147-183`.

- **Fonte:** frases do B2W-Reviews01, baixadas por URL (`dados_brutos/` fica
  fora do git). As classes são balanceadas com `random_state=42`.
- **Divisão:** as frases [0:300) de cada classe vão para o treino e as
  [300:400) para o teste, então nenhuma frase aparece nos dois.
- **Montagem:** `gerar_lote(treino, 900, semente=20260813)` e
  `gerar_lote(teste, 300, semente=999)`.
- **Reprodutível?** Sim, tudo depende de semente. Os riscos residuais são a
  versão do pandas (ordem das linhas) e a diferença de float entre torch e
  ONNX. O cartão do modelo registra 0 de 180 categorias trocadas.
- `retreinar_fusor_local.py --cache` grava `{xt, yt, xe, ye}` em JSON. As
  entregas E2 (e o E4, antes de descartado) partem desse cache, **sem retreinar nada** (o script só
  grava o fusor com `--promover`, que não será usado).

**O que é gravado e o que é derivado.** A tabela `conversas`
(`fraus/db.py:57-65` mais a migração em `:686-692`) guarda `score`, uma
`categoria` que a leitura ignora, `payload` (a `Conversa` inteira em JSON),
`lexico_versao` e `regua`.

- **Não gravados:** probabilidades por classe, as 39 features e as
  contribuições.
- **Derivados na leitura** (`_com_derivacoes`, `conversas.py:283-302`): nota,
  categoria, latências, evidência fraca e contestação.
- **Contribuições:** são recalculadas rodando os modelos de novo em
  `GET /conversas/{id}/atribuicao`, que responde 409 se a régua ou a versão
  do léxico mudaram desde a pontuação.

**Contribuição por feature.** `Fusor.contribuicoes` (`fraus/fusor.py:313`)
calcula `(coef[2] − coef[0]) ⊙ z`, onde `z` é o vetor **depois** do `log1p`
das quatro features de espera e **depois** do `StandardScaler`. A escala está
certa.

- **Não é aditiva até a nota.** Σ contribuições + (b₂ − b₀) reproduz
  `log(P₂/P₀)` exatamente, mas o intercepto não é devolvido, a classe neutra
  fica de fora, e o score `100·(P₂ + 0,75·P₁)` não é linear.
- Isto é o que E1 corrige (ver o spec de E1).

**Atribuição por mensagem.** `Motor._atribuir` (`motor.py:284-335`) dá a cada
fala **do cliente** as probabilidades de satisfação, a emoção e a ironia (esta
última fora do score). Os pesos por palavra vêm de oclusão
(`fraus/sinais/palavras.py`).

- **Não existe** contribuição por mensagem para a nota do fusor.
- O que mais se aproxima é o Replay (`GET /operacao/replay/{id}`), que pontua
  cada prefixo sem ver falas futuras.

**Deriva.** `/saude/deriva` **não guarda faixa de treino** (mínimo e máximo).
Ela usa só a média e o desvio do scaler e marca uma feature como fora quando
`|z| > 4` (`LIMIAR_Z`). Nestes specs, "dentro da faixa de treino" significa
exatamente isso, e o texto de tela diz isso.

**Calibração.** O notebook `05_calibracao.ipynb` mede a temperatura e o ECE
das **três cabeças BERTimbau** e grava `modelos/calibracao.json`. O runtime
não lê esse arquivo.

- **Nada calibra nem mede o fusor**, que é de onde sai a nota. E2 cobre essa
  lacuna.

**Nota declarada.** Hoje só existe `Conversa.feedback_declarado ∈ {-1, 1}`,
um polegar, usado em `concordancia_com_feedback`. Não há campo para nota de
0 a 10 nem para CSAT.

**LLM.** Nada no repositório usa LLM. Não existem `scripts/benchmark/` nem
`precos.toml`.

## Baseline — 14/10/2026, branch criado de `main` em `cdaa9e2`

| comando | resultado |
|---|---|
| `uv run pytest -q` | **1395 passed, 7 skipped, 1 deselected** (159 s) |
| `scripts/conferir_fusor.py` | **falha pré-existente de ambiente:** `modelos/importancias.json` não existe |
| `scripts/medir_faixas.py` | **falha pré-existente de ambiente:** `ModeloAusenteError` (`modelos/bertimbau-satisfacao`) |
| `npm ci && npm test` | 351 passed (42 arquivos) |
| `npx tsc --noEmit` / `npm run build` | ok / ok |
| OpenAPI (`criar_app` com banco temporário) | **76 caminhos**, salvos como referência fora do repositório |
| pacote da API | **não medido localmente** sem o bundle; vale o documentado: ~1,95 GB, deploy de 30/09/2026 |

As duas falhas têm a mesma causa: **os pesos não estão nesta máquina**.
`modelos/` só tem `comparacao_modelos.json` e `metricas_laya.json`, e também
faltam `fusor.joblib`, `bertimbau-*` e `modelos-onnx/`.

## Bloqueios e decisões que dependem do João

1. **Pesos locais (bloqueia as medições de E1, E2 e E6).** O bundle sai
   do Oracle por `FRAUS_MODELOS_URL` + `FRAUS_MODELOS_SHA256`, ou do Drive.
   Baixá-lo é leitura, mas a regra 9 proíbe tocar no Oracle. Preciso que o
   João me entregue o ZIP ou autorize o download.
2. **Drivers agregados (E1)** exigem contribuições de muitas conversas. As
   features não são gravadas, então há duas saídas: recalcular sob demanda
   numa amostra com teto, ou gravá-las (schema, regra 5). Recomendação:
   amostra com teto, sem schema.
3. **Abstenção na lista (E2)** exige alguma coisa por conversa sem rodar os
   modelos. Recomendação: conformal sobre o **score gravado**, sem schema
   (ver E2).
4. **Nota declarada (E3)** é schema novo, mesmo que entre só no `payload`
   JSON. Precisa de aprovação.
5. **Benchmark (E4): descartado pelo João em 14/10/2026.**
6. **Sinalizadores (E5):** quem anota a amostra à mão, e com qual material. O
   repositório não tem conversa real.

## Limites que valem para todas as entregas

- Nenhuma entrega altera `score`, nota ou categoria gravados.
- Nenhuma toca `modelos/`, `modelos-onnx/`, `NOMES_FEATURES`,
  `PESO_NEUTRO_NO_SCORE`, `FEATURES_EM_LOG` ou a cabeça de ironia.
- Nenhuma roda ao vivo durante o atendimento, e nenhuma saída aciona ação.
- Nenhuma julga o atendente humano.
- Toda métrica nova declara o conjunto usado e que o tempo do fusor é
  **sintético**.
