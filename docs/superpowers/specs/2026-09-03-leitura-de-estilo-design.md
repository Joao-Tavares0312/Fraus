# Leitura de estilo por mensagem + revisão de limiares

Data: 2026-09-03
Status: aprovado para plano de implementação
Parte de uma sessão única com `2026-09-03-incongruencia-ironia-design.md` e
`2026-09-03-censura-pii-design.md`.

## Contexto

`fraus/sinais/estilo.py` já calcula caixa alta, alongamento, pontuação
enfática, palavrão e censura sobre as falas do cliente, agregado por
conversa. As 6 features (`estilo_*`) já aparecem no painel genérico de
contribuições da dashboard (`BarrasDeFeature.tsx`, rótulos em
`derivacoes.ts`), mas não têm destaque equivalente ao que emoção e ironia já
têm: `CabecasDeLeitura.tsx` mostra a leitura **por frase** dessas duas no
Simulador e no Analisador, enquanto estilo só existe agregado, misturado nas
outras ~34-39 barras.

Esta spec cobre dois ajustes, ambos restritos às falas do cliente (sem
mudança de escopo para o bot):

1. Um componente novo de leitura de estilo, no mesmo lugar onde
   `CabecasDeLeitura` já aparece.
2. Revisão dos limiares fixos contra a bibliografia já levantada para o
   sinal de incongruência (Ptáček et al. 2014 e correlatos citam limiares
   típicos de pontuação/repetição/maiúsculas) — ajuste só onde a literatura
   diverge claramente do valor atual, com a justificativa registrada no
   código. Não é calibração por dado real: não há corpus rotulado de
   atendimento disponível para isso ainda.

## Componente novo

`LeituraDeEstilo`, em `dashboard/components/CabecasDeLeitura.tsx` (mesmo
arquivo, para não repetir o problema que o comentário do arquivo já descreve:
duas cópias de painel que explica um modelo envelhecem separadas). Mostra,
por mensagem do cliente:

- indicador de caixa alta (grito) presente/ausente na mensagem
- indicador de alongamento presente/ausente
- pontuação enfática (contagem de `!!`/`?!` na mensagem)
- palavrão: presente e, se sim, intensidade (leve/médio/pesado) e se
  dirigido a pessoa
- censura (mascaramento tipo `p*rra`) presente/ausente

Diferente de `features_estilo` (que agrega a conversa inteira), o componente
roda as mesmas funções auxiliares de `estilo.py` (`_e_grito`,
`_tem_alongamento`, `PONTUACAO_ENFATICA`, `tem_censura`/`casar_censurado`)
**por mensagem individual**, exigindo que essas funções fiquem expostas
(hoje já são funções de módulo, não precisam mudar de assinatura — só a API
precisa de uma rota ou campo que devolva a leitura por mensagem, hoje só
`features_estilo` agregado é exposto). Mesmo texto de ressalva do padrão
`CabecasDeLeitura`: o número aqui é desta mensagem, a média que pesa no
Fusor é outra.

## Revisão de limiares

Cada constante de `estilo.py` — `MINIMO_CAIXA_ALTA`, `MINIMO_ALONGAMENTO`, o
padrão `PONTUACAO_ENFATICA` — é revisada contra a bibliografia de
`2026-09-03-incongruencia-bibliografia.md` (itens 26-29: Burgers 2012,
Ptáček 2014, Bouazizi & Ohtsuki). Ajuste só acontece se a literatura indicar
um valor claramente diferente do atual; a justificativa (valor antigo, valor
novo, referência, por que muda) substitui ou complementa o comentário que já
existe em cada constante — o padrão de comentário "POR QUE" que o arquivo já
segue.

## Testes

- Testes novos para `LeituraDeEstilo` (dashboard): mensagem com grito único
  numa conversa de várias falas mostra o indicador só naquela mensagem, não
  nas demais (a queixa que motivou a existência do componente).
- Se algum limiar mudar: os testes existentes de `test_sinal_estilo.py` que
  fixam esse limiar são atualizados junto, nunca soltos (limiar e teste
  andam na mesma mudança).
