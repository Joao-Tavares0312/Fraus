# Diferenciais — relatório de entrega (14/10/2026)

Este relatório preserva o registro de 14/10/2026 e separa implementação de
validação. A revisão documental de **16/11/2026** conferiu o código e a árvore
de artefatos, sem repetir testes, inferência ou consulta à produção.

**Modelos congelados por decisão do projeto em 16/11/2026:** sem retreino,
calibração, promoção ou troca de pesos/arquitetura na fila ativa. Comandos e
medições de outubro são histórico, não autorização para reabrir essa frente.
Onde não houve medição, não há alegação de qualidade validada.

## Resumo

| entrega | estado | medição real |
|---|---|---|
| E1 — por que esta nota, contrafactual e drivers | implementado; validação real incompleta | aditividade registrada no fusor sintético; **no fusor real: não verificado** |
| E2 — calibração, abstenção e conjunto conformal | implementado; validação real incompleta | **não verificado**; `fraus/dados/conformal_fusor.json` ausente na árvore de 16/11 |
| E3 — nota declarada × inferida | **não iniciado**, adiado; não há aprovação de schema `nota_declarada` | o feedback binário existente não entrega E3 |
| E4 — benchmark contra LLM | **descartado** em 14/10/2026 | — |
| E5 — sinalizadores por regra | implementado; validação real incompleta | casos construídos; **precisão e recall reais: não verificados** |
| E6 — impacto por tema e início da deterioração | implementado; validação real incompleta | **não verificado** no fusor real; lead time do simulador é artefato do gerador |

**Bloqueio histórico de 14/10/2026.** O registro da entrega aponta ausência de
`fusor.joblib` compatível com `log1p` na máquina de desenvolvimento.
`Fusor.carregar` recusa segundos crus de propósito; não se contorna essa
recusa com dublê. Isso explica as medições faltantes daquela data, mas não
identifica quais pesos estão publicados agora.

A régua é uma identidade parcial (`regua_do_fusor`, em `fraus/motor.py`):
assinatura do fusor mais lista de cortesias, sem identidade dos checkpoints
das cabeças ou do backend. Um artefato conformal “da mesma régua” não prova
que todo o pipeline permaneceu igual.

O backend aceita `feedback_declarado` (`-1`/`1`) e comentário, sem alterar
score (`fraus/modelos.py`, `fraus/api/registro.py`). `GET /indicadores` já
retorna total com voto e score e concordância (positivo/promotor,
negativo/detrator). A dashboard não apresenta esse agregado e o TARS não
envia o voto. “Resolveu” não é nota NPS, nem validação causal da satisfação.

## O que vale para todas as entregas

- **Sem LLM em runtime.** Toda explicação é feita dos coeficientes ou por template, e nenhuma chamada de rede entra no caminho de predição.
- **As leituras E1/E2/E5/E6 não alteram score.** Nota e categoria são derivadas na leitura; não há nova predição persistida por essas leituras. Isso não descreve todo o sistema: o feedback binário e os registros operacionais têm contratos próprios.
- **Nenhuma régua nova nesta entrega de 14/10/2026.** Naquele escopo não houve retreino e ficaram intocados:
  - `modelos/`;
  - `NOMES_FEATURES` (39);
  - `PESO_NEUTRO_NO_SCORE` (0,75);
  - `FEATURES_EM_LOG`;
  - a cabeça de ironia.
- **Ausência não vira zero.** Conversa sem sinal, n abaixo do mínimo ou campo ausente numa API antiga aparecem nomeados, nunca como 0.
- **Conformidade.**
  - Nada pontua atendente.
  - As leituras são retrospectivas, sem alerta ao vivo; o schema aceita conversa sem `encerrada_em`, portanto não impõe encerramento na entrada.
  - Nada decide sozinho: as marcas (abstenção, sinalizadores, deterioração) informam e não mudam a nota. O atendimento continua no NPS.
- **O sinal de tempo do fusor é sintético**, e toda métrica nova declara isso.

## E1 — "Por que esta nota", contrafactual de espera e drivers

**O que entrou.**

