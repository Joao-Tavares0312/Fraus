# E3 — Declarado × inferido

> Estado: **aguardando aprovação, com schema novo** (regra 5). Faz parte de
> [Diferenciais](2026-10-14-diferenciais-visao-geral.md).

## Objetivo

Duas perguntas:

- O NPS inferido concorda com a nota que o cliente declarou?
- Quantos clientes "silenciosos" o Fraus enxerga e a pesquisa não alcança?

É a prova da tese central, e só vale com dado real de parceiro. Sem esse
dado, tudo sai rotulado como **ilustrativo**.

## Desenho

**1. Campo opcional `nota_declarada: int 0..10 | None`.**

- **Onde entra:** em `Conversa` (`fraus/modelos.py`), ao lado de
  `feedback_declarado`, e na ingestão: `PedidoIngestao`, o webhook e uma
  coluna opcional `nota_declarada` no CSV.
- **Como é guardado:** dentro do `payload` JSON que já existe. **Nenhuma
  coluna ou tabela nova, nenhuma DDL**, então a paridade entre SQLite e
  Postgres é automática.
- Mesmo assim, o contrato de entrada muda, e por isso **peço aprovação**.
- **O que o campo nunca faz:** nunca entra no vetor, no score, na nota ou na
  categoria (invariante 3); nunca é aceito como veredito.
- **Validação:** inteiro de 0 a 10. Fora disso é 422. Ausente é `None`,
  nunca 0.

**2. Relatório** (`fraus/declarado.py`, puro, mais
`scripts/relatorio_declarado.py` e a rota
`GET /indicadores/declarado-inferido`, com escopo por canal):

- **Concordância:** Spearman entre a nota declarada e o score inferido;
  kappa ponderado quadrático entre as categorias declarada e inferida (faixas
  vigentes, passadas por parâmetro); matriz de confusão 3×3.
- **IC:** bootstrap para Spearman e kappa.
- **Cobertura:** % de conversas com nota declarada × % com score Fraus.
- **Recorte "sem resposta de pesquisa":** n e NPS inferido das conversas com
  sinal e sem nota declarada.
- **Abaixo de 30 pares**, a concordância é ocultada e só o `n` aparece, como
  o cartão de NPS faz.

**3. Dado sintético ilustrativo.**

- `scripts/gerar_declarado_ilustrativo.py` gera, por semente, a nota
  declarada a partir do **rótulo** do simulador, com ruído e taxa de resposta
  de cerca de 10–20%.
- Todo artefato e toda tela com esse dado traz a marca "ilustrativo — não é
  validação".
- O script de relatório aceita CSV de parceiro sem mudança de código.

## Métrica de aceitação

- **Testes do campo:** validação de 0 a 10, ausente = `None`, e o campo
  **não muda o score**. Esse último é um teste de regressão: mesma conversa,
  com e sem nota, dá o mesmo score.
- **Testes do relatório:** Spearman e kappa conferidos contra
  `scipy`/`sklearn` em casos pequenos; ocultação abaixo de 30; escopo por
  canal; `None` fora das contas.
- **Rótulo:** relatório com dado sintético traz "ilustrativo" no cabeçalho, e
  há teste para isso.

## Dados

Sintéticos (ilustrativos) até haver dado de parceiro. O dado de parceiro
**nunca** vai para fixture.

## Limitações declaradas

- Concordância medida em dado sintético não valida nada.
- Com dado real, o viés de quem responde pesquisa afeta a comparação, e o
  recorte "sem resposta" **não tem verdade de referência**: é estimativa, não
  medida.

## Fora de escopo

- Usar a nota declarada para treinar ou recalibrar.
- Pesquisa ativa ao cliente.
