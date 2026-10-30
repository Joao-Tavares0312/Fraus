# Diferenciais — relatório de entrega (14/10/2026)

Este relatório fecha a missão "diferenciais do Fraus, ancorados em concorrentes reais e medidos". Para cada entrega, diz:

- o que entrou;
- o que foi medido;
- o que **não foi verificado**, e por quê;
- como reproduzir.

Nenhum número aqui foi estimado à mão. Onde não houve medição, está escrito "não verificado" e o script já está pronto para rodar.

## Resumo

| entrega | estado | medição real |
|---|---|---|
| E1 — por que esta nota, contrafactual e drivers | entregue | aditividade exata provada no fusor sintético; **no fusor real: não verificado** |
| E2 — calibração, abstenção e conjunto conformal | entregue | **não verificado** (artefato conformal não gerado) |
| E3 — declarado × inferido | **não iniciado**: exige schema novo (`nota_declarada`), ainda não aprovado | — |
| E4 — benchmark contra LLM | **descartado** em 14/10/2026 | — |
| E5 — sinalizadores por regra | entregue | casos construídos e taxa de disparo no simulador; **precisão e recall em dado real: não verificado** |
| E6 — impacto por tema e início da deterioração | entregue | **não verificado** no fusor real; o lead time do simulador é artefato do gerador |

**Por que tanta coisa "não verificado".** A máquina de desenvolvimento não tem o `fusor.joblib` treinado em `log1p`. O artefato que estava disponível foi treinado em segundos crus, e `Fusor.carregar` o recusa de propósito (invariante 10). Sem esse fusor:

- nenhuma métrica que dependa da nota real pôde ser medida;
- cada instrumento falha alto, sem motor dublê (invariante 7).