- **Decomposição exata do fusor** (`Fusor.decompor`). O intercepto mais as contribuições é igual ao log da razão contra a classe de referência, e o score é refeito a partir dos logits.
- **Efeito por família em pontos de score.** É um recálculo exato, mas **não é aditivo**, e a tela diz isso.
- **Frases por template** em `fraus/explicacao.py`, sem LLM. A explicação vem dentro de `GET /conversas/{id}/atribuicao`.
- **`POST /conversas/{id}/contrafactual`**, que testa a primeira resposta ou um teto de espera. Recusa com 422 se a conversa original ou a hipótese sai da faixa (`|z| > 4`); exige motor real, régua vigente e orçamento de mensagens.
- **`GET /indicadores/drivers`**, sobre uma amostra por semente (50, com teto de 200). Mostra a média por família em detratores e em promotores, com IC por bootstrap, e o rótulo "associação no modelo, não causa".
- **Duas telas:** um bloco na transcrição e um painel sob demanda na Visão geral.

**Medido.** No fusor sintético dos testes, a aditividade fecha com erro menor que 1e-9.

**Não verificado.** A aditividade e o tempo no fusor real. O script `scripts/medir_aditividade.py` está pronto.

## E2 — Calibração, abstenção e conjunto conformal

**O que entrou.**

- **Conjunto conformal Mondrian (por classe) sobre o score gravado** (`fraus/conformal.py`). O alvo padrão dos instrumentos é 90%, mas é um parâmetro; a rota usa o alvo do artefato, não uma garantia empiricamente validada no atendimento.
- **Falha explícita sem artefato.** Ausência, conteúdo inválido ou régua incompatível do artefato geram 503; uma conversa com score de régua antiga pode gerar 409 no detalhe. Nunca devolvem conjunto vazio fingindo confiança. O formato previsto para `fraus/dados/conformal_fusor.json` inclui a régua de referência.
- **Abstenção** ("leitura sem confiança suficiente"):
  - dispara quando o conjunto não tem exatamente uma classe ou, no detalhe, quando há deriva;
  - informa e não corrige.
- **Rotas:**
  - `GET /conversas/{id}/confianca`;
  - `GET /indicadores/confianca`, que dá a fração de abstenção com IC de Wilson.
- **Instrumentos de medição:**
  - `scripts/medir_calibracao.py` (ECE, MCE e por classe, com bootstrap);
  - `scripts/medir_abstencao.py`;
  - `scripts/calibrar_conformal.py` (só grava artefato com `--gravar`).
- **Selo de confiança no atendimento.** Ele fala em "classe de satisfação", não em categoria NPS.

**Não verificado nesta entrega.** Cobertura empírica, ECE e curva de abstenção. Há medições sintéticas posteriores de ECE top-1 na campanha de outubro e em 13/11, descritas em [Generalização](../generalizacao.md); elas não validam a cobertura conformal. O arquivo conformal esperado não está na árvore consultada em 16/11/2026; sem um artefato válido no ambiente de execução, as rotas respondem 503. A consulta ao repositório não prova o estado da produção. Calibração permanece fora da fila ativa.

O agregado conta apenas abstenção por conjunto vazio ou múltiplo, excluindo
scores defasados. No detalhe, deriva também pode provocar abstenção, mas
acima de 40 mensagens do cliente a resposta declara deriva não avaliada
(`fraus/api/rotas/confianca.py`).

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
- **Lista de achados e marca de sinalização** na transcrição.
- **Instrumento:** `scripts/medir_sinalizadores.py`.

**Registro de medição de 14/10/2026, não repetido nesta revisão.**

- Os 15 casos construídos se comportam como declarado. Isso **verifica a implementação, não mede qualidade**.
- No simulador (60 conversas, sem rótulo de regra, só a taxa de disparo): `abandono` 15, `cliente_repete` 2, as outras 0.
- `loop_do_bot` deixou de ser cúbico: 1.000 respostas do bot levavam 27,98 s e agora levam 0,083 s.

Fonte dos números acima: registro documental desta entrega. O conjunto
construído está em `fraus/dados/casos_sinalizadores.py`; ele não é uma amostra
real. Não há resultado bruto versionado do benchmark de tempo em
`fraus/dados/`, portanto esses tempos não são um orçamento atual.

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

**Registro de medição de 14/10/2026, não repetido nesta revisão.**

