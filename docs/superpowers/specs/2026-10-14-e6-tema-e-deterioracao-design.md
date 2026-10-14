# E6 — Impacto por tema e trajetória de deterioração (retrospectiva)

> Estado: **aguardando aprovação**. Faz parte de
> [Diferenciais](2026-10-14-diferenciais-visao-geral.md).

## Objetivo

Duas perguntas:

- Quanto o NPS inferido muda em conversas de um tema, com IC?
- Numa conversa **encerrada**, onde a estimativa começou a cair, e quanto
  antes do fim isso seria visível?

As duas são **retrospectivas e em lote**. Alerta durante o atendimento está
fora de escopo (regra 3 da Conformidade).

## Desenho

**1. Tema × impacto.** Estende `descobrir_temas` (`fraus/operacao.py`) e
`GET /operacao/radar`.

- **Novo campo por tema:** `impacto_nps = NPS(tema) − NPS(resto do recorte)`.
  O IC vem de bootstrap (1.000 reamostras, semente fixa). As faixas vigentes
  são passadas por parâmetro.
- **Abaixo de 30 conversas com sinal no tema:** `impacto_nps: null` e
  `motivo: "n abaixo do mínimo"`, como o cartão de NPS faz. Nunca 0.
- **Rótulo:** "associação, não causa". Um tema pode se correlacionar com
  outro fator.

**2. Replay de deterioração.** É uma função pura sobre os scores por prefixo
que `Motor.scores_do_replay` já produz, e que não veem fala futura.

- **Ponto de virada:** o primeiro prefixo a partir do qual o score fica abaixo
  do limiar de detrator (faixa vigente, nota ≤ 6) **e não volta acima** até o
  fim.
- **Lead time hipotético:** o número de falas e o tempo (timestamps) entre a
  virada e o fim. É derivado e não é gravado (invariante 5).
- **Saída na rota:** entra em `GET /operacao/replay/{id}` como o campo
  `deterioracao`.

**3. Medição** (`scripts/medir_deterioracao.py`).

- Sobre conversas do simulador com rótulo e semente: recall de detratores no
  fim, taxa de falso alarme e curva limiar × recall.
- **Comparação** com o baseline "só no fim", que é o score final.
- **Conferência obrigatória:** se o simulador não gera trajetória (rótulo
  constante ao longo da conversa), o lead time medido é **artefato do
  gerador**. Isso é verificado primeiro e declarado como sair.

## Métrica de aceitação

- **Vazamento:** um teste **falha** se o score do prefixo `k` mudar quando se
  altera uma mensagem `j > k`. É o teste de não vazamento.
- **Tema:** abaixo do n mínimo devolve `null` com motivo; o IC é reprodutível
  por semente; o escopo por canal é respeitado; conversas sem sinal ficam fora
  e são contadas.
- **Score intacto:** nada é gravado e os scores não mudam.

## Dados

Simulador, com o tempo **sintético** declarado. Nenhum dado real.

## Limitações declaradas

- Simulação não demonstra causalidade.
- O lead time em dado sintético não prevê o lead time em produção.
- O tema vem de TF-IDF com DBSCAN e é instável com pouco dado.

## Fora de escopo

- Alerta ao vivo.
- Ação automática.
- Persistir trajetória.
