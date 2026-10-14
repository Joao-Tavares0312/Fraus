# E6 — Impacto por tema e trajetória de deterioração (retrospectiva)

> Estado: **aprovado em 14/10/2026**. Faz parte de
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

## Desvios aceitos

Decisões do plano de implementação que detalham ou se afastam do desenho acima:

1. O impacto viaja aninhado em `tema["impacto"]` (`impacto_nps`, `ic_inferior`, `ic_superior`, `n_tema`, `n_resto`, `sem_sinal_tema`, `minimo`, `motivo`, `rotulo`), como o `intervalo` já faz.
2. O n mínimo (30 conversas com sinal) vale para os dois lados: com o resto abaixo de 30, o impacto também é `null`.
3. "Resto do recorte" são as conversas examinadas pelo radar (depois do `TETO_RADAR`) que não estão no tema.
4. O IC é o percentil 2,5–97,5 da diferença, com reamostragem independente de tema e resto (1.000 reamostras, semente `20261014`).
5. Virada: primeiro índice com score detrator tal que todo score definido depois dele também é detrator; score `None` não quebra a sequência; sem virada se o último score definido não é detrator (`não terminou detratora`) ou sem nenhum score (`sem sinal do cliente`).
6. Lead time: `falas_ate_o_fim = len(mensagens) − 1 − k` e `segundos_ate_o_fim = fim − enviada_em[k]`, com `fim = encerrada_em` ou a última mensagem; virada na última mensagem dá 0.
7. O campo `virada` que já existe nos pontos (variação ≥ 10) não muda; o novo é `deterioracao.indice_virada`, outro conceito.
8. Conferência do simulador estrutural: um teste prende a assinatura de `gerar_conversa` (um só `frases_cliente`) e o script declara que o lead time medido nele é artefato do gerador.
9. A virada não aumenta o recall sobre o baseline "só no fim" (há virada se e só se o último score é detrator); o script imprime os dois recalls e diz isso. O que a virada acrescenta é o lead time.
10. Com modelo ausente o script imprime a conferência, depois "não verificado — modelos ausentes: <erro>", e sai com código 2; nada de motor dublê (invariante 7).
11. Na tela: o impacto entra no `<details>` do tema, ao lado do NPS do tema; a deterioração entra no Replay com uma linha de referência no gráfico e uma frase. Campo ausente (API antiga) não renderiza nada inventado: o impacto mostra "indisponível nesta versão da API"; a deterioração não mostra nada.
12. Teste de vazamento usa um dublê de texto local que lê o texto (o dublê compartilhado ignora o texto e deixaria o teste vazio).

## Fora de escopo

- Alerta ao vivo.
- Ação automática.
- Persistir trajetória.
