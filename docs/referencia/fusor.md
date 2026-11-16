# O fusor e as 39 features

`NOMES_FEATURES` é **o contrato**. O comentário dele conta a história inteira do
vetor — por que subiu para 40, por que a ironia saiu, e por que 39 é o número
de hoje.

São sete famílias no vetor e oito no sistema. A ironia continua obrigatória
para leitura por mensagem, mas não tem entrada aqui. `vetorizar` aplica
`log1p` às quatro features de `FEATURES_EM_LOG` antes do `StandardScaler`;
chave ausente é `KeyError`, chave extra é `ValueError`. A carga valida número
de entradas e escala do tempo.
As três latências sem resposta aceitam `None`: o vetor usa `NaN` e o fusor
neutraliza essas entradas depois do scaler (`z = 0`). As chaves não podem
ser omitidas; nenhuma outra feature aceita ausência.

::: fraus.fusor

## Motor de inferência

Coordena as três cabeças e o fusor; a régua do motor cobre a assinatura do
fusor e a regra de cortesia, não os bytes dos classificadores ou o executor.
A curadoria tem versão própria. Veja [Arquitetura](../arquitetura.md).

::: fraus.motor

## Explicações por template

Contribuições somam no logit; efeitos por família não somam diretamente em
pontos de score e não demonstram causalidade. Nenhum LLM gera as frases.

::: fraus.explicacao