- No teto do radar, o custo do bootstrap independe de n: com 15.000 conversas por lado, caiu de 1,58 s para 0,069 s.
- Conferência estrutural do simulador: ele sorteia todas as falas do cliente de um único rótulo, então **não gera trajetória**. O lead time medido nele é artefato do gerador, e o script diz isso antes de imprimir qualquer número.
- Por construção, o início da deterioração **não aumenta o recall** sobre o score final. O que ele acrescenta é o lead time.

**Não verificado em 14/10/2026.** Recall, falso alarme e lead time com o fusor real: naquela condição, o script saía com código 2. A conferência visual mostrou que a regra não tem margem em torno do limiar (na demonstração, a deterioração começou com uma queda de cerca de 67 para 61 pontos). Isso está declarado; a execução não foi repetida nesta revisão.

Os tempos e a demonstração acima são registros desta entrega, não resultados
JSON versionados em `fraus/dados/` nem prova de desempenho atual.

## Contrato da API

O registro de 14/10/2026 apontava passagem de **76** para **80** caminhos no OpenAPI. É contagem histórica, não o total atual. Os quatro caminhos acrescentados naquela entrega:

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

O registro daquela entrega não apontou remoção de caminhos; a revisão atual não executou o OpenAPI.

## Verificação final

Resultados registrados em **14/10/2026**, sem nova execução nesta revisão.
Os totais abaixo não representam a suíte ou a árvore de trabalho de hoje.

| comando | resultado |
|---|---|
| `uv run pytest -q` | 1585 passed, 5 skipped (baseline: 1395 passed, 7 skipped) |
| `cd dashboard && npm test` | 389 passed (baseline: 351) |
| `npx tsc --noEmit` | limpo |
| `uv run mkdocs build --strict` | limpo |
| `modelos/`, `modelos-onnx/`, `pyproject.toml`, `uv.lock`, `dashboard/package.json` | sem diff desde `cdaa9e2` |
| `NOMES_FEATURES`, `PESO_NEUTRO_NO_SCORE`, `FEATURES_EM_LOG` | valores intactos (o E1 só moveu o cálculo do score para `_score_das_probabilidades`) |

## Reproduzir

Os instrumentos abaixo existem para medir o comportamento dos artefatos;
não comprovam que as medições tenham ocorrido. Exigem fusor compatível com
`log1p` e, quando aplicável, cache com manifesto e proveniência verificáveis.
Cache posicional antigo não é reutilizável por nome; ver
[Generalização](../generalizacao.md). Preparação de candidato e calibração
foram retiradas desta sequência porque estão fora da fila ativa desde
16/11/2026. Medir artefato existente não autoriza retreinar nem promover.

Defina `FUSOR` como o caminho do artefato existente e `CACHE` como o cache
compatível com esse artefato e seu manifesto. Não use pesos candidatos
como substituição silenciosa dos ativos.

```bash
uv run python scripts/medir_aditividade.py --fusor "$FUSOR"
uv run python scripts/medir_calibracao.py --fusor "$FUSOR" --cache "$CACHE"
uv run python scripts/medir_abstencao.py --fusor "$FUSOR" --cache "$CACHE"
uv run python scripts/medir_sinalizadores.py --simulador 600
# Com amostra autorizada e anotada: acrescente --anotada amostra.jsonl.
uv run python scripts/medir_deterioracao.py --n 300
```

## Pendências que dependem do João

1. **Medição dos artefatos existentes.** Depende de disponibilidade e compatibilidade verificadas, sem contornar a recusa de segundos crus. Não inclui treinamento ou promoção.
2. **E3 adiado.** A comparação de nota declarada 0–10 com inferida não foi iniciada e não tem schema aprovado. Completar o feedback binário existente é outra frente.
3. **Amostra real anotada dos sinalizadores (E5).** Definir fonte autorizada e anotação antes de medir precisão e recall; não fabricar corpus.
4. **Concorrentes.** As afirmações estão em [concorrentes](concorrentes.md), com URL e data; as fontes precisam de releitura antes da banca.

Esta lista registra dependências dos diferenciais, não substitui a fila
priorizada do projeto. E1/E2/E5/E6 implementados não significam validação real
concluída; E4 continua descartado.