Assim que o fusor estiver em `modelos/`, os comandos da seção [Reproduzir](#reproduzir) produzem os números.

## O que vale para todas as entregas

- **Sem LLM em runtime.** Toda explicação é feita dos coeficientes ou por template, e nenhuma chamada de rede entra no caminho de predição.
- **Nada novo é gravado.** O `score`, a nota e a categoria gravados não mudam. Nenhuma coluna, tabela ou chave de payload foi criada. Tudo é derivado na leitura.
- **Nenhuma régua nova.** Nada retreina o modelo, e ficaram intocados:
  - `modelos/`;
  - `NOMES_FEATURES` (39);
  - `PESO_NEUTRO_NO_SCORE` (0,75);
  - `FEATURES_EM_LOG`;
  - a cabeça de ironia.
- **Ausência não vira zero.** Conversa sem sinal, n abaixo do mínimo ou campo ausente numa API antiga aparecem nomeados, nunca como 0.
- **Conformidade.**
  - Nada pontua atendente.
  - Tudo roda em lote, sobre conversa encerrada; nada alerta ao vivo.
  - Nada decide sozinho: as marcas (abstenção, sinalizadores, deterioração) informam e não mudam a nota. O atendimento continua no NPS.
- **O sinal de tempo do fusor é sintético**, e toda métrica nova declara isso.

## E1 — "Por que esta nota", contrafactual de espera e drivers

**O que entrou.**

- **Decomposição exata do fusor** (`Fusor.decompor`). O intercepto mais as contribuições é igual ao log da razão contra a classe de referência, e o score é refeito a partir dos logits.
- **Efeito por família em pontos de score.** É um recálculo exato, mas **não é aditivo**, e a tela diz isso.
- **Frases por template** em `fraus/explicacao.py`, sem LLM. A explicação vem dentro de `GET /conversas/{id}/atribuicao`.
- **`POST /conversas/{id}/contrafactual`**, que testa a primeira resposta ou um teto de espera. Ele recusa com 422 quando a conversa sai da faixa de treino (`|z| > 4`).
- **`GET /indicadores/drivers`**, sobre uma amostra por semente (50, com teto de 200). Mostra a média por família em detratores e em promotores, com IC por bootstrap, e o rótulo "associação no modelo, não causa".
- **Duas telas:** um bloco na transcrição e um painel sob demanda na Visão geral.

**Medido.** No fusor sintético dos testes, a aditividade fecha com erro menor que 1e-9.

**Não verificado.** A aditividade e o tempo no fusor real. O script `scripts/medir_aditividade.py` está pronto.

## E2 — Calibração, abstenção e conjunto conformal

**O que entrou.**

- **Conjunto conformal Mondrian (por classe) sobre o score gravado** (`fraus/conformal.py`). Para cada nota, diz quais classes de satisfação são compatíveis com ela, com cobertura-alvo de 90% por classe. O artefato `fraus/dados/conformal_fusor.json` é chaveado pela régua.
- **Falha explícita sem artefato.** Se o artefato estiver ausente, inválido ou for de outra régua, as rotas respondem 503 ou 409 com o motivo. Nunca devolvem um conjunto vazio fingindo confiança.
- **Abstenção** ("leitura sem confiança suficiente"):
  - dispara quando o conjunto não tem exatamente uma classe ou, no detalhe, quando há deriva;
  - informa e não corrige.
- **Rotas:**
  - `GET /conversas/{id}/confianca`;
  - `GET /indicadores/confianca`, que dá a fração de abstenção com IC de Wilson.
- **Instrumentos** que não gravam nada:
  - `scripts/medir_calibracao.py` (ECE, MCE e por classe, com bootstrap);
  - `scripts/medir_abstencao.py`;
  - `scripts/calibrar_conformal.py`.
- **Selo de confiança no atendimento.** Ele fala em "classe de satisfação", não em categoria NPS.

**Não verificado.** A cobertura empírica, o ECE e a curva de abstenção. O artefato conformal não foi gerado, então as rotas de confiança respondem 503 até alguém rodar `scripts/calibrar_conformal.py --gravar`.

## E5 — Sinalizadores por regra

**O que entrou.**

- **Cinco regras derivadas na leitura** (`fraus/sinalizadores.py`):
  - `loop_do_bot`;
  - `cliente_repete`;
  - `pedido_de_humano_ignorado`;
  - `escalada_tardia`;
  - `abandono`.
- **Nenhuma regra lê o texto ou o relógio da fala do atendente.** Um teste troca os dois e prova que o resultado não muda. A fala humana também nunca entra na evidência.
- **Conversa sem fala do cliente** dá `None` ("não avaliado"), nunca `[]`.
- **Filtro `?sinalizador=`** em `GET /conversas`:
  - pagina depois de filtrar;
  - respeita o escopo por canal;
  - responde 400 a regra desconhecida.
- **Lista de achados e marca ⚑** na transcrição.
- **Instrumento:** `scripts/medir_sinalizadores.py`.

**Medido.**

- Os 15 casos construídos se comportam como declarado. Isso **verifica a implementação, não mede qualidade**.
- No simulador (60 conversas, sem rótulo de regra, só a taxa de disparo): `abandono` 15, `cliente_repete` 2, as outras 0.
- `loop_do_bot` deixou de ser cúbico: 1.000 respostas do bot levavam 27,98 s e agora levam 0,083 s.

**Não verificado.** Precisão e recall em dado real. Falta a amostra anotada à mão, e a fonte dela é decisão do João. O script aceita `--anotada arquivo.jsonl`. O falso positivo de despedida do bot e o léxico fechado estão declarados em [Limitações](../limitacoes.md).

## E6 — Impacto por tema e início da deterioração

**O que entrou.**

- **Impacto por tema** (`fraus/impacto.py`), em cada tema de `GET /operacao/radar`:
  - é o NPS do tema menos o NPS do resto do recorte;
  - o IC 95% sai de bootstrap multinomial (1.000 reamostras, semente fixa) e tem o rótulo "associação, não causa";
  - abaixo de 30 conversas com sinal em qualquer um dos lados, o resultado é nulo, com o motivo e as duas contagens.
- **Início da deterioração** (`fraus/deterioracao.py`), no campo `deterioracao` de `GET /operacao/replay/{id}`:
  - é a mensagem a partir da qual a estimativa por prefixo fica detratora e não volta;
  - traz o lead time em mensagens e em segundos;
  - é retrospectivo e nunca alerta.
- **Teste de não vazamento.** Alterar a mensagem `j` não muda nenhum prefixo `k < j`, e o teste não passa no vazio.
- **Instrumento:** `scripts/medir_deterioracao.py`.

**Medido.**

- No teto do radar, o custo do bootstrap independe de n: com 15.000 conversas por lado, caiu de 1,58 s para 0,069 s.
- Conferência estrutural do simulador: ele sorteia todas as falas do cliente de um único rótulo, então **não gera trajetória**. O lead time medido nele é artefato do gerador, e o script diz isso antes de imprimir qualquer número.
- Por construção, o início da deterioração **não aumenta o recall** sobre o score final. O que ele acrescenta é o lead time.

**Não verificado.** Recall, falso alarme e lead time com o fusor real: o script sai com código 2. A conferência visual mostrou que a regra não tem margem em torno do limiar (na demonstração, a deterioração começou com uma queda de cerca de 67 para 61 pontos). Isso está declarado.

## Contrato da API

O OpenAPI foi de **76** caminhos (referência da Fase 0) para **80**. Os quatro novos:

| caminho | entrega |
|---|---|
| `/conversas/{conversa_id}/contrafactual` | E1 |
| `/indicadores/drivers` | E1 |
| `/conversas/{conversa_id}/confianca` | E2 |
| `/indicadores/confianca` | E2 |

E5 e E6 acrescentaram só campos e parâmetros a rotas que já existiam:

- `sinalizadores` e `?sinalizador=`;
- `impacto` no radar;
- `deterioracao` no replay.

Nenhum caminho sumiu.

## Verificação final

| comando | resultado |
|---|---|
| `uv run pytest -q` | 1585 passed, 5 skipped (baseline: 1395 passed, 7 skipped) |
| `cd dashboard && npm test` | 389 passed (baseline: 351) |
| `npx tsc --noEmit` | limpo |
| `uv run mkdocs build --strict` | limpo |
| `modelos/`, `modelos-onnx/`, `pyproject.toml`, `uv.lock`, `dashboard/package.json` | sem diff desde `cdaa9e2` |
| `NOMES_FEATURES`, `PESO_NEUTRO_NO_SCORE`, `FEATURES_EM_LOG` | valores intactos (o E1 só moveu o cálculo do score para `_score_das_probabilidades`) |

## Reproduzir

Os instrumentos de medição do fusor pressupõem o artefato `log1p` compatível.
Para a extração atual, `B2W` identifica o CSV, `EXPERIMENTO` um diretório
externo ao repositório/checkpoints e `CABECAS` a raiz dos candidatos. Reserve
o manifesto antes do notebook 01 (`FRAUS_MANIFESTO_FUSOR`), não depois do
treino da cabeça. Cache posicional antigo não é reutilizável por nome; ver
[Generalização](../generalizacao.md).

```bash
uv run python scripts/medir_aditividade.py
uv run python scripts/retreinar_fusor_local.py \
  --b2w "$B2W" --manifesto "$EXPERIMENTO/manifesto.json" --gerar-manifesto
uv run python scripts/retreinar_fusor_local.py \
  --b2w "$B2W" --manifesto "$EXPERIMENTO/manifesto.json" \
  --modelos "$CABECAS" --backend torch \
  --cache "$EXPERIMENTO/features.json" --saida "$EXPERIMENTO/candidato"
uv run python scripts/calibrar_conformal.py \
  --fusor "$EXPERIMENTO/candidato/fusor.joblib" --cache "$EXPERIMENTO/features.json"
uv run --with matplotlib python scripts/medir_calibracao.py \
  --fusor "$EXPERIMENTO/candidato/fusor.joblib" \
  --cache "$EXPERIMENTO/features.json" --png "$EXPERIMENTO/calibracao.png"
uv run python scripts/medir_abstencao.py \
  --fusor "$EXPERIMENTO/candidato/fusor.joblib" --cache "$EXPERIMENTO/features.json"
uv run python scripts/medir_sinalizadores.py --simulador 600 [--anotada amostra.jsonl]
uv run python scripts/medir_deterioracao.py --n 300
```

## Pendências que dependem do João

1. **Fusor `log1p` nesta máquina.** Destrava todas as medições marcadas "não verificado".
2. **Schema `nota_declarada` (E3).** Precisa de aprovação, por causa da paridade SQLite × Postgres.
3. **Amostra anotada dos sinalizadores (E5).** Falta definir a fonte, quem anota e com qual material.
4. **Concorrentes.** As afirmações estão em [concorrentes](concorrentes.md), com URL e data. Elas não substituem uma leitura própria antes da banca.
