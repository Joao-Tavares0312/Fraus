# Indicadores

NPS inferido, CSAT inferido, contenção, **falso containment** e série diária.
Ausência de medida permanece `None`: zero só significa um valor calculado.
Contagens, por sua vez, podem legitimamente ser zero. O ponto de NPS não é
exibido abaixo de 30 conversas com sinal; o intervalo amostral não mede erro
do modelo. Faixas vigentes são passadas por parâmetro.

::: fraus.indicadores

## Impacto por tema

Diferença entre NPS inferido do tema e do resto do recorte, com bootstrap.
Exige pelo menos 30 conversas com sinal em cada lado: associação, não causa.

::: fraus.impacto

## Deterioração retrospectiva

Lê os scores por prefixo do replay de conversa encerrada. Não é alerta ao vivo
e não acrescenta recall sobre a classificação final.

::: fraus.deterioracao
