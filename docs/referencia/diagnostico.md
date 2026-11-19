# Evidência e deriva

Diagnósticos de evidência observável, distribuição e incerteza. Nenhum destes
módulos corrige o score gravado; probabilidade, evidência fraca e conjunto
conformal são grandezas diferentes.

**Leitura histórica das docstrings:** os casos de 08/09/2026 em segundos crus
não descrevem a transformação atual do vetor. Hoje `fraus.fusor.vetorizar`
aplica `log1p` às quatro features de espera; o carregador recusa o artefato
antigo. Retreino e calibração citados como propostas históricas estão fora da
fila por decisão de 16/11/2026. Veja [Arquitetura](../arquitetura.md) para os
contratos HTTP e [Limitações](../limitacoes.md) antes de interpretar os números.

## Evidência fraca — a cabeça tracejada

::: fraus.evidencia

## Deriva de distribuição — a invariante 10 em runtime

::: fraus.deriva

## Conjunto conformal e abstenção

`GET /conversas/{id}/confianca` e `GET /indicadores/confianca` exigem artefato
compatível com a régua. Sua presença no código não comprova disponibilidade no
ambiente. A garantia é condicionada à permutabilidade, não valida atendimento
real sob mudança de distribuição.

::: fraus.conformal

## Medição de calibração

ECE, MCE e métricas por classe, com bootstrap: medição, não ajuste automático
das probabilidades em runtime.

::: fraus.calibracao

## Sinalizadores por regra

Cinco regras derivadas na leitura; não leem texto nem relógio da fala humana
e não modificam score, nota ou categoria.

::: fraus.sinalizadores

## Avaliação por fatia

Regras e métricas puras; a execução dos modelos pertence ao script
`scripts/avaliar_por_fatias.py`. Resultado sintético não é validação real.

::: fraus.fatias
