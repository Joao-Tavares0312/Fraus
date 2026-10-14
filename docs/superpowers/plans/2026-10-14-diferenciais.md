# Plano — Diferenciais (14/10/2026)

> Estado: **aguardando aprovação**.
>
> - Specs: `docs/superpowers/specs/2026-10-14-*`.
> - Branch: `diferenciais/2026-10-14`, criado de `main` em `cdaa9e2`.
> - Cada entrega é **um commit**, com a mensagem trazendo o que muda e a
>   medição. Cada uma passa por TDD, `/review` e verificação com a saída
>   colada.
> - Este plano é de nível de tarefa. Quando o spec de uma entrega for
>   aprovado, ela ganha o plano detalhado de `writing-plans`, com os testes
>   escritos antes.

## Ordem e dependências

| # | entrega | depende de | dá para fazer sem os pesos? |
|---|---|---|---|
| 0 | reconciliação de docs | — | sim, **feito** (`07ffa6a`) |
| E1 | por que esta nota + drivers | — | código e testes sim (fusor sintético); exemplos reais não |
| E2 | calibração + conformal + abstenção | pesos + download B2W | código e testes sim; **medição não** |
| E3 | declarado × inferido | **aprovação de schema** | sim (sintético ilustrativo) |
| ~~E4~~ | benchmark × LLM | **descartado em 14/10/2026** | — |
| E5 | sinalizadores | fonte da amostra anotada | sim |
| E6 | tema × impacto + deterioração | — | código sim; medição do replay exige pesos |

Corte se faltar tempo: **E1–E3** (o E4 foi descartado). Paralelizável com subagentes, cada um no seu
worktree, porque os arquivos são disjuntos:

- **E1** em `fraus/fusor.py` e `fraus/explicacao.py`;
- **E2** em `fraus/conformal.py` e `scripts/`;
- **E5** em `fraus/sinalizadores.py`;

O ponto de conflito é `_com_derivacoes` em `fraus/api/rotas/conversas.py`
(E2 e E5). Esse ponto é integrado em série.

## Tarefas

**E1.**

1. Teste vermelho de aditividade em `Fusor.decompor` (fusor sintético de 3
   classes e binário).
2. Implementação de `decompor` e do mapa feature→família no servidor.
3. Efeito por família (zerar `z` da família) e teste contra `pontuar`.
4. Templates em `fraus/explicacao.py`, um teste por template.
5. `POST /conversas/{id}/contrafactual`, com testes de recusa `|z| > 4`
   (422), de escopo (404) e de score gravado intacto.
6. `GET /explicacao/drivers`, com teto de 200, bootstrap por semente, contagem
   de sem sinal e de outra régua, escopo e o rótulo "associação".
7. Front: bloco na transcrição e painel de Drivers, com testes vitest.
   Conferência em 390 px e desktop, piso de 11 px.
8. Commit `feat(explicacao): ...`.

**E2** (só a medição espera os pesos).

1. `fraus/conformal.py` puro: quantis por classe com correção finita;
   conjunto por score; testes de cobertura em dado sintético com
   permutabilidade verdadeira.
2. Carga do artefato com assinatura, falha 503 e testes vermelhos primeiro.
3. Abstenção em `_com_derivacoes` e no detalhe com deriva; teste "não sai do
   NPS/CSAT".
4. `scripts/medir_calibracao.py`: ECE/MCE, classwise, bootstrap, PNG,
   proposta de temperatura sem aplicar.
5. `scripts/medir_abstencao.py`: cobertura × acurácia, risco × cobertura.
6. Com os pesos: gerar o cache do holdout, gerar
   `fraus/dados/conformal_fusor.json`, medir, e estender o cartão do modelo.
7. Front: selo "leitura sem confiança suficiente", com o critério que
   disparou.
8. Commit `feat(confianca): ...`.

**E3** (depois da aprovação do schema).

1. Testes do campo `nota_declarada` (0–10, `None`, não muda o score).
2. Ingestão: `PedidoIngestao`, webhook e coluna CSV opcional.
3. `fraus/declarado.py` com Spearman, kappa quadrático, matriz, cobertura,
   recorte silencioso e ocultação abaixo de 30.
4. Gerador ilustrativo, script de relatório e rota com escopo.
5. Commit `feat(declarado): ...`.

**E4.** Descartado pelo João em 14/10/2026.

**E5.**

1. Uma regra por vez: teste positivo, negativo e de borda, depois a
   implementação.
2. Guarda de Conformidade (nenhuma regra lê o conteúdo de fala `humano`).
3. Exposição em `_com_derivacoes`, filtro `?sinalizador=`, destaque na
   transcrição.
4. `scripts/medir_sinalizadores.py` com IC de Wilson.
5. Commit `feat(sinalizadores): ...`.

**E6.**

1. Teste de não vazamento do replay (que falha se o prefixo vê o futuro).
2. Deterioração pura sobre os scores por prefixo; campo no replay.
3. `impacto_nps` por tema com bootstrap e n mínimo; tela do Radar.
4. Conferência de trajetória no simulador antes de medir lead time.
5. `scripts/medir_deterioracao.py`.
6. Commit `feat(radar): ...`.

**Transversal.**

- README, Limitações, Cartão do modelo, Arquitetura e, se o escopo mudar,
  Conformidade.
- `docs/diferenciais/concorrentes.md`, com URL e data reverificadas.
- `docs/diferenciais/roteiro-demo.md`, incluindo o slide "o que o Fraus não
  faz".
- `docs/diferenciais/relatorio.md`.

**Verificação final**, com a saída colada:

- a lista de comandos da missão;
- o diff do OpenAPI (só rotas novas, contra os 76 caminhos de referência);
- `requirements.txt` sem dependência nova;
- `modelos/` e `NOMES_FEATURES` intactos.
